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

# ---------------------------------------------------------------- Chat AI (Modern Dark IDE)
# Bảng MÀU RIÊNG cho khu vực "AI Trợ lý" — dark xanh-tối + accent cam #FF6A00
# theo PROMPT tái thiết kế "AI Coding Assistant". Chrome toàn cục của Studio VẪN
# dùng palette VS Code ở trên; chỉ selector `AIChat*`/`AIWelcome*`/... lấy @CHAT_.
CHAT_BG = "#0d1014"               # nền chính sâu nhất của khung chat
CHAT_BG_STRONGER = "#11151a"      # header / composer strip / thanh tab
CHAT_SURFACE = "#151a21"          # card, tin nhắn, pill model
CHAT_PANEL = "#131820"            # panel phụ / input nền
CHAT_RAISED = "#191f27"           # nút, chip, badge (mức card-hover)
CHAT_RAISED_HOVER = "#1a2028"     # hover icon trần / nút
CHAT_HOVER = "#171c23"            # hover hàng / tab chưa chọn
CHAT_BORDER = "#272e38"           # viền chính
CHAT_BORDER_WEAK = "#1e242c"      # viền mảnh, phân cách
CHAT_TEXT = "#f2f4f7"             # chữ nhấn / tiêu đề
CHAT_TEXT_2 = "#b7c1cd"           # chữ nội dung chính
CHAT_TEXT_3 = "#9da7b5"           # chữ phụ / nhãn mờ
CHAT_TEXT_4 = "#646d79"           # chữ disabled / ghi chú
CHAT_ACCENT = "#ff6a00"           # cam nhấn chính
CHAT_ACCENT_HOVER = "#ff7a1a"
CHAT_ACCENT_PRESSED = "#e95f00"
CHAT_ACCENT_DEEP = "#4a2814"      # nền/avatar accent nhạt
CHAT_ON_ACCENT = "#111111"        # chữ trên nền cam
CHAT_INPUT = "#131820"            # nền ô soạn prompt
CHAT_INPUT_BORDER = "#303946"     # viền ô soạn prompt
CHAT_TAB_ACTIVE = "#1c1815"       # nền tab đang chọn (cam ám rất tối)
CHAT_ACCESS_BG = "#191714"        # nền pill Full Access đang bật
CHAT_STOP = "#e95555"             # nút Dừng khi agent chạy
CHAT_SEND_DISABLED = "#242a31"    # nền nút Gửi khi rỗng
CHAT_ON_SEND_DISABLED = "#68727e" # chữ nút Gửi khi rỗng
CHAT_TS = "#77818e"               # timestamp góc phải thẻ tin
CHAT_AVATAR_USER = "#252d38"      # avatar "B"
CHAT_SCROLL_THUMB = "#343c47"     # thanh cuộn mảnh
CHAT_SCROLL_THUMB_HOVER = "#48515e"
# Khối code trong transcript (render HTML nội bộ, không đụng editor palette):
CHAT_CODE_BG = "#0c1117"
CHAT_CODE_BORDER = "#242c36"
CHAT_CODE_GUTTER = "#0a0e13"      # nền cột số dòng
CHAT_CODE_GUTTER_TEXT = "#727d8c" # số dòng
CHAT_CODE_LANG = "#8995a5"        # nhãn ngôn ngữ ở header
# 6 màu cú pháp riêng cho code block chat (khác bảng VS Code của editor):
CHAT_SYN_KEYWORD = "#c792ea"
CHAT_SYN_STRING = "#e6b673"
CHAT_SYN_NUMBER = "#82aaff"
CHAT_SYN_FUNCTION = "#7fdbca"
CHAT_SYN_COMMENT = "#66717f"
CHAT_SYN_VARIABLE = "#aab8d4"

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
