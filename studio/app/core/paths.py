from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_FOLDER = "LuaS30IDE"
LEGACY_APP_FOLDER = "LuaS30Engine"
PROJECTS_FOLDER = "LuaS30 Projects"
# Older Documents project roots (before dedicated "LuaS30 Projects").
LEGACY_PROJECTS_FOLDERS = ("LuaS30IDE", "LuaS30Engine")


def _resolve_folder(base: Path) -> Path:
    """Chọn thư mục dữ liệu, tự đổi tên thư mục cũ `LuaS30Engine` nếu cần.

    An toàn dữ liệu là ưu tiên số một:
      * tên mới đã có -> dùng luôn, không đụng thư mục cũ;
      * chỉ `os.rename` (nguyên tử, cùng ổ đĩa) — không copy rồi xoá, nên không
        có cửa sổ nào để mất dữ liệu;
      * đổi tên thất bại (khác ổ đĩa, file đang bị giữ) -> **dùng lại thư mục
        cũ** thay vì trỏ vào thư mục rỗng. Thà ở lại tên cũ còn hơn mồ côi
        cấu hình và dự án.
    """
    current = base / APP_FOLDER
    legacy = base / LEGACY_APP_FOLDER
    if current.exists():
        return current
    if legacy.is_dir():
        try:
            os.rename(legacy, current)
        except OSError:
            return legacy
        return current
    return current


def _windows_documents() -> Path:
    """Return the user's real Documents directory, including redirected folders."""
    if os.name != "nt":
        return Path.home() / "Documents"
    try:
        import ctypes
        from ctypes import wintypes

        CSIDL_PERSONAL = 5
        SHGFP_TYPE_CURRENT = 0
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        result = ctypes.windll.shell32.SHGetFolderPathW(
            None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf
        )
        if result == 0 and buf.value:
            return Path(buf.value)
    except Exception:
        pass
    return Path.home() / "Documents"


def app_data_root() -> Path:
    override = os.environ.get("LUAS30_APPDATA")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if base:
            return _resolve_folder(Path(base))
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return _resolve_folder(Path(base))
    return _resolve_folder(Path.home() / ".config")


def documents_root() -> Path:
    override = os.environ.get("LUAS30_DOCUMENTS")
    if override:
        return Path(override).expanduser()
    return _windows_documents()


def projects_root() -> Path:
    """User project store: Documents\\LuaS30 Projects (config stays in AppData)."""
    override = os.environ.get("LUAS30_PROJECTS")
    if override:
        path = Path(override).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    docs = documents_root()
    root = docs / PROJECTS_FOLDER
    if not root.exists():
        migrated = False
        for legacy_name in LEGACY_PROJECTS_FOLDERS:
            legacy = docs / legacy_name
            if not legacy.is_dir():
                continue
            # Prefer rename; fall back to merge-copy if rename fails.
            try:
                os.rename(legacy, root)
                migrated = True
                break
            except OSError:
                try:
                    root.mkdir(parents=True, exist_ok=True)
                    for child in legacy.iterdir():
                        target = root / child.name
                        if not target.exists():
                            try:
                                os.rename(child, target)
                            except OSError:
                                shutil.copytree(child, target, dirs_exist_ok=True)
                    migrated = True
                    break
                except OSError:
                    continue
        if not migrated and not root.exists():
            root.mkdir(parents=True, exist_ok=True)
    else:
        # Root exists: pull any leftover projects out of legacy folders.
        for legacy_name in LEGACY_PROJECTS_FOLDERS:
            legacy = docs / legacy_name
            if not legacy.is_dir():
                continue
            for child in legacy.iterdir():
                target = root / child.name
                if not target.exists():
                    try:
                        os.rename(child, target)
                    except OSError:
                        pass
    root.mkdir(parents=True, exist_ok=True)
    return root


def config_dir() -> Path:
    return app_data_root() / "config"


def logs_dir() -> Path:
    return app_data_root() / "logs"


def cache_dir() -> Path:
    return app_data_root() / "cache"


def temp_dir() -> Path:
    return app_data_root() / "temp"


def backups_dir() -> Path:
    return app_data_root() / "backups"


def venv_dir() -> Path:
    return app_data_root() / "venv"


def ensure_user_dirs() -> dict[str, Path]:
    paths = {
        "app_data": app_data_root(),
        "config": config_dir(),
        "logs": logs_dir(),
        "cache": cache_dir(),
        "temp": temp_dir(),
        "backups": backups_dir(),
        "venv": venv_dir(),
        "projects": projects_root(),
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def resolve_script(base: Path | str, name: str) -> Path:
    """Prefer a .py script; fall back to packaged sourceless .pyc.

    MSI builds ship studio/ and tools/ as bytecode only, so installed machines
    have `build.pyc` / `main.pyc` without the original sources.
    """
    root = Path(base)
    py = root / f"{name}.py"
    if py.is_file():
        return py
    pyc = root / f"{name}.pyc"
    if pyc.is_file():
        return pyc
    return py


def bundled_python(engine_root: Path | str) -> Path | None:
    """Python kem theo ban cai (`python/python.exe`), neu co."""
    candidate = Path(engine_root) / "python" / "python.exe"
    return candidate if candidate.is_file() else None


def tool_python(engine_root: Path | str | None = None) -> str:
    """Trinh thong dich de chay cac script `tools/*.py`.

    Ban frozen (LuaS30IDE.exe) khong chay duoc file .py truc tiep nen bat
    buoc dung Python kem theo. Ban source (run.bat) da chon dung interpreter
    (venv/bundled) truoc khi mo Studio nen giu sys.executable.
    """
    if getattr(sys, "frozen", False):
        if engine_root is not None:
            found = bundled_python(engine_root)
            if found is not None:
                return str(found)
        for candidate in ("py", "python"):
            located = shutil.which(candidate)
            if located:
                return located
        return sys.executable
    return sys.executable
