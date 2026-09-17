# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec cho LuaS30 Studio (kieu VXPEngine.spec).

Ket qua: dist-frozen/LuaS30IDE/LuaS30IDE.exe (windowed, icon app).
Thu muc tools/toolchain/emulator/python/app-icon/... nam canh exe
(o do build_frozen.py / package_single_exe.py ghep vao), Studio doc
chung qua engine_root = thu muc chua exe.
"""
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parents[1]

a = Analysis(
    [str(ROOT / "studio" / "main.py")],
    pathex=[str(ROOT / "studio")],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pip", "setuptools", "ensurepip", "venv"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LuaS30IDE",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / "app-icon" / "icon.ico"),
    contents_directory=".",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="LuaS30IDE",
)
