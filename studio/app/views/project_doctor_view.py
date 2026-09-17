from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.services.project_doctor import inspect_project
from app.ui.icons import apply_icon


class ProjectDoctorView(QWidget):
    def __init__(self, engine_root: Path, project: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self.engine_root = Path(engine_root).resolve()
        self.project: Path | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 7, 10, 10)
        root.setSpacing(6)
        header = QHBoxLayout()
        title = QLabel("PROJECT DOCTOR")
        title.setObjectName("ViewTitle")
        self.summary = QLabel("Open a project to run checks")
        self.summary.setObjectName("Muted")
        refresh = QPushButton("Run Checks")
        apply_icon(refresh, "refresh", 14)
        refresh.clicked.connect(self.refresh)
        header.addWidget(title)
        header.addWidget(self.summary, 1)
        header.addWidget(refresh)
        root.addLayout(header)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Severity", "Check"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 90)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        root.addWidget(self.table, 1)

        if project:
            self.set_project(project)

    def set_project(self, project: Path | None) -> None:
        self.project = Path(project).resolve() if project else None
        self.refresh()

    def refresh(self) -> None:
        self.table.setRowCount(0)
        if not self.project:
            self.summary.setText("No project open")
            return
        report = inspect_project(self.project, self.engine_root)
        for issue in report.issues:
            row = self.table.rowCount()
            self.table.insertRow(row)
            severity = QTableWidgetItem(issue.severity)
            message = QTableWidgetItem(issue.message)
            self.table.setItem(row, 0, severity)
            self.table.setItem(row, 1, message)
        self.summary.setText(f"{self.project.name}: {report.errors} errors, {report.warnings} warnings")
