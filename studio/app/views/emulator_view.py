from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.ui.icons import apply_icon


class EmulatorView(QWidget):
    run_last_requested = Signal()
    stop_requested = Signal()
    open_build_folder_requested = Signal()
    open_emulator_folder_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.project_root: Path | None = None
        self.manifest: dict = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 6, 10, 10)
        root.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("EMULATOR")
        title.setObjectName("ViewTitle")
        header.addWidget(title)
        header.addStretch(1)

        run = QPushButton("Run Last Build")
        apply_icon(run, "play", 14)
        stop = QPushButton("Stop")
        apply_icon(stop, "stop", 14)
        run.clicked.connect(self.run_last_requested)
        stop.clicked.connect(self.stop_requested)
        header.addWidget(run)
        header.addWidget(stop)
        root.addLayout(header)

        panel = QFrame()
        panel.setObjectName("Panel")
        form = QFormLayout(panel)
        form.setContentsMargins(10, 8, 10, 8)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(7)

        self.state = QLabel("Idle")
        self.vxp = QLabel("No build artifact")
        self.vxp.setTextInteractionFlags(self.vxp.textInteractionFlags())
        self.sha = QLabel("-")
        self.pid = QLabel("-")
        self.profile = QLabel("-")

        form.addRow("State", self.state)
        form.addRow("VXP", self.vxp)
        form.addRow("SHA-256", self.sha)
        form.addRow("Process", self.pid)
        form.addRow("Runtime", self.profile)
        root.addWidget(panel)

        path_row = QHBoxLayout()
        build_folder = QPushButton("Open Build Folder")
        apply_icon(build_folder, "folder_open", 14)
        emu_folder = QPushButton("Open Emulator Folder")
        apply_icon(emu_folder, "folder_open", 14)
        build_folder.clicked.connect(self.open_build_folder_requested)
        emu_folder.clicked.connect(self.open_emulator_folder_requested)
        path_row.addWidget(build_folder)
        path_row.addWidget(emu_folder)
        path_row.addStretch(1)
        root.addLayout(path_row)
        root.addStretch(1)

    def set_project(self, root: Path | None) -> None:
        self.project_root = Path(root).resolve() if root else None
        self.manifest = {}
        self.vxp.setText("No build artifact")
        self.sha.setText("-")
        self.pid.setText("-")
        self.profile.setText("Generic MRE/VXP")

    def set_state(self, state: str) -> None:
        self.state.setText(state)

    def set_manifest(self, data: dict) -> None:
        self.manifest = dict(data)
        self.vxp.setText(Path(str(data.get("vxp", ""))).name or "No build artifact")
        self.vxp.setToolTip(str(data.get("vxp", "")))
        sha = str(data.get("vxp_sha256", ""))
        self.sha.setText((sha[:16] + "...") if len(sha) > 18 else (sha or "-"))
        self.sha.setToolTip(sha)
        pid = data.get("emulator_pid")
        self.pid.setText(str(pid) if pid else "-")
        self.profile.setText("Generic MRE/VXP")
