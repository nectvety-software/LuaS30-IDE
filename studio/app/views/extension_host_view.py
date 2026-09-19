"""Host webview cho một extension đã cài (``type: "webview"``).

Trang HTML của extension chạy trong QWebEngineView và nhận về một bridge
``window.luaS30`` qua QWebChannel:

    window.luaS30.project(cb)            -> {"root": "...", "name": "..."} | null
    window.luaS30.writeFiles(files, cb)  -> {"ok": bool, "written": [...], "errors": [...]}
    window.luaS30.notify(message, level) -> báo lên status bar của Studio
    window.luaS30.extension(cb)          -> {"id","name","version"}

files là mảng ``{"path": "duong/dan/tuong.doi/trong/du/an", "text": "..."}``
hoặc ``{"path": ..., "base64": "<png/json nhị phân>"}``. Mọi thao tác ghi bị
giới hạn trong thư mục dự án và chặn tệp nhạy cảm; nếu chưa mở dự án thì
bridge trả lỗi thay vì ghi lung tung. Trang mở bằng trình duyệt thường (không
có Qt) vẫn chạy được vì ``window.luaS30`` chỉ tồn tại trong host — extension
phải kiểm tra trước khi dùng.

Import QtWebEngine được hoãn vào trong hàm để ``import`` module này khi chưa
có display (offscreen validator, boot check) không kéo theo Chromium.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

from PySide6.QtCore import QFile, QIODevice, QObject, QUrl, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.services.extension_service import ExtensionManifest
from app.ui import palette
from app.vxpui.icons import icon

MAX_FILES_PER_BATCH = 512
MAX_FILE_BYTES = 8 * 1024 * 1024
_BLOCKED_NAMES = {".env", ".env.local", "credentials.json", "secrets.json", "id_rsa", "id_ed25519"}
_BLOCKED_PARTS = {".git", ".luas30", "__pycache__", "node_modules"}

_BRIDGE_JS = """
(function () {
  function install() {
    if (typeof QWebChannel === "undefined" || typeof qt === "undefined" || !qt.webChannelTransport) return;
    if (window.luaS30) return;
    new QWebChannel(qt.webChannelTransport, function (channel) {
      var raw = channel.objects.luaS30;
      if (!raw) return;
      function parse(value) {
        try { return JSON.parse(value); } catch (e) { return null; }
      }
      window.luaS30 = {
        extension: function (cb) { raw.extensionInfo(function (r) { cb(parse(r)); }); },
        project: function (cb) { raw.projectInfo(function (r) { cb(parse(r)); }); },
        notify: function (message, level) { raw.notify(String(message || ""), String(level || "info")); },
        writeFiles: function (files, cb) {
          raw.writeProjectFiles(JSON.stringify(files || []), function (result) {
            var parsed = null;
            try { parsed = JSON.parse(result); } catch (e) { parsed = null; }
            if (!parsed) parsed = { ok: false, error: String(result) };
            if (typeof cb === "function") cb(parsed);
          });
        }
      };
      window.luaS30Ready = true;
      window.dispatchEvent(new Event("luas30-bridge-ready"));
    });
  }
  install();
  document.addEventListener("DOMContentLoaded", install);
})();
"""


def _safe_relative(root: Path, raw: str) -> Path | None:
    value = str(raw or "").strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    if not value or value.startswith("/") or ".." in Path(value).parts:
        return None
    try:
        target = (root / value).resolve()
        target.relative_to(root)
    except (OSError, ValueError):
        return None
    name = target.name.lower()
    if name in _BLOCKED_NAMES or any(token in name for token in ("secret", "credential", "private_key")):
        return None
    rel_parts = {part.lower() for part in target.relative_to(root).parts}
    if rel_parts & _BLOCKED_PARTS:
        return None
    return target


class ExtensionBridge(QObject):
    """Slots an toàn cho phía HTML — chỉ nhân danh một extension cụ thể."""

    def __init__(
        self,
        manifest: ExtensionManifest,
        project_root_provider,
        status_reporter=None,
        on_files_written=None,
    ) -> None:
        super().__init__()
        self.manifest = manifest
        self._project_root = project_root_provider
        self._status = status_reporter
        self._written = on_files_written

    @Slot(result=str)
    def extensionInfo(self) -> str:
        return json.dumps(
            {"id": self.manifest.id, "name": self.manifest.name, "version": self.manifest.version}
        )

    @Slot(result=str)
    def projectInfo(self) -> str:
        root = self._project_root() if callable(self._project_root) else None
        if not root:
            return json.dumps({"root": None, "name": None})
        root = Path(root)
        return json.dumps({"root": str(root), "name": root.name})

    @Slot(str, str)
    def notify(self, message: str, level: str = "info") -> None:
        text = " · ".join(part for part in (self.manifest.name, str(message or "").strip()) if part)
        if callable(self._status):
            self._status(text)

    @Slot(str, result=str)
    def writeProjectFiles(self, payload: str) -> str:
        root = self._project_root() if callable(self._project_root) else None
        if not root:
            return json.dumps({"ok": False, "error": "Chưa mở dự án nào để ghi tệp."})
        try:
            # Windows có thể trả tên dạng 8.3 (DOXUAN~1) — resolve() để so
            # relative_to với đường dẫn đã làm phẳng của từng tệp.
            root = Path(root).resolve()
        except OSError:
            return json.dumps({"ok": False, "error": "Thư mục dự án không tồn tại."})
        try:
            files = json.loads(str(payload or "[]"))
        except json.JSONDecodeError as exc:
            return json.dumps({"ok": False, "error": f"Payload không phải JSON: {exc}"})
        if not isinstance(files, list) or not files:
            return json.dumps({"ok": False, "error": "writeFiles cần mảng không rỗng."})
        if len(files) > MAX_FILES_PER_BATCH:
            return json.dumps({"ok": False, "error": f"Quá {MAX_FILES_PER_BATCH} tệp trong một lần ghi."})

        written: list[str] = []
        errors: list[str] = []
        for item in files:
            if not isinstance(item, dict):
                errors.append("Mục ghi phải là object {path, text|base64}.")
                continue
            raw_path = str(item.get("path") or "")
            target = _safe_relative(root, raw_path)
            if target is None:
                errors.append(f"Đường dẫn bị chặn: {raw_path!r}")
                continue
            data, error = _decode_payload(item)
            if error:
                errors.append(f"{raw_path}: {error}")
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                written.append(target.relative_to(root).as_posix())
            except OSError as exc:
                errors.append(f"{raw_path}: {exc}")

        if written and callable(self._written):
            self._written(written)
        status = json.dumps(
            {
                "ok": not errors,
                "written": written,
                "errors": errors,
                "projectRoot": str(root),
            },
            ensure_ascii=False,
        )
        return status


def _decode_payload(item: dict) -> tuple[bytes, str]:
    if item.get("base64") is not None:
        raw = str(item.get("base64") or "")
        # Data-URL ("data:image/png;base64,....") là dạng phổ biến nhất từ canvas.
        if raw.startswith("data:") and "," in raw:
            raw = raw.split(",", 1)[1]
        try:
            data = base64.b64decode(raw, validate=False)
        except Exception:
            return b"", "base64 không giải mã được."
    elif item.get("text") is not None:
        data = str(item.get("text")).encode("utf-8")
    else:
        return b"", "Thiếu 'text' hoặc 'base64'."
    if not data:
        return b"", "Tệp rỗng."
    if len(data) > MAX_FILE_BYTES:
        return b"", f"Tệp vượt {MAX_FILE_BYTES // (1024 * 1024)}MB."
    return data, ""


def _bridge_script_source() -> str:
    source = ""
    script_file = QFile(":/qtwebchannel/qwebchannel.js")
    if script_file.exists() and script_file.open(QIODevice.ReadOnly):
        source = bytes(script_file.readAll()).decode("utf-8", "replace")
        script_file.close()
    return source + "\n" + _BRIDGE_JS


class ExtensionHostView(QWidget):
    def __init__(
        self,
        manifest: ExtensionManifest,
        *,
        project_root_provider,
        status_reporter=None,
        on_files_written=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        from PySide6.QtWebChannel import QWebChannel
        from PySide6.QtWebEngineCore import QWebEngineScript, QWebEngineSettings
        from PySide6.QtWebEngineWidgets import QWebEngineView

        self.manifest = manifest
        self._project_root = project_root_provider

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("ExtensionHostHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)
        header_layout.setSpacing(8)
        title = QLabel(f"{manifest.name} · v{manifest.version}")
        title.setObjectName("ExtensionHostTitle")
        description = QLabel(manifest.description)
        description.setObjectName("Muted")
        description.setWordWrap(False)
        reload_button = QPushButton("Tải lại")
        reload_button.setObjectName("GhostButton")
        reload_button.setIcon(icon("fa5s.sync-alt"))
        header_layout.addWidget(title)
        header_layout.addWidget(description, 1)
        header_layout.addWidget(reload_button)
        layout.addWidget(header)

        self.web = QWebEngineView(self)
        settings = self.web.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        try:
            self.web.setBackgroundColor(QColor(palette.BG_SURFACE))
        except Exception:
            pass
        layout.addWidget(self.web, 1)

        self.bridge = ExtensionBridge(
            manifest,
            project_root_provider,
            status_reporter=status_reporter,
            on_files_written=on_files_written,
        )
        self.channel = QWebChannel(self.web.page())
        self.channel.registerObject("luaS30", self.bridge)
        self.web.page().setWebChannel(self.channel)

        script = QWebEngineScript()
        script.setName("luas30-bridge")
        script.setSourceCode(_bridge_script_source())
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(False)
        self.web.page().scripts().insert(script)

        reload_button.clicked.connect(self.reload)
        self.web.loadFinished.connect(self._on_loaded)
        self.reload()

    def reload(self) -> None:
        self.web.load(QUrl.fromLocalFile(str(self.manifest.entry)))

    def _on_loaded(self, ok: bool) -> None:
        if not ok:
            self.bridge.notify(f"Không tải được giao diện {self.manifest.entry.name}", "error")

    def focus_webview(self) -> None:
        self.web.setFocus()
