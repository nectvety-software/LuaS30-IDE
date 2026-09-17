"""
palette.py — Bảng màu DUY NHẤT của LuaS30 Studio.

Chuẩn thiết kế: VS Code Dark Modern / Dark+ (neutral gray chrome + accent xanh
dương `#0078d4`), không còn slate navy + cam MRE.

Quy ước:
- Mọi màu chrome (nền, viền, chữ, nút, selection) phải lấy từ đây. Không viết
  hex trực tiếp trong `theme.py` hay trong code Python.
  `tools/studio_theme_check.py` kiểm tra điều này.
- Màu cú pháp (SYN_*) là ngoại lệ có chủ ý: giữ bảng VS Code dark+ để code dễ
  đọc.
- Thang nền: INK (chrome sâu) → SURFACE/ALT (editor, nội dung) → RAISED
  (menu, popup) → HOVER → PRESSED.
"""

# ---------------------------------------------------------------- nền (VS Code Dark Modern)
BG_INK = "#181818"        # activity bar, side bar, title, menu bar — sâu nhất
BG_ALT = "#1f1f1f"        # editor mặc định, tab chưa chọn, hàng xen kẽ
BG_SURFACE = "#1e1e1e"    # mặt nội dung chính: panel, card, dialog, editor
BG_RAISED = "#252526"     # menu, popup, command center, card nổi
BG_HOVER = "#2a2d2e"      # hover hàng / nút
BG_PRESSED = "#37373d"    # nút phụ, trạng thái nhấn
BG_SELECT = "#04395e"     # mục đang chọn trong list / menu (VS Code selection)
BG_SELECT_SOFT = "#264f78"  # vùng chọn chữ trong editor

# ---------------------------------------------------------------- viền
BORDER = "#2b2b2b"        # viền mảnh, đường phân cách
BORDER_STRONG = "#3c3c3c"  # viền ô nhập / nút / khung
BORDER_HOVER = "#454545"  # viền khi hover
SCROLL = "#424242"        # tay cuộn
SCROLL_HOVER = "#7a7a7a"

# ---------------------------------------------------------------- chữ
TEXT = "#ffffff"          # tiêu đề, chữ nhấn
TEXT_2 = "#cccccc"        # chữ thường
TEXT_3 = "#9d9d9d"        # nhãn
TEXT_4 = "#858585"        # chữ mờ
TEXT_5 = "#8a8a8a"        # chữ rất mờ, ghi chú nhỏ

# ---------------------------------------------------------------- accent (VS Code blue)
ACCENT = "#0078d4"
ACCENT_HOVER = "#0063b8"
ACCENT_LIGHT = "#4da6ff"
ACCENT_DEEP = "#005a9e"
ON_ACCENT = "#ffffff"     # chữ trên nền accent

# ---------------------------------------------------------------- status bar (VS Code Dark+)
STATUS_BG = "#007acc"
STATUS_FG = "#ffffff"
STATUS_HOVER = "#0063a1"

# ---------------------------------------------------------------- trạng thái
GREEN = "#0f7b4c"
GREEN_LIGHT = "#6ee7b7"
GREEN_BORDER = "#166534"
RED = "#f87171"
RED_LIGHT = "#fca5a5"
RED_DEEP = "#b91c1c"
RED_BORDER = "#7f1d1d"
AMBER = "#fbbf24"
AMBER_DEEP = "#78350f"
AMBER_BORDER = "#78350f"
INFO = "#7dd3fc"
INFO_BG = "#0b2032"
INFO_BORDER = "#164e63"

# ---------------------------------------------------------------- diff (AI review)
DIFF_ADDED_BG = "#173321"      # nền dòng được thêm
DIFF_REMOVED_BG = "#3b1f24"    # nền dòng bị xoá

# ---------------------------------------------------------------- màu cú pháp
# Ngoại lệ có chủ ý — bảng VS Code dark+, KHÔNG đồng bộ theo chrome.
SYN_KEYWORD = "#c586c0"
SYN_STRING = "#ce9178"
SYN_FUNC = "#dcdcaa"
SYN_TYPE = "#4ec9b0"
SYN_VAR = "#9cdcfe"
SYN_NUMBER = "#b5cea8"
SYN_COMMENT = "#6a9955"
SYN_CONST = "#569cd6"

# ---------------------------------------------------------------- UI Designer
DESIGNER_BG_DOT = "#2a2a2a"    # lưới chấm sau khung điện thoại
DESIGNER_FRAME = ACCENT        # khung màn hình + viền thân máy
DESIGNER_BEZEL = "#0a0a0a"     # vỏ máy
GUIDE_ITEM = GREEN             # đường dóng: thẳng hàng thành phần
GUIDE_FRAME = AMBER            # đường dóng: thẳng với khung màn hình


# Tập hợp để kiểm tra "màu lạ" — xem tools/studio_theme_check.py
def values() -> dict[str, str]:
    return {
        name: value
        for name, value in globals().items()
        if name.isupper() and isinstance(value, str) and value.startswith("#")
    }


def hex_set() -> set[str]:
    return {value.lower() for value in values().values()}


def qcolor(token: str, alpha: int | None = None):
    """Tiện dụng: hex -> QColor (kèm alpha tuỳ chọn)."""
    from PySide6.QtGui import QColor

    color = QColor(token)
    if alpha is not None:
        color.setAlpha(alpha)
    return color
