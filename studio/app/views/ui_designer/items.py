"""
items.py — Thành phần trên canvas UI Designer.

Mỗi loại thành phần có cách vẽ riêng (button, label, checkbox, textbox, image,
progress, slider, switch, panel, card, row, column, divider, spacer, canvas,
sprite, tile) theo token theme 2Dutiful. Item kéo di chuyển + chọn được, có
thể resize bằng tay nắm ở góc, và luôn bị kẹp trong khung màn hình 240×320
(bắt dính lưới 4px) — kéo ra ngoài màn hình là không thể.

Ngoài catalog tĩnh còn có SPRITE_REGISTRY: sprite do người dùng vẽ ở Sprite
Editor rồi bấm "Áp dụng" sẽ được đăng ký vào đây, hiện thành một nhóm riêng
trong palette và thả ra canvas dưới dạng thành phần Hình ảnh mang bitmap thật.
"""
from __future__ import annotations

import itertools
import re
import unicodedata

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem

from .tokens import ACCENT, BORDER, BORDER_HOVER, TEXT, TEXT_3
from .guides import bounds_at, rotated_size

# số thứ tự tăng dần cho mỗi thành phần — dùng để phá hoà khi so z-value
# (QGraphicsScene.items() không đảm bảo thứ tự giữa các item cùng z)
_ITEM_SEQ = itertools.count(1)

# Bộ đếm RIÊNG cho ID mặc định, tách khỏi `_ITEM_SEQ`. Palette vẽ ảnh xem trước
# bằng cách tạo tạm một DesignerItem cho mỗi loại thành phần — nếu dùng chung
# một bộ đếm thì ID người dùng nhận được sẽ nhảy cách quãng (button_1, label_3,
# progress_5…). Palette lưu/khôi phục bộ đếm này quanh lúc dựng ảnh xem trước.
_NAME_COUNTERS: dict[str, int] = {}


def next_default_name(widget_type: str) -> str:
    """ID mặc định cho thành phần mới: `button_1`, `button_2`, `label_1`…"""
    index = _NAME_COUNTERS.get(widget_type, 0) + 1
    _NAME_COUNTERS[widget_type] = index
    return f"{widget_type}_{index}"


def peek_name_counters() -> dict[str, int]:
    """Ảnh chụp bộ đếm ID — dùng khi cần dựng item tạm mà không tốn số."""
    return dict(_NAME_COUNTERS)


def restore_name_counters(snapshot: dict[str, int]) -> None:
    _NAME_COUNTERS.clear()
    _NAME_COUNTERS.update(snapshot or {})

# ---------------------------------------------------------------- catalog

# mỗi thành phần: nhãn VI, tên EN, kích thước mặc định, text mặc định, nhóm
COMPONENTS: dict[str, dict] = {
    # --- Giao diện ---
    "button":   {"vi": "Nút bấm",        "en": "Button",       "w": 78, "h": 24, "text": "Button",  "group": "ui"},
    "label":    {"vi": "Nhãn văn bản",   "en": "Label",        "w": 84, "h": 18, "text": "Label",   "group": "ui"},
    "checkbox": {"vi": "Hộp kiểm",       "en": "CheckBox",     "w": 92, "h": 20, "text": "Tùy chọn", "group": "ui"},
    "textbox":  {"vi": "Hộp nhập liệu",  "en": "TextBox",      "w": 110, "h": 26, "text": "",       "group": "ui"},
    "image":    {"vi": "Hình ảnh",       "en": "Image",        "w": 56, "h": 56, "text": "",        "group": "ui"},
    "progress": {"vi": "Thanh tiến trình", "en": "ProgressBar", "w": 110, "h": 12, "text": "",       "group": "ui"},
    "slider":   {"vi": "Thanh trượt",    "en": "Slider",       "w": 110, "h": 18, "text": "",       "group": "ui"},
    "switch":   {"vi": "Công tắc",       "en": "Switch",       "w": 46, "h": 22, "text": "",        "group": "ui"},
    # --- Bố cục ---
    "panel":    {"vi": "Khung nền",      "en": "Panel",        "w": 140, "h": 90, "text": "",       "group": "layout"},
    "card":     {"vi": "Thẻ nội dung",   "en": "Card",         "w": 140, "h": 76, "text": "Card",   "group": "layout"},
    "row":      {"vi": "Hàng ngang",     "en": "Row",          "w": 150, "h": 30, "text": "Row",    "group": "layout"},
    "column":   {"vi": "Cột dọc",        "en": "Column",       "w": 90, "h": 110, "text": "Column", "group": "layout"},
    "divider":  {"vi": "Đường phân cách", "en": "Divider",     "w": 150, "h": 6, "text": "",        "group": "layout"},
    "spacer":   {"vi": "Khoảng trống",   "en": "Spacer",       "w": 70, "h": 26, "text": "",        "group": "layout"},
    # --- Đồ họa ---
    "canvas":   {"vi": "Vùng vẽ",        "en": "Canvas",       "w": 170, "h": 120, "text": "",      "group": "draw"},
    "sprite":   {"vi": "Nhân vật",       "en": "Sprite",       "w": 32, "h": 32, "text": "",        "group": "draw"},
    "tile":     {"vi": "Ô gạch",         "en": "Tile",         "w": 16, "h": 16, "text": "",        "group": "draw"},
    "rect":     {"vi": "Hình chữ nhật",  "en": "Rect",         "w": 90, "h": 60, "text": "",        "group": "draw"},
}

GROUPS = [
    ("ui", "GIAO DIỆN"),
    ("layout", "BỐ CỤC"),
    ("draw", "ĐỒ HỌA"),
]

# những thành phần thực sự có nội dung chữ (để Inspector bật/tắt ô "Nội dung")
TEXT_TYPES = {"button", "label", "checkbox", "textbox", "card", "row", "column"}

DEFAULT_SIZE = (80, 24)

# ---------------------------------------------------------------- khung màn hình
SCREEN_W = 240
SCREEN_H = 320
GRID = 4  # lưới bắt dính khi thả / kéo thành phần


def snap(value: float, grid: int = GRID) -> float:
    """Bắt dính toạ độ về lưới `grid` px (mặc định 4px) cho gọn gàng."""
    return float(round(value / grid) * grid)


def clamp_to_screen(x: float, y: float, w: float, h: float) -> tuple[float, float]:
    """Kẹp góc trên-trái để thành phần luôn nằm trong màn hình 240×320."""
    max_x = max(0.0, SCREEN_W - w)
    max_y = max(0.0, SCREEN_H - h)
    return (min(max(float(x), 0.0), max_x), min(max(float(y), 0.0), max_y))


def component_info(widget_type: str) -> dict:
    return COMPONENTS.get(widget_type, {"vi": widget_type, "en": widget_type,
                                        "w": DEFAULT_SIZE[0], "h": DEFAULT_SIZE[1],
                                        "text": "", "group": "ui"})


def default_rect(widget_type: str) -> tuple[float, float]:
    info = component_info(widget_type)
    return float(info.get("w", DEFAULT_SIZE[0])), float(info.get("h", DEFAULT_SIZE[1]))


def default_text(widget_type: str) -> str:
    return str(component_info(widget_type).get("text", ""))


def supports_text(widget_type: str) -> bool:
    """Thành phần này có nội dung chữ để chỉnh trong Inspector không."""
    return widget_type in TEXT_TYPES


# ---------------------------------------------------------------- ID thành phần
# `DesignerItem.name` KHÔNG chỉ là nhãn hiển thị — nó chính là ID của thành phần
# và được ghi vào mã Lua ở khoá `name` của scene, cùng khoá `ui.<id>` của tệp
# logic. Vì vậy nó phải là một ĐỊNH DANH LUA hợp lệ và không được trùng nhau.

ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def is_valid_id(name: str) -> bool:
    """`name` có dùng được làm định danh Lua (và khoá `ui.<name>`) không."""
    return bool(name) and ID_RE.match(str(name)) is not None


def sanitize_id(name: str, fallback: str = "widget") -> str:
    """Biến văn bản bất kỳ thành định danh Lua hợp lệ.

    Bỏ dấu tiếng Việt ("Nút bấm" -> "Nut bam") rồi thay mọi ký tự không hợp lệ
    bằng '_'. Tên đã hợp lệ thì giữ nguyên (không đổi hoa/thường).
    """
    raw = str(name or "")
    if is_valid_id(raw):
        return raw
    ascii_name = unicodedata.normalize("NFKD", raw)
    ascii_name = ascii_name.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", ascii_name).strip("_")
    if not cleaned:
        cleaned = fallback
    if cleaned[0].isdigit():
        cleaned = f"{fallback}_{cleaned}"
    return cleaned


def unique_id(base: str, taken) -> str:
    """Thêm hậu tố _2, _3… cho tới khi không trùng với tập `taken`."""
    base = sanitize_id(base)
    taken = set(taken or ())
    if base not in taken:
        return base
    i = 2
    while f"{base}_{i}" in taken:
        i += 1
    return f"{base}_{i}"


# ---------------------------------------------------------------- sổ đăng ký ảnh
# Có hai nguồn ảnh trở thành thành phần kéo thả được trong palette UI Designer:
#   1. Sprite vẽ ở Sprite Editor rồi bấm "Áp dụng"       -> GROUP_DRAWN
#   2. Ảnh nhập từ ngoài vào assets/ của project         -> GROUP_ASSETS
# Cả hai dùng chung một dạng token 'img:<key>' khi đi qua MIME/kéo thả.
GROUP_DRAWN = ("drawn", "SPRITE ĐÃ VẼ")
GROUP_ASSETS = ("assets", "TÀI NGUYÊN DỰ ÁN")
IMAGE_TOKEN_PREFIX = "img:"

SPRITE_REGISTRY: dict[str, dict] = {}   # sprite vẽ tay ở Sprite Editor
ASSET_REGISTRY: dict[str, dict] = {}    # ảnh nhập từ ngoài vào assets/

# tương thích với tên gọi cũ trong Sprite Editor
CUSTOM_GROUP = GROUP_DRAWN
SPRITE_TOKEN_PREFIX = IMAGE_TOKEN_PREFIX


def image_token(key: str) -> str:
    """Token dùng chung cho palette / MIME / canvas: 'img:<key>'."""
    return f"{IMAGE_TOKEN_PREFIX}{key}"


def is_image_token(token: str) -> bool:
    return isinstance(token, str) and token.startswith(IMAGE_TOKEN_PREFIX)


def image_key(token: str) -> str:
    return token[len(IMAGE_TOKEN_PREFIX):] if is_image_token(token) else ""


# tên cũ (giữ để code Sprite Editor không phải đổi hết)
sprite_token = image_token
is_sprite_token = is_image_token
sprite_key = image_key


def _register(registry: dict, group, key: str, title: str, image: QImage,
              src: str = "", folder: str = "") -> dict:
    entry = {
        "key": key,
        "title": title or key,
        "image": image,
        "src": src,
        "folder": folder,
        "group": group[0],
        "w": float(image.width()) if image is not None else 0.0,
        "h": float(image.height()) if image is not None else 0.0,
    }
    registry[key] = entry
    return entry


def register_sprite(key: str, title: str, image: QImage, src: str = "") -> dict:
    """Đăng ký một sprite vừa vẽ ở Sprite Editor."""
    return _register(SPRITE_REGISTRY, GROUP_DRAWN, key, title, image, src)


def register_asset(key: str, title: str, image: QImage, src: str,
                   folder: str = "") -> dict:
    """Đăng ký một ảnh vừa nhập từ ngoài vào project."""
    return _register(ASSET_REGISTRY, GROUP_ASSETS, key, title, image, src, folder)


def image_entry(key: str) -> dict | None:
    """Tra ảnh theo key trong cả hai sổ đăng ký."""
    return SPRITE_REGISTRY.get(key) or ASSET_REGISTRY.get(key)


def image_for_src(src: str) -> dict | None:
    """Tìm lại ảnh theo đường dẫn (dùng khi mở lại file .lua đã lưu)."""
    if not src:
        return None
    for registry in (SPRITE_REGISTRY, ASSET_REGISTRY):
        for entry in registry.values():
            if entry.get("src") == src:
                return entry
    return None


def image_entries() -> list[dict]:
    """Mọi ảnh đã đăng ký, xếp theo nhóm rồi theo tên."""
    entries = list(SPRITE_REGISTRY.values()) + list(ASSET_REGISTRY.values())
    return sorted(entries, key=lambda e: (e.get("group", ""), e.get("title", "")))


def clear_images():
    SPRITE_REGISTRY.clear()
    ASSET_REGISTRY.clear()


# tên cũ
sprite_entry = image_entry
sprite_for_src = image_for_src
clear_sprites = clear_images


def load_image(path) -> QImage | None:
    """Nạp ảnh từ đĩa; trả None nếu không đọc được."""
    image = QImage(str(path))
    return None if image.isNull() else image


def fit_in_screen(w: float, h: float) -> tuple[float, float]:
    """Thu nhỏ ảnh quá khổ (canvas vẽ tới 256px) cho vừa màn hình 240×320."""
    if w <= SCREEN_W and h <= SCREEN_H:
        return w, h
    scale = min(SCREEN_W / w, SCREEN_H / h)
    return max(8.0, round(w * scale)), max(8.0, round(h * scale))


# ---------------------------------------------------------------- palette màu

C_BORDER = QColor(BORDER)
# C_ACCENT là màu NỘI DUNG: nút / checkbox / progress / slider / switch trong
# game đều lấy nó làm mặc định, khớp `lua_export.ACCENT`. Accent CHROME của IDE
# là `ACCENT` (cam) — dùng trực tiếp `QColor(ACCENT)` cho viền chọn thành phần.
C_ACCENT = QColor("#007acc")
C_ACCENT_SOFT = QColor("#007acc")
C_ACCENT_SOFT.setAlpha(60)
C_TEXT = QColor(TEXT)
C_TEXT_DIM = QColor(TEXT_3)
# --- Màu NỘI DUNG (vẽ bên trong khung 240x320) -------------------------------
# Cố ý KHÔNG theo palette chrome: đây là hình minh hoạ widget trong game, đổi
# là đổi output ui_design.lua. Khớp với bảng màu của lua_export.py.
C_FILL = QColor("#2d2d30")
C_FILL_SOFT = QColor(45, 45, 48, 150)
C_GREEN = QColor("#4ec9b0")
C_AMBER = QColor("#d7ba7d")
# --- Màu CHROME --------------------------------------------------------------
C_TRACK = QColor(BORDER)
C_DASH = QColor(BORDER_HOVER)   # viền gạch của khung rỗng (row/column/spacer)

HANDLE = 5.0  # kích thước tay nắm resize (đơn vị scene)

# Thứ tự lớp (z-order): item thứ i trong danh sách layer có z = BASE + i * STEP.
# Bezel = -20, khung màn hình = -10 nên mọi thành phần luôn nằm trên nền.
LAYER_Z_BASE = 10
LAYER_Z_STEP = 10


class DesignerItem(QGraphicsRectItem):
    """Thành phần UI trên canvas — kéo di chuyển, chọn, resize góc dưới-phải.

    Ngoài hình học còn giữ:
      name    — ID của thành phần (định danh Lua, đồng bộ sang mã ở khoá `name`
                của scene và `ui.<id>` của tệp logic). Kích đúp ở bảng LAYERS
                hoặc sửa ô "ID" trong INSPECTOR để đổi.
      fill    — màu tô riêng (None = dùng màu mặc định của từng loại thành phần)
      rotation — góc xoay quanh tâm, dùng cho nút "Xoay" ở bảng LAYERS
    """

    def __init__(self, widget_type: str, x: float, y: float,
                 w: float | None = None, h: float | None = None, text: str = "",
                 image: QImage | None = None, src: str = "",
                 fill: QColor | None = None, rotation: float = 0.0):
        if w is None or h is None:
            dw, dh = default_rect(widget_type)
            w = dw if w is None else w
            h = dh if h is None else h
        super().__init__(0, 0, w, h)
        self.widget_type = widget_type
        self.text = text
        # bitmap cho thành phần Hình ảnh (sprite vẽ ở Sprite Editor áp dụng sang)
        self.image = image
        self.src = src
        # màu tô riêng — None nghĩa là dùng màu mặc định theo loại thành phần
        self.fill: QColor | None = QColor(fill) if fill is not None else None
        self.seq = next(_ITEM_SEQ)   # thứ tự tạo — phá hoà khi so z-value
        # ID mặc định suy từ bộ đếm theo loại (KHÔNG dùng id(self): id đổi mỗi
        # lần chạy nên tên sẽ không ổn định giữa các phiên). Scene sẽ uniquify
        # lại khi thêm.
        self.name = next_default_name(widget_type)
        self._resizing = False
        self._resize_origin = QPointF()
        self._resize_start = QRectF()
        # chỉ hít dính khi NGƯỜI DÙNG đang kéo — setPos() từ code (mở tệp, nhân
        # bản, undo…) phải đặt đúng toạ độ đã ghi, không bị dóng lại
        self._dragging = False

        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(LAYER_Z_BASE)
        if rotation:
            self.set_angle(rotation)

    # ------------------------------------------------ thông báo thay đổi
    def _notify_changed(self):
        """Báo scene rằng nội dung thành phần đã khác đi (để tự động lưu).

        Chỉ những trường ĐƯỢC GHI RA TỆP mới cần báo: vị trí, kích thước, chữ,
        màu tô, góc xoay, tên, ẩn/hiện. Trạng thái thuần hiển thị (đang chọn,
        đang hover) không báo — nếu không, chỉ bấm chọn một thành phần cũng làm
        IDE tưởng có việc để ghi.
        """
        scene = self.scene()
        notify = getattr(scene, "notify_content_changed", None)
        if notify is not None:
            notify()

    # ------------------------------------------------ màu tô
    def set_fill(self, color: QColor | None):
        """Đổi màu tô; truyền None để quay về màu mặc định của loại thành phần."""
        new = QColor(color) if color is not None and QColor(color).isValid() else None
        changed = (new is None) != (self.fill is None) or (
            new is not None and self.fill is not None and new != self.fill)
        self.fill = new
        self.update()
        if changed:
            self._notify_changed()

    def fill_or(self, default) -> QColor:
        """Màu tô đang dùng, hoặc `default` nếu chưa đặt màu riêng."""
        return QColor(self.fill) if self.fill is not None else QColor(default)

    # ------------------------------------------------ hình học
    def set_text(self, text: str):
        if text == self.text:
            return
        self.text = text
        self.update()
        self._notify_changed()

    def set_name(self, name: str):
        """Đổi ID thành phần (đồng bộ sang mã Lua qua bảng LAYERS / INSPECTOR).

        Không tự kiểm tra hợp lệ/trùng lặp — việc đó thuộc `DesignerScene.rename_item`
        để mọi đường vào (kích đúp, ô ID, mở tệp) dùng chung một luật.
        """
        name = str(name or "").strip()
        if name and name != self.name:
            self.name = name
            self.update()
            self._notify_changed()

    def set_image(self, image: QImage | None, src: str = ""):
        """Gắn bitmap cho thành phần Hình ảnh (sprite áp dụng từ Sprite Editor)."""
        self.image = image
        if src:
            self.src = src
        self.update()
        self._notify_changed()

    def set_size(self, w: float, h: float):
        """Đổi kích thước — KHÔNG cho thành phần vượt ra ngoài màn hình 240×320.

        Thành phần luôn phải nằm trọn trong khung màn hình, nên kích thước tối đa
        bị chặn bởi vị trí hiện tại: w <= SCREEN_W - x, h <= SCREEN_H - y.
        """
        x, y = self.pos().x(), self.pos().y()
        w = max(4.0, min(float(w), SCREEN_W - x))
        h = max(4.0, min(float(h), SCREEN_H - y))
        rect = self.rect()
        changed = (w, h) != (rect.width(), rect.height())
        self.setRect(0, 0, w, h)
        self.update()
        if changed:
            self._notify_changed()

    def max_size(self) -> tuple[float, float]:
        """Kích thước lớn nhất còn nằm trong màn hình, tính theo vị trí hiện tại."""
        pos = self.pos()
        return (max(4.0, SCREEN_W - pos.x()), max(4.0, SCREEN_H - pos.y()))

    # ------------------------------------------------ xoay
    def rotated_bounds(self) -> tuple[float, float]:
        """Kích thước hộp bao sau khi xoay (theo trục toạ độ màn hình)."""
        r = self.rect()
        return rotated_size(r.width(), r.height(), self.rotation())

    def aligned_bounds(self, pos: QPointF | None = None) -> QRectF:
        """Hộp bao HÌNH HỌC của thành phần — cơ sở để hít dính căn chỉnh.

        KHÔNG dùng `sceneBoundingRect()`: nó cộng thêm nửa bề dày nét vẽ (0.5px
        mỗi phía) nên dóng theo nó thì thành phần lệch nửa pixel so với thành
        phần khác. Vật đang kéo và vật tham chiếu phải cùng một cơ sở.
        """
        return bounds_at(self.rect(), self.rotation(), pos if pos is not None
                         else self.pos())

    def _clamp_for_rotation(self, x: float, y: float) -> tuple[float, float]:
        """Kẹp vị trí sao cho hộp bao SAU KHI XOAY vẫn nằm trong màn hình.

        Gốc xoay là tâm hình chữ nhật, nên hộp bao vượt ra mỗi phía
        (bw - w) / 2 so với hình chưa xoay.
        """
        r = self.rect()
        w, h = r.width(), r.height()
        bw, bh = self.rotated_bounds()
        lo_x, hi_x = (bw - w) / 2.0, SCREEN_W - w - (bw - w) / 2.0
        lo_y, hi_y = (bh - h) / 2.0, SCREEN_H - h - (bh - h) / 2.0
        x = (lo_x + hi_x) / 2.0 if hi_x < lo_x else min(max(x, lo_x), hi_x)
        y = (lo_y + hi_y) / 2.0 if hi_y < lo_y else min(max(y, lo_y), hi_y)
        return x, y

    def set_angle(self, angle: float):
        """Xoay thành phần quanh tâm rồi kẹp lại trong màn hình."""
        angle = float(angle) % 360.0
        changed = angle != self.rotation()
        self.setTransformOriginPoint(self.rect().center())
        self.setRotation(angle)
        x, y = self._clamp_for_rotation(self.pos().x(), self.pos().y())
        if (x, y) != (self.pos().x(), self.pos().y()):
            self.setPos(x, y)
        self.update()
        if changed:
            self._notify_changed()

    def rotate_by(self, delta: float = 90.0):
        """Xoay thêm `delta` độ (mặc định 90° — bốn hướng cho ảnh/sprite)."""
        self.set_angle(self.rotation() + delta)

    # ------------------------------------------------ chặn kéo ra ngoài màn hình
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene() is not None:
            x, y = value.x(), value.y()
            scene = self.scene()
            snap_item = getattr(scene, "snap_item", None)
            if self._dragging and snap_item is not None:
                # hít dính vào thành phần khác / khung màn hình (đồng thời cập
                # nhật danh sách đường dóng cho view vẽ)
                x, y = snap_item(self, x, y)
            if self.rotation():
                x, y = self._clamp_for_rotation(x, y)
            else:
                x, y = clamp_to_screen(x, y, self.rect().width(), self.rect().height())
            if x != value.x() or y != value.y():
                return QPointF(x, y)
        elif change in (QGraphicsItem.ItemPositionHasChanged,
                        QGraphicsItem.ItemVisibleHasChanged):
            # vị trí / ẩn-hiện đều được ghi ra tệp -> canvas đang bẩn
            self._notify_changed()
        return super().itemChange(change, value)

    def _end_drag(self):
        """Kết thúc kéo: tắt cờ hít dính và xoá đường dóng còn sót."""
        if not self._dragging:
            return
        self._dragging = False
        scene = self.scene()
        clear = getattr(scene, "clear_guides", None)
        if clear is not None:
            clear()

    # ------------------------------------------------ resize bằng tay nắm
    def _handle_rect(self) -> QRectF:
        r = self.rect()
        return QRectF(r.right() - HANDLE, r.bottom() - HANDLE, HANDLE * 2, HANDLE * 2)

    def hoverMoveEvent(self, event):
        on_handle = self._handle_rect().contains(event.pos())
        self.setCursor(Qt.SizeFDiagCursor if on_handle else Qt.SizeAllCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._handle_rect().contains(event.pos()):
            self._resizing = True
            self._resize_origin = event.scenePos()
            self._resize_start = QRectF(self.rect())
            event.accept()
            return
        super().mousePressEvent(event)
        # bật hít dính cho thao tác KÉO sắp tới (resize ở trên đã return sớm)
        if event.button() == Qt.LeftButton:
            self._dragging = True

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.scenePos() - self._resize_origin
            # đi qua set_size() để kích thước luôn bị kẹp trong màn hình
            self.set_size(self._resize_start.width() + delta.x(),
                          self._resize_start.height() + delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._resizing = False
        self._end_drag()
        super().mouseReleaseEvent(event)

    def mouseUngrabEvent(self, event):
        """Chuột bị giành mất giữa chừng (dialog bật lên…) -> đừng để cờ kẹt."""
        self._resizing = False
        self._end_drag()
        super().mouseUngrabEvent(event)

    # ------------------------------------------------ vẽ
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect()
        draw = _PAINTERS.get(self.widget_type, _draw_panel)
        draw(painter, rect, self)

        if self.isSelected():
            pen = QPen(QColor("#f59e0b"), 1.4, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#f59e0b")))
            r = self._handle_rect()
            painter.drawRect(QRectF(r.center().x() - 2.5, r.center().y() - 2.5, 5, 5))

    # ------------------------------------------------ serialize
    def to_dict(self) -> dict:
        pos = self.pos()
        rect = self.rect()
        d = {
            "type": self.widget_type,
            "name": self.name,
            "x": round(pos.x()),
            "y": round(pos.y()),
            "w": round(rect.width()),
            "h": round(rect.height()),
            "text": self.text,
        }
        if self.src:
            d["src"] = self.src
        if self.fill is not None:
            d["fill"] = self.fill.name()
        if self.rotation():
            d["rot"] = round(self.rotation(), 1)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "DesignerItem":
        src = d.get("src", "")
        image = None
        entry = sprite_for_src(src)
        if entry is not None:
            image = entry.get("image")
        fill_raw = d.get("fill")
        fill = QColor(fill_raw) if fill_raw else None
        item = cls(d["type"], d["x"], d["y"], d["w"], d["h"], d.get("text", ""),
                   image=image, src=src, fill=fill,
                   rotation=float(d.get("rot", 0.0) or 0.0))
        item.set_name(d.get("name", item.name))
        return item


# ---------------------------------------------------------------- helper vẽ

def _font(size: int = 8, bold: bool = False) -> QFont:
    f = QFont("Segoe UI", size)
    f.setBold(bold)
    return f


def _text(painter, rect: QRectF, text: str, color: QColor,
          align=Qt.AlignLeft | Qt.AlignVCenter, bold=False, pad: float = 4):
    if not text:
        return
    painter.setPen(QPen(color))
    painter.setFont(_font(8, bold))
    painter.drawText(rect.adjusted(pad, 0, -pad, 0), int(align), text)


def _dashed_box(painter, rect: QRectF, color: QColor = C_DASH):
    pen = QPen(color, 1, Qt.DashLine)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawRect(rect)


def _readable_on(color: QColor) -> QColor:
    """Màu chữ đọc được trên nền `color` (đen hoặc trắng tuỳ độ sáng)."""
    lum = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
    return QColor("#10131a") if lum > 148 else QColor("#ffffff")


def _fill_or(item, default) -> QColor:
    """Màu tô của thành phần, hoặc màu mặc định của loại đó."""
    getter = getattr(item, "fill_or", None)
    return getter(default) if getter is not None else QColor(default)


# ---------------------------------------------------------------- painters

def _draw_panel(painter, rect, item):
    painter.setPen(QPen(C_BORDER, 1))
    painter.setBrush(QBrush(_fill_or(item, "#161d29")))
    painter.drawRoundedRect(rect, 3, 3)


def _draw_card(painter, rect, item):
    painter.setPen(QPen(C_BORDER, 1))
    painter.setBrush(QBrush(_fill_or(item, "#1b2230")))
    painter.drawRoundedRect(rect, 5, 5)
    # vạch nhấn trên đỉnh thẻ
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(C_ACCENT_SOFT))
    painter.drawRoundedRect(QRectF(rect.left() + 1, rect.top() + 1, rect.width() - 2, 14), 4, 4)
    _text(painter, QRectF(rect.left(), rect.top(), rect.width(), 16), item.text, C_TEXT, pad=7)


def _draw_button(painter, rect, item):
    bg = _fill_or(item, C_ACCENT)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(bg))
    painter.drawRoundedRect(rect, 4, 4)
    _text(painter, rect, item.text, _readable_on(bg), Qt.AlignCenter, bold=True)


def _draw_label(painter, rect, item):
    _text(painter, rect, item.text, _fill_or(item, "#dfe4ee"))


def _draw_checkbox(painter, rect, item):
    box = QRectF(rect.left(), rect.top() + (rect.height() - 12) / 2, 12, 12)
    painter.setPen(QPen(C_ACCENT, 1.2))
    painter.setBrush(QBrush(QColor("#1c2029")))
    painter.drawRoundedRect(box, 2.5, 2.5)
    # dấu check
    painter.setPen(QPen(QColor("#ffffff"), 1.6))
    painter.drawLine(QPointF(box.left() + 3, box.center().y()),
                     QPointF(box.center().x(), box.bottom() - 3.5))
    painter.drawLine(QPointF(box.center().x(), box.bottom() - 3.5),
                     QPointF(box.right() - 2.5, box.top() + 3.5))
    _text(painter, rect.adjusted(16, 0, 0, 0), item.text, C_TEXT)


def _draw_textbox(painter, rect, item):
    painter.setPen(QPen(C_BORDER, 1))
    painter.setBrush(QBrush(C_FILL))
    painter.drawRoundedRect(rect, 4, 4)
    placeholder = item.text or "Nhập nội dung…"
    color = C_TEXT if item.text else QColor("#5f6b80")
    _text(painter, rect, placeholder, color, pad=7)


def _draw_image(painter, rect, item):
    painter.setPen(QPen(C_BORDER, 1))
    painter.setBrush(QBrush(QColor("#10151e")))
    painter.drawRoundedRect(rect, 3, 3)

    image = getattr(item, "image", None)
    if image is not None and not image.isNull():
        # vẽ bitmap thật (sprite áp dụng từ Sprite Editor), giữ tỉ lệ, canh giữa,
        # FastTransformation để pixel art không bị nhoè
        inner = rect.adjusted(1, 1, -1, -1)
        target = inner.size().toSize()
        scaled = image.scaled(target, Qt.KeepAspectRatio, Qt.FastTransformation)
        painter.drawImage(
            QPointF(inner.center().x() - scaled.width() / 2.0,
                    inner.center().y() - scaled.height() / 2.0),
            scaled,
        )
        return

    if rect.width() < 14 or rect.height() < 14:
        return
    painter.setPen(QPen(C_TEXT_DIM, 1.2))
    painter.setBrush(Qt.NoBrush)
    inner = rect.adjusted(6, 6, -6, -6)
    painter.drawEllipse(QPointF(inner.left() + inner.width() * 0.28,
                                inner.top() + inner.height() * 0.28), 2.2, 2.2)
    path = QPainterPath()
    path.moveTo(inner.left(), inner.bottom())
    path.lineTo(inner.left() + inner.width() * 0.38, inner.top() + inner.height() * 0.42)
    path.lineTo(inner.left() + inner.width() * 0.62, inner.bottom() - inner.height() * 0.18)
    path.lineTo(inner.left() + inner.width() * 0.82, inner.top() + inner.height() * 0.55)
    path.lineTo(inner.right(), inner.bottom())
    painter.drawPath(path)


def _draw_progress(painter, rect, item):
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(C_TRACK))
    painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
    fill = QRectF(rect.left(), rect.top(), max(4.0, rect.width() * 0.62), rect.height())
    painter.setBrush(QBrush(C_ACCENT))
    painter.drawRoundedRect(fill, rect.height() / 2, rect.height() / 2)


def _draw_slider(painter, rect, item):
    mid = rect.center().y()
    painter.setPen(QPen(C_TRACK, 3))
    painter.drawLine(QPointF(rect.left() + 5, mid), QPointF(rect.right() - 5, mid))
    painter.setPen(QPen(C_ACCENT, 3))
    painter.drawLine(QPointF(rect.left() + 5, mid),
                     QPointF(rect.left() + 5 + (rect.width() - 10) * 0.55, mid))
    knob = QPointF(rect.left() + 5 + (rect.width() - 10) * 0.55, mid)
    painter.setPen(QPen(C_ACCENT, 1.4))
    painter.setBrush(QBrush(QColor("#ffffff")))
    painter.drawEllipse(knob, 5, 5)


def _draw_switch(painter, rect, item):
    h = min(rect.height(), rect.width() / 2)
    track = QRectF(rect.left(), rect.center().y() - h / 2, rect.width(), h)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(C_ACCENT))
    painter.drawRoundedRect(track, h / 2, h / 2)
    painter.setBrush(QBrush(QColor("#ffffff")))
    knob_r = h / 2 - 2
    painter.drawEllipse(QPointF(track.right() - h / 2, track.center().y()), knob_r, knob_r)


def _draw_row(painter, rect, item):
    _dashed_box(painter, rect, QColor("#3f6fa8"))
    _text(painter, rect, item.text or "Row", QColor("#7fb4e8"), pad=6)


def _draw_column(painter, rect, item):
    _dashed_box(painter, rect, QColor("#3f6fa8"))
    _text(painter, QRectF(rect.left(), rect.top(), rect.width(), 14),
          item.text or "Column", QColor("#7fb4e8"), pad=6)


def _draw_divider(painter, rect, item):
    painter.setPen(QPen(C_BORDER, 1.4))
    painter.drawLine(QPointF(rect.left(), rect.center().y()),
                     QPointF(rect.right(), rect.center().y()))


def _draw_spacer(painter, rect, item):
    _dashed_box(painter, rect, QColor("#4a5468"))


def _draw_canvas(painter, rect, item):
    painter.setPen(QPen(C_BORDER, 1))
    painter.setBrush(QBrush(QColor("#0e131b")))
    painter.drawRect(rect)
    painter.setPen(QPen(QColor("#232b39"), 1))
    step = 10
    x = rect.left() + step
    while x < rect.right():
        painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        x += step
    y = rect.top() + step
    while y < rect.bottom():
        painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        y += step


def _draw_sprite(painter, rect, item):
    painter.setPen(QPen(C_BORDER, 1))
    painter.setBrush(QBrush(QColor("#12181f")))
    painter.drawRect(rect)
    if rect.width() < 10:
        return
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(C_AMBER))
    painter.drawEllipse(QPointF(rect.center().x(), rect.top() + rect.height() * 0.32),
                        rect.width() * 0.14, rect.height() * 0.14)
    painter.setBrush(QBrush(QColor("#ef665c")))
    painter.drawRoundedRect(
        QRectF(rect.center().x() - rect.width() * 0.18, rect.top() + rect.height() * 0.48,
               rect.width() * 0.36, rect.height() * 0.42), 2, 2)


def _draw_tile(painter, rect, item):
    painter.setPen(QPen(C_BORDER, 0.8))
    painter.setBrush(QBrush(QColor("#2d5d47")))
    painter.drawRect(rect)
    painter.setPen(QPen(QColor("#1a352c"), 0.8))
    painter.drawLine(QPointF(rect.center().x(), rect.top()),
                     QPointF(rect.center().x(), rect.bottom()))
    painter.drawLine(QPointF(rect.left(), rect.center().y()),
                     QPointF(rect.right(), rect.center().y()))


def _draw_rect(painter, rect, item):
    painter.setPen(QPen(C_ACCENT, 1.2))
    painter.setBrush(QBrush(_fill_or(item, QColor(43, 107, 242, 45))))
    painter.drawRoundedRect(rect, 3, 3)


_PAINTERS = {
    "panel": _draw_panel,
    "card": _draw_card,
    "button": _draw_button,
    "label": _draw_label,
    "checkbox": _draw_checkbox,
    "textbox": _draw_textbox,
    "image": _draw_image,
    "progress": _draw_progress,
    "slider": _draw_slider,
    "switch": _draw_switch,
    "row": _draw_row,
    "column": _draw_column,
    "divider": _draw_divider,
    "spacer": _draw_spacer,
    "canvas": _draw_canvas,
    "sprite": _draw_sprite,
    "tile": _draw_tile,
    "rect": _draw_rect,
}
