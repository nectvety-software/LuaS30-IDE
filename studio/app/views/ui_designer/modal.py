"""
modal.py — Hộp thoại modal dùng chung cho UI Designer (thay `app/ui/modal.py`
của bản lua-engine).

Bản gốc dựng card bo góc + title bar tự vẽ + icon Lucide. Studio LuaS30 đi theo
hướng ngược lại: theme nằm ở QSS của app (`app/ui/theme.py`) nên dialog chỉ cần
đúng các `objectName` là tự khớp tông. Ở đây giữ NGUYÊN API mà các lớp con
(ScreenNameDialog, ImportAssetDialog) gọi tới:

    super().__init__(title, message, parent, width=...)
    self.add_body_widget(w)
    self.add_button(text, primary=True, ghost=False, on_click=...)
    self.set_title(...)  /  self.request_close()

QSS cho các objectName dưới đây nằm trong `app/ui/theme.py` (mục UI DESIGNER).
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QCloseEvent, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)


class _DialogTitleBar(QWidget):
    """Title bar kéo được — giữ đúng vai trò của bản gốc."""

    def __init__(self, owner: "ModalDialog"):
        super().__init__(owner)
        self._owner = owner
        self.setObjectName("DialogTitleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(30)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 4, 0)
        layout.setSpacing(6)

        self.title_label = QLabel(owner.windowTitle())
        self.title_label.setObjectName("DialogTitleText")
        self.title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.title_label, 1)

        self.close_button = QPushButton()
        self.close_button.setObjectName("DialogCloseButton")
        self.close_button.setFixedSize(36, 24)
        self.close_button.setText("\u2715")
        self.close_button.setToolTip("Đóng")
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.clicked.connect(owner.request_close)
        layout.addWidget(self.close_button)

    def set_title(self, title: str):
        self.title_label.setText(title)

    def mousePressEvent(self, event: QMouseEvent):
        self._owner._title_mouse_press(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        self._owner._title_mouse_move(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._owner._title_mouse_release(event)


class ModalDialog(QDialog):
    """Dialog tối, canh giữa cửa sổ cha, có title bar kéo được."""

    def __init__(self, title: str, message: str = "", parent=None, width: int = 480):
        super().__init__(parent)
        self.setObjectName("ModalDialog")
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._preferred_width = max(340, int(width))
        self._close_handler = None
        self._drag_pos: QPoint | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.title_bar = _DialogTitleBar(self)
        outer.addWidget(self.title_bar)

        self.card = QFrame()
        self.card.setObjectName("ModalCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)
        outer.addWidget(self.card, 1)

        if message:
            hint = QLabel(message)
            hint.setObjectName("DialogHint")
            hint.setWordWrap(True)
            card_layout.addWidget(hint)

        self.body_scroll = QScrollArea()
        self.body_scroll.setObjectName("ModalBody")
        self.body_scroll.setWidgetResizable(True)
        self.body_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(8)
        self.body_scroll.setWidget(self.body)
        card_layout.addWidget(self.body_scroll, 1)

        self.footer = QWidget()
        self.footer.setObjectName("ModalFooter")
        self.button_row = QHBoxLayout(self.footer)
        self.button_row.setContentsMargins(0, 0, 0, 0)
        self.button_row.setSpacing(8)
        self.button_row.addStretch(1)
        card_layout.addWidget(self.footer)

    # ------------------------------------------------ API cho lớp con
    def set_title(self, title: str):
        self.setWindowTitle(title)
        self.title_bar.set_title(title)

    def set_close_handler(self, handler):
        self._close_handler = handler

    def request_close(self):
        if callable(self._close_handler):
            self._close_handler()
            return
        self.reject()

    def add_widget(self, widget: QWidget):
        self.body_layout.addWidget(widget)
        return widget

    def add_body_widget(self, widget: QWidget):
        self.body_layout.addWidget(widget)
        return widget

    def add_button(self, text: str, primary: bool = False, on_click=None,
                   ghost: bool = False) -> QPushButton:
        return self.add_footer_button(text, accent=primary, ghost=ghost,
                                      on_click=on_click)

    def add_footer_button(self, text: str, accent: bool = False, ghost: bool = False,
                          on_click=None) -> QPushButton:
        btn = QPushButton(text)
        if accent:
            btn.setObjectName("PrimaryButton")
        elif ghost:
            btn.setObjectName("GhostButton")
        btn.setMinimumHeight(28)
        btn.setMinimumWidth(88)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if on_click is not None:
            btn.clicked.connect(on_click)
        self.button_row.addWidget(btn)
        return btn

    def hide_footer(self):
        self.footer.setVisible(False)

    # ------------------------------------------------ hành vi
    def showEvent(self, event):
        super().showEvent(event)
        self.setFixedWidth(self._preferred_width)
        self._fit_height()
        parent = self.parentWidget()
        if parent is not None:
            geo = parent.window().frameGeometry()
            self.move(geo.center() - self.rect().center())

    def _fit_height(self):
        """Chọn chiều cao theo nội dung, nhưng không vượt quá cửa sổ cha.

        `sizeHint()` của một QScrollArea luôn đòi khá nhiều chỗ, nên nếu để Qt
        tự quyết thì dialog cao quá màn hình. Ở đây lấy theo nội dung thật của
        phần thân và kẹp lại — phần thừa người dùng cuộn được.
        """
        body_hint = self.body.sizeHint().height()
        chrome = (self.title_bar.height()
                  + self.card.layout().contentsMargins().top()
                  + self.card.layout().contentsMargins().bottom()
                  + self.footer.sizeHint().height()
                  + self.card.layout().spacing() * 3)
        message_hint = 0
        for index in range(self.card.layout().count()):
            widget = self.card.layout().itemAt(index).widget()
            if isinstance(widget, QLabel) and widget.objectName() == "DialogHint":
                message_hint = widget.sizeHint().height()
        wanted = chrome + body_hint + message_hint + 16

        cap = 720
        parent = self.parentWidget()
        if parent is not None:
            cap = min(cap, int(parent.window().height() * 0.85))
        self.resize(self._preferred_width, max(180, min(wanted, cap)))

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.request_close()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent):
        if callable(self._close_handler):
            self._close_handler()
            event.ignore()
            return
        super().closeEvent(event)

    # ---- kéo bằng title bar ----
    def _title_mouse_press(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (event.globalPosition().toPoint()
                              - self.frameGeometry().topLeft())

    def _title_mouse_move(self, event: QMouseEvent):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def _title_mouse_release(self, _event: QMouseEvent):
        self._drag_pos = None


def confirm_dialog(parent, title: str, message: str,
                   ok_text: str = "OK", cancel_text: str = "Huỷ") -> bool:
    """Hộp thoại xác nhận trả về bool — thay QMessageBox cho câu hỏi phá huỷ."""
    dialog = ModalDialog(title, message, parent, width=440)
    dialog.body_scroll.setVisible(False)
    result = {"ok": False}

    def on_ok():
        result["ok"] = True
        dialog.accept()

    dialog.add_button(cancel_text, ghost=True, on_click=dialog.reject)
    dialog.add_button(ok_text, primary=True, on_click=on_ok)
    dialog.exec()
    return result["ok"]
