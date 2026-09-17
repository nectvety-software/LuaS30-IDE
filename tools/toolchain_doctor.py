from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"tools"))

from toolchain_profiles import PROFILE_IDS, configure_environment, detect_toolchain, version_text
from build import compile_command, link_command, write_probe


def run(cmd):
    print("[RUN]"," ".join(str(x) for x in cmd))
    p=subprocess.run(
        [str(x) for x in cmd],
        capture_output=True,text=True,errors="replace",
        env=os.environ.copy(),
    )
    if p.stdout: print(p.stdout,end="")
    if p.stderr: print(p.stderr,end="",file=sys.stderr)
    return p


def main():
    ap=argparse.ArgumentParser(description="Diagnose LuaS30 MRE compiler toolchains")
    ap.add_argument("--toolchain",required=True,type=Path)
    ap.add_argument("--profile",choices=PROFILE_IDS,default="auto")
    ap.add_argument("--entry-symbol")
    args=ap.parse_args()

    try:
        tc=detect_toolchain(args.toolchain,args.profile)
    except Exception as exc:
        print("[FAIL]",exc)
        return 2

    configure_environment(tc)
    entry=args.entry_symbol or tc.entry_symbol
    print("Profile:",tc.profile_id, "-",tc.display_name)
    print("Toolchain:",tc.root)
    print("Compiler:",tc.compiler)
    print("Linker:",tc.linker)
    print("Entry:",entry)
    version=version_text(tc.compiler,tc.compiler_family)
    if version: print(version.splitlines()[0])

    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        src=td/"probe.c";obj=td/"probe.o";axf=td/"probe.axf"
        write_probe(src,entry)
        p=run(compile_command(tc,src,obj,probe=True))
        if p.returncode or not obj.is_file():
            print("[FAIL] compiler/assembler probe failed")
            return p.returncode or 3
        p=run(link_command(tc,[obj],axf,entry))
        if p.returncode or not axf.is_file():
            print("[FAIL] linker/entry probe failed")
            return p.returncode or 4

    print(f"[PASS] {tc.display_name}: compiler + assembler + linker + {entry}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
