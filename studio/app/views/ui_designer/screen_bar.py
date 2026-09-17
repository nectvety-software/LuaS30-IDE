"""
screen_bar.py — Thanh chọn / tạo màn hình UI của UI Designer.

Bố cục:  [ MÀN HÌNH ] [ combo ▾ ] [ + ] [ ⋮ ]

  * combo — chọn màn hình đang thiết kế
  * `+`   — TẠO màn hình mới (dialog đặt tên)
  * `⋮`   — đổi tên / nhân bản / xoá / mở thư mục chứa thiết kế

Màn hình mặc định là **main** — không đổi tên, không xoá được.

Bản lua-engine làm việc trên `Path` của từng tệp `src/ui/<tên>.ui.dtfe`. Studio
LuaS30 gói MỌI màn hình vào một tệp `.luas30/ui_design.json`, nên widget này chỉ
làm việc trên **id màn hình** (chuỗi). Nhờ vậy đổi tên màn hình chỉ là đổi khoá
trong JSON — không phải rename tệp, không có nguy cơ mồ côi tệp logic.

Widget chỉ phát tín hiệu; toàn bộ việc đọc-ghi nằm ở `UIDesignerWidget` để giữ
một chỗ duy nhất quản lý màn hình đang mở.
"""

from __future__ import annotations

import re

from app.ui import palette
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QMenu, QToolButton, QWidget,
)

from . import icons_compat as icons
from .design_store import DESIGN_FILENAME, MAIN_SCREEN_ID, UI_DIR
from .items import sanitize_id
from .modal import ModalDialog

# mục giữ chỗ khi chưa mở màn hình nào (data = None -> không phải màn hình thật)
PLACEHOLDER_TEXT = "(chưa mở màn hình)"

# ký tự không hợp lệ trong tên màn hình (vừa là khoá JSON vừa là định danh Lua)
_BAD_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def screen_slug(name: str) -> str:
    """Tên màn hình -> định danh hợp lệ (khoá JSON + `require`-able id)."""
    cleaned = _BAD_NAME_CHARS.sub("_", str(name or "")).strip().strip(".")
    return sanitize_id(cleaned, "screen")


class ScreenNameDialog(ModalDialog):
    """Đặt tên cho màn hình (dùng chung cho tạo mới / đổi tên / nhân bản)."""

    def __init__(self, title: str, message: str, initial: str,
                 taken: set[str], parent=None, ok_text: str = "Tạo màn hình",
                 locked: bool = False):
        super().__init__(title, message, parent, width=460)
        self._taken = {t.lower() for t in taken}
        self.result_name: str = ""
        self._locked = bool(locked)

        self.add_body_widget(self._label("Tên màn hình"))
        self.name_edit = QLineEdit(initial)
        self.name_edit.setClearButtonEnabled(True)
        self.name_edit.setMinimumHeight(28)
        self.name_edit.selectAll()
        self.name_edit.setEnabled(not self._locked)
        self.add_body_widget(self.name_edit)

        self.file_label = QLabel("")
        self.file_label.setObjectName("DialogHint")
        self.file_label.setWordWrap(True)
        self.add_body_widget(self.file_label)

        self.btn_ok = self.add_button(ok_text, primary=True, on_click=self._accept)
        self.add_button("Huỷ", ghost=True, on_click=self.reject)

        if self._locked:
            self.btn_ok.setEnabled(False)
            self._set_hint(
                f"'{MAIN_SCREEN_ID}' là màn hình khởi động — không thể đổi tên.",
                False)
        else:
            self.name_edit.textChanged.connect(self._validate)
            self.name_edit.returnPressed.connect(self._accept)
            self._validate(initial)

    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("PropName")
        return label

    def _validate(self, text: str):
        raw = str(text or "").strip()
        slug = screen_slug(raw)
        if not raw:
            self._set_hint("Nhập tên màn hình, ví dụ: menu, inventory, hud.", False)
            return
        if slug.lower() == MAIN_SCREEN_ID:
            self._set_hint(
                f"'{MAIN_SCREEN_ID}' là màn hình khởi động — chọn tên khác.",
                False)
            return
        if slug.lower() in self._taken:
            self._set_hint(f"Đã có màn hình tên '{slug}' — chọn tên khác.", False)
            return
        self._set_hint(
            f"Lưu thành màn hình '{slug}' trong {UI_DIR}/{DESIGN_FILENAME}", True)

    def _set_hint(self, text: str, ok: bool):
        self.file_label.setText(text)
        self.file_label.setProperty("state", "ok" if ok else "error")
        self.file_label.style().unpolish(self.file_label)
        self.file_label.style().polish(self.file_label)
        self.btn_ok.setEnabled(ok and not self._locked)

    def _accept(self):
        if not self.btn_ok.isEnabled():
            return
        self.result_name = screen_slug(self.name_edit.text())
        self.accept()


class ScreenBar(QWidget):
    """Thanh chọn / tạo màn hình — xem docstring đầu tệp."""

    screenSelected = Signal(str)       # id màn hình được chọn
    createRequested = Signal()
    renameRequested = Signal()
    duplicateRequested = Signal()
    deleteRequested = Signal()
    revealRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ScreenBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._updating = False
        self._root = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        self.label = QLabel("MÀN HÌNH")
        self.label.setObjectName("ScreenBarLabel")
        layout.addWidget(self.label)

        self.combo = QComboBox()
        self.combo.setObjectName("ScreenCombo")
        self.combo.setMinimumWidth(120)
        self.combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo.setMinimumContentsLength(12)
        self.combo.currentIndexChanged.connect(self._on_combo_changed)
        layout.addWidget(self.combo, 1)

        self.btn_add = self._action_button(
            icons.icon_plus, f"Tạo màn hình mới ({UI_DIR}/{DESIGN_FILENAME})",
            self.createRequested)
        layout.addWidget(self.btn_add)

        self.btn_menu = self._action_button(
            icons.icon_ellipsis_h, "Thao tác với màn hình", None)
        self.btn_menu.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.btn_menu)
        for icon_func, text, signal in (
            (icons.icon_text, "Đổi tên màn hình…", self.renameRequested),
            (icons.icon_duplicate, "Nhân bản màn hình", self.duplicateRequested),
            (icons.icon_folder_open, f"Mở thư mục {UI_DIR}", self.revealRequested),
        ):
            action = menu.addAction(icon_func("palette.TEXT_2"), text)
            action.triggered.connect(signal)
        menu.addSeparator()
        remove = menu.addAction(icons.icon_trash("palette.RED"), "Xoá màn hình")
        remove.triggered.connect(self.deleteRequested)
        self.btn_menu.setMenu(menu)
        layout.addWidget(self.btn_menu)

        self.set_project(None)

    def _action_button(self, icon_func, tooltip: str, signal) -> QToolButton:
        btn = QToolButton()
        btn.setObjectName("ScreenActionBtn")
        btn.setIcon(icon_func("palette.TEXT_2", icons.ICON))
        btn.setIconSize(QSize(icons.ICON, icons.ICON))
        btn.setFixedSize(icons.BTN, icons.BTN)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tooltip)
        if signal is not None:
            btn.clicked.connect(signal)
        return btn

    # ------------------------------------------------ dữ liệu
    def set_project(self, root, screens: list[str] | None = None,
                    current: str | None = None):
        """Nạp danh sách màn hình. `root=None` -> thanh bị vô hiệu hoá."""
        self._root = root
        self.set_screens(screens or [], current)

    def set_screens(self, screens: list[str], current: str | None):
        """Dựng lại combo; `current` được chọn sẵn.

        Khi chưa mở màn hình nào (`current is None`) mà project đã có màn hình,
        combo chèn một mục giữ chỗ — nếu không nó sẽ tự chọn màn hình đầu tiên và
        trông như đang sửa màn hình đó trong khi canvas vẫn là "màn hình mới".
        """
        screens = [str(s) for s in screens]
        current = str(current) if current else None
        if current is not None and current not in screens:
            screens = screens + [current]

        self._updating = True
        try:
            self.combo.clear()
            if current is None:
                self.combo.addItem(icons.icon_file("palette.TEXT_5"),
                                   PLACEHOLDER_TEXT, None)
            for sid in screens:
                self.combo.addItem(icons.icon_code("palette.ACCENT"), sid, sid)
            index = self.combo.findData(current) if current is not None else -1
            if index < 0:
                index = 0 if self.combo.count() else -1
            self.combo.setCurrentIndex(index)
        finally:
            self._updating = False

        has_project = self._root is not None
        self.combo.setEnabled(has_project and bool(screens))
        for btn in (self.btn_add, self.btn_menu):
            btn.setEnabled(has_project)
        self._update_tooltip(current, has_project, bool(screens))

    def _update_tooltip(self, current: str | None, has_project: bool,
                        has_screens: bool):
        if not has_project:
            text = (f"Mở một project để tạo màn hình UI "
                    f"({UI_DIR}/{DESIGN_FILENAME})")
        elif current is not None:
            extra = " — màn hình khởi động, không đổi tên" \
                if current == MAIN_SCREEN_ID else ""
            text = f"Đang sửa: {current}{extra}"
        elif has_screens:
            text = ("Chưa mở màn hình nào — chọn một màn hình trong danh sách, "
                    "hoặc bấm + để tạo mới")
        else:
            text = ("Chưa có màn hình nào — bấm + để tạo màn hình khác")
        self.combo.setToolTip(text)

    # ------------------------------------------------ truy vấn
    def current_id(self) -> str | None:
        data = self.combo.currentData()
        return str(data) if data else None

    def _on_combo_changed(self, _index: int):
        if self._updating:
            return
        screen_id = self.current_id()
        if screen_id is not None:
            self.screenSelected.emit(screen_id)
