from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.ui.icons import apply_icon


class WelcomeView(QWidget):
    new_project_requested = Signal()
    open_project_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(42, 36, 42, 36)
        root.setSpacing(10)
        root.addStretch(1)

        title = QLabel("LuaS30 IDE")
        title.setObjectName("WelcomeTitle")
        subtitle = QLabel("Open a project to start editing, building and testing VXP applications.")
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)

        row = QHBoxLayout()
        row.setSpacing(8)
        new_btn = QPushButton("New Project")
        apply_icon(new_btn, "add", 15)
        open_btn = QPushButton("Open Folder")
        apply_icon(open_btn, "folder_open", 15)
        new_btn.clicked.connect(self.new_project_requested)
        open_btn.clicked.connect(self.open_project_requested)
        row.addWidget(new_btn)
        row.addWidget(open_btn)
        row.addStretch(1)

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(8)
        root.addLayout(row)
        root.addStretch(2)
