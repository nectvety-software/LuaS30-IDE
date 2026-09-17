from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from app.core.paths import resolve_script, tool_python
from app.core.utf8 import decode_process_bytes, utf8_qprocess_environment
from app.ui.icons import apply_icon


class ToolchainDoctorView(QWidget):
    def __init__(self, engine_root: Path, parent=None) -> None:
        super().__init__(parent)
        self.engine_root = Path(engine_root).resolve()
        self.process: QProcess | None = None
        self.compiler_profile = "auto"
        self.toolchain_root = self.engine_root / "toolchain" / "arm-gcc"

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 7, 10, 10)
        root.setSpacing(6)
        header = QHBoxLayout()
        title = QLabel("TOOLCHAIN DOCTOR")
        title.setObjectName("ViewTitle")
        self.state = QLabel("Ready")
        self.state.setObjectName("Muted")
        run = QPushButton("Run Diagnostics")
        apply_icon(run, "play", 14)
        run.clicked.connect(self.run)
        header.addWidget(title)
        header.addWidget(self.state, 1)
        header.addWidget(run)
        root.addLayout(header)

        self.log = QPlainTextEdit()
        self.log.setObjectName("LogView")
        self.log.setReadOnly(True)
        root.addWidget(self.log, 1)

    def set_toolchain(self, root: Path | str, profile: str = "auto") -> None:
        self.toolchain_root = Path(root).expanduser().resolve()
        self.compiler_profile = str(profile or "auto")

    def run(self) -> None:
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            return
        script = resolve_script(self.engine_root / "tools", "toolchain_doctor")
        toolchain = self.toolchain_root
        self.log.clear()
        self.state.setText("Running...")
        proc = QProcess(self)
        self.process = proc
        proc.setWorkingDirectory(str(self.engine_root))
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(self._read)
        proc.finished.connect(self._finished)
        proc.setProcessEnvironment(utf8_qprocess_environment())
        proc.start(
            tool_python(self.engine_root),
            [
                str(script),
                "--toolchain", str(toolchain),
                "--profile", self.compiler_profile,
            ],
        )

    def _read(self) -> None:
        if not self.process:
            return
        text = decode_process_bytes(self.process.readAllStandardOutput())
        if text:
            self.log.appendPlainText(text.rstrip("\n"))

    def _finished(self, code: int, _status) -> None:
        self._read()
        self.state.setText("PASS" if code == 0 else f"FAIL ({code})")
        if self.process:
            self.process.deleteLater()
        self.process = None
