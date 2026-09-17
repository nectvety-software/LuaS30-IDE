from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QTextCursor
from PySide6.QtWidgets import QWidget

from app.ui import palette

class MiniMap(QWidget):
    """Low-overhead source minimap. It paints text directly instead of creating a second document."""

    def __init__(self, editor=None, parent=None) -> None:
        super().__init__(parent)
        self.editor = None
        self.setFixedWidth(118)
        self.setMinimumWidth(90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if editor:
            self.set_editor(editor)

    def set_editor(self, editor) -> None:
        if self.editor is not None:
            try:
                self.editor.textChanged.disconnect(self.update)
                self.editor.verticalScrollBar().valueChanged.disconnect(self.update)
            except (RuntimeError, TypeError):
                pass
        self.editor = editor
        if editor is not None:
            editor.textChanged.connect(self.update)
            editor.verticalScrollBar().valueChanged.connect(self.update)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(palette.BG_INK))
        if not self.editor:
            return
        doc = self.editor.document()
        line_count = max(1, doc.blockCount())
        height = max(1, self.height() - 8)
        line_h = max(1.0, min(3.0, height / line_count))
        font = QFont("Cascadia Code")
        font.setPixelSize(3)
        painter.setFont(font)
        painter.setPen(QColor(palette.TEXT_5))

        block = doc.firstBlock()
        line = 0
        while block.isValid() and line < 2500:
            y = 4 + int(line * line_h)
            if y > self.height():
                break
            text = block.text().replace("\t", "    ")[:80]
            if text.strip():
                painter.drawText(3, y + 3, text)
            block = block.next()
            line += 1

        scroll = self.editor.verticalScrollBar()
        maximum = max(1, scroll.maximum() + scroll.pageStep())
        top_ratio = scroll.value() / maximum
        page_ratio = min(1.0, scroll.pageStep() / maximum)
        y = int(top_ratio * self.height())
        h = max(18, int(page_ratio * self.height()))
        painter.setPen(QPen(QColor(palette.ACCENT), 1))
        painter.fillRect(0, y, self.width() - 1, h, QColor(33, 126, 220, 45))
        painter.drawRect(0, y, self.width() - 2, h)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if not self.editor or event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        ratio = max(0.0, min(1.0, event.position().y() / max(1, self.height())))
        target_line = int(ratio * max(0, self.editor.document().blockCount() - 1))
        block = self.editor.document().findBlockByNumber(target_line)
        if block.isValid():
            cursor = QTextCursor(block)
            self.editor.setTextCursor(cursor)
            self.editor.centerCursor()
        event.accept()
