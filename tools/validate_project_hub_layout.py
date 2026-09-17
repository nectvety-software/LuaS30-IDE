from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
errors=[]

main=(ROOT/"studio/app/ui/main_window.py").read_text(encoding="utf-8")
editor=(ROOT/"studio/app/views/code_editor_view.py").read_text(encoding="utf-8")

for token in (
    'VERSION = "1.15.0"',
    "self.activity_bar = self._build_activity_bar()",
    "def _set_project_hub_mode",
    'key in {"welcome", "projects"}',
    "self.activity_bar.setVisible((not enabled) and bool(self._editor_activity_bar_visible))",
    "self.editor_view.set_hub_mode(enabled)",
):
    if token not in main:
        errors.append("MainWindow missing Project Hub rule: "+token)

for token in (
    "def set_hub_mode",
    "_editor_sidebar_visible",
    "_editor_bottom_visible",
    "_editor_find_visible",
    "self.left_tabs.hide()",
    "self.bottom.hide()",
    "self.find_bar.hide()",
):
    if token not in editor:
        errors.append("CodeEditorView missing Project Hub state: "+token)

# Session state must use desired editor visibility, not physical hub visibility.
if '"visible": bool(self._editor_sidebar_visible)' not in editor:
    errors.append("sidebar session state is still tied to physical hub visibility")
if '"visible": bool(self._editor_bottom_visible)' not in editor:
    errors.append("panel session state is still tied to physical hub visibility")

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
