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
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], cwd: Path) -> int:
    print("[RUN]", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, cwd=str(cwd)).returncode


def _clear_target(target: Path) -> None:
    """Bo ban frozen cu ma KHONG `rmtree` thang cay lon nam trong repo.

    ⚠️ Hook `[safe-delete]` cua host chan `shutil.rmtree` khi so muc xoa trong
    MOT luot vuot nguong (50 muc) va chi mien hoan toan cac duong dan duoi temp
    cua OS. `dist/frozen/LuaS30IDE` do duoc **3022 tep**, nen `rmtree` se lam
    script CHET voi `exit 1` ma khong in gi (stderr bi nuot) — trong y nhu
    "PyInstaller hong", khong nhu "bi chan xoa".
    Doi ten (metadata, KHONG phai xoa) sang ten tam cung o dia la duong an toan;
    ten bat dau bang `.` nen `package_msi._iter_files` se bo qua no khi stage.
    """
    if not target.exists():
        return
    aside = target.parent / f".old-{target.name}-{time.strftime('%Y%m%d-%H%M%S')}"
    try:
        target.rename(aside)
        print(f"[clean] Ban frozen cu -> {aside.name} (doi ten, khong xoa)")
    except OSError as exc:
        print(f"[WARN] Khong doi ten duoc ban cu ({exc}); thu xoa truc tiep.")
        shutil.rmtree(target, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build frozen LuaS30IDE.exe (PyInstaller onedir)")
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "frozen")
    ap.add_argument("--spec", type=Path, default=ROOT / "packaging" / "windows" / "LuaS30IDE.spec")
    args = ap.parse_args()

    out: Path = args.out.resolve()
    spec: Path = args.spec.resolve()
    if not spec.is_file():
        raise SystemExit(f"[ERROR] Khong thay spec: {spec}")
    out.mkdir(parents=True, exist_ok=True)

    # ⚠️ `_work/` cua PyInstaller chua hang nghin tep. Don no trong `out`
    # (thuong la `dist/`) se vuot ngan sach xoa theo luot cua hook `[safe-delete]`
    # ⇒ scratch PHAI nam trong temp cua OS (`_should_bypass_safe_delete()` mien
    # moi duong dan duoi temp). Xem `doc/build/BUILD_VXP.md` / memory.
    with tempfile.TemporaryDirectory(prefix="luas30-frozen-") as tmp:
        work = Path(tmp) / "_work"
        distpath = Path(tmp) / "_dist"

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
        _clear_target(target)
        # Khac o dia (temp tren C:, `out` tren D:) thi `shutil.move` se copy roi
        # xoa nguon — nguon nam duoi temp nen duoc mien, khong dung guard.
        shutil.move(str(frozen), str(target))

    # LuaS30IDE doc VERSION tu thu muc chua exe; thieu no thi app bao
    # "unknown" va lam nhiem setup_state.json (hoi dialog thiet lap lan dau
    # o lan chay that tiep theo).
    version_file = ROOT / "VERSION"
    if version_file.is_file():
        shutil.copy2(version_file, target / "VERSION")

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
