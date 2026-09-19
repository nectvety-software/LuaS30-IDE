"""validate_ai_skills.py — hệ thống SKILLS + KHOANH VÙNG agent trong project.

Kiểm tra:
  1. SkillService parse frontmatter, khám phá skills từ project/extension,
     trùng tên thì project thắng.
  2. Tool `skill` (op list|read) chạy qua AIReadOnlyToolService.
  3. Tool "engine" KHÔNG còn trong TOOL_NAMES; lời gọi kiểu cũ bị HẠ CẤP thành
     read/grep/glob phục vụ TRONG project, và scope="engine" bị stripping.
  4. Agent KHÔNG đọc được mã nguồn của chính IDE: scope=engine bị bỏ, mọi đường
     dẫn chỉ resolve theo gốc project đang mở.
  5. Context build có <agent_skills> nhưng KHÔNG còn <engine_core>/scope=engine.
  6. Vòng lặp chat chạy MỌI tool trong một lượt (_run_tools) + prompt quảng bá
     giới hạn project (Project scope STRICT), không còn engine tool riêng.
  7. Tool "problems" + thẻ lỗi kiểu Antigravity: main_window nối provider
     bảng PROBLEMS CẤU TRÚC + open_location; AIChatView có report_errors_after_change.
     Mặc định access mode "edit_auto" (kiểu Cline Act: áp code thẳng vào dự án).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "studio"))

errors: list[str] = []


def check(ok: bool, label: str) -> None:
    print(("  [OK  ] " if ok else "  [FAIL] ") + label)
    if not ok:
        errors.append(label)


from app.services.ai_agent_protocol import (
    TOOL_NAMES,
    agent_protocol_prompt,
    parse_agent_response,
)
from app.services.ai_tool_service import AIReadOnlyToolService
from app.services.codebase_context_service import CodebaseContextService
from app.services.skill_service import SkillService, parse_front_matter

print("\n-- 1. frontmatter + khám phá --")
meta, body = parse_front_matter(
    "---\nname: demo-skill\ndescription: Mô tả demo\n---\n\nThân skill.\n")
check(meta.get("name") == "demo-skill" and "Thân skill." in body, "parse_front_matter")
meta2, body2 = parse_front_matter("# Không có frontmatter\nĐoạn đầu tiên.\n")
check(meta2 == {} and body2.startswith("# Không"), "thiếu frontmatter -> thân nguyên vẹn")

skills = SkillService(ROOT)
engine_skill_names = {s.name for s in skills.discover()}
check({"vxp-build-run", "s30plus-ui-design", "problems-autofix"} <= engine_skill_names
      and "engine-api-check" not in engine_skill_names,
      f"3 skill IDE-curate còn lại, engine-api-check đã bỏ: {sorted(engine_skill_names)}")
check(any(s.source.startswith("extension:") for s in skills.discover()),
      "tài liệu gốc của extension thành skill theo yêu cầu")

with tempfile.TemporaryDirectory() as td:
    project = Path(td)
    (project / "skills" / "my-game").mkdir(parents=True)
    (project / "skills" / "my-game" / "SKILL.md").write_text(
        "---\nname: my-game\ndescription: Luật riêng của project\n---\nbody\n",
        encoding="utf-8")
    (project / "skills" / "vxp-build-run").mkdir()
    (project / "skills" / "vxp-build-run" / "SKILL.md").write_text(
        "skill trùng tên để thắng bản IDE\n", encoding="utf-8")
    found = {s.name: s for s in skills.discover(project)}
    check(found.get("my-game") is not None and found["my-game"].source == "project",
          "skill của project được khám phá")
    check(found["vxp-build-run"].source == "project",
          "trùng tên: project thắng skill IDE")
    index = skills.index_text(project)
    check("<agent_skills>" in index and "my-game" in index, "index_text có <agent_skills>")

print("\n-- 2. tool skill qua AIReadOnlyToolService --")
tools = AIReadOnlyToolService(engine_root=ROOT)
listing = tools.execute(project, parse_agent_response(
    '```luas30-tool\n{"tool":"skill","args":{"op":"list"}}\n```'
).tool_actions[0])
check("SKILLS" in listing and "vxp-build-run" in listing, "op list trả mục lục")
loaded = tools.execute(project, parse_agent_response(
    '```luas30-tool\n{"tool":"skill","args":{"op":"read","name":"vxp-build-run"}}\n```'
).tool_actions[0])
check("SKILL vxp-build-run" in loaded and "build.py" in loaded, "op read trả toàn văn")
try:
    tools.execute(project, parse_agent_response(
        '```luas30-tool\n{"tool":"skill","args":{"op":"read","name":"khong-ton-tai"}}\n```'
    ).tool_actions[0])
    check(False, "skill lạ phải báo lỗi")
except ValueError as exc:
    check("Không tìm thấy skill" in str(exc), "skill lạ báo lỗi kèm danh sách có sẵn")

print("\n-- 3. tool engine không còn; lời gọi cũ hạ cấp về project --")
check("engine" not in TOOL_NAMES and "skill" in TOOL_NAMES,
      f"TOOL_NAMES = {TOOL_NAMES}")
parsed = parse_agent_response(
    '```luas30-tool\n{"tool":"engine","args":{"op":"read","path":"engine/src/runtime_lua.c"}}\n```'
)
check(len(parsed.tool_actions) == 1 and parsed.tool_actions[0].tool == "read"
      and "scope" not in parsed.tool_actions[0].args
      and parsed.tool_actions[0].args.get("path") == "engine/src/runtime_lua.c",
      "engine op read -> read phục vụ PROJECT, mọi scope bị bỏ")
parsed_list = parse_agent_response(
    '```luas30-tool\n{"tool":"engine","args":{"op":"list","path":"compat"}}\n```'
)
check(parsed_list.tool_actions[0].tool == "glob"
      and parsed_list.tool_actions[0].args.get("pattern") == "compat/*"
      and "scope" not in parsed_list.tool_actions[0].args,
      "engine op list -> glob pattern <path>/*, không scope")

print("\n-- 4. agent CHỈ đọc được project đang mở, không đọc được mã nguồn IDE --")
with tempfile.TemporaryDirectory() as td2:
    proj2 = Path(td2)
    (proj2 / "main.lua").write_text("print('in project')\n", encoding="utf-8")
    ok_read = tools.execute(proj2, parse_agent_response(
        '```luas30-tool\n{"tool":"read","args":{"path":"main.lua","scope":"engine"}}\n```'
    ).tool_actions[0])
    check("READ" in ok_read and "in project" in ok_read,
          "scope=engine bị strip -> vẫn chỉ resolve theo gốc PROJECT")
    try:
        tools.execute(proj2, parse_agent_response(
            '```luas30-tool\n{"tool":"read","args":{"path":"../secrets.env"}}\n```'
        ).tool_actions[0])
        check(False, "đường dẫn thoát project phải bị chặn")
    except ValueError as exc:
        check("project" in str(exc).lower(), "chặn mọi đường dẫn ra ngoài project")
    try:
        tools.execute(proj2, parse_agent_response(
            '```luas30-tool\n{"tool":"read","args":{"path":"studio/app/services/ai_tool_service.py","scope":"engine"}}\n```'
        ).tool_actions[0])
        check(False, "không được đọc mã nguồn của chính IDE")
    except ValueError as exc:
        check("not found" in str(exc).lower(),
              "đường dẫn tới mã nguồn IDE không tồn tại trong project -> bất khả thi")

print("\n-- 5. context chống trùng --")
context = CodebaseContextService(ROOT)
ext_docs = [d for m in context.extension_service.discover() for d in m.instruction_docs()]
instr = context.instruction_paths(project)
check(all(d not in instr for d in ext_docs),
      "SKILLS.md gốc của extension không còn nạp toàn văn vào luật")
bundle = context.build(project, "demo")
check("<agent_skills>" in bundle.text, "build() nhét mục lục <agent_skills>")
check('scope="engine"' not in bundle.text and "<engine_core>" not in bundle.text,
      "context không còn engine_core/scope=engine (khoanh vùng project)")

print("\n-- 6. vòng lặp + prompt --")
chat = (ROOT / "studio/app/views/ai_chat_view.py").read_text(encoding="utf-8")
protocol_src = (ROOT / "studio/app/services/ai_agent_protocol.py").read_text(encoding="utf-8")
check("def _run_tools" in chat and "self._run_tools(\n                parsed.tool_actions," in chat,
      "_response_ready chạy MỌI tool qua _run_tools")
check('"/skills"' in chat, "lệnh /skills trong slash command")
check("SEVERAL luas30-tool" in protocol_src, "prompt cho phép nhiều tool một lượt")
prompt = agent_protocol_prompt(shell_enabled=True)
check('"scope":"engine"' not in prompt and "Project scope (STRICT)" in prompt
      and "Skill tool" in prompt and '"tool":"engine"' not in prompt,
      "prompt quảng bá Project scope STRICT + skill, không còn engine tool/scope")

print("\n-- 7. tool problems + thẻ lỗi Antigravity + mặc định edit_auto (Cline Act) --")
check("problems" in TOOL_NAMES, f"TOOL_NAMES có problems: {TOOL_NAMES}")
parsed_problems = parse_agent_response(
    '```luas30-tool\n{"tool":"problems","args":{"op":"list"},"reason":"Current diagnostics"}\n```'
)
check(len(parsed_problems.tool_actions) == 1
      and parsed_problems.tool_actions[0].tool == "problems",
      "lời gọi problems parse thành công")
check('"tool":"problems"' in prompt and "Problems tool" in prompt,
      "prompt quảng bá Problems tool")
loaded_fix = tools.execute(project, parse_agent_response(
    '```luas30-tool\n{"tool":"skill","args":{"op":"read","name":"problems-autofix"}}\n```'
).tool_actions[0])
check("SKILL problems-autofix" in loaded_fix and "PROBLEMS" in loaded_fix,
      "skill problems-autofix nạp được qua tool skill")
check('self._access_mode = "edit_auto"' in chat
      and "def _problems_snapshot" in chat
      and 'tool == "problems"' in chat,
      "AIChatView: mặc định edit_auto + handler problems nội bộ")
sessions_src = (ROOT / "studio/app/services/ai_session_service.py").read_text(encoding="utf-8")
check('access_mode: str = "edit_auto"' in sessions_src
      and '"ask"' not in sessions_src,
      'AIChatSessionStore mặc định edit_auto, không còn "ask"')
mw = (ROOT / "studio/app/vxpui/main_window.py").read_text(encoding="utf-8")
check("set_problems_provider(self._ai_problems_snapshot)" in mw
      and "def _ai_problems_snapshot" in mw,
      "main_window nối provider bảng PROBLEMS (text cho tool problems)")
check("set_problems_rows_provider(lambda: self.bottom.problems._rows())" in mw
      and "set_open_location_provider(self._ai_open_location)" in mw
      and "def _ai_open_location" in mw,
      "main_window nối provider dòng lỗi + open_location (Antigravity)")
check("report_errors_after_change()" in mw,
      "main_window gọi báo lỗi sau khi áp code (mở thẻ lỗi tự động)")
check("def report_errors_after_change" in chat and "x-luas30://openfile/" in chat
      and "def _insert_problem_card" in chat,
      "AIChatView: thẻ lỗi + neo mở file kiểu Antigravity")

print("\n== KẾT QUẢ ==")
if errors:
    print("FAIL:")
    for e in errors:
        print(" -", e)
    raise SystemExit(1)
print("FAIL: không có")
