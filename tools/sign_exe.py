from __future__ import annotations

"""
sign_exe.py -- Ky so Authenticode (SHA-256 + RFC3161 timestamp) cho file EXE.

Dung de loai bo canh bao xanh "Windows protected your PC" (SmartScreen) khi
cai tren may khac. SmartScreen chi tin file DUOC KY boi certificate do CA
tin cay cap (OV/EV). File khong ky (hoac tu ky) van bi canh bao — day la
co che cua Windows, khong co meo code nao tranh duoc.

Cach dung:
    set LUAS30_SIGN_PASSWORD=mat-khau-pfx
    py tools/sign_exe.py --pfx C:\\certs\\qeafivels.pfx --file dist\\LuaS30IDE-Setup-1.0.1.exe

    py tools/sign_exe.py --pfx C:\\certs\\qeafivels.pfx --password mat-khau ^
        --timestamp http://timestamp.digicert.com --file app.exe

BAO MAT: KHONG bao gio commit file .pfx/.p12 hay mat khau vao git.
Uu tien doc mat khau tu bien moi truong LUAS30_SIGN_PASSWORD.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_TIMESTAMP = "http://timestamp.digicert.com"


def find_signtool(explicit: str | None = None) -> Path | None:
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
    found = shutil.which("signtool")
    if found:
        return Path(found)
    for base in (
        Path(r"C:\Program Files (x86)\Windows Kits"),
        Path(r"C:\Program Files\Windows Kits"),
    ):
        if not base.is_dir():
            continue
        hits = sorted(base.glob("*/bin/*/x64/signtool.exe"), reverse=True)
        if hits:
            return hits[0]
    return None


def sign(signtool: Path, pfx: Path, password: str, timestamp: str, target: Path) -> int:
    cmd = [
        str(signtool), "sign",
        "/f", str(pfx),
        "/p", password,
        "/fd", "sha256",
    ]
    if timestamp and timestamp.lower() != "none":
        cmd += ["/td", "sha256", "/tr", timestamp]
    cmd.append(str(target))
    ts_note = timestamp if (timestamp and timestamp.lower() != "none") else "(khong timestamp)"
    print("[RUN] signtool sign /f ... /tr", ts_note, target.name, flush=True)
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if p.stdout.strip():
        print(p.stdout)
    if p.returncode != 0 and p.stderr.strip():
        print(p.stderr)
    return p.returncode


def verify(signtool: Path, target: Path) -> int:
    p = subprocess.run(
        [str(signtool), "verify", "/pa", "/v", str(target)],
        capture_output=True, text=True, errors="replace",
    )
    print(p.stdout)
    if p.returncode != 0:
        print(p.stderr)
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="Ky so Authenticode SHA-256 cho file EXE")
    ap.add_argument("--pfx", type=Path, required=True, help="File chung thu so .pfx/.p12 (KHONG commit)")
    ap.add_argument("--password", default=os.environ.get("LUAS30_SIGN_PASSWORD", ""),
                    help="Mat khau PFX (khuyen dung env LUAS30_SIGN_PASSWORD)")
    ap.add_argument("--timestamp", default=DEFAULT_TIMESTAMP,
                    help="Server RFC3161 (VD: http://timestamp.digicert.com). "
                    "Dung 'none' de bo qua timestamp (chi khi test cert tu ky).")
    ap.add_argument("--signtool", default=None)
    ap.add_argument("--file", type=Path, required=True)
    args = ap.parse_args()

    if not args.pfx.is_file():
        print(f"[ERROR] Khong thay PFX: {args.pfx}")
        return 2
    if not args.password:
        print("[ERROR] Thieu mat khau PFX (--password hoac LUAS30_SIGN_PASSWORD).")
        return 2
    if not args.file.is_file():
        print(f"[ERROR] Khong thay file can ky: {args.file}")
        return 2
    st = find_signtool(args.signtool)
    if not st:
        print("[ERROR] Khong tim thay signtool.exe (cai Windows SDK).")
        return 3
    print(f"[sign] signtool: {st}")
    if sign(st, args.pfx, args.password, args.timestamp, args.file) != 0:
        return 4
    if verify(st, args.file) != 0:
        return 5
    print(f"[OK] Da ky: {args.file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
