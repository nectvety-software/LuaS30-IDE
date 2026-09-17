from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.ui import palette
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPixmap


# Code points are from the Windows Segoe MDL2 / Fluent icon set.
# No font binaries are bundled with LuaS30 IDE.
GLYPHS: dict[str, str] = {
    "menu": "",
    "add": "",
    "close": "",
    "settings": "",
    "search": "",
    "refresh": "",
    "check": "",
    "save": "",
    "console": "",
    "terminal": "",
    "play": "",
    "stop": "",
    "edit": "",
    "chevron_up": "",
    "chevron_down": "",
    "back": "",
    "forward": "",
    "folder": "",
    "folder_open": "",
    "file": "",
    "copy": "",
    "cut": "",
    "paste": "",
    "build": "",
    "image": "",
    "designer": "",
    "info": "",
    "warning": "",
    "error": "",
    "projects": "",
    "new_file": "",
    "new_folder": "",
    "open_external": "",
    "collapse": "",
    "expand": "",
    "delete": "",
    "undo": "",
    "redo": "",
    "select_all": "",
    "code": "",
    "home": "",
    "run": "",
    "chat": "",
    "send": "",
    "spark": "",
    "more": "",
    "connect": "",
    # --- UI Designer ---
    "zoom": "",
    "zoom_in": "",
    "zoom_out": "",
    "magnet": "",
    "rotate": "",
    "frame": "",
    "fit": "",
    "layers": "",
    "duplicate": "",
    "arrow_up": "",
    "arrow_down": "",
    "sync": "",
    "grid": "",
    "pointer": "",
    "text_style": "",
    "music": "",
}


FONT_CANDIDATES = (
    "Segoe Fluent Icons",
    "Segoe MDL2 Assets",
    "Segoe UI Symbol",
)


def resolve_color(color: str | None) -> str:
    """Accept palette token names (`palette.TEXT_3` / `TEXT_3`) or raw #hex."""
    if not color:
        return palette.TEXT_3
    token = color.split(".", 1)[-1]
    value = getattr(palette, token, None)
    if isinstance(value, str) and value.startswith("#"):
        return value
    if isinstance(color, str) and color.startswith("#"):
        return color
    return palette.TEXT_3


@lru_cache(maxsize=1)
def icon_font_family() -> str:
    families = set(QFontDatabase.families())
    for family in FONT_CANDIDATES:
        if family in families:
            return family
    # Development fallback only. Windows 10/11 normally has MDL2/Fluent.
    return "Segoe UI Symbol"


def icon_font(pixel_size: int = 18) -> QFont:
    font = QFont(icon_font_family())
    font.setPixelSize(pixel_size)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def glyph(name: str) -> str:
    return GLYPHS.get(name, GLYPHS["info"])


def _glyph_pixmap(name: str, size: int, color: str) -> QPixmap:
    scale = 2
    px = QPixmap(size * scale, size * scale)
    px.fill(Qt.GlobalColor.transparent)
    px.setDevicePixelRatio(scale)

    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.setPen(QColor(resolve_color(color)))
    painter.setFont(icon_font(max(10, int(size * 0.95))))
    painter.drawText(
        QRect(0, 0, size, size),
        int(Qt.AlignmentFlag.AlignCenter),
        glyph(name),
    )
    painter.end()
    return px


@lru_cache(maxsize=256)
def font_icon(
    name: str,
    size: int = 16,
    normal: str = "palette.TEXT_3",
    active: str = "palette.TEXT",
    disabled: str = "palette.TEXT_5",
) -> QIcon:
    icon = QIcon()
    icon.addPixmap(_glyph_pixmap(name, size, normal), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(_glyph_pixmap(name, size, active), QIcon.Mode.Active, QIcon.State.Off)
    icon.addPixmap(_glyph_pixmap(name, size, active), QIcon.Mode.Selected, QIcon.State.On)
    icon.addPixmap(_glyph_pixmap(name, size, disabled), QIcon.Mode.Disabled, QIcon.State.Off)
    return icon


def apply_icon(widget, name: str, size: int = 16, color: str = "palette.TEXT_3") -> None:
    widget.setIcon(font_icon(name, size=size, normal=color))
    widget.setIconSize(QSize(size, size))


def apply_action_icon(action, name: str, size: int = 16) -> None:
    action.setIcon(font_icon(name, size=size))


# --- Bieu tuong ung dung (logo LuaS30) tu thu muc app-icon/ ---
APP_IMAGE_CANDIDATES = ("icon.png", "icon.ico", "64x64.png", "32x32.png")


def find_app_image(engine_root: Path | str) -> Path | None:
    """Tra ve file logo app dau tien tim thay trong <engine_root>/app-icon/."""
    base = Path(engine_root) / "app-icon"
    for name in APP_IMAGE_CANDIDATES:
        candidate = base / name
        if candidate.is_file():
            return candidate
    return None


def app_icon(engine_root: Path | str) -> QIcon:
    """QIcon logo app cho cua so/taskbar (fallback QIcon rong neu thieu file)."""
    found = find_app_image(engine_root)
    if found is None:
        return QIcon()
    return QIcon(str(found))


def app_logo_pixmap(engine_root: Path | str, height: int = 22, device_ratio: float = 1.0) -> QPixmap:
    """Pixmap logo app theo chieu cao, net tren man hinh HiDPI (fallback pixmap rong)."""
    found = find_app_image(engine_root)
    if found is None:
        return QPixmap()
    source = QPixmap(str(found))
    if source.isNull():
        return QPixmap()
    ratio = device_ratio if device_ratio and device_ratio > 0 else 1.0
    scaled = source.scaledToHeight(
        max(1, int(height * ratio)),
        Qt.TransformationMode.SmoothTransformation,
    )
    scaled.setDevicePixelRatio(ratio)
    return scaled
