from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
main = (ROOT / "studio/app/ui/main_window.py").read_text(encoding="utf-8")
errors = []

for token in (
    'VERSION = "1.0.1"',
    'if kind in {"file", "untitled"}',
    "Skipped {skipped_source_tabs} source/untitled tab(s) on startup.",
    "def _startup_safe_editor_state",
    'entry.get("type") == "tool"',
    '"restore_source_tabs": False',
    "Deliberately no main.lua fallback here",
):
    if token not in main:
        errors.append("missing startup-clean-tabs contract: " + token)

# Explicitly reject the old auto-open-main fallback inside restore.
restore_start = main.find("def _restore_workspace_session")
restore_end = main.find("def _restore_tool_tab", restore_start)
restore = main[restore_start:restore_end]
if "self.editor_view.open_file(main_lua)" in restore:
    errors.append("restore still automatically opens main.lua")

if errors:
    print("FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("PASS: restart skips persisted source file tabs")
print("PASS: restart skips untitled editor tabs")
print("PASS: source tabs are filtered from the saved startup session")
print("PASS: no automatic main.lua fallback remains")
print("PASS: project/layout/tool state can still be restored")
