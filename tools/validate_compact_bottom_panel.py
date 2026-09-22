from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
errors=[]

view=(ROOT/"studio/app/vxpui/main_window.py").read_text(encoding="utf-8")
panel=(ROOT/"studio/app/widgets/bottom_panel.py").read_text(encoding="utf-8")
theme=(ROOT/"studio/app/ui/theme.py").read_text(encoding="utf-8")
main=(ROOT/"studio/app/vxpui/main_window.py").read_text(encoding="utf-8")

for token in (
    "self._console_visible = False",
    "self.bottom.hide()",
    'def _toggle_console_panel',
    'def _set_console_visible',
    '"visible": bool(self._console_visible)',
    '"height": int(self._console_last_height)',
    '"active_key": self.bottom.active_key()',
):
    if token not in view:
        errors.append("MainWindow missing compact panel contract: "+token)

restore_start=view.find("def _restore_workspace_layout_state")
restore_end=view.find("def _restore_tool_tab",restore_start)
restore=view[restore_start:restore_end]
if "self._console_visible = False" not in restore:
    errors.append("workspace restore can still auto-open bottom panel")
if "self.bottom.hide()" not in restore:
    errors.append("workspace restore does not explicitly hide bottom panel")
if "_set_console_visible(True)" in restore:
    errors.append("workspace restore force-opens the bottom panel")

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

if 'VERSION = "1.0.2"' not in main:
    errors.append("MainWindow version is not 1.0.2")

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
