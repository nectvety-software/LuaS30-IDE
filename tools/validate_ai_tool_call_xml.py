"""validate_ai_tool_call_xml.py — dich tool-call XML goc cua model (Gemini/Ling).

Model bo qua fenced protocol ```luas30-tool va phat the tool_call + cap
arg_key/arg_value; parse_agent_response nay dich duoc ca hai dinh dang
de vong lap agent khong chet va code van duoc tu ap vao du an.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "studio"))

errors: list[str] = []


def check(ok: bool, label: str) -> None:
    print(("  [OK  ] " if ok else "  [FAIL] ") + label)
    if not ok:
        errors.append(label)


from app.services.ai_agent_protocol import parse_agent_response

AK = "<arg_key>"
KV = "<arg_value>"
EK = "</" + "arg_key>"
EV = "</" + "arg_value>"
TC = "</" + "tool_call>"


def call(opener: str, *pairs) -> str:
    body = "".join(AK + k + EK + KV + v + EV for k, v in pairs)
    return "<tool_call" + opener + ">" + body + TC


# 1. Dung dang trong anh loi: khong co ten tool, chi args.
sample = "Let me read all needed sections now.\n" + call(
    "",
    ("path", "main.lua"),
    ("start_line", "770"),
    ("end_line", "790"),
    ("reason", "Inspect unexpected end at line 777"),
)
p = parse_agent_response(sample)
check(len(p.tool_actions) == 1 and p.tool_actions[0].tool == "read"
      and p.tool_actions[0].args.get("path") == "main.lua"
      and p.tool_actions[0].args.get("start_line") == "770",
      "XML khong ten -> read (path/start_line/end_line)")
check(p.tool_actions[0].reason == "Inspect unexpected end at line 777"
      and "reason" not in p.tool_actions[0].args,
      "reason tach rieng, khong lan vao args")
check("tool_call" not in p.visible_text and "arg_key" not in p.visible_text
      and "Let me read" in p.visible_text,
      "XML go khoi chu hien thi, prose giu nguyen")

# 2. Ten trong the mo.
p2 = parse_agent_response(call("=grep", ("pattern", "elseif"), ("include", "**/*.lua")))
check(len(p2.tool_actions) == 1 and p2.tool_actions[0].tool == "grep",
      "<tool_call=ten> duoc nhan dien")

p3 = parse_agent_response(call(' name="write_file"',
                               ("path", "src/ui.lua"),
                               ("content", "local t = {}\nreturn t\n")))
check(len(p3.code_edits) == 1 and p3.code_edits[0].path == "src/ui.lua"
      and "return t" in (p3.code_edits[0].content or ""),
      "write_file XML -> CodeEditAction full content")

p4 = parse_agent_response(call("=edit_file",
                               ("path", "main.lua"),
                               ("find", "elseif then"),
                               ("replace", "else\nend")))
check(len(p4.code_edits) == 1 and p4.code_edits[0].find == "elseif then"
      and p4.code_edits[0].replace == "else\nend",
      "edit_file XML -> find/replace")

# 3. Suy doan khi thieu ten.
pg = parse_agent_response(call("", ("pattern", "**/*.lua")))
check(len(pg.tool_actions) == 1 and pg.tool_actions[0].tool == "glob",
      "pattern ky tu dai dien -> glob")
psk = parse_agent_response(call("", ("op", "read"), ("name", "problems-autofix")))
check(len(psk.tool_actions) == 1 and psk.tool_actions[0].tool == "skill"
      and psk.tool_actions[0].args.get("name") == "problems-autofix",
      "op read + name -> skill")
ppb = parse_agent_response(call("", ("op", "list")))
check(len(ppb.tool_actions) == 1 and ppb.tool_actions[0].tool == "problems",
      "op list don doc -> problems")

# 4. engine kieu cu trong XML -> HA CAP thành read project, KHONG con scope=engine
#    (agent chi duoc doc codebase cua mo dang mo, khong phai ma nguon cua IDE).
pe = parse_agent_response(call("=engine",
                               ("op", "read"),
                               ("path", "templates/basic/src/engine.lua")))
check(len(pe.tool_actions) == 1 and pe.tool_actions[0].tool == "read"
      and "scope" not in pe.tool_actions[0].args,
      "engine XML -> read project, khong con scope=engine")

# 5. Khong trung lap voi fenced JSON cung noi dung; nhieu khoi XML giu thu tu.
mix = ('```luas30-tool\n{"tool":"read","args":{"path":"main.lua"},"reason":"x"}\n```\n'
       + call("", ("path", "main.lua")) + "\n"
       + call("=grep", ("pattern", "abc")))
pm = parse_agent_response(mix)
check(len(pm.tool_actions) == 2 and pm.tool_actions[0].tool == "read"
      and pm.tool_actions[1].tool == "grep",
      "fenced JSON uu tien, XML trung bi bo, giu thu tu")

# 6. Hoi quy: chi co prose -> khong hanh dong, khong doi text.
plain = parse_agent_response("Chi giai thich, khong co tool nao ca.")
check(not plain.tool_actions and not plain.code_edits
      and plain.visible_text.startswith("Chi giai thich"),
      "proise thuan khong bi anh huong")

print("\n== KET QUA ==")
if errors:
    print("FAIL:")
    for e in errors:
        print(" -", e)
    raise SystemExit(1)
print("FAIL: khong co")
