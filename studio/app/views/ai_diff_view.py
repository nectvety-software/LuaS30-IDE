from __future__ import annotations

import difflib
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPlainTextEdit,
    QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from app.services.ai_change_service import PreparedChange, PreparedChangeSet
from app.ui import palette
from app.ui.icons import apply_icon


class _DiffText(QPlainTextEdit):
    def __init__(self, object_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def set_changed_lines(self, lines: set[int], background: str) -> None:
        selections = []
        for number in sorted(lines):
            block = self.document().findBlockByNumber(number)
            if not block.isValid():
                continue
            selection = QPlainTextEdit.ExtraSelection()
            selection.cursor = QTextCursor(block)
            selection.cursor.clearSelection()
            fmt = QTextCharFormat()
            fmt.setBackground(QColor(background))
            fmt.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
            selection.format = fmt
            selections.append(selection)
        self.setExtraSelections(selections)


def _changed_line_sets(before: str, after: str) -> tuple[set[int], set[int]]:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    left: set[int] = set()
    right: set[int] = set()
    matcher = difflib.SequenceMatcher(a=before_lines, b=after_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in {"replace", "delete"}:
            left.update(range(i1, i2))
        if tag in {"replace", "insert"}:
            right.update(range(j1, j2))
    return left, right


class AIDiffView(QWidget):
    apply_all_requested = Signal()
    reject_all_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("AIDiffView")
        self.change_set: PreparedChangeSet | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        toolbar = QFrame()
        toolbar.setObjectName("AIDiffToolbar")
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(8, 5, 8, 5)
        row.setSpacing(6)

        title = QLabel("AI CODE CHANGES")
        title.setObjectName("AIDiffTitle")
        row.addWidget(title)
        self.summary = QLabel("No pending changes")
        self.summary.setObjectName("AIDiffSummary")
        row.addWidget(self.summary, 1)

        self.reject_button = QPushButton("Reject")
        self.reject_button.setObjectName("AIDiffReject")
        apply_icon(self.reject_button, "close", 13)
        self.reject_button.clicked.connect(self.reject_all_requested)
        row.addWidget(self.reject_button)

        self.apply_button = QPushButton("Apply Code")
        self.apply_button.setObjectName("AIDiffApply")
        apply_icon(self.apply_button, "save", 13)
        self.apply_button.clicked.connect(self.apply_all_requested)
        row.addWidget(self.apply_button)
        root.addWidget(toolbar)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setHandleWidth(2)

        self.files = QListWidget()
        self.files.setObjectName("AIDiffFiles")
        self.files.setMinimumWidth(190)
        self.files.setMaximumWidth(300)
        self.files.currentRowChanged.connect(self._show_row)
        split.addWidget(self.files)

        editors = QSplitter(Qt.Orientation.Horizontal)
        editors.setHandleWidth(2)

        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        self.before_label = QLabel("CURRENT")
        self.before_label.setObjectName("AIDiffPaneTitle")
        left_layout.addWidget(self.before_label)
        self.before = _DiffText("AIDiffBefore")
        left_layout.addWidget(self.before, 1)
        editors.addWidget(left_frame)

        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        self.after_label = QLabel("PROPOSED")
        self.after_label.setObjectName("AIDiffPaneTitle")
        right_layout.addWidget(self.after_label)
        self.after = _DiffText("AIDiffAfter")
        right_layout.addWidget(self.after, 1)
        editors.addWidget(right_frame)
        editors.setSizes([1, 1])

        split.addWidget(editors)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([220, 1000])
        root.addWidget(split, 1)

        self.status = QLabel(
            "AI changes are only written after Apply Code unless the selected access mode permits automatic edits."
        )
        self.status.setObjectName("AIDiffStatus")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        self.set_change_set(None)

    def set_change_set(self, change_set: PreparedChangeSet | None) -> None:
        self.change_set = change_set
        self.files.clear()
        enabled = bool(change_set and change_set.changes)
        self.apply_button.setEnabled(enabled)
        self.reject_button.setEnabled(enabled)
        if not enabled:
            self.summary.setText("No pending changes")
            self.before.clear()
            self.after.clear()
            self.before_label.setText("CURRENT")
            self.after_label.setText("PROPOSED")
            return

        self.summary.setText(change_set.summary())
        for item in change_set.changes:
            prefix = "+" if not item.existed else "~"
            row = QListWidgetItem(
                f"{prefix} {item.relative_path}\n+{item.added_lines} -{item.removed_lines}"
            )
            row.setToolTip(item.reason or item.relative_path)
            self.files.addItem(row)
        self.files.setCurrentRow(0)

    def current_change(self) -> PreparedChange | None:
        if not self.change_set:
            return None
        row = self.files.currentRow()
        if 0 <= row < len(self.change_set.changes):
            return self.change_set.changes[row]
        return None

    def _show_row(self, _row: int) -> None:
        item = self.current_change()
        if not item:
            self.before.clear()
            self.after.clear()
            return
        self.before_label.setText(f"CURRENT · {item.relative_path}")
        self.after_label.setText(f"PROPOSED · {item.relative_path}")
        self.before.setPlainText(item.before)
        self.after.setPlainText(item.after)
        left, right = _changed_line_sets(item.before, item.after)
        self.before.set_changed_lines(left, palette.DIFF_REMOVED_BG)
        self.after.set_changed_lines(right, palette.DIFF_ADDED_BG)

    def mark_applied(self, backup_dir: Path | None = None) -> None:
        self.apply_button.setEnabled(False)
        self.reject_button.setEnabled(False)
        message = "Applied AI code changes."
        if backup_dir:
            message += f" Backup: {backup_dir}"
        self.status.setText(message)

    def mark_rejected(self) -> None:
        self.apply_button.setEnabled(False)
        self.reject_button.setEnabled(False)
        self.status.setText("AI code changes were rejected; project files were not modified.")
