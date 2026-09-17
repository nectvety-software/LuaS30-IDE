from __future__ import annotations

"""
build_frozen.py -- Dong Studio thanh LuaS30IDE.exe (PyInstaller onedir).

    py tools/build_frozen.py --out dist/frozen
    py tools/build_frozen.py --out dist/frozen --skip-verify

Ket qua: <out>/LuaS30IDE/LuaS30IDE.exe (+ _internal/, PySide6...).
Thu muc nay duoc package_single_exe.py ghep voi tools/toolchain/
emulator/python/... thanh stage duy nhat cho Inno Setup.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], cwd: Path) -> int:
    print("[RUN]", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, cwd=str(cwd)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="Build frozen LuaS30IDE.exe (PyInstaller onedir)")
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "frozen")
    ap.add_argument("--spec", type=Path, default=ROOT / "packaging" / "windows" / "LuaS30IDE.spec")
    args = ap.parse_args()

    out: Path = args.out.resolve()
    spec: Path = args.spec.resolve()
    if not spec.is_file():
        raise SystemExit(f"[ERROR] Khong thay spec: {spec}")

    work = out / "_work"
    distpath = out / "_dist"
    for d in (work, distpath):
        if d.exists():
            shutil.rmtree(d)

    rc = _run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--workpath", str(work),
        "--distpath", str(distpath),
        str(spec),
    ], ROOT)
    if rc != 0:
        raise SystemExit(f"PyInstaller failed (code {rc})")

    frozen = distpath / "LuaS30IDE"
    exe = frozen / "LuaS30IDE.exe"
    if not exe.is_file():
        raise SystemExit("Khong thay LuaS30IDE.exe sau khi build.")
    target = out / "LuaS30IDE"
    if target.exists():
        shutil.rmtree(target)
    shutil.move(str(frozen), str(target))
    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(distpath, ignore_errors=True)

    # Smoke test: --version khong can mo Qt.
    probe = subprocess.run([str(target / "LuaS30IDE.exe"), "--version"],
                           capture_output=True, text=True, timeout=60)
    print((probe.stdout + probe.stderr).strip())
    if probe.returncode != 0:
        raise SystemExit("Smoke test --version that bai.")
    mb = sum(f.stat().st_size for f in target.rglob("*") if f.is_file()) / (1024 * 1024)
    print(f"[OK] Frozen: {target} ({mb:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
