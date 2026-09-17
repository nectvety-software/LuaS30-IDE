from __future__ import annotations
import argparse, json, os, platform, subprocess, sys
from pathlib import Path

def run_version(cmd):
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,errors='replace',timeout=15)
        text=(p.stdout or p.stderr).strip().splitlines()
        return {"ok":p.returncode==0,"version":text[0] if text else "","code":p.returncode}
    except Exception as e:
        return {"ok":False,"error":str(e)}

def f(path:Path):
    return {"exists":path.is_file(),"path":str(path),"size":path.stat().st_size if path.is_file() else 0}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent.parent)
    ap.add_argument('--write',type=Path)
    a=ap.parse_args()
    root=a.root.resolve()
    report={
        "engine":"LuaS30 IDE","version":((root/"VERSION").read_text(encoding="utf-8").strip() if (root/"VERSION").is_file() else "unknown"),
        "platform":platform.platform(),"python":sys.version,
        "python_executable":sys.executable,
        "components":{}
    }
    try:
        import PySide6
        from PySide6.QtCore import qVersion
        report["pyside6"]={"ok":True,"version":PySide6.__version__,"qt":qVersion()}
    except Exception as e:
        report["pyside6"]={"ok":False,"error":str(e)}
    gcc=root/'toolchain/arm-gcc/bin/arm-none-eabi-gcc.exe'
    readelf=root/'toolchain/arm-gcc/bin/arm-none-eabi-readelf.exe'
    emu=root/'emulator/VXPEmu.exe'
    report["components"]["gcc"]={**f(gcc),**(run_version([str(gcc),'--version']) if gcc.is_file() else {})}
    report["components"]["readelf"]={**f(readelf),**(run_version([str(readelf),'--version']) if readelf.is_file() else {})}
    report["components"]["emulator"]=f(emu)
    report["components"]["coremre_entry"]=f(root/'engine/src/coremre_entry.c')
    report["components"]["lua_5_1"]=f(root/'vendor/lua-5.1.5/src/lua.h')
    mandatory=[report['pyside6'].get('ok',False),gcc.is_file(),readelf.is_file(),emu.is_file(),(root/'engine/src/coremre_entry.c').is_file()]
    report["ready"]=all(mandatory)
    text=json.dumps(report,indent=2,ensure_ascii=False)
    print(text)
    if a.write:
        target=a.write if a.write.is_absolute() else root/a.write
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(text,encoding='utf-8')
    return 0 if report['ready'] else 1

if __name__=='__main__':
    raise SystemExit(main())
