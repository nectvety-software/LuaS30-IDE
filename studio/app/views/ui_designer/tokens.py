"""
tokens.py — Tên token của UI Designer, dẫn xuất từ `app/ui/palette.py`.

Bản gốc bên lua-engine đọc token từ `app/ui/theme.py` (bảng màu "2Dutiful dark
enterprise" nền xanh đen). Ở đây KHÔNG định nghĩa màu nữa: mọi tên token đều
trỏ thẳng về `palette.py` — bảng màu duy nhất của Studio, theo ngôn ngữ thiết kế
của hộp thoại "Cấu hình MediaTek MRE SDK". Nhờ vậy canvas / palette / inspector
không thể lệch khỏi phần còn lại của IDE.

Giữ nguyên TÊN token của bản gốc để phần thân các module port sang không phải
sửa: `ACCENT`, `BORDER`, `BG_HOVER`, `TEXT_2`, `TEXT_3`, `TEXT_4`.

Thang chữ: `TEXT` > `TEXT_2` > `TEXT_3` > `TEXT_4`. Bản gốc có bốn mức xám riêng;
palette chỉ có một mức "chữ mờ" nên `TEXT_3` và `TEXT_4` cùng trỏ về `TEXT_4` —
đúng như cách `theme.py` đã gom hai mức xám mờ nhất về một token.
"""

from app.ui import palette

# ---- Nền ----
BG_APP = palette.BG_INK          # nền editor / canvas
BG_ROOT = palette.BG_SURFACE     # nền shell
BG_PANEL = palette.BG_RAISED     # panel / card / toolbar
BG_SIDEBAR = palette.BG_INK      # rail / panel phụ
BG_HOVER = palette.BG_HOVER      # hover row
BG_ACTIVE = palette.BG_SELECT    # row đang chọn
BG_INPUT = palette.BG_INK        # ô nhập
BG_CARD = palette.BG_SURFACE
BG_SELECTED = palette.BG_SELECT  # mục đang chọn trong list/menu

# ---- Viền ----
BORDER = palette.BORDER
BORDER_SOFT = palette.BORDER
BORDER_HOVER = palette.BORDER_HOVER

# ---- Chữ ----
TEXT = palette.TEXT
TEXT_2 = palette.TEXT_2
TEXT_3 = palette.TEXT_4
TEXT_4 = palette.TEXT_4

# ---- Accent (cam MRE) ----
ACCENT = palette.ACCENT
ACCENT_HOVER = palette.ACCENT_HOVER
ACCENT_LIGHT = palette.ACCENT_LIGHT
ACCENT_LINK = palette.ACCENT_HOVER

# ---- Trạng thái ----
GREEN = palette.GREEN
GREEN_LIGHT = palette.GREEN_LIGHT
RED = palette.RED
RED_LIGHT = palette.RED_LIGHT
AMBER = palette.AMBER

# ---- Riêng UI Designer ----
DESIGNER_BG_DOT = palette.DESIGNER_BG_DOT    # lưới chấm sau khung điện thoại
DESIGNER_FRAME = palette.DESIGNER_FRAME      # khung màn hình + viền thân máy
DESIGNER_BEZEL = palette.DESIGNER_BEZEL
GUIDE_ITEM = palette.GUIDE_ITEM              # dóng với thành phần khác
GUIDE_FRAME = palette.GUIDE_FRAME            # dóng với khung màn hình

qcolor = palette.qcolor
