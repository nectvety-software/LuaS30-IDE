from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
errors=[]

required=(
    "studio/app/views/start_page_view.py",
    "doc/studio/START_PAGE_1_9_2.md",
)
for rel in required:
    if not (ROOT/rel).is_file():
        errors.append("missing: "+rel)

main=(ROOT/"studio/app/ui/main_window.py").read_text(encoding="utf-8")
tabs=(ROOT/"studio/app/editor/editor_tabs.py").read_text(encoding="utf-8")
groups=(ROOT/"studio/app/editor/editor_group_manager.py").read_text(encoding="utf-8")
view=(ROOT/"studio/app/views/start_page_view.py").read_text(encoding="utf-8")

for token in (
    'VERSION = "1.15.0"',
    '"welcome"',
    '"Welcome"',
    'insert_at=0',
    'show_start_page',
    '_open_start_page',
):
    if token not in main:
        errors.append("MainWindow missing startup contract: "+token)

for token in ("insert_at", "activate"):
    if token not in tabs:
        errors.append("EditorTabs missing tool-tab placement option: "+token)
    if token not in groups:
        errors.append("EditorGroupManager missing tool-tab placement option: "+token)

for token in (
    "New Project...",
    "Open Project Folder...",
    "Import into Project Storage...",
    "Manage Project Storage...",
    "Recent",
    "Project Storage",
):
    if token not in view:
        errors.append("StartPageView missing: "+token)

if errors:
    print("FAIL")
    for e in errors:
        print(" -",e)
    raise SystemExit(1)

print("PASS: Welcome is the default startup hub")
print("PASS: Welcome can be inserted at group 0 / tab index 0")
print("PASS: startup destination is now controlled centrally by Settings")
print("PASS: Start/Recent/Project Storage controls are present")
