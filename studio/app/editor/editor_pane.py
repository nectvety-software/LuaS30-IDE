from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QWidget

from .code_editor import CodeEditor
from .minimap import MiniMap


class EditorPane(QWidget):
    def __init__(self, path: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.editor = CodeEditor(path, self)
        self.minimap = MiniMap(self.editor, self)
        row.addWidget(self.editor, 1)
        row.addWidget(self.minimap)
