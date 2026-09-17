from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

from app.core.paths import resolve_script, tool_python
from app.core.utf8 import decode_process_bytes, utf8_qprocess_environment


class EmulatorService(QObject):
    """Starts the SHA-verified VXP through LuaS30's emulator runner."""

    output = Signal(str)
    state_changed = Signal(str)
    launched = Signal(object)
    failed = Signal(str)

    def __init__(self, engine_root: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.engine_root = Path(engine_root).resolve()
        self.process: QProcess | None = None
        self.last_manifest: dict = {}

    def launch_manifest(self, manifest: dict | Path) -> bool:
        if isinstance(manifest, Path):
            path = manifest.resolve()
            if not path.is_file():
                self.failed.emit(f"Manifest not found: {path}")
                return False
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError) as exc:
                self.failed.emit(f"Invalid sync manifest: {exc}")
                return False
            data["_manifest_path"] = str(path)
        else:
            data = dict(manifest)

        vxp = Path(str(data.get("vxp", ""))).expanduser()
        expected = str(data.get("vxp_sha256", "")).strip()
        manifest_path = Path(str(data.get("_manifest_path") or ""))
        if not vxp.is_file():
            self.failed.emit(f"VXP not found: {vxp}")
            return False
        if not expected:
            self.failed.emit("sync_manifest.json has no VXP SHA-256.")
            return False

        runner = resolve_script(self.engine_root / "tools", "run_emulator")
        if not runner.is_file():
            self.failed.emit(f"Emulator runner not found: {runner}")
            return False

        proc = QProcess(self)
        self.process = proc
        proc.setWorkingDirectory(str(self.engine_root))
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(self._read)
        proc.finished.connect(lambda code, status: self._runner_finished(code))
        proc.setProcessEnvironment(utf8_qprocess_environment())

        args = [
            str(runner),
            "--vxp", str(vxp),
            "--sha256", expected,
        ]
        if manifest_path.is_file():
            args += ["--manifest", str(manifest_path)]

        self.last_manifest = data
        self.state_changed.emit("Launching")
        self.output.emit(f'> run_emulator.py --vxp "{vxp}" --sha256 {expected}\n')
        proc.start(tool_python(self.engine_root), args)
        if not proc.waitForStarted(3000):
            message = proc.errorString() or "Unable to start emulator runner."
            self.failed.emit(message)
            self.state_changed.emit("Error")
            self.process = None
            return False
        return True

    def stop(self) -> None:
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/IM", "VXPEmu.exe"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        self.state_changed.emit("Stopped")
        self.output.emit("[EMU] Stop requested.\n")

    def _read(self) -> None:
        if not self.process:
            return
        text = decode_process_bytes(self.process.readAllStandardOutput())
        if text:
            self.output.emit(text)

    def _runner_finished(self, exit_code: int) -> None:
        self._read()
        if exit_code == 0:
            self.state_changed.emit("Running")
            # run_emulator.py writes the emulator PID back to the manifest.
            path = Path(str(self.last_manifest.get("_manifest_path", "")))
            if path.is_file():
                try:
                    refreshed = json.loads(path.read_text(encoding="utf-8"))
                    refreshed["_manifest_path"] = str(path)
                    self.last_manifest = refreshed
                except Exception:
                    pass
            self.launched.emit(dict(self.last_manifest))
        else:
            message = f"Emulator runner exited with code {exit_code}."
            self.state_changed.emit("Error")
            self.failed.emit(message)
        if self.process:
            self.process.deleteLater()
        self.process = None
