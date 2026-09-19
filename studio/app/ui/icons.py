from __future__ import annotations

import sys
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
    "delete": "",
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
    "arrow_left": "",
    "arrow_right": "",
    "sync": "",
    "grid": "",
    "pointer": "",
    "text_style": "",
    "music": "",
    "minus": "",
    "gamepad": "",
    "users": "",
    "robot": "",
    "brush": "",
    "power": "",
    "circle": "",
    "bell": "",
    "library": "",
    "download": "",
    "microchip": "",
    "square": "",
    "location": "",
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


# Mã PUA của Segoe (E1xx/E7xx/E8xx...) KHÔNG có mặt đầy đủ trong mọi font ứng
# viên: "Segoe UI Symbol" thiếu gần hết, "Segoe Fluent Icons" (Win11) vắng một
# vài mã cũ. Chọn font THEO TỪNG GLYPH bằng cách đọc cmap trực tiếp từ TTF hệ
# thống — đáng tin hơn QFontDatabase.families() (lỗi/offscreen hay sai).
_FAMILY_FILES = {
    "Segoe Fluent Icons": "segoefluenticons.ttf",
    "Segoe MDL2 Assets": "segmdl2.ttf",
    "Segoe UI Symbol": "segoesym.ttf",
}


def _cmap_codepoints(data: bytes) -> set[int]:
    import struct

    num = struct.unpack(">H", data[4:6])[0]
    tables = {}
    for i in range(num):
        tag = data[12 + 16 * i:16 + 16 * i]
        off, ln = struct.unpack(">II", data[20 + 16 * i:28 + 16 * i])
        tables[tag.decode("latin-1")] = off
    off = tables["cmap"]
    n = struct.unpack(">H", data[off + 2:off + 4])[0]
    have: set[int] = set()
    for i in range(n):
        pid, eid, so = struct.unpack(">HHI", data[off + 4 + 8 * i:off + 12 + 8 * i])
        if (pid, eid) not in ((3, 1), (3, 10), (0, 3), (0, 4)):
            continue
        s = off + so
        fmt = struct.unpack(">H", data[s:s + 2])[0]
        if fmt == 4:
            segx2 = struct.unpack(">H", data[s + 6:s + 8])[0]
            seg = segx2 // 2
            ends = struct.unpack(f">{seg}H", data[s + 14:s + 14 + segx2])
            starts = struct.unpack(f">{seg}H", data[s + 16 + segx2:s + 16 + 2 * segx2])
            deltas = struct.unpack(f">{seg}h", data[s + 16 + 2 * segx2:s + 16 + 3 * segx2])
            rpos = s + 16 + 3 * segx2
            ranges = struct.unpack(f">{seg}H", data[rpos:rpos + segx2])
            for k in range(seg):
                for c in range(starts[k], min(ends[k], 0xFFFE) + 1):
                    if ranges[k] == 0:
                        gid = (c + deltas[k]) & 0xFFFF
                    else:
                        addr = rpos + 2 * k + ranges[k] + 2 * (c - starts[k])
                        if addr + 2 > len(data):
                            continue
                        gid = struct.unpack(">H", data[addr:addr + 2])[0]
                        if gid:
                            gid = (gid + deltas[k]) & 0xFFFF
                    if gid:
                        have.add(c)
        elif fmt == 12:
            ng = struct.unpack(">I", data[s + 12:s + 16])[0]
            for g in range(ng):
                sc, ec, sg = struct.unpack(">III", data[s + 16 + 12 * g:s + 28 + 12 * g])
                have.update(c for c in range(sc, ec + 1) if sg + (c - sc))
        elif fmt == 6:
            first, cnt = struct.unpack(">HH", data[s + 6:s + 10])
            have.update(first + j for j in range(cnt) if data[s + 10 + j])
    return have


@lru_cache(maxsize=8)
def _family_codepoints(family: str) -> frozenset[int]:
    fname = _FAMILY_FILES.get(family)
    if not fname or sys.platform != "win32":
        return frozenset()
    import os

    base = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    path = base / fname
    try:
        return frozenset(_cmap_codepoints(path.read_bytes()))
    except (OSError, KeyError, ValueError, IndexError):
        return frozenset()


@lru_cache(maxsize=256)
def _family_for_char(char: str) -> str:
    cp = ord(char)
    for family in FONT_CANDIDATES:
        codepoints = _family_codepoints(family)
        if codepoints and cp in codepoints:
            return family
    return icon_font_family()


def icon_font(pixel_size: int = 18, char: str | None = None) -> QFont:
    family = _family_for_char(char) if char else icon_font_family()
    font = QFont(family)
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
    ch = glyph(name)
    painter.setFont(icon_font(max(10, int(size * 0.95)), char=ch))
    painter.drawText(
        QRect(0, 0, size, size),
        int(Qt.AlignmentFlag.AlignCenter),
        ch,
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
