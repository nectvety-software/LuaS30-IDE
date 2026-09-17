"""
ai_design_tool_service.py — công cụ UI Design + Assets cho AI Agent.

Cho phép ChatAI *tạo* thiết kế giao diện và tài nguyên cho game/app thay vì chỉ
đọc mã nguồn. Hai công cụ, gọi qua khối ```luas30-tool:

    {"tool":"ui_design","args":{"op":"add_item","screen":"main",
      "type":"button","name":"btn_start","x":60,"y":240,"text":"Bat dau"}}

    {"tool":"asset","args":{"op":"make","kind":"button","name":"btn_primary",
      "width":78,"height":24,"text":"OK"}}

(Màu của tài nguyên sinh ra lấy mặc định từ `lua_export` — tức bảng màu NỘI DUNG
game. Muốn khác thì truyền `color` / `color2`; viền mặc định suy ra từ màu tô.)

Nguyên tắc:

- **Không định nghĩa lại schema.** Mọi thứ đi qua đúng lớp mà UI Designer dùng:
  `design_store` (nguồn sự thật `.luas30/ui_design.json`), `lua_export` (sinh
  `ui_design.lua`) và `items.COMPONENTS` (danh mục thành phần + kích thước mặc
  định). Thêm thành phần mới vào Designer là công cụ này tự biết.
- **Đọc luôn được, ghi phải được phép.** `execute(..., allow_write=False)` từ
  chối mọi thao tác ghi. ChatAI truyền cờ này theo access mode, giống code edit.
- **Toạ độ đi qua đúng luật của Designer**: `snap()` về lưới 4px và
  `clamp_to_screen()` giữ trong khung 240×320, nên thiết kế do AI tạo không bao
  giờ nằm ngoài màn hình.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)

from app.services.ai_agent_protocol import DESIGN_TOOL_NAMES, TOOL_NAMES
from app.views.ui_designer import design_store, lua_export
from app.views.ui_designer.asset_import import IMAGE_TARGETS, TARGET_DIRS
from app.views.ui_designer.items import (
    COMPONENTS,
    GROUPS,
    SCREEN_H,
    SCREEN_W,
    TEXT_TYPES,
    clamp_to_screen,
    default_rect,
    default_text,
    is_valid_id,
    sanitize_id,
    snap,
    unique_id,
)

# Thao tác chỉ đọc — chạy được ở mọi access mode, giống read/grep/glob.
UI_DESIGN_READ_OPS = ("catalog", "screens", "get")
UI_DESIGN_WRITE_OPS = (
    "add_screen", "delete_screen", "rename_screen", "set_screen",
    "add_item", "update_item", "remove_item", "export",
)
ASSET_READ_OPS = ("list",)
ASSET_WRITE_OPS = ("make",)

# Bảng màu NỘI DUNG mặc định — lấy thẳng từ `lua_export` (nguồn màu game thật),
# KHÔNG phải accent chrome của IDE. Tài nguyên sinh ra là nội dung game.
DEFAULT_CONTENT_COLOR = lua_export.ACCENT
DEFAULT_CONTENT_TEXT = lua_export.TEXT
DEFAULT_CONTENT_TRACK = lua_export.DEFAULT_FILL["progress"]

# kind -> (thư mục đích mặc định, rộng, cao)
ASSET_KINDS: dict[str, tuple[str, int, int]] = {
    "solid": ("ui", 32, 32),
    "gradient": ("background", SCREEN_W, SCREEN_H),
    "checker": ("tiles", 64, 64),
    "grid": ("tiles", 64, 64),
    "button": ("ui", 78, 24),
    "panel": ("ui", 140, 90),
    "frame": ("ui", 120, 80),
    "bar": ("ui", 110, 12),
    "label": ("ui", 96, 20),
}

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_SAFE_NAME_RE = re.compile(r"[^a-z0-9_-]+")


def _int(value, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _color(value, fallback: str) -> QColor:
    text = str(value or "").strip()
    if text and _HEX_RE.match(text):
        color = QColor(text)
        if color.isValid():
            return color
    return QColor(fallback)


def _color_or(value, fallback: QColor) -> QColor:
    """Như `_color` nhưng fallback là một QColor dẫn xuất (vd màu đậm hơn)."""
    text = str(value or "").strip()
    if text and _HEX_RE.match(text):
        color = QColor(text)
        if color.isValid():
            return color
    return QColor(fallback)


def safe_asset_name(value: str, fallback: str = "asset") -> str:
    """Tên tệp an toàn: chỉ `[a-z0-9_-]`, không dấu, tối đa 64 ký tự."""
    text = str(value or "").strip().lower()
    text = text[:-4] if text.endswith(".png") else text
    text = _SAFE_NAME_RE.sub("_", text).strip("_")
    text = re.sub(r"_{2,}", "_", text)[:64].strip("_")
    return text or fallback


class AIDesignToolService:
    """Công cụ UI Design + Assets, giới hạn trong thư mục project."""

    def __init__(self, max_output: int = 18000) -> None:
        self.max_output = max(1000, int(max_output))

    # ------------------------------------------------------------ tiện ích
    @staticmethod
    def _root(project_root: Path | None) -> Path:
        if not project_root:
            raise ValueError("Open a project before using design tools.")
        root = Path(project_root).expanduser().resolve()
        if not root.is_dir():
            raise ValueError("The active project directory is unavailable.")
        return root

    def _limit(self, text: str) -> str:
        value = str(text or "")
        if len(value) <= self.max_output:
            return value
        half = self.max_output // 2
        return value[:half] + "\n...[tool output truncated]...\n" + value[-half:]

    @staticmethod
    def _load(root: Path) -> design_store.DesignStore:
        store = design_store.DesignStore(root)
        if not store.loaded and not store.load():
            # Project chưa có ui_design.json — không phải lỗi, bắt đầu từ trống.
            store.payload = design_store.blank_design()
        return store

    @staticmethod
    def _screen_items(store: design_store.DesignStore, screen_id: str) -> list[dict]:
        if not store.has_screen(screen_id):
            raise ValueError(
                f"Screen '{screen_id}' does not exist. Screens: "
                + ", ".join(store.screen_ids() or ["(none)"])
            )
        return store.screen_items(screen_id)

    @staticmethod
    def _find_item(items: list[dict], name: str) -> dict:
        for item in items:
            if str(item.get("name") or "") == name:
                return item
        raise ValueError(f"No component named '{name}' on this screen.")

    # ------------------------------------------------------------ điều phối
    def execute(self, project_root: Path | None, action, *, allow_write: bool = False) -> str:
        root = self._root(project_root)
        tool = str(getattr(action, "tool", "") or "").lower()
        args = dict(getattr(action, "args", None) or {})
        op = str(args.get("op") or "").strip().lower()

        if tool == "ui_design":
            if op in UI_DESIGN_WRITE_OPS and not allow_write:
                raise ValueError(
                    "Design changes are not permitted in the current access mode. "
                    "Ask the user to switch to an editing mode."
                )
            return self._ui_design(root, op, args)
        if tool == "asset":
            if op in ASSET_WRITE_OPS and not allow_write:
                raise ValueError(
                    "Asset generation is not permitted in the current access mode. "
                    "Ask the user to switch to an editing mode."
                )
            return self._asset(root, op, args)
        raise ValueError(f"Unsupported design tool: {getattr(action, 'tool', '')}")

    # ------------------------------------------------------------ ui_design
    def _ui_design(self, root: Path, op: str, args: dict) -> str:
        if op == "catalog":
            return self._op_catalog(root)
        if op == "screens":
            return self._op_screens(root)
        if op == "get":
            return self._op_get(root, args)
        if op == "add_screen":
            return self._op_add_screen(root, args)
        if op == "delete_screen":
            return self._op_delete_screen(root, args)
        if op == "rename_screen":
            return self._op_rename_screen(root, args)
        if op == "set_screen":
            return self._op_set_screen(root, args)
        if op == "add_item":
            return self._op_add_item(root, args)
        if op == "update_item":
            return self._op_update_item(root, args)
        if op == "remove_item":
            return self._op_remove_item(root, args)
        if op == "export":
            return self._op_export(root)
        raise ValueError(
            f"Unsupported ui_design op '{op}'. Read: {', '.join(UI_DESIGN_READ_OPS)}. "
            f"Write: {', '.join(UI_DESIGN_WRITE_OPS)}."
        )

    def _op_catalog(self, root: Path) -> str:
        lines = [
            f"UI CATALOG canvas={SCREEN_W}x{SCREEN_H} grid=4 "
            f"screens={len(self._load(root).screens())}",
        ]
        for group_key, group_label in GROUPS:
            members = [
                f"{key} {info['w']}x{info['h']}"
                + (f" text={info['text']!r}" if info.get("text") else "")
                for key, info in COMPONENTS.items()
                if info.get("group") == group_key
            ]
            lines.append(f"  {group_label} ({group_key}): " + ", ".join(members))
        lines.append(
            "  ops: read=" + ",".join(UI_DESIGN_READ_OPS)
            + " write=" + ",".join(UI_DESIGN_WRITE_OPS)
        )
        lines.append(
            "  item fields: type, name, x, y, w, h, text, src, fill, rot, hidden"
        )
        return self._limit("\n".join(lines))

    def _op_screens(self, root: Path) -> str:
        store = self._load(root)
        rows = [
            {
                "id": str(screen.get("id")),
                "name": str(screen.get("name") or ""),
                "items": len(screen.get("items") or []),
            }
            for screen in store.screens()
        ]
        width, height = store.canvas_size()
        head = f"UI SCREENS canvas={width}x{height} current={store.current_id()}"
        return self._limit(head + "\n" + json.dumps(rows, ensure_ascii=False))

    def _op_get(self, root: Path, args: dict) -> str:
        store = self._load(root)
        screen_id = str(args.get("screen") or store.current_id())
        items = self._screen_items(store, screen_id)
        head = f"UI SCREEN {screen_id} items={len(items)}"
        return self._limit(head + "\n" + json.dumps(items, ensure_ascii=False))

    def _op_add_screen(self, root: Path, args: dict) -> str:
        store = self._load(root)
        raw_id = str(args.get("id") or args.get("screen") or "").strip()
        if not raw_id:
            raise ValueError("add_screen needs an 'id'.")
        screen_id = sanitize_id(raw_id, "screen")
        if store.has_screen(screen_id):
            return f"UI add_screen {screen_id} already exists (no change)."
        store.add_screen(screen_id, str(args.get("name") or ""))
        self._require_save(store)
        return f"UI add_screen {screen_id} ok screens={store.screen_ids()}"

    def _op_delete_screen(self, root: Path, args: dict) -> str:
        store = self._load(root)
        screen_id = str(args.get("screen") or args.get("id") or "")
        if screen_id == design_store.MAIN_SCREEN_ID:
            raise ValueError("The 'main' screen is the startup screen and cannot be deleted.")
        if not store.delete_screen(screen_id):
            raise ValueError(f"Screen '{screen_id}' does not exist.")
        self._require_save(store)
        return f"UI delete_screen {screen_id} ok screens={store.screen_ids()}"

    def _op_rename_screen(self, root: Path, args: dict) -> str:
        store = self._load(root)
        old = str(args.get("screen") or "")
        new = sanitize_id(str(args.get("to") or args.get("id") or ""), "screen")
        if not store.rename_screen(old, new):
            raise ValueError(
                f"Cannot rename '{old}' to '{new}' (missing screen, name taken, "
                "or it is the protected 'main' screen)."
            )
        self._require_save(store)
        return f"UI rename_screen {old} -> {new} ok"

    def _op_set_screen(self, root: Path, args: dict) -> str:
        store = self._load(root)
        screen_id = str(args.get("screen") or store.current_id())
        raw_items = args.get("items")
        if not isinstance(raw_items, list):
            raise ValueError("set_screen needs 'items' as a JSON array.")
        prepared = [self._prepare_item(store, screen_id, raw, index)
                    for index, raw in enumerate(raw_items)]
        store.set_screen_items(screen_id, prepared)
        self._require_save(store)
        return (f"UI set_screen {screen_id} items={len(prepared)} ok "
                f"names={[it.get('name') for it in prepared]}")

    def _op_add_item(self, root: Path, args: dict) -> str:
        store = self._load(root)
        screen_id = str(args.get("screen") or store.current_id())
        items = self._screen_items(store, screen_id)
        item = self._prepare_item(store, screen_id, args, len(items), existing=items)
        store.set_screen_items(screen_id, items + [item])
        self._require_save(store)
        return (f"UI add_item {screen_id} {item['type']} '{item.get('name')}' "
                f"x={item['x']} y={item['y']} w={item['w']} h={item['h']} "
                f"total={len(items) + 1}")

    def _op_update_item(self, root: Path, args: dict) -> str:
        store = self._load(root)
        screen_id = str(args.get("screen") or store.current_id())
        items = self._screen_items(store, screen_id)
        name = str(args.get("name") or "")
        target = self._find_item(items, name)
        fields = args.get("fields")
        if not isinstance(fields, dict) or not fields:
            raise ValueError("update_item needs 'fields' as a JSON object.")
        merged = dict(target)
        merged.update(fields)
        if "name" in fields:
            candidate = str(fields.get("name") or "").strip()
            if candidate and candidate != name and any(
                str(it.get("name") or "") == candidate for it in items
            ):
                raise ValueError(f"Another component is already named '{candidate}'.")
        prepared = self._prepare_item(
            store, screen_id, merged, items.index(target), existing=items, ignore=name
        )
        items[items.index(target)] = prepared
        store.set_screen_items(screen_id, items)
        self._require_save(store)
        return (f"UI update_item {screen_id} '{prepared.get('name')}' "
                f"x={prepared['x']} y={prepared['y']} w={prepared['w']} h={prepared['h']}")

    def _op_remove_item(self, root: Path, args: dict) -> str:
        store = self._load(root)
        screen_id = str(args.get("screen") or store.current_id())
        items = self._screen_items(store, screen_id)
        name = str(args.get("name") or "")
        target = self._find_item(items, name)
        items.remove(target)
        store.set_screen_items(screen_id, items)
        self._require_save(store)
        return f"UI remove_item {screen_id} '{name}' remaining={len(items)}"

    def _op_export(self, root: Path) -> str:
        store = self._load(root)
        path = lua_export.export_lua(store)
        if path is None:
            raise ValueError("Export failed: no project root.")
        size = Path(path).stat().st_size
        return (f"UI export ok {design_store.relative_to_project(root, path)} "
                f"bytes={size} screens={len(store.screens())}")

    # ------------------------------------------------------------ asset
    def _asset(self, root: Path, op: str, args: dict) -> str:
        if op == "list":
            return self._op_asset_list(root)
        if op == "make":
            return self._op_asset_make(root, args)
        raise ValueError(
            f"Unsupported asset op '{op}'. Read: {', '.join(ASSET_READ_OPS)}. "
            f"Write: {', '.join(ASSET_WRITE_OPS)}."
        )

    def _op_asset_list(self, root: Path) -> str:
        rows: list[dict] = []
        for _key, _label, rel in IMAGE_TARGETS:
            folder = root / rel
            if not folder.is_dir():
                continue
            for path in sorted(folder.iterdir()):
                if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}:
                    rows.append({
                        "src": path.relative_to(root).as_posix(),
                        "bytes": path.stat().st_size,
                    })
        targets = ", ".join(f"{key}={rel}" for key, _label, rel in IMAGE_TARGETS)
        head = f"ASSETS count={len(rows)}\n  targets: {targets}\n  kinds: " \
               + ", ".join(ASSET_KINDS)
        return self._limit(head + "\n" + json.dumps(rows, ensure_ascii=False))

    def _op_asset_make(self, root: Path, args: dict) -> str:
        kind = str(args.get("kind") or "").strip().lower()
        if kind not in ASSET_KINDS:
            raise ValueError(
                f"Unknown asset kind '{kind}'. Supported: {', '.join(ASSET_KINDS)}."
            )
        default_target, default_w, default_h = ASSET_KINDS[kind]
        target = str(args.get("target") or default_target).strip().lower()
        if target not in TARGET_DIRS:
            raise ValueError(
                f"Unknown target '{target}'. Supported: {', '.join(TARGET_DIRS)}."
            )
        width = max(1, min(1024, _int(args.get("width"), default_w)))
        height = max(1, min(1024, _int(args.get("height"), default_h)))
        name = safe_asset_name(str(args.get("name") or ""), f"{kind}_{width}x{height}")

        dest_dir = root / TARGET_DIRS[target]
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / f"{name}.png"

        image = self._render_asset(kind, width, height, args)
        if not image.save(str(path), "PNG"):
            raise ValueError(f"Could not write {path.name}.")
        rel = path.relative_to(root).as_posix()
        return (f"ASSET make {rel} {width}x{height} kind={kind} "
                f"bytes={path.stat().st_size}")

    def _render_asset(self, kind: str, width: int, height: int, args: dict) -> QImage:
        color = _color(args.get("color"), DEFAULT_CONTENT_COLOR)
        # Viền mặc định suy ra từ chính màu tô (đậm hơn) — asset luôn cùng họ màu,
        # và không phải bịa thêm một hằng màu nữa.
        color2 = _color_or(args.get("color2"), color.darker(150))
        alpha = max(0, min(255, _int(args.get("alpha"), 255 if kind != "label" else 0)))
        radius = max(0, min(min(width, height) // 2, _int(args.get("radius"), 6)))
        cell = max(2, min(min(width, height), _int(args.get("cell"), 8)))

        image = QImage(width, height, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)

            if kind == "solid":
                painter.fillRect(0, 0, width, height, _with_alpha(color, alpha))
            elif kind == "gradient":
                gradient = QLinearGradient(0.0, 0.0, 0.0, float(height))
                gradient.setColorAt(0.0, _with_alpha(color, alpha))
                gradient.setColorAt(1.0, _with_alpha(color2, alpha))
                painter.fillRect(0, 0, width, height, gradient)
            elif kind == "checker":
                for y in range(0, height, cell):
                    for x in range(0, width, cell):
                        even = ((x // cell) + (y // cell)) % 2 == 0
                        painter.fillRect(x, y, cell, cell,
                                         _with_alpha(color if even else color2, alpha))
            elif kind == "grid":
                pen = QPen(_with_alpha(color, alpha if alpha else 255))
                pen.setWidth(1)
                painter.setPen(pen)
                for x in range(0, width + 1, cell):
                    painter.drawLine(x, 0, x, height)
                for y in range(0, height + 1, cell):
                    painter.drawLine(0, y, width, y)
            elif kind == "bar":
                fraction = max(0.0, min(1.0, _float(args.get("value"), 0.6)))
                track = _color(args.get("track"), DEFAULT_CONTENT_TRACK)
                self._rounded(painter, 0, 0, width, height, radius,
                              _with_alpha(track, alpha))
                fill_w = int(round(width * fraction))
                if fill_w > 0:
                    self._rounded(painter, 0, 0, max(fill_w, radius * 2), height, radius,
                                  _with_alpha(color, alpha))
            elif kind == "frame":
                # khung RỖNG: chỉ viền, không tô — nếu tô thì giống hệt "panel"
                self._rounded(painter, 0.5, 0.5, width - 1, height - 1, radius,
                              None, stroke=color2, stroke_width=2)
            elif kind in {"button", "panel"}:
                self._rounded(painter, 0.5, 0.5, width - 1, height - 1, radius,
                              _with_alpha(color, alpha), stroke=color2, stroke_width=1)
                if kind == "button":
                    self._draw_text(painter, args, width, height,
                                    _color(args.get("text_color"), DEFAULT_CONTENT_TEXT))
            elif kind == "label":
                self._draw_text(painter, args, width, height,
                                _color(args.get("text_color"), DEFAULT_CONTENT_TEXT))
        finally:
            painter.end()
        return image

    @staticmethod
    def _rounded(painter: QPainter, x: float, y: float, w: float, h: float,
                 radius: int, fill: QColor | None, *, stroke: QColor | None = None,
                 stroke_width: int = 1) -> None:
        """Vẽ hình chữ nhật bo góc. `fill=None` → chỉ vẽ viền (khung rỗng)."""
        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, max(1.0, w), max(1.0, h)), radius, radius)
        if fill is not None:
            painter.fillPath(path, fill)
        if stroke is not None:
            pen = QPen(stroke)
            pen.setWidth(stroke_width)
            painter.setPen(pen)
            painter.drawPath(path)

    @staticmethod
    def _draw_text(painter: QPainter, args: dict, width: int, height: int,
                   color: QColor) -> None:
        text = str(args.get("text") or "")
        if not text:
            return
        size = max(6, min(64, _int(args.get("font_size"), max(7, height // 2))))
        font = QFont("Segoe UI", size)
        font.setBold(bool(args.get("bold", False)))
        painter.setFont(font)
        painter.setPen(QPen(color))
        painter.drawText(QRectF(0, 0, width, height),
                         int(Qt.AlignCenter) | int(Qt.TextWordWrap), text)

    # ------------------------------------------------------------ chuẩn hoá
    def _prepare_item(self, store: design_store.DesignStore, screen_id: str,
                      raw: dict, index: int, *, existing: list[dict] | None = None,
                      ignore: str = "") -> dict:
        """Dựng item đúng schema, snap lưới, kẹp khung, tên không đụng nhau."""
        if not isinstance(raw, dict):
            raise ValueError("Each item must be a JSON object.")

        widget_type = str(raw.get("type") or "").strip().lower()
        if widget_type not in COMPONENTS:
            raise ValueError(
                f"Unknown component type '{widget_type}'. "
                f"Supported: {', '.join(COMPONENTS)}."
            )

        default_w, default_h = default_rect(widget_type)
        width = max(4.0, _float(raw.get("w"), default_w))
        height = max(4.0, _float(raw.get("h"), default_h))
        x = snap(_float(raw.get("x"), 0.0))
        y = snap(_float(raw.get("y"), 0.0))
        x, y = clamp_to_screen(x, y, width, height)

        name = str(raw.get("name") or "").strip()
        if name and not is_valid_id(name):
            name = sanitize_id(name, widget_type)
        taken = {
            str(item.get("name") or "")
            for item in (existing if existing is not None else [])
            if str(item.get("name") or "") != ignore
        }
        if not name:
            name = self._auto_name(widget_type, taken)
        elif name in taken:
            name = unique_id(name, taken)

        candidate = dict(raw)
        candidate.update({
            "type": widget_type,
            "name": name,
            "x": x,
            "y": y,
            "w": width,
            "h": height,
        })
        if widget_type in TEXT_TYPES and not candidate.get("text"):
            candidate["text"] = default_text(widget_type)

        item = design_store.coerce_item(candidate)
        if item is None:
            raise ValueError(f"Could not build a '{widget_type}' component.")
        item["name"] = name
        return item

    @staticmethod
    def _auto_name(widget_type: str, taken: set[str]) -> str:
        """Tên tự sinh theo đúng quy ước Designer: `button_1`, `label_2`…

        Không dùng `items.next_default_name()` vì hàm đó tiêu số của bộ đếm
        TOÀN CỤC, sẽ làm lệch tên mà Designer sinh ra sau đó.
        """
        index = 1
        while f"{widget_type}_{index}" in taken:
            index += 1
        return f"{widget_type}_{index}"

    @staticmethod
    def _require_save(store: design_store.DesignStore) -> None:
        if not store.save():
            raise ValueError(store.error or "Could not write ui_design.json.")


def _with_alpha(color: QColor, alpha: int) -> QColor:
    out = QColor(color)
    out.setAlpha(max(0, min(255, int(alpha))))
    return out
