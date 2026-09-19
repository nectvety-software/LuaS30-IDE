from __future__ import annotations

"""
verify_release.py -- Kiem tra thu muc stage truoc khi dong goi installer
(kieu VXPEngine verify_release.py).

    py tools/verify_release.py <stage-dir>

Kiem tra:
  * Du file: LuaS30IDE.exe (frozen GUI), python/python.exe,
    toolchain ARM GCC, emulator, tools/build.py, VERSION, icon.
  * LuaS30IDE.exe la Windows GUI executable (PE subsystem).
  * Khong lot private key (.pem/.key noi dung) vao ban release.
  * Probe: LuaS30IDE.exe --version tra ve dung VERSION.
  * Probe: python kem theo chay duoc tools/build.py --help (stdlib).
"""

import re
import subprocess
import sys
from pathlib import Path

import pefile

SUBSYSTEM_WINDOWS_GUI = 2


def require(path: Path) -> Path:
    if not path.is_file():
        raise SystemExit(f"Missing release file: {path}")
    return path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: py tools/verify_release.py <stage-dir>")
        return 2
    stage = Path(sys.argv[1]).resolve()
    if not stage.is_dir():
        raise SystemExit(f"Stage dir not found: {stage}")

    ide = require(stage / "LuaS30IDE.exe")
    sdk_python = require(stage / "python" / "python.exe")
    require(stage / "toolchain" / "arm-gcc" / "bin" / "arm-none-eabi-gcc.exe")
    require(stage / "emulator" / "VXPEmu.exe")
    require(stage / "tools" / "build.py")
    require(stage / "app-icon" / "icon.ico")
    # Thieu qss nay trong ban frozen = chrome VXPEngine mat moi selector, cua
    # so frameless trong suot (loi hien thi Home page tren may that).
    require(stage / "app" / "vxpui" / "resources" / "dark_theme.qss")
    version_file = require(stage / "VERSION")
    version = version_file.read_text(encoding="utf-8").strip()
    if not version:
        raise SystemExit("VERSION is empty")

    pe = pefile.PE(str(ide), fast_load=True)
    if pe.OPTIONAL_HEADER.Subsystem != SUBSYSTEM_WINDOWS_GUI:
        raise SystemExit("LuaS30IDE.exe is not a Windows GUI executable")
    print(f"[verify] PE GUI subsystem OK: {ide.name}")

    leaked = []
    private_pem = re.compile(
        rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----\r?\n"
        rb"[A-Za-z0-9+/=\r\n]{64,}"
        rb"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    )
    for candidate in stage.rglob("*"):
        if not candidate.is_file() or candidate.stat().st_size > 2_000_000:
            continue
        try:
            if private_pem.search(candidate.read_bytes()):
                leaked.append(str(candidate.relative_to(stage)))
        except OSError:
            continue
    if leaked:
        raise SystemExit("Private key material found in release: " + ", ".join(leaked))
    print("[verify] No private key material in stage")

    probe = subprocess.run(
        [str(ide), "--version"],
        capture_output=True, text=True, timeout=60,
    )
    out = (probe.stdout + probe.stderr).strip()
    if probe.returncode != 0 or version not in out:
        raise SystemExit(f"LuaS30IDE.exe --version failed: rc={probe.returncode} out={out!r}")
    print(f"[verify] GUI probe OK: {out}")

    probe = subprocess.run(
        [str(sdk_python), str(stage / "tools" / "build.py"), "--help"],
        capture_output=True, text=True, timeout=60,
        cwd=str(stage),
    )
    if probe.returncode != 0 or "usage:" not in (probe.stdout + probe.stderr).lower():
        raise SystemExit("Bundled Python tool probe failed (tools/build.py --help)")
    print("[verify] Bundled Python tool probe OK")

    print(f"[verify] RELEASE OK (version {version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
