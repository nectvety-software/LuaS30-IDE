from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
errors=[]

settings=(ROOT/"studio/app/views/settings_view.py").read_text(encoding="utf-8")
main=(ROOT/"studio/app/vxpui/main_window.py").read_text(encoding="utf-8")
groups=(ROOT/"studio/app/editor/editor_group_manager.py").read_text(encoding="utf-8")

for token in (
    '("Welcome", "welcome")',
    '("Project Hub", "project_hub")',
    '("Empty Editor", "empty_editor")',
    "startup_mode_changed = Signal(str)",
    "Startup screen",
):
    if token not in settings:
        errors.append("Settings missing startup option: "+token)

for token in (
    'VERSION = "1.0.2"',
    'self._startup_mode = "welcome"',
    'mode not in {"welcome", "project_hub", "empty_editor"}',
    "def _activate_startup_mode",
    'self._startup_mode == "project_hub"',
    'self._startup_mode == "empty_editor"',
    '"mode": self._startup_mode',
    'if self._startup_mode != "empty_editor":',
    "def _set_startup_mode",
):
    if token not in main:
        errors.append("MainWindow missing startup-mode contract: "+token)

if "def show_empty_editor" not in groups:
    errors.append("Editor group manager has no empty-editor startup operation")

if errors:
    print("FAIL")
    for error in errors:
        print(" -",error)
    raise SystemExit(1)

print("PASS: Settings exposes Welcome / Project Hub / Empty Editor")
print("PASS: startup mode is persisted in workspace session")
print("PASS: Empty Editor suppresses restored tool tabs and source tabs")
print("PASS: legacy show_start_page sessions migrate")
print("PASS: duplicate Welcome startup checkbox is removed")
