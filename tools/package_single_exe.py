from __future__ import annotations

"""
package_single_exe.py -- Dong goi LuaS30 IDE thanh DUY NHAT MOT file Setup EXE.

Ket qua:
    dist/LuaS30IDE-Setup-<version>.exe   (mot file duy nhat)

File Setup EXE nay la trinh cai dat day du (Inno Setup 6):
  * Wizard cai dat + che do im lang:  Setup.exe /SILENT   (hoac /VERYSILENT)
  * Bieu tuong ung dung: app-icon/icon.ico cho Setup, shortcut, Add/Remove Programs
  * Thu vien moi truong: vendor/wheels/ chua san wheel PySide6 cho
    Python 3.10-3.14 (win_amd64) -> may dich cai offline, khong can Internet
  * Toolchain ARM GCC + Emulator duoc dong goi ben trong (tru khi --skip-optional)

Cach dung:
    py tools/package_single_exe.py --out dist
    py tools/package_single_exe.py --out dist --skip-optional
    py tools/package_single_exe.py --out dist --python-versions 3.12
    py tools/package_single_exe.py --out dist --skip-wheels   (dung nhung van build Setup)

Yeu cau luc build: co Internet (tai wheels + Inno Setup lan dau).
May dich cai dat: KHONG can Internet (da co wheels offline) nhung can
Python 3.10+ cai san (run.bat se tu tao venv va cai PySide6 tu wheels noi bo).

Chong canh bao SmartScreen "Windows protected your PC" tren may la:
    set LUAS30_SIGN_PASSWORD=mat-khau-pfx
    py tools/package_single_exe.py --out dist --sign-pfx C:/certs/ten-mien.pfx
Can chung thu so OV/EV do CA tin cay cap (mua hang nam). Khong co PFX thi
file van build duoc nhung Windows se canh bao vi khong ky — day la co che
cua Windows, khong co meo code nao tranh duoc.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import package_msi as msi  # noqa: E402  (tai su dung SKIP_* / CORE_* / _version)
import sign_exe as signmod  # noqa: E402  (tim signtool cho tuy chon --sign-pfx)

PRODUCT_NAME = "LuaS30 IDE"
MANUFACTURER = "Qeafivels"
APP_ID = "{A3F5C2D1-8B4E-4F7A-9C10-6E7541301D01}"  # giu nguyen nhu MSI UpgradeCode
ICON_SRC = ROOT / "app-icon" / "icon.ico"
EULA_SRC = ROOT / "packaging" / "EULA.rtf"
PUBLISHER_URL = "https://qeafivels.com/"

INNO_VERSION = "6.7.3"
INNO_URL = (
    "https://github.com/jrsoftware/issrc/releases/download/"
    f"is-{INNO_VERSION.replace('.', '_')}/innosetup-{INNO_VERSION}.exe"
)

# Thu vien moi truong can dong goi (giong requirements-studio.txt).
DEFAULT_PYTHON_VERSIONS = ("3.10", "3.11", "3.12", "3.13", "3.14")


def _run(cmd: list[str], cwd: Path | None = None) -> int:
    print("[RUN]", " ".join(str(c) for c in cmd), flush=True)
    p = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    return p.returncode


def ensure_wheels(wheels_dir: Path, python_versions: tuple[str, ...]) -> int:
    """Tai wheels PySide6 offline (win_amd64) vao wheels_dir.

    PySide6 hien tai phat hanh wheel `cp310-abi3-win_amd64`, tuong thich ABI
    voi moi Python 3.10+ (3.10-3.14) nen chi can tai MOT lan duy nhat thay vi
    tai rieng cho tung phien ban. ``python_versions`` chi dung de ghi log
    pham vi ho tro.
    """
    wheels_dir.mkdir(parents=True, exist_ok=True)
    req = ROOT / "requirements-studio.txt"
    print(f"[wheels] Ho tro Python: {', '.join(python_versions)} (wheel abi3 dung chung).", flush=True)
    cmd = [
        sys.executable, "-m", "pip", "download",
        "--dest", str(wheels_dir),
        "--only-binary=:all:",
        "-r", str(req),
    ]
    rc = _run(cmd)
    if rc != 0:
        print("[WARN] Tai wheels that bai; may dich van cai online duoc.")
    whls = sorted(wheels_dir.glob("*.whl"))
    for w in whls:
        print(f"[wheels]   {w.name} ({w.stat().st_size / 1e6:.1f} MB)")
    # Dong bo wheels vao vendor/wheels cua repo de lan build sau khoi tai lai.
    repo_wheels = ROOT / "vendor" / "wheels"
    if wheels_dir.resolve() != repo_wheels.resolve():
        repo_wheels.mkdir(parents=True, exist_ok=True)
        for whl in whls:
            dest = repo_wheels / whl.name
            if not dest.is_file():
                shutil.copy2(whl, dest)
    return len(whls)


def find_iscc(extra_dir: Path | None = None) -> Path | None:
    found = shutil.which("ISCC") or shutil.which("iscc")
    if found:
        return Path(found)
    candidates: list[Path] = []
    if extra_dir:
        candidates.append(extra_dir / "ISCC.exe")
    for env in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
        base = os.environ.get(env)
        if base:
            candidates.append(Path(base) / "Inno Setup 6" / "ISCC.exe")
    candidates.append(ROOT / "dist" / "inno-cache" / "innosetup" / "ISCC.exe")
    for c in candidates:
        if c.is_file():
            return c
    return None


def ensure_inno(cache_root: Path) -> Path:
    hit = find_iscc(cache_root / "innosetup")
    if hit:
        print(f"[inno] ISCC san co: {hit}")
        return hit
    cache_root.mkdir(parents=True, exist_ok=True)
    installer = cache_root / f"innosetup-{INNO_VERSION}.exe"
    if not installer.is_file():
        print(f"[inno] Tai Inno Setup {INNO_VERSION} (~10 MB) ...", flush=True)
        req = urllib.request.Request(INNO_URL, headers={"User-Agent": "LuaS30IDE-packager"})
        with urllib.request.urlopen(req, timeout=120) as r, open(installer, "wb") as f:
            shutil.copyfileobj(r, f)
        print(f"[inno] Da tai: {installer} ({installer.stat().st_size / 1e6:.1f} MB)")
    target = cache_root / "innosetup"
    print(f"[inno] Cai Inno Setup vao {target} ...", flush=True)
    rc = _run([str(installer), "/SILENT", f"/DIR={target}"])
    if rc != 0:
        raise SystemExit(f"Inno Setup silent install failed (code {rc})")
    iscc = target / "ISCC.exe"
    if not iscc.is_file():
        raise SystemExit(f"Khong tim thay ISCC.exe tai {target}")
    return iscc


def stage_tree(dest: Path, skip_optional: bool) -> None:
    """Copy toan bo IDE (ke ca .py nguon + vendor/wheels) vao thu muc staging."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    bag: list[str] = []
    for name in msi.CORE_FILES:
        src = ROOT / name
        if src.is_file():
            shutil.copy2(src, dest / name)
            bag.append(name)
    for tree in msi.CORE_DIRS:
        msi._copy_tree(ROOT, dest, tree, bag)
    if not skip_optional:
        for tree, _fid, _cg in msi.OPTIONAL_PAIRS:
            msi._copy_tree(ROOT, dest, tree, bag)
    print(f"[stage] {len(bag)} files -> {dest}")


def stage_frozen(stage: Path, frozen_dir: Path | None) -> bool:
    """Ghep thu muc frozen (LuaS30IDE.exe + _internal/) vao goc stage."""
    if frozen_dir is None:
        return False
    frozen_dir = Path(frozen_dir)
    exe = frozen_dir / "LuaS30IDE.exe"
    if not exe.is_file():
        print(f"[frozen] Khong thay {exe}; Setup se dung run.bat/VBS nhu cu.")
        return False
    for item in sorted(frozen_dir.iterdir()):
        dest = stage / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    print(f"[frozen] Da ghep LuaS30IDE.exe vao stage.")
    return True


def write_iss(iss_path: Path, stage: Path, out_dir: Path, version: str,
              iscc_dir: Path, skip_optional: bool, sign: bool = False,
              frozen: bool = False) -> Path:
    setup_name = f"LuaS30IDE-Setup-{version}"
    icon = stage / "app-icon" / "icon.ico"
    eula = stage / "EULA.rtf"
    if (ROOT / "packaging" / "EULA.rtf").is_file() and not eula.is_file():
        shutil.copy2(ROOT / "packaging" / "EULA.rtf", eula)
    vietnamese_isl = iscc_dir.parent / "Languages" / "Vietnamese.isl"
    lines: list[str] = []
    a = lines.append
    a("; Tu dong sinh boi tools/package_single_exe.py - KHONG sua tay.")
    a("; LuaS30 IDE single-file installer (Inno Setup 6).")
    a("[Setup]")
    a(f"AppId={{{APP_ID}}}")
    a(f"AppName={PRODUCT_NAME}")
    a(f"AppVersion={version}")
    a(f"AppVerName={PRODUCT_NAME} {version}")
    a(f"AppPublisher={MANUFACTURER}")
    a(f"AppPublisherURL={PUBLISHER_URL}")
    a(f"AppCopyright=© {MANUFACTURER} All rights reserved.")
    # Metadata hien trong hop thoai UAC/SmartScreen "More info".
    a(f"VersionInfoVersion={version}")
    a(f"VersionInfoCompany={MANUFACTURER}")
    a(f"VersionInfoDescription={PRODUCT_NAME} Setup")
    a(f"VersionInfoCopyright=© {MANUFACTURER} All rights reserved.")
    a(f"VersionInfoProductName={PRODUCT_NAME}")
    a(f"VersionInfoProductVersion={version}")
    if sign:
        a("SignTool=luas30sign")
        a("SignedUninstaller=yes")
    a("DefaultDirName={localappdata}\\Programs\\LuaS30 IDE")
    a("DefaultGroupName=LuaS30 IDE")
    a("PrivilegesRequired=lowest")
    a("PrivilegesRequiredOverridesAllowed=dialog")
    a(f"OutputDir={out_dir}")
    a(f"OutputBaseFilename={setup_name}")
    if icon.is_file():
        a(f"SetupIconFile={icon}")
        a(f"UninstallDisplayIcon={{app}}\\app-icon\\icon.ico")
    if eula.is_file():
        a(f"LicenseFile={eula}")
    a("WizardStyle=modern")
    a("Compression=lzma2/max")
    a("SolidCompression=yes")
    a("ArchitecturesAllowed=x64compatible")
    a("ArchitecturesInstallIn64BitMode=x64compatible")
    a("DisableProgramGroupPage=yes")
    a("UsePreviousAppDir=yes")
    a("ShowLanguageDialog=no")
    a("")
    a("[Languages]")
    a('Name: "english"; MessagesFile: "compiler:Default.isl"')
    if vietnamese_isl.is_file():
        a('Name: "vietnamese"; MessagesFile: "compiler:Languages\\Vietnamese.isl"')
    a("")
    a("[Tasks]")
    a('Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"')
    a("")
    a("[Files]")
    a(f'Source: "{stage}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs')
    a("")
    a("[Icons]")
    common = 'WorkingDir: "{app}"; IconFilename: "{app}\\app-icon\\icon.ico"'
    if frozen and (stage / "LuaS30IDE.exe").is_file():
        a(f'Name: "{{autoprograms}}\\{PRODUCT_NAME}"; Filename: "{{app}}\\LuaS30IDE.exe"; {common}; Comment: "{PRODUCT_NAME} {version}"')
        a(f'Name: "{{autodesktop}}\\{PRODUCT_NAME}"; Filename: "{{app}}\\LuaS30IDE.exe"; Tasks: desktopicon; {common}; Comment: "{PRODUCT_NAME} {version}"')
    else:
        a(f'Name: "{{autoprograms}}\\{PRODUCT_NAME}"; Filename: "{{app}}\\LuaS30-IDE.vbs"; {common}; Comment: "{PRODUCT_NAME} {version}"')
        a(f'Name: "{{autodesktop}}\\{PRODUCT_NAME}"; Filename: "{{app}}\\LuaS30-IDE.vbs"; Tasks: desktopicon; {common}; Comment: "{PRODUCT_NAME} {version}"')
    a(f'Name: "{{autoprograms}}\\{PRODUCT_NAME} (Debug Console)"; Filename: "{{app}}\\LuaS30-IDE.cmd"; WorkingDir: "{{app}}"')
    a("")
    a("[Run]")
    if frozen and (stage / "LuaS30IDE.exe").is_file():
        a('Filename: "{app}\\LuaS30IDE.exe"; Description: "{cm:LaunchProgram,LuaS30 IDE}"; Flags: nowait postinstall skipifsilent')
    else:
        a('Filename: "wscript.exe"; Parameters: """{app}\\LuaS30-IDE.vbs"""; Description: "{cm:LaunchProgram,LuaS30 IDE}"; Flags: nowait postinstall skipifsilent')
    a("")
    iss_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(f"[iss] {iss_path}")
    return iss_path


def _candidate_312s() -> list[str]:
    """Cac ban 3.12.x tu moi den cu (them ban du phong khi ban moi nhat
    chua co file embed tren FTP)."""
    found: list[str] = []
    try:
        req = urllib.request.Request(
            "https://www.python.org/ftp/python/",
            headers={"User-Agent": "LuaS30IDE-packager"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", "replace")
        vers = sorted({m.group(1) for m in re.finditer(r'href="3\.12\.(\d+)/"', html)}, key=int, reverse=True)
        found = [f"3.12.{v}" for v in vers]
    except Exception as exc:
        print(f"[python] Khong doc duoc danh sach FTP ({exc}).")
    for fallback in ("3.12.10", "3.12.9", "3.12.8"):
        if fallback not in found:
            found.append(fallback)
    return found


def _download(url: str, dest: Path, timeout: int) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LuaS30IDE-packager"})
        with urllib.request.urlopen(req, timeout=timeout) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        return True
    except Exception as exc:
        print(f"[python] Tai that bai {url} ({exc})")
        try:
            if dest.is_file():
                dest.unlink()
        except OSError:
            pass
        return False


def ensure_embedded_python(stage: Path, cache: Path) -> bool:
    """Stage Python embedded (python/) vao bo cai: may dich KHONG can cai Python.

    Tai python-3.12.x-embed-amd64.zip + get-pip.py + wheel pip, giai nen vao
    <stage>/python, bat `import site`, tao Lib/site-packages. Lan chay dau
    run.bat se bootstrap pip offline va cai PySide6 tu vendor/wheels.
    Tra ve True neu stage duoc Python kem theo.
    """
    cache.mkdir(parents=True, exist_ok=True)
    version = ""
    zip_path: Path | None = None

    def _ver_key(path: Path) -> tuple[int, ...]:
        raw = path.name[len("python-"):-len("-embed-amd64.zip")]
        return tuple(int(x) for x in raw.split(".") if x.isdigit())

    # ⚠️ Quet CACHE truoc, mang sau. `_candidate_312s()` lay danh sach tu FTP nen
    # tra ve "ban moi nhat truoc"; ban da cache (thuong cu hon) nam CUOI danh
    # sach ⇒ truoc day moi lan build deu thu tai 4-5 ban khong co trong cache
    # (404) roi moi dung ban cache. Do duoc: 4 lan 404 truoc khi roi vao cache
    # 3.12.10. Quet cache truoc ⇒ build chay OFFLINE khi da co san.
    cached_zips = sorted(cache.glob("python-3.12.*-embed-amd64.zip"), key=_ver_key)
    if cached_zips:
        pick = cached_zips[-1]
        version = pick.name[len("python-"):-len("-embed-amd64.zip")]
        zip_path = pick
        print(f"[python] Dung Python embedded cache san: {pick.name}")

    for cand in (() if zip_path else _candidate_312s()):
        name = f"python-{cand}-embed-amd64.zip"
        dest = cache / name
        if dest.is_file():
            version, zip_path = cand, dest
            print(f"[python] Dung Python embedded cache san: {name}")
            break
        url = f"https://www.python.org/ftp/python/{cand}/{name}"
        print(f"[python] Thu Python embedded {cand} (~18 MB) ...", flush=True)
        if _download(url, dest, 180):
            version, zip_path = cand, dest
            break
    if not version or zip_path is None:
        print("[WARN] Khong tai duoc Python embedded. Setup van build tiep "
              "nhung may dich se can Python 3.10+ cai san.")
        return False
    getpip = cache / "get-pip.py"
    if not getpip.is_file():
        print("[python] Tai get-pip.py ...", flush=True)
        if not _download("https://bootstrap.pypa.io/get-pip.py", getpip, 120):
            print("[WARN] Khong tai duoc get-pip.py. Bo qua Python kem theo.")
            return False
    pip_whl = sorted(cache.glob("pip-*.whl"))
    if not pip_whl:
        print("[python] Tai wheel pip (de bootstrap offline) ...", flush=True)
        rc = _run([sys.executable, "-m", "pip", "download", "--dest", str(cache),
                   "--no-deps", "--only-binary=:all:", "pip"])
        if rc != 0:
            print("[WARN] Khong tai duoc wheel pip. Bo qua Python kem theo.")
            return False
        pip_whl = sorted(cache.glob("pip-*.whl"))
        if not pip_whl:
            print("[WARN] Khong tim thay wheel pip sau khi tai.")
            return False

    target = stage / "python"
    if target.exists():
        shutil.rmtree(target)
    (target / "bootstrap").mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(target)
    shutil.copy2(getpip, target / "bootstrap" / "get-pip.py")
    for whl in pip_whl:
        shutil.copy2(whl, target / "bootstrap" / whl.name)
    # Bat site-packages cho embedded python (mac dinh `import site` bi comment).
    major = version.split(".")[0] + version.split(".")[1]  # "312"
    pth = target / f"python{major}._pth"
    if pth.is_file():
        text = pth.read_text(encoding="utf-8", errors="replace")
        text = text.replace("#import site", "import site")
        if "import site" not in text:
            text = text.rstrip("\n") + "\nimport site\n"
        if "Lib\\site-packages" not in text and "Lib/site-packages" not in text:
            text = text.rstrip("\n") + "\nLib\\site-packages\n"
        # Embedded chay isolated mode: khong tu them thu muc script vao
        # sys.path nen cac tools/*.py goi nhau that bai. Them ../tools
        # (tuong doi tu python/ -> tools/ canh ben) de moi subprocess
        # deu import duoc nhau ma khong can sua tung file.
        if "../tools" not in text.replace("\\", "/"):
            text = text.rstrip("\n") + "\n../tools\n"
        pth.write_text(text, encoding="utf-8")
    (target / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)
    exe = target / "python.exe"
    print(f"[python] Da stage Python kem theo: {exe} ({version})")
    return exe.is_file()


def main() -> int:
    ap = argparse.ArgumentParser(description="Build DUY NHAT 1 file LuaS30IDE-Setup-<ver>.exe")
    ap.add_argument("--out", type=Path, default=ROOT / "dist")
    ap.add_argument("--skip-optional", action="store_true",
                    help="Bo toolchain/emulator (file Setup nho hon; copy thu cong sau)")
    ap.add_argument("--skip-wheels", action="store_true",
                    help="Khong tai wheels offline (dung vendor/wheels san co neu co)")
    ap.add_argument("--python-versions", default=",".join(DEFAULT_PYTHON_VERSIONS),
                    help="VD: 3.12  hoac  3.10,3.11,3.12,3.13,3.14")
    ap.add_argument("--inno-cache", type=Path, default=ROOT / "dist" / "inno-cache")
    ap.add_argument("--sign-pfx", type=Path, default=None,
                    help="File .pfx de ky so Setup EXE (chong SmartScreen). KHONG commit file nay.")
    ap.add_argument("--sign-password", default=os.environ.get("LUAS30_SIGN_PASSWORD", ""),
                    help="Mat khau PFX (khuyen dung env LUAS30_SIGN_PASSWORD)")
    ap.add_argument("--sign-timestamp", default=signmod.DEFAULT_TIMESTAMP)
    ap.add_argument("--signtool", default=None, help="Duong dan signtool.exe (tu tim neu bo trong)")
    ap.add_argument("--skip-python", action="store_true",
                    help="Khong dong goi Python kem theo (may dich can Python 3.10+ cai san)")
    ap.add_argument("--py-cache", type=Path, default=ROOT / "dist" / "py-embed-cache")
    ap.add_argument("--frozen-dir", type=Path, default=ROOT / "dist" / "frozen" / "LuaS30IDE",
                    help="Thu muc frozen (build_frozen.py). Khong co thi bo qua exe frozen.")
    ap.add_argument("--skip-frozen", action="store_true",
                    help="Khong ghep LuaS30IDE.exe (dung run.bat/VBS nhu cu)")
    ap.add_argument("--skip-verify", action="store_true",
                    help="Bo qua verify_release.py tren stage")
    args = ap.parse_args()

    out_dir: Path = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    version = msi._version()

    if not ICON_SRC.is_file():
        print(f"[WARN] Thieu icon {ICON_SRC}; Setup se dung icon mac dinh.")

    wheels_dir = ROOT / "vendor" / "wheels"
    if args.skip_wheels:
        n = len(list(wheels_dir.glob("*.whl"))) if wheels_dir.is_dir() else 0
        print(f"[wheels] Bo qua tai moi; dung {n} file .whl san co trong vendor/wheels.")
    else:
        versions = tuple(v.strip() for v in str(args.python_versions).split(",") if v.strip())
        ensure_wheels(wheels_dir, versions)

    iscc = ensure_inno(args.inno_cache.resolve()).resolve()

    # Tuy chon ky so: can PFX do CA tin cay cap (OV/EV). Khong co PFX thi
    # build khong ky nhu cu (SmartScreen se canh bao tren may la).
    do_sign = args.sign_pfx is not None
    sign_param: list[str] = []
    if do_sign:
        pfx = args.sign_pfx
        if not pfx.is_file():
            raise SystemExit(f"[ERROR] Khong thay PFX: {pfx}")
        if not args.sign_password:
            raise SystemExit("[ERROR] Thieu mat khau PFX (--sign-password hoac LUAS30_SIGN_PASSWORD).")
        st = signmod.find_signtool(args.signtool)
        if not st:
            raise SystemExit("[ERROR] Khong tim thay signtool.exe (cai Windows SDK).")
        print(f"[sign] Ky so bang PFX: {pfx} (signtool: {st})")
        ts = (args.sign_timestamp or "").strip()
        ts_args = "" if ts.lower() == "none" else f"/td sha256 /tr {ts} "
        cmd = (
            f'"{st}" sign /f "{pfx}" /p "{args.sign_password}" '
            f'/fd sha256 {ts_args}$f'
        )
        sign_param = [f'/S"luas30sign={cmd}"']

    # ⚠️ Scratch (stage = ca IDE + toolchain + emulator + python) PHAI nam trong
    # temp cua OS, KHONG duoc `dir=str(out_dir)`: hook `[safe-delete]` cua host
    # chan `shutil.rmtree` khi so muc xoa trong MOT luot vuot nguong (50 muc) va
    # chi mien cac duong dan duoi temp. Don stage trong `dist/` se lam script
    # CHET voi `exit 1` ma khong in gi (stderr bi nuot) — trong y nhu "ISCC hong".
    with tempfile.TemporaryDirectory(prefix="luas30-setup-") as tmp:
        work = Path(tmp).resolve()
        stage = work / "stage"
        stage_tree(stage, skip_optional=args.skip_optional)
        if args.skip_python:
            print("[python] Bo qua Python kem theo (--skip-python).")
        else:
            ensure_embedded_python(stage, args.py_cache.resolve())
        has_frozen = False if args.skip_frozen else stage_frozen(stage, args.frozen_dir)
        if not args.skip_verify:
            print("[verify] Chay verify_release.py tren stage ...", flush=True)
            rc_v = subprocess.run([sys.executable, str(ROOT / "tools" / "verify_release.py"),
                                   str(stage)]).returncode
            if rc_v != 0:
                raise SystemExit(f"verify_release failed (code {rc_v})")
        iss = write_iss(work / "LuaS30IDE.iss", stage, out_dir, version,
                        iscc.parent, args.skip_optional, sign=do_sign, frozen=has_frozen)
        rc = _run([str(iscc), *sign_param, str(iss)])
        if rc != 0:
            raise SystemExit(f"ISCC failed (code {rc}); giu nguyen {iss} de kiem tra.")

    setup = out_dir / f"LuaS30IDE-Setup-{version}.exe"
    if not setup.is_file():
        raise SystemExit("Khong thay file Setup exe sau khi bien dich.")
    import hashlib
    digest = hashlib.sha256(setup.read_bytes()).hexdigest()
    (setup.parent / f"{setup.name}.sha256").write_text(
        f"{digest}  {setup.name}\n", encoding="utf-8")
    print(f"[OK] SHA-256: {digest}")
    mb = setup.stat().st_size / (1024 * 1024)
    print("")
    print(f"[OK] DUY NHAT 1 FILE: {setup}")
    print(f"[OK] Dung luong: {mb:.1f} MB")
    print(f"[OK] Cai dat: \"{setup.name}\"  (wizard)")
    print(f"[OK] Cai im lang: \"{setup.name}\" /SILENT  (hoac /VERYSILENT)")
    print("[OK] Go bo cai dat: Settings > Apps > LuaS30 IDE > Uninstall")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
