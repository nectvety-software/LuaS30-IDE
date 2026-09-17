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

# Tên công cụ hợp lệ trong khối ```luas30-tool — nguồn DUY NHẤT, dùng cho cả
# bước lọc lúc parse lẫn bước quảng bá trong prompt. Thêm công cụ mới thì thêm
# ở đây, đừng sửa hai nơi.
READONLY_TOOL_NAMES = ("read", "grep", "glob")
DESIGN_TOOL_NAMES = ("ui_design", "asset")
TOOL_NAMES = READONLY_TOOL_NAMES + DESIGN_TOOL_NAMES


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
            if tool not in TOOL_NAMES:
                continue
            args = item.get("args")
            if not isinstance(args, dict):
                args = {key: value for key, value in item.items() if key not in {"tool", "reason"}}
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
    readonly_tools = (
        "Read-only codebase tools are available and may be used in any access mode. "
        "When you need information that is not already in context, request exactly one tool and wait for its result. "
        "Supported tools are read, grep, and glob. Emit a fenced JSON block such as:\n"
        "```luas30-tool\n"
        '{"tool":"read","args":{"path":"main.lua","start_line":1,"end_line":220},"reason":"Inspect current implementation"}\n'
        "```\n"
        "For grep use args.pattern plus optional args.include; for glob use args.pattern. "
        "Use project-relative paths and never request secrets or .env files."
    )
    design_tools = (
        "UI Design and Assets tools let you read this project's interface design and asset "
        "library. Emit exactly one per turn:\n"
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

