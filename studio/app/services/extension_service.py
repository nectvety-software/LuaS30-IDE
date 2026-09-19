"""Chuẩn tiện ích mở rộng của LuaS30 Studio.

Một extension là một thư mục con trong ``<engine_root>/extensions/``:

    extensions/<id>/
        extension.json      — manifest (bắt buộc, nguồn DUY NHẤT mô tả tool)
        ui/index.html       — entry webview (trỏ tới bằng manifest "entry")
        SKILLS.md/PROMPT.md — tài liệu bất kỳ: ChatAI tự nạp làm luật khi trả lời

Manifest tối thiểu::

    {"id": "sprite-sheet", "name": "Sprite Sheet Cutter", "version": "1.0.0",
     "description": "...", "author": "...", "type": "webview",
     "entry": "ui/index.html", "icon": "fa5s.crop-alt", "requiresProject": true}

id phải trùng tên thư mục chứa nó; mọi đường dẫn trong manifest là tương đối
và bị chặn thoát khỏi thư mục extension. type "webview" là host được hỗ trợ
duy nhất hiện tại — manifest lỗi hoặc type lạ bị bỏ qua và ghi vào
``last_errors`` để in ra console khi cần chẩn đoán.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

EXTENSIONS_DIR_NAME = "extensions"
MANIFEST_NAME = "extension.json"
SUPPORTED_TYPES = ("webview",)
INSTRUCTION_NAMES = ("SKILLS.md", "SKILL.md", "PROMPT.md")
DEFAULT_ICON = "fa5s.puzzle-piece"


@dataclass(frozen=True)
class ExtensionManifest:
    id: str
    name: str
    version: str
    description: str
    author: str
    type: str
    entry: Path
    root: Path
    icon: str = DEFAULT_ICON
    requires_project: bool = True
    manifest_path: Path | None = None

    @property
    def tool_key(self) -> str:
        return f"extension:{self.id}"

    def instruction_docs(self) -> list[Path]:
        return [self.root / name for name in INSTRUCTION_NAMES if (self.root / name).is_file()]

    def agent_summary(self) -> str:
        return (
            f'<extension id={self.id!r} type={self.type!r}>\n'
            f"name: {self.name}\nversion: {self.version}\nauthor: {self.author}\n"
            f"description: {self.description}\n"
            f"folder: extensions/{self.id}\nentry: {self.entry.relative_to(self.root).as_posix()}\n"
            f"docs: {', '.join(d.name for d in self.instruction_docs()) or '(none)'}\n"
            f"</extension>"
        )


def _relative_inside(root: Path, raw: str) -> Path | None:
    value = str(raw or "").strip().replace("\\", "/")
    if not value or value.startswith("/") or ".." in Path(value).parts:
        return None
    try:
        target = (root / value).resolve()
        target.relative_to(root)
    except (OSError, ValueError):
        return None
    return target


def load_manifest(extension_dir: Path) -> tuple[ExtensionManifest | None, str]:
    """Đọc một thư mục extension; trả (manifest, lỗi). Manifest hợp lệ ⇒ lỗi == ''."""
    path = extension_dir / MANIFEST_NAME
    if not path.is_file():
        return None, f"{extension_dir.name}: thiếu {MANIFEST_NAME}"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{extension_dir.name}: {MANIFEST_NAME} không hợp lệ ({exc})"
    if not isinstance(data, dict):
        return None, f"{extension_dir.name}: {MANIFEST_NAME} phải là JSON object"

    ext_id = str(data.get("id") or "").strip()
    if ext_id != extension_dir.name:
        return None, f"{extension_dir.name}: id {ext_id!r} phải trùng tên thư mục"
    ext_type = str(data.get("type") or "webview").strip().lower()
    if ext_type not in SUPPORTED_TYPES:
        return None, f"{extension_dir.name}: type {ext_type!r} chưa được hỗ trợ"
    entry = _relative_inside(extension_dir.resolve(), str(data.get("entry") or ""))
    if entry is None or not entry.is_file():
        return None, f"{extension_dir.name}: entry {data.get('entry')!r} không tồn tại trong extension"

    return (
        ExtensionManifest(
            id=ext_id,
            name=str(data.get("name") or ext_id).strip() or ext_id,
            version=str(data.get("version") or "0.0.0").strip(),
            description=str(data.get("description") or "").strip(),
            author=str(data.get("author") or "").strip(),
            type=ext_type,
            entry=entry,
            root=extension_dir.resolve(),
            icon=str(data.get("icon") or DEFAULT_ICON).strip() or DEFAULT_ICON,
            requires_project=bool(data.get("requiresProject", True)),
            manifest_path=path,
        ),
        "",
    )


class ExtensionService:
    """Quét ``engine_root/extensions`` và cung cấp manifest đã kiểm tra."""

    INSTALLED_FILE_NAME = "extensions_installed.json"

    def __init__(self, engine_root: Path) -> None:
        self.engine_root = Path(engine_root).resolve()
        self.extensions_dir = self.engine_root / EXTENSIONS_DIR_NAME
        self.last_errors: list[str] = []
        self._cache: list[ExtensionManifest] | None = None

    def discover(self, *, refresh: bool = False) -> list[ExtensionManifest]:
        if self._cache is not None and not refresh:
            return list(self._cache)
        found: list[ExtensionManifest] = []
        errors: list[str] = []
        if self.extensions_dir.is_dir():
            for child in sorted(self.extensions_dir.iterdir(), key=lambda p: p.name.lower()):
                if not child.is_dir() or child.name.startswith((".", "_")):
                    continue
                manifest, error = load_manifest(child)
                if manifest is not None:
                    found.append(manifest)
                else:
                    errors.append(error)
        self._cache = found
        self.last_errors = errors
        return list(found)

    def manifest(self, extension_id: str) -> ExtensionManifest | None:
        wanted = str(extension_id or "").strip().lower()
        for item in self.discover():
            if item.id.lower() == wanted:
                return item
        return None

    def agent_briefing(self) -> str:
        """Mô tả ngắn mọi extension đã cài — CodebaseContextService nhét thẳng
        vào ``<installed_extensions>`` của system prompt."""
        installed = self.discover()
        if not installed:
            return ""
        sections = [item.agent_summary() for item in installed]
        return "<installed_extensions>\n" + "\n".join(sections) + "\n</installed_extensions>"

    # ------------------------------------------------------ trạng thái "cài"
    # Marketplace kiểu VS Code: khám phá ≠ cài. Chỉ extension đã cài mới có
    # icon trên activity bar; danh sách id lưu trong appdata để còn giữa phiên.

    def installed_file(self) -> Path:
        from app.core.paths import config_dir

        return config_dir() / self.INSTALLED_FILE_NAME

    def installed_ids(self) -> set[str]:
        try:
            raw = json.loads(self.installed_file().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return set()
        if not isinstance(raw, list):
            return set()
        known = {item.id.lower() for item in self.discover()}
        return {str(x).lower() for x in raw if str(x).lower() in known}

    def is_installed(self, extension_id: str) -> bool:
        return str(extension_id or "").strip().lower() in self.installed_ids()

    def set_installed(self, extension_id: str, installed: bool) -> bool:
        manifest = self.manifest(extension_id)
        if manifest is None:
            return False
        ids = self.installed_ids()
        key = manifest.id.lower()
        if installed:
            ids.add(key)
        else:
            ids.discard(key)
        path = self.installed_file()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(sorted(ids), ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
        except OSError:
            return False
        return True
