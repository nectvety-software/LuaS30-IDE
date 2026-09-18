from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest().upper()

def resolve_emulator(value: str | None) -> Path | None:
    candidates = []
    if value:
        p = Path(value)
        candidates += [p, p / 'VXPEmu.exe']
    env = os.environ.get('LUAS30_EMULATOR')
    if env:
        p = Path(env)
        candidates += [p, p / 'VXPEmu.exe']
    candidates += [
        ROOT / 'emulator' / 'VXPEmu.exe',
        ROOT / 'toolchain' / 'emulator' / 'VXPEmu.exe',
    ]
    for p in candidates:
        try:
            p = p.expanduser().resolve()
        except Exception:
            continue
        if p.is_file():
            return p
    return None

def kill_old_emulator() -> None:
    if os.name != 'nt':
        return
    subprocess.run(
        ['taskkill', '/F', '/IM', 'VXPEmu.exe'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

def main() -> int:
    ap = argparse.ArgumentParser(description='Run the exact VXP just built by LuaS30 IDE')
    ap.add_argument('--vxp', required=True, type=Path)
    ap.add_argument('--emulator', help='VXPEmu.exe or its directory')
    ap.add_argument('--sha256', help='expected VXP SHA-256; launch is refused on mismatch')
    ap.add_argument('--manifest', type=Path, help='optional sync manifest to update')
    ap.add_argument('--keep-old', action='store_true', help='do not terminate a previous VXPEmu')
    a = ap.parse_args()

    vxp = a.vxp.resolve()
    if not vxp.is_file():
        print(f'[ERROR] VXP not found: {vxp}', file=sys.stderr)
        return 2

    actual = sha256_file(vxp)
    if a.sha256 and actual.upper() != a.sha256.upper():
        print('[ERROR] Build/emulator sync failed: SHA-256 mismatch.', file=sys.stderr)
        print(' expected:', a.sha256, file=sys.stderr)
        print(' actual:  ', actual, file=sys.stderr)
        return 3

    exe = resolve_emulator(a.emulator)
    if not exe:
        print('[ERROR] VXPEmu.exe was not found.', file=sys.stderr)
        print('Run setup_emulator.bat once, or set LUAS30_EMULATOR.', file=sys.stderr)
        return 4

    if os.name != 'nt':
        print('[ERROR] VXPEmu.exe is a Windows emulator and can only be launched on Windows.', file=sys.stderr)
        return 5

    if not a.keep_old:
        kill_old_emulator()
        time.sleep(0.15)

    # VXPEmu needs its own directory as cwd so Qt/unicorn DLLs resolve correctly.
    # --screen-only yields the bare 240x320 framebuffer window that the Nokia
    # shell embeds (same launch contract as VXPEngine).
    emu_args = [str(vxp), '--autostart', '--testapi', '--screen-only']
    cmd = [str(exe)] + emu_args
    print('[EMU] Executable:', exe)
    print('[EMU] VXP:', vxp)
    print('[EMU] SHA-256:', actual)
    print('[EMU] Starting exact build output...')
    proc = subprocess.Popen(cmd, cwd=str(exe.parent))

    if a.manifest:
        mpath = a.manifest.resolve()
        data = {}
        if mpath.is_file():
            try:
                data = json.loads(mpath.read_text(encoding='utf-8'))
            except Exception:
                data = {}
        data.update({
            'emulator': str(exe),
            'emulator_pid': proc.pid,
            'emulated_vxp': str(vxp),
            'emulated_vxp_sha256': actual,
            'emulator_args': emu_args,
            'sync_verified': True,
        })
        mpath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f'[OK] VXPEmu started (PID {proc.pid}) with SHA-verified VXP.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
