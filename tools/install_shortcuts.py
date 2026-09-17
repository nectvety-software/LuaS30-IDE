from __future__ import annotations

"""Create Start Menu / Desktop shortcuts for the local LuaS30 IDE install."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICON = ROOT / "app-icon" / "icon.ico"
# Hidden launcher (no console flash). .cmd remains for visible/debug runs.
LAUNCH = ROOT / "LuaS30-IDE.vbs"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").is_file() else "1.0.0"


def _desktop() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"


def _start_menu() -> Path:
    appdata = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "LuaS30 IDE"


def _ps_create_shortcut(target: Path, link: Path, icon: Path, arguments: str = "", description: str = "") -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    cmd = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{link}');"
        "$s.TargetPath='{target}';"
        "$s.Arguments='{args}';"
        "$s.WorkingDirectory='{cwd}';"
        "$s.IconLocation='{icon}';"
        "$s.Description='{desc}';"
        "$s.WindowStyle=7;"
        "$s.Save()"
    ).format(
        link=str(link).replace("'", "''"),
        target=str(target).replace("'", "''"),
        args=arguments.replace("'", "''"),
        cwd=str(ROOT).replace("'", "''"),
        icon=str(icon).replace("'", "''"),
        desc=description.replace("'", "''"),
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
        check=True,
        capture_output=True,
        text=True,
    )


def main() -> int:
    if not LAUNCH.is_file():
        print(f"[ERROR] launcher missing: {LAUNCH}")
        return 1
    if not ICON.is_file():
        print(f"[ERROR] icon missing: {ICON}")
        return 1

    desktop = _desktop() / "LuaS30 IDE.lnk"
    start = _start_menu() / "LuaS30 IDE.lnk"
    desc = f"LuaS30 IDE {VERSION} — MRE / VXP development workspace"

    _ps_create_shortcut(LAUNCH, desktop, ICON, "", desc)
    print(f"[OK] Desktop: {desktop}")
    _ps_create_shortcut(LAUNCH, start, ICON, "", desc)
    print(f"[OK] Start Menu: {start}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
