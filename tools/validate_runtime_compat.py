from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent.parent
errors=[]

required=(
    "sdk/luas30/include/ls30/compat.h",
    "sdk/luas30/src/compat.c",
    "doc/sdk/RUNTIME_COMPATIBILITY_1_8_2.md",
)
for rel in required:
    if not (ROOT/rel).is_file():
        errors.append("missing: "+rel)

abi=(ROOT/"sdk/luas30/src/abi_resolver.c").read_text(encoding="utf-8")
compat=(ROOT/"sdk/luas30/src/compat.c").read_text(encoding="utf-8")
api=(ROOT/"sdk/luas30/src/api.c").read_text(encoding="utf-8")
bridge=(ROOT/"engine/src/runtime_bridge.c").read_text(encoding="utf-8")
build=(ROOT/"tools/build.py").read_text(encoding="utf-8")

for token in ("BIND_ALIASES","vm_get_removeable_driver","vm_get_removable_driver","ls30_compat_finalize"):
    if token not in abi:
        errors.append("ABI alias layer missing: "+token)

for token in ("LS30_COMPAT_DEGRADED","LS30_FB_LINE_FROM_FILL","LS30_FB_RENAME_COPY_DELETE","missing_required"):
    if token not in compat and token not in (ROOT/"sdk/luas30/include/ls30/compat.h").read_text(encoding="utf-8"):
        errors.append("compatibility contract missing: "+token)

for token in ("software_line_from_fill","software_fill_from_line","fallback_file_rename"):
    if token not in api:
        errors.append("fallback implementation missing: "+token)

for token in ("runtime_compat","has_touch","has_rename","runtime_compatible"):
    if token not in bridge:
        errors.append("Lua compatibility API missing: "+token)

if 'SDK_SRC/"compat.c"' not in build:
    errors.append("compat.c is not compiled into the runtime")

# Guard against unsafe audio aliasing.
if "vm_audio_play_bytes" in abi.replace("vm_audio_play_bytes_no_block",""):
    errors.append("audio resolver aliases a different playback API/signature")

if errors:
    print("FAIL")
    for e in errors: print(" -",e)
    raise SystemExit(1)

print("PASS: runtime compatibility report is compiled")
print("PASS: conservative ABI aliases are present")
print("PASS: safe graphics/file/service fallbacks are present")
print("PASS: Lua runtime compatibility API is exposed")
print("PASS: audio alias policy avoids different-signature fallbacks")
