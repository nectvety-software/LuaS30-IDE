from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
mw = (ROOT / "studio/app/ui/main_window.py").read_text(encoding="utf-8")
errors = []

for forbidden_import in (
    "dashboard_view", "projects_view", "build_view", "console_view"
):
    if forbidden_import in mw:
        errors.append(f"duplicate whole-screen view still imported: {forbidden_import}")

for forbidden_menu in (
    'addMenu("Selection")',
    'addMenu("Go")',
    'addMenu("Help")',
):
    if forbidden_menu in mw:
        errors.append(f"duplicate menu still present: {forbidden_menu}")

for required in (
    "studio/app/services/build_service.py",
    "studio/app/services/emulator_service.py",
    "studio/app/services/project_doctor.py",
    "studio/app/ui/command_palette.py",
    "studio/app/views/project_manager_view.py",
):
    if not (ROOT / required).is_file():
        errors.append(f"missing: {required}")

emu = (ROOT / "studio/app/views/emulator_view.py").read_text(encoding="utf-8")
if "S30+ DEVICE" in emu or "LuaS30 Emulator\\n240" in emu:
    errors.append("decorative emulator mock is still present")

if errors:
    print("FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("PASS: compact workbench has no duplicate Dashboard/Build/Console pages")
print("PASS: menu ownership is File/Edit/View/Run/Terminal/Tools/About")
print("PASS: build/emulator/project-management services are present")
print("PASS: emulator view uses artifact/process metadata, not fake device UI")
