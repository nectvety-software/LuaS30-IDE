"""
design_store.py — Lớp lưu trữ của UI Designer theo chuẩn LuaS30 Studio.

Bản lua-engine lưu MỖI màn hình thành hai tệp trong `src/ui/`:
`<tên>.ui.dtfe` (JSON bố cục) + `<tên>.lua` (logic). Studio LuaS30 đã có quy ước
riêng, đã dùng từ bản UI Designer đầu tiên (xem `CHANGELOG_1_7_0`): một tệp
`.luas30/ui_design.json` cho cả project và một tệp `ui_design.lua` sinh ra để
game nạp. Package này giữ đúng quy ước đó, chỉ mở rộng dữ liệu widget cho đủ
tính năng của bản đầy đủ.

    <project>/.luas30/ui_design.json   nguồn sự thật — mọi màn hình
    <project>/ui_design.lua            SINH RA khi xuất, game require() tệp này

`.luas30/` là thư mục metadata sẵn có của project (xem
`app/core/project_session.py` — nơi ghi `mre_sdk.json`), nên UI Designer không
tạo thêm thư mục lạ nào ở gốc project.

Định dạng `ui_design.json` (version 2):

    {
      "format": "LuaS30 UI Design",
      "version": 2,
      "canvas": {"width": 240, "height": 320},
      "current": "main",
      "screens": [
        {"id": "main", "name": "Main", "items": [
            {"type": "button", "name": "btn_1", "x": 60, "y": 200,
             "w": 78, "h": 24, "text": "Bắt đầu", "fill": "#007acc"}
        ]}
      ]
    }

Trường tuỳ chọn của một item (chỉ ghi khi khác mặc định):
    src     — đường dẫn ảnh, tương đối project ("assets/ui/btn.png")
    fill    — màu tô riêng, "#rrggbb"
    rot     — góc xoay quanh tâm, độ
    hidden  — lớp đang bị ẩn ở bảng LAYERS, không vẽ trong game
    lock    — lớp bị khoá trên canvas (không kéo/resize được)

Tương thích ngược: `version: 1` (bản đầu tiên) là một danh sách item phẳng ở
khoá `items` — khi đọc sẽ được nâng thành màn hình `main`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

MAIN_SCREEN_ID = "main"
MAIN_SCREEN_NAME = "Main"

UI_DIR = ".luas30"
DESIGN_FILENAME = "ui_design.json"
EXPORT_FILENAME = "ui_design.lua"

FORMAT_NAME = "LuaS30 UI Design"
FORMAT_VERSION = 2

# khớp `project.json` mặc định (templates/basic) — màn hình QVGA của Nokia S30+
CANVAS_W = 240
CANVAS_H = 320


# ---------------------------------------------------------------- đường dẫn

def ui_dir(project_root) -> Path:
    return Path(project_root) / UI_DIR


def design_path(project_root) -> Path:
    return ui_dir(project_root) / DESIGN_FILENAME


def export_path(project_root) -> Path:
    return Path(project_root) / EXPORT_FILENAME


def relative_to_project(project_root, path) -> str:
    """Đường dẫn hiển thị gọn cho breadcrumb / log."""
    try:
        return str(Path(path).relative_to(Path(project_root)))
    except (ValueError, TypeError):
        return str(path)


# ---------------------------------------------------------------- định dạng tệp

def blank_screen(screen_id: str = MAIN_SCREEN_ID,
                 name: str | None = None) -> dict:
    return {"id": screen_id, "name": name or _title(screen_id), "items": []}


def blank_design(current: str = MAIN_SCREEN_ID) -> dict:
    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "canvas": {"width": CANVAS_W, "height": CANVAS_H},
        "current": current,
        "screens": [blank_screen(MAIN_SCREEN_ID)],
    }


def _title(screen_id: str) -> str:
    """`main_menu` -> `Main Menu` (nhãn hiển thị mặc định cho màn hình mới)."""
    text = str(screen_id or MAIN_SCREEN_ID).replace("_", " ").strip()
    return text.title() if text else MAIN_SCREEN_NAME


def _coerce_item(raw: dict) -> dict | None:
    """Chuẩn hoá một item đọc từ đĩa — bỏ qua bản ghi hỏng thay vì làm sập view."""
    if not isinstance(raw, dict) or "type" not in raw:
        return None
    item = {
        "type": str(raw.get("type") or "panel"),
        "x": _num(raw.get("x"), 0),
        "y": _num(raw.get("y"), 0),
        "w": _num(raw.get("w"), 40),
        "h": _num(raw.get("h"), 20),
        "text": str(raw.get("text") or ""),
    }
    # Không đặt `name` khi tệp không có: để DesignerItem tự sinh ID theo LOẠI
    # (`button_1`, `label_1`…) thay vì gán bừa một cái tên chung chung. Điều này
    # quan trọng với tệp v1 và với JSON sửa tay thiếu `name`.
    name = str(raw.get("name") or "").strip()
    if name:
        item["name"] = name
    src = raw.get("src")
    if src:
        item["src"] = str(src)
    fill = raw.get("fill")
    if fill:
        item["fill"] = str(fill)
    rot = _num(raw.get("rot"), 0.0)
    if rot:
        item["rot"] = rot
    if raw.get("hidden"):
        item["hidden"] = True
    if raw.get("lock"):
        item["lock"] = True
    return item


def _num(value, default):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return int(number) if float(number).is_integer() else round(number, 1)


def coerce_item(raw: dict) -> dict | None:
    """Bản công khai của `_coerce_item` cho lớp ngoài (AI tools, CLI).

    Dùng hàm này thay vì tự dựng lại dict item ở nơi khác: hình dạng item chỉ
    được định nghĩa MỘT chỗ, nếu không tệp ghi ra sẽ lệch dần so với thứ
    Designer đọc được.
    """
    return _coerce_item(raw)


def migrate(payload: dict) -> dict:
    """Nâng payload bất kỳ (v1 phẳng / v2 / lạ) về đúng dạng v2."""
    if not isinstance(payload, dict):
        return blank_design()

    canvas = payload.get("canvas")
    if isinstance(canvas, dict):
        width = int(_num(canvas.get("width"), CANVAS_W))
        height = int(_num(canvas.get("height"), CANVAS_H))
    elif isinstance(canvas, (list, tuple)) and len(canvas) == 2:
        width = int(_num(canvas[0], CANVAS_W))
        height = int(_num(canvas[1], CANVAS_H))
    else:
        width, height = CANVAS_W, CANVAS_H

    screens: list[dict] = []
    raw_screens = payload.get("screens")
    if isinstance(raw_screens, list):
        for entry in raw_screens:
            if not isinstance(entry, dict):
                continue
            screen_id = str(entry.get("id") or "").strip()
            if not screen_id:
                continue
            items = [_coerce_item(it) for it in (entry.get("items") or [])]
            screens.append({
                "id": screen_id,
                "name": str(entry.get("name") or _title(screen_id)),
                "items": [it for it in items if it is not None],
            })

    if not screens:
        # v1: danh sách item phẳng ở khoá "items"
        items = [_coerce_item(it) for it in (payload.get("items") or [])]
        main = blank_screen(MAIN_SCREEN_ID)
        main["items"] = [it for it in items if it is not None]
        screens = [main]

    ids = {s["id"] for s in screens}
    if MAIN_SCREEN_ID not in ids:
        screens.insert(0, blank_screen(MAIN_SCREEN_ID))
    else:
        screens.sort(key=lambda s: (0 if s["id"] == MAIN_SCREEN_ID else 1, s["id"]))

    current = str(payload.get("current") or "")
    if current not in {s["id"] for s in screens}:
        current = MAIN_SCREEN_ID

    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "canvas": {"width": width, "height": height},
        "current": current,
        "screens": screens,
    }


# ---------------------------------------------------------------- store

class DesignStore:
    """Bộ nhớ đệm của `ui_design.json` + các thao tác màn hình.

    Widget UI Designer giữ canvas là nguồn sự thật khi đang vẽ; store này chỉ
    quản lý DANH SÁCH màn hình và tệp trên đĩa. Vòng đời một lần ghi:

        store.begin()                     # đọc tệp (nếu có)
        store.set_screen_items(sid, items)  # cập nhật màn hình đang vẽ
        store.save()                      # ghi .luas30/ui_design.json
    """

    def __init__(self, project_root=None):
        self.root: Path | None = None
        self.payload: dict = blank_design()
        self.loaded = False
        self.migrated = False
        self.error: str = ""
        self.set_project(project_root)

    # ------------------------------------------------ nạp / ghi
    def set_project(self, project_root) -> None:
        self.root = Path(project_root).resolve() if project_root else None
        self.payload = blank_design()
        self.loaded = False
        self.migrated = False
        self.error = ""
        if self.root is not None:
            self.load()

    def load(self) -> bool:
        """Đọc `ui_design.json`. Tệp chưa có KHÔNG phải lỗi — chỉ là project mới."""
        self.loaded = False
        self.migrated = False
        self.error = ""
        path = design_path(self.root) if self.root is not None else None
        if path is None or not path.is_file():
            return False
        try:
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            self.error = f"Không đọc được {DESIGN_FILENAME}: {exc}"
            return False
        version = raw.get("version") if isinstance(raw, dict) else None
        self.payload = migrate(raw)
        self.migrated = version != FORMAT_VERSION
        self.loaded = True
        return True

    def save(self) -> bool:
        """Ghi `ui_design.json`. Trả False + đặt `self.error` khi không ghi được."""
        if self.root is None:
            self.error = "Chưa mở project."
            return False
        path = design_path(self.root)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(self.payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            self.error = f"Không ghi được {DESIGN_FILENAME}: {exc}"
            return False
        self.loaded = True
        self.migrated = False
        self.error = ""
        return True

    def ensure_main(self) -> Path | None:
        """Bảo đảm project có màn hình `main`; tạo tệp nếu chưa có.

        Không ghi đè tệp đang có — chỉ ghi khi `ui_design.json` chưa tồn tại.
        Trả về đường dẫn tệp thiết kế.
        """
        if self.root is None:
            return None
        path = design_path(self.root)
        if path.is_file():
            if not self.loaded:
                self.load()
            return path
        self.payload = blank_design()
        self.save()
        return path

    # ------------------------------------------------ truy vấn
    def screens(self) -> list[dict]:
        return self.payload.get("screens") or []

    def screen_ids(self) -> list[str]:
        return [str(s.get("id", "")) for s in self.screens()]

    def screen(self, screen_id: str) -> dict | None:
        for entry in self.screens():
            if str(entry.get("id")) == str(screen_id):
                return entry
        return None

    def has_screen(self, screen_id: str) -> bool:
        return self.screen(screen_id) is not None

    def screen_name(self, screen_id: str) -> str:
        entry = self.screen(screen_id)
        return str(entry.get("name")) if entry else _title(screen_id)

    def screen_items(self, screen_id: str) -> list[dict]:
        entry = self.screen(screen_id)
        return list(entry.get("items") or []) if entry else []

    def current_id(self) -> str:
        current = str(self.payload.get("current") or "")
        if self.has_screen(current):
            return current
        return MAIN_SCREEN_ID

    def set_current(self, screen_id: str) -> None:
        if self.has_screen(screen_id):
            self.payload["current"] = str(screen_id)

    def canvas_size(self) -> tuple[int, int]:
        canvas = self.payload.get("canvas") or {}
        return (int(_num(canvas.get("width"), CANVAS_W)),
                int(_num(canvas.get("height"), CANVAS_H)))

    # ------------------------------------------------ cập nhật
    def set_screen_items(self, screen_id: str, items: Iterable[dict]) -> None:
        entry = self.screen(screen_id)
        if entry is None:
            entry = blank_screen(screen_id)
            self.screens().append(entry)
            self._sort_screens()
        entry["items"] = [it for it in (_coerce_item(i) for i in items)
                          if it is not None]

    def add_screen(self, screen_id: str, name: str = "") -> bool:
        if not screen_id or self.has_screen(screen_id):
            return False
        self.screens().append(blank_screen(screen_id, name or None))
        self._sort_screens()
        return True

    def rename_screen(self, old_id: str, new_id: str) -> bool:
        if old_id == MAIN_SCREEN_ID or not new_id:
            return False
        entry = self.screen(old_id)
        if entry is None or self.has_screen(new_id):
            return False
        entry["id"] = new_id
        entry["name"] = _title(new_id)
        if self.payload.get("current") == old_id:
            self.payload["current"] = new_id
        self._sort_screens()
        return True

    def duplicate_screen(self, src_id: str, new_id: str) -> bool:
        source = self.screen(src_id)
        if source is None or not new_id or self.has_screen(new_id):
            return False
        clone = {
            "id": new_id,
            "name": _title(new_id),
            "items": [dict(it) for it in (source.get("items") or [])],
        }
        self.screens().append(clone)
        self._sort_screens()
        return True

    def delete_screen(self, screen_id: str) -> bool:
        if screen_id == MAIN_SCREEN_ID:
            return False
        entry = self.screen(screen_id)
        if entry is None:
            return False
        self.screens().remove(entry)
        if self.payload.get("current") == screen_id:
            self.payload["current"] = MAIN_SCREEN_ID
        return True

    def unique_id(self, base: str) -> str:
        """`menu` -> `menu`, `menu_2`, `menu_3`… sao cho không đụng màn hình có sẵn."""
        candidate = base or "screen"
        if not self.has_screen(candidate):
            return candidate
        index = 2
        while self.has_screen(f"{candidate}_{index}"):
            index += 1
        return f"{candidate}_{index}"

    def _sort_screens(self) -> None:
        self.screens().sort(
            key=lambda s: (0 if s.get("id") == MAIN_SCREEN_ID else 1,
                           str(s.get("id", ""))))


# ---------------------------------------------------------------- scene <-> dict

def scene_to_items(scene) -> list[dict]:
    """Canvas -> danh sách item. Thứ tự = thứ tự vẽ (dưới trước)."""
    items = []
    for item in sorted(scene.widget_items(), key=lambda it: it.zValue()):
        data = item.to_dict()
        if not item.isVisible():
            data["hidden"] = True
        items.append(data)
    return items


def items_to_scene(items: Iterable[dict], scene, base_dir=None) -> None:
    """Nạp danh sách item vào canvas (chế độ bulk — không đánh dấu bẩn).

    `base_dir` (gốc project) cho phép thành phần Hình ảnh tự nạp bitmap từ đĩa
    khi `src` chưa có trong registry — xem `DesignerItem.from_dict`.
    """
    from .items import DesignerItem

    scene.begin_bulk()
    try:
        scene.clear_widgets()
        created = []
        for entry in items:
            data = _coerce_item(entry)
            if data is None:
                continue
            item = DesignerItem.from_dict(data, base_dir=base_dir)
            scene.addItem(item)
            if data.get("hidden"):
                item.setVisible(False)
            created.append(item)
        scene._assign_z(list(reversed(created)))
        normalize_ids(scene)
        scene.layersChanged.emit()
    finally:
        scene.end_bulk()


def normalize_ids(scene) -> int:
    """Bảo đảm mọi thành phần có ID hợp lệ và không trùng (tệp cũ / sửa tay).

    Trả về số ID đã bị đổi. Duyệt theo thứ tự vẽ (dưới trước) để thành phần
    nằm dưới giữ nguyên ID gốc khi có xung đột.
    """
    from .items import sanitize_id, unique_id

    taken: set[str] = set()
    changed = 0
    for item in sorted(scene.widget_items(), key=lambda it: it.zValue()):
        wanted = unique_id(sanitize_id(item.name, item.widget_type), taken)
        if wanted != item.name:
            item.set_name(wanted)
            changed += 1
        taken.add(item.name)
    return changed
