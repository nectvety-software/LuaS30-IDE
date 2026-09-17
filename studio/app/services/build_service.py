from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

from app.core.utf8 import decode_process_bytes, utf8_qprocess_environment


class BuildService(QObject):
    """Runs the actual LuaS30 builder and exposes structured IDE signals."""

    started = Signal()
    output = Signal(str)
    stage_changed = Signal(str)
    finished = Signal(bool, int, object)

    def __init__(self, engine_root: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.engine_root = Path(engine_root).resolve()
        self.process: QProcess | None = None
        self.project: Path | None = None
        self._buffer = ""
        self.compiler_profile = "auto"
        self.toolchain_root = self.engine_root / "toolchain" / "arm-gcc"
        self.compat_profile = "auto"
        self.mre_sdk_root: Path | None = None
        self.device_imsi = ""

    @property
    def active(self) -> bool:
        return bool(
            self.process
            and self.process.state() != QProcess.ProcessState.NotRunning
        )

    def set_compiler_profile(self, profile: str) -> None:
        profile = str(profile or "auto").lower()
        if profile not in {"auto", "gcc", "rvds", "ads12"}:
            profile = "auto"
        self.compiler_profile = profile

    def set_toolchain_root(self, root: Path | str) -> None:
        self.toolchain_root = Path(root).expanduser().resolve()

    def set_compat_profile(self, profile: str) -> None:
        profile = str(profile or "auto").lower()
        if profile not in {"auto","standalone","s30plus-native","nokia225-rm1011"}:
            profile = "auto"
        self.compat_profile = profile

    def set_mre_sdk_root(self, root: Path | str | None) -> None:
        self.mre_sdk_root = Path(root).expanduser().resolve() if root else None

    def set_device_imsi(self, imsi: str) -> None:
        # Session-only. Never write this value to logs or manifests.
        self.device_imsi = "".join(ch for ch in str(imsi or "") if ch.isdigit())

    def start(self, project: Path) -> bool:
        if self.active:
            return False

        project = Path(project).resolve()
        builder = self.engine_root / "tools" / "build.py"
        toolchain = self.toolchain_root
        if not builder.is_file():
            raise FileNotFoundError(f"Builder not found: {builder}")
        if not toolchain.is_dir():
            raise FileNotFoundError(f"Toolchain root not found: {toolchain}")
        if not project.is_dir():
            raise NotADirectoryError(project)

        self.project = project
        self._buffer = ""
        proc = QProcess(self)
        self.process = proc
        proc.setWorkingDirectory(str(self.engine_root))
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(self._read)
        proc.finished.connect(self._finished)

        args = [
            str(builder),
            "--project", str(project),
            "--toolchain", str(toolchain),
            "--compiler-profile", self.compiler_profile,
            "--compat-profile", self.compat_profile,
            "--no-run",
        ]
        if self.mre_sdk_root:
            args += ["--mre-sdk", str(self.mre_sdk_root)]

        extra_env = {}
        if self.device_imsi:
            extra_env["LUAS30_DEVICE_IMSI"] = self.device_imsi
        if self.mre_sdk_root:
            extra_env["MRE_SDK"] = str(self.mre_sdk_root)
        proc.setProcessEnvironment(utf8_qprocess_environment(extra_env))

        self.stage_changed.emit("Validate")
        self.output.emit(
            f"> {Path(sys.executable).name} tools/build.py "
            f'--project "{project}" --toolchain "{toolchain}" '
            f'--compiler-profile {self.compiler_profile} --no-run\n'
        )
        proc.start(sys.executable, args)
        if not proc.waitForStarted(3000):
            message = proc.errorString() or "Unable to start builder."
            self.output.emit(f"[ERROR] {message}\n")
            self.process = None
            raise RuntimeError(message)

        self.started.emit()
        return True

    def cancel(self) -> None:
        if not self.active or not self.process:
            return
        self.output.emit("\n[BUILD] Cancel requested.\n")
        self.process.kill()

    def _read(self) -> None:
        if not self.process:
            return
        text = decode_process_bytes(self.process.readAllStandardOutput())
        if not text:
            return
        self.output.emit(text)
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._classify(line.strip())

    def _classify(self, line: str) -> None:
        low = line.lower()
        if "target profile:" in low or "native sdk" in low:
            self.stage_changed.emit("Validate")
        elif "[ok] resources:" in low:
            self.stage_changed.emit("Resources")
        elif any(name in low for name in ("arm-none-eabi-gcc", "armcc", "tcc")) and " -c " in f" {low} ":
            self.stage_changed.emit("Compile")
        elif (
            ("armlink" in low and ".axf" in low)
            or ("arm-none-eabi-gcc" in low and ".axf" in low)
        ):
            self.stage_changed.emit("Link")
        elif "verify_elf.py" in low or "elf report:" in low:
            self.stage_changed.emit("Verify ELF")
        elif "dev vxp:" in low or "device-bound vxp:" in low:
            self.stage_changed.emit("Package VXP")
        elif "final vxp sha-256:" in low:
            self.stage_changed.emit("SHA-256")

    def _finished(self, exit_code: int, _status) -> None:
        self._read()
        success = exit_code == 0
        manifest_data: dict = {}
        if success and self.project:
            manifest = self.project / "build" / "sync_manifest.json"
            if manifest.is_file():
                try:
                    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
                    manifest_data["_manifest_path"] = str(manifest)
                except (OSError, ValueError, TypeError) as exc:
                    self.output.emit(f"[WARN] Could not read sync manifest: {exc}\n")
        self.stage_changed.emit("Ready" if success else "Failed")
        self.finished.emit(success, int(exit_code), manifest_data)
        if self.process:
            self.process.deleteLater()
        self.process = None
