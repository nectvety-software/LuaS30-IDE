from __future__ import annotations

"""Mo ta + kiem tra + cai dat cac thanh phan moi truong LuaS30 IDE.

Kieu VXPEngine environment_spec/environment_setup nhung don gian hon:
cac check chay dong bo (nhanh), cai dat chay QProcess noi tiep qua
EnvironmentInstaller. Hoi thoai dung o views/setup_dialog.py.

Khong co gi tu chay khi import.
"""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from app.core.paths import config_dir, tool_python

SETUP_STATE_FILE = "setup_state.json"


@dataclass(slots=True)
class Requirement:
    key: str
    name: str
    hint: str = ""
    check: Callable[[], bool] = field(default=lambda: False)
    command: Callable[[], list[str] | None] = field(default=lambda: None)

    @property
    def is_installable(self) -> bool:
        try:
            return self.command() is not None
        except Exception:
            return False


def _run_quiet(program: str, *args: str, timeout: int = 60) -> bool:
    try:
        p = subprocess.run(
            [program, *args],
            capture_output=True, text=True, errors="replace",
            timeout=timeout,
        )
        return p.returncode == 0
    except Exception:
        return False


def all_requirements(engine_root: Path | str) -> list[Requirement]:
    root = Path(engine_root).resolve()
    tools = root / "tools"
    gcc = root / "toolchain" / "arm-gcc" / "bin" / "arm-none-eabi-gcc.exe"
    emu = root / "emulator" / "VXPEmu.exe"
    lua_h = root / "vendor" / "lua-5.1.5" / "src" / "lua.h"
    build_py = tools / "build.py"
    req_file = root / "requirements-studio.txt"
    wheels = root / "vendor" / "wheels"
    vc_tool = tools / "install_vc_runtime.py"

    def tool_py() -> str:
        return tool_python(root)

    def has_python() -> bool:
        exe = tool_py()
        if not exe or not Path(exe).is_file() and not shutil.which(exe):
            return False
        return _run_quiet(exe, "-c", "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)")

    def has_pyside() -> bool:
        return _run_quiet(tool_py(), "-c", "import PySide6")

    def pyside_cmd() -> list[str] | None:
        dm = tools / "dependency_manager.py"
        if not dm.is_file() or not req_file.is_file():
            return None
        cmd = [tool_py(), str(dm), "--requirements", str(req_file),
               "--python", tool_py(), "--mode", "auto"]
        if wheels.is_dir() and any(wheels.glob("*.whl")):
            cmd += ["--find-links", str(wheels)]
        return cmd

    def has_gcc() -> bool:
        return gcc.is_file() and _run_quiet(str(gcc), "--version")

    def has_emu() -> bool:
        return emu.is_file()

    def has_lua() -> bool:
        return lua_h.is_file()

    def has_build_tools() -> bool:
        return (
            build_py.is_file()
            and (root / "engine" / "src" / "runtime_entry.c").is_file()
            and (root / "sdk" / "luas30" / "include" / "ls30" / "api.h").is_file()
        )

    def has_vc() -> bool:
        if os.name != "nt":
            return True
        sys32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
        return (sys32 / "vcruntime140_1.dll").is_file() or (sys32 / "vcruntime140.dll").is_file()

    def vc_cmd() -> list[str] | None:
        if vc_tool.is_file():
            return [tool_py(), str(vc_tool)]
        return None

    return [
        Requirement(
            key="python",
            name="Python 3.10+ (kèm theo bản cài / hệ thống)",
            hint="Cài lại bản Setup đầy đủ, hoặc cài Python từ python.org.",
            check=has_python,
        ),
        Requirement(
            key="pyside_libs",
            name="Thư viện Python (PySide6)",
            hint="Bấm Tự động cài đặt để cài offline từ vendor/wheels.",
            check=has_pyside,
            command=pyside_cmd,
        ),
        Requirement(
            key="arm_gcc",
            name="ARM GCC (biên dịch VXP cho máy thật)",
            hint="Cài lại bản Setup đầy đủ (gồm toolchain/arm-gcc).",
            check=has_gcc,
        ),
        Requirement(
            key="emulator",
            name="VXPEmu (chạy thử trên máy tính)",
            hint="Cài lại bản Setup đầy đủ (gồm emulator/).",
            check=has_emu,
        ),
        Requirement(
            key="lua_src",
            name="Lua 5.1.5 source (nhân build)",
            hint="Cài lại bản Setup đầy đủ (gồm vendor/lua-5.1.5).",
            check=has_lua,
        ),
        Requirement(
            key="build_tools",
            name="Công cụ build VXP (build.py + Native SDK)",
            hint="Cài lại bản Setup đầy đủ.",
            check=has_build_tools,
        ),
        Requirement(
            key="vc_runtime",
            name="Visual C++ runtime (cần cho Qt6)",
            hint="Bấm Tự động cài đặt để tải từ Microsoft.",
            check=has_vc,
            command=vc_cmd,
        ),
    ]


def detect_missing(engine_root: Path | str) -> list[Requirement]:
    return [req for req in all_requirements(engine_root) if not _safe_check(req)]


def _safe_check(req: Requirement) -> bool:
    try:
        return bool(req.check())
    except Exception:
        return False


def installable(items: Iterable[Requirement]) -> list[Requirement]:
    return [item for item in items if item.is_installable]


# ------------------------------ setup-state ------------------------------

def _state_path() -> Path:
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory / SETUP_STATE_FILE


def is_first_run(current_version: str) -> bool:
    """True khi chua thiet lap xong, hoac version moi hon lan thiet lap truoc."""
    try:
        data = json.loads(_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True
    if not data.get("done"):
        return True
    return str(data.get("version") or "") != str(current_version)


def mark_setup_done(current_version: str) -> None:
    try:
        _state_path().write_text(
            json.dumps({"done": True, "version": str(current_version)}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


# ------------------------------ installer ------------------------------

class EnvironmentInstaller(QObject):
    """Chay noi tiep cac lenh cai moi truong, log chay truc tiep ra dialog."""

    log = Signal(str)
    step_started = Signal(str, int, int)
    step_finished = Signal(str, int)
    finished = Signal(bool, object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._queue: list[tuple[Requirement, list[str]]] = []
        self._results: list[tuple[str, int]] = []
        self._current: Requirement | None = None
        self._running = False
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._process.setProcessEnvironment(QProcessEnvironment.systemEnvironment())
        self._process.readyReadStandardOutput.connect(self._read_output)
        self._process.finished.connect(self._step_finished)

    @property
    def is_running(self) -> bool:
        return self._running

    def install(self, items: Iterable[Requirement]) -> bool:
        if self._running:
            self.log.emit("[Setup] Đang có tiến trình cài đặt khác.")
            return False
        queue: list[tuple[Requirement, list[str]]] = []
        for item in items:
            try:
                command = item.command()
            except Exception:
                command = None
            if not command:
                self.log.emit(f"[Setup] Bỏ qua {item.name}: {item.hint or 'không có lệnh cài tự động.'}")
                continue
            queue.append((item, list(command)))
        if not queue:
            self.log.emit("[Setup] Không có mục nào cài tự động được.")
            self.finished.emit(False, [])
            return False
        self._queue = queue
        self._results = []
        self._running = True
        self._start_next()
        return True

    def stop(self) -> None:
        if self._running and self._process.state() != QProcess.ProcessState.NotRunning:
            self.log.emit("[Setup] Đang dừng tiến trình cài đặt...")
            self._queue.clear()
            self._process.kill()

    def _start_next(self) -> None:
        if not self._queue:
            self._running = False
            self._current = None
            ok = all(code == 0 for _name, code in self._results)
            self.finished.emit(ok, list(self._results))
            return
        item, command = self._queue.pop(0)
        self._current = item
        done = len(self._results) + 1
        total = done + len(self._queue)
        self.step_started.emit(item.name, done, total)
        self.log.emit(f"[Setup] ({done}/{total}) {item.name}")
        program, args = command[0], command[1:]
        self.log.emit(f"[Setup] $ {program} {' '.join(args)}".rstrip())
        self._process.start(program, args)

    def _read_output(self) -> None:
        data = bytes(self._process.readAllStandardOutput()).decode("utf-8", "replace")
        for line in data.splitlines():
            line = line.rstrip()
            if line:
                self.log.emit(f"[Setup] {line}")

    def _step_finished(self, code: int, _status) -> None:
        item = self._current
        name = item.name if item is not None else "?"
        self._results.append((name, int(code)))
        self.step_finished.emit(name, int(code))
        if code == 0:
            self.log.emit(f"[Setup] Xong: {name}")
        else:
            hint = item.hint if item is not None else ""
            self.log.emit(f"[Setup] Lỗi: {name} (mã {code})" + (f" — {hint}" if hint else ""))
        self._current = None
        self._start_next()
