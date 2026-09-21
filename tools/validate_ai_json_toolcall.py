"""Validator: phat hien tool-call dang the XML co THAN LA JSON.

Mot so model (Ling/Gemini-style) bo qua fenced protocol va phat the
tool_call voi ten dinh thang sau tag, than la JSON, thuong quen dong the.
Ca EDIT_RE (can fence) lan XML_TOOL_RE (can '>' + arg_key + dong the) bo lot
dang nay -> loi sua code bi roi, "khong thay sua gi". parse_agent_response
nay nap JSON do thanh CodeEditAction/ToolAction that.

Chay:  py -3.12 -u tools/validate_ai_json_toolcall.py
Quy uoc bao cao: in 'OK' tung kiem tra, ket 'FAIL: khong co' khi khong co loi.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "studio"))

from app.services.ai_agent_protocol import (  # noqa: E402
    parse_agent_response,
    _recover_json_tool_calls,
    _TOOL_CALL_OPEN_RE,
)

FENCE = chr(96) * 3
OPEN = "<" + "tool_call"
CLOSE = "<" + "/tool_call>"

failures: list[str] = []


def check(name: str, cond: bool) -> None:
    print(("OK  " if cond else "BAD ") + name)
    if not cond:
        failures.append(name)


# --- tinh static ---------------------------------------------------------------
check("bo open regex khong con \\b (ten dinh sau tag van khop)",
      "\\b" not in _TOOL_CALL_OPEN_RE.pattern)
check("ham recover ton tai", callable(_recover_json_tool_calls))

# --- CASE 1: the khong dong, ten luas30-edit, JSON array (dung like screenshot) --
raw1 = (
    "Let me apply it now with a proper edit block:\n"
    + OPEN
    + "luas30-edit [{\"path\":\"main.lua\",\"find\":\"abc,\",\"replace\":\"abc\",\"reason\":\"Fix trailing comma\"}]\n"
    + "That should resolve the syntax error."
)
p1 = parse_agent_response(raw1, allow_plain_code_edit=True)
check("CASE1 mo 1 edit tu tool_call JSON khong dong",
      len(p1.code_edits) == 1 and p1.code_edits[0].path == "main.lua"
      and p1.code_edits[0].find == "abc," and p1.code_edits[0].replace == "abc")
check("CASE1 xoa khoi noi dung hien thi",
      OPEN not in p1.visible_text and "proper edit block" in p1.visible_text)

# --- CASE 2: name="write" attr, dong the ---------------------------------------
raw2 = "ok " + OPEN + " name=\"write\">[{\"path\":\"src/a.lua\",\"content\":\"x=1\"}]" + CLOSE + " done"
p2 = parse_agent_response(raw2, allow_plain_code_edit=True)
check("CASE2 name=write dong the -> edit content",
      len(p2.code_edits) == 1 and p2.code_edits[0].content == "x=1")
check("CASE2 xoa khoi visible", OPEN not in p2.visible_text)

# --- CASE 3: read tool qua JSON body {tool,args} --------------------------------
raw3 = OPEN + " read>{\"tool\":\"read\",\"args\":{\"path\":\"main.lua\"}}" + CLOSE
t3, e3, _ = _recover_json_tool_calls(raw3)
check("CASE3 doc tool read tu JSON", any(t.tool == "read" and t.args.get("path") == "main.lua" for t in t3) and not e3)

# --- CASE 4: nhieu edit trong mot array ----------------------------------------
raw4 = OPEN + "luas30-edit>" + "[{\"path\":\"a.lua\",\"content\":\"1\"},{\"path\":\"b.lua\",\"content\":\"2\"}]" + CLOSE
p4 = parse_agent_response(raw4, allow_plain_code_edit=True)
check("CASE4 nhieu edit", [e.path for e in p4.code_edits] == ["a.lua", "b.lua"])

# --- CASE 5: fenced ```luas30-edit``` van thang, khong tinh trung ----------------
raw5 = FENCE + "luas30-edit\n[{\"path\":\"a.lua\",\"content\":\"x=1\"}]\n" + FENCE
p5 = parse_agent_response(raw5, allow_plain_code_edit=True)
check("CASE5 fenced edit khong bi tinh doi", len(p5.code_edits) == 1)

# --- CASE 6: van prose nhac tool_call khong co payload -> khong chep dat -------
raw6 = "I will use " + OPEN + " blocks later, no payload here."
p6 = parse_agent_response(raw6, allow_plain_code_edit=True)
check("CASE6 prose khong tao hanh dong gia", not p6.code_edits and not p6.tool_actions)

# --- CASE 7: arg_key XML read van parse (khong bi regression) ------------------
raw7 = OPEN + " read><arg_key>path</arg_key><arg_value>main.lua</arg_value>" + CLOSE
p7 = parse_agent_response(raw7, allow_plain_code_edit=True)
check("CASE7 arg_key read khong bi mat", any(t.tool == "read" for t in p7.tool_actions))

# --- CASE 8: duong dan thoat (../) van giu nguyen de _safe_target chan --------
raw8 = OPEN + "luas30-edit [{\"path\":\"../evil.lua\",\"content\":\"x\"}]"
p8 = parse_agent_response(raw8, allow_plain_code_edit=True)
check("CASE8 parser giu nguyen path de _safe_target chan sau",
      len(p8.code_edits) == 1 and p8.code_edits[0].path == "../evil.lua")

print("\n== KET QUA ==")
if failures:
    print("FAIL: " + "; ".join(failures))
    sys.exit(0)
print("FAIL: khong co")
sys.exit(0)