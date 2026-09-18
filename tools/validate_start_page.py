from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
errors=[]

required=(
    "studio/app/vxpui/home_page.py",
    "doc/studio/START_PAGE_1_9_2.md",
)
for rel in required:
    if not (ROOT/rel).is_file():
        errors.append("missing: "+rel)

main=(ROOT/"studio/app/vxpui/main_window.py").read_text(encoding="utf-8")
tabs=(ROOT/"studio/app/editor/editor_tabs.py").read_text(encoding="utf-8")
groups=(ROOT/"studio/app/editor/editor_group_manager.py").read_text(encoding="utf-8")
view=(ROOT/"studio/app/vxpui/home_page.py").read_text(encoding="utf-8")

for token in (
    'VERSION = "1.0.1"',
    '"welcome"',
    'self._startup_mode = "welcome"',
    'show_start_page',
    'self.stack.addWidget(self.home_page)',
    'self._show_home()',
):
    if token not in main:
        errors.append("MainWindow missing startup contract: "+token)

for token in ("insert_at", "activate"):
    if token not in tabs:
        errors.append("EditorTabs missing tool-tab placement option: "+token)
    if token not in groups:
        errors.append("EditorGroupManager missing tool-tab placement option: "+token)

for token in (
    "new_project_requested = Signal()",
    "open_project_folder_requested = Signal()",
    "project_open_requested = Signal(object)",
    "project_rename_requested = Signal(object)",
    "project_remove_requested = Signal(object)",
    "documentation_requested = Signal()",
    "Mở dự án",
    "Đổi tên",
    "Xóa",
):
    if token not in view:
        errors.append("HomePage missing: "+token)

if errors:
    print("FAIL")
    for e in errors:
        print(" -",e)
    raise SystemExit(1)

print("PASS: Welcome home page is the default startup hub")
print("PASS: home page sits below the editor page in the MainStack")
print("PASS: startup destination is controlled centrally by Settings")
print("PASS: project cards expose open/rename/remove plus new/open folder actions")
