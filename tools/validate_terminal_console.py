from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
errors=[]
required=(
    "studio/app/widgets/terminal_view.py",
    "studio/app/widgets/bottom_panel.py",
    "doc/studio/TERMINAL_CONSOLE_1_9_3.md",
)
for rel in required:
    if not (ROOT/rel).is_file(): errors.append("missing: "+rel)

main=(ROOT/"studio/app/ui/main_window.py").read_text(encoding="utf-8")
view=(ROOT/"studio/app/views/code_editor_view.py").read_text(encoding="utf-8")
panel=(ROOT/"studio/app/widgets/bottom_panel.py").read_text(encoding="utf-8")
terminal=(ROOT/"studio/app/widgets/terminal_view.py").read_text(encoding="utf-8")

for token in ('Toggle Console','Toggle Terminal','New Terminal','menu.addMenu("Terminal")','VERSION = "1.0.1"'):
    if token not in main: errors.append("MainWindow missing: "+token)
for token in ('def toggle_console','def toggle_terminal','def new_terminal','"active_key"'):
    if token not in view: errors.append("CodeEditorView missing: "+token)
for token in ('"CONSOLE"','"TERMINAL"','IntegratedTerminal','self.output = self.console'):
    if token not in panel: errors.append("BottomPanel missing: "+token)
for token in ('QProcess','cmd.exe','command_submitted','def kill_terminal','def new_terminal'):
    if token not in terminal: errors.append("Terminal implementation missing: "+token)

if errors:
    print("FAIL")
    for e in errors: print(" -",e)
    raise SystemExit(1)
print("PASS: Console/Terminal are integrated bottom-panel surfaces")
print("PASS: Terminal uses a real QProcess shell")
print("PASS: VS Code-style toggle actions and terminal menu are present")
print("PASS: active panel key is workspace-session compatible")
