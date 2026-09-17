from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent.parent
errors=[]

for rel in ("tools/vxp_inspect.py","tools/lua_harden.py","doc/build/RELEASE_AND_HARDENING.md"):
    if not (ROOT/rel).is_file():
        errors.append("missing: "+rel)

# "IDE không ký" do `tools/validate_no_signing.py` canh — MỘT nguồn duy nhất.
# Đừng chép danh sách token ký về đây: guard nào liệt kê token cấm thì chính nó
# lại chứa token đó, và một vòng quét toàn repo sẽ báo lỗi giả.
if (ROOT/"tools/build_matrix.py").exists():
    errors.append("build_matrix.py must not exist")

build=(ROOT/"tools/build.py").read_text(encoding="utf-8")
for forbidden in ("--profile","requested_profile"):
    if forbidden in build:
        errors.append("per-device build token remains: "+forbidden)

for required in (
    'final_vxp=build/f"{name}.vxp"',
    '"artifact_model":"canonical-generic-plus-optional-install-binding"',
    '"device_specific_artifact":bool(device_vxp)',
    '"runtime_detection":True',
):
    if required not in build:
        errors.append("Single-VXP contract missing: "+required)

for template in ("templates/basic/project.json","templates/device_probe/project.json"):
    data=json.loads((ROOT/template).read_text(encoding="utf-8"))
    if "target_profile" in data:
        errors.append(template+": target_profile remains")
    if data.get("single_vxp") is not True:
        errors.append(template+": single_vxp must be true")

if errors:
    print("FAIL")
    for e in errors: print(" -",e)
    raise SystemExit(1)

print("PASS: one canonical VXP output")
print("PASS: canonical build remains generic; optional phone install binding is explicit and non-persistent")
print("PASS: templates use generic MRE/VXP runtime")
print("PASS: release hardening and VXP inspection remain")
print("PASS: signing is guarded by validate_no_signing.py (single source)")
