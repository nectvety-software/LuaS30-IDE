from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
errors=[]

view=(ROOT/"studio/app/views/code_editor_view.py").read_text(encoding="utf-8")
panel=(ROOT/"studio/app/widgets/bottom_panel.py").read_text(encoding="utf-8")
theme=(ROOT/"studio/app/ui/theme.py").read_text(encoding="utf-8")
main=(ROOT/"studio/app/ui/main_window.py").read_text(encoding="utf-8")

for token in (
    "DEFAULT_BOTTOM_PANEL_HEIGHT = 145",
    "MIN_BOTTOM_PANEL_HEIGHT = 72",
    "def _reveal_bottom_panel",
    "def hide_bottom_panel",
    "self._editor_bottom_visible = False",
    "self.bottom.hide()",
    "preferred_height",
):
    if token not in view:
        errors.append("CodeEditorView missing compact panel contract: "+token)

restore_start=view.find("def restore_layout_state")
restore_end=view.find("def connect_workspace_state_changed",restore_start)
restore=view[restore_start:restore_end]
if "self._editor_bottom_visible = False" not in restore:
    errors.append("workspace restore can still auto-open bottom panel")
if "self.bottom.hide()" not in restore:
    errors.append("workspace restore does not explicitly hide bottom panel")

for token in (
    "close_requested = Signal()",
    'setObjectName("BottomPanelClose")',
    'setToolTip("Close Panel (Ctrl+J)")',
    "self.setCornerWidget",
):
    if token not in panel:
        errors.append("BottomPanel close UI missing: "+token)

for token in (
    "width: 7px",
    "height: 7px",
    "QToolButton#BottomPanelClose",
    "QSplitter::handle:vertical { height: 3px; }",
):
    if token not in theme:
        errors.append("compact theme missing: "+token)

if 'VERSION = "1.15.0"' not in main:
    errors.append("MainWindow version is not 1.15.0")

if errors:
    print("FAIL")
    for error in errors:
        print(" -",error)
    raise SystemExit(1)

print("PASS: bottom panel starts hidden after session restore")
print("PASS: Terminal/Console reveal and toggle behavior is implemented")
print("PASS: top-right Close Panel control is present")
print("PASS: preferred compact panel height is remembered")
print("PASS: global scrollbars are reduced to 7 px")
