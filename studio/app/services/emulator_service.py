from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from app.core.paths import resolve_script, tool_python
from app.core.utf8 import decode_process_bytes, utf8_qprocess_environment
from app.services.build_service import kill_process_tree

_STILL_ACTIVE = 259
_WATCH_INTERVAL_MS = 2000


def pid_alive(pid: int) -> bool:
    """True khi PID con song. Windows: GetExitCodeProcess (chinh xac hon
    os.kill(pid, 0) — ham do van bao OK sau khi tien trinh chet)."""
    if not pid or pid <= 0:
        return False
    if os.name != "nt":
        return True
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, int(pid))
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == _STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return False


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
        self._watched_pid = 0
        self._watcher = QTimer(self)
        self._watcher.setInterval(_WATCH_INTERVAL_MS)
        self._watcher.timeout.connect(self._watch_tick)

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

        self._stop_watching()

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
        self._stop_watching()
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            pid = int(self.process.processId() or 0)
            # run_emulator.py spawn VXPEmu.exe làm con. Giết đúng CÂY theo PID
            # (thay vì /IM VXPEmu.exe toàn cục, vốn có thể tắt cả instance
            # không liên quan) rồi mới kill() python cha.
            kill_process_tree(pid)
            self.process.kill()
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
            self._start_watching()
        else:
            message = f"Emulator runner exited with code {exit_code}."
            self.state_changed.emit("Error")
            self.failed.emit(message)
        if self.process:
            self.process.deleteLater()
        self.process = None

    def _start_watching(self) -> None:
        """Canh PID VXPEmu that: tat/crash -> bao Stopped thay vi ket Running."""
        self._stop_watching()
        try:
            pid = int(self.last_manifest.get("emulator_pid") or 0)
        except (TypeError, ValueError):
            pid = 0
        if pid <= 0 or os.name != "nt":
            return
        self._watched_pid = pid
        self._watcher.start()

    def _stop_watching(self) -> None:
        self._watcher.stop()
        self._watched_pid = 0

    def _watch_tick(self) -> None:
        if self._watched_pid and pid_alive(self._watched_pid):
            return
        self._stop_watching()
        self.output.emit("[EMU] VXPEmu đã thoát (đóng cửa sổ hoặc crash). Trạng thái: Stopped.\n")
        self.state_changed.emit("Stopped")
