from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"tools"))

import build
from toolchain_profiles import detect_toolchain

errors=[]

with tempfile.TemporaryDirectory() as td:
    src=Path(td)/"probe.c"
    build.write_probe(src,"gcc_entry")
    raw=src.read_bytes()
    text=raw.decode("ascii")
    if b"\\n" in raw:
        errors.append("generated probe still contains literal backslash-n")
    if not raw.endswith(b"\n"):
        errors.append("generated probe does not end with a real newline")
    if "void gcc_entry(" not in text:
        errors.append("generated probe does not model gcc_entry")
    if text.count("\n") < 5:
        errors.append("generated probe is not multiline C source")

profiles=(ROOT/"tools/toolchain_profiles.py").read_text(encoding="utf-8")
for token in (
    "-march=armv5te",
    "-fpic",
    "-mlittle-endian",
    "-fvisibility=hidden",
    "-D__MRE_COMPILER_GCC__",
    'entry_symbol="gcc_entry"',
    "-fpcc-struct-return",
):
    if token not in profiles:
        errors.append("GCC MRE profile missing: "+token)

builder=(ROOT/"tools/build.py").read_text(encoding="utf-8")
for token in ("compile_command","link_command","write_probe","toolchain_preflight"):
    if token not in builder:
        errors.append("build.py missing shared MRE GCC pipeline: "+token)

if errors:
    print("FAIL")
    for error in errors:
        print(" -",error)
    raise SystemExit(1)

print("PASS: generated GCC probe contains real newlines")
print("PASS: GCC profile keeps ARMv5TE/PIC/little-endian MRE flags")
print("PASS: gcc_entry remains the GCC entry convention")
print("PASS: GCC now shares the multi-toolchain compile/link pipeline")
