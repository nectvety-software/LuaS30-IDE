from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass


SUMMARY_RE = re.compile(
    r"```luas30-summary\s*(.*?)```",
    re.IGNORECASE | re.DOTALL,
)
SHELL_RE = re.compile(
    r"```luas30-shell\s*(.*?)```",
    re.IGNORECASE | re.DOTALL,
)
EDIT_RE = re.compile(
    r"```luas30-edit\s*(.*?)```",
    re.IGNORECASE | re.DOTALL,
)
TOOL_RE = re.compile(
    r"```luas30-tool\s*(.*?)```",
    re.IGNORECASE | re.DOTALL,
)
GENERIC_CODE_RE = re.compile(
    r"```([^\n`]*)\n(.*?)```",
    re.IGNORECASE | re.DOTALL,
)
# Một số model (Gemini/Ling-style) bỏ qua protocol fenced JSON và phát
# tool-call gốc XML: <tool_call=read> / <tool_call name="read"> với các cặp
# <arg_key>/<arg_value>. Bộ parse dưới dịch dạng đó sang ToolAction/
# CodeEditAction để vòng lặp agent không chết giữa chừng.
XML_TOOL_RE = re.compile(
    r"<tool_call\b([^<>]*)>(.*?)</tool_call>",
    re.IGNORECASE | re.DOTALL,
)
XML_ARG_RE = re.compile(
    r"<arg_key>\s*(.*?)\s*</arg_key>\s*<arg_value>(.*?)</arg_value>",
    re.IGNORECASE | re.DOTALL,
)
_XML_NAME_ATTR_RE = re.compile(r"\b(?:name|tool)\s*=\s*[\"']?([\w:.\-]+)", re.IGNORECASE)
_XML_PLAIN_NAME_RE = re.compile(r"^[\"'\s]*=?[\"'\s]*([\w:.\-]+)[\"'\s]*$")

_XML_TOOL_ALIASES = {
    "read": "read", "read_file": "read", "view_file": "read",
    "grep": "grep", "search": "grep", "search_files": "grep",
    "glob": "glob", "list_files": "glob", "find_files": "glob",
    "write": "write", "write_file": "write", "create_file": "write",
    "edit": "write", "edit_file": "write", "replace_in_file": "write",
    "ui_design": "ui_design", "asset": "asset",
    "skill": "skill", "problems": "problems", "engine": "engine",
}


_XML_RAW_VALUE_KEYS = {"content", "find", "replace", "old", "new"}


def _xml_tool_calls(raw: str) -> list[tuple[str, dict]]:
    """`<tool_call…>…</tool_call>` -> [(tên tool hoặc "", args)]."""
    calls: list[tuple[str, dict]] = []
    for opener, body in XML_TOOL_RE.findall(raw):
        args: dict = {}
        for key, value in XML_ARG_RE.findall(body):
            key = str(key).strip().lower()
            if not key or key in args:
                continue
            # Value mã nguồn giữ nguyên từng ký tự (newline cuối rất quan trọng);
            # các key mô tả (path/op/pattern…) thì cắt khoảng trắng thừa.
            if key in _XML_RAW_VALUE_KEYS:
                args[key] = str(value)
            else:
                args[key] = str(value).strip()
        name = ""
        opener = str(opener or "").strip()
        if opener:
            match = _XML_NAME_ATTR_RE.search(opener) or _XML_PLAIN_NAME_RE.match(opener)
            if match:
                name = match.group(1)
        if not name:
            name = str(args.pop("tool", "") or "")
        calls.append((name.strip().lower(), args))
    return calls


def _xml_infer_tool(args: dict) -> str:
    """Không có tên tool trong thẻ -> đoán từ chính các args đã cho."""
    keys = set(args)
    if {"path", "content"} <= keys or (keys & {"find", "replace"}) and "path" in keys:
        return "write"
    if keys & {"start_line", "end_line", "scope"} and "path" in keys:
        return "read"
    if "pattern" in keys:
        return "glob" if any(ch in str(args["pattern"]) for ch in "*?[") and "include" not in keys else "grep"
    if "path" in keys and len(keys) <= 3:
        return "read"
    op = str(args.get("op") or "").strip().lower()
    if op in {"catalog", "screens", "get", "add_screen", "add_item", "export"}:
        return "ui_design"
    if op == "make":
        return "asset"
    if op == "read" and "name" in keys:
        return "skill"
    if op in {"list", "count"}:
        return "problems" if keys == {"op"} else "skill"
    return ""


def _xml_to_actions(name: str, args: dict) -> tuple[list, list]:
    """(ToolAction[], CodeEditAction[]) từ một lời gọi XML đã suy ra args."""
    tools: list[ToolAction] = []
    edits: list[CodeEditAction] = []
    reason = str(args.pop("reason", "") or "").strip()
    tool = _XML_TOOL_ALIASES.get(name, "") or _xml_infer_tool(args)
    if tool == "engine":
        tool, args = _normalise_engine_call(args)
    if tool == "write":
        path = str(args.get("path") or "").strip()
        content = args.get("content")
        find = args.get("find", args.get("old"))
        replace = args.get("replace", args.get("new"))
        if path and (content is not None or find is not None):
            edits.append(
                CodeEditAction(
                    path=path,
                    reason=reason,
                    content=str(content) if content is not None else None,
                    find=str(find) if find is not None else None,
                    replace=str(replace) if replace is not None else "",
                    replace_all=str(args.get("replace_all") or "").lower() in {"1", "true", "yes"},
                )
            )
    elif tool in TOOL_NAMES:
        tools.append(ToolAction(tool=tool, args=dict(args), reason=reason))
    return tools, edits

# Tên công cụ hợp lệ trong khối ```luas30-tool — nguồn DUY NHẤT, dùng cho cả
# bước lọc lúc parse lẫn bước quảng bá trong prompt. Thêm công cụ mới thì thêm
# ở đây, đừng sửa hai nơi.
READONLY_TOOL_NAMES = ("read", "grep", "glob")
DESIGN_TOOL_NAMES = ("ui_design", "asset")
# "skill": nạp quy trình làm việc theo yêu cầu (xem skill_service.py).
# "problems": đọc bảng PROBLEMS thật của IDE — handler nằm ở AIChatView vì
# dữ liệu thuộc main_window, không thuộc service nào cả.
WORKBENCH_TOOL_NAMES = ("skill", "problems")
TOOL_NAMES = READONLY_TOOL_NAMES + DESIGN_TOOL_NAMES + WORKBENCH_TOOL_NAMES

# Tool "engine" cũ ĐÃ BỊ GỘP vào read/grep/glob bằng args.scope="engine" —
# hai bộ tool cùng đọc tệp chỉ khác gốc là trùng lặp thuần tuý. Model vẫn có
# thể phát lời gọi kiểu cũ; _normalise_engine_call dịch chúng sang dạng mới.
_ENGINE_OP_TO_TOOL = {"read": "read", "grep": "grep", "glob": "glob", "list": "glob"}


def _normalise_engine_call(args: dict) -> tuple[str, dict]:
    """`{"tool":"engine","args":{"op":...}}` -> (tên tool mới, args có scope)."""
    value = dict(args or {})
    op = str(value.pop("op", None) or "read").strip().lower()
    tool = _ENGINE_OP_TO_TOOL.get(op, "read")
    if op == "list":
        scope_path = str(value.pop("path", "") or "").strip().strip("/")
        value.setdefault("pattern", f"{scope_path}/*" if scope_path else "**/*")
    value["scope"] = "engine"
    return tool, value


@dataclass(frozen=True)
class ShellAction:
    command: str
    reason: str = ""
    cwd: str = "project"

@dataclass(frozen=True)
class ToolAction:
    tool: str
    args: dict
    reason: str = ""


@dataclass(frozen=True)
class CodeEditAction:
    path: str
    reason: str = ""
    content: str | None = None
    find: str | None = None
    replace: str | None = None
    replace_all: bool = False


@dataclass(frozen=True)
class ParsedAgentResponse:
    visible_text: str
    reasoning_summary: str
    shell_actions: tuple[ShellAction, ...]
    tool_actions: tuple[ToolAction, ...]
    code_edits: tuple[CodeEditAction, ...]
    recovered_plain_edit: bool = False


DANGEROUS_PATTERNS = (
    r"\brm\s+-[^\n]*r[^\n]*f",
    r"\bdel\s+/(?:f|q|s)",
    r"\brmdir\s+/(?:s|q)",
    r"\bremove-item\b[^\n]*(?:-recurse|-force)",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-[^\n]*f",
    r"\bformat\b",
    r"\bdiskpart\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\breg\s+delete\b",
    r"\bmkfs(?:\.|\s)",
    r"\bdd\s+if=",
)

SENSITIVE_PATTERNS = (
    r"(^|[;&|]\s*)(?:set|env|printenv)\s*(?:$|[;&|])",
    r"get-childitem\s+env:",
    r"\bcat\s+[^\n]*(?:\.env|credential|secret|private[_-]?key)",
    r"\btype\s+[^\n]*(?:\.env|credential|secret|private[_-]?key)",
)

SAFE_PREFIXES = (
    "dir", "ls", "pwd", "cd", "echo", "where", "which", "whoami",
    "type ", "cat ", "head ", "tail ", "find ", "findstr ", "grep ",
    "rg ", "git status", "git diff", "git log", "git branch", "git show",
    "python --version", "python -v", "py --version", "gcc --version",
    "arm-none-eabi-gcc --version", "cmake --version", "ninja --version",
)


def _request_looks_like_edit(user_request: str) -> bool:
    value = re.sub(r"\s+", " ", str(user_request or "").strip().lower())
    if not value:
        return False

    # Do not reinterpret ordinary explanation/review prompts as file writes.
    readonly_markers = (
        "giải thích", "phân tích", "review", "explain", "why ", "tại sao",
        "đánh giá", "nhận xét", "what does", "là gì",
    )
    if any(marker in value for marker in readonly_markers):
        return False

    edit_markers = (
        "sửa", "chỉnh", "thay", "thêm", "xóa", "xoá", "tạo", "cập nhật",
        "viết", "tối ưu", "hoàn thiện", "nâng cấp", "tích hợp", "fix", "edit",
        "change", "modify", "update", "add ", "remove", "delete", "create",
        "write", "implement", "refactor", "replace", "patch", "apply",
    )
    return any(marker in value for marker in edit_markers)


def _language_matches_path(header: str, path: str) -> bool:
    suffix = os.path.splitext(path)[1].lower()
    token = str(header or "").strip().lower()
    if not token:
        return True
    # Fence headers can be "lua", "lua main.lua", "path=main.lua", etc.
    if os.path.basename(path).lower() in token or path.lower().replace("\\", "/") in token.replace("\\", "/"):
        return True
    aliases = {
        ".lua": ("lua",),
        ".c": ("c",),
        ".h": ("c", "h", "cpp", "c++"),
        ".cc": ("cpp", "c++", "cc"),
        ".cpp": ("cpp", "c++"),
        ".hpp": ("cpp", "c++", "hpp"),
        ".py": ("python", "py"),
        ".js": ("javascript", "js"),
        ".ts": ("typescript", "ts"),
        ".tsx": ("tsx", "typescript", "ts"),
        ".jsx": ("jsx", "javascript", "js"),
        ".json": ("json",),
        ".md": ("markdown", "md"),
        ".txt": ("text", "txt"),
    }
    first = token.split()[0].strip("{}[]()<>:;,=\'\"")
    return first in aliases.get(suffix, ())


def _recover_plain_fenced_edit(
    raw: str,
    *,
    active_path: str,
    active_text: str,
    user_request: str,
) -> tuple[CodeEditAction | None, str]:
    if not active_path or not _request_looks_like_edit(user_request):
        return None, raw

    candidates: list[tuple[int, re.Match[str], str]] = []
    active_name = os.path.basename(active_path).lower()
    for match in GENERIC_CODE_RE.finditer(raw):
        header = str(match.group(1) or "").strip()
        if header.lower().startswith("luas30-"):
            continue
        if not _language_matches_path(header, active_path):
            continue
        code = str(match.group(2) or "").replace("\r\n", "\n").replace("\r", "\n")
        code = code.strip("\n")
        if not code.strip():
            continue

        score = 1
        if active_name and active_name in header.lower():
            score += 4
        if header:
            score += 1
        candidates.append((score, match, code))

    if not candidates:
        return None, raw

    candidates.sort(key=lambda item: (item[0], len(item[2])), reverse=True)
    _score, match, code = candidates[0]

    old_lines = max(1, len(str(active_text or "").splitlines()))
    new_lines = len(code.splitlines())
    # A plain Markdown fence is only used as a compatibility fallback when it
    # resembles a complete active-file replacement. Small snippets remain chat
    # text so automatic-edit modes cannot accidentally replace a whole file.
    if str(active_text or "").strip():
        minimum = max(6, int(old_lines * 0.40))
        if new_lines < minimum:
            return None, raw
    elif new_lines < 3:
        return None, raw

    normalized = code + ("\n" if code and not code.endswith("\n") else "")
    visible = (raw[: match.start()] + raw[match.end() :]).strip()
    if not visible:
        visible = f"Prepared code changes for `{active_path}`."
    return (
        CodeEditAction(
            path=active_path,
            reason="Recovered plain fenced code as an active-file edit proposal.",
            content=normalized,
        ),
        visible,
    )


def parse_agent_response(
    text: str,
    *,
    active_path: str = "",
    active_text: str = "",
    user_request: str = "",
    allow_plain_code_edit: bool = False,
) -> ParsedAgentResponse:
    raw = str(text or "")
    summaries = [match.strip() for match in SUMMARY_RE.findall(raw) if match.strip()]
    actions: list[ShellAction] = []

    for block in SHELL_RE.findall(raw):
        block = block.strip()
        if not block:
            continue
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            command = str(item.get("command") or "").strip()
            if not command:
                continue
            actions.append(
                ShellAction(
                    command=command,
                    reason=str(item.get("reason") or "").strip(),
                    cwd=str(item.get("cwd") or "project").strip() or "project",
                )
            )

    tools: list[ToolAction] = []
    for block in TOOL_RE.findall(raw):
        block = block.strip()
        if not block:
            continue
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            tool = str(item.get("tool") or "").strip().lower()
            args = item.get("args")
            if not isinstance(args, dict):
                args = {key: value for key, value in item.items() if key not in {"tool", "reason"}}
            if tool == "engine":
                tool, args = _normalise_engine_call(args)
            if tool not in TOOL_NAMES:
                continue
            tools.append(
                ToolAction(
                    tool=tool,
                    args=dict(args),
                    reason=str(item.get("reason") or "").strip(),
                )
            )

    edits: list[CodeEditAction] = []
    for block in EDIT_RE.findall(raw):
        block = block.strip()
        if not block:
            continue
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "").strip()
            if not path:
                continue
            content = item.get("content")
            find = item.get("find")
            replace = item.get("replace")
            if content is None and find is None:
                continue
            edits.append(
                CodeEditAction(
                    path=path,
                    reason=str(item.get("reason") or "").strip(),
                    content=str(content) if content is not None else None,
                    find=str(find) if find is not None else None,
                    replace=str(replace) if replace is not None else "",
                    replace_all=bool(item.get("replace_all", False)),
                )
            )

    recovered_plain_edit = False
    visible_source = raw
    # Lời gọi XML (model không tuân theo fenced protocol) — chạy SAU vòng lặp
    # JSON để ưu tiên định dạng chuẩn và khử trùng lặp.
    for name, xml_args in _xml_tool_calls(raw):
        xml_tools, xml_edits = _xml_to_actions(name, xml_args)
        for action in xml_tools:
            if any(a.tool == action.tool and a.args == action.args for a in tools):
                continue
            tools.append(action)
        edits.extend(xml_edits)
    if allow_plain_code_edit and not edits and active_path:
        recovered, recovered_visible = _recover_plain_fenced_edit(
            raw,
            active_path=active_path,
            active_text=active_text,
            user_request=user_request,
        )
        if recovered is not None:
            edits.append(recovered)
            visible_source = recovered_visible
            recovered_plain_edit = True

    visible = SUMMARY_RE.sub("", visible_source)
    visible = SHELL_RE.sub("", visible)
    visible = TOOL_RE.sub("", visible)
    visible = EDIT_RE.sub("", visible)
    visible = XML_TOOL_RE.sub("", visible)
    visible = re.sub(r"\n{3,}", "\n\n", visible).strip()
    return ParsedAgentResponse(
        visible_text=visible,
        reasoning_summary="\n".join(summaries).strip(),
        shell_actions=tuple(actions),
        tool_actions=tuple(tools),
        code_edits=tuple(edits),
        recovered_plain_edit=recovered_plain_edit,
    )


def classify_shell_command(command: str) -> tuple[str, str]:
    value = str(command or "").strip()
    low = value.lower()
    if not value:
        return "blocked", "Empty command"

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, low, re.IGNORECASE):
            return "dangerous", "Potentially destructive command"

    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, low, re.IGNORECASE):
            return "sensitive", "May expose environment variables or secret files"

    normalized = re.sub(r"\s+", " ", low)
    if any(normalized == prefix or normalized.startswith(prefix) for prefix in SAFE_PREFIXES):
        return "safe", "Read-only or inspection-oriented command"

    if any(token in normalized for token in (
        " tools\\build.py", " tools/build.py", "validate_", "pytest", "unittest",
        "cmake --build", "ninja", "make", "gcc ", "g++ ", "clang ", "python ", "py ",
    )):
        return "project", "Project command may create or update build artifacts"

    return "project", "Command can modify the project or local environment"


def redact_shell_output(text: str) -> str:
    value = str(text or "")
    # Redact values from common secret-bearing environment variables before shell
    # output is returned to a remote model. Do not mutate what the local terminal shows.
    for key, secret in os.environ.items():
        upper = key.upper()
        if not any(token in upper for token in (
            "KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "IMSI", "CREDENTIAL",
        )):
            continue
        if secret and len(secret) >= 5:
            value = value.replace(secret, f"<redacted:{key}>")
    return value


def bounded_shell_output(text: str, limit: int = 18000) -> str:
    value = redact_shell_output(text)
    if len(value) <= limit:
        return value
    head = value[: limit // 2]
    tail = value[-limit // 2 :]
    return head + "\n...[shell output truncated]...\n" + tail


def agent_protocol_prompt(
    shell_enabled: bool,
    edit_enabled: bool = True,
    plan_mode: bool = False,
    full_access: bool = False,
) -> str:
    if plan_mode:
        shell = "Plan mode is active. Do not emit luas30-shell blocks."
        edits = "Plan mode is active. Do not emit luas30-edit blocks or claim files were modified."
    else:
        shell = (
            "Full Access is active. Shell actions are executed automatically without confirmation. "
            "Work autonomously, request one command at a time, inspect its result, and continue until the task is complete. "
            "Do not claim a command ran until its result is returned. Emit a fenced block like:\n"
            "```luas30-shell\n"
            '{"command":"python tools/validate_x.py","cwd":"project","reason":"Run validation"}\n'
            "```"
            if shell_enabled and full_access
            else
            (
            "Shell access is available through a user-controlled tool. "
            "When a shell command is genuinely useful, emit exactly one fenced block like:\n"
            "```luas30-shell\n"
            '{"command":"python tools/validate_x.py","cwd":"project","reason":"Run validation"}\n'
            "```\n"
            "Do not claim it ran until a shell result is returned."
            if shell_enabled
            else
            "Shell access is disabled. Do not emit luas30-shell blocks."
            )
        )
        edits = (
            "Code-change proposals are available. When the user asks you to create, fix, update, "
            "refactor or otherwise modify project code, you MUST emit a luas30-edit JSON block "
            "instead of pasting the changed source only in an ordinary Markdown code fence. "
            "Use project-relative paths only. Prefer exact "
            "find/replace edits for small changes and full content only when necessary. Examples:\n"
            "```luas30-edit\n"
            '[{"path":"main.lua","find":"old text","replace":"new text","reason":"Fix logic"}]\n'
            "```\n"
            "or\n"
            "```luas30-edit\n"
            '{"path":"src/new.lua","content":"-- full file\\n","reason":"Add module"}\n'
            "```\n"
            "Do not claim an edit was applied until the tool reports that it was applied."
            if edit_enabled
            else
            "Code editing is disabled. Do not emit luas30-edit blocks."
        )
    # Tool "engine" cũ giờ là args.scope="engine" của read/grep/glob — một lời
    # gọi mô tả, không phải một bộ máy mới.
    engine_scope_note = (
        'Engine scope: add "scope":"engine" to read/grep/glob to open the LuaS30 IDE '
        "itself — the MRE core that a project cannot see: the thin Lua wrapper "
        "templates/basic/src/engine.lua, the luaL_Reg funcs[] table registered by "
        "luas30_bridge_open in engine/src/runtime_bridge.c (a function absent there "
        "does not exist), other "
        "templates, the MRE SDK surface (sdk/luas30: abi/symbols.json, include/ls30), "
        "device compatibility fixtures (compat/) and doc/ai/. Paths are relative to "
        "the IDE root and only those folders are readable. Never invent engine "
        'functions — verify with scope=engine grep/read first. Example:\n'
        "```luas30-tool\n"
        '{"tool":"read","args":{"path":"templates/basic/src/engine.lua","start_line":1,'
        '"end_line":200,"scope":"engine"},"reason":"Learn the real Engine API"}\n'
        "```"
    )
    skills_note = (
        "Skill tool: <agent_skills> in the context lists on-demand procedure "
        "documents (project/engine/extension skills). When one fits the task, load "
        "its full text and follow it:\n"
        "```luas30-tool\n"
        '{"tool":"skill","args":{"op":"read","name":"engine-api-check"},'
        '"reason":"Load the procedure"}\n'
        "```\n"
        "op list re-discovers skills; op read needs args.name.\n"
        "Problems tool: read the IDE's live PROBLEMS panel (Lua diagnostics the "
        "editor collected) to analyze and fix errors autonomously:\n"
        "```luas30-tool\n"
        '{"tool":"problems","args":{"op":"list"},"reason":"Current diagnostics"}\n'
        "```\n"
        "Use it after applying edits to verify the fix, and again at the end of a "
        "bug-fixing task — follow the problems-autofix skill when one is listed."
    )
    readonly_tools = (
        "Read-only codebase tools are available and may be used in any access mode. "
        "You may emit SEVERAL luas30-tool blocks in one answer — they run sequentially "
        "in order and every result is returned before you continue. When you need "
        "information that is not already in context, ask for it instead of guessing. "
        "Supported tools: read (args.path + optional start_line/end_line), "
        "grep (args.pattern, optional args.include), glob (args.pattern). Example:\n"
        "```luas30-tool\n"
        '{"tool":"read","args":{"path":"main.lua","start_line":1,"end_line":220},"reason":"Inspect current implementation"}\n'
        "```\n"
        "Use project-relative paths and never request secrets or .env files.\n"
        + engine_scope_note + "\n" + skills_note
    )
    design_tools = (
        "UI Design and Assets tools let you read this project's interface design and asset "
        "library. One block per operation:\n"
        "```luas30-tool\n"
        '{"tool":"ui_design","args":{"op":"catalog"},"reason":"See available component types"}\n'
        "```\n"
        "`ui_design` read ops: catalog (component types + default sizes), screens, get (args.screen).\n"
        "```luas30-tool\n"
        '{"tool":"asset","args":{"op":"list"},"reason":"List existing project assets"}\n'
        "```"
    )
    design_tools += (
        " You may also CREATE design work when the user asks for it.\n"
        "`ui_design` write ops: add_screen (args.id), rename_screen, delete_screen, set_screen, "
        "add_item, update_item (args.name + args.fields), remove_item, export (writes ui_design.lua).\n"
        "```luas30-tool\n"
        '{"tool":"ui_design","args":{"op":"add_item","screen":"main","type":"button",'
        '"name":"btn_start","x":64,"y":240,"w":78,"h":24,"text":"Bat dau"},'
        '"reason":"Add the start button"}\n'
        "```\n"
        "`asset` write op: make — generates a real PNG design resource. kinds: "
        "solid, gradient, checker, grid, button, panel, frame, bar, label. Optional args: name, "
        "target (ui|sprites|background|tiles|maps|assets), width, height, color, color2, radius, "
        "text, font_size, value, cell.\n"
        "```luas30-tool\n"
        '{"tool":"asset","args":{"op":"make","kind":"button","name":"btn_primary",'
        '"width":78,"height":24,"color":"#007acc","text":"OK"},"reason":"Generate button sprite"}\n'
        "```\n"
        "Coordinates are snapped to a 4px grid and clamped inside the 240x320 screen for you. "
        "Run `ui_design` op `export` after changing the design, and never claim a design or asset "
        "was written until the tool reports success."
        if (edit_enabled and not plan_mode)
        else
        " Design changes and asset generation are unavailable in this mode; do not emit "
        "ui_design or asset write ops."
    )
    return (
        "Do not reveal private chain-of-thought. Instead, when useful, provide only a brief "
        "high-level reasoning summary (1-5 short bullets) in this block:\n"
        "```luas30-summary\n- inspected relevant files\n- next step and why\n```\n"
        "The summary must describe conclusions/actions, not hidden token-by-token reasoning.\n"
        + readonly_tools + "\n" + design_tools + "\n" + shell + "\n" + edits
        + (
            "\nFull Access automation is active: use the available read tools, code edits and shell actions autonomously, "
            "validate your work when useful, and stop only when the requested task is complete or you truly need user input."
            if full_access and not plan_mode
            else ""
        )
    )

