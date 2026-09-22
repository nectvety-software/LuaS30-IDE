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
# Models sometimes ignore the luas30-edit protocol and paste complete source in a
# plain Markdown fence. When that fence NAMES a project file in its info string
# (```lua path=src/menu.lua```, ```file=src/menu.lua```, or a bare ```src/menu.lua
# header) we recover it into a whole-file edit so generated code becomes a real
# project file Codex-style. Confinement to the open project is still enforced
# downstream by AIChangeService._safe_target, so a bogus/absolute path can never
# escape into the IDE install tree.
FENCE_PATH_ATTR_RE = re.compile(
    r"\b(?:path|file|filename|title)\s*[:=]\s*[\"']?([^\s\"']+)[\"']?",
    re.IGNORECASE,
)
# Models often put the file directive on its own first line inside the fence, e.g.
# ```lua\npath=src/menu.lua\nlocal Menu = {}\n... So a full-line directive at the
# top of the block body is treated the same as an info-string path.
FENCE_DIRECTIVE_LINE_RE = re.compile(
    r"^\s*(?:path|file|filename|title)\s*[:=]\s*(\S.*?)\s*$",
    re.IGNORECASE,
)
FENCE_ALLOWED_SUFFIXES = frozenset({
    ".lua", ".c", ".h", ".cpp", ".hpp", ".cc", ".py", ".js", ".ts", ".tsx",
    ".jsx", ".json", ".md", ".txt", ".xml", ".conf", ".cfg", ".ini", ".css",
    ".html", ".htm", ".vxp", ".gitignore", ".csv", ".yaml", ".yml",
})


def _extract_fenced_path(header: str) -> str:
    """Trả về đường dẫn tương đối-project nếu info-string khai báo một tệp,
    ngược lại rỗng (để ```lua trần vẫn rơi về phục hồi theo tệp đang mở)."""
    token = str(header or "").strip()
    if not token or token.lower().startswith("luas30-"):
        return ""
    match = FENCE_PATH_ATTR_RE.search(token)
    if match:
        candidate = match.group(1).strip()
    else:
        parts = token.split()
        candidate = parts[0].strip("[](){}<>") if parts else ""
    candidate = candidate.replace("\\", "/").strip().strip("/")
    if not candidate:
        return ""
    if candidate.startswith("/") or re.match(r"^[A-Za-z]:", candidate):
        return ""
    if ".." in candidate.split("/"):
        return ""
    if os.path.splitext(candidate)[1].lower() not in FENCE_ALLOWED_SUFFIXES:
        return ""
    return candidate


def _recover_fenced_files(raw: str) -> tuple[list[CodeEditAction], str]:
    edits: list[CodeEditAction] = []
    spans: list[tuple[int, int]] = []
    for match in GENERIC_CODE_RE.finditer(raw):
        header = str(match.group(1) or "")
        code = str(match.group(2) or "").replace("\r\n", "\n").replace("\r", "\n")
        path = _extract_fenced_path(header)
        drop_first_line = False
        if not path and code.strip():
            line_match = FENCE_DIRECTIVE_LINE_RE.match(code.split("\n", 1)[0])
            if line_match:
                path = _extract_fenced_path("path=" + line_match.group(1).strip("\"' "))
                drop_first_line = bool(path)
        if not path:
            continue
        lines = code.split("\n")
        if drop_first_line:
            lines = lines[1:]
        body = "\n".join(lines).strip("\n")
        if not body.strip():
            continue
        body += "\n" if body and not body.endswith("\n") else ""
        edits.append(
            CodeEditAction(
                path=path,
                reason="Recovered fenced code block as file content.",
                content=body,
            )
        )
        spans.append((match.start(), match.end()))
    if not edits:
        return [], raw
    visible = raw
    for start, end in sorted(spans, reverse=True):
        visible = visible[:start] + visible[end:]
    visible = re.sub(r"\n{3,}", "\n\n", visible).strip()
    if not visible:
        visible = "Đã chuẩn bị ghi các tệp: " + ", ".join(e.path for e in edits[:6]) + "."
    return edits, visible


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
    "skill": "skill", "problems": "problems",
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
    if keys & {"start_line", "end_line"} and "path" in keys:
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
    args.pop("scope", None)
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
# "run_app": build project + chạy thử game/app trên VXPEmu screen-only + chụp
# ảnh khói; handler bất đồng bộ cũng nằm ở AIChatView (kết quả về qua callback).
# "goal": cập nhật kế hoạch/trạng thái của Goal Mode (`.luas30/ai_goal.json`).
# Phải nằm trong TOOL_NAMES kể cả khi chưa bật Goal Mode: parser lọc theo danh
# sách này, thêm tool mà quên ở đây thì khối tool bị bỏ IM LẶNG (0 action, không
# lỗi) — đúng lỗi đã từng dính với các tool trước.
WORKBENCH_TOOL_NAMES = ("skill", "problems", "run_app", "goal")
TOOL_NAMES = READONLY_TOOL_NAMES + DESIGN_TOOL_NAMES + WORKBENCH_TOOL_NAMES

# Ops hợp lệ của tool `goal` — nguồn duy nhất, dùng cho cả handler lẫn prompt.
GOAL_OPS = ("status", "plan", "start", "done", "fail", "blocked", "finish")

# Agent KHÔNG còn quyền đọc mã nguồn của chính LuaS30 IDE (đã bỏ scope="engine").
# Model cũ vẫn có thể phát `{"tool":"engine","args":{"op":...}}`; lời gọi đó được
# HẠ CẤP thành read/grep/glob phục vụ TRONG project đang mở — cùng op, nhưng gốc
# là project chứ không phải thư mục cài IDE, nên không lộ mã nguồn của IDE.
_ENGINE_OP_TO_TOOL = {"read": "read", "grep": "grep", "glob": "glob", "list": "glob"}


def _downgrade_engine_call(args: dict) -> tuple[str, dict]:
    """`tool=="engine"` -> (read/grep/glob project, args đã bỏ mọi scope)."""
    value = dict(args or {})
    value.pop("scope", None)
    op = str(value.pop("op", None) or ("glob" if "pattern" in value else "read")).strip().lower()
    tool = _ENGINE_OP_TO_TOOL.get(op, "read")
    if op == "list":
        scope_path = str(value.pop("path", "") or "").strip().strip("/")
        value.setdefault("pattern", f"{scope_path}/*" if scope_path else "**/*")
    return tool, value


# Model kieu Ling/Gemini co the phat tool-call dang the XML voi ten dinh sau
# tag va THAN LA JSON, khong phai fenced protocol. Cac ham recover duoi day
# nap dang do (xem _recover_json_tool_calls).

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


# Model kieu Ling/Gemini co the phat tool-call dang the XML: ten dinh thang sau
# tag, THAN LA JSON (khong phai cap arg_key), va thuong quen dong the. Ca
# EDIT_RE (can fence ba huy) lan XML_TOOL_RE (can '>' + arg_key + dong the) deu
# bo lot, nen loi sua code cua model bi roi xuong dat va "khong thay sua gi".
# _recover_json_tool_calls o duoi nap JSON do bang raw_decode, chiu duoc than
# nhieu dong va the khong dong, bien no thanh CodeEditAction/ToolAction that.
_EDIT_CALL_NAMES = {
    "luas30-edit", "edit", "edit_file", "write", "write_file",
    "create_file", "replace_in_file", "apply_patch",
}
_TOOL_CALL_OPEN_RE = re.compile(r"<tool_call", re.IGNORECASE)
_TOOL_CALL_NAME_RE = re.compile(
    r"\s*(?:(?:name|tool)\s*=\s*[\x22\x27]([^\x22\x27]+)[\x22\x27]|([A-Za-z0-9_.:\-]+))",
    re.IGNORECASE,
)
_JSON_DECODER = json.JSONDecoder()
_CLOSE_TAG = "<" + "/tool_call>"


def _edits_from_json(payload) -> list[CodeEditAction]:
    out: list[CodeEditAction] = []
    items = payload if isinstance(payload, list) else [payload]
    for item in items:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip()
        if not path:
            continue
        content = item.get("content")
        find = item.get("find", item.get("old"))
        replace = item.get("replace", item.get("new"))
        if content is None and find is None:
            continue
        out.append(
            CodeEditAction(
                path=path,
                reason=str(item.get("reason") or "").strip(),
                content=str(content) if content is not None else None,
                find=str(find) if find is not None else None,
                replace=str(replace) if replace is not None else "",
                replace_all=bool(item.get("replace_all", False)),
            )
        )
    return out


def _tools_from_json(payload) -> list[ToolAction]:
    out: list[ToolAction] = []
    items = payload if isinstance(payload, list) else [payload]
    for item in items:
        if not isinstance(item, dict):
            continue
        tool = str(item.get("tool") or "").strip().lower()
        args = item.get("args")
        if not isinstance(args, dict):
            args = {k: v for k, v in item.items() if k not in {"tool", "reason"}}
        if tool == "engine":
            tool, args = _downgrade_engine_call(args)
        if tool not in TOOL_NAMES:
            continue
        out.append(
            ToolAction(tool=tool, args=dict(args), reason=str(item.get("reason") or "").strip())
        )
    return out


def _recover_json_tool_calls(raw: str):
    """Tra (tools, edits, spans) tu cac the tool_call co than la JSON.

    spans = vung text da chuyen thanh hanh dong, phuc vu xoai khoi noi dung
    hien thi (giong cach _recover_fenced_files lam voi khoi fenced).
    """
    tools: list[ToolAction] = []
    edits: list[CodeEditAction] = []
    spans: list[tuple[int, int]] = []
    for opener in _TOOL_CALL_OPEN_RE.finditer(raw):
        start = opener.start()
        after = opener.end()
        close = raw.lower().find(_CLOSE_TAG, after)
        region = raw[after: close if close != -1 else len(raw)]
        match = _TOOL_CALL_NAME_RE.match(region)
        name = ""
        if match:
            name = (match.group(1) or match.group(2) or "").strip().lower()
        search_from = match.end() if match else 0
        json_start = -1
        for idx in range(search_from, len(region)):
            if region[idx] in "[{":
                json_start = idx
                break
        if json_start < 0:
            continue
        try:
            payload, consumed = _JSON_DECODER.raw_decode(region[json_start:])
        except ValueError:
            continue
        mapped = _XML_TOOL_ALIASES.get(name, "")
        if name in _EDIT_CALL_NAMES or mapped == "write":
            edits.extend(_edits_from_json(payload))
        elif mapped in TOOL_NAMES:
            if isinstance(payload, dict) and "tool" in payload:
                tools.extend(_tools_from_json(payload))
            elif isinstance(payload, dict):
                tools.append(
                    ToolAction(
                        tool=mapped,
                        args=dict(payload),
                        reason=str(payload.get("reason") or "").strip(),
                    )
                )
            else:
                continue
        else:
            recovered = _edits_from_json(payload)
            if recovered:
                edits.extend(recovered)
            else:
                tools.extend(_tools_from_json(payload))
        end = after + json_start + consumed
        if close != -1:
            end = close + len(_CLOSE_TAG)
        spans.append((start, end))
    return tools, edits, spans


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
                tool, args = _downgrade_engine_call(args)
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
    # Tool-call dang the XML nhung THAN LA JSON (quen fence, quen dong the) —
    # thu phat hien CUOI CUNG de khong trung lap voi fenced/XML chuan. Xoai
    # vung da chuyen thanh hanh dong khoi noi dung hien thi.
    json_tools, json_edits, json_spans = _recover_json_tool_calls(raw)
    for action in json_tools:
        if any(a.tool == action.tool and a.args == action.args for a in tools):
            continue
        tools.append(action)
    edits.extend(json_edits)
    if json_spans and visible_source is raw:
        cut = raw
        for s, e in sorted(json_spans, reverse=True):
            cut = cut[:s] + cut[e:]
        visible_source = re.sub(r"\n{3,}", "\n\n", cut).strip()
    if allow_plain_code_edit and not edits:
        recovered_files, files_visible = _recover_fenced_files(raw)
        if recovered_files:
            edits.extend(recovered_files)
            visible_source = files_visible
            recovered_plain_edit = True
        elif active_path:
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
    goal_mode: bool = False,
) -> str:
    if plan_mode:
        shell = "Plan mode is active. Do not emit luas30-shell blocks."
        edits = "Plan mode is active. Do not emit luas30-edit blocks or claim files were modified."
    else:
        shell = (
            "Full Access is active. Safe and project-scoped shell actions are executed automatically without confirmation. "
            "Commands classified dangerous or secret-bearing still ask for confirmation — do not try to bypass that gate. "
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
            "If you instead paste a complete file in a plain Markdown fence, put the "
            "project-relative path in the fence header (```lua path=src/menu.lua``` or "
            "a bare ```src/menu.lua header) so the IDE writes it as a real project file. "
            "Do not claim an edit was applied until the tool reports that it was applied."
            if edit_enabled
            else
            "Code editing is disabled. Do not emit luas30-edit blocks."
        )
    # Agent chỉ làm việc TRONG project đang mở: không còn đường nào đọc mã nguồn
    # của chính LuaS30 IDE (scope="engine"/tool `engine` đã bỏ hẳn).
    project_scope_note = (
        "Project scope (STRICT): every read/grep/glob path is relative to the OPEN "
        "project root and stays inside it. You cannot — and must not try to — read or "
        "edit the LuaS30 IDE's own installation/source tree (no scope=engine, no "
        "outside paths, no '..'). Work only with the project files in context; if a "
        "needed symbol is not in the project, say so instead of opening IDE internals."
    )
    skills_note = (
        "Skill tool: <agent_skills> in the context lists on-demand procedure "
        "documents (project/extension skills). When one fits the task, load "
        "its full text and follow it:\n"
        "```luas30-tool\n"
        '{"tool":"skill","args":{"op":"read","name":"problems-autofix"},'
        '"reason":"Load the procedure"}\n'
        "```\n"
        "op list re-discovers skills; op read needs args.name.\n"
        "Problems tool: read the IDE's live PROBLEMS panel (Lua diagnostics the "
        "editor collected) to analyze and fix errors autonomously:\n"
        "```luas30-tool\n"
        '{"tool":"problems","args":{"op":"list"},"reason":"Current diagnostics"}\n'
        "```\n"
        "Use it after applying edits to verify the fix, and again at the end of a "
        "bug-fixing task — follow the problems-autofix skill when one is listed.\n"
        "Run/test tool: build the OPEN project and launch it on the VXPEmu emulator "
        "(headless, screen-only), then a screenshot of the running app is captured as "
        "a smoke test you can reason about. Use it when the user asks to run, test, "
        "preview or check that the game/app works. Emit ONE run_app per turn:\n"
        "```luas30-tool\n"
        '{"tool":"run_app","args":{"op":"run"},"reason":"Build and smoke-test the app on the emulator"}\n'
        "```\n"
        'op "stop" halts the running emulator. Do not claim the app runs or looks '
        "correct until a run/test result (with its screenshot path) is returned."
    )
    goal_note = (
        "GOAL MODE is active: the user gave an objective instead of a one-line "
        "request, and you are expected to close the loop yourself — plan, split the "
        "objective into subtasks, edit the project source, run debug commands, test "
        "the result, and repeat until the objective is genuinely achieved (not just "
        "described). A goal state file is maintained for you; keep it truthful.\n"
        "Drive it with the goal tool, one block per update:\n"
        "```luas30-tool\n"
        '{"tool":"goal","args":{"op":"plan","steps":["Inspect the keypad template",'
        '"Fix the fresh-key guard in src/keypad.lua","Run luac -p on every changed file",'
        '"Verify the smoke test passes"]},"reason":"Split the objective into verifiable steps"}\n'
        "```\n"
        "ops: plan (args.steps, 1-12 short verifiable steps), start (args.step), "
        "done (args.step + args.verify — the command or check that PROVED it), "
        "fail (args.step + args.note), blocked (args.reason — you need the user), "
        "finish (objective achieved), status (read the current state back).\n"
        "Rules: call plan once, before your first edit. Mark a step done ONLY after "
        "a real check passed — a verification you did not run is not a verification. "
        "When a step fails and you cannot fix it in this turn, call fail, and call "
        "blocked when you need a decision from the user. Do not call finish while any "
        "step is still open or failed. Prefer several small verified steps over one "
        "large unverified claim."
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
        + project_scope_note + "\n" + skills_note + (("\n" + goal_note) if goal_mode else "")
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
        + (
            "\nGoal Mode: keep working through the step list until every step is done and "
            "verified, or until you call blocked/finish. Never end a turn with an open step "
            "and no next action — either take the next action or call blocked with the "
            "decision you need."
            if goal_mode
            else ""
        )
    )

