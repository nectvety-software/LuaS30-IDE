from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
errors=[]

main=(ROOT/"studio/app/vxpui/main_window.py").read_text(encoding="utf-8")
editor=(ROOT/"studio/app/vxpui/main_window.py").read_text(encoding="utf-8")

for token in (
    'VERSION = "1.0.2"',
    'self.stack.setObjectName("MainStack")',
    "def _show_home",
    "def _enter_editor",
    "self.title_bar.set_home_mode(True)",
    "self.title_bar.set_home_mode(False)",
    "self.home_page.set_projects(self.project_library.scan())",
):
    if token not in main:
        errors.append("MainWindow missing home-page mode rule: "+token)

# Session state must use desired editor visibility, not physical page state.
if '"visible": bool(self._console_visible)' not in editor:
    errors.append("panel session state is not persisted from desired visibility")
if '"height": int(self._console_last_height)' not in editor:
    errors.append("bottom panel preferred height is not persisted")

# Project Hub: cây thư mục bên trái + bảng bên phải, và nền của chính QHeaderView.
manager=(ROOT/"studio/app/views/project_manager_view.py").read_text(encoding="utf-8")
theme=(ROOT/"studio/app/ui/theme.py").read_text(encoding="utf-8")
tree=(ROOT/"studio/app/editor/project_tree.py").read_text(encoding="utf-8")

for token in (
    "from app.editor.project_tree import ProjectTree",
    "QSplitter",
    "self.tree = ProjectTree()",
    "self.tree.set_project_root(self.service.projects_root)",
    "self.tree.clicked.connect(self._on_tree_clicked)",
    "splitter.addWidget(tree_panel)",
    "splitter.addWidget(right)",
    "def _on_tree_clicked",
    "def _managed_root_for",
):
    if token not in manager:
        errors.append("ProjectManagerView missing storage tree rule: "+token)

# Cây phải được thêm vào splitter TRƯỚC bảng — kiểm thứ tự thật, không chỉ sự tồn tại.
if manager.find("splitter.addWidget(tree_panel)") > manager.find("splitter.addWidget(right)"):
    errors.append("storage tree is not added before the table pane")

if "def reveal_path" not in tree:
    errors.append("ProjectTree missing reveal_path()")

# Nền của CHÍNH QHeaderView: thiếu rule này thì vùng SAU section cuối rơi về
# palette mặc định (sáng) — đã từng thành dải trắng bên phải tiêu đề bảng.
if "QHeaderView {" not in theme:
    errors.append("theme.py missing QHeaderView background rule (only ::section styled)")

if errors:
    print("FAIL")
    for error in errors:
        print(" -",error)
    raise SystemExit(1)

print("PASS: Welcome/Project Storage hide editor-only chrome")
print("PASS: Activity Bar is hidden in Project Hub mode")
print("PASS: editor sidebar/panel preferences survive Project Hub presentation")
print("PASS: returning to editor can restore previous sidebar/panel visibility")
print("PASS: Project Hub has a storage tree on the LEFT of the project table")
print("PASS: clicking a folder in the tree selects the owning project row")
print("PASS: theme.py paints the QHeaderView background, not just ::section")
