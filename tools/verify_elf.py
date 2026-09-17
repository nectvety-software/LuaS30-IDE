from __future__ import annotations
import re, subprocess, sys
from pathlib import Path

from utf8_stdio import configure_utf8_stdio, utf8_env

configure_utf8_stdio()

def run(readelf, *args):
    p=subprocess.run(
        [str(readelf),*args],
        capture_output=True,text=True,
        encoding="utf-8",errors="replace",
        env=utf8_env(),
    )
    if p.returncode: raise SystemExit(p.stdout+p.stderr)
    return p.stdout

def verify(readelf: Path, elf: Path):
    h=run(readelf,"-h",elf); ph=run(readelf,"-l",elf); sy=run(readelf,"-sW",elf); rel=run(readelf,"-rW",elf)
    checks={
      "ELF32":"Class:" in h and "ELF32" in h,
      "ARM":"Machine:" in h and "ARM" in h,
      "EABI5":"Version5 EABI" in h,
      "gcc_entry": bool(re.search(r"\bgcc_entry\b",sy)),
      "no_vm_undefined": not bool(re.search(r"UND\s+vm_[A-Za-z0-9_]",sy)),
      "no_percommon_symbols": "_vm_malloc" not in sy,
    }
    text="# CoreMRE-NG ELF report\n\n"+"\n".join(f"{k}: {'PASS' if v else 'FAIL'}" for k,v in checks.items())+"\n\n## ELF header\n```\n"+h+"```\n\n## Program headers\n```\n"+ph+"```\n\n## Dynamic/undefined VM symbol check\n```\n"+"No static MRE API imports expected.\n"+"```\n"
    return all(checks.values()),text

if __name__=="__main__":
    configure_utf8_stdio()
    if len(sys.argv)!=4: raise SystemExit("usage: verify_elf.py <readelf> <elf> <report>")
    ok,text=verify(Path(sys.argv[1]),Path(sys.argv[2]));Path(sys.argv[3]).write_text(text,encoding="utf-8",errors="replace");print(text.split("## ELF header")[0]);raise SystemExit(0 if ok else 2)
