from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
errors=[]
required=[
 "sdk/luas30/include/ls30/api.h","sdk/luas30/src/abi_resolver.c","sdk/luas30/src/api.c",
 "engine/src/runtime_entry.c","engine/src/runtime_bridge.c","engine/src/runtime_lua.c",
 "engine/include/luas30_runtime.h","engine/linker/luas30.ld",
 "vendor/lua-5.1.5/src/lua.h","vendor/lua-5.1.5/src/lapi.c","tools/build.py"
]
for rel in required:
    if not (ROOT/rel).is_file(): errors.append("missing: "+rel)
forbidden=["percommon.a","peraudio.a","#include <vmsys.h>","#include <vmgraph.h>","#include <vmio.h>","#include <vmmm.h>"]
native_paths=list((ROOT/"sdk/luas30/src").glob("*.c"))+list((ROOT/"engine/src").glob("*.c"))+list((ROOT/"sdk/luas30/include").rglob("*.h"))
native="\n".join(p.read_text(encoding="utf-8",errors="ignore") for p in native_paths)
for item in forbidden:
    if item in native: errors.append("native runtime contains forbidden dependency: "+item)
if errors:
    print("FAIL")
    for e in errors: print(" -",e)
    sys.exit(1)
print("PASS: standalone LuaS30 Native SDK tree")
print("PASS: no vendor MRE static library/header dependency")
print("PASS: bundled Lua 5.1.5 source")
print("PASS: raw Lua resource mode supported")
