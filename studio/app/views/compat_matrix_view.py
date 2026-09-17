from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QPlainTextEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.ui.icons import apply_icon


class CompatMatrixView(QWidget):
    run_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 7, 10, 10)
        root.setSpacing(6)
        header = QHBoxLayout()
        title = QLabel("RUNTIME COMPATIBILITY MATRIX")
        title.setObjectName("ViewTitle")
        self.summary = QLabel("Not run")
        self.summary.setObjectName("Muted")
        run = QPushButton("Run Matrix")
        apply_icon(run, "play", 14)
        run.clicked.connect(self.run_requested)
        header.addWidget(title)
        header.addWidget(self.summary, 1)
        header.addWidget(run)
        root.addLayout(header)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Firmware", "Native Caps", "ABI Aliases", "Fallbacks", "Missing", "Level", "Result"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 240)
        self.table.setColumnWidth(2, 250)
        self.table.setColumnWidth(3, 250)
        self.table.setColumnWidth(4, 130)
        self.table.setColumnWidth(5, 90)
        self.table.setColumnWidth(6, 90)
        root.addWidget(self.table, 1)

        self.log = QPlainTextEdit()
        self.log.setObjectName("LogView")
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(125)
        root.addWidget(self.log)

    def clear_log(self) -> None:
        self.log.clear()

    def append_output(self, text: str) -> None:
        if text:
            self.log.appendPlainText(text.rstrip("\n"))

    def set_running(self) -> None:
        self.summary.setText("Running...")
        self.clear_log()

    def load_report(self, path: Path) -> None:
        path = Path(path)
        if not path.is_file():
            self.summary.setText("Report not found")
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("firmwares", [])
        self.table.setRowCount(0)
        for row_data in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            aliases = row_data.get("abi_aliases", [])
            alias_text = "; ".join(f'{a.get("field")}:{a.get("selected")}' for a in aliases) or "-"
            values = [
                str(row_data.get("id") or row_data.get("firmware") or "-"),
                ", ".join(row_data.get("native_capabilities", [])) or "-",
                alias_text,
                ", ".join(row_data.get("fallbacks", [])) or "-",
                ", ".join(row_data.get("missing_required", [])) or "-",
                str(row_data.get("compatibility_level") or "-"),
                str(row_data.get("final_result") or "-"),
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        summary = payload.get("summary", {})
        self.summary.setText(
            f'{summary.get("total", len(rows))} firmware rows · '
            f'PASS {summary.get("pass", 0)} · DEGRADED {summary.get("degraded", 0)} · FAIL {summary.get("fail", 0)}'
        )
