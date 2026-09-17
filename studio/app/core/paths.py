from __future__ import annotations

import os
from pathlib import Path

APP_FOLDER = "LuaS30IDE"
LEGACY_APP_FOLDER = "LuaS30Engine"


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
    override = os.environ.get("LUAS30_PROJECTS")
    if override:
        return Path(override).expanduser()
    return _resolve_folder(documents_root())


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
