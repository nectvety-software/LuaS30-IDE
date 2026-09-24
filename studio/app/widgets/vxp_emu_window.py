"""Vỏ Nokia 225 Dual SIM host cửa sổ framebuffer thật của VXPEmu.

Cấu trúc theo VXPEngine (app/widgets/vxpemu_window.py): VXPEmu.exe vẫn là lõi
chạy game; widget này chỉ tìm cửa sổ chính của nó theo PID, nhúng vào màn
hình 240×320/320×240 bằng Win32 SetParent và gửi phím MRE qua WM_KEYDOWN.

Ngoại hình bám theo mockup "classic dark": thân gradient DỰNG ĐỨNG, hàng trạng
thái xanh ngay trên màn hình, màn hình chờ có đồng hồ thật, và bàn phím 21 phím
kiểu viên thuốc hai dòng (số lớn + chữ cái nhỏ bên dưới).

**Rail công cụ bên phải** (kiểu LDPlayer) thay cho hai chip `MENU`/`Shot` chờm
trên đỉnh vỏ ở bản trước: rail dọc chỉ có ICON, rê chuột lên icon thì hiện tên
công cụ ở bong bóng ngay cạnh rail. Đây là phần DUY NHẤT của vỏ máy không lấy số
đo từ mockup — mockup không có rail — nên nó được chốt bởi validator chứ không
bởi ảnh.

Rê chuột lên một phím thì **tên phím** (tên Lua trong `doc/ai/Keypad.md` §0,
ví dụ `up`, `softleft`, `7 · pqrs`) hiện ra ở dòng dưới của hàng trạng thái,
và phím đó sáng lên. Cố ý vẽ NGAY TRÊN VỎ MÁY chứ không phụ thuộc tooltip của
hệ điều hành: tooltip là cửa sổ của OS (chậm ~700ms, có thể bị cửa sổ khác che,
và không kiểm chứng được offscreen), còn hàng trạng thái thì luôn nhìn thấy —
kể cả khi VXPEmu đang chạy chiếm màn hình. Tooltip vẫn giữ, để có thêm phần mô
tả dài. Bong bóng tên công cụ của rail cũng theo đúng lý do đó.

⚠️ Bảng màu ở đây là màu **THIẾT BỊ**, không phải màu IDE — cố ý không đi qua
`ui/palette.py` (giống `items.C_ACCENT` của game). Mọi số đo lấy trực tiếp từ
mockup 576×1288, mà mockup đó đúng **2×** vỏ thật (màn hình của nó 480×640 =
2× framebuffer 240×320), nên các hằng số dưới đây là px THẬT.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from PySide6.QtCore import (
    QDateTime, QLocale, QProcess, QRectF, QSize, QStandardPaths, Qt, QTimer, QUrl, Signal,
)
from PySide6.QtGui import (
    QBrush, QColor, QDesktopServices, QFont, QFontMetrics, QGuiApplication, QLinearGradient,
    QPainter, QPen,
)
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from app.core import native_window
from app.ui.icons import font_icon

PORTRAIT = "portrait"
LANDSCAPE = "landscape"
SCREEN_SIZE = {PORTRAIT: (240, 320), LANDSCAPE: (320, 240)}

# Khung hình mục tiêu của runtime LuaS30 — mọi `conf.lua` trong `templates/`
# đều khai `fps = 15` (`templates/basic/conf.lua`, `keypad-demo`, …). Đây là
# CON SỐ MỤC TIÊU, không phải FPS đo được: app không đo FPS ở đâu cả, nên đừng
# biến hàng trạng thái thành lời nói dối bằng cách bịa một số đo.
TARGET_FPS = 15

# ------------------------------------------------------------------ bảng màu
# Lấy mẫu bằng chế độ (màu phổ biến nhất) trên từng vùng của mockup, KHÔNG lấy
# một điểm ảnh đơn lẻ — điểm đơn lẻ hay trúng nét chữ.
BODY_TOP = "#2a3343"          # đỉnh thân vỏ
BODY_BOTTOM = "#161d28"       # đáy thân vỏ
BODY_EDGE = "#435069"         # viền thân vỏ
SCREEN_FILL = "#090d14"       # nền framebuffer khi chưa chạy
KEY_FILL = "#34445d"          # nền phím
KEY_FILL_HOVER = "#3f5580"    # nền phím khi RÊ CHUỘT — màu SUY RA, không lấy từ mockup
KEY_FILL_HELD = "#4e6c96"     # nền phím đang giữ
KEY_EDGE = "#506685"          # viền phím
KEY_TEXT = "#ffffff"          # chữ lớn trên phím (số, OK)
KEY_SUB = "#9aa6b8"           # chữ nhỏ dưới số (abc, def, …)
ACCENT = "#65dc96"            # xanh lá của mockup (rail đang bật, hàng trạng thái)
# Chữ sáng của dòng đọc tên (tên phím / tên công cụ). Trước đây tên là `CHIP_TEXT`
# vì nó thuộc về hai chip; chip đã bị thay bằng rail nên đổi tên cho khỏi nói dối.
READOUT_TEXT = "#f1f5fb"
STATUS_IDLE = "#5b6472"       # thanh tín hiệu khi CHƯA nối được VXPEmu
SCREEN_TEXT = "#c8d0d8"
SCREEN_CLOCK = "#e8eef4"
SCREEN_DATE = "#bdc5cc"
SCREEN_MODEL = "#b5bcc4"
SCREEN_MESSAGE = "#858c93"
SCREEN_DIVIDER = "#2a2d33"
SCREEN_SOFTKEY = "#d8e0e8"

# ------------------------------------------------------------- hình học vỏ
BODY_WIDTH = 268
BODY_RADIUS = 18
BODY_EDGE_W = 1.5
#: Lề ngang của chữ trong hàng trạng thái. Trước đây mượn `CHIP_PAD_X` của hai
#: chip chờm trên đỉnh vỏ — chip đã bị thay bằng rail nên đây mới là nhà đúng.
BODY_PAD_X = 11
SCREEN_MARGIN = 14            # lề hai bên của màn hình trong thân vỏ
SCREEN_TOP = 34               # đỉnh vỏ -> đỉnh màn hình (chứa hàng trạng thái)
KEYPAD_GAP = 12               # màn hình -> bàn phím
BODY_PAD_BOTTOM = 6

KEY_W = 76
KEY_H = 30                    # phím số
KEY_H_NAV = 26                # phím điều hướng
KEY_H_OK = 36                 # phím OK — cao hơn hai hàng cạnh nó
KEY_GAP_X = 3
KEY_GAP_Y = 4
KEY_RADIUS = 10
KEY_GLYPH_SIZE = 17
KEY_LABEL_SIZE = 14
KEY_SUB_SIZE = 9

# ------------------------------------------------------------- rail công cụ
# ⚠️ Mockup gốc KHÔNG có rail — đây là yêu cầu trực tiếp của người dùng (chuyển
# menu sang phải kiểu LDPlayer). Nên các số dưới đây là số CHỌN, không phải số ĐO
# từ mockup như phần còn lại của file: chúng được chốt bởi
# `tools/validate_emulator_shell_frame.py`, không bởi ảnh.
RAIL_W = 34                   # bề ngang rail
RAIL_BTN = 30                 # cạnh nút icon (vuông)
RAIL_GAP_X = 8                # khe giữa thân máy và rail
RAIL_GAP_Y = 4                # khe giữa hai nút
RAIL_PAD_Y = 10               # lề trên/dưới trong rail
RAIL_RADIUS = 8               # thang bo góc đã chốt của IDE: 6/8/10/12
RAIL_ICON = 16
RAIL_FILL = "#161d28"         # = BODY_BOTTOM: rail đọc như một panel tách khỏi vỏ
RAIL_EDGE = "#435069"         # = BODY_EDGE
RAIL_HOVER = "#2a3343"        # = BODY_TOP — phải XA RAIL_FILL, xem guard trong validator
RAIL_GLYPH = "#9aa6b8"        # = KEY_SUB
TIP_H = 24
TIP_PAD_X = 8
TIP_GAP_X = 6                 # khe giữa bong bóng và rail
TIP_RADIUS = 6
TIP_FILL = "#0f1620"
TIP_EDGE = "#435069"
TIP_TEXT = "#f1f5fb"
TIP_TEXT_SIZE = 12

#: Icon trên rail, theo thứ tự từ trên xuống: `(khoá, glyph, tên hiện khi rê chuột)`.
#: Khoá là hợp đồng với `VxpEmuWindow._tool_handlers()` — thiếu handler thì icon
#: đó bấm không làm gì, và validator canh đúng chuyện đó.
RAIL_ITEMS = (
    ("run", "play", "Chạy VXP đang mở"),
    ("load", "folder", "Nạp tệp .vxp khác…"),
    ("shot", "image", "Chụp màn hình"),
    ("folder", "folder_open", "Mở thư mục ảnh / video"),
    ("record", "circle", "Quay video"),
    ("rotate", "rotate", "Xoay 240×320 / 320×240"),
    ("fullscreen", "expand", "Toàn màn hình"),
)

STATUS_BAR_W = 15
STATUS_BAR_H = 5
STATUS_BAR_Y = 13.5           # tâm thanh tín hiệu, tính từ đỉnh vỏ
STATUS_FRAME_Y = 25           # tâm dòng "240x320 · 15 FPS"
STATUS_GAP = 7
STATUS_TEXT_SIZE = 13

# Màn hình chờ (chỉ hiện khi VXPEmu chưa được nhúng).
IDLE_TEXT_PAD = 10
IDLE_STATUS_Y = 8
IDLE_CLOCK_Y = 52
IDLE_CLOCK_SIZE = 34
IDLE_DATE_Y = 88
IDLE_DATE_SIZE = 14
IDLE_MODEL_Y = 166
IDLE_MODEL_SIZE = 13
IDLE_MESSAGE_Y = 190
IDLE_SOFTKEY_TOP = 292
IDLE_SOFTKEY_SIZE = 13
IDLE_TEXT_SIZE = 13

# Trạng thái màn hình chờ. Một nguồn cho cả nhãn lẫn màu, để `state` và `live`
# không thể lệch nhau.
STATE_IDLE = "idle"
STATE_STARTING = "starting"
STATE_RUNNING = "running"
STATE_STOPPED = "stopped"

# Bàn phím thật → mã MRE. Đây là bản sao **đúng** bảng mặc định của VXPEmu
# (`KeyboardMapping::loadDefaults`, `src/ui/KeyboardMapping.cpp`), nên gõ trên
# bàn phím thật trong shell cho ra y hệt cửa sổ VXPEmu gốc.
_QT_TO_MRE = {
    **{int(getattr(Qt.Key, f"Key_{n}")): 0x30 + n for n in range(10)},
    int(Qt.Key.Key_Asterisk): 0x2A,
    # `#` giữ trong bảng để phản ánh ĐÚNG bảng mặc định của VXPEmu, nhưng không
    # gửi được qua cửa sổ — xem `native_window.MRE_KEYS_NOT_INJECTABLE`.
    int(Qt.Key.Key_NumberSign): 0x23,
    int(Qt.Key.Key_Up): native_window.MRE_KEY_UP,
    int(Qt.Key.Key_Down): native_window.MRE_KEY_DOWN,
    int(Qt.Key.Key_Left): native_window.MRE_KEY_LEFT,
    int(Qt.Key.Key_Right): native_window.MRE_KEY_RIGHT,
    int(Qt.Key.Key_Return): native_window.MRE_KEY_OK,
    int(Qt.Key.Key_Slash): native_window.MRE_KEY_LEFT_SOFT,
    int(Qt.Key.Key_Shift): native_window.MRE_KEY_RIGHT_SOFT,
    int(Qt.Key.Key_Escape): native_window.MRE_KEY_BACK,
    int(Qt.Key.Key_Backspace): native_window.MRE_KEY_CLEAR,
}


def _ui_font(size_px: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """Font theo **pixel**, không theo point.

    Mọi số đo của mockup là pixel thật, mà `QFont(family, 8)` lại là 8 *point*
    (≈ 10.7 px ở 96 dpi) — dùng point thì không thể đối chiếu với mockup được.
    """
    font = QFont("Segoe UI")
    font.setPixelSize(int(size_px))
    font.setWeight(weight)
    return font


class ScreenHost(QWidget):
    """Khung 240×320 nhúng cửa sổ VXPEmu — và là màn hình chờ khi chưa chạy.

    Khi VXPEmu đã được nhúng (`live`) widget này bị cửa sổ con che hoàn toàn nên
    `paintEvent` thoát sớm. Màn hình chờ vì thế chỉ là thứ hiện ra trước khi chạy
    và sau khi dừng — nhưng đó lại là thứ người dùng nhìn thấy nhiều nhất.
    """

    STATES = {
        STATE_IDLE: ("chờ", "#8a9199"),
        STATE_STARTING: ("khởi động", "#e0b36a"),
        STATE_RUNNING: ("chạy", ACCENT),
        STATE_STOPPED: ("dừng", "#e0b36a"),
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, True)
        self.setFixedSize(240, 320)
        self.message = "Đang chờ VXPEmu…"
        self.name = "VXPEmu"
        self.model = "NOKIA 225 DUAL SIM"
        self.state = STATE_IDLE
        self.live = False
        # Đồng hồ chỉ đánh thức khi KHÔNG live: lúc live widget bị che nên vẽ vô ích.
        self._clock = QTimer(self)
        self._clock.setInterval(20000)
        self._clock.timeout.connect(self._tick)
        self._clock.start()

    def _tick(self) -> None:
        if not self.live:
            self.update()

    def set_state(self, state: str, message: str = "") -> None:
        """Đổi trạng thái màn hình chờ.

        `live` được SUY RA từ `state` chứ không đặt rời: hai cờ cùng nói một
        chuyện thì sớm muộn cũng lệch, và lệch ở đây nghĩa là vẽ đè lên cửa sổ
        VXPEmu đang chạy (hoặc không vẽ gì dù chưa có gì để xem).
        """
        self.state = state if state in self.STATES else STATE_IDLE
        self.live = self.state == STATE_RUNNING
        if message:
            self.message = message
        self.update()

    # ------------------------------------------------------------- vẽ
    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(SCREEN_FILL))
        if self.live:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_status_bar(painter)
        self._paint_clock(painter)
        self._paint_identity(painter)
        self._paint_softkeys(painter)

    def _paint_status_bar(self, painter: QPainter) -> None:
        """Dòng trên cùng: tên tệp .vxp đang nạp (trái) + nhãn trạng thái (phải).

        Mockup ghi `4G VoLTE` + vạch sóng — đó là chrome của chiếc điện thoại.
        App không có dữ liệu sóng, nên chỗ này hiện thứ THẬT: tệp nào đang nạp
        và giả lập đang ở trạng thái nào.
        """
        label, colour = self.STATES.get(self.state, self.STATES[STATE_IDLE])
        font = _ui_font(IDLE_TEXT_SIZE)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        painter.setPen(QColor(SCREEN_TEXT))
        painter.drawText(QRectF(IDLE_TEXT_PAD, IDLE_STATUS_Y, 150, 16),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         metrics.elidedText(self.name, Qt.TextElideMode.ElideMiddle, 150))
        painter.setPen(QColor(colour))
        painter.drawText(QRectF(self.width() - IDLE_TEXT_PAD - 90, IDLE_STATUS_Y, 90, 16),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, label)

    def _paint_clock(self, painter: QPainter) -> None:
        """Đồng hồ thật của máy — mockup vẽ `10:30` / `Mon 12 May` là số cứng."""
        now = QDateTime.currentDateTime()
        painter.setPen(QColor(SCREEN_CLOCK))
        painter.setFont(_ui_font(IDLE_CLOCK_SIZE, QFont.Weight.Bold))
        painter.drawText(QRectF(0, IDLE_CLOCK_Y, self.width(), IDLE_CLOCK_SIZE + 6),
                         Qt.AlignmentFlag.AlignCenter, now.toString("HH:mm"))
        painter.setPen(QColor(SCREEN_DATE))
        painter.setFont(_ui_font(IDLE_DATE_SIZE))
        painter.drawText(QRectF(0, IDLE_DATE_Y, self.width(), IDLE_DATE_SIZE + 5),
                         Qt.AlignmentFlag.AlignCenter,
                         QLocale.system().toString(now, "ddd dd MMM"))

    def _paint_identity(self, painter: QPainter) -> None:
        model_font = _ui_font(IDLE_MODEL_SIZE)
        model_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        painter.setPen(QColor(SCREEN_MODEL))
        painter.setFont(model_font)
        painter.drawText(QRectF(0, IDLE_MODEL_Y, self.width(), IDLE_MODEL_SIZE + 5),
                         Qt.AlignmentFlag.AlignCenter, self.model)
        painter.setPen(QColor(SCREEN_MESSAGE))
        painter.setFont(_ui_font(IDLE_TEXT_SIZE))
        painter.drawText(QRectF(12, IDLE_MESSAGE_Y, self.width() - 24, 36),
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
                         | Qt.TextFlag.TextWordWrap, self.message)

    def _paint_softkeys(self, painter: QPainter) -> None:
        """Dải phím mềm — CHỈ có trên màn hình chờ.

        Nó không thuộc framebuffer: khi VXPEmu chạy, màn hình là game vẽ. Đây chỉ
        là hình vẽ lại hai phím mềm của máy để người dùng biết nút nào làm gì.
        """
        painter.setPen(QPen(QColor(SCREEN_DIVIDER), 1))
        painter.drawLine(IDLE_TEXT_PAD, IDLE_SOFTKEY_TOP,
                         self.width() - IDLE_TEXT_PAD, IDLE_SOFTKEY_TOP)
        painter.setPen(QColor(SCREEN_SOFTKEY))
        painter.setFont(_ui_font(IDLE_SOFTKEY_SIZE, QFont.Weight.DemiBold))
        row = QRectF(IDLE_TEXT_PAD, IDLE_SOFTKEY_TOP + 6,
                     self.width() - 2 * IDLE_TEXT_PAD, 16)
        painter.drawText(row, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Menu")
        painter.drawText(row, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, "Chọn")


class PhoneKey(QPushButton):
    """Một nút trên vỏ máy — GIỮ được, không chỉ bấm nhả.

    Bản cũ nối thẳng `clicked`, nên mỗi lần bấm là một cặp down+up tức thời:
    app không bao giờ thấy trạng thái "đang giữ". Hợp đồng phím
    (`doc/ai/Keypad.md` §2.1) bắt buộc có cặp pressed/released, và bảng `held`
    của `templates/keypad-demo/src/keypad.lua` chỉ đúng khi phím được giữ thật —
    nên điều hướng kiểu "giữ để chạy" không thể hoạt động qua đường `clicked`.

    Nút tự vẽ (`paintEvent`) để có hai dòng chữ như mockup: số lớn ở trên, chữ
    cái nhỏ ở dưới. QSS không vẽ nữa, nhưng `objectName` vẫn là `PhoneKey` để
    rule `QPushButton#PhoneKey` trong `theme.py` còn nghĩa.
    """

    pressed_code = Signal(int)
    released_code = Signal(int)
    # `(nút, vừa-vào=True / vừa-ra=False)`. Gửi kèm chính nút chứ không chỉ mã,
    # vì bên nhận phải so danh tính để chịu được thứ tự Enter/Leave không bảo đảm.
    hover_changed = Signal(object, bool)

    def __init__(self, code: int, glyph: str, label: str, subtitle: str, tip: str,
                 readout: str, parent=None) -> None:
        super().__init__("", parent)     # text rỗng: toàn bộ chữ do paintEvent vẽ
        self._code = int(code)
        self._held = False
        self._hover = False
        self.glyph = glyph
        self.label = label
        self.subtitle = subtitle
        # Chuỗi hiện ở hàng trạng thái khi rê chuột: TÊN phím, kèm chữ nhỏ nếu có
        # (`7 · pqrs`). Khác tooltip: tooltip có cả phần mô tả dài.
        self.readout = readout
        self.setObjectName("PhoneKey")
        # Không nhận focus: nếu không, phím mũi tên bị Qt dùng để chuyển focus
        # giữa các nút và Space/Enter bị QPushButton ăn mất — bàn phím thật của
        # người dùng sẽ không tới được cửa sổ giả lập.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._icon = font_icon(glyph, KEY_GLYPH_SIZE, KEY_TEXT) if glyph else None
        # `#` không gửi được vào VXPEmu (`native_window.MRE_KEYS_NOT_INJECTABLE`).
        # Làm mờ chữ của nút đó để sự thật ấy NHÌN THẤY được, thay vì chỉ nằm
        # trong tooltip.
        self._dim = not native_window.is_injectable(self._code)
        if tip:
            self.setToolTip(tip)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._held:
            self._held = True
            self.setDown(True)
            self.pressed_code.emit(self._code)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.release_held()
        super().mouseReleaseEvent(event)

    def enterEvent(self, event) -> None:
        """Rê chuột vào nút -> sáng nút + báo tên nút cho vỏ máy.

        `QPushButton` không tự dùng `enterEvent` (nó dùng `QEvent::HoverEnter`
        qua `WA_Hover`), nên ghi đè ở đây không phá gì — mà đó cũng là lý do phải
        ghi đè: không có `WA_Hover` thì Qt không phát `HoverEnter` cho ta.
        """
        self._hover = True
        self.update()
        self.hover_changed.emit(self, True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        self.hover_changed.emit(self, False)
        super().leaveEvent(event)

    def hideEvent(self, event) -> None:
        # Nút bị ẩn giữa chừng thì không còn nhận được mouseReleaseEvent nữa.
        self.release_held()
        # Cùng lý do với `_hover`: ẩn lúc đang rê chuột thì `leaveEvent` không tới,
        # nên tên phím sẽ KẸT lại trên hàng trạng thái mãi mãi.
        if self._hover:
            self._hover = False
            self.hover_changed.emit(self, False)
        super().hideEvent(event)

    def release_held(self) -> None:
        if self._held:
            self._held = False
            self.setDown(False)
            self.released_code.emit(self._code)

    def is_held(self) -> bool:
        return self._held

    def is_hovered(self) -> bool:
        return self._hover

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if self._held:
            fill = KEY_FILL_HELD
        elif self._hover:
            fill = KEY_FILL_HOVER
        else:
            fill = KEY_FILL
        painter.setPen(QPen(QColor(KEY_EDGE), 1))
        painter.setBrush(QColor(fill))
        painter.drawRoundedRect(rect, KEY_RADIUS, KEY_RADIUS)
        if self._dim:
            painter.setOpacity(0.45)
        if self._icon is not None:
            offset = (self.height() - KEY_GLYPH_SIZE) // 2
            self._icon.paint(painter, int((self.width() - KEY_GLYPH_SIZE) / 2), offset,
                             KEY_GLYPH_SIZE, KEY_GLYPH_SIZE)
            return
        painter.setPen(QColor(KEY_TEXT))
        if self.subtitle:
            painter.setFont(_ui_font(KEY_LABEL_SIZE, QFont.Weight.Bold))
            painter.drawText(QRectF(0, 3, self.width(), KEY_LABEL_SIZE + 4),
                             Qt.AlignmentFlag.AlignCenter, self.label)
            painter.setPen(QColor(KEY_SUB))
            painter.setFont(_ui_font(KEY_SUB_SIZE))
            painter.drawText(QRectF(0, self.height() - KEY_SUB_SIZE - 5, self.width(),
                                    KEY_SUB_SIZE + 3),
                             Qt.AlignmentFlag.AlignCenter, self.subtitle)
        else:
            painter.setFont(_ui_font(KEY_LABEL_SIZE, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.label)


class PhoneKeypad(QWidget):
    key_pressed = Signal(int)
    key_released = Signal(int)
    # Chuỗi hiện ở hàng trạng thái khi rê chuột; "" = không trỏ vào phím nào.
    hover_changed = Signal(str)

    # Tên phím Lua cho từng mã MRE — ĐÚNG 21 phím của hợp đồng `doc/ai/Keypad.md`
    # §0 (runtime chỉ gửi tên chữ thường qua `engine.keypressed`/`keyreleased`).
    # Đây là nguồn duy nhất ở phía shell: tooltip của mọi nút lấy tên từ đây.
    MRE_KEY_NAMES = {
        native_window.MRE_KEY_UP: "up",
        native_window.MRE_KEY_DOWN: "down",
        native_window.MRE_KEY_LEFT: "left",
        native_window.MRE_KEY_RIGHT: "right",
        native_window.MRE_KEY_OK: "ok",
        native_window.MRE_KEY_LEFT_SOFT: "softleft",
        native_window.MRE_KEY_RIGHT_SOFT: "softright",
        native_window.MRE_KEY_BACK: "back",
        native_window.MRE_KEY_CLEAR: "clear",
        **{0x30 + n: str(n) for n in range(10)},
        0x2A: "*",
        0x23: "#",
    }

    # Bố cục 3 cột × 7 hàng = ĐÚNG 21 phím, theo mockup: cụm điều hướng 3 hàng
    # (OK cao hơn hai hàng cạnh nó, `down` nằm ngay dưới OK), rồi 4 hàng số.
    # Mỗi mục: (mã MRE, glyph, chữ lớn, chữ nhỏ, mô tả cách dùng).
    #
    # `back`/`clear` dùng CHỮ chứ không dùng glyph: glyph `back` của bộ icon là
    # một mũi tên trái, đứng cạnh `left` (cũng mũi tên trái) thì không ai phân
    # biệt được nút nào là nút nào — mà đây là nút để bấm, không phải để đọc.
    #
    # Chữ nhỏ dưới số phải là ký tự ASCII hoặc ký tự Segoe UI CÓ THẬT: `∞`
    # (U+221E) và `–` (U+2013) thì có, còn `⇧` (U+21E7) KHÔNG — nó chỉ nằm
    # trong Segoe UI Symbol, nên vẽ bằng Segoe UI là ra ô vuông mà không báo lỗi.
    # `Aa` là cách viết shift bằng ASCII. `tools/validate_emulator_shell_frame.py`
    # đọc thẳng cmap của segoeui.ttf để canh đúng chuyện này.
    KEYS = (
        (native_window.MRE_KEY_LEFT_SOFT, "menu", "", "", "mở menu / tuỳ chọn"),
        (native_window.MRE_KEY_UP, "arrow_up", "", "", "đi lên / chọn mục phía trên (dự phòng: 2)"),
        (native_window.MRE_KEY_RIGHT_SOFT, "close", "", "", "quay lại / huỷ thao tác"),
        (native_window.MRE_KEY_LEFT, "arrow_left", "", "", "sang trái / giảm chỉ số (dự phòng: 4)"),
        (native_window.MRE_KEY_OK, "", "OK", "", "xác nhận / hành động chính (dự phòng: 5)"),
        (native_window.MRE_KEY_RIGHT, "arrow_right", "", "", "sang phải / tăng chỉ số (dự phòng: 6)"),
        (native_window.MRE_KEY_BACK, "", "Back", "", "thoát màn hình hiện tại về menu"),
        (native_window.MRE_KEY_DOWN, "arrow_down", "", "", "đi xuống / chọn mục phía dưới (dự phòng: 8)"),
        (native_window.MRE_KEY_CLEAR, "", "Clear", "", "xoá một ký tự / huỷ nhập liệu"),
        (0x31, "", "1", "∞", "phím số"),
        (0x32, "", "2", "abc", "phím số"),
        (0x33, "", "3", "def", "phím số"),
        (0x34, "", "4", "ghi", "phím số"),
        (0x35, "", "5", "jkl", "phím số"),
        (0x36, "", "6", "mno", "phím số"),
        (0x37, "", "7", "pqrs", "phím số"),
        (0x38, "", "8", "tuv", "phím số"),
        (0x39, "", "9", "wxyz", "phím số"),
        (0x2A, "", "*", "+", "tạm dừng / bật HUD / đổi kiểu nhập"),
        (0x30, "", "0", "–", "nhập số 0"),
        (0x23, "", "#", "Aa", "xoá hết ký tự nhập / bật tắt âm — CHỈ trên máy thật, "
                             "VXPEmu không nhận được phím này"),
    )

    # Chiều cao từng hàng (hàng 1 = OK). Tổng + 6 khe = 232 px, khớp mockup.
    ROWS = (KEY_H_NAV, KEY_H_OK, KEY_H_NAV, KEY_H, KEY_H, KEY_H, KEY_H)
    KEYPAD_WIDTH = KEY_W * 3 + KEY_GAP_X * 2
    KEYPAD_HEIGHT = sum(ROWS) + KEY_GAP_Y * (len(ROWS) - 1)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.buttons: list[PhoneKey] = []
        self._hovered: PhoneKey | None = None
        for code, glyph, label, subtitle, description in self.KEYS:
            name = self.MRE_KEY_NAMES.get(code, "?")
            # Tên hiện khi rê chuột: chỉ tên phím, thêm chữ nhỏ nếu phím có
            # (`7 · pqrs`). Phần mô tả dài để cho tooltip.
            readout = f"{name} · {subtitle}" if subtitle else name
            # `parent=self` là BẮT BUỘC: nút được đặt bằng `setGeometry` chứ không
            # qua layout, mà `setGeometry` KHÔNG tự nhận cha — thiếu tham số này
            # thì 21 nút thành cửa sổ rời và bàn phím trống trơn, không lỗi gì.
            button = PhoneKey(code, glyph, label, subtitle,
                              f"{name} — {description}", readout, self)
            button.pressed_code.connect(self.key_pressed.emit)
            button.released_code.connect(self.key_released.emit)
            button.hover_changed.connect(self._on_key_hover)
            self.buttons.append(button)
        self._relayout()

    def _on_key_hover(self, button: PhoneKey, entered: bool) -> None:
        """Rê chuột vào/ra một phím -> phát tên phím cho vỏ máy.

        ⚠️ KHÔNG xử lý theo cặp "Enter thì bật, Leave thì tắt". Thứ tự Enter/Leave
        khi chuột chạy từ nút này sang nút kề bên KHÔNG được Qt bảo đảm: nếu
        `Leave(nút cũ)` tới SAU `Enter(nút mới)` thì cách xử lý theo cặp vừa bật
        tên nút mới xong đã tắt ngay ⇒ tên phím nhấp nháy hoặc mất hẳn. Ở đây chỉ
        ghi nhớ nút MỚI NHẤT được Enter, và chỉ xoá khi CHÍNH nút đang nhớ phát
        Leave — đúng với cả hai thứ tự.
        """
        if entered:
            self._hovered = button
        elif self._hovered is button:
            self._hovered = None
        self.hover_changed.emit(self._hovered.readout if self._hovered else "")

    def _relayout(self) -> None:
        """Đặt 21 nút theo lưới 3 cột, mỗi hàng một chiều cao.

        Đặt tay thay vì `QGridLayout`: hàng OK vừa có phím cao 36 vừa có phím
        cao 26, mà grid layout chỉ biết một chiều cao cho cả hàng.
        """
        tops: list[int] = []
        offset = 0
        for height in self.ROWS:
            tops.append(offset)
            offset += height + KEY_GAP_Y
        for index, button in enumerate(self.buttons):
            row, column = divmod(index, 3)
            button.setGeometry(column * (KEY_W + KEY_GAP_X), tops[row], KEY_W, self.ROWS[row])
        self.setFixedSize(self.KEYPAD_WIDTH, self.KEYPAD_HEIGHT)

    def key_for(self, code: int) -> PhoneKey | None:
        for button in self.buttons:
            if button._code == code:
                return button
        return None

    def held_codes(self) -> list[int]:
        return [button._code for button in self.buttons if button.is_held()]

    def release_all(self) -> None:
        """Nhả mọi phím đang giữ — dùng khi mất focus/đóng cửa sổ/dừng giả lập.

        Thiếu bước này, một phím đang giữ lúc cửa sổ đóng sẽ **kẹt vĩnh viễn**
        trong app: không bao giờ có `keyreleased` tương ứng.
        """
        for button in list(self.buttons):
            button.release_held()


class PhoneBody(QWidget):
    """Thân máy: hàng trạng thái + màn hình + bàn phím, trên nền gradient."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.orientation = PORTRAIT
        self.screen = ScreenHost(self)
        self.keypad = PhoneKeypad(self)
        self.link_live = False
        self.link_text = "VXPEmu · chưa nối"
        self.frame_text = f"240×320 · {TARGET_FPS} FPS"
        # Tên phím đang được rê chuột ("" = không trỏ vào phím nào).
        self.hover_text = ""
        self.set_orientation(PORTRAIT)

    def set_hover(self, text: str) -> None:
        """Hiện tên phím đang rê chuột ở dòng dưới hàng trạng thái.

        Dòng đó vốn hiện `240x320 · 15 FPS`; khi rê chuột thì nó NHƯỜNG CHỖ cho
        tên phím rồi tự trả lại khi chuột ra. Chỉ `update()` khi chuỗi ĐỔI: hàm
        này bị gọi mỗi lần chuột qua một nút, vẽ lại vô ích thì bàn phím 21 nút
        nhấp nháy theo.
        """
        text = text or ""
        if text != self.hover_text:
            self.hover_text = text
            self.update()

    def set_link(self, live: bool, text: str = "") -> None:
        """Trạng thái "đã nối được cửa sổ VXPEmu" — thanh xanh ở hàng trạng thái."""
        self.link_live = bool(live)
        if text:
            self.link_text = str(text)
        self.update()

    def set_orientation(self, orientation: str) -> None:
        self.orientation = orientation if orientation in SCREEN_SIZE else PORTRAIT
        sw, sh = SCREEN_SIZE[self.orientation]
        self.screen.setFixedSize(sw, sh)
        if self.orientation == PORTRAIT:
            width = BODY_WIDTH
            height = SCREEN_TOP + sh + KEYPAD_GAP + self.keypad.height() + BODY_PAD_BOTTOM
            self.screen.setGeometry(SCREEN_MARGIN, SCREEN_TOP, sw, sh)
            self.keypad.setGeometry((width - self.keypad.width()) // 2,
                                    SCREEN_TOP + sh + KEYPAD_GAP,
                                    self.keypad.width(), self.keypad.height())
        else:
            width = SCREEN_MARGIN + sw + KEYPAD_GAP + self.keypad.width() + SCREEN_MARGIN
            height = SCREEN_TOP + max(sh, self.keypad.height()) + BODY_PAD_BOTTOM
            self.screen.setGeometry(SCREEN_MARGIN, SCREEN_TOP, sw, sh)
            self.keypad.setGeometry(SCREEN_MARGIN + sw + KEYPAD_GAP,
                                    SCREEN_TOP + (max(sh, self.keypad.height())
                                                  - self.keypad.height()) // 2,
                                    self.keypad.width(), self.keypad.height())
        # Dòng thứ hai của hàng trạng thái là số THẬT: kích thước framebuffer
        # hiện tại + FPS mục tiêu. Xoay máy là nó đổi theo.
        self.frame_text = f"{sw}×{sh} · {TARGET_FPS} FPS"
        self.setFixedSize(width, height)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        inset = BODY_EDGE_W / 2
        rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        # Gradient DỰNG ĐỨNG (mockup: #2a3343 ở đỉnh -> #161d28 ở đáy), không
        # phải chéo như bản cũ.
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.0, QColor(BODY_TOP))
        gradient.setColorAt(1.0, QColor(BODY_BOTTOM))
        painter.setPen(QPen(QColor(BODY_EDGE), BODY_EDGE_W))
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(rect, BODY_RADIUS, BODY_RADIUS)
        self._paint_status(painter)

    def _paint_status(self, painter: QPainter) -> None:
        """Hàng trạng thái trong thân vỏ, ngay trên màn hình.

        Mockup ghi `WiFi · 1.0Gbps` và `56 FPS`. App KHÔNG có nguồn cho hai số
        đó (không chỗ nào trong `EmulatorService` đo FPS, cũng không có dữ liệu
        mạng), nên chỗ này hiện thông tin THẬT: thanh xanh = đã nối được cửa sổ
        VXPEmu, dòng dưới = kích thước khung hình + FPS mục tiêu của runtime.
        """
        colour = ACCENT if self.link_live else STATUS_IDLE
        font = _ui_font(STATUS_TEXT_SIZE, QFont.Weight.DemiBold)
        metrics = QFontMetrics(font)
        text = metrics.elidedText(self.link_text, Qt.TextElideMode.ElideRight,
                                  self.width() - 2 * BODY_PAD_X - STATUS_BAR_W - STATUS_GAP)
        text_width = metrics.horizontalAdvance(text)
        left = (self.width() - (STATUS_BAR_W + STATUS_GAP + text_width)) / 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(colour))
        painter.drawRoundedRect(QRectF(left, STATUS_BAR_Y - STATUS_BAR_H / 2,
                                       STATUS_BAR_W, STATUS_BAR_H),
                                STATUS_BAR_H / 2, STATUS_BAR_H / 2)
        painter.setPen(QColor(colour))
        painter.setFont(font)
        painter.drawText(QRectF(left + STATUS_BAR_W + STATUS_GAP, STATUS_BAR_Y - 8,
                                text_width, 16),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        # Dòng dưới: tên phím đang rê chuột (màu sáng) hay thông số khung hình
        # (màu nhấn). Màu khác nhau là cố ý — nếu cùng màu thì người dùng không
        # biết dòng đó vừa đổi nội dung.
        if self.hover_text:
            painter.setPen(QColor(READOUT_TEXT))
            painter.setFont(_ui_font(STATUS_TEXT_SIZE, QFont.Weight.Bold))
            painter.drawText(QRectF(0, STATUS_FRAME_Y - 8, self.width(), 16),
                             Qt.AlignmentFlag.AlignCenter, self.hover_text)
        else:
            painter.setPen(QColor(ACCENT))
            painter.setFont(_ui_font(STATUS_TEXT_SIZE, QFont.Weight.DemiBold))
            painter.drawText(QRectF(0, STATUS_FRAME_Y - 8, self.width(), 16),
                             Qt.AlignmentFlag.AlignCenter, self.frame_text)


class PhoneRailButton(QPushButton):
    """Một icon trên rail công cụ — **chỉ icon**, tên hiện khi rê chuột.

    Bản trước là hai chip `MENU`/`Shot` in tên mình ngay trên mặt chip, nên tài
    liệu cũ ghi "hai chip cố ý KHÔNG tham gia readout: hiện lại tên là lặp vô
    ích". Rail bỏ chữ khỏi mặt nút, nên phần hiện tên trở thành **bắt buộc**:
    không có nó thì không ai đoán được icon nào là việc gì. Đây chính là chỗ mà
    ghi chú cũ nói "nếu sau này muốn thống nhất thì thêm `hover_changed`".

    Nút tự vẽ, và `objectName` là `PhoneRailButton` để rule QSS trong `theme.py`
    còn nghĩa (cùng lý do như `PhoneKey`).
    """

    activated = Signal(str)
    # `(nút, vừa-vào=True / vừa-ra=False)`. Gửi kèm chính nút chứ không chỉ khoá,
    # vì bên nhận phải so danh tính để chịu được thứ tự Enter/Leave không bảo đảm.
    hover_changed = Signal(object, bool)

    def __init__(self, key: str, glyph: str, title: str, parent=None) -> None:
        super().__init__("", parent)     # text rỗng: toàn bộ hình do paintEvent vẽ
        self.key = key
        self.glyph = glyph
        self.title = title
        self._hover = False
        self._active = False
        self.setObjectName("PhoneRailButton")
        # NoFocus cùng lý do như `PhoneKey`: phím mũi tên phải tới cửa sổ giả lập.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(RAIL_BTN, RAIL_BTN)
        self.setToolTip(title)
        self._icon = font_icon(glyph, RAIL_ICON, RAIL_GLYPH)
        self.clicked.connect(lambda: self.activated.emit(self.key))

    def set_item(self, glyph: str, title: str) -> None:
        """Đổi icon + tên theo trạng thái (chạy↔dừng, quay↔dừng quay, …)."""
        self.glyph = glyph
        self.title = title
        self._icon = font_icon(glyph, RAIL_ICON, RAIL_GLYPH)
        self.setToolTip(title)
        self.update()

    def set_active(self, active: bool) -> None:
        """Viền accent khi công cụ đó đang bật (đang chạy, đang quay, toàn màn hình)."""
        self._active = bool(active)
        self.update()

    def enterEvent(self, event) -> None:
        # `QPushButton` không tự dùng `enterEvent` (nó dùng `QEvent::HoverEnter`
        # qua `WA_Hover`), nên ghi đè ở đây không phá gì — mà đó cũng là lý do
        # phải ghi đè: không có `WA_Hover` thì Qt không phát `HoverEnter` cho ta.
        self._hover = True
        self.update()
        self.hover_changed.emit(self, True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        self.hover_changed.emit(self, False)
        super().leaveEvent(event)

    def hideEvent(self, event) -> None:
        """Ẩn nút thì phải DỌN hover, nếu không bong bóng kẹt vĩnh viễn trên màn hình.

        Cùng loại bẫy như tên phím kẹt ở hàng trạng thái khi bàn phím bị ẩn:
        `Leave` không tới khi widget biến mất.
        """
        self._hover = False
        self.hover_changed.emit(self, False)
        super().hideEvent(event)

    def is_hovered(self) -> bool:
        return self._hover

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        edge = ACCENT if self._active else RAIL_EDGE
        painter.setPen(QPen(QColor(edge), 1))
        painter.setBrush(QColor(RAIL_HOVER if self._hover else RAIL_FILL))
        painter.drawRoundedRect(rect, RAIL_RADIUS, RAIL_RADIUS)
        if self._icon is not None:
            self._icon.paint(painter, (self.width() - RAIL_ICON) // 2,
                             (self.height() - RAIL_ICON) // 2, RAIL_ICON, RAIL_ICON)


class ToolRail(QWidget):
    """Rail icon dọc: `RAIL_ITEMS` từ trên xuống, chỉ icon.

    Rail tự khai bề rộng/cao theo các hằng số, nên `PhoneStage` chỉ việc `move()`.
    """

    triggered = Signal(str)
    #: `(tên hiện khi rê chuột, tâm Y của nút TÍNH THEO `PhoneStage`)`. Tên rỗng = đã rời hết.
    #: ⚠️ Phải quy về hệ toạ độ của `PhoneStage`, không phải hệ của rail: bên nhận
    #: đặt bong bóng bằng toạ độ stage, nên `button.y()` trần sẽ lệch đúng bằng
    #: `rail.y()` (đã mắc — bong bóng hiện cao hơn nút ~175px mà không có lỗi nào).
    hover_changed = Signal(str, int)

    def __init__(self, items, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ToolRail")
        self.buttons: dict[str, PhoneRailButton] = {}
        self._current: PhoneRailButton | None = None
        y = RAIL_PAD_Y
        for key, glyph, title in items:
            button = PhoneRailButton(key, glyph, title, self)
            button.move((RAIL_W - RAIL_BTN) // 2, y)
            button.activated.connect(self.triggered)
            button.hover_changed.connect(self._on_hover)
            self.buttons[key] = button
            y += RAIL_BTN + RAIL_GAP_Y
        self.setFixedSize(RAIL_W, y - RAIL_GAP_Y + RAIL_PAD_Y)

    def _on_hover(self, button: PhoneRailButton, entered: bool) -> None:
        """Nhớ nút MỚI NHẤT được Enter, đừng xử lý theo cặp.

        Thứ tự `Enter`/`Leave` giữa hai nút kề nhau **không được Qt bảo đảm**. Nếu
        xử lý theo cặp thì ở một trong hai thứ tự, bong bóng tắt ngay sau khi vừa
        bật — lỗi chỉ hiện ở MỘT thứ tự nên rất khó thấy.
        """
        if entered:
            self._current = button
            # Cộng `self.y()` để trả về hệ toạ độ `PhoneStage` — xem ghi chú ở signal.
            self.hover_changed.emit(button.title,
                                    self.y() + button.y() + button.height() // 2)
        elif button is self._current:
            self._current = None
            self.hover_changed.emit("", 0)

    def set_item(self, key: str, glyph: str, title: str) -> None:
        self.buttons[key].set_item(glyph, title)

    def set_active(self, key: str, active: bool) -> None:
        self.buttons[key].set_active(active)


class RailTip(QWidget):
    """Bong bóng tên công cụ, vẽ ngay bên trái rail khi rê chuột.

    Cố ý KHÔNG dùng `QToolTip`: tooltip là cửa sổ của OS, và **không kiểm chứng
    được offscreen** (`QTest.mouseMove` + `QToolTip.isVisible()` luôn trả "không
    hiện", kể cả với `QPushButton` thường — đã chạy đối chứng). Xây tính năng dựa
    vào thứ không đo được thì không guard nào bảo vệ nó.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # ⚠️ Bong bóng nằm ĐÈ lên thân máy, mà thân máy có bàn phím cần bấm.
        # `WA_TransparentForMouseEvents` làm trong suốt với chuột CẢ widget này
        # lẫn con của nó — nên nó bắt buộc phải là widget LÁ, không được chứa nút.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._text = ""
        self.setFixedHeight(TIP_H)

    def setText(self, text: str) -> None:
        self._text = text
        metrics = QFontMetrics(_ui_font(TIP_TEXT_SIZE, QFont.Weight.Bold))
        self.setFixedWidth(TIP_PAD_X * 2 + metrics.horizontalAdvance(text))
        self.update()

    def text(self) -> str:
        return self._text

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor(TIP_EDGE), 1))
        painter.setBrush(QColor(TIP_FILL))
        painter.drawRoundedRect(rect, TIP_RADIUS, TIP_RADIUS)
        painter.setPen(QColor(TIP_TEXT))
        painter.setFont(_ui_font(TIP_TEXT_SIZE, QFont.Weight.Bold))
        painter.drawText(self.rect(),
                         Qt.AlignmentFlag.AlignCenter, self._text)


class PhoneStage(QWidget):
    """Sân khấu: thân máy + rail công cụ bên phải + bong bóng tên công cụ.

    Rail và bong bóng đều nằm NGOÀI khung `PhoneBody` nên không thể là con của
    nó — phải có một widget cha rộng hơn. Đó là toàn bộ lý do lớp này tồn tại.

    Thân máy giờ ở `(0, 0)`: bản trước nó bị đẩy xuống `CHIP_H - CHIP_OVERLAP` px
    để nhường chỗ cho hai chip chờm lên đỉnh vỏ, và **mọi toạ độ trong ảnh
    `stage.grab()` đều lệch theo con số đó**.
    """

    tool_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.body = PhoneBody(self)
        self.rail = ToolRail(RAIL_ITEMS, self)
        # Tạo SAU `body` để vẽ ĐÈ lên trên: widget cùng cha thì thứ tự tạo quyết
        # định thứ tự chồng.
        self.tip = RailTip(self)
        self.tip.hide()
        self.rail.triggered.connect(self.tool_requested)
        self.rail.hover_changed.connect(self._on_rail_hover)
        self._relayout()

    def _on_rail_hover(self, title: str, centre_y: int) -> None:
        if not title:
            self.tip.hide()
            return
        self.tip.setText(title)
        # Đặt bên TRÁI rail, tức đè lên mép phải thân máy — giống LDPlayer. Kẹp
        # `max(0, …)` vì con không vẽ được ra ngoài cha, chữ dài sẽ bị cắt cụt.
        self.tip.move(max(0, self.rail.x() - TIP_GAP_X - self.tip.width()),
                      max(0, centre_y - TIP_H // 2))
        self.tip.show()
        self.tip.raise_()

    def set_orientation(self, orientation: str) -> None:
        self.body.set_orientation(orientation)
        self._relayout()

    def _relayout(self) -> None:
        body = self.body
        body.move(0, 0)
        self.rail.move(body.width() + RAIL_GAP_X,
                       max(0, (body.height() - self.rail.height()) // 2))
        self.setFixedSize(body.width() + RAIL_GAP_X + RAIL_W, body.height())
        # Đổi hướng/đổi kích thước thì bong bóng đang trỏ vào toạ độ cũ.
        if self.tip.isVisible():
            self.tip.hide()


class VxpEmuWindow(QWidget):
    """Cửa sổ điện thoại riêng; process VXPEmu do EmulatorService quản lý."""

    restart_requested = Signal()
    stop_requested = Signal()
    load_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Nokia 225 Dual SIM — VXPEmu")
        self.setObjectName("VxpEmuPhoneWindow")
        self._pid = 0
        self._hwnd: int | None = None
        self._attempts = 0
        self._artifact = ""
        self._closing_for_shutdown = False
        self._held_keys: set[int] = set()
        self._record_dir: Path | None = None
        self._record_frame = 0
        self._record_output: Path | None = None
        self._encoder: QProcess | None = None
        self._attach_timer = QTimer(self)
        self._attach_timer.setInterval(300)
        self._attach_timer.timeout.connect(self._try_attach)
        self._fit_timer = QTimer(self)
        self._fit_timer.setInterval(400)
        self._fit_timer.timeout.connect(self._fit)
        self._record_timer = QTimer(self)
        self._record_timer.setInterval(100)
        self._record_timer.timeout.connect(self._capture_record_frame)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        stage_row = QWidget()
        stage_layout = QVBoxLayout(stage_row)
        stage_layout.setContentsMargins(16, 8, 16, 4)
        self.stage = PhoneStage()
        # `body` giữ lại như thuộc tính công khai: `window.body.keypad` là đường
        # mà `tools/validate_keypad_emulation.py` (và mọi script kiểm thử) dùng.
        self.body = self.stage.body
        stage_layout.addWidget(self.stage, 0, Qt.AlignmentFlag.AlignCenter)
        root.addWidget(stage_row)
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 2, 10, 8)
        # ⚠️ Câu gợi ý này QUYẾT ĐỊNH bề ngang cửa sổ (`_fit_shell` lấy
        # `sizeHint()`, mà nhãn QLabel không tự co). Dài thêm ~34 ký tự là cửa sổ
        # phình từ 632 lên 829px — vỏ máy 268px nằm lọt thỏm giữa một khung rộng.
        # Muốn thêm chữ thì phải bỏ chữ khác.
        hint = QLabel("Rail phải: icon công cụ · rê chuột để xem tên · "
                      "GIỮ phím được; nhận cả bàn phím thật")
        hint.setStyleSheet("color:#7788a2")
        self.status = QLabel("Chưa chạy")
        self.status.setStyleSheet("color:#91a6c5")
        footer_layout.addWidget(hint, 1)
        footer_layout.addWidget(self.status)
        root.addWidget(footer)

        self.stage.tool_requested.connect(self._run_tool)
        self.body.keypad.key_pressed.connect(self.send_key_down)
        self.body.keypad.key_released.connect(self.send_key_up)
        # Rê chuột lên phím -> tên phím hiện ở hàng trạng thái của vỏ máy.
        self.body.keypad.hover_changed.connect(self.body.set_hover)
        self.setStyleSheet("#VxpEmuPhoneWindow { background:#0d121b; color:#dce7f7; }")
        self._sync_rail()
        self._fit_shell()

    @property
    def running(self) -> bool:
        return self._pid > 0

    def attach_process(self, artifact: str, pid: int) -> None:
        self._pid, self._hwnd, self._attempts = int(pid), None, 0
        self._artifact = str(artifact)
        self.body.screen.name = Path(artifact).name
        self.body.screen.set_state(STATE_STARTING, "Đang khởi động VXPEmu…")
        self.body.set_link(False, f"VXPEmu · PID {pid}")
        self.status.setText(f"{Path(artifact).name} · PID {pid}")
        self.show()
        self.raise_()
        self.activateWindow()
        self._attach_timer.start()
        self._sync_rail()

    def _try_attach(self) -> None:
        self._attempts += 1
        hwnd = native_window.find_main_window(self._pid)
        if hwnd and native_window.embed(hwnd, int(self.body.screen.winId()),
                                        self.body.screen.width(), self.body.screen.height()):
            self._hwnd = hwnd
            self._attach_timer.stop()
            self._fit_timer.start()
            self.body.screen.set_state(STATE_RUNNING)
            self.body.set_link(True, f"VXPEmu · PID {self._pid}")
            self.status.setText(f"Đang chạy · {self.body.screen.width()}×{self.body.screen.height()}")
        elif self._attempts >= 50:
            self._attach_timer.stop()
            self.body.screen.set_state(STATE_STOPPED, "Không tìm thấy cửa sổ VXPEmu")
            self.status.setText("Không tìm thấy cửa sổ VXPEmu")

    def toggle_orientation(self) -> None:
        self.set_orientation(LANDSCAPE if self.body.orientation == PORTRAIT else PORTRAIT)

    def set_orientation(self, orientation: str) -> None:
        self.stage.set_orientation(orientation)
        if not self.isFullScreen():
            self._fit_shell()
        self._fit()
        if self._pid:
            self.status.setText(
                f"Đang chạy · {self.body.screen.width()}×{self.body.screen.height()}"
            )

    def _fit_shell(self) -> None:
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        self.stage.updateGeometry()
        self.layout().invalidate()
        self.layout().activate()
        self.setFixedSize(self.sizeHint())

    def _fit(self) -> None:
        if not self._hwnd:
            return
        if not native_window.is_alive(self._hwnd):
            self.process_stopped(-1)
            return
        native_window.fit(
            self._hwnd,
            self.body.screen.width(),
            self.body.screen.height(),
            int(self.body.screen.winId()),
        )

    # ------------------------------------------------------------ rail công cụ
    def _tool_handlers(self) -> dict:
        """Khoá rail -> việc cần làm. MỘT nguồn cho cả dispatch lẫn validator.

        Bản trước là `_open_tools_menu()` dựng `QMenu` rồi `menu.exec()`. Bỏ được
        `QMenu` là bỏ luôn một bẫy: `QMenu.exec()` mở vòng lặp sự kiện **LỒNG
        NHAU**, nên validator offscreen bấm vào chip MENU sẽ treo im lặng.
        """
        return {
            "run": self._toggle_run,
            "load": self._choose_vxp,
            "shot": self.capture_screenshot,
            "folder": self.open_capture_folder,
            "record": self.toggle_recording,
            "rotate": self.toggle_orientation,
            "fullscreen": self.toggle_fullscreen,
        }

    def _run_tool(self, key: str) -> None:
        handler = self._tool_handlers().get(key)
        if handler is None:
            # Không im lặng: icon không có việc thì phải NHÌN THẤY là nó không có việc.
            self.status.setText(f"Chưa gán việc cho icon {key!r}")
            return
        handler()

    def _sync_rail(self) -> None:
        """Đồng bộ icon/tên/viền theo trạng thái thật.

        Icon chỉ đổi hình khi trạng thái đổi, nên phải gọi hàm này ở MỌI chỗ đổi
        trạng thái — bỏ sót một chỗ là rail nói dối (ví dụ vẫn vẽ "play" trong khi
        giả lập đang chạy).
        """
        rail = self.stage.rail
        running = bool(self._pid)
        rail.set_item("run", "stop" if running else "play",
                      "Dừng giả lập" if running else "Chạy VXP đang mở")
        rail.set_active("run", running)
        recording = self._record_timer.isActive()
        rail.set_item("record", "stop" if recording else "circle",
                      "Dừng quay video" if recording else "Quay video")
        rail.set_active("record", recording)
        full = self.isFullScreen()
        rail.set_item("fullscreen", "collapse" if full else "expand",
                      "Thoát toàn màn hình" if full else "Toàn màn hình")
        rail.set_active("fullscreen", full)

    def _toggle_run(self) -> None:
        if self._pid:
            self.stop_requested.emit()
        else:
            self.restart_requested.emit()

    def _choose_vxp(self) -> None:
        start = Path(self._artifact).parent if self._artifact else Path.home()
        selected, ok = QFileDialog.getOpenFileName(
            self, "Nạp ứng dụng VXP", str(start), "Ứng dụng MRE VXP (*.vxp)"
        )
        if ok and selected:
            self.load_requested.emit(selected)

    @staticmethod
    def capture_directory() -> Path:
        pictures = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
        target = Path(pictures or str(Path.home() / "Pictures")) / "LuaS30" / "VXPEmu"
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _grab_screen(self):
        screen = self.body.screen.screen() or QGuiApplication.primaryScreen()
        return screen.grabWindow(int(self.body.screen.winId())) if screen is not None else None

    def capture_screenshot(self) -> None:
        stamp = QDateTime.currentDateTime().toString("yyyyMMdd-HHmmss")
        output = self.capture_directory() / f"VXPEmu-{stamp}.png"
        if self.capture_to_file(output):
            self.status.setText(f"Đã chụp · {output.name}")
        else:
            self.status.setText("Không chụp được màn hình VXPEmu")

    def capture_to_file(self, output: Path) -> bool:
        """Chụp đúng vùng framebuffer VXPEmu đang embed và lưu PNG; trả về True nếu ghi được."""
        pixmap = self._grab_screen()
        if pixmap is None or pixmap.isNull():
            return False
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            return bool(pixmap.save(str(output), "PNG"))
        except OSError:
            return False

    def open_capture_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.capture_directory())))

    def toggle_recording(self) -> None:
        if self._record_timer.isActive():
            self._stop_recording()
            return
        if not self._hwnd:
            self.status.setText("Hãy chạy VXP trước khi quay")
            return
        if shutil.which("ffmpeg") is None:
            self.status.setText("Không tìm thấy ffmpeg để quay video")
            return
        self._record_dir = Path(tempfile.mkdtemp(prefix="luas30-vxpemu-record-"))
        self._record_frame = 0
        stamp = QDateTime.currentDateTime().toString("yyyyMMdd-HHmmss")
        self._record_output = self.capture_directory() / f"VXPEmu-{stamp}.mp4"
        self._record_timer.start()
        self.status.setText("Đang quay · 10 FPS")
        self._sync_rail()

    def _capture_record_frame(self) -> None:
        if self._record_dir is None:
            return
        pixmap = self._grab_screen()
        if pixmap is None or pixmap.isNull():
            return
        self._record_frame += 1
        pixmap.save(str(self._record_dir / f"frame-{self._record_frame:06d}.png"), "PNG")

    def _stop_recording(self) -> None:
        self._record_timer.stop()
        if self._record_dir is None or self._record_output is None or self._record_frame == 0:
            self._discard_recording()
            return
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            self._discard_recording()
            return
        self.status.setText("Đang lưu video…")
        encoder = QProcess(self)
        encoder.setProgram(str(ffmpeg))
        encoder.setArguments([
            "-y", "-framerate", "10", "-i", str(self._record_dir / "frame-%06d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(self._record_output),
        ])
        encoder.finished.connect(self._recording_encoded)
        self._encoder = encoder
        encoder.start()

    def _recording_encoded(self, code: int, _status) -> None:
        output = self._record_output
        ok = code == 0 and output is not None and output.is_file()
        self._discard_recording()
        self.status.setText(f"Đã lưu · {output.name}" if ok and output else "Lưu video thất bại")

    def _discard_recording(self) -> None:
        if self._record_dir is not None:
            shutil.rmtree(self._record_dir, ignore_errors=True)
        self._record_dir = None
        self._record_output = None
        self._record_frame = 0
        self._encoder = None
        # Mọi đường thoát của việc quay đều đi qua đây, nên đồng bộ rail ở đây là
        # chỗ duy nhất không thể bỏ sót.
        self._sync_rail()

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self._fit_shell()
        else:
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.showFullScreen()
        self._sync_rail()

    # ------------------------------------------------------------ gửi phím MRE
    def send_key_down(self, code: int) -> None:
        """Giữ một phím MRE xuống; trạng thái giữ được theo dõi để luôn nhả được."""
        if not self._hwnd or code in self._held_keys:
            return
        self._held_keys.add(code)
        native_window.send_key_down(self._hwnd, code)

    def send_key_up(self, code: int) -> None:
        if code not in self._held_keys:
            return
        self._held_keys.discard(code)
        if self._hwnd:
            native_window.send_key_up(self._hwnd, code)

    def release_all_keys(self) -> None:
        """Nhả mọi phím đang giữ (nút trên vỏ máy + bàn phím thật).

        Không có bước này, phím đang giữ lúc cửa sổ mất focus/đóng lại sẽ kẹt
        trong app: nó không bao giờ nhận được `keyreleased` tương ứng, nên bảng
        `held` phía Lua ở lại `true` vĩnh viễn (nhân vật chạy mãi một hướng).
        """
        self.body.keypad.release_all()   # nút đang bị giữ -> phát `released_code`
        for code in sorted(self._held_keys):
            if self._hwnd:
                native_window.send_key_up(self._hwnd, code)
        self._held_keys.clear()

    def keyPressEvent(self, event) -> None:
        """Bàn phím thật → phím MRE (cùng bảng mặc định của VXPEmu).

        Cửa sổ giả lập được nhúng bằng `SetParent` nên cửa sổ này mới là cửa sổ
        đang hoạt động; không chuyển tiếp thì người dùng phải bấm chuột từng phím.
        """
        code = _QT_TO_MRE.get(event.key())
        if code is not None and not event.isAutoRepeat():
            self.send_key_down(code)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        code = _QT_TO_MRE.get(event.key())
        if code is not None and not event.isAutoRepeat():
            self.send_key_up(code)
            event.accept()
            return
        super().keyReleaseEvent(event)

    def focusOutEvent(self, event) -> None:
        # Mất focus = không còn keyRelease nào tới nữa (Alt+Tab khi đang giữ phím).
        self.release_all_keys()
        super().focusOutEvent(event)

    def process_stopped(self, code: int) -> None:
        self.release_all_keys()
        self._attach_timer.stop()
        self._fit_timer.stop()
        self._pid, self._hwnd = 0, None
        self.body.screen.set_state(STATE_STOPPED, "VXPEmu đã dừng")
        self.body.set_link(False, "VXPEmu · chưa nối")
        if self._record_timer.isActive():
            self._stop_recording()
        self.status.setText(f"Đã dừng · code {code}")
        self._sync_rail()

    def closeEvent(self, event) -> None:
        self.release_all_keys()
        if not self._closing_for_shutdown and self._pid:
            self.stop_requested.emit()
        event.accept()

    def shutdown(self) -> None:
        self._closing_for_shutdown = True
        self.release_all_keys()
        self._attach_timer.stop()
        self._fit_timer.stop()
        self._record_timer.stop()
        self._discard_recording()
        self.close()
