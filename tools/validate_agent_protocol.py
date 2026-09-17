from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
skill = ROOT / "doc" / "ai" / "SKILL.md"
prompt = ROOT / "doc" / "ai" / "PROMPT.md"
entry = ROOT / "doc" / "ai" / "README.md"

errors = []
for path in (skill, prompt, entry):
    if not path.is_file():
        errors.append(f"missing: {path.relative_to(ROOT)}")

if skill.is_file():
    text = skill.read_text(encoding="utf-8")
    for required in (
        "Mandatory AI Agent preflight",
        "doc/ai/SKILL.md",
        "doc/ai/PROMPT.md",
        "GENERIC_VXP",
        "KNOWN_DEVICE_PROFILE",
        "NEW_DEVICE_PORT",
        "Target dependency policy",
        "Dedicated MRE engine per S30+ target",
    ):
        if required not in text:
            errors.append(f"SKILL.md missing contract: {required}")

if prompt.is_file():
    text = prompt.read_text(encoding="utf-8")
    for required in (
        "Mandatory first action for every AI agent",
        "doc/ai/SKILL.md",
        "doc/ai/PROMPT.md",
        "Runtime independence goal",
        "S30+ specialized MRE engine strategy",
        "templates/device_probe",
    ):
        if required not in text:
            errors.append(f"PROMPT.md missing contract: {required}")

if errors:
    print("FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("PASS: AI agents are instructed to read SKILL.md then PROMPT.md before project creation")
print("PASS: project target mode/profile selection is mandatory")
print("PASS: engine-only target dependency policy is documented")
print("PASS: per-device S30+/MRE specialization strategy is documented")
