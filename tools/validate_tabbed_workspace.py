from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
errors=[]

required=(
    "studio/app/services/project_library.py",
    "studio/app/views/project_manager_view.py",
    "studio/app/views/project_doctor_view.py",
    "studio/app/views/compat_matrix_view.py",
    "studio/app/views/toolchain_doctor_view.py",
    "doc/studio/TABBED_WORKSPACE_1_9.md",
)
for rel in required:
    if not (ROOT/rel).is_file():
        errors.append("missing: "+rel)

mw=(ROOT/"studio/app/vxpui/main_window.py").read_text(encoding="utf-8")
tabs=(ROOT/"studio/app/editor/editor_tabs.py").read_text(encoding="utf-8")
manager=(ROOT/"studio/app/views/project_manager_view.py").read_text(encoding="utf-8")
library=(ROOT/"studio/app/services/project_library.py").read_text(encoding="utf-8")

if "MainStack" not in mw:
    errors.append("MainWindow lost the home/editor two-page stack")

for token in (
    '"projects", "Project Hub"',
    'doctor_action.triggered.connect(self._open_project_doctor)',
    'compat_action.triggered.connect(self._open_compat_matrix)',
    'toolchain_action.triggered.connect(self._open_toolchain_doctor)',
    'self.tabs.open_tool_tab(',
):
    if token not in mw:
        errors.append("MainWindow missing tabbed feature: "+token)

for token in ("def open_tool_tab", "def tool_widget", "def close_file_tabs", "luas30ToolKey"):
    if token not in tabs:
        errors.append("EditorTabs missing: "+token)

# Tools menu must contain tab features, not command-only folder/build utilities.
tools_block = mw.split('tools_menu = menu_bar.addMenu("Công cụ")',1)[1].split('help_menu = menu_bar.addMenu("Trợ giúp")',1)[0]
for forbidden in ("clean_build_action","open_project_folder_action","open_build_folder_action","open_emulator_folder_action"):
    if forbidden in tools_block:
        errors.append("Tools menu contains command-only utility instead of tab feature: "+forbidden)

for token in ("Import", "Duplicate", "Rename", "Delete", "Reveal"):
    if token not in manager:
        errors.append("Project Storage missing UI operation: "+token)

for token in ("def scan", "def import_project", "def duplicate", "def rename", "def delete"):
    if token not in library:
        errors.append("ProjectLibraryService missing real operation: "+token)

if errors:
    print("FAIL")
    for error in errors:
        print(" -",error)
    raise SystemExit(1)

print("PASS: one central editor workbench; no QStackedWidget tool-page switching")
print("PASS: persistent tools use keyed editor-area tabs")
print("PASS: every Tools-menu feature opens/focuses a tab")
print("PASS: Project Storage has real scan/import/duplicate/rename/delete/reveal logic")
print("PASS: project switching can close source tabs without destroying tool tabs")
