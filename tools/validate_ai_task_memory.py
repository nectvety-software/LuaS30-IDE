#!/usr/bin/env python3
"""validate_ai_task_memory.py — bộ nhớ công việc đang làm của AI Agent.

Người dùng yêu cầu: agent phải **code dài hơn** và **nhớ việc đang làm**. Hai thứ
đó chết cùng một kiểu — HỎNG IM LẶNG:

  * Trần hội thoại: `_start_request` từng gửi đúng `self._history[-16:]`, không tóm
    tắt gì. Phiên dài thì đầu phiên biến mất, và triệu chứng là agent hỏi lại đúng
    thứ vừa thống nhất xong — không exception, không log.
  * Không có bộ nhớ: đóng IDE, mở lại (hoặc /new) là mất sạch ngữ cảnh; agent làm
    lại từ đầu hoặc làm sai hướng.

Bài kiểm này soi bốn tầng:

  A. Hợp đồng tĩnh — tool `task` phải nằm trong `TOOL_NAMES` (quên là khối tool bị
     bỏ im lặng, 0 action), và `TASK_OPS` phải là thứ handler THẬT SỰ nhận.
  B. Dịch vụ thật trên thư mục tạm — ghi/đọc/xoá, bền qua khởi động lại, JSON
     nguyên tử, chịu được JSON hỏng, tách theo project, có trần.
  C. Prompt — khối `<task_memory>` có mặt, và biến mất khi không có project.
  D. Vòng lặp thật — gọi THẲNG `AIChatView._earlier_work_digest` và
     `AIChatView._nudge_unfinished_work` trên stub, để chứng minh thân hàm thật sự
     chạy chứ không chỉ "có chữ trong file".

Chạy:

    QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
        py -3.12 -u tools/validate_ai_task_memory.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import types
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "studio"
sys.path.insert(0, str(STUDIO))

# Dựng AIChatView THẬT ở phần E sẽ chạm tới config/dự án thật nếu không chuyển hướng.
# Phải đặt TRƯỚC khi nạp module, vì `config_dir()` đọc lúc gọi.
_SANDBOX = Path(tempfile.mkdtemp(prefix="luas30_taskmem_"))
os.environ.setdefault("LUAS30_APPDATA", str(_SANDBOX / "appdata"))
os.environ.setdefault("LUAS30_PROJECTS", str(_SANDBOX / "projects"))

errors: list[str] = []


def check(label: str, ok: bool) -> None:
    if not ok:
        errors.append(label)


# ------------------------------------------------------------------ import
try:
    from app.services.ai_agent_protocol import (
        TASK_OPS,
        TOOL_NAMES,
        agent_protocol_prompt,
        parse_agent_response,
    )
    from app.services.ai_task_memory import (
        MAX_FACTS,
        STATE_RELPATH,
        TaskMemory,
        TaskMemoryError,
    )
except Exception as exc:  # noqa: BLE001 - thiếu môi trường thì báo, đừng im
    print("FAIL")
    print(" -", f"không import được dịch vụ: {exc}")
    raise SystemExit(1)

try:
    from app.views.ai_chat_view import AIChatView
except Exception as exc:  # noqa: BLE001
    errors.append(f"không nạp được AIChatView để kiểm vòng lặp thật: {exc}")
    AIChatView = None  # type: ignore[assignment]

sandbox = _SANDBOX

# ------------------------------------------------ A. Hợp đồng tĩnh (protocol)
check("tool `task` KHÔNG có trong TOOL_NAMES (khối tool sẽ bị bỏ im lặng)",
      "task" in TOOL_NAMES)

block = (
    "```luas30-tool\n"
    '{"tool":"task","args":{"op":"next","text":"viết src/shop.lua"},'
    '"reason":"ghi việc kế tiếp"}\n'
    "```"
)
parsed = parse_agent_response(block)
check("khối luas30-tool gọi tool `task` bị parser nuốt mất",
      len(parsed.tool_actions) == 1)
check("parser trả về sai tool",
      bool(parsed.tool_actions) and parsed.tool_actions[0].tool == "task")
check("parser làm mất args của tool `task`",
      bool(parsed.tool_actions)
      and str((parsed.tool_actions[0].args or {}).get("text") or "") == "viết src/shop.lua")

for enabled, label in ((True, "bật"), (False, "tắt")):
    prompt = agent_protocol_prompt(shell_enabled=True, full_access=True, task_memory=enabled)
    has_note = "WORKING MEMORY (task tool)" in prompt
    check(f"task_memory={label} nhưng khối chỉ dẫn không {'có' if enabled else 'mất'}",
          has_note is enabled)
    if enabled:
        for op in TASK_OPS:
            check(f"prompt không nhắc op {op!r} nên model sẽ không bao giờ gọi",
                  op in prompt)

# ------------------------------------------------ B. Dịch vụ thật trên đĩa
root_a = sandbox / "project_a"
root_b = sandbox / "project_b"
root_a.mkdir(parents=True, exist_ok=True)
root_b.mkdir(parents=True, exist_ok=True)

mem = TaskMemory(root_a)
check("chưa có gì mà prompt_block() không rỗng", mem.prompt_block() == "")
check("chưa có gì mà should_continue() lại True", not mem.state.should_continue)
check("state file được tạo khi chưa ghi gì", not (root_a / STATE_RELPATH).is_file())

# Mọi op trong TASK_OPS phải ĐƯỢC handler nhận — đây là cặp prompt/handler từng
# lệch nhau ở Goal Mode (`step_done` vs `done`) làm mục tiêu đứng im.
for op in TASK_OPS:
    args: dict = {}
    if op == "objective":
        args = {"text": "Thêm màn hình shop; xong khi /run hiện ra và problems sạch"}
    elif op == "plan":
        args = {"steps": ["Đọc template", "Viết src/shop.lua", "Chạy luac -p", "Chạy /run"]}
    elif op == "step":
        args = {"step": 1, "state": "done"}
    elif op == "fact":
        args = {"text": "Template vẽ bằng rect() chứ không phải drawImage()"}
    elif op == "file":
        args = {"path": "src/shop.lua", "note": "màn hình mới"}
    elif op == "next":
        args = {"text": "Viết src/shop.lua rồi chạy luac -p"}
    elif op == "blocked":
        args = {"reason": "cần người dùng chọn vị trí nút"}
    elif op == "unblock":
        args = {"note": "người dùng đã chọn"}
    elif op == "done":
        args = {"verify": "luac -p sạch + /run đã chụp ảnh"}
    elif op == "reset":
        args = {"reason": "kiểm tra"}
    try:
        mem.handle_op(op, args)
    except TaskMemoryError as exc:
        errors.append(f"op {op!r} có trong TASK_OPS nhưng handler từ chối: {exc}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"op {op!r} làm handler nổ: {exc!r}")

# Sau `reset` (op cuối) thì sổ rỗng; dựng lại nội dung thật để kiểm phần còn lại.
mem.handle_op("reset", {"reason": ""})
mem.handle_op("objective", {"text": "Thêm màn hình shop; xong khi /run hiện ra"})
mem.handle_op("plan", {"steps": ["Đọc template", "Viết src/shop.lua", "Chạy luac -p"]})
mem.handle_op("step", {"step": 1, "state": "done"})
mem.handle_op("step", {"step": 2, "state": "doing"})
mem.handle_op("fact", {"text": "Dùng rect() chứ không phải drawImage()"})
mem.handle_op("file", {"path": "src/shop.lua", "note": "màn hình mới"})
mem.handle_op("next", {"text": "Viết src/shop.lua rồi chạy luac -p"})
mem.record_evidence("Lệnh đã chạy", "luac -p src/shop.lua → exit 0")

check("op objective không ghi được mục tiêu",
      "Thêm màn hình shop" in mem.state.objective)
check("op plan không ghi được bước", len(mem.state.steps) == 3)
check("op step không đánh dấu được bước", mem.state.done_steps == 1)
check("current_step không trỏ vào bước đang làm",
      bool(mem.state.current_step) and mem.state.current_step.index == 2)
check("op fact không ghi được ghi chú", len(mem.state.facts) == 1)
check("op file không ghi được tệp", len(mem.state.files) == 1)
check("bằng chứng quan sát được không vào sổ", len(mem.state.evidence) == 1)
check("should_continue phải True khi còn next + đang working",
      mem.state.should_continue)

# JSON phải hợp lệ SAU MỖI lần ghi (ghi nguyên tử, không để lại tệp cụt).
path_a = root_a / STATE_RELPATH
check("không thấy tệp trạng thái", path_a.is_file())
if path_a.is_file():
    try:
        payload = json.loads(path_a.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"tệp trạng thái không phải JSON hợp lệ: {exc}")
        payload = {}
    check("JSON thiếu khoá next", "next" in payload)
    check("JSON thiếu khoá steps", "steps" in payload)

# Bền qua khởi động lại: đây là điều kiện để "nhớ việc đang làm" có nghĩa.
reloaded = TaskMemory(root_a)
check("nạp lại mất mục tiêu", reloaded.state.objective == mem.state.objective)
check("nạp lại mất bước", len(reloaded.state.steps) == 3)
check("nạp lại mất ghi chú", len(reloaded.state.facts) == 1)
check("nạp lại mất việc kế tiếp", reloaded.state.next_action == mem.state.next_action)
check("nạp lại mất bằng chứng", len(reloaded.state.evidence) == 1)

prompt_block = reloaded.prompt_block()
for needle, label in (
    ("<task_memory>", "thiếu thẻ mở"),
    ("</task_memory>", "thiếu thẻ đóng"),
    ("Thêm màn hình shop", "thiếu mục tiêu"),
    ("[x] 1. Đọc template", "thiếu bước đã xong"),
    ("[>] 2. Viết src/shop.lua", "thiếu bước đang làm"),
    ("Dùng rect()", "thiếu ghi chú"),
    ("src/shop.lua", "thiếu tệp đã đụng"),
    ("Viết src/shop.lua rồi chạy luac -p", "thiếu việc kế tiếp"),
):
    check(f"prompt_block {label}", needle in prompt_block)

# Tách theo project: bộ nhớ của A KHÔNG được rò sang B.
other = TaskMemory(root_b)
check("bộ nhớ rò sang project khác", other.prompt_block() == "")
other.handle_op("objective", {"text": "việc của project B"})
check("đổi project mà vẫn đọc nhầm sổ cũ",
      "project B" in other.prompt_block() and "shop" not in other.prompt_block())

# `next` rỗng khi vẫn "working" là trạng thái NÓI DỐI -> phải tự hạ trạng thái,
# nếu không vòng lặp tự tiếp tục sẽ đuổi theo một việc không tồn tại.
mem.handle_op("next", {"text": ""})
check("xoá next mà vẫn giữ trạng thái working (sổ nói dối)",
      mem.state.status in {"done", "idle"})
check("xoá next rồi mà should_continue vẫn True", not mem.state.should_continue)

# `blocked` phải chặn vòng lặp tự chạy.
mem.handle_op("next", {"text": "làm tiếp"})
mem.handle_op("blocked", {"reason": "cần người dùng chọn vị trí nút"})
check("blocked không hạ trạng thái", mem.state.status == "blocked")
check("đang tắc mà vẫn đòi tự tiếp tục", not mem.state.should_continue)
check("lý do tắc không vào prompt", "cần người dùng chọn vị trí nút" in mem.prompt_block())
mem.handle_op("unblock", {"note": "người dùng đã chọn"})
check("gỡ tắc không quay lại working", mem.state.status == "working")

# op lạ phải bị từ chối TƯỜNG MINH, không im lặng bỏ qua.
try:
    mem.handle_op("step_done", {})
    errors.append("op lạ `step_done` được chấp nhận — đúng cái bẫy đã làm Goal Mode đứng im")
except TaskMemoryError:
    pass
except Exception as exc:  # noqa: BLE001
    errors.append(f"op lạ làm nổ sai kiểu: {exc!r}")

# Trần danh sách: ghi 200 ghi chú thì sổ không được phình vô hạn.
for i in range(200):
    mem.handle_op("fact", {"text": f"ghi chú số {i}"})
check(f"sổ không cắt ghi chú theo trần {MAX_FACTS}", len(mem.state.facts) <= MAX_FACTS)
check("cắt ghi chú sai đầu (phải giữ mới nhất)",
      any("199" in f for f in mem.state.facts))

# JSON hỏng do sửa tay: coi như rỗng nhưng KHÔNG được xoá tệp của người dùng.
broken_root = sandbox / "project_broken"
broken_root.mkdir(parents=True, exist_ok=True)
broken_path = broken_root / STATE_RELPATH
broken_path.parent.mkdir(parents=True, exist_ok=True)
broken_path.write_text('{"objective": "cụt', encoding="utf-8")
broken = TaskMemory(broken_root)
check("JSON hỏng làm nổ thay vì coi như rỗng", broken.prompt_block() == "")
check("JSON hỏng bị XOÁ MẤT (mất dữ liệu người dùng)", broken_path.is_file())

# Không có project: mọi thứ phải là no-op chứ không nổ.
detached = TaskMemory()
check("không có project mà prompt_block() không rỗng", detached.prompt_block() == "")
try:
    detached.handle_op("objective", {"text": "x"})
    errors.append("không có project mà vẫn ghi được sổ")
except TaskMemoryError:
    pass

# ------------------------------------- D. Vòng lặp thật (thân hàm của AIChatView)
if AIChatView is not None:

    class _DigestStub:
        """Đủ thuộc tính để thân hàm thật của AIChatView chạy được."""

        REPLAY_WINDOW = AIChatView.REPLAY_WINDOW
        DIGEST_MAX_CHARS = AIChatView.DIGEST_MAX_CHARS
        DIGEST_MAX_ROWS = AIChatView.DIGEST_MAX_ROWS

        def __init__(self, history: list[dict], goal_active: bool = False) -> None:
            self._history = history
            self.goal_service = types.SimpleNamespace(active=goal_active)

        def _replay_window(self) -> int:
            return self.REPLAY_WINDOW

    check("cửa sổ hội thoại vẫn là 16 cũ (mất mạch khi code dài)",
          AIChatView.REPLAY_WINDOW > 16)

    short = _DigestStub([{"role": "user", "content": f"câu {i}"} for i in range(5)])
    check("hội thoại ngắn mà vẫn sinh bản tóm tắt thừa",
          AIChatView._earlier_work_digest(short) == "")

    history = [{"role": "user", "content": "thống nhất dùng rect() thay drawImage()"}]
    history += [{"role": "assistant", "content": f"bước {i}"} for i in range(80)]
    history += [{"role": "user", "content": "câu mới nhất"}]
    long_stub = _DigestStub(history)
    digest = AIChatView._earlier_work_digest(long_stub)
    check("phiên dài KHÔNG sinh bản tóm tắt (đầu phiên biến mất im lặng)", bool(digest))
    check("bản tóm tắt thiếu thẻ <earlier_work>", "<earlier_work>" in digest)
    check("bản tóm tắt mất việc đã thống nhất ở đầu phiên",
          "rect()" in digest)
    check("bản tóm tắt không bị chặn trần ký tự",
          len(digest) <= AIChatView.DIGEST_MAX_CHARS + 600)

    class _NudgeStub:
        def __init__(self, memory, *, mode="edit_auto", goal_active=False) -> None:
            self.task_memory = memory
            self._task_nudge_used = False
            self._cancel_requested = False
            self._mode = mode
            self.goal_service = types.SimpleNamespace(active=goal_active)
            self.queued: list[str] = []
            self.notes: list[str] = []

        def current_access_mode(self) -> str:
            return self._mode

        def _queue_continue(self, question: str) -> None:
            self.queued.append(question)

        class _Activity:
            def __init__(self, sink) -> None:
                self._sink = sink

            def add(self, kind, text, tone="info") -> None:
                self._sink.append(text)

        @property
        def activity(self):  # noqa: ANN201 - stub
            return _NudgeStub._Activity(self.notes)

    work = TaskMemory(sandbox / "project_a")
    work.handle_op("next", {"text": "chạy luac -p src/shop.lua"})
    check("sổ đang dở việc mà should_continue lại False", work.state.should_continue)

    stub = _NudgeStub(work)
    first = AIChatView._nudge_unfinished_work(stub)
    check("sổ ghi còn việc mà agent dừng luôn (lỗi người dùng báo)", first is True)
    check("nhắc mà không nói rõ việc kế tiếp",
          bool(stub.queued) and "luac -p" in stub.queued[0])
    second = AIChatView._nudge_unfinished_work(stub)
    check("nhắc mãi không dừng (phải chỉ nhắc MỘT lần)", second is False)

    idle = TaskMemory(sandbox / "project_b")
    idle.handle_op("objective", {"text": "việc của project B"})
    check("sổ không có việc kế tiếp mà vẫn bị nhắc",
          AIChatView._nudge_unfinished_work(_NudgeStub(idle)) is False)
    check("Goal Mode đang chạy mà vẫn nhắc chồng (hai vòng lặp giành nhau)",
          AIChatView._nudge_unfinished_work(_NudgeStub(work, goal_active=True)) is False)
    check("plan mode mà vẫn tự đòi làm tiếp",
          AIChatView._nudge_unfinished_work(_NudgeStub(work, mode="plan")) is False)

    # Trần lượt: đủ rộng cho việc dài nhưng LUÔN có biên.
    source = (STUDIO / "app/views/ai_chat_view.py").read_text(encoding="utf-8")
    for token, label in (
        ("self.task_memory = TaskMemory()", "chưa gắn bộ nhớ công việc vào AIChatView"),
        ("self._attach_task_memory()", "đổi project không nạp lại bộ nhớ"),
        ("task_block = self.task_memory.prompt_block()", "system prompt thiếu khối bộ nhớ"),
        # Hai hàm dưới chỉ có ích nếu ĐƯỢC GỌI. Có thân hàm mà không ai gọi là bài
        # kiểm trang trí — đúng kiểu hỏng im lặng mà file này sinh ra để chặn.
        ("digest = self._earlier_work_digest()", "_earlier_work_digest() không được gọi"),
        ("+ digest", "bản tóm tắt không được nhồi vào prompt"),
        ("if self._nudge_unfinished_work():", "_nudge_unfinished_work() không được gọi"),
        ('if tool == "task":', "tool `task` không được định tuyến"),
        ("def _run_task_tool", "thiếu handler cho tool `task`"),
        ("self.task_memory.record_evidence(", "không tự ghi bằng chứng quan sát được"),
        ("def _handle_task_command", "thiếu lệnh /task"),
        ("self._history[-self._replay_window():]", "vẫn cắt hội thoại cứng"),
    ):
        check(label, token in source)

    # Trần lượt là thuộc tính INSTANCE (gán trong __init__) nên đọc từ nguồn, không
    # đọc được từ class. Đủ rộng cho việc dài nhưng LUÔN có biên.
    import re as _re

    limit_agent = _re.search(r"self\._max_agent_turns\s*=\s*(\d+)", source)
    limit_full = _re.search(r"self\._max_full_access_turns\s*=\s*(\d+)", source)
    check("không tìm thấy trần lượt của agent", bool(limit_agent))
    check("trần lượt không được nâng lên cho việc dài",
          bool(limit_agent) and bool(limit_full)
          and int(limit_agent.group(1)) >= 24 and int(limit_full.group(1)) >= 120)
    check("trần lượt bị bỏ hẳn (vòng lặp vô hạn)",
          bool(limit_agent) and int(limit_agent.group(1)) < 10_000)

# ------------------------------- E. Widget THẬT: prompt do AIChatView lắp ráp
# Phần D gọi thân hàm trên stub. Phần E dựng `AIChatView` THẬT trên project thật
# trong thư mục tạm rồi đọc system prompt THẬT — để chứng minh khối bộ nhớ thật sự
# đi tới model, chứ không chỉ tồn tại như một hàm không ai gọi.
try:
    from PySide6.QtWidgets import QApplication

    from app.views.ai_chat_view import AIChatView as _RealView

    app = QApplication.instance() or QApplication([])
    real_project = sandbox / "project_real"
    (real_project / ".luas30").mkdir(parents=True, exist_ok=True)
    (real_project / "main.lua").write_text("local e = engine\n", encoding="utf-8")

    view = _RealView(ROOT)
    view.set_project_root(real_project)
    check("set_project_root không gắn bộ nhớ vào project",
          view.task_memory.root == real_project.resolve())
    check("project mới mà prompt_block() không rỗng", view.task_memory.prompt_block() == "")

    view.task_memory.handle_op("objective", {"text": "Thêm màn hình shop"})
    view.task_memory.handle_op("plan", {"steps": ["Đọc template", "Viết shop.lua"]})
    view.task_memory.handle_op("next", {"text": "Viết shop.lua"})
    view._history = [{"role": "user", "content": "thống nhất dùng rect()"}] + [
        {"role": "assistant", "content": f"bước {i}"} for i in range(90)
    ]
    real_prompt = view._system_prompt("<codebase_context>…</codebase_context>")

    check("system prompt THẬT thiếu <task_memory>", "<task_memory>" in real_prompt)
    check("system prompt THẬT thiếu mục tiêu đang làm", "Thêm màn hình shop" in real_prompt)
    check("system prompt THẬT thiếu <earlier_work> (đầu phiên biến mất)",
          "<earlier_work>" in real_prompt)
    check("system prompt THẬT mất quyết định ở đầu phiên", "rect()" in real_prompt)
    check("system prompt THẬT thiếu chỉ dẫn tool `task`",
          "WORKING MEMORY (task tool)" in real_prompt)
    check("system prompt THẬT phình quá lớn", len(real_prompt) < 60_000)

    # Không có project: khối bộ nhớ phải BIẾN MẤT, không để lại rác.
    view.set_project_root(None)
    bare = view._system_prompt("<codebase_context>…</codebase_context>")
    check("không có project mà prompt vẫn có <task_memory>", "<task_memory>" not in bare)
except Exception as exc:  # noqa: BLE001 - thiếu Qt thì báo, đừng im
    errors.append(f"không dựng được AIChatView thật để kiểm prompt: {exc!r}")

if errors:
    print("FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("PASS: tool `task` nằm trong TOOL_NAMES, parse được, và TASK_OPS khớp handler")
print("PASS: bộ nhớ ghi/đọc/xoá đúng, bền qua khởi động lại, JSON nguyên tử, tách theo project")
print("PASS: JSON hỏng được coi như rỗng nhưng KHÔNG bị xoá")
print("PASS: prompt luôn có <task_memory>; phiên dài có <earlier_work> thay vì cắt im lặng")
print("PASS: agent định dừng khi sổ còn việc thì được nhắc đúng MỘT lần")
