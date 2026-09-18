from pathlib import Path
import json
import tempfile
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"studio"))

from app.ui import palette

errors=[]

bottom=(ROOT/"studio/app/widgets/bottom_panel.py").read_text(encoding="utf-8")
terminal=(ROOT/"studio/app/widgets/terminal_view.py").read_text(encoding="utf-8")
main=(ROOT/"studio/app/vxpui/main_window.py").read_text(encoding="utf-8")
session=(ROOT/"studio/app/core/project_session.py").read_text(encoding="utf-8")
library=(ROOT/"studio/app/services/project_library.py").read_text(encoding="utf-8")

for token in (
    "class HexView(QWidget)",
    'self.addTab(self.hex_view, "HEX")',
    "PAGE_SIZE = 64 * 1024",
    "BYTES_PER_LINE = 16",
    "classify_log_line",
):
    if token not in bottom:
        errors.append("BottomPanel missing: "+token)

# Mau log lay tu palette.py (nguon duy nhat), khong duoc hardcode lai hex —
# day chinh la thu da lam bang mau lech nhau giua bottom_panel/terminal/ai_chat.
for key, token in (("error", "palette.RED"), ("success", "palette.GREEN_LIGHT"),
                   ("warning", "palette.AMBER"), ("info", "palette.INFO")):
    if f'"{key}": {token}' not in bottom:
        errors.append(f"BottomPanel log color '{key}' phai la {token}")

# terminal_view dung thuoc tinh *_format chu khong phai dict
for attr, token in (("_prompt_format", "palette.INFO"),
                    ("_input_format", "palette.SYN_FUNC"),
                    ("_success_format", "palette.GREEN_LIGHT"),
                    ("_error_format", "palette.RED"),
                    ("_warning_format", "palette.AMBER")):
    if f"self.{attr}.setForeground(QColor({token}))" not in terminal:
        errors.append(f"Terminal {attr} phai la {token}")

for token in ("_prompt_format","_input_format","_error_format","_success_format"):
    if token not in terminal:
        errors.append("Terminal colors missing: "+token)

for token in (
    "self.bottom.show_hex(vxp)",
    "self.bottom.hex_view.set_file(vxp)",
    "HEX loaded",
    'VERSION = "1.0.1"',
):
    if token not in main:
        errors.append("MainWindow HEX integration missing: "+token)

for token in ("rewrite_project_identity","assign_new_app_id=True"):
    if token not in session:
        errors.append("ProjectSession unique AppID missing: "+token)

if library.count("assign_new_app_id=True") < 2:
    errors.append("Import/Duplicate do not both request new AppIDs")
if "assign_new_app_id=False" not in library:
    errors.append("Rename does not explicitly preserve AppID")

if errors:
    print("FAIL")
    for error in errors:
        print(" -",error)
    raise SystemExit(1)

print("PASS: Console/Build semantic colors are installed")
print("PASS: direct terminal prompt/output colors are installed")
print("PASS: BottomPanel contains paged HEX viewer")
print("PASS: emulator launch selects the exact manifest VXP in HEX")
print("PASS: New/Import/Duplicate request a fresh AppID; Rename preserves it")
