"""
layers_panel.py — Bảng LAYERS kiểu Photoshop cho UI Designer.

Cho phép:
  * Kéo-thả hàng trong danh sách để đổi thứ tự lớp (trên cùng = vẽ sau cùng,
    nằm trên các lớp khác — đúng quy ước của Photoshop).
  * Kích đúp tên lớp để ĐỔI ID thành phần tại chỗ; ID này chính là khoá được
    đồng bộ sang mã Lua (`name` trong tệp scene, `ui.<id>` trong tệp logic)
    nên đặt tên xong là gán được tính năng/logic cho thành phần.
  * Nút đưa lớp ra trước / ra sau một bậc.
  * Nhân bản lớp, xoay 90°, ẩn/hiện, xoá.
  * Bấm một hàng = chọn thành phần đó trên canvas (hai chiều đều đồng bộ).

Thứ tự lớp chính là z-value của DesignerItem: hàng đầu danh sách có z lớn nhất.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QToolButton, QVBoxLayout, QWidget,
)

from app.ui import palette
from . import icons_compat as icons
from .items import component_info, image_key, is_image_token
from .widgets_palette import PREVIEW_H, PREVIEW_W, preview_pixmap

ROLE_ITEM = Qt.UserRole + 10
PANEL_WIDTH = 212


def _type_label(item) -> str:
    """Nhãn LOẠI của một lớp (tên tiếng Việt, hoặc tên file ảnh)."""
    if is_image_token(getattr(item, "widget_type", "")):
        return image_key(item.widget_type)
    src = getattr(item, "src", "")
    if src:
        return src.rsplit("/", 1)[-1]
    info = component_info(item.widget_type)
    return info.get("vi", item.widget_type)


class _LayerList(QListWidget):
    """Danh sách lớp — kéo-thả nội bộ để đổi thứ tự vẽ, kích đúp để sửa ID."""

    orderChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LayerList")
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        # icon hàng lớp 22×16 + hàng sát nhau — mật độ giống cây file của VS Code
        self.setIconSize(QSize(PREVIEW_W, PREVIEW_H))
        self.setUniformItemSizes(True)
        self.setSpacing(0)
        # sửa ID: chỉ khi kích đúp hoặc F2 — KHÔNG sửa khi bấm một lần
        # (bấm một lần vẫn phải là "chọn lớp", như Photoshop)
        self.setEditTriggers(QAbstractItemView.DoubleClicked |
                             QAbstractItemView.EditKeyPressed)
        # rowsMoved phát ra cả khi kéo-thả lẫn khi dùng phím tắt
        self.model().rowsMoved.connect(lambda *_: self.orderChanged.emit())


class LayersPanel(QWidget):
    """Panel phải của UI Designer: danh sách lớp + thao tác thứ tự/xoay/nhân bản."""

    logMessage = Signal(str)
    # (item, ID cũ, ID mới) — UIDesignerWidget nghe để đồng bộ sang mã Lua
    itemRenamed = Signal(object, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LayersPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(PANEL_WIDTH)
        self._scene = None
        self._syncing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("LỚP  ·  ID")
        header.setObjectName("PanelHeaderTitle")
        header.setContentsMargins(10, 8, 10, 4)
        layout.addWidget(header)

        # ---- hàng nút thao tác ----
        tools = QWidget()
        tools.setObjectName("LayerTools")
        tl = QHBoxLayout(tools)
        tl.setContentsMargins(8, 0, 8, 6)
        tl.setSpacing(3)

        self.btn_front = self._tool_button(
            icons.icon_arrow_up, "Đưa lớp ra trước (lên trên)", self.raise_layer)
        self.btn_back = self._tool_button(
            icons.icon_arrow_down, "Đẩy lớp ra sau (xuống dưới)", self.lower_layer)
        tl.addWidget(self.btn_front)
        tl.addWidget(self.btn_back)
        tl.addSpacing(6)
        self.btn_dup = self._tool_button(
            icons.icon_duplicate, "Nhân bản lớp (Ctrl+D)", self.duplicate_layer)
        self.btn_rotate = self._tool_button(
            icons.icon_rotate, "Xoay 90° quanh tâm", self.rotate_layer)
        tl.addWidget(self.btn_dup)
        tl.addWidget(self.btn_rotate)
        tl.addStretch(1)
        self.btn_delete = self._tool_button(
            icons.icon_trash, "Xoá lớp (Delete)", self.delete_layer)
        tl.addWidget(self.btn_delete)
        layout.addWidget(tools)

        # ---- danh sách lớp ----
        self.list = _LayerList()
        self.list.currentItemChanged.connect(self._on_current_changed)
        self.list.itemChanged.connect(self._on_item_changed)
        self.list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list.orderChanged.connect(self._on_order_changed)
        layout.addWidget(self.list, 1)

        hint = QLabel("Kích đúp tên để đổi ID · kéo-thả đổi thứ tự · "
                      "hàng trên cùng nằm trên hết")
        hint.setObjectName("PaletteHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._update_buttons()

    def _tool_button(self, icon_func, tooltip: str, callback) -> QToolButton:
        btn = QToolButton()
        btn.setObjectName("LayerToolBtn")
        btn.setIcon(icon_func("palette.TEXT_3", icons.ICON))
        btn.setIconSize(QSize(icons.ICON, icons.ICON))
        btn.setFixedSize(icons.BTN, icons.BTN)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        return btn

    # ------------------------------------------------ gắn vào scene
    def attach(self, scene):
        """Gắn bảng vào một DesignerScene và bắt đầu đồng bộ hai chiều."""
        self._scene = scene
        scene.layersChanged.connect(self.refresh)
        scene.itemSelected.connect(self._on_scene_selection)
        self.refresh()

    def refresh(self):
        """Dựng lại danh sách từ scene.

        Hàng được giữ chọn ưu tiên theo LỰA CHỌN TRÊN CANVAS (để sau khi nhân
        bản, bảng nhảy sang bản sao vừa tạo chứ không đứng lại ở bản gốc).

        Chữ trên hàng là **ID thành phần** (`item.name`) — cũng là khoá được
        đồng bộ sang mã Lua. Loại thành phần nằm ở tooltip + icon.
        """
        if self._scene is None:
            return
        current = None
        selected = self._scene.selectedItems()
        if selected:
            current = selected[0]
        if current is None:
            current = self._selected_item()
        self._syncing = True
        try:
            self.list.clear()
            for item in self._scene.layer_items():
                row = QListWidgetItem(self.list)
                row.setData(ROLE_ITEM, item)
                row.setText(item.name)
                row.setIcon(QIcon(preview_pixmap(self._token_of(item),
                                                 PREVIEW_W, PREVIEW_H)))
                row.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable |
                             Qt.ItemIsDragEnabled | Qt.ItemIsUserCheckable |
                             Qt.ItemIsEditable)
                row.setCheckState(Qt.Checked if item.isVisible() else Qt.Unchecked)
                row.setToolTip(self._row_tooltip(item))
            if current is not None:
                self._select_row(current)
        finally:
            self._syncing = False
        self._update_buttons()

    def _row_tooltip(self, item) -> str:
        """Chú thích hàng: ID, loại, hình học và gợi ý đổi tên."""
        pos = item.pos()
        lines = [
            f"ID: {item.name}",
            _type_label(item),
            f"({round(pos.x())}, {round(pos.y())})  "
            f"{round(item.rect().width())}×{round(item.rect().height())}",
        ]
        if item.rotation():
            lines.append(f"Xoay {round(item.rotation())}°")
        lines.append("Kích đúp để đổi ID (Enter nhận · Esc huỷ)")
        return "\n".join(lines)

    def _token_of(self, item) -> str:
        """Token để render ảnh xem trước: ảnh đăng ký dùng 'img:<key>'."""
        src = getattr(item, "src", "")
        if src:
            from .items import image_for_src
            entry = image_for_src(src)
            if entry is not None:
                return f"img:{entry['key']}"
        return item.widget_type

    # ------------------------------------------------ đồng bộ chọn
    def _selected_item(self):
        row = self.list.currentItem()
        return row.data(ROLE_ITEM) if row is not None else None

    def _select_row(self, item) -> bool:
        for i in range(self.list.count()):
            row = self.list.item(i)
            if row.data(ROLE_ITEM) is item:
                self.list.setCurrentItem(row)
                self.list.scrollToItem(row)
                return True
        return False

    def _on_scene_selection(self, item):
        if self._syncing or self._scene is None:
            return
        self._syncing = True
        try:
            if item is None:
                self.list.clearSelection()
                self.list.setCurrentItem(None)
            else:
                self._select_row(item)
        finally:
            self._syncing = False
        self._update_buttons()

    def _on_current_changed(self, current, _previous):
        if self._syncing or self._scene is None or current is None:
            return
        item = current.data(ROLE_ITEM)
        if item is None:
            return
        self._syncing = True
        try:
            self._scene.clearSelection()
            item.setSelected(True)
        finally:
            self._syncing = False
        self._update_buttons()

    def _on_item_double_clicked(self, row: QListWidgetItem):
        """Kích đúp một hàng = mở ô sửa ID tại chỗ.

        QListWidget tự mở editor (hàng có cờ ItemIsEditable + edit trigger
        DoubleClicked); ở đây chỉ báo cho người dùng biết đang sửa cái gì.
        """
        if self._scene is None:
            return
        item = row.data(ROLE_ITEM)
        if item is None:
            return
        self.logMessage.emit(
            f"[UI DESIGNER] Đang sửa ID lớp '{item.name}' "
            f"— Enter để nhận, Esc để huỷ")

    def _on_item_changed(self, row: QListWidgetItem):
        """Một hàng đổi: hoặc ĐỔI ID (chữ), hoặc ẩn/hiện (ô tick)."""
        if self._syncing or self._scene is None:
            return
        item = row.data(ROLE_ITEM)
        if item is None:
            return

        text = row.text().strip()
        if text != item.name:
            self._apply_rename(row, item, text)
            return

        visible = row.checkState() == Qt.Checked
        if item.isVisible() != visible:
            item.setVisible(visible)
            self.logMessage.emit(
                f"[UI DESIGNER] Lớp '{item.name}' {'hiện' if visible else 'ẩn'}")

    def _apply_rename(self, row: QListWidgetItem, item, new_text: str):
        """Áp ID mới vừa gõ; sai thì trả hàng về ID cũ (không dựng lại cả bảng)."""
        old = item.name
        ok, err = self._scene.rename_item(item, new_text)
        if not ok:
            self.logMessage.emit(f"[UI DESIGNER] Không đổi được ID: {err}")
            self._set_row(row, item, old)
            return
        if item.name == old:
            # chỉ khác khoảng trắng / hoa-thường không đổi -> chuẩn hoá lại hàng
            self._set_row(row, item, item.name)
            return
        self._set_row(row, item, item.name)
        self.logMessage.emit(f"[UI DESIGNER] Đổi ID '{old}' → '{item.name}'")
        self.itemRenamed.emit(item, old, item.name)

    def _set_row(self, row: QListWidgetItem, item, text: str):
        """Ghi chữ/chú thích cho một hàng mà không kích hoạt lại slot đổi tên."""
        self._syncing = True
        try:
            row.setText(text)
            row.setToolTip(self._row_tooltip(item))
        finally:
            self._syncing = False

    def _on_order_changed(self):
        """Người dùng vừa kéo-thả đổi thứ tự hàng -> áp lại z-order cho scene."""
        if self._syncing or self._scene is None:
            return
        order = [self.list.item(i).data(ROLE_ITEM) for i in range(self.list.count())]
        order = [it for it in order if it is not None]
        if not order:
            return
        self._syncing = True
        try:
            self._scene.set_layer_order(order)
        finally:
            self._syncing = False
        self.logMessage.emit("[UI DESIGNER] Đã đổi thứ tự lớp (trên cùng vẽ sau cùng)")

    # ------------------------------------------------ thao tác
    def _update_buttons(self):
        item = self._selected_item()
        has = item is not None
        for btn in (self.btn_front, self.btn_back, self.btn_dup,
                    self.btn_rotate, self.btn_delete):
            btn.setEnabled(has)

    def raise_layer(self):
        self._move(1)

    def lower_layer(self):
        self._move(-1)

    def _move(self, delta: int):
        item = self._selected_item()
        if item is None or self._scene is None:
            return
        if self._scene.move_layer(item, delta):
            self.logMessage.emit(
                f"[UI DESIGNER] Lớp '{item.name}' "
                f"{'lên trên' if delta > 0 else 'xuống dưới'}")
        self.refresh()

    def duplicate_layer(self):
        item = self._selected_item()
        if item is None or self._scene is None:
            return
        clone = self._scene.duplicate_item(item)
        if clone is not None:
            self.logMessage.emit(f"[UI DESIGNER] Đã nhân bản lớp '{item.name}'")
        self.refresh()

    def rotate_layer(self):
        item = self._selected_item()
        if item is None or self._scene is None:
            return
        self._scene.rotate_item(item, 90.0)
        self.logMessage.emit(
            f"[UI DESIGNER] Lớp '{item.name}' xoay {round(item.rotation())}°")
        self.refresh()

    def delete_layer(self):
        item = self._selected_item()
        if item is None or self._scene is None:
            return
        name = item.name
        if self._scene.remove_items([item]):
            self.logMessage.emit(f"[UI DESIGNER] Đã xoá lớp '{name}'")
        self.refresh()
