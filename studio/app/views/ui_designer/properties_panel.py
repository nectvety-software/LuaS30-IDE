"""
properties_panel.py — Inspector thuộc tính widget của UI Designer, dùng đúng
idiom property-grid của 2Dutiful: PropGroupLabel + PropRow (PropName trái,
ô giá trị/điều khiển bên phải). Nhóm: WIDGET / TRANSFORM / MÀU SẮC / TEXT.

Nhóm MÀU SẮC dùng bảng chọn màu của package này (`color_button.py`) — bấm ô màu
là mở popup lưới màu dựng sẵn + ô HEX, kèm nút mở QColorDialog khi cần chọn kỹ.

Ô "ID" trong nhóm WIDGET chính là ID thành phần (`DesignerItem.name`) — cùng
giá trị với tên lớp ở bảng LAYERS, và là khoá được đồng bộ sang mã Lua
(`name` trong tệp scene, `ui.<id>` trong tệp logic). Sửa ô này hoặc kích đúp
tên lớp ở bảng LAYERS đều cho cùng kết quả.
"""
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QLineEdit, QFrame,
    QSizePolicy, QToolButton
)

from app.ui import palette
from . import icons_compat as icons
from .color_button import ColorButton
from .items import (
    DesignerItem, SCREEN_H, SCREEN_W, component_info, supports_text
)

NAME_WIDTH = 72
# Màu tô mặc định của thành phần MỚI — đây là màu NỘI DUNG (ghi vào
# ui_design.json rồi vẽ trong game), không phải màu chrome của IDE, nên cố ý
# không lấy từ palette.py.
DEFAULT_FILL = QColor("#4f8cff")


def _group(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("PropGroupLabel")
    label.setProperty("class", "PropGroupLabel")
    return label


def _row(name: str, widget: QWidget, name_width: int = NAME_WIDTH) -> QFrame:
    row = QFrame()
    row.setObjectName("PropRow")
    row.setProperty("class", "PropRow")
    layout = QHBoxLayout(row)
    layout.setContentsMargins(2, 2, 2, 2)
    layout.setSpacing(6)
    label = QLabel(name)
    label.setObjectName("PropName")
    label.setProperty("class", "PropName")
    label.setFixedWidth(name_width)
    layout.addWidget(label)
    layout.addWidget(widget, 1)
    return row


class _NumberField(QWidget):
    """Spin + label compact kiểu Figma (X/Y hoặc W/H trong 1 hàng)."""

    def __init__(self, label: str, maximum: int = 2000, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        lab = QLabel(label)
        lab.setObjectName("InlineFieldLabel")
        lab.setFixedWidth(12)
        layout.addWidget(lab)
        self.spin = QSpinBox()
        self.spin.setRange(0, maximum)
        self.spin.setButtonSymbols(QSpinBox.NoButtons)
        self.spin.setFixedHeight(24)
        layout.addWidget(self.spin, 1)

    @property
    def value(self):
        return self.spin.value()

    @value.setter
    def value(self, v):
        self.spin.setValue(v)


class PropertiesPanel(QWidget):
    # (item, ID thô vừa gõ) — UIDesignerWidget kiểm tra hợp lệ/trùng rồi đồng bộ mã
    idEdited = Signal(object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InspectorForm")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._current: DesignerItem = None
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 12)
        layout.setSpacing(3)

        # ---- header chọn đối tượng ----
        self.selection = QLabel("Chưa chọn widget")
        self.selection.setObjectName("InspectorSelectionText")
        selection_box = QFrame()
        selection_box.setObjectName("InspectorSelection")
        selection_box.setAttribute(Qt.WA_StyledBackground, True)
        sb = QHBoxLayout(selection_box)
        sb.setContentsMargins(10, 6, 10, 6)
        sb.addWidget(self.selection, 1)
        layout.addWidget(selection_box)
        layout.addSpacing(2)

        # ---- nhóm WIDGET ----
        layout.addWidget(_group("WIDGET"))
        self.type_label = QLabel("—")
        self.type_label.setObjectName("PropValue")
        self.type_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(_row("Loại", self.type_label))

        # ID thành phần = khoá đồng bộ sang mã Lua; cũng đổi được bằng cách
        # kích đúp tên lớp ở bảng LAYERS
        self.id_edit = QLineEdit()
        self.id_edit.setObjectName("PropIdEdit")
        self.id_edit.setPlaceholderText("id_thanh_phan")
        self.id_edit.setMinimumHeight(24)
        self.id_edit.setToolTip(
            "ID của thành phần — cũng là khoá 'ui.<id>' trong mã Lua của màn hình.\n"
            "Kích đúp tên lớp ở bảng LỚP cũng đổi được ID.")
        self.id_edit.editingFinished.connect(self._apply_id)
        layout.addWidget(_row("ID", self.id_edit))

        # ---- nhóm TRANSFORM ----
        layout.addWidget(_group("TRANSFORM"))
        self.x_spin = _NumberField("X")
        self.y_spin = _NumberField("Y")
        pos_widget = QWidget()
        pos_layout = QHBoxLayout(pos_widget)
        pos_layout.setContentsMargins(0, 0, 0, 0)
        pos_layout.setSpacing(6)
        pos_layout.addWidget(self.x_spin, 1)
        pos_layout.addWidget(self.y_spin, 1)
        layout.addWidget(_row("Vị trí", pos_widget))

        self.w_spin = _NumberField("W", maximum=SCREEN_W)
        self.h_spin = _NumberField("H", maximum=SCREEN_H)
        size_widget = QWidget()
        size_layout = QHBoxLayout(size_widget)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(6)
        size_layout.addWidget(self.w_spin, 1)
        size_layout.addWidget(self.h_spin, 1)
        layout.addWidget(_row("Kích thước", size_widget))

        # ---- nhóm MÀU SẮC ----
        layout.addWidget(_group("MÀU SẮC"))
        fill_widget = QWidget()
        fill_layout = QHBoxLayout(fill_widget)
        fill_layout.setContentsMargins(0, 0, 0, 0)
        fill_layout.setSpacing(4)
        self.fill_button = ColorButton(DEFAULT_FILL, show_text=True)
        self.fill_button.setToolTip(
            "Màu tô của thành phần — bấm để mở bảng chọn màu (S/V, tông màu, HEX)")
        self.fill_button.colorChanged.connect(self._apply_fill)
        fill_layout.addWidget(self.fill_button, 1)
        self.fill_reset = QToolButton()
        self.fill_reset.setObjectName("LayerToolBtn")
        self.fill_reset.setIcon(icons.icon_refresh("palette.TEXT_4", icons.ICON))
        self.fill_reset.setIconSize(QSize(icons.ICON, icons.ICON))
        self.fill_reset.setFixedSize(icons.BTN, icons.BTN)
        self.fill_reset.setCursor(Qt.PointingHandCursor)
        self.fill_reset.setToolTip("Về màu mặc định của loại thành phần")
        self.fill_reset.clicked.connect(self._reset_fill)
        fill_layout.addWidget(self.fill_reset)
        layout.addWidget(_row("Màu tô", fill_widget))

        self.rot_spin = _NumberField("°", maximum=359)
        self.rot_spin.spin.setSuffix("°")
        self.rot_spin.setToolTip("Góc xoay quanh tâm thành phần")
        layout.addWidget(_row("Xoay", self.rot_spin))

        # ---- nhóm TEXT ----
        layout.addWidget(_group("TEXT"))
        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Nhập nội dung…")
        self.text_edit.setMinimumHeight(26)
        self.text_row = _row("Nội dung", self.text_edit)
        layout.addWidget(self.text_row)

        layout.addStretch(1)

        self._hint = QLabel("Chọn một widget trên canvas")
        self._hint.setObjectName("PropertyHint")
        layout.addWidget(self._hint)

        for f in (self.x_spin, self.y_spin, self.w_spin, self.h_spin):
            f.spin.valueChanged.connect(self._apply_geometry)
        self.rot_spin.spin.valueChanged.connect(self._apply_rotation)
        self.text_edit.textChanged.connect(self._apply_text)

        self._set_enabled(False)

    # ---------------- helpers ----------------
    def _set_enabled(self, enabled: bool):
        for w in (self.type_label, self.id_edit, self.x_spin, self.y_spin,
                  self.w_spin, self.h_spin, self.rot_spin, self.text_edit,
                  self.fill_button, self.fill_reset):
            w.setEnabled(enabled)

    def set_item(self, item: DesignerItem):
        self._current = item
        if item is None:
            self._set_enabled(False)
            self._hint.setVisible(True)
            self.selection.setText("Chưa chọn widget")
            return
        self._set_enabled(True)
        self._hint.setVisible(False)
        info = component_info(item.widget_type)
        kind = f"{info.get('vi', item.widget_type)}  ·  {info.get('en', '')}"
        self.selection.setText(f"{info.get('en', item.widget_type)}  —  WIDGET")
        self.type_label.setText(kind)
        # chỉ thành phần có chữ mới bật ô "Nội dung"
        self.text_row.setEnabled(supports_text(item.widget_type))
        self._updating = True
        self.id_edit.setText(item.name)
        self.x_spin.value = round(item.pos().x())
        self.y_spin.value = round(item.pos().y())
        self.w_spin.value = round(item.rect().width())
        self.h_spin.value = round(item.rect().height())
        self.rot_spin.value = round(item.rotation())
        self.fill_button.set_color(item.fill_or(DEFAULT_FILL), emit=False)
        self.fill_button.setEnabled(True)
        self.text_edit.setText(item.text)
        self._updating = False

    def _apply_id(self):
        """Ô 'ID' sửa xong -> nhờ UIDesignerWidget kiểm tra + đồng bộ mã Lua.

        Ở đây chỉ phát yêu cầu: tính hợp lệ/trùng lặp cần cả scene nên thuộc
        `DesignerScene.rename_item`, và việc ghi mã Lua thuộc UIDesignerWidget.
        """
        if self._updating or not self._current:
            return
        text = self.id_edit.text().strip()
        if text == self._current.name:
            return
        self.idEdited.emit(self._current, text)

    def _apply_geometry(self):
        if self._updating or not self._current:
            return
        item = self._current
        item.setPos(self.x_spin.value, self.y_spin.value)
        # set_size() kẹp kích thước trong màn hình 240×320 -> đọc lại giá trị thật
        item.set_size(self.w_spin.value, self.h_spin.value)
        self._resync()

    def _apply_rotation(self):
        if self._updating or not self._current:
            return
        self._current.set_angle(self.rot_spin.value)
        self._resync()

    def _apply_fill(self, color: QColor):
        if self._updating or not self._current:
            return
        self._current.set_fill(color)

    def _reset_fill(self):
        if not self._current:
            return
        self._current.set_fill(None)
        self._updating = True
        self.fill_button.set_color(DEFAULT_FILL, emit=False)
        self._updating = False

    def _resync(self):
        """Đọc lại hình học từ item (sau khi bị kẹp vào màn hình)."""
        if not self._current:
            return
        item = self._current
        self._updating = True
        self.x_spin.value = round(item.pos().x())
        self.y_spin.value = round(item.pos().y())
        self.w_spin.value = round(item.rect().width())
        self.h_spin.value = round(item.rect().height())
        self.rot_spin.value = round(item.rotation())
        self._updating = False

    def _apply_text(self, text):
        if self._updating or not self._current:
            return
        self._current.set_text(text)
