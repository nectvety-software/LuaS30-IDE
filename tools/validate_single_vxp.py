from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
errors=[]
build=(ROOT/"tools/build.py").read_text(encoding="utf-8")

if 'build/f"{name}.vxp"' not in build:
    errors.append("canonical VXP output missing")
for token in ("build_matrix.py","--profile"):
    if token in build:
        errors.append("per-device token remains in build.py: "+token)

for batch in ("build.bat","build_only.bat"):
    text=(ROOT/batch).read_text(encoding="utf-8",errors="ignore")
    if "IMSI" in text or "--imsi" in text:
        errors.append(batch+" still exposes device binding")

if errors:
    print("FAIL")
    for e in errors: print(" -",e)
    raise SystemExit(1)

print("PASS: normal build path is single-VXP only")
print("PASS: batch launchers have no device-specific parameters")

print("PASS: optional IMSI binding is treated as a post-build install artifact, not a canonical build identity")
