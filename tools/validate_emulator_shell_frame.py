#!/usr/bin/env python3
"""validate_emulator_shell_frame.py — vỏ máy giả lập vẽ ĐÚNG như thiết kế.

`vxp_emu_window.py` không dùng QSS cho thân máy: gradient, rail công cụ, hàng
trạng thái và bàn phím hai dòng đều do `paintEvent` vẽ tay. Nghĩa là **không có
gì canh được ngoại hình nó ngoài chính ảnh nó vẽ ra** — đổi một hằng số là vỏ
máy lệch khỏi mockup mà không có lỗi, không có cảnh báo, không có test nào đỏ.

Nên script này render THẬT vỏ máy ở nền offscreen rồi soi từng điểm ảnh:

  A. Hằng số thiết bị còn đó và là màu `#rrggbb` hợp lệ.
  B. Hình học: màn hình, bàn phím, 21 nút, rail công cụ bên phải.
  C. Ảnh render: gradient DỰNG ĐỨNG (kiểm ở orientation NGANG — xem §C1), góc
     bo tròn, hàng trạng thái nằm TRÊN màn hình, mỗi phím số có HAI dòng chữ
     thật chứ không phải một dòng bị cắt.
  D. Mọi ký tự trên vỏ máy phải có trong cmap của Segoe UI. `⇧` (U+21E7) KHÔNG
     có trong Segoe UI (chỉ Segoe UI Symbol mới có) nên vẽ ra ô vuông mà im
     lặng — bẫy đã mắc thật khi dựng mockup này. Tên công cụ của rail cũng là
     chữ được VẼ, nên cũng phải qua đây.
  E. Hành vi: `live` SUY RA từ `state`; đồng hồ màn hình chờ là GIỜ THẬT chứ
     không phải số cứng; mọi khoá rail đều có handler; `#` được làm mờ.
  F. Rê chuột lên phím: tên phím hiện ở hàng trạng thái, phím sáng lên, và tên
     đó phải TẮT khi chuột ra — kể cả khi chuột chạy thẳng từ nút này sang nút
     kề (thứ tự Enter/Leave không được Qt bảo đảm).
  G. Rê chuột lên ICON rail: bong bóng hiện đúng tên công cụ, đúng bề rộng chữ,
     nằm ĐÚNG cạnh nút đang trỏ (cùng hệ toạ độ), tắt khi rời chuột, và **không
     được chặn chuột** lên thân máy nằm dưới nó.

Bốn cái bẫy của CHÍNH script này, đã mắc thật khi viết (đừng "đơn giản hoá" lại):

  1. `QWidget.grab()` ở nền offscreen tô vùng KHÔNG được vẽ bằng `#efefef` (xám
     sáng), không phải bằng nền vỏ máy. Nên "đếm điểm ảnh khác nền" không chứng
     minh được gì: một bàn phím KHÔNG hề vẽ cũng ra đầy "mực". Phải đếm điểm ảnh
     TRÙNG màu phím.
  2. Gốc toạ độ của ảnh là `PhoneStage`. Bản trước thân vỏ bị đẩy xuống `CHIP_H -
     CHIP_OVERLAP` px cho hai chip chờm lên đỉnh vỏ, nên lấy điểm "(1,1)" là lấy
     vùng trống phía trên chip. Nay thân vỏ ở `(0, 0)` — nhưng đừng quên rail
     nằm BÊN PHẢI, nên `stage.width()` KHÔNG còn bằng `body.width()`.
  3. `QMenu.exec()` là vòng lặp sự kiện LỒNG NHAU: bấm một widget mở QMenu trong
     script nền offscreen sẽ treo vô hạn, im lặng. Rail bỏ hẳn QMenu nên bẫy này
     không còn — nhưng nếu ai đó thêm lại menu thì phải nhớ nó.
  4. So cả ảnh màn hình chờ để kiểm "đồng hồ là giờ thật" là vô nghĩa: dòng NGÀY
     cũng đổi theo giờ nên phép thử vẫn xanh dù đồng hồ đã bị hard-code. Phải so
     ĐÚNG dải đồng hồ.
  5. Dải `FRAME_Y ± 8` của hàng trạng thái CHỒNG lên dải của dòng trên (`BAR_Y ±
     8`): hộp chữ dòng 1 là 5.5–21.5, hộp chữ dòng 2 là 17–33. Đo "dòng dưới" mà
     lấy cả hộp thì bắt được cả chữ của dòng trên — và vì dòng trên dùng đúng
     `ACCENT`, phép "dòng khung hình phải biến mất" sẽ đỏ vô cớ. Đo từ `FRAME_Y`
     xuống `SCREEN_TOP` (25–33), vừa hết chồng lấn vừa không chạm màn hình.

Chạy:

    QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
        py -3.12 -u tools/validate_emulator_shell_frame.py

Chỉ dựng widget ngoài màn hình — KHÔNG mở VXPEmu, KHÔNG gửi phím thật.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "studio"))

errors: list[str] = []
notes: list[str] = []
checks = 0


def check(label: str, ok: bool) -> bool:
    global checks
    checks += 1
    if not ok:
        errors.append(label)
    return bool(ok)


def note(text: str) -> None:
    notes.append(text)


from PySide6.QtCore import QDateTime, QEvent, QPoint, QPointF, QRect, Qt  # noqa: E402
from PySide6.QtGui import QColor, QEnterEvent, QFont, QFontMetrics, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.widgets import vxp_emu_window as shell  # noqa: E402

app = QApplication.instance() or QApplication([])

SOURCE = (ROOT / "studio/app/widgets/vxp_emu_window.py").read_text(encoding="utf-8")


def _colour_distance(first: str, second: str) -> float:
    """Khoảng cách Euclid giữa hai màu `#rrggbb`.

    Có mặt vì một bẫy đã mắc thật ở bàn phím: màu hover quá gần màu nền thì nút
    "sáng lên" trong code mà không sáng lên trong ẢNH — và kiểu kiểm tra "hằng số
    còn tồn tại" không bao giờ thấy được chuyện đó.
    """
    a, b = QColor(first), QColor(second)
    return ((a.red() - b.red()) ** 2 + (a.green() - b.green()) ** 2
            + (a.blue() - b.blue()) ** 2) ** 0.5


# ------------------------------------------------------- A. hằng số thiết bị
print("-- A. hằng số thiết bị --", flush=True)

PALETTE_NAMES = (
    "BODY_TOP", "BODY_BOTTOM", "BODY_EDGE", "SCREEN_FILL", "KEY_FILL", "KEY_FILL_HOVER",
    "KEY_FILL_HELD", "KEY_EDGE", "KEY_TEXT", "KEY_SUB", "ACCENT", "READOUT_TEXT",
    "RAIL_FILL", "RAIL_EDGE", "RAIL_HOVER", "RAIL_GLYPH",
    "TIP_FILL", "TIP_EDGE", "TIP_TEXT",
    "STATUS_IDLE", "SCREEN_CLOCK", "SCREEN_DIVIDER",
)
for name in PALETTE_NAMES:
    value = getattr(shell, name, None)
    check(f"thiếu hằng màu {name}", isinstance(value, str))
    if isinstance(value, str):
        check(f"{name}={value!r} không phải màu #rrggbb",
              re.fullmatch(r"#[0-9a-fA-F]{6}", value) is not None)
        check(f"{name}={value!r} không phải màu Qt hợp lệ", QColor(value).isValid())

for name in ("BODY_WIDTH", "BODY_RADIUS", "SCREEN_TOP", "SCREEN_MARGIN", "KEYPAD_GAP",
             "KEY_W", "KEY_H", "KEY_H_NAV", "KEY_H_OK", "BODY_PAD_X",
             "RAIL_W", "RAIL_BTN", "RAIL_GAP_X", "RAIL_GAP_Y", "RAIL_PAD_Y",
             "TIP_H", "TIP_PAD_X", "TIP_GAP_X",
             "STATUS_BAR_Y", "STATUS_FRAME_Y", "TARGET_FPS"):
    check(f"thiếu hằng hình học {name}", isinstance(getattr(shell, name, None), (int, float)))

check("rail phải đủ rộng cho nút icon",
      shell.RAIL_W >= shell.RAIL_BTN + 2)
check("màu hover của rail phải XA màu nền, nếu không thì rê chuột không thấy gì",
      _colour_distance(shell.RAIL_HOVER, shell.RAIL_FILL) >= 40)
check("màu glyph của rail phải XA màu nền, nếu không thì icon vô hình",
      _colour_distance(shell.RAIL_GLYPH, shell.RAIL_FILL) >= 60)
check("chữ bong bóng phải XA nền bong bóng",
      _colour_distance(shell.TIP_TEXT, shell.TIP_FILL) >= 120)

check("bảng màu phải ghi rõ nó là màu THIẾT BỊ, không phải chrome IDE",
      "THIẾT BỊ" in SOURCE and "palette.py" in SOURCE)

# ------------------------------------------------------------- dựng widget
window = shell.VxpEmuWindow()
window.resize(window.sizeHint())
window.show()
app.processEvents()

body = window.body
stage = window.stage
keypad = body.keypad
screen = body.screen
# Toạ độ trong ảnh `stage.grab()`: thân vỏ ở (0, 0). Bản trước nó bị đẩy xuống
# `CHIP_H - CHIP_OVERLAP` px cho hai chip chờm lên đỉnh vỏ; chip đã bị thay bằng
# rail nằm BÊN PHẢI, nên `stage.width()` KHÔNG còn bằng `body.width()`.
BODY_DY = 0


def stage_image() -> QImage:
    return stage.grab().toImage()


def screen_image() -> QImage:
    return screen.grab().toImage()


def at(image: QImage, x: float, y: float) -> QColor:
    return image.pixelColor(int(round(x)), int(round(y)))


def near(a: QColor, b: QColor, tol: int = 14) -> bool:
    return (abs(a.red() - b.red()) <= tol and abs(a.green() - b.green()) <= tol
            and abs(a.blue() - b.blue()) <= tol)


def count_near(image: QImage, rect: QRect, colour: QColor, tol: int = 20) -> int:
    """Số điểm ảnh TRÙNG `colour` trong `rect`.

    Cố ý đếm "trùng màu X", không đếm "khác nền": vùng chưa được vẽ của
    `QWidget.grab()` là `#efefef`, nên phép "khác nền" tính cả vùng trống là mực
    và một bàn phím không hề vẽ vẫn xanh.
    """
    count = 0
    for y in range(rect.top(), rect.bottom() + 1):
        for x in range(rect.left(), rect.right() + 1):
            if 0 <= x < image.width() and 0 <= y < image.height():
                if near(at(image, x, y), colour, tol):
                    count += 1
    return count


# ------------------------------------------------------------- B. hình học
print("-- B. hình học --", flush=True)

check(f"màn hình phải ở ({shell.SCREEN_MARGIN}, {shell.SCREEN_TOP}) 240×320",
      screen.geometry() == QRect(shell.SCREEN_MARGIN, shell.SCREEN_TOP, 240, 320))
check(f"thân vỏ phải rộng {shell.BODY_WIDTH}", body.width() == shell.BODY_WIDTH)
check("thân vỏ phải cao đúng bằng các phần cộng lại",
      body.height() == shell.SCREEN_TOP + screen.height() + shell.KEYPAD_GAP
      + keypad.height() + shell.BODY_PAD_BOTTOM)
check("bàn phím phải đặt đúng kích thước nó khai",
      keypad.width() == shell.PhoneKeypad.KEYPAD_WIDTH
      and keypad.height() == shell.PhoneKeypad.KEYPAD_HEIGHT)
check("bàn phím không được chồng lên màn hình",
      keypad.geometry().top() >= screen.geometry().bottom() + 1)
check("bàn phím không được tràn khỏi đáy thân vỏ",
      keypad.geometry().bottom() + shell.BODY_PAD_BOTTOM <= body.height())

check("bàn phím phải có đúng 21 nút", len(keypad.buttons) == 21)
keypad_rect = QRect(0, 0, keypad.width(), keypad.height())
for button in keypad.buttons:
    name = keypad.MRE_KEY_NAMES.get(button._code, hex(button._code))
    check(f"nút {name!r} tràn khỏi bàn phím: {button.geometry()}",
          keypad_rect.contains(button.geometry()))
    check(f"nút {name!r} không mang mã MRE", isinstance(button._code, int))
for index, first in enumerate(keypad.buttons):
    for second in keypad.buttons[index + 1:]:
        check(f"nút {first._code:#x} chồng lên nút {second._code:#x}",
              not first.geometry().intersects(second.geometry()))

check("phím OK phải cao hơn các phím cùng hàng",
      shell.PhoneKeypad.ROWS[1] == shell.KEY_H_OK
      and shell.PhoneKeypad.ROWS[1] > shell.PhoneKeypad.ROWS[0])
check("tổng chiều cao các hàng phải khớp KEYPAD_HEIGHT",
      sum(shell.PhoneKeypad.ROWS) + shell.KEY_GAP_Y * (len(shell.PhoneKeypad.ROWS) - 1)
      == shell.PhoneKeypad.KEYPAD_HEIGHT)

# ------------------------------------------------- rail công cụ (bên phải)
rail = stage.rail
check("rail phải có đúng số icon như `RAIL_ITEMS` khai",
      len(rail.buttons) == len(shell.RAIL_ITEMS))
check("khoá rail phải khớp `RAIL_ITEMS`",
      tuple(rail.buttons) == tuple(key for key, _g, _t in shell.RAIL_ITEMS))
for key, glyph, title in shell.RAIL_ITEMS:
    button = rail.buttons[key]
    check(f"icon {key!r} sai glyph/tên so với khai báo",
          button.glyph == glyph and button.title == title)
    check(f"icon {key!r} không vuông {shell.RAIL_BTN}px",
          button.width() == shell.RAIL_BTN and button.height() == shell.RAIL_BTN)

rail_rect = QRect(0, 0, rail.width(), rail.height())
for key, button in rail.buttons.items():
    check(f"icon {key!r} tràn khỏi rail: {button.geometry()}",
          rail_rect.contains(button.geometry()))
for index, first in enumerate(rail.buttons.values()):
    for second in list(rail.buttons.values())[index + 1:]:
        check(f"icon {first.key!r} chồng lên icon {second.key!r}",
              not first.geometry().intersects(second.geometry()))

check("rail phải nằm BÊN PHẢI thân máy, không đè lên nó",
      rail.geometry().left() >= body.geometry().right() + 1)
check(f"khe giữa thân máy và rail phải là {shell.RAIL_GAP_X}px",
      rail.geometry().left() - body.geometry().right() - 1 == shell.RAIL_GAP_X)
check("rail phải nằm gọn trong bề ngang stage",
      rail.geometry().right() <= stage.width() - 1)
check("rail phải nằm gọn trong bề cao stage",
      rail.geometry().top() >= 0 and rail.geometry().bottom() <= stage.height() - 1)
check("rail phải được canh giữa theo chiều dọc thân máy",
      abs(rail.geometry().center().y() - body.geometry().center().y()) <= 1)
check("stage phải rộng đúng bằng thân máy + khe + rail",
      stage.width() == body.width() + shell.RAIL_GAP_X + shell.RAIL_W)
check("stage phải cao đúng bằng thân vỏ",
      stage.height() == BODY_DY + body.height())
check("thân máy phải nằm ở gốc stage (không còn chip chờm lên đỉnh)",
      body.geometry().top() == BODY_DY and body.geometry().left() == 0)

# Mọi khoá rail phải có việc. Icon không có handler là icon bấm không làm gì —
# và nếu chỉ kiểm "rail có 7 nút" thì chuyện đó lọt qua.
handlers = window._tool_handlers()
for key, _glyph, _title in shell.RAIL_ITEMS:
    check(f"icon {key!r} không có handler trong `_tool_handlers()`", key in handlers)
check("`_tool_handlers()` thừa khoá không có trên rail",
      set(handlers) <= {key for key, _g, _t in shell.RAIL_ITEMS})
_QT_WIDGETS_IMPORT = SOURCE.split("from PySide6.QtWidgets import (")[1].split(")")[0]
check("không được quay lại `QMenu` cho bảng công cụ (nó treo offscreen)",
      "QMenu" not in _QT_WIDGETS_IMPORT and "QMenu(" not in SOURCE
      and "def _open_tools_menu(" not in SOURCE)
# ⚠️ Kiểm theo LỐI DÙNG, không kiểm tên trần: ghi chú giải thích "bản trước dựng
# QMenu rồi menu.exec()" trong `_tool_handlers()` cũng chứa đúng những chữ đó, nên
# `"QMenu" not in SOURCE` bắt nhầm lời giải thích của chính nó. Cùng loại bẫy với
# `validate_no_signing.py`: guard liệt kê token cấm thì chính nó chứa token đó.

# --------------------------------------------------- C. ảnh render (1:1)
print("-- C. ảnh render --", flush=True)

image = stage_image()
check("không grab được ảnh vỏ máy", not image.isNull())
check("ảnh vỏ máy sai kích thước",
      image.width() == stage.width() and image.height() == stage.height())

# C1. Gradient DỰNG ĐỨNG.
# Ở orientation DỌC, thân vỏ 268×604 nên gradient chéo gần như trùng gradient
# dựng đứng (đường chéo bị trục y chi phối) — đo ở đây sẽ xanh vô ích. Orientation
# NGANG cho thân vỏ ~594×280, lúc đó gradient chéo lệch hẳn: hai mép cùng một
# hàng khác nhau gần trọn dải màu. Nên phép thử có răng phải chạy ở NGANG.
window.set_orientation(shell.LANDSCAPE)
app.processEvents()
wide = stage_image()
mid_y = BODY_DY + body.height() // 2
# ⚠️ Đừng lấy x=0 / x=width-1: đó là NÉT VIỀN (cùng một màu ở mọi hàng), nên
# phép "hai mép cùng hàng phải cùng màu" xanh vô điều kiện — kể cả khi gradient
# đã bị đổi sang chéo. Lấy vào trong nét viền vài px.
left = at(wide, 4, mid_y)
right = at(wide, body.width() - 5, mid_y)
check(f"gradient KHÔNG dựng đứng: trái {left.name()} vs phải {right.name()} "
      f"(cùng hàng phải cùng màu)", near(left, right, 6))
top = at(wide, 8, BODY_DY + 24)
bottom = at(wide, 8, BODY_DY + body.height() - 24)
check(f"gradient không đổi màu từ đỉnh xuống đáy: {top.name()} -> {bottom.name()}",
      not near(top, bottom, 8))
check("đỉnh thân vỏ phải sáng hơn đáy (mockup: #2a3343 -> #161d28)",
      top.red() > bottom.red() and top.blue() > bottom.blue())

# C2. Góc bo tròn. Ở góc VUÔNG thì điểm sát góc nằm ngay trên nét viền; ở góc bo
# thì nó nằm NGOÀI hình vẽ (vùng chưa tô của `grab()`).
# ⚠️ Gốc toạ độ là `PhoneStage`: góc trên-trái của THÂN VỎ là `(0, BODY_DY)`.
corner = at(wide, 1, BODY_DY + 1)
edge_mid = at(wide, 0, mid_y)
inside = at(wide, 8, mid_y)
check(f"góc vỏ không bo tròn: (1,{BODY_DY + 1})={corner.name()} trùng màu viền "
      f"{shell.BODY_EDGE}", not near(corner, QColor(shell.BODY_EDGE), 30))
# Nét viền 1.5px bị khử răng cưa nên (1,y) là màu PHA, không phải màu viền thuần
# — so tương quan thì đúng, so bằng nhau là sai.
check(f"nét viền bên hông phải sáng hơn nền thân vỏ: "
      f"viền {edge_mid.name()} vs trong {inside.name()}",
      edge_mid.red() > inside.red() + 10 and edge_mid.blue() > inside.blue() + 10)

window.set_orientation(shell.PORTRAIT)
app.processEvents()
image = stage_image()

# C3. Hàng trạng thái: TRONG thân vỏ, TRÊN màn hình, đổi màu theo kết nối.
check("hàng trạng thái phải nằm trên màn hình",
      shell.STATUS_BAR_Y + shell.STATUS_BAR_H / 2 <= shell.SCREEN_TOP)
check("dòng khung hình phải nằm trên màn hình",
      shell.STATUS_FRAME_Y + 8 <= shell.SCREEN_TOP)

# Dung sai 14: `BODY_EDGE` (#435069) chỉ lệch `STATUS_IDLE` (#5b6472) 24/20/9 —
# để dung sai 30 thì nét viền thân vỏ bị nhận nhầm thành thanh tín hiệu và phép
# đo ra một "thanh" dài 266px. Bẫy đã mắc thật.
COLOUR_TOL = 14
BAR_Y = int(round(BODY_DY + shell.STATUS_BAR_Y))
FRAME_Y = int(round(BODY_DY + shell.STATUS_FRAME_Y))


def first_run(colour: QColor, y: int) -> tuple[int, int]:
    """Đoạn LIỀN MẠCH đầu tiên trùng `colour` trên hàng `y`.

    Phải là đoạn liền mạch, không phải "điểm trùng đầu .. điểm trùng cuối": chữ
    `VXPEmu · chưa nối` cùng màu nằm ngay bên phải thanh, lấy min/max là gộp cả
    chữ vào số đo.
    """
    hits = [x for x in range(body.width()) if near(at(image, x, y), colour, COLOUR_TOL)]
    if not hits:
        return -1, -1
    start = end = hits[0]
    for x in hits[1:]:
        if x - end > 2:
            break
        end = x
    return start, end


body.set_link(False, "VXPEmu · chưa nối")
app.processEvents()
image = stage_image()
start, end = first_run(QColor(shell.STATUS_IDLE), BAR_Y)
check("không thấy thanh tín hiệu khi chưa nối", start >= 0)
check(f"thanh tín hiệu phải dài ~{shell.STATUS_BAR_W}px, đang {end - start + 1}",
      0 < (end - start + 1) <= shell.STATUS_BAR_W + 3)
check(f"thanh tín hiệu khi chưa nối phải là màu chờ {shell.STATUS_IDLE}, "
      f"đang {at(image, max(start, 0), BAR_Y).name()}",
      near(at(image, max(start, 0), BAR_Y), QColor(shell.STATUS_IDLE), 20))
check("thanh tín hiệu phải nằm nửa trái (chấm + chữ căn giữa cả cụm)",
      end < body.width() / 2)

body.set_link(True, "VXPEmu · PID 1")
app.processEvents()
image = stage_image()
start, end = first_run(QColor(shell.ACCENT), BAR_Y)
check("không thấy thanh tín hiệu khi ĐÃ nối", start >= 0)
check(f"thanh tín hiệu khi ĐÃ nối phải là màu nhấn {shell.ACCENT}, "
      f"đang {at(image, max(start, 0), BAR_Y).name()}",
      near(at(image, max(start, 0), BAR_Y), QColor(shell.ACCENT), 20))

# Hàng trạng thái phải có HAI dòng chữ được vẽ, không phải một.
accent = QColor(shell.ACCENT)
bar_band = QRect(0, BAR_Y - 8, body.width(), 16)
frame_band = QRect(0, FRAME_Y - 8, body.width(), 16)
check("dòng liên kết của hàng trạng thái không được vẽ",
      count_near(image, bar_band, accent, 40) > 20)
check("dòng khung hình của hàng trạng thái không được vẽ",
      count_near(image, frame_band, accent, 40) > 20)
check("hai dòng trạng thái phải nằm ở hai hàng khác nhau",
      abs(shell.STATUS_BAR_Y - shell.STATUS_FRAME_Y) >= 8)

# C4. Mỗi phím phải được VẼ, và phím số phải có HAI dòng chữ thật.
#
# ⚠️ Toạ độ của nút là toạ độ TRONG `PhoneKeypad`, mà `PhoneKeypad` lại nằm trong
# `PhoneBody`, mà `PhoneBody` lại bị đẩy xuống `BODY_DY` trong `PhoneStage`. Quên
# cộng lề ngang của bàn phím (17px) là lấy nhầm... nền thân vỏ, và mọi phím đều
# "không được tô nền". Dùng đúng một hàm quy đổi cho mọi phép đo.
KEYPAD_DX = keypad.geometry().left()
KEYPAD_DY = BODY_DY + keypad.geometry().top()


def keypad_rect(rect: QRect) -> QRect:
    return rect.translated(KEYPAD_DX, KEYPAD_DY)


# Cũng đừng kiểm "tỉ lệ điểm ảnh trùng nền phím" trên cả hình chữ nhật trong của
# phím: phím bo góc 10px nên bốn góc của hình chữ nhật đó nằm ngoài hình vẽ và bị
# khử răng cưa, kéo tỉ lệ xuống còn ~65-72% — ngưỡng nào cũng thành đánh đố. Lấy
# MỘT điểm chắc chắn nằm trong lòng phím, và lấy DẢI GIỮA (cách hai mép 9px, cách
# trên/dưới 4px) để đếm mực chữ — dải giữa thì không dính góc bo.
key_fill = QColor(shell.KEY_FILL)
two_line = 0
for button in keypad.buttons:
    name = keypad.MRE_KEY_NAMES.get(button._code, hex(button._code))
    geom = button.geometry()
    probe = keypad_rect(QRect(geom.left() + 7, geom.top() + geom.height() // 2, 1, 1)).topLeft()
    colour = at(image, probe.x(), probe.y())
    check(f"phím {name!r} không được tô nền phím: {probe} = {colour.name()} "
          f"phải là {shell.KEY_FILL}", near(colour, key_fill, 22))
    if not button.subtitle:
        continue
    two_line += 1
    zone = keypad_rect(QRect(geom.left() + 9, geom.top() + 4,
                             geom.width() - 18, geom.height() - 8))
    half = zone.height() // 2
    upper = QRect(zone.left(), zone.top(), zone.width(), half)
    lower = QRect(zone.left(), zone.top() + half, zone.width(), zone.height() - half)
    upper_ink = upper.width() * upper.height() - count_near(image, upper, key_fill, 22)
    lower_ink = lower.width() * lower.height() - count_near(image, lower, key_fill, 22)
    check(f"phím {name!r} không vẽ được chữ lớn (dòng trên), mực={upper_ink}",
          upper_ink > 3)
    check(f"phím {name!r} không vẽ được chữ nhỏ (dòng dưới), mực={lower_ink}",
          lower_ink > 3)
check(f"phải có 12 phím hai dòng (số + chữ cái), đang có {two_line}", two_line == 12)

# Chữ nhỏ phải NHÌN THẤY được, không chỉ "có điểm ảnh khác nền".
sub = QColor(shell.KEY_SUB)
check(f"chữ nhỏ {shell.KEY_SUB} quá gần nền phím {shell.KEY_FILL}",
      abs(sub.red() - key_fill.red()) + abs(sub.green() - key_fill.green())
      + abs(sub.blue() - key_fill.blue()) >= 90)

# C5. `#` không gửi được vào VXPEmu -> phải bị làm mờ để NHÌN thấy sự thật đó.
dimmed = {b._code for b in keypad.buttons if getattr(b, "_dim", False)}
check(f"chỉ phím `#` mới được làm mờ, đang mờ: {[hex(c) for c in sorted(dimmed)]}",
      dimmed == {0x23})

# ------------------------------------------------- D. ký tự có trong font
print("-- D. ký tự phải nằm trong cmap của Segoe UI --", flush=True)

codepoints: set[int] = set()
try:
    from app.ui.icons import _cmap_codepoints  # noqa: PLC0415

    for path in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"):
        codepoints |= _cmap_codepoints(Path(path).read_bytes())
except (ImportError, OSError) as exc:            # pragma: no cover - tuỳ máy
    note(f"SKIP kiểm cmap: {exc}")
if codepoints:
    strings: list[str] = []
    for _code, _glyph, label, subtitle, _description in shell.PhoneKeypad.KEYS:
        strings.extend([label, subtitle])
    strings.extend(list(keypad.MRE_KEY_NAMES.values()))
    # Tên phím hiện khi rê chuột — cũng là chữ được VẼ, nên cũng phải có trong
    # font. `·` (U+00B7) trong `7 · pqrs` là ký tự dễ quên nhất ở đây.
    strings.extend(button.readout for button in keypad.buttons)
    # Tên công cụ của rail cũng là chữ được VẼ (trong bong bóng khi rê chuột) —
    # `×` (U+00D7) trong "Xoay 240×320" là ký tự dễ quên nhất ở đây, y như `·`
    # của bàn phím.
    strings.extend(title for _key, _glyph, title in shell.RAIL_ITEMS)
    strings.extend(button.title for button in rail.buttons.values())
    strings.extend([
        screen.model, "Menu", "Chọn", body.link_text, body.frame_text,
        "Đang chờ VXPEmu…", "Đang khởi động VXPEmu…", "VXPEmu đã dừng",
        "Không tìm thấy cửa sổ VXPEmu",
        *[label for label, _colour in shell.ScreenHost.STATES.values()],
    ])
    missing = sorted({ch for text in strings for ch in text if ord(ch) not in codepoints})
    check(f"ký tự không có trong Segoe UI (sẽ ra ô vuông): "
          f"{[(c, hex(ord(c))) for c in missing]}", not missing)

# --------------------------------------------------------------- E. hành vi
print("-- E. hành vi --", flush=True)

# E1. `live` phải SUY RA từ `state`, không đặt rời.
screen.set_state(shell.STATE_RUNNING)
check("set_state(running) mà `live` vẫn False", screen.live is True)
screen.set_state(shell.STATE_IDLE)
check("set_state(idle) mà `live` vẫn True", screen.live is False)
screen.set_state("khong_co_trang_thai_nay")
check("state lạ phải rơi về idle",
      screen.state == shell.STATE_IDLE and screen.live is False)
app.processEvents()
idle_image = screen_image()

# E2. Đồng hồ màn hình chờ phải là GIỜ THẬT, không phải `10:30` như mockup.
#
# Không grep nguồn: docstring của `_paint_clock` CÓ nhắc `10:30` (để giải thích
# mockup vẽ số cứng) nên grep là bắt nhầm chính lời giải thích. Đóng băng đồng hồ
# ở hai thời điểm rồi so ĐÚNG DẢI ĐỒNG HỒ — so cả ảnh thì dòng NGÀY (cũng đổi
# theo giờ) làm phép thử xanh kể cả khi đồng hồ đã bị hard-code.
CLOCK_BAND = QRect(0, shell.IDLE_CLOCK_Y, 240, shell.IDLE_CLOCK_SIZE + 6)
DATE_BAND = QRect(0, shell.IDLE_DATE_Y, 240, shell.IDLE_DATE_SIZE + 5)


class _FrozenClock:
    value: QDateTime | None = None

    @classmethod
    def currentDateTime(cls) -> QDateTime:
        return cls.value


original_clock = shell.QDateTime
shell.QDateTime = _FrozenClock
try:
    _FrozenClock.value = QDateTime(2020, 1, 2, 10, 30, 0)
    first = screen_image()
    _FrozenClock.value = QDateTime(2024, 6, 7, 23, 58, 0)
    second = screen_image()
finally:
    shell.QDateTime = original_clock
check("dải ĐỒNG HỒ không đổi theo giờ hệ thống (số cứng?)",
      first.copy(CLOCK_BAND).constBits().tobytes()
      != second.copy(CLOCK_BAND).constBits().tobytes())
check("dải NGÀY không đổi theo giờ hệ thống (số cứng?)",
      first.copy(DATE_BAND).constBits().tobytes()
      != second.copy(DATE_BAND).constBits().tobytes())

# Màn hình chờ phải vẽ đủ các khối của mockup, không chỉ vài chữ ở giữa.
screen_fill = QColor(shell.SCREEN_FILL)
for label, band in (
    ("dòng trạng thái trên cùng", QRect(0, shell.IDLE_STATUS_Y, 240, 16)),
    ("đồng hồ", CLOCK_BAND),
    ("ngày", DATE_BAND),
    ("tên máy", QRect(0, shell.IDLE_MODEL_Y, 240, shell.IDLE_MODEL_SIZE + 5)),
    ("dòng trạng thái giữa", QRect(12, shell.IDLE_MESSAGE_Y, 216, 36)),
    ("dải phím mềm", QRect(0, shell.IDLE_SOFTKEY_TOP, 240, 320 - shell.IDLE_SOFTKEY_TOP)),
):
    check(f"màn hình chờ không vẽ {label}",
          count_near(idle_image, band, screen_fill, 30)
          < band.width() * band.height() - 20)

# E3. Rail phải phát tín hiệu khi bấm, kèm ĐÚNG khoá của nút.
# ⚠️ Phải dùng một `PhoneStage` RIÊNG, KHÔNG bấm rail của `window`. Lý do đã đổi
# so với bản chip: nay không còn `QMenu.exec()` (vòng lặp sự kiện LỒNG NHAU, chạy
# nền offscreen thì treo vô hạn) — nhưng `_choose_vxp` mở `QFileDialog` cũng là
# hộp thoại MODAL, và `open_capture_folder` mở trình duyệt tệp của hệ điều hành.
# Bấm thẳng rail của cửa sổ thật trong script nền sẽ treo hoặc bật cửa sổ lạ.
# Cái cần chứng minh ở đây là WIDGET phát đúng khoá; việc khoá đó có handler thì
# §B đã canh bằng `_tool_handlers()`.
probe_stage = shell.PhoneStage()
fired: list[str] = []
probe_stage.tool_requested.connect(fired.append)
for key in probe_stage.rail.buttons:
    probe_stage.rail.buttons[key].click()
app.processEvents()
check(f"rail không phát tín hiệu, nhận được {fired}",
      fired == [key for key, _g, _t in shell.RAIL_ITEMS])
check("rail phát sai thứ tự khoá",
      fired == [key for key, _g, _t in shell.RAIL_ITEMS])

# E4. Bảng công cụ cũ phải dồn vào rail, không mất chức năng nào.
check("còn sót thanh công cụ cũ (mockup không có)",
      "PhoneToolBar" not in SOURCE and "PhoneWindowBar" not in SOURCE)
check("rail chưa nối tới bộ dispatch",
      "def _run_tool(" in SOURCE
      and "self.stage.tool_requested.connect(self._run_tool)" in SOURCE)
for token in ("capture_screenshot", "open_capture_folder", "toggle_recording",
              "toggle_orientation", "toggle_fullscreen", "_choose_vxp", "_toggle_run"):
    check(f"rail mất chức năng {token}", f"self.{token}" in SOURCE)
# `_sync_rail` phải được gọi ở MỌI chỗ đổi trạng thái, nếu không icon nói dối:
# rail vẫn vẽ "play" trong khi giả lập đang chạy.
for place in ("def attach_process", "def process_stopped", "def _discard_recording",
              "def toggle_recording", "def toggle_fullscreen"):
    start = SOURCE.index(place)
    end = SOURCE.find("\n    def ", start + 1)
    chunk = SOURCE[start:end if end > 0 else len(SOURCE)]
    check(f"{place}() đổi trạng thái mà không gọi `_sync_rail()`",
          "_sync_rail()" in chunk)

# E5. Màn hình chờ không được vẽ đè lên cửa sổ VXPEmu đang chạy.
screen.set_state(shell.STATE_RUNNING)
app.processEvents()
live_image = screen_image()
check("màn hình chờ vẫn vẽ nội dung khi VXPEmu đang chạy (sẽ đè lên game)",
      count_near(live_image, live_image.rect(), QColor(shell.SCREEN_FILL), 12)
      == live_image.width() * live_image.height())
check("màn hình chờ không vẽ gì khi chưa chạy",
      count_near(idle_image, idle_image.rect(), screen_fill, 12)
      < idle_image.width() * idle_image.height() - 200)

# ------------------------------------------- F. rê chuột hiện tên phím bấm
print("-- F. rê chuột hiện tên phím --", flush=True)

# Đưa màn hình về trạng thái chờ: §E5 vừa đặt `running`, mà lúc đó cửa sổ VXPEmu
# (không có ở đây) sẽ che màn hình — không liên quan tới hàng trạng thái, nhưng
# để mọi phép đo dưới đây chạy trên cùng một ảnh nền.
screen.set_state(shell.STATE_IDLE)
body.set_link(True, "VXPEmu · PID 1")
body.set_hover("")
app.processEvents()

# ⚠️ `FRAME_Y` và `BODY_DY` đã ở hệ toạ độ ẢNH (`stage.grab()`), còn
# `shell.SCREEN_TOP` thì KHÔNG — trộn hai hệ vào nhau ra chiều cao ÂM
# (`QRect(0, 52, 268, -18)`) và mọi phép đếm trong đó trả 0. Bẫy đã mắc thật.
SCREEN_TOP_STAGE = BODY_DY + shell.SCREEN_TOP
# ⚠️ Đo CẢ HỘP CHỮ dòng dưới, không phải nửa dưới. Nửa dưới (25–33) làm `* · +`
# mất sạch mực — `*` nằm cao, `+` nằm giữa, phần dưới hộp gần như trống — nên
# "rê chuột mà không thấy chữ" đỏ vô cớ (đã mắc thật). Đo cả hộp được vì DÒNG
# TRÊN KHÔNG BAO GIỜ vẽ màu gần trắng (`ACCENT` xanh, `STATUS_IDLE` xám, đều cách
# `READOUT_TEXT` xa hơn dung sai 40), nên mực trắng trong hộp chỉ có thể là tên
# phím. Còn "dòng khung hình đã biến mất" thì so LƯỢNG mực xanh trước/sau: mực
# xanh của dòng trên là hằng số ở cả hai lần đo nên hiệu cô lập đúng dòng dưới.
FRAME_BOX = QRect(0, FRAME_Y - 8, body.width(), 16)
check(f"hộp chữ dòng dưới {FRAME_BOX} phải nằm trên màn hình",
      FRAME_BOX.bottom() < SCREEN_TOP_STAGE)

hover_colour = QColor(shell.KEY_FILL_HOVER)
normal_fill = QColor(shell.KEY_FILL)
readout_ink = QColor(shell.READOUT_TEXT)
accent_ink = QColor(shell.ACCENT)


def hover_on(button) -> None:
    """Rê chuột vào nút — gửi ĐÚNG `QEnterEvent` mà Qt gửi, nên chạy đúng
    `PhoneKey.enterEvent` thật, không phải bản viết lại."""
    QApplication.sendEvent(
        button, QEnterEvent(QPointF(5, 5), QPointF(5, 5), QPointF(5, 5)))
    app.processEvents()


def hover_off(button) -> None:
    QApplication.sendEvent(button, QEvent(QEvent.Type.Leave))
    app.processEvents()


def box_ink(colour: QColor) -> int:
    return count_near(stage_image(), FRAME_BOX, colour, 40)


# F1. Chưa rê chuột thì KHÔNG được có tên phím nào, và dòng khung hình phải còn.
check("chưa rê chuột mà đã có tên phím hiện sẵn", body.hover_text == "")
PLAIN_ACCENT = box_ink(accent_ink)
check(f"dòng khung hình phải hiện khi chưa rê chuột, mực xanh = {PLAIN_ACCENT}",
      PLAIN_ACCENT > 20)
check("chưa rê chuột mà đã có chữ sáng ở dòng dưới", box_ink(readout_ink) == 0)

# F2. MỌI phím phải có tên để hiện, và rê vào là hiện ĐÚNG tên đó.
readouts = [button.readout for button in keypad.buttons]
check(f"có phím không có tên hiện khi rê chuột: {readouts.count('')}",
      all(readouts))
check(f"tên phím bị trùng nhau: {sorted({r for r in readouts if readouts.count(r) > 1})}",
      len(set(readouts)) == len(readouts))
check("tên phím không được rỗng và không được chỉ có khoảng trắng",
      all(r.strip() == r and r for r in readouts))

for button in keypad.buttons:
    name = keypad.MRE_KEY_NAMES.get(button._code, hex(button._code))
    hover_on(button)
    check(f"rê chuột phím {name!r} mà hàng trạng thái hiện {body.hover_text!r}",
          body.hover_text == button.readout)
    white = box_ink(readout_ink)
    # Ngưỡng 10, không phải 20: tên phím NGẮN NHẤT là `* · +` — `*` và `+` là
    # nét mảnh, ở cỡ 13px chỉ ra ~17 điểm mực sáng. Ngưỡng 20 làm đúng chuỗi đó
    # đỏ vô cớ (đã mắc thật). Còn hộp KHÔNG được vẽ gì thì mực sáng = 0, nên 10
    # vẫn phân biệt được "có vẽ" với "không vẽ".
    check(f"rê chuột phím {name!r} mà không thấy chữ nào ở dòng tên phím "
          f"(mực sáng = {white})", white >= 10)
    green = box_ink(accent_ink)
    check(f"rê chuột phím {name!r} mà dòng khung hình vẫn còn vẽ "
          f"(mực xanh {green} không giảm so với {PLAIN_ACCENT})",
          green < PLAIN_ACCENT)
    hover_off(button)
    check(f"chuột ra khỏi phím {name!r} mà tên phím vẫn còn", body.hover_text == "")
    check(f"chuột ra khỏi phím {name!r} mà dòng khung hình không trở lại",
          box_ink(accent_ink) >= PLAIN_ACCENT)

# F3. Phím đang trỏ phải SÁNG lên, và chỉ phím đó.
# Dò MỘT điểm trong lòng phím (phím bo góc 10px nên bốn góc hình chữ nhật nằm
# ngoài hình vẽ — xem ghi chú ở §C4).
def key_fill_at(button) -> QColor:
    geom = button.geometry()
    probe = keypad_rect(QRect(geom.left() + 7, geom.top() + geom.height() // 2,
                              1, 1)).topLeft()
    return at(stage_image(), probe.x(), probe.y())


target = keypad.buttons[10]                    # phím số `2`
neighbour = keypad.buttons[9]                  # phím số `1` cạnh nó
check(f"nền phím lúc thường phải là {shell.KEY_FILL}, đang {key_fill_at(target).name()}",
      near(key_fill_at(target), normal_fill, 22))
hover_on(target)
hovered_fill = key_fill_at(target)
check(f"rê chuột mà phím không sáng lên: {hovered_fill.name()} "
      f"phải là {shell.KEY_FILL_HOVER}", near(hovered_fill, hover_colour, 22))
check(f"màu phím khi rê chuột {hovered_fill.name()} quá gần nền thường "
      f"{shell.KEY_FILL} nên nhìn không ra", not near(hovered_fill, normal_fill, 22))
check(f"rê chuột phím này mà phím bên cạnh cũng sáng: {key_fill_at(neighbour).name()}",
      near(key_fill_at(neighbour), normal_fill, 22))
hover_off(target)
check(f"chuột ra rồi mà phím vẫn sáng: {key_fill_at(target).name()}",
      near(key_fill_at(target), normal_fill, 22))

# F4. Chạy thẳng từ nút này sang nút kề: Qt KHÔNG bảo đảm thứ tự Enter/Leave.
# Đây là bẫy chính của tính năng này — xử lý theo cặp thì tên phím tắt ngay sau
# khi vừa bật, mà lại chỉ tắt ở một trong hai thứ tự nên rất khó thấy.
first, second = keypad.buttons[10], keypad.buttons[11]
hover_on(first)
QApplication.sendEvent(first, QEvent(QEvent.Type.Leave))     # Leave CŨ tới trước
hover_on(second)
check(f"Enter(nút mới) sau Leave(nút cũ) mà tên phím sai: {body.hover_text!r}",
      body.hover_text == second.readout)
hover_off(second)
check("Leave(nút mới) mà tên phím không tắt", body.hover_text == "")

hover_on(first)
hover_on(second)                                             # Enter MỚI tới trước
hover_off(first)                                             # rồi mới Leave CŨ
check(f"Enter(nút mới) TRƯỚC Leave(nút cũ) mà tên phím bị xoá oan: "
      f"{body.hover_text!r}", body.hover_text == second.readout)
hover_off(second)
check("chuột ra khỏi cả hai nút mà tên phím vẫn còn", body.hover_text == "")

# F5. Nút bị ẩn lúc đang rê chuột thì tên phím phải tắt, không được KẸT lại:
# `hideEvent` là đường duy nhất dọn được, vì `leaveEvent` không tới nữa.
hover_on(first)
keypad.hide()
app.processEvents()
check(f"ẩn bàn phím lúc đang rê chuột mà tên phím kẹt lại: {body.hover_text!r}",
      body.hover_text == "")
keypad.show()
app.processEvents()

# ------------------------------------- G. rê chuột lên icon rail -> hiện tên
print("-- G. rê chuột lên icon rail --", flush=True)

tip = stage.tip
TIP_FONT = QFontMetrics(shell._ui_font(shell.TIP_TEXT_SIZE, QFont.Weight.Bold))


def tip_ink() -> int:
    return count_near(stage_image(), tip.geometry(), QColor(shell.TIP_TEXT), 40)


# G1. Chưa rê chuột thì không được có bong bóng nào.
check("chưa rê chuột mà bong bóng đã hiện", not tip.isVisible())
check(f"chưa rê chuột mà bong bóng còn chữ {tip.text()!r}", tip.text() == "")

# G2. Mọi icon phải có tên riêng, và rê vào là hiện ĐÚNG tên đó.
titles = [button.title for button in rail.buttons.values()]
check(f"icon rail không có tên: {titles.count('')}", all(titles))
check(f"tên công cụ bị trùng nhau: "
      f"{sorted({t for t in titles if titles.count(t) > 1})}",
      len(set(titles)) == len(titles))

for key, button in rail.buttons.items():
    hover_on(button)
    check(f"rê chuột icon {key!r} mà bong bóng không hiện", tip.isVisible())
    check(f"rê chuột icon {key!r} mà bong bóng hiện {tip.text()!r}",
          tip.text() == button.title)

    # Vị trí: bong bóng phải nằm NGAY BÊN TRÁI nút đang trỏ và canh giữa theo nút.
    # ⚠️ Đây là chỗ bẫy hệ toạ độ đã mắc thật: `button.y()` là toạ độ TRONG rail,
    # còn bong bóng đặt bằng toạ độ TRONG stage — lệch nhau đúng `rail.y()`, và
    # bong bóng hiện cao hơn nút ~175px mà không có lỗi nào cả.
    centre = button.geometry().center()
    centre_in_stage = QPoint(rail.geometry().left() + centre.x(),
                             rail.geometry().top() + centre.y())
    check(f"bong bóng của {key!r} lệch dọc so với nút "
          f"({tip.geometry().center().y()} vs {centre_in_stage.y()})",
          abs(tip.geometry().center().y() - centre_in_stage.y()) <= 1)
    check(f"bong bóng của {key!r} không nằm bên trái rail "
          f"(right={tip.geometry().right()}, rail.left={rail.geometry().left()})",
          tip.geometry().right() < rail.geometry().left())
    check(f"bong bóng của {key!r} cách rail quá xa",
          rail.geometry().left() - tip.geometry().right() - 1 <= shell.TIP_GAP_X + 1)
    check(f"bong bóng của {key!r} tràn khỏi stage: {tip.geometry()}",
          stage.rect().contains(tip.geometry()))

    # Nội dung: bề rộng mực phải khớp bề rộng chữ của ĐÚNG tên đó. Chỉ đếm "có
    # mực" thì một bong bóng vẽ nhầm tên vẫn xanh.
    ink = tip_ink()
    expected = TIP_FONT.horizontalAdvance(button.title)
    check(f"bong bóng {key!r} không vẽ chữ nào (mực = {ink})", ink >= 10)
    check(f"bong bóng {key!r} rộng {tip.width()} nhưng chữ "
          f"{button.title!r} cần {expected + 2 * shell.TIP_PAD_X}",
          tip.width() == expected + 2 * shell.TIP_PAD_X)

    hover_off(button)
    check(f"chuột ra khỏi icon {key!r} mà bong bóng vẫn còn", not tip.isVisible())

# G3. Bong bóng KHÔNG được chặn chuột lên thân máy nằm dưới nó.
# Đây là lý do `RailTip` phải là widget LÁ và mang `WA_TransparentForMouseEvents`:
# nó vẽ đè lên thân máy, chỗ có bàn phím và màn hình cần bấm.
hover_on(rail.buttons["record"])
tip_centre = tip.geometry().center()
check("bong bóng không mang WA_TransparentForMouseEvents",
      tip.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))
# ⚠️ Đo bằng `childAt` chứ không tin mỗi cái attribute: attribute có thể bị đặt
# lên nhầm widget. Đã đo thật: `childAt` TÔN TRỌNG cờ này (trả về `ScreenHost`,
# không phải `RailTip`) nên phép kiểm này có nghĩa.
under = stage.childAt(tip_centre)
check(f"bong bóng chặn chuột: widget dưới nó là {type(under).__name__}",
      under is not None and under is not tip)
check("không có widget nào dưới bong bóng (chỗ đó phải bấm được)",
      under is not None)
hover_off(rail.buttons["record"])

# G4. Chạy thẳng từ icon này sang icon kề: thứ tự Enter/Leave không được bảo đảm.
# Cùng bẫy như bàn phím ở §F4, nhưng ở rail thì bong bóng SAI VỊ TRÍ chứ không chỉ
# sai chữ, nên càng khó thấy.
first, second = rail.buttons["load"], rail.buttons["shot"]
hover_on(first)
QApplication.sendEvent(first, QEvent(QEvent.Type.Leave))     # Leave CŨ tới trước
hover_on(second)
check(f"Enter(icon mới) sau Leave(icon cũ) mà bong bóng sai: {tip.text()!r}",
      tip.isVisible() and tip.text() == second.title)
hover_off(second)
check("Leave(icon mới) mà bong bóng không tắt", not tip.isVisible())

hover_on(first)
hover_on(second)                                        # Enter MỚI tới trước
hover_off(first)                                        # rồi mới Leave CŨ
check(f"Enter(icon mới) TRƯỚC Leave(icon cũ) mà bong bóng bị xoá oan: "
      f"{tip.text()!r}", tip.isVisible() and tip.text() == second.title)
hover_off(second)
check("chuột ra khỏi cả hai icon mà bong bóng vẫn còn", not tip.isVisible())

# G5. Icon bị ẩn lúc đang rê chuột thì bong bóng phải tắt, không được KẸT lại.
hover_on(first)
rail.hide()
app.processEvents()
check(f"ẩn rail lúc đang rê chuột mà bong bóng kẹt lại: {tip.text()!r}",
      not tip.isVisible())
rail.show()
app.processEvents()

# G6. Icon đang bật phải có viền accent, và chỉ icon đó.
def rail_accent_ink(button) -> int:
    """Số điểm ảnh màu accent trong ô của icon.

    ⚠️ Đếm CẢ Ô, không dò một điểm. Viền chỉ dày 1px và `drawRoundedRect` vẽ nó
    lệch nửa điểm ảnh, nên `at(left + 1, giữa)` trả về màu NỀN và phép kiểm đỏ oan
    (đã mắc thật ngay lần đầu viết mục này). Đo được: bật ⇒ 88 điểm, tắt ⇒ 0.
    """
    geom = button.geometry()
    box = QRect(rail.geometry().left() + geom.left(), rail.geometry().top() + geom.top(),
                geom.width(), geom.height())
    return count_near(stage_image(), box, QColor(shell.ACCENT), 60)


rail.set_active("record", True)
app.processEvents()
check(f"icon đang bật không có viền accent (mực accent = "
      f"{rail_accent_ink(rail.buttons['record'])})",
      rail_accent_ink(rail.buttons["record"]) >= 40)
check(f"icon không bật cũng có viền accent (mực accent = "
      f"{rail_accent_ink(rail.buttons['shot'])})",
      rail_accent_ink(rail.buttons["shot"]) == 0)
rail.set_active("record", False)
app.processEvents()
check("tắt active rồi mà viền accent vẫn còn",
      rail_accent_ink(rail.buttons["record"]) == 0)

if notes:
    for text in notes:
        print("  " + text, flush=True)

if errors:
    print("FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print(f"PASS: {checks} phép kiểm — vỏ máy vẽ đúng mockup (gradient dựng đứng, "
      f"góc bo, hàng trạng thái hai dòng, bàn phím hai dòng)")
print("PASS: mọi ký tự trên vỏ máy có trong cmap của Segoe UI (không ô vuông)")
print("PASS: `live` suy ra từ `state`, đồng hồ là giờ thật, mọi khoá rail có handler")
print("PASS: rê chuột lên phím hiện tên phím ở hàng trạng thái, phím sáng lên, "
      "tắt đúng khi chuột ra")
print("PASS: rail icon bên phải chỉ có icon; rê chuột hiện đúng tên ở bong bóng "
      "đúng vị trí, và bong bóng không chặn chuột lên thân máy")
