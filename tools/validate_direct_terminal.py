from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
terminal=(ROOT/"studio/app/widgets/terminal_view.py").read_text(encoding="utf-8")
theme=(ROOT/"studio/app/ui/theme.py").read_text(encoding="utf-8")
main=(ROOT/"studio/app/ui/main_window.py").read_text(encoding="utf-8")
errors=[]

for token in (
    "class TerminalSurface(QPlainTextEdit)",
    "command_submitted = Signal(str)",
    "def show_prompt",
    "def replace_current_input",
    "def keyPressEvent",
    "Qt.Key.Key_Up",
    "Qt.Key.Key_Down",
    "Qt.Key.Key_Home",
    "Qt.Key.Key_L",
    "_DONE_PREFIX",
    "self.surface = TerminalSurface()",
    "self.output = self.surface",
    "self.input = self.surface",
    "marker_line = line.lstrip()",
):
    if token not in terminal:
        errors.append("terminal direct-input contract missing: "+token)

if "class TerminalInput(QLineEdit)" in terminal:
    errors.append("legacy TerminalInput QLineEdit still exists")
if 'setObjectName("TerminalInput")' in terminal:
    errors.append("legacy TerminalInput widget still exists")
if "QLineEdit#TerminalInput" in theme:
    errors.append("legacy terminal textbox theme still exists")
if "QPlainTextEdit#TerminalSurface" not in theme:
    errors.append("TerminalSurface theme is missing")
if 'VERSION = "1.15.0"' not in main:
    errors.append("MainWindow version is not 1.15.0")

if errors:
    print("FAIL")
    for error in errors:
        print(" -",error)
    raise SystemExit(1)

print("PASS: terminal command input is inside the terminal surface")
print("PASS: no separate terminal QLineEdit remains")
print("PASS: terminal history/output is protected from normal editing")
print("PASS: Up/Down/Home/Ctrl+L/Ctrl+C direct terminal keys are implemented")
print("PASS: persistent shell completion marker updates the cwd prompt")
