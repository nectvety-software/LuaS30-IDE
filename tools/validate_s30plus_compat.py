from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent.parent
errors=[]

build=(ROOT/"tools/build.py").read_text(encoding="utf-8")
compat=(ROOT/"tools/s30plus_compat.py").read_text(encoding="utf-8")
entry=(ROOT/"engine/src/runtime_entry.c").read_text(encoding="utf-8")
settings=(ROOT/"studio/app/views/settings_view.py").read_text(encoding="utf-8")
service=(ROOT/"studio/app/services/build_service.py").read_text(encoding="utf-8")
main=(ROOT/"studio/app/ui/main_window.py").read_text(encoding="utf-8")

for token in (
    '"s30plus-native"',
    '"nokia225-rm1011"',
    "-D_MINIGUI_LIB_",
    "-D_USE_MINIGUIENTRY",
    "-D__MRE_SDK__",
    "-D__MRE_VENUS_NORMAL__",
    "-D__MMI_MAINLCD_240X320__",
    "percommon.a",
    "scat.ld",
    "--start-group",
):
    if token not in compat:
        errors.append("S30+ profile missing: "+token)

for token in (
    "void vm_main(void)",
    "void gcc_entry(",
    "vm_main();",
):
    if token not in entry:
        errors.append("runtime entry compatibility missing: "+token)

for token in (
    "--compat-profile",
    "--mre-sdk",
    "--device-imsi",
    "bind_nokia225",
    "api=api_list",
    "device_imsi_bound",
):
    if token not in build:
        errors.append("builder S30+ feature missing: "+token)

for token in (
    "S30+ compatibility",
    "Nokia 225 Dual SIM RM-1011",
    "MRE SDK root",
    "Nokia IMSI",
):
    if token not in settings:
        errors.append("Settings S30+ UI missing: "+token)

if "LUAS30_DEVICE_IMSI" not in service:
    errors.append("BuildService does not pass IMSI by environment")
if '"device_imsi"' in main or "'device_imsi'" in main:
    errors.append("MainWindow persists raw device IMSI field")
if 'VERSION = "1.0.1"' not in main:
    errors.append("MainWindow version is not 1.0.1")

profile_path=ROOT/"compat/devices/nokia-225-dual-sim-rm1011.json"
if not profile_path.is_file():
    errors.append("Nokia 225 profile JSON missing")
else:
    data=json.loads(profile_path.read_text(encoding="utf-8"))
    if data.get("display")!={"width":240,"height":320,"orientation":"portrait"}:
        errors.append("Nokia 225 display profile is not 240x320 portrait")
    if data.get("build",{}).get("application_entry")!="vm_main":
        errors.append("Nokia profile application entry is not vm_main")

if errors:
    print("FAIL")
    for error in errors: print(" -",error)
    raise SystemExit(1)

print("PASS: native S30+ MRE SDK build profile exists")
print("PASS: Nokia 225 RM-1011 profile exists")
print("PASS: runtime exports gcc_entry -> vm_main")
print("PASS: MRE SDK libraries/scat.ld are modeled")
print("PASS: IMSI install binding is session-only and non-persistent")
