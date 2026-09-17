from __future__ import annotations

"""Cai Visual C++ runtime (can cho PySide6/Qt6) khi may con thieu.

Tai vc_redist.x64.exe tu Microsoft (can mang), cai im lang /quiet,
kiem tra lai DLL. Stdlib-only de chay duoc bang Python kem theo.

    python tools/install_vc_runtime.py
    python tools/install_vc_runtime.py --check   (chi kiem tra, exit 0/1)
"""

import argparse
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
DLLS = ("vcruntime140_1.dll", "vcruntime140.dll")


def system32() -> Path:
    root = os.environ.get("SystemRoot", r"C:\Windows")
    return Path(root) / "System32"


def installed() -> bool:
    return any((system32() / name).is_file() for name in DLLS)


def install(timeout: int = 300) -> int:
    if os.name != "nt":
        print("[vc] Khong phai Windows; bo qua.")
        return 0
    if installed():
        print("[vc] Visual C++ runtime da co.")
        return 0
    tmp = Path(tempfile.gettempdir()) / "luas30_vc_redist.x64.exe"
    print(f"[vc] Dang tai vc_redist.x64.exe ...")
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "LuaS30IDE-setup"})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
    except Exception as exc:
        print(f"[vc] ERROR tai that bai: {exc}")
        return 2
    print("[vc] Dang cai dat (quiet, co the mat 1-2 phut) ...")
    try:
        p = subprocess.run([str(tmp), "/quiet", "/norestart"], timeout=timeout)
    except Exception as exc:
        print(f"[vc] ERROR khi cai: {exc}")
        return 3
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
    if installed():
        print("[vc] OK: Visual C++ runtime da san sang.")
        return 0
    print(f"[vc] ERROR: cai xong (code {p.returncode}) nhung van thieu DLL.")
    return 4


def main() -> int:
    ap = argparse.ArgumentParser(description="Cai Visual C++ runtime cho LuaS30 IDE")
    ap.add_argument("--check", action="store_true", help="Chi kiem tra, khong cai")
    args = ap.parse_args()
    if args.check:
        print("[vc] Da co." if installed() else "[vc] Thieu.")
        return 0 if installed() else 1
    return install()


if __name__ == "__main__":
    raise SystemExit(main())
