"""
icons_compat.py — Adapter icon cho UI Designer.

Bản gốc (lua-engine) vẽ icon bằng QPainterPath theo chuẩn Lucide 24x24
(`icons.icon_save("palette.TEXT_3")`, `icons.colored_pixmap(icons.path_music, ...)`).
Studio LuaS30 không bundle font/svg icon nào — nó vẽ glyph từ font hệ thống
Segoe MDL2 Assets / Segoe Fluent Icons (`app/ui/icons.py`).

Module này giữ NGUYÊN chữ ký của bản gốc để phần thân các module port sang
không phải sửa một dòng nào:

    icons.icon_save("palette.TEXT_3")        -> QIcon
    icons.colored_pixmap(path_music, "palette.ACCENT", size=20, stroke=1.8) -> QPixmap

`path_music` ở đây là một KHOÁ GLYPH (chuỗi) chứ không phải hàm trả
QPainterPath — `colored_pixmap` nhận cả hai kiểu nên lời gọi giữ nguyên hiệu lực.
"""

from __future__ import annotations

from functools import lru_cache

from app.ui import palette
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

from app.ui.icons import font_icon, glyph

DEFAULT_COLOR = "palette.TEXT_3"
DEFAULT_SIZE = 16

# ---------------------------------------------------------------- cỡ icon
# Một chỗ duy nhất quy định cỡ icon của UI Designer, theo thói quen của VS Code:
# icon trên thanh công cụ 20px, mọi icon còn lại (palette, bảng LỚP, nút nhỏ)
# 16px. Nút vuông nhỏ là 22px — vừa khít một icon 16px cộng viền hover.
#
# QUAN TRỌNG: pixmap glyph được render ĐÚNG cỡ hiển thị (`font_icon(name, size)`).
# Render 16px rồi cho Qt phóng lên 20px sẽ ra icon nhoè, nên nơi nào đổi cỡ hiển
# thị thì phải truyền đúng cỡ đó xuống hàm `icon_*`.
ICON = 16
ICON_TOOLBAR = 20
BTN = 22


# ---------------------------------------------------------------- pixmap

@lru_cache(maxsize=256)
def _glyph_pixmap(name: str, size: int, color: str) -> QPixmap:
    """Glyph đơn sắc -> QPixmap trong suốt (không cache QIcon để tránh giữ widget)."""
    scale = 2
    px = QPixmap(size * scale, size * scale)
    px.fill(Qt.GlobalColor.transparent)
    px.setDevicePixelRatio(scale)

    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setPen(QColor(color))
    from app.ui.icons import icon_font

    painter.setFont(icon_font(max(9, int(size * 0.94))))
    painter.drawText(
        0, 0, size, size,
        int(Qt.AlignmentFlag.AlignCenter),
        glyph(name),
    )
    painter.end()
    return px


def icon(name: str, color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    """Icon theo tên glyph — lớp nền cho mọi hàm `icon_*` bên dưới."""
    return font_icon(name, size=size, normal=color, active=color, disabled="palette.TEXT_5")


def colored_pixmap(path_func, color: str, size: int = 20, stroke: float = 1.6) -> QPixmap:
    """Pixmap cho widget cần ảnh tĩnh (QLabel / QComboBox item).

    `path_func` nhận khoá glyph (chuỗi) — hoặc hàm trả về khoá glyph. Tham số
    `stroke` giữ lại cho tương thích chữ ký bản gốc (glyph font không dùng nét).
    """
    key = path_func() if callable(path_func) else path_func
    return _glyph_pixmap(str(key), int(size), color)


# ---------------------------------------------------------------- path symbols
# Bản gốc trả QPainterPath; ở đây chỉ cần một khoá glyph là đủ.
path_music = "music"


# ---------------------------------------------------------------- icon set
# Mỗi hàm nhận (color, size) — đúng chữ ký bản gốc `icons.icon_x(color)`.

def icon_add(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("add", color, size)


def icon_close(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("close", color, size)


def icon_search(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("search", color, size)


def icon_check(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("check", color, size)


def icon_file(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("file", color, size)


def icon_folder(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("folder", color, size)


def icon_folder_open(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("folder_open", color, size)


def icon_save(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("save", color, size)


def icon_image(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("image", color, size)


def icon_play(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("play", color, size)


def icon_code(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("code", color, size)


def icon_text(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("text_style", color, size)


def icon_refresh(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("refresh", color, size)


def icon_sync(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("sync", color, size)


def icon_trash(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("delete", color, size)


def icon_duplicate(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("duplicate", color, size)


def icon_rotate(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("rotate", color, size)


def icon_arrow_up(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("arrow_up", color, size)


def icon_arrow_down(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("arrow_down", color, size)


def icon_ellipsis_h(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("more", color, size)


def icon_plus(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("add", color, size)


def icon_magnet(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("magnet", color, size)


def icon_zoom_in(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("zoom_in", color, size)


def icon_zoom_out(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("zoom_out", color, size)


def icon_zoom(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("zoom", color, size)


def icon_frame(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("fit", color, size)


def icon_fit(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("fit", color, size)


def icon_layers(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("layers", color, size)


def icon_grid(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("grid", color, size)


def icon_pointer(color: str = DEFAULT_COLOR, size: int = DEFAULT_SIZE) -> QIcon:
    return icon("pointer", color, size)
