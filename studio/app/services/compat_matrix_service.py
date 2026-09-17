from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

from app.core.paths import resolve_script, tool_python
from app.core.utf8 import decode_process_bytes, utf8_qprocess_environment


class CompatMatrixService(QObject):
    started = Signal()
    output = Signal(str)
    finished = Signal(bool, int, object)

    def __init__(self, engine_root: Path, parent=None) -> None:
        super().__init__(parent)
        self.engine_root = Path(engine_root).resolve()
        self.process: QProcess | None = None

    @property
    def active(self) -> bool:
        return bool(self.process and self.process.state() != QProcess.ProcessState.NotRunning)

    def start(self) -> bool:
        if self.active:
            return False
        script = resolve_script(self.engine_root / "tools", "runtime_compat_matrix")
        out = self.engine_root / "build" / "runtime_compat_matrix"
        if not script.is_file():
            raise FileNotFoundError(script)

        proc = QProcess(self)
        self.process = proc
        proc.setWorkingDirectory(str(self.engine_root))
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(self._read)
        proc.finished.connect(self._finished)
        proc.setProcessEnvironment(utf8_qprocess_environment())
        proc.start(tool_python(self.engine_root), [str(script), "--out", str(out)])
        if not proc.waitForStarted(3000):
            message = proc.errorString() or "Unable to start compatibility matrix."
            self.output.emit(f"[COMPAT] {message}\n")
            self.process = None
            raise RuntimeError(message)
        self.started.emit()
        return True

    def _read(self) -> None:
        if not self.process:
            return
        text = decode_process_bytes(self.process.readAllStandardOutput())
        if text:
            self.output.emit(text)

    def _finished(self, exit_code: int, _status) -> None:
        self._read()
        report = self.engine_root / "build" / "runtime_compat_matrix" / "runtime_compat_matrix.json"
        self.finished.emit(exit_code == 0, int(exit_code), report)
        if self.process:
            self.process.deleteLater()
        self.process = None
