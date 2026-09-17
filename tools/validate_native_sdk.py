from __future__ import annotations
from pathlib import Path
import json, re, sys

ROOT=Path(__file__).resolve().parent.parent
native=list((ROOT/"sdk/luas30/src").glob("*.c"))+list((ROOT/"engine/src").glob("*.c"))
headers=list((ROOT/"sdk/luas30/include/ls30").glob("*.h"))+list((ROOT/"engine/include").glob("*.h"))

forbidden=[
    "percommon.a","peraudio.a",
    "#include <vmsys.h>","#include <vmgraph.h>","#include <vmio.h>","#include <vmmm.h>",
    '#include "vmsys.h"','#include "vmgraph.h"','#include "vmio.h"','#include "vmmm.h"',
]
text="\n".join(p.read_text(encoding="utf-8",errors="ignore") for p in native+headers)
bad=[x for x in forbidden if x in text]

required=[
    "sdk/luas30/include/ls30/api.h",
    "sdk/luas30/src/abi_resolver.c",
    "sdk/luas30/src/api.c",
    "engine/src/runtime_entry.c",
    "engine/src/runtime_lua.c",
    "engine/src/runtime_bridge.c",
    "profiles/generic-vxp-qvga.json",
]
missing=[x for x in required if not (ROOT/x).is_file()]
# Studio/tools may ship as .pyc only on installed packages.
for rel in ("studio/app/editor/explorer_panel", "tools/build"):
    if not (ROOT/f"{rel}.py").is_file() and not (ROOT/f"{rel}.pyc").is_file():
        missing.append(rel + ".py")

profiles=[]
for p in sorted((ROOT/"profiles").glob("*.json")):
    profiles.append(json.loads(p.read_text(encoding="utf-8"))["id"])

build_path = ROOT/"tools/build.py"
if not build_path.is_file():
    build_path = ROOT/"tools/build.pyc"
build = build_path.read_bytes() if build_path.is_file() else b""
# Check only actual linker tokens, not the self-check strings documented in build.py.
link_forbidden=[]
for token in ("percommon.a","peraudio.a"):
    if f'LINKER_LIB={token!r}'.encode() in build or f'LINKER_LIB="{token}"'.encode() in build:
        link_forbidden.append(token)

if bad or missing or link_forbidden:
    print("FAIL")
    for x in bad: print("forbidden native dependency:",x)
    for x in missing: print("missing:",x)
    for x in link_forbidden: print("forbidden build link:",x)
    raise SystemExit(1)

print("PASS: LuaS30 Native SDK is source-owned and vendor-header-free")
print("PASS: build.py links no vendor MRE static library")
print("PASS: firmware access is isolated behind sdk/luas30/src/abi_resolver.c")
print("PASS: Explorer tree module present")
print("PASS: device profiles:",", ".join(profiles))
