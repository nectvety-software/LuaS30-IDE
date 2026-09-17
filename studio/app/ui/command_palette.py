from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout


class CommandPalette(QDialog):
    def __init__(self, actions: list[QAction], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setObjectName("CommandPalette")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.resize(620, 360)

        self.actions = [a for a in actions if a and not a.isSeparator()]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.query = QLineEdit()
        self.query.setPlaceholderText("Type a command...")
        self.list = QListWidget()
        layout.addWidget(self.query)
        layout.addWidget(self.list, 1)

        self.query.textChanged.connect(self._refill)
        self.query.returnPressed.connect(self._activate_current)
        self.list.itemActivated.connect(lambda _item: self._activate_current())
        self._refill("")
        self.query.setFocus()

    def _refill(self, text: str) -> None:
        needle = text.strip().lower()
        self.list.clear()
        for action in self.actions:
            label = action.text().replace("&", "")
            shortcut = action.shortcut().toString()
            haystack = f"{label} {shortcut}".lower()
            if needle and needle not in haystack:
                continue
            item = QListWidgetItem(action.icon(), label)
            if shortcut:
                item.setText(f"{label}    {shortcut}")
            item.setData(Qt.ItemDataRole.UserRole, action)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _activate_current(self) -> None:
        item = self.list.currentItem()
        if not item:
            return
        action = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(action, QAction) and action.isEnabled():
            self.accept()
            action.trigger()
