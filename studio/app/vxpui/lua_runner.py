from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, Signal


_DIAG = re.compile(
    r"^(?P<file>[\w\s:.\\/-]+?):(?P<line>\d+):(?P<column>\d+):\s*"
    r"(?P<severity>error|warning|note):\s*(?P<message>.+)$"
)


class LuaRunner(QObject):
    """VXPEngine-style runner facade over the LuaS30 Lua -> VXP core.

    Signal vocabulary mirrors VXPEngine's VxpRunner so the VXPEngine UI shell
    drives it unchanged; the pipeline behind it is tools/build.py +
    tools/run_emulator.py via BuildService/EmulatorService.
    """

    output = Signal(str)
    started = Signal(str)
    finished = Signal(int, bool)
    running_changed = Signal(bool)
    project_structure_changed = Signal(str)
    diagnostic = Signal(dict)
    artifact_found = Signal(str)
    phase_changed = Signal(str)
    debugger_output = Signal(str)
    debugger_state = Signal(str)
    environment_checked = Signal(dict)
    environment_install_completed = Signal(bool)
    vxpemu_output = Signal(str)
    vxpemu_started = Signal(str, int)
    vxpemu_stopped = Signal(int)

    def __init__(
        self,
        build_service,
        emulator_service,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.build_service = build_service
        self.emulator_service = emulator_service
        self.last_manifest: dict | None = None
        self._post_action = ""
        self._stopping = False

        build_service.started.connect(self._on_build_started)
        build_service.output.connect(self._on_build_output)
        build_service.stage_changed.connect(self.phase_changed.emit)
        build_service.finished.connect(self._on_build_finished)
        emulator_service.output.connect(self.vxpemu_output.emit)
        emulator_service.state_changed.connect(self._on_emulator_state)
        emulator_service.launched.connect(self._on_emulator_launched)
        emulator_service.failed.connect(self._on_emulator_failed)

    @property
    def is_running(self) -> bool:
        return self.build_service.active

    def build(self, project: Path, *, release: bool = False) -> bool:
        return self._start_pipeline(project, post_action="")

    def run(self, project: Path) -> bool:
        return self._start_pipeline(project, post_action="vxpemu")

    def clean(self, project: Path) -> None:
        build_dir = Path(project) / "build"
        try:
            if build_dir.is_dir():
                shutil.rmtree(build_dir)
                self.output.emit(f"[Build] Đã dọn thư mục build: {build_dir}")
            else:
                self.output.emit("[Build] Không có thư mục build để dọn.")
        except OSError as error:
            self.output.emit(f"[Build] Lỗi khi dọn build: {error}")
            return
        self.project_structure_changed.emit(str(project))
        self.finished.emit(0, True)

    def stop(self) -> None:
        self._stopping = True
        self.build_service.cancel()

    def stop_vxpemu(self) -> None:
        self.emulator_service.stop()

    def launch_vxpemu_artifact(self, artifact: str | Path) -> None:
        path = Path(artifact)
        if not path.is_file():
            self._on_emulator_failed(f"Không tìm thấy VXP: {path}")
            return
        digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".json", prefix="luas30_emu_", delete=False
        )
        try:
            with handle:
                json.dump({"vxp": str(path), "vxp_sha256": digest}, handle)
        except OSError as error:
            self._on_emulator_failed(str(error))
            return
        self._launch_manifest({"vxp": str(path), "vxp_sha256": digest,
                               "_manifest_path": handle.name})

    def check_environment(self, project: Path | None = None) -> None:
        from app.services.environment_setup import all_requirements

        found: list[str] = []
        missing_required: list[dict] = []
        missing_optional: list[dict] = []
        engine_root = self.build_service.engine_root
        optional_keys = {"vc_runtime"}
        for requirement in all_requirements(engine_root):
            try:
                ok = bool(requirement.check())
            except Exception:
                ok = False
            entry = {"key": requirement.key, "title": requirement.name,
                     "hint": requirement.hint}
            if ok:
                found.append(requirement.key)
            elif requirement.key in optional_keys:
                missing_optional.append(entry)
            else:
                missing_required.append(entry)
        self.environment_checked.emit({
            "found": found,
            "missing_required": missing_required,
            "missing_optional": missing_optional,
        })

    def debug_command(self, command: str = "", *_args, **_kwargs) -> None:
        cmd = str(command or "").strip()
        self.debugger_output.emit(
            f"[Debugger] {cmd or '?'}: pipeline Lua chưa hỗ trợ lệnh debug trực tiếp."
        )

    def _start_pipeline(self, project: Path, *, post_action: str) -> bool:
        if self.build_service.active:
            self.output.emit("[VXPEmu] Bản build đang chạy, vui lòng đợi…")
            return False
        self._post_action = post_action
        self._stopping = False
        try:
            ok = self.build_service.start(Path(project))
        except (FileNotFoundError, NotADirectoryError, RuntimeError) as error:
            self.output.emit(f"[Build] {error}")
            self.finished.emit(1, False)
            return False
        if ok:
            self.started.emit("Lua → VXP")
            self.running_changed.emit(True)
            self.phase_changed.emit("Khởi động pipeline")
        return ok

    def _on_build_started(self) -> None:
        self.output.emit("[Build] Bắt đầu biên dịch dự án Lua…")

    def _on_build_output(self, line: str) -> None:
        self.output.emit(line)
        match = _DIAG.match(line.strip())
        if match:
            self.diagnostic.emit({
                "severity": match.group("severity"),
                "file": match.group("file").strip(),
                "line": int(match.group("line")),
                "column": int(match.group("column")),
                "message": match.group("message").strip(),
            })

    def _on_build_finished(self, success: bool, code: int, manifest: object) -> None:
        self.running_changed.emit(False)
        self.phase_changed.emit("")
        if success and isinstance(manifest, dict):
            self.last_manifest = manifest
            artifact = str(manifest.get("vxp") or "")
            if artifact:
                self.artifact_found.emit(artifact)
            self.project_structure_changed.emit(str(manifest.get("project") or ""))
            if self._post_action == "vxpemu" and not self._stopping:
                self._launch_manifest(manifest)
                return
        elif not success:
            self.output.emit("[Build] ✗ Biên dịch thất bại.")
        self.finished.emit(code, bool(success))

    def _launch_manifest(self, manifest: dict) -> None:
        try:
            self.emulator_service.launch_manifest(manifest)
        except Exception as error:  # noqa: BLE001 - surface launch failures to console
            self._on_emulator_failed(str(error))

    def _on_emulator_state(self, state: str) -> None:
        if state in {"Stopped", "Error"}:
            self.vxpemu_stopped.emit(0 if state == "Stopped" else 1)

    def _on_emulator_launched(self, manifest: object) -> None:
        if not isinstance(manifest, dict):
            return
        self.last_manifest = manifest
        artifact = str(manifest.get("vxp") or "")
        pid = int(manifest.get("emulator_pid") or 0)
        if artifact:
            self.vxpemu_started.emit(artifact, pid)

    def _on_emulator_failed(self, message: str) -> None:
        self.output.emit(f"[VXPEmu] ✗ {message}")
        self.vxpemu_stopped.emit(1)
