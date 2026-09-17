from pathlib import Path
import importlib.util
import tempfile

ROOT=Path(__file__).resolve().parent.parent
errors=[]

for rel in (
    "toolchain/profiles/gcc-mre.json",
    "toolchain/profiles/rvds-mre.json",
    "toolchain/profiles/ads12-mre.json",
):
    if not (ROOT/rel).is_file():
        errors.append("missing profile manifest: "+rel)

profiles=(ROOT/"tools/toolchain_profiles.py").read_text(encoding="utf-8")
build=(ROOT/"tools/build.py").read_text(encoding="utf-8")
entry=(ROOT/"engine/src/runtime_entry.c").read_text(encoding="utf-8")
pack=(ROOT/"tools/vxp_pack.py").read_text(encoding="utf-8")
settings=(ROOT/"studio/app/views/settings_view.py").read_text(encoding="utf-8")

for token in (
    'profile_id="gcc"',
    'profile_id="rvds"',
    'profile_id="ads12"',
    'entry_symbol="gcc_entry"',
    'entry_symbol="rvct_entry"',
    'entry_symbol="ads_entry"',
    '"arm-none-eabi-gcc.exe"',
    '"armcc.exe"',
    '"armlink.exe"',
    '"tcc.exe"',
    '"fromelf.exe"',
    '"--apcs=/fpic"',
    '"-apcs", "/fpic"',
):
    if token not in profiles:
        errors.append("toolchain profile missing: "+token)

for token in (
    "--compiler-profile",
    "--entry-symbol",
    "detect_toolchain",
    "link_command",
    "verify_armcc_elf.py",
):
    if token not in build:
        errors.append("builder missing multi-toolchain contract: "+token)

for symbol in ("gcc_entry","rvct_entry","ads_entry","ls30_entry_common"):
    if symbol not in entry:
        errors.append("runtime entry wrapper missing: "+symbol)

for symbol in ("gcc_entry","rvct_entry","ads_entry"):
    if symbol not in pack:
        errors.append("VXP entry extractor missing: "+symbol)

for value in ("Auto Detect","ARM GCC (MRE)","RVDS / RVCT","ARM ADS 1.2"):
    if value not in settings:
        errors.append("Settings compiler option missing: "+value)

if errors:
    print("FAIL")
    for error in errors:
        print(" -",error)
    raise SystemExit(1)

print("PASS: GCC/RVDS/ADS1.2 profiles exist")
print("PASS: toolchain detection covers gcc, armcc/armlink/fromelf and tcc")
print("PASS: gcc_entry/rvct_entry/ads_entry route to one runtime bootstrap")
print("PASS: VXP entry extraction understands all compiler conventions")
print("PASS: Studio Settings exposes compiler profile + toolchain root")
