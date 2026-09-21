#!/usr/bin/env python3
"""validate_ai_fenced_files.py — Ép code fenced trong chat thành TỆP DỰ ÁN (kiểu Codex).

Chạy (không cần Qt, không cần biến môi trường):

    py -3.12 -u tools/validate_ai_fenced_files.py

Nguyên tắc được guard: LuaS30-IDE chỉ là trình soạn thảo + biên dịch + launcher
giả lập; "codebase" mà AI ghi code vào là PROJECT ĐANG MỞ, không bao giờ là thư
mục cài đặt IDE. Khi model BỎ QUA protocol `luas30-edit` và chỉ dán nguồn trong
một khối Markdown fence bình thường, IDE vẫn phải biến khối đó thành tệp THẬT
trong project (kể cả TỆP MỚI) — nhưng chỉ khi info-string của fence KHAI BÁO
đường dẫn (```lua path=src/menu.lua``` hoặc bare ```src/menu.lua). Đường dẫn
vẫn bị giam trong project bởi AIChangeService._safe_target.

Hai tầng: TĨNH (hàm/regex/prompt/messoge còn nguyên) + HÀNH VI (parser thật và
AIChangeService ghi/thật sự tạo tệp trong tmp project, đồng thời chặn escape).
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "studio"))

PROTOCOL = ROOT / "studio" / "app" / "services" / "ai_agent_protocol.py"
VIEW = ROOT / "studio" / "app" / "views" / "ai_chat_view.py"
SERVICE = ROOT / "studio" / "app" / "services" / "ai_change_service.py"

FAILS: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label} {detail}", flush=True)
    if not ok:
        FAILS.append(label)


def check_static() -> None:
    print("-- A. tĩnh: mắt xích phục hồi fenced -> tệp --", flush=True)
    proto = PROTOCOL.read_text(encoding="utf-8")
    for token in (
        "def _extract_fenced_path(",
        "def _recover_fenced_files(",
        "FENCE_PATH_ATTR_RE = re.compile(",
        "FENCE_ALLOWED_SUFFIXES = frozenset(",
    ):
        check(f"protocol: còn {token}", token in proto)
    check(
        "protocol: parse_agent_response gọi _recover_fenced_files",
        "recovered_files, files_visible = _recover_fenced_files(raw)" in proto,
    )
    # Đã có khối luas30-edit thì KHÔNG phục hồi chồng lặp.
    check(
        "protocol: recovery chỉ chạy khi chưa có edits",
        re.search(r"if allow_plain_code_edit and not edits:", proto) is not None,
    )
    check(
        "protocol: prompt dạy model đặt path trong fence",
        "path=src/menu.lua" in proto and "project-relative path in the fence header" in proto,
    )
    # Confinement: function phải chặn tuyệt đối/ổ đĩa/.. trước cả _safe_target.
    check("protocol: chặn .. trong _extract_fenced_path", '".." in candidate.split' in proto)
    check("protocol: chặn đường dẫn ổ đĩa", 're.match(r"^[A-Za-z]:"' in proto)

    view = VIEW.read_text(encoding="utf-8")
    check(
        "view: message phục hồi dùng code_edits (không hard-code active)",
        "Đã chuyển code sinh trong chat thành thay đổi cho" in view,
    )

    service = SERVICE.read_text(encoding="utf-8")
    check("service: _safe_target vẫn giam writes vào project", "escaped the project root" in service)


def check_behavior() -> None:
    print("-- B. hành vi: parser + ghi tệp thật --", flush=True)
    from app.services.ai_agent_protocol import (
        _extract_fenced_path,
        parse_agent_response,
    )

    F = "`" * 3

    # 1. fence khai báo TỆP MỚI (không có active file) -> tạo đúng tệp đó.
    raw = (
        "đây là module:\n"
        + F
        + "lua path=src/menu.lua\nlocal M = {}\nfunction M.new() return 1 end\nreturn M\n"
        + F
        + "\nxong."
    )
    p = parse_agent_response(raw, active_path="", user_request="tạo module menu",
                             allow_plain_code_edit=True)
    check("CASE1: tạo tệp mới từ fence path=", [e.path for e in p.code_edits] == ["src/menu.lua"])
    check("CASE1: giữ nguyên nội dung code",
          bool(p.code_edits) and "function M.new() return 1 end" in (p.code_edits[0].content or ""))
    check("CASE1: code không còn nằm lại trong chat", "function M.new" not in p.visible_text)
    check("CASE1: cờ recovered_plain_edit bật", p.recovered_plain_edit is True)

    # 2. bare-path header.
    p2 = parse_agent_response(F + "src/conf.lua\nreturn {w=240}\n" + F,
                              active_path="", user_request="add config",
                              allow_plain_code_edit=True)
    check("CASE2: bare path header hoạt động", [e.path for e in p2.code_edits] == ["src/conf.lua"])

    # 3. chỉ ngôn ngữ (```lua) + active file -> rơi về phục hồi tệp đang mở.
    p3 = parse_agent_response(F + "lua\n" + ("print(1)\n" * 30) + F,
                              active_path="main.lua", active_text="x\n" * 30,
                              user_request="viết lại main.lua", allow_plain_code_edit=True)
    check("CASE3: language-only + active -> active-file fallback",
          [e.path for e in p3.code_edits] == ["main.lua"])

    # 4. snippet nhỏ, không path, không active -> KHÔNG bịa ra tệp.
    p4 = parse_agent_response(F + "lua\nprint(1)\n" + F, active_path="",
                              user_request="cho tôi ví dụ code", allow_plain_code_edit=True)
    check("CASE4: snippet ngắn không path -> không ghi tệp", len(p4.code_edits) == 0)

    # 5. khối luas30-edit thắng; fenced recovery không chồng lặp.
    raw5 = (F + 'luas30-edit\n{"path":"a.lua","content":"print(1)\\n"}\n' + F
            + "\n\n" + F + "lua path=b.lua\nx\n" + F)
    p5 = parse_agent_response(raw5, user_request="sửa code", allow_plain_code_edit=True)
    check("CASE5: luas30-edit được ưu tiên, recovery bỏ qua",
          [e.path for e in p5.code_edits] == ["a.lua"] and p5.recovered_plain_edit is False)

    # 6. tắt chỉnh sửa -> không phục hồi.
    p6 = parse_agent_response(raw, user_request="tạo file", allow_plain_code_edit=False)
    check("CASE6: edit disabled -> không ghi gì", len(p6.code_edits) == 0)

    # 7. chặn escape ngay ở _extract_fenced_path.
    for bad in ("lua path=/etc/passwd", "lua path=../../secret.lua",
                "lua path=C:/Windows/x.lua", "lua path=tool.bin", "lua"):
        check(f"escape/ngôn ngữ bị chặn: {bad!r}", _extract_fenced_path(bad) == "")

    # 7b. DẠNG SCREENSHOT: directive nằm ở DÒNG ĐẦU TIÊN của body (```lua\n
    #     path=src/menu.lua\n<code>), không phải trên info-string.
    raw_line = (F + "lua\npath=src/menu.lua\nlocal Menu = {}\nreturn Menu\n" + F)
    pl = parse_agent_response(raw_line, active_path="", user_request="tạo module src/menu.lua",
                              allow_plain_code_edit=True)
    check("CASE7b: path ở dòng đầu body -> tạo tệp",
          [e.path for e in pl.code_edits] == ["src/menu.lua"])
    check("CASE7b: dòng path= bị gỡ khỏi nội dung",
          bool(pl.code_edits) and (pl.code_edits[0].content or "").startswith("local Menu")
          and "path=" not in (pl.code_edits[0].content or ""))
    # biến thể file= và không phải đường dẫn (code thật) không bị nhầm.
    raw_code = F + "lua\nlocal path = require('x.lua')\nprint(path)\n" + F
    pc = parse_agent_response(raw_code, active_path="", user_request="code",
                              allow_plain_code_edit=True)
    check("CASE7b: dòng code có chữ path= KHÔNG bị coi là directive", len(pc.code_edits) == 0)

    # 8. END-TO-END: phục hồi rồi prepare/apply TẠO TỆP TRONG PROJECT; escape bị chặn.
    from app.services.ai_change_service import AIChangeService
    from app.services.ai_agent_protocol import CodeEditAction

    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        svc = AIChangeService()
        # apply recovered new file
        cs = svc.prepare(project, list(p.code_edits))
        paths, _backup = svc.apply(cs)
        made = (project / "src" / "menu.lua")
        check("E2E: tệp mới được ghi vào trong project", made.is_file())
        check("E2E: nội dung khớp",
              made.is_file() and "function M.new" in made.read_text(encoding="utf-8"))
        # escape phải fatal, không ghi ra ngoài
        escaped = False
        try:
            svc.prepare(project, [CodeEditAction(path="../outside.lua", content="x\n")])
        except Exception:
            escaped = True
        check("E2E: path thoát khỏi project bị chặn (fatal)", escaped)
        check("E2E: không tạo tệp ngoài project", not (project.parent / "outside.lua").exists())


def main() -> int:
    check_static()
    check_behavior()
    print("\n== KẾT QUẢ ==", flush=True)
    print("FAIL:", FAILS or "khong co", flush=True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
