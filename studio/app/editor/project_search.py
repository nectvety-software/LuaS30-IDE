from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout,
)

from .project_index import IGNORE_DIRS


class SearchWorker(QThread):
    result = Signal(object)
    done = Signal(int)

    def __init__(self, root: Path, query: str, pattern: str, case_sensitive: bool, whole_word: bool) -> None:
        super().__init__()
        self.root = root
        self.query = query
        self.pattern = pattern or "*.lua"
        self.case_sensitive = case_sensitive
        self.whole_word = whole_word

    def run(self) -> None:
        flags = 0 if self.case_sensitive else re.IGNORECASE
        expr = re.escape(self.query)
        if self.whole_word:
            expr = r"\b" + expr + r"\b"
        regex = re.compile(expr, flags)
        count = 0
        patterns = [p.strip() for p in self.pattern.split(";") if p.strip()] or ["*.lua"]
        for path in self.root.rglob("*"):
            if self.isInterruptionRequested():
                break
            if not path.is_file():
                continue
            rel = path.relative_to(self.root)
            if any(part in IGNORE_DIRS for part in rel.parts[:-1]):
                continue
            if not any(fnmatch.fnmatch(path.name, pat) for pat in patterns):
                continue
            if path.stat().st_size > 2_000_000:
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line_no, text in enumerate(lines, 1):
                match = regex.search(text)
                if match:
                    self.result.emit((path, line_no, match.start() + 1, text.strip()))
                    count += 1
                    if count >= 5000:
                        self.done.emit(count)
                        return
        self.done.emit(count)


class ProjectSearchPanel(QFrame):
    open_result = Signal(object, int, int)
    status_message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.root: Path | None = None
        self.worker: SearchWorker | None = None
        col = QVBoxLayout(self)
        col.setContentsMargins(8, 8, 8, 8)
        col.setSpacing(6)
        title = QLabel("SEARCH PROJECT")
        title.setObjectName("SectionTitle")
        self.query = QLineEdit()
        self.query.setPlaceholderText("Search text")
        self.pattern = QLineEdit("*.lua")
        self.pattern.setPlaceholderText("Files: *.lua;*.json")
        opts = QHBoxLayout()
        self.case = QCheckBox("Aa")
        self.word = QCheckBox("Word")
        self.search_btn = QPushButton("Search")
        self.search_btn.setObjectName("PrimaryButton")
        opts.addWidget(self.case)
        opts.addWidget(self.word)
        opts.addStretch()
        opts.addWidget(self.search_btn)
        self.results = QTreeWidget()
        self.results.setHeaderLabels(["File / line", "Preview"])
        self.results.setColumnWidth(0, 150)
        col.addWidget(title)
        col.addWidget(self.query)
        col.addWidget(self.pattern)
        col.addLayout(opts)
        col.addWidget(self.results, 1)
        self.search_btn.clicked.connect(self.start_search)
        self.query.returnPressed.connect(self.start_search)
        self.results.itemActivated.connect(self._activate)

    def set_root(self, root: str | Path) -> None:
        self.root = Path(root).resolve()


    def clear_root(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
        self.root = None
        self.results.clear()

    def focus_query(self, seed: str = "") -> None:
        if seed:
            self.query.setText(seed)
        self.query.setFocus()
        self.query.selectAll()

    def start_search(self) -> None:
        if not self.root or not self.query.text().strip():
            return
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            if not self.worker.wait(1500):
                self.status_message.emit("Previous search is still stopping…")
                return
        self.results.clear()
        self.search_btn.setEnabled(False)
        self.search_btn.setText("Searching…")
        self.worker = SearchWorker(
            self.root, self.query.text(), self.pattern.text(), self.case.isChecked(), self.word.isChecked()
        )
        self.worker.result.connect(self._add_result)
        self.worker.done.connect(self._finished)
        self.worker.start()

    def _add_result(self, result) -> None:
        path, line, column, preview = result
        rel = path.relative_to(self.root) if self.root else path
        item = QTreeWidgetItem([f"{rel}:{line}", preview])
        item.setData(0, 0x0100, (str(path), line, column))
        self.results.addTopLevelItem(item)

    def _finished(self, count: int) -> None:
        self.search_btn.setEnabled(True)
        self.search_btn.setText("Search")
        self.status_message.emit(f"Project search: {count} result(s)")

    def _activate(self, item: QTreeWidgetItem, _column: int) -> None:
        data = item.data(0, 0x0100)
        if data:
            path, line, column = data
            self.open_result.emit(Path(path), int(line), int(column))
