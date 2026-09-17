from __future__ import annotations

"""
package_msi.py — Build LuaS30 IDE MSI with WiX 3 (binaries under packaging/wix).

Usage:
  py tools/package_msi.py --out dist
  py tools/package_msi.py --out dist --skip-optional   # core only (smaller)
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
WIX_DIR = ROOT / "packaging" / "wix"
CANDLE = WIX_DIR / "candle.exe"
LIGHT = WIX_DIR / "light.exe"
UPGRADE_CODE = "{A3F5C2D1-8B4E-4F7A-9C10-6E7541301D01}"
PRODUCT_NAME = "LuaS30 IDE"
MANUFACTURER = "LuaS30"
ICON_SRC = ROOT / "app-icon" / "icon.ico"

CORE_FILES = [
    "VERSION",
    "LICENSE",
    "README.md",
    "requirements-studio.txt",
    "run.bat",
    "build.bat",
    "build_only.bat",
    "new_project.bat",
    "LuaS30-IDE.cmd",
    "LuaS30-IDE.vbs",
    "install_silent.cmd",
]
CORE_DIRS = [
    "studio",
    "tools",
    "engine",
    "sdk",
    "templates",
    "profiles",
    "compat",
    "app-icon",
    "doc",
    "wiki",
    "vendor",
]
OPTIONAL_PAIRS = [
    ("toolchain", "ToolchainFeature", "CG_Toolchain"),
    ("emulator", "EmulatorFeature", "CG_Emulator"),
]
SKIP_PARTS = {
    "__pycache__",
    ".luas30-tmp",
    ".git",
    "wix",
    "dist",
    "build",
    ".workbuddy-ai",
    "packaging",
}
SKIP_SUFFIXES = {
    ".tmp",
    ".log",
    ".vxp",
    ".axf",
    ".pdb",
    ".msi",
    ".cab",
    ".wixobj",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}
SKIP_NAMES = {
    ".ds_store",
    "thumbs.db",
    "ai_credentials.json",
    "secrets.json",
    "credentials.json",
    "id_rsa",
    "id_ed25519",
    ".env",
}


def _version() -> str:
    text = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").is_file() else "1.0.0"
    parts = [p for p in text.split(".") if p.isdigit()]
    while len(parts) < 3:
        parts.append("0")
    return ".".join(parts[:3])


def _id(prefix: str, *parts: str) -> str:
    raw = prefix + "|" + "|".join(p.replace("\\", "/") for p in parts)
    return f"{prefix}{hashlib.md5(raw.encode('utf-8')).hexdigest()[:12]}"


def _guid() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


def _iter_files(base: Path):
    if not base.is_dir():
        return
    for path in sorted(base.rglob("*"), key=lambda p: str(p).lower()):
        if not path.is_file():
            continue
        rel = path.relative_to(base)
        if any(part in SKIP_PARTS or part.startswith(".") for part in rel.parts):
            continue
        if path.name.lower() in SKIP_NAMES or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        yield path


def _copy_tree(src_root: Path, dest_root: Path, rel_dir: str, bag: list) -> None:
    base = src_root / rel_dir
    if not base.is_dir():
        return
    for f in _iter_files(base):
        rel = Path(rel_dir) / f.relative_to(base)
        dest = dest_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
        bag.append(rel.as_posix())


# Python sources that ship as compiled bytecode only (not plain .py).
BYTECODE_TREES = ("studio", "tools")


def _compile_tree_to_pyc(dest_root: Path, rel_dir: str, bag: list[str]) -> None:
    """Copy Python package, compile to sourceless .pyc, drop .py sources."""
    src = ROOT / rel_dir
    if not src.is_dir():
        return
    stage = dest_root / rel_dir
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(src, stage, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # compileall -b: place module.pyc next to where module.py was (sourceless import).
    proc = subprocess.run(
        [sys.executable, "-m", "compileall", "-b", "-f", "-q", str(stage)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(f"compileall failed for {rel_dir}")
    # Remove sources + leftover caches so the MSI only ships bytecode for these trees.
    for path in sorted(stage.rglob("*"), reverse=True):
        if path.is_file() and path.suffix == ".py":
            path.unlink()
        elif path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass
    for f in _iter_files(stage):
        bag.append((Path(rel_dir) / f.relative_to(stage)).as_posix())


def build_msi(out_dir: Path, skip_optional: bool = False) -> Path:
    if not CANDLE.is_file() or not LIGHT.is_file():
        raise SystemExit(f"WiX missing at {WIX_DIR}. Expected candle.exe/light.exe")

    version = _version()
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="luas30-msi-") as tmp:
        work = Path(tmp)
        source = work / "source"
        source.mkdir(parents=True)

        core_files: list[str] = []
        for name in CORE_FILES:
            src = ROOT / name
            if not src.is_file():
                continue
            dest = source / name
            shutil.copy2(src, dest)
            core_files.append(name)

        for tree in CORE_DIRS:
            if tree in BYTECODE_TREES:
                _compile_tree_to_pyc(source, tree, core_files)
            else:
                _copy_tree(ROOT, source, tree, core_files)

        optional_groups: dict[str, list[str]] = {}
        if not skip_optional:
            for tree, _fid, cg in OPTIONAL_PAIRS:
                bag: list[str] = []
                _copy_tree(ROOT, source, tree, bag)
                optional_groups[cg] = bag

        if ICON_SRC.is_file():
            shutil.copy2(ICON_SRC, source / "appicon.ico")
        eula_src = ROOT / "packaging" / "EULA.rtf"
        if eula_src.is_file():
            shutil.copy2(eula_src, source / "EULA.rtf")

        # Collect unique directory parents for DirectoryRef
        all_rels = list(core_files)
        for bag in optional_groups.values():
            all_rels.extend(bag)

        dir_map: dict[str, str] = {"": "INSTALLDIR"}  # rel dir posix -> id
        parents: dict[str, str] = {}

        def ensure_dir(rel_dir: str) -> str:
            rel_dir = "" if rel_dir in {".", ""} else rel_dir
            if rel_dir in dir_map:
                return dir_map[rel_dir]
            parent_key = str(Path(rel_dir).parent.as_posix())
            if parent_key == ".":
                parent_key = ""
            parent_id = ensure_dir(parent_key)
            did = _id("D", rel_dir)
            dir_map[rel_dir] = did
            parents[did] = parent_id
            return did

        for rel in all_rels:
            ensure_dir(str(Path(rel).parent.as_posix()) if Path(rel).parent.as_posix() != "." else "")

        product_id = _guid()
        icon_ok = (source / "appicon.ico").is_file()
        wxs = work / "product.wxs"
        w: list[str] = []
        a = w.append
        a('<?xml version="1.0" encoding="UTF-8"?>')
        a('<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">')
        a(f'  <Product Id="{product_id}" Name="{escape(PRODUCT_NAME)}" Language="1033"')
        a(f'           Version="{version}" Manufacturer="{escape(MANUFACTURER)}"')
        a(f'           UpgradeCode="{UPGRADE_CODE}">')
        a(f'    <Package InstallerVersion="500" Compressed="yes" InstallScope="perUser" Platform="x64"/>')
        a(f'    <MajorUpgrade DowngradeErrorMessage="A newer version of {escape(PRODUCT_NAME)} is already installed."/>')
        a('    <MediaTemplate EmbedCab="yes" CompressionLevel="high"/>')
        a('    <Property Id="AUTOLAUNCH" Value="1" Secure="yes"/>')
        if icon_ok:
            a('    <Icon Id="LuaS30Icon" SourceFile="source\\appicon.ico"/>')
            a('    <Property Id="ARPPRODUCTICON" Value="LuaS30Icon"/>')
        a(f'    <Property Id="WIXUI_INSTALLDIR" Value="INSTALLDIR"/>')
        if (source / "EULA.rtf").is_file():
            a('    <Property Id="WIXUI_LICENSE_RTF" Value="source\\EULA.rtf"/>')

        # Per-user layout (like VXPEngine): %LOCALAPPDATA%\Programs\LuaS30 IDE
        a('    <Directory Id="TARGETDIR" Name="SourceDir">')
        a('      <Directory Id="LocalAppDataFolder">')
        a('        <Directory Id="ProgramsFolder" Name="Programs">')
        a('          <Directory Id="INSTALLDIR" Name="LuaS30 IDE"/>')
        a('        </Directory>')
        a('      </Directory>')
        a('      <Directory Id="ProgramMenuFolder" Name="LuaS30 IDE"/>')
        a('      <Directory Id="DesktopFolder"/>')
        a('    </Directory>')

        # Nested dirs under INSTALLDIR
        for rel, did in sorted(dir_map.items(), key=lambda kv: (kv[0].count("/"), kv[0])):
            if rel == "":
                continue
            parent = parents.get(did, "INSTALLDIR")
            a(f'    <DirectoryRef Id="{parent}">')
            a(f'      <Directory Id="{did}" Name="{escape(Path(rel).name)}"/>')
            a('    </DirectoryRef>')

        # Component definitions live under DirectoryRef (not inside ComponentGroup).
        # ComponentGroup only holds ComponentRef children.
        def components_for(rels: list[str]):
            items = []
            for rel in sorted(set(rels)):
                rel_path = Path(rel)
                parent_key = str(rel_path.parent.as_posix()) if rel_path.parent.as_posix() != "." else ""
                dir_id = dir_map.get(parent_key, "INSTALLDIR")
                cid = _id("C", rel)
                fid = _id("F", rel)
                items.append((dir_id, cid, fid, rel_path, rel))
            return items

        # Emit DirectoryRef/Component pairs for all groups
        group_refs: dict[str, list[str]] = {
            "CG_Core": list(core_files),
        }
        if not skip_optional:
            for tree, fid, cg in OPTIONAL_PAIRS:
                group_refs[cg] = list(optional_groups.get(cg, []))

        # Group by directory to reduce nesting noise
        dir_to_components: dict[str, list] = {}
        for gid, rels in group_refs.items():
            for item in components_for(rels):
                dir_to_components.setdefault(item[0], []).append(item)

        for dir_id, items in sorted(dir_to_components.items(), key=lambda kv: kv[0]):
            a(f'    <DirectoryRef Id="{dir_id}">')
            for _d, cid, fid, rel_path, rel in items:
                a(f'      <Component Id="{cid}" Guid="{_guid()}">')
                a(f'        <File Id="{fid}" Name="{escape(rel_path.name)}" Source="source\\{escape(rel.replace("/", "\\"))}" KeyPath="yes"/>')
                a('      </Component>')
            a('    </DirectoryRef>')

        # Non-advertised shortcuts -> hidden VBS launcher (no console flash)
        icon_attr = f' Icon="LuaS30Icon" IconIndex="0"' if icon_ok else ""
        a('    <DirectoryRef Id="ProgramMenuFolder">')
        a(f'      <Component Id="cmp_shortcut_start" Guid="{_guid()}">')
        a(f'        <Shortcut Id="sc_start" Name="{escape(PRODUCT_NAME)}" Target="[INSTALLDIR]LuaS30-IDE.vbs" WorkingDirectory="INSTALLDIR" Advertise="no"{icon_attr} Description="{escape(PRODUCT_NAME)} {version}"/>')
        a(f'        <RegistryValue Root="HKCU" Key="Software\\{escape(MANUFACTURER)}\\{escape(PRODUCT_NAME)}" Name="StartMenuShortcut" Type="string" Value="1" KeyPath="yes"/>')
        a('      </Component>')
        a('    </DirectoryRef>')
        a('    <DirectoryRef Id="DesktopFolder">')
        a(f'      <Component Id="cmp_shortcut_desktop" Guid="{_guid()}">')
        a(f'        <Shortcut Id="sc_desktop" Name="{escape(PRODUCT_NAME)}" Target="[INSTALLDIR]LuaS30-IDE.vbs" WorkingDirectory="INSTALLDIR" Advertise="no"{icon_attr} Description="{escape(PRODUCT_NAME)} {version}"/>')
        a(f'        <RegistryValue Root="HKCU" Key="Software\\{escape(MANUFACTURER)}\\{escape(PRODUCT_NAME)}" Name="DesktopShortcut" Type="string" Value="1" KeyPath="yes"/>')
        a('      </Component>')
        a('    </DirectoryRef>')

        for gid, rels in group_refs.items():
            if not rels:
                a(f'    <ComponentGroup Id="{gid}"/>')
                continue
            a(f'    <ComponentGroup Id="{gid}">')
            for _d, cid, _fid, _rp, _rel in components_for(rels):
                a(f'      <ComponentRef Id="{cid}"/>')
            if gid == "CG_Core":
                a('      <ComponentRef Id="cmp_shortcut_start"/>')
                a('      <ComponentRef Id="cmp_shortcut_desktop"/>')
            a('    </ComponentGroup>')
        if skip_optional:
            a('    <ComponentGroup Id="CG_Toolchain"/>')
            a('    <ComponentGroup Id="CG_Emulator"/>')

        a('    <Feature Id="ProductFeature" Title="' + escape(PRODUCT_NAME) + '" Level="1">')
        a('      <ComponentGroupRef Id="CG_Core"/>')
        a('    </Feature>')
        if not skip_optional:
            for tree, fid, cg in OPTIONAL_PAIRS:
                level = "20" if "toolchain" in tree else "30"
                a(f'    <Feature Id="{fid}" Title="{escape(PRODUCT_NAME)} {escape(tree)}" Level="{level}" Absent="allow">')
                a(f'      <ComponentGroupRef Id="{cg}"/>')
                a('    </Feature>')

        # Launch app once after a successful fresh/upgrade install (silent or UI).
        a('    <CustomAction Id="LaunchAppAfterInstall"')
        a('                  Directory="INSTALLDIR"')
        a('                  ExeCommand="wscript.exe &quot;[INSTALLDIR]LuaS30-IDE.vbs&quot;"')
        a('                  Execute="immediate"')
        a('                  Return="asyncNoWait"/>')
        a('    <InstallExecuteSequence>')
        a('      <Custom Action="LaunchAppAfterInstall" After="InstallFinalize">')
        a('        <![CDATA[NOT Installed AND AUTOLAUNCH=1]]>')
        a('      </Custom>')
        a('    </InstallExecuteSequence>')

        if icon_ok:
            a('    <UIRef Id="WixUI_InstallDir"/>')
            a('    <UIRef Id="WixUI_ErrorProgressText"/>')
        a('  </Product>')
        a('</Wix>')

        wxs.write_text("\n".join(w) + "\n", encoding="utf-8")

        wixobj = work / "product.wixobj"
        msi = out_dir / f"LuaS30IDE-{version}.msi"
        if msi.exists():
            msi.unlink()

        def run(cmd: list[str]) -> int:
            print("[RUN]", " ".join(cmd))
            p = subprocess.run(cmd, cwd=str(work), capture_output=True, text=True)
            if p.returncode != 0:
                print(p.stdout)
                print(p.stderr, file=sys.stderr)
            else:
                if p.stdout.strip():
                    print(p.stdout)
            return p.returncode

        candle = [str(CANDLE), "-nologo", "-arch", "x64", "-out", str(wixobj), str(wxs)]
        rc = run(candle)
        if rc != 0:
            # UIRef may fail without extension
            text = wxs.read_text(encoding="utf-8")
            text = text.replace('    <UIRef Id="WixUI_InstallDir"/>\n', "")
            text = text.replace('    <UIRef Id="WixUI_ErrorProgressText"/>\n', "")
            wxs.write_text(text, encoding="utf-8")
            rc = run(candle)
            if rc != 0:
                raise SystemExit(rc)

        light = [
            str(LIGHT), "-nologo", "-sval", "-spdb",
            "-ext", "WixUIExtension",
            "-out", str(msi), str(wixobj),
        ]
        rc = run(light)
        if rc != 0:
            # Retry without UI extension if WixUI refs are still present
            text = wxs.read_text(encoding="utf-8")
            text = text.replace('    <UIRef Id="WixUI_InstallDir"/>\n', "")
            text = text.replace('    <UIRef Id="WixUI_ErrorProgressText"/>\n', "")
            wxs.write_text(text, encoding="utf-8")
            rc = run([str(CANDLE), "-nologo", "-arch", "x64", "-out", str(wixobj), str(wxs)])
            if rc != 0:
                raise SystemExit(rc)
            rc = run([str(LIGHT), "-nologo", "-sval", "-spdb", "-out", str(msi), str(wixobj)])
            if rc != 0:
                raise SystemExit(rc)

    return msi


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "dist")
    ap.add_argument("--skip-optional", action="store_true")
    args = ap.parse_args()
    msi = build_msi(args.out, skip_optional=args.skip_optional)
    silent = ROOT / "install_silent.cmd"
    if silent.is_file():
        shutil.copy2(silent, args.out / "install_silent.cmd")
        print(f"[OK] Silent installer wrapper: {args.out / 'install_silent.cmd'}")
    mb = msi.stat().st_size / (1024 * 1024)
    print(f"[OK] MSI: {msi}")
    print(f"[OK] Size: {mb:.1f} MB")
    print(f"[OK] UpgradeCode: {UPGRADE_CODE}")
    print(f"[OK] Install path: %LOCALAPPDATA%\\Programs\\LuaS30 IDE")
    print("[OK] After install the IDE launches via LuaS30-IDE.vbs (AUTOLAUNCH=1)")
    print("[OK] Background install: dist\\install_silent.cmd  (msiexec /qn + launch)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
