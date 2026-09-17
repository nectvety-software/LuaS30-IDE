from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QTextCursor, QTextDocument
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton

from app.ui.icons import apply_icon


class FindReplaceBar(QFrame):
    closed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("FindBar")
        self.editor = None
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(6)
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Find")
        self.find_edit.setMaximumWidth(250)
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("Replace")
        self.replace_edit.setMaximumWidth(250)
        self.case_box = QCheckBox("Aa")
        self.word_box = QCheckBox("Word")
        self.count_label = QLabel("0/0")
        self.prev_btn = QPushButton("")
        apply_icon(self.prev_btn, "chevron_up", 13)
        self.next_btn = QPushButton("")
        apply_icon(self.next_btn, "chevron_down", 13)
        self.replace_btn = QPushButton("Replace")
        self.all_btn = QPushButton("All")
        self.close_btn = QPushButton("")
        apply_icon(self.close_btn, "close", 13)
        self.prev_btn.setToolTip("Previous match")
        self.next_btn.setToolTip("Next match")
        self.close_btn.setToolTip("Close Find/Replace")
        for b in (self.prev_btn, self.next_btn, self.close_btn):
            b.setFixedWidth(34)
        row.addWidget(self.find_edit)
        row.addWidget(self.replace_edit)
        row.addWidget(self.case_box)
        row.addWidget(self.word_box)
        row.addWidget(self.count_label)
        row.addWidget(self.prev_btn)
        row.addWidget(self.next_btn)
        row.addWidget(self.replace_btn)
        row.addWidget(self.all_btn)
        row.addStretch()
        row.addWidget(self.close_btn)

        self.find_edit.textChanged.connect(self._refresh)
        self.case_box.toggled.connect(self._refresh)
        self.word_box.toggled.connect(self._refresh)
        self.find_edit.returnPressed.connect(self.find_next)
        self.prev_btn.clicked.connect(self.find_previous)
        self.next_btn.clicked.connect(self.find_next)
        self.replace_btn.clicked.connect(self.replace_one)
        self.all_btn.clicked.connect(self.replace_all)
        self.close_btn.clicked.connect(self.hide_bar)
        self.hide()

    def set_editor(self, editor) -> None:
        if self.editor is editor:
            return
        if self.editor:
            self.editor.set_search_ranges([])
        self.editor = editor
        self._refresh()

    def show_find(self, replace: bool = False, seed: str = "") -> None:
        self.show()
        self.replace_edit.setVisible(replace)
        self.replace_btn.setVisible(replace)
        self.all_btn.setVisible(replace)
        if seed:
            self.find_edit.setText(seed)
        self.find_edit.setFocus()
        self.find_edit.selectAll()
        self._refresh()

    def hide_bar(self) -> None:
        if self.editor:
            self.editor.set_search_ranges([])
        self.hide()
        self.closed.emit()

    def _flags(self, backward: bool = False):
        flags = QTextDocument.FindFlag(0)
        if self.case_box.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.word_box.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        if backward:
            flags |= QTextDocument.FindFlag.FindBackward
        return flags

    def _all_ranges(self):
        if not self.editor or not self.find_edit.text():
            return []
        ranges: list[tuple[int, int]] = []
        doc = self.editor.document()
        cursor = QTextCursor(doc)
        while True:
            found = doc.find(self.find_edit.text(), cursor, self._flags())
            if found.isNull():
                break
            ranges.append((found.selectionStart(), found.selectionEnd()))
            cursor.setPosition(found.selectionEnd())
            if len(ranges) >= 3000:
                break
        return ranges

    def _refresh(self) -> None:
        ranges = self._all_ranges()
        if self.editor:
            self.editor.set_search_ranges(ranges)
        self.count_label.setText(f"{len(ranges)} match" + ("es" if len(ranges) != 1 else ""))

    def _find(self, backward: bool) -> None:
        if not self.editor or not self.find_edit.text():
            return
        doc = self.editor.document()
        cursor = self.editor.textCursor()
        found = doc.find(self.find_edit.text(), cursor, self._flags(backward))
        if found.isNull():
            start = QTextCursor(doc)
            start.movePosition(QTextCursor.MoveOperation.End if backward else QTextCursor.MoveOperation.Start)
            found = doc.find(self.find_edit.text(), start, self._flags(backward))
        if not found.isNull():
            self.editor.setTextCursor(found)
            self.editor.ensureCursorVisible()

    def find_next(self) -> None:
        self._find(False)

    def find_previous(self) -> None:
        self._find(True)

    def replace_one(self) -> None:
        if not self.editor:
            return
        cursor = self.editor.textCursor()
        selected = cursor.selectedText()
        expected = self.find_edit.text()
        same = selected == expected if self.case_box.isChecked() else selected.lower() == expected.lower()
        if same and expected:
            cursor.insertText(self.replace_edit.text())
            self.editor.setTextCursor(cursor)
        else:
            self.find_next()
        self._refresh()

    def replace_all(self) -> None:
        if not self.editor or not self.find_edit.text():
            return
        ranges = self._all_ranges()
        if not ranges:
            return
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        # Reverse order keeps offsets stable.
        for start, end in reversed(ranges):
            c = QTextCursor(self.editor.document())
            c.setPosition(start)
            c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            c.insertText(self.replace_edit.text())
        cursor.endEditBlock()
        self._refresh()
