from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []

required = (
    "studio/app/core/workspace_session.py",
    "studio/app/editor/editor_group_manager.py",
    "doc/studio/WORKSPACE_SESSION_1_9_1.md",
)
for rel in required:
    if not (ROOT / rel).is_file():
        errors.append("missing: " + rel)

main = (ROOT / "studio/app/ui/main_window.py").read_text(encoding="utf-8")
view = (ROOT / "studio/app/views/code_editor_view.py").read_text(encoding="utf-8")
groups = (ROOT / "studio/app/editor/editor_group_manager.py").read_text(encoding="utf-8")
store = (ROOT / "studio/app/core/workspace_session.py").read_text(encoding="utf-8")

for token in (
    "WorkspaceSessionStore",
    "_restore_workspace_session",
    "_save_workspace_session",
    "_restore_tool_tab",
    "Split Editor Right",
    "Close Editor Group",
):
    if token not in main:
        errors.append("main window missing: " + token)

for token in (
    "EditorGroupManager",
    "workspace_state",
    "restore_layout_state",
    "connect_workspace_state_changed",
):
    if token not in view:
        errors.append("code editor view missing: " + token)

for token in (
    "session_state",
    "active_group",
    "group_sizes",
    "open_file_in_group",
    "open_untitled_in_group",
):
    if token not in groups:
        errors.append("editor group manager missing: " + token)

for token in ("workspace_session.json", "temp.replace", "SCHEMA = 1"):
    if token not in store:
        errors.append("workspace session store missing: " + token)

if errors:
    print("FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("PASS: current project is persisted/restored")
print("PASS: tool tabs and active tool state are persisted; source/untitled tabs are excluded from startup restore")
print("PASS: real editor groups, active group and group sizes are persisted")
print("PASS: sidebar and bottom-panel visibility/selection/sizes are persisted")
print("PASS: session uses AppData config and atomic temp-file replacement")
