"""drive_ide_as_user.py — mo phong NGUOI DUNG THAT ben trong LuaS30-IDE.

Dung VxpMainWindow THAT (chrome VXPEngine), tao du an MAU qua dung duong
session.create_project + _switch_project (copy templates/basic), go cau yeu
vao composer Chat AI that roi bam send(). Chi stub dung lop mang
(AIRequestThread) bang kich ban 8 luot tra loi MIXED (fenced JSON + XML) de
test tat dinh — moi thu con lai (parse, tool, AIChangeService, auto-apply,
_reload_applied_editors, PROBLEMS provider) chay THAT.
Neu agent khong tuong tac duoc voi du an -> chan doan tung luot va fail.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
os.environ["LUAS30_APPDATA"] = tempfile.mkdtemp(prefix="user_appdata_")
os.environ["LUAS30_PROJECTS"] = tempfile.mkdtemp(prefix="user_projects_")
os.environ["LUAS30_DOCUMENTS"] = tempfile.mkdtemp(prefix="user_docs_")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
sys.path.insert(0, str(_ROOT / "studio"))

# Chan modal SetupDialog (no 800ms sau khi dung cua so) — khien headless treo.
from app.services.environment_setup import mark_setup_done
from app.vxpui.main_window import VxpMainWindow
mark_setup_done(VxpMainWindow.VERSION)

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

import app.views.ai_chat_view as chat_module

AK = "<arg_key>"
KV = "<arg_value>"
EK = "</" + "arg_key>"
EV = "</" + "arg_value>"
CT = "</" + "tool_call>"


def xcall(opener, *pairs):
    body = "".join(AK + str(k) + EK + KV + str(v) + EV for k, v in pairs)
    return "<tool_call" + opener + ">" + body + CT


def fenced(payload):
    return "```luas30-tool\n" + payload + "\n```"


MAIN_LUA_V1 = """-- DemoApp (sinh boi ChatAI agent nhu nguoi dung yeu cau)
local ui = require("ui")

function draw()
  -- TODO: ve UI (button/label/photo/textbox/card)
end

return { draw = draw }
"""

MAIN_LUA_FIX = "  ui.draw('main')\n  ui.draw_photo()"

SCRIPT = [
    "Minh kiem tra catalog va tao anh truoc.\n" + fenced(
        '{"tool":"ui_design","args":{"op":"catalog"},"reason":"List component types"}'
    ) + "\n" + fenced(
        '{"tool":"asset","args":{"op":"make","kind":"solid","name":"photo_hero",'
        '"target":"sprites","width":56,"height":56,"color":"#35507a"},'
        '"reason":"Photo placeholder PNG"}'
    ),
    fenced('{"tool":"ui_design","args":{"op":"add_screen","id":"main"},"reason":"Main screen"}')
    + "\n" + xcall("=ui_design", ("op", "add_item"), ("screen", "main"), ("type", "button"),
                   ("name", "btn_ok"), ("x", "80"), ("y", "240"), ("w", "78"), ("h", "24"),
                   ("text", "OK"), ("reason", "Nut nhan OK")),
    xcall("", ("op", "add_item"), ("screen", "main"), ("type", "label"),
          ("name", "lbl_title"), ("x", "16"), ("y", "16"), ("w", "208"), ("h", "20"),
          ("text", "Xin chao S30"), ("reason", "Dong chu"))
    + "\n" + xcall("=ui_design", ("op", "add_item"), ("screen", "main"), ("type", "image"),
                   ("name", "img_photo"), ("x", "92"), ("y", "64"), ("w", "56"), ("h", "56"),
                   ("src", "assets/sprites/photo_hero.png"), ("reason", "Buc anh"))
    + "\n<tool_call name=\"ui_design\">" + AK + "op" + EK + KV + "add_item" + EV
    + AK + "screen" + EK + KV + "main" + EV + AK + "type" + EK + KV + "textbox" + EV
    + AK + "name" + EK + KV + "txt_name" + EV + AK + "x" + EK + KV + "16" + EV
    + AK + "y" + EK + KV + "140" + EV + AK + "w" + EK + KV + "208" + EV
    + AK + "h" + EK + KV + "24" + EV + AK + "text" + EK + KV + "Nhap ten" + EV
    + AK + "reason" + EK + KV + "Textbox" + EV + CT,
    fenced('{"tool":"ui_design","args":{"op":"add_item","screen":"main","type":"card",'
           '"name":"card_info","x":"16","y":"180","w":"208","h":"48","text":"Info card"},'
           '"reason":"The card don gian"}'),
    xcall(' name="write_file"', ("path", "main.lua"), ("content", MAIN_LUA_V1),
          ("reason", "Tao diem vao UI")),
    "```luas30-edit\n" + json.dumps({
        "path": "main.lua",
        "find": "-- TODO: ve UI (button/label/photo/textbox/card)",
        "replace": MAIN_LUA_FIX,
        "reason": "Noi UI vao ham draw()",
    }, ensure_ascii=False) + "\n```",
    fenced('{"tool":"problems","args":{"op":"list"},"reason":"Kiem tra loi con lai"}'),
    "Xong: man hinh main co nut OK, chu, anh, textbox va card; main.lua da duoc cap nhat.",
]


class FakeThread(QThread):
    completed = Signal(str)
    failed = Signal(str)
    idx = 0

    def __init__(self, cfg, api_key, system_prompt, messages, parent=None):
        super().__init__(parent)
        self.messages = list(messages or [])

    def run(self):
        if self.isInterruptionRequested():
            return
        i = FakeThread.idx
        FakeThread.idx += 1
        if i >= len(SCRIPT):
            self.failed.emit("Kich ban het luot (agent van con muon goi tool)")
            return
        self.completed.emit(SCRIPT[i])


chat_module.AIRequestThread = FakeThread
from app.views.ai_chat_view import AIChatView  # noqa: E402


import main as studio_main  # noqa: E402
app.setStyleSheet(studio_main._stylesheet())

win = VxpMainWindow(engine_root=_ROOT, version=VxpMainWindow.VERSION)
win.resize(1536, 960)
win.show()
for _ in range(15):
    app.processEvents()
    time.sleep(0.01)

USER_PROMPT = ("Tao cho minh mot ung dung don gian co: nut nhan, dong chu (text), "
               "buc anh (photo), o nhap (textbox) va mot the (card). "
               "Sau do kiem tra loi va tu sua neu co.")

print("-- Nguoi dung: mo IDE that, tao du an mau 'DemoApp' --")
info = win.session.create_project("DemoApp")
win._switch_project(info.root)
for _ in range(15):
    app.processEvents()
    time.sleep(0.01)
project = Path(info.root)
chat = win.ai_chat
print("   du an:", project)
print("   ai_chat.project_root ===", (chat.project_root == project.resolve()
                                     or chat.project_root == project))
print("   access mode mac dinh:", chat.current_access_mode())

print("-- Nguoi dung: go vao composer roi bam gui --")
chat.prompt.setPlainText(USER_PROMPT)
chat.send()

deadline = time.time() + 40
while time.time() < deadline:
    app.processEvents()
    if FakeThread.idx >= len(SCRIPT) and not chat._agent_active and chat._worker is None:
        break
    time.sleep(0.01)
for _ in range(30):
    app.processEvents()
    time.sleep(0.01)


failures: list[str] = []


def check(ok, label):
    print(("  [OK  ] " if ok else "  [FAIL] ") + label)
    if not ok:
        failures.append(label)


def diagnose():
    print("\n---- CHAN DOAN: agent khong tuong tac duoc voi du an? ----")
    print(f"luot model da phat: {FakeThread.idx}/{len(SCRIPT)}")
    print(f"du an: {project}  |  ton tai: {project.is_dir()}")
    for i, item in enumerate(chat._history):
        role = str(item.get("role") or "")
        content = str(item.get("content") or "")
        if role == "user" and item.get("_internal"):
            print(f"[ket qua tool] {content[:180]}")
        elif role == "assistant":
            print(f"[luot {i}] {content[:140].strip()}")
    print("-----------------------------------------------------------")


print("\n-- Ket qua mo phong nguoi dung trong IDE that --")
check(FakeThread.idx == len(SCRIPT), f"du 8 luot model chay het ({FakeThread.idx})")

design_path = project / ".luas30" / "ui_design.json"
check(design_path.is_file(), ".luas30/ui_design.json duoc tao trong du an")
types = set()
if design_path.is_file():
    design = json.loads(design_path.read_text(encoding="utf-8"))
    blob = json.dumps(design, ensure_ascii=False)
    for screen in design.get("screens") or []:
        for item in screen.get("items") or []:
            types.add(str(item.get("type")))
    check({"button", "label", "image", "textbox", "card"} <= types,
          f"UI du 5 loai: {sorted(types)}")
    check("photo_hero.png" in blob, "image tro den asset photo")
else:
    blob = ""

png = project / "assets" / "sprites" / "photo_hero.png"
check(png.is_file() and png.read_bytes()[:4] == b"\x89PNG", "PNG anh that ton tai")

main_lua = project / "main.lua"
text = main_lua.read_text(encoding="utf-8") if main_lua.is_file() else ""
check("local ui = require" in text, "write_file XML da ghi main.lua")
check("ui.draw('main')" in text and "TODO" not in text, "luas30-edit da sua main.lua")
check(win._ai_last_applied is not None, "main_window._apply_ai_changes da chay (pipeline that)")
check(bool(win.ai_change_service.last_backup_dir), "backup .luas30/ai-backups duoc tao")
ed = win.tabs.current_editor() if hasattr(win.tabs, "current_editor") else None
check(ed is not None and "ui.draw('main')" in ed.toPlainText(),
      "trinh soan tha da reload noi dung moi")
tool_errors = [str(i.get("content") or "") for i in chat._history
               if "Tool error" in str(i.get("content") or "")]
check(not tool_errors, "khong co 'Tool error'" + (f": {tool_errors[0][:160]}" if tool_errors else ""))
check("Xong" in chat.transcript.toPlainText(), "luot ket thuc len transcript")
from app.views.ai_diff_view import AIDiffView  # regression: ExtraSelection crash
_diff = AIDiffView()
_diff.set_change_set(win._ai_last_applied)
check(len(_diff.before.extraSelections()) > 0
      and len(_diff.after.extraSelections()) > 0,
      "AIDiffView highlight duoc dong thay doi (khong crash ExtraSelection)")
check(not chat._agent_active, "vong lap agent dung dung luc")

shot = _ROOT / "build" / "shots_user_ide"
shot.mkdir(parents=True, exist_ok=True)
win.grab().save(str(shot / "ide_as_user.png"))
print("screenshot:", shot / "ide_as_user.png")

if failures:
    diagnose()
    print("\n== KET QUA ==\nFAIL:")
    for e in failures:
        print(" -", e)
    raise SystemExit(1)
print("\n== KET QUA ==\nFAIL: khong co")
