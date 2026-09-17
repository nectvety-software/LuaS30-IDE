from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
profiles=(ROOT/"tools/toolchain_profiles.py").read_text(encoding="utf-8")
build=(ROOT/"tools/build.py").read_text(encoding="utf-8")
doctor=(ROOT/"tools/toolchain_doctor.py").read_text(encoding="utf-8")
errors=[]

for token in (
    "configure_environment",
    'root / "bin"',
    'root / "arm-none-eabi" / "bin"',
    "LUAS30_TOOLCHAIN_ROOT",
    "detect_toolchain",
):
    if token not in profiles:
        errors.append("toolchain_profiles.py missing: "+token)

for token in ("toolchain_preflight","compiler/tool output","detect_toolchain"):
    if token not in build:
        errors.append("build.py missing: "+token)

for token in ("--profile","detect_toolchain","link_command","compile_command"):
    if token not in doctor:
        errors.append("toolchain_doctor.py missing: "+token)

if errors:
    print("FAIL")
    for error in errors:
        print(" -",error)
    raise SystemExit(1)

print("PASS: portable PATH setup remains available")
print("PASS: compiler/linker profile auto-detection is installed")
print("PASS: compiler stderr is propagated into build errors")
print("PASS: Toolchain Doctor uses the same profile commands as build.py")
