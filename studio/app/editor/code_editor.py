from __future__ import annotations

import re
from pathlib import Path

from app.ui import palette
from PySide6.QtCore import QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QTextCharFormat, QTextCursor, QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from .completion import LuaCompletionController
from .diagnostics import Diagnostic, LuaSyntaxAnalyzer, Severity
from .lua_highlighter import LuaHighlighter


class LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:  # noqa: N802
        self.editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    cursor_info_changed = Signal(int, int, int)
    diagnostics_changed = Signal(object)
    go_to_definition_requested = Signal(str, object)
    request_find = Signal(bool)

    def __init__(self, path: Path | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("CodeEditor")
        self.path = path
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setCenterOnScroll(True)
        self.setMouseTracking(True)

        font = QFont("Cascadia Code")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(10)
        self.setFont(font)

        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self._cursor_changed)
        self.cursorPositionChanged.connect(self._refresh_extra_selections)
        self.update_line_number_area_width(0)

        self.highlighter: LuaHighlighter | None = None
        if path and path.suffix.lower() == ".lua":
            self.highlighter = LuaHighlighter(self.document())

        self.completion = LuaCompletionController(self)
        self._analyzer = LuaSyntaxAnalyzer()
        self._diagnostics: list[Diagnostic] = []
        self._search_ranges: list[tuple[int, int]] = []
        self._diagnostic_timer = QTimer(self)
        self._diagnostic_timer.setSingleShot(True)
        self._diagnostic_timer.setInterval(350)
        self._diagnostic_timer.timeout.connect(self._run_diagnostics)
        self.textChanged.connect(self._on_text_changed)

    @property
    def display_name(self) -> str:
        return self.path.name if self.path else "Untitled"

    @property
    def diagnostics(self) -> list[Diagnostic]:
        return list(self._diagnostics)

    def attach_path(self, path: Path) -> None:
        self.path = path
        if path.suffix.lower() == ".lua" and self.highlighter is None:
            self.highlighter = LuaHighlighter(self.document())
        self._schedule_diagnostics()

    def line_number_area_width(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _new_block_count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event) -> None:
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(palette.BG_ALT))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        current = self.textCursor().blockNumber()
        error_lines = {d.line - 1 for d in self._diagnostics if d.severity == Severity.ERROR}

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                if block_number in error_lines:
                    painter.setPen(QColor(palette.RED))
                else:
                    painter.setPen(QColor(palette.TEXT_3) if block_number == current else QColor(palette.TEXT_5))
                painter.drawText(
                    0, top, self.line_number_area.width() - 7, self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def _cursor_changed(self) -> None:
        cursor = self.textCursor()
        self.cursor_info_changed.emit(
            cursor.blockNumber() + 1, cursor.positionInBlock() + 1, len(cursor.selectedText())
        )

    def _on_text_changed(self) -> None:
        self.completion.refresh_document_symbols(self.toPlainText())
        self._schedule_diagnostics()

    def _schedule_diagnostics(self) -> None:
        if self.path is None or self.path.suffix.lower() == ".lua":
            self._diagnostic_timer.start()
        else:
            self._diagnostics = []
            self.diagnostics_changed.emit([])
            self._refresh_extra_selections()

    def _run_diagnostics(self) -> None:
        self._diagnostics = self._analyzer.analyze(self.toPlainText())
        self.diagnostics_changed.emit(list(self._diagnostics))
        self._refresh_extra_selections()
        self.line_number_area.update()

    def set_search_ranges(self, ranges: list[tuple[int, int]]) -> None:
        self._search_ranges = list(ranges)
        self._refresh_extra_selections()

    def _refresh_extra_selections(self) -> None:
        selections: list[QTextEdit.ExtraSelection] = []

        current = QTextEdit.ExtraSelection()
        current.format.setBackground(QColor(palette.BG_ALT))
        current.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        current.cursor = self.textCursor()
        current.cursor.clearSelection()
        selections.append(current)

        search_fmt = QTextCharFormat()
        search_fmt.setBackground(QColor(palette.AMBER_DEEP))
        search_fmt.setForeground(QColor(palette.TEXT))
        for start, end in self._search_ranges[:1000]:
            c = QTextCursor(self.document())
            c.setPosition(start)
            c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            sel = QTextEdit.ExtraSelection()
            sel.cursor = c
            sel.format = search_fmt
            selections.append(sel)

        for d in self._diagnostics[:200]:
            block = self.document().findBlockByNumber(max(0, d.line - 1))
            if not block.isValid():
                continue
            c = QTextCursor(block)
            pos = block.position() + max(0, d.column - 1)
            c.setPosition(min(pos, block.position() + max(0, block.length() - 1)))
            c.setPosition(
                min(c.position() + max(1, d.length), block.position() + max(0, block.length() - 1)),
                QTextCursor.MoveMode.KeepAnchor,
            )
            fmt = QTextCharFormat()
            fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
            fmt.setUnderlineColor(QColor(palette.RED if d.severity == Severity.ERROR else palette.AMBER))
            sel = QTextEdit.ExtraSelection()
            sel.cursor = c
            sel.format = fmt
            selections.append(sel)

        self.setExtraSelections(selections)

    def symbol_under_cursor(self) -> str:
        cursor = self.textCursor()
        block = cursor.block().text()
        col = cursor.positionInBlock()
        left = col
        right = col
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:")
        while left > 0 and block[left - 1] in allowed:
            left -= 1
        while right < len(block) and block[right] in allowed:
            right += 1
        return block[left:right].strip(".:")

    def goto_line(self, line: int, column: int = 1, center: bool = True) -> None:
        block = self.document().findBlockByNumber(max(0, line - 1))
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        cursor.setPosition(min(block.position() + max(0, column - 1), block.position() + block.length() - 1))
        self.setTextCursor(cursor)
        if center:
            self.centerCursor()
        self.setFocus()

    def go_to_definition(self) -> None:
        symbol = self.symbol_under_cursor()
        if symbol:
            self.go_to_definition_requested.emit(symbol, self.path)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if self.completion.popup_visible() and event.key() in (
            Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Tab, Qt.Key.Key_Backtab
        ):
            event.ignore()
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Space:
            self.completion.show(force=True)
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_F:
            self.request_find.emit(False)
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_H:
            self.request_find.emit(True)
            return
        if event.key() == Qt.Key.Key_F12:
            self.go_to_definition()
            return
        if event.key() == Qt.Key.Key_Tab and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.insertPlainText("    ")
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            current_line = cursor.block().text()
            indent = current_line[: len(current_line) - len(current_line.lstrip(" \t"))]
            stripped = current_line.strip()
            opens_block = (
                stripped.endswith(" then") or stripped.endswith(" do")
                or stripped.startswith("function ") or stripped.startswith("local function ")
                or stripped == "repeat"
            )
            super().keyPressEvent(event)
            self.insertPlainText(indent + ("    " if opens_block else ""))
            return

        typed = event.text()
        super().keyPressEvent(event)
        if typed == ".":
            self.completion.show(force=True)
        elif typed and (typed[-1].isalnum() or typed[-1] == "_"):
            self.completion.show(force=False)
        elif event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self.completion.show(force=False)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        super().mouseDoubleClickEvent(event)
