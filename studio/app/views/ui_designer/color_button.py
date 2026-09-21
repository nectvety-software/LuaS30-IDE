"""
color_button.py — Ô chọn màu cho Inspector của UI Designer.

Bản lua-engine có `app/ui/color_picker.py` với popup S/V + thanh tông màu +
alpha tự vẽ (400 dòng). Studio LuaS30 không có sẵn module đó, nên ở đây dựng
bản gọn hơn nhưng giữ nguyên API mà `properties_panel.py` gọi tới:

    btn = ColorButton(DEFAULT_FILL, show_text=True)
    btn.colorChanged.connect(slot)      # slot nhận QColor
    btn.set_color(color, emit=False)
    btn.color() -> QColor

Popup gồm: lưới màu dựng sẵn (bảng màu thiết bị S30+ 16 màu + thang xám) và ô
nhập HEX. Nút "Tuỳ chọn…" mở ColorPickerDialog frameless (custom Title Bar,
không dùng thanh tiêu đề hệ điều hành) khi cần chọn kỹ.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget,
)

from app.ui import palette
from app.vxpui.custom_dialog import ColorPickerDialog

# 16 màu hay dùng cho UI máy S30+ (đọc rõ trên màn hình 240x320 độ tương phản thấp)
PRESET_COLORS = [
    "#000000", "#1e1e1e", "#3c3c3c", "#6b6b6b",
    "#8f8f8f", "#bdbdbd", "#e6e6e6", "#ffffff",
    "#007acc", "#4ec9b0", "#d7ba7d", "#f14c4c",
    "#c586c0", "#569cd6", "#4ec9b0", "#ce9178",
]


class ColorPickerPopup(QFrame):
    """Popup nhỏ: lưới màu dựng sẵn + ô HEX + nút mở hộp thoại màu hệ thống."""

    colorPicked = Signal(QColor)

    def __init__(self, color: QColor, with_alpha: bool = False,
                 sv_size: QSize | None = None, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("ColorPopup")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._color = QColor(color)
        self._with_alpha = bool(with_alpha)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        grid = QGridLayout()
        grid.setSpacing(3)
        for index, value in enumerate(PRESET_COLORS):
            row, col = divmod(index, 4)
            swatch = QPushButton()
            swatch.setFixedSize(28, 22)
            swatch.setCursor(Qt.CursorShape.PointingHandCursor)
            swatch.setToolTip(value.upper())
            swatch.setStyleSheet(
                f"background-color:{value}; border:1px solid palette.BORDER_HOVER;"
                "border-radius:2px;")
            swatch.clicked.connect(
                lambda _checked=False, v=value: self._pick(QColor(v)))
            grid.addWidget(swatch, row, col)
        layout.addLayout(grid)

        hex_row = QHBoxLayout()
        hex_row.setSpacing(4)
        self.hex_edit = QLineEdit(self._color.name().upper())
        self.hex_edit.setMaxLength(9)
        self.hex_edit.setFixedHeight(24)
        self.hex_edit.returnPressed.connect(self._commit_hex)
        hex_row.addWidget(QLabel("HEX"))
        hex_row.addWidget(self.hex_edit, 1)
        layout.addLayout(hex_row)

        more = QPushButton("Tuỳ chọn…")
        more.setObjectName("GhostButton")
        more.setFixedHeight(24)
        more.setCursor(Qt.CursorShape.PointingHandCursor)
        more.clicked.connect(self._open_native)
        layout.addWidget(more)

    def _pick(self, color: QColor):
        self._color = QColor(color)
        self.colorPicked.emit(self.color())
        self.close()

    def _commit_hex(self):
        text = self.hex_edit.text().strip()
        if not text.startswith("#"):
            text = "#" + text
        color = QColor(text)
        if color.isValid():
            self._pick(color)
        else:
            self.hex_edit.setText(self._color.name().upper())

    def _open_native(self):
        color = ColorPickerDialog.get_color(
            self._color, self.parentWidget(),
            title="Chọn màu", show_alpha=self._with_alpha,
        )
        if color.isValid():
            self._pick(color)

    def color(self) -> QColor:
        return QColor(self._color)


class ColorButton(QPushButton):
    """Nút swatch — bấm mở bảng chọn màu trong popup."""

    colorChanged = Signal(QColor)

    def __init__(self, color: QColor | None = None, with_alpha: bool = False,
                 show_text: bool = True, sv_size: QSize | None = None,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("ColorButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(24)
        self.setMinimumWidth(46)
        self._with_alpha = with_alpha
        self._show_text = show_text
        self._sv_size = sv_size
        # màu NỘI DUNG khi chưa chọn gì (giống DEFAULT_FILL của inspector),
        # không phải màu chrome — xem properties_panel.DEFAULT_FILL
        self._color = QColor(color) if color else QColor("#4f8cff")
        self._popup: ColorPickerPopup | None = None
        self.clicked.connect(self._open)
        self._refresh()

    def color(self) -> QColor:
        return QColor(self._color)

    def set_color(self, color: QColor, emit: bool = False):
        if not color or not color.isValid():
            return
        self._color = QColor(color)
        self._refresh()
        if emit:
            self.colorChanged.emit(self.color())

    def _refresh(self):
        c = self._color
        if self._with_alpha and c.alpha() < 255:
            css = (f"background-color: rgba({c.red()},{c.green()},{c.blue()},"
                   f"{c.alpha() / 255:.3f});")
        else:
            css = f"background-color: {c.name()};"
        # chữ tự đổi màu theo độ sáng nền để luôn đọc được
        lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
        fg = "#101010" if lum > 148 else "#e8e8e8"
        self.setStyleSheet(
            css + f"color:{fg}; border:1px solid palette.BORDER_HOVER; border-radius:3px;"
                  "padding:0 6px; font-size:10px; font-weight:600;")
        self.setText(c.name().upper() if self._show_text else "")

    def _open(self):
        self._popup = ColorPickerPopup(self._color, with_alpha=self._with_alpha,
                                       sv_size=self._sv_size, parent=self)
        self._popup.colorPicked.connect(self._on_picked)
        self._popup.setFixedSize(self._popup.sizeHint())
        self._popup.move(self.mapToGlobal(QPoint(0, self.height() + 4)))
        self._popup.show()

    def _on_picked(self, color: QColor):
        self.set_color(color, emit=True)


class ColorWidget(QWidget):
    """Ô màu có nhãn — dùng khi cần đặt màu trong form dạng nhãn + giá trị."""

    colorChanged = Signal(QColor)

    def __init__(self, label: str, color: QColor | None = None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.button = ColorButton(color)
        self.button.colorChanged.connect(self.colorChanged)
        layout.addWidget(QLabel(label))
        layout.addWidget(self.button, 1)

    def color(self) -> QColor:
        return self.button.color()

    def set_color(self, color: QColor, emit: bool = False):
        self.button.set_color(color, emit=emit)
