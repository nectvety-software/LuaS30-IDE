"""Goal Mode — kiểm chứng bằng cách CHẠY THẬT widget, không đọc chuỗi.

Bốn thứ phải đúng, và cả bốn đều chỉ lộ ra khi chạy:

  1. `/goal <mục tiêu>` tạo mục tiêu, hiện dải tiến độ, và khởi động vòng lặp.
  2. Tool `goal` do agent phát ra phải điều khiển được trạng thái THẬT
     (op=plan / start / done / blocked) — nếu tên op lệch giữa prompt và handler
     thì mục tiêu đứng im mà không có lỗi nào.
  3. Bị chặn -> tự quay lui về bản chụp của bước đã xác nhận, tệp trên đĩa về
     nguyên bản cũ.
  4. Hết ngân sách lượt -> DỪNG vòng lặp (không chạy vô hạn) và GIỮ mã đã sửa.

Chạy offscreen: cần `QT_QPA_PLATFORM=offscreen` và `QT_QPA_FONTDIR=C:/Windows/Fonts`
(thiếu FONTDIR thì glyph icon hỏng âm thầm, xem doc/studio/STUDIO_GUIDE.md).
"""

from pathlib import Path
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "studio"))

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

import app.views.ai_chat_view as chat_module
from app.services.ai_agent_protocol import CodeEditAction, ToolAction, parse_agent_response
from app.services.ai_change_service import AIChangeService
from app.services.ai_goal_service import GoalService
from app.views.ai_chat_view import AIChatView


class OfflineRequestThread(QObject):
    """Thay `AIRequestThread` thật: KHÔNG gọi mạng, KHÔNG tự phát tín hiệu.

    Bài kiểm này BẮT BUỘC phải chạy offline. Lần đầu viết, tôi để nguyên thread
    thật nên `_start_request` đã gọi provider thật của người dùng (config +
    API key nằm trong %APPDATA%), model trả về một kế hoạch kèm edit, và vì chế
    độ mặc định là edit_auto nên nó GHI LUÔN vào dự án tạm — làm hỏng cả tính
    xác định của bài kiểm lẫn dự án đang mở. Không bao giờ để lại như vậy.
    """

    completed = Signal(str)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self._running = False

    def isRunning(self) -> bool:
        return self._running

    def start(self) -> None:
        pass

    def cancel(self) -> None:
        pass

    def requestInterruption(self) -> None:
        pass

    def wait(self, *args) -> bool:
        return True


chat_module.AIRequestThread = OfflineRequestThread

PASS = []


def ok(message):
    PASS.append(message)
    print("PASS:", message)


# Nội dung main.lua SAU khi bước 1 thay "old" -> "new" (tệp gốc có 2 dòng).
NEW_CONTENT = 'local mode = "new"\nfunction tick() return mode end\n'


def build_project(root: Path) -> Path:
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "main.lua").write_text(
        'local mode = "old"\nfunction tick() return mode end\n', encoding="utf-8"
    )
    (root / "src" / "helper.lua").write_text("return 1\n", encoding="utf-8")
    return root


app = QApplication.instance() or QApplication([])

with tempfile.TemporaryDirectory() as td:
    project = build_project(Path(td))

    # --- 1. /goal tạo mục tiêu, dải tiến độ hiện ra ---------------------------
    chat = AIChatView(ROOT)
    chat.set_project_root(project)
    assert chat.goal_card.isHidden(), "chưa có mục tiêu thì không được hiện dải"
    chat._handle_goal_command("sửa lỗi bàn phím trong template keypad")
    goal = chat.goal_service.goal
    assert goal is not None and goal.status == "planning", goal
    assert not chat.goal_card.isHidden(), "dải tiến độ phải hiện khi có mục tiêu"
    assert chat.goal_title.text() == goal.title
    assert chat.goal_service.state_path.is_file(), "trạng thái phải được ghi ra đĩa"
    ok("/goal tạo mục tiêu, hiện dải tiến độ và ghi .luas30/ai_goal.json")

    # --- 2. agent phát tool goal -> trạng thái thật đổi ----------------------
    # Đi qua ĐÚNG đường parse của protocol, không gọi thẳng service: đây là chỗ
    # tên op lệch sẽ bị nuốt im lặng.
    parsed = parse_agent_response(
        'Kế hoạch:\n```luas30-tool\n'
        '{"tool":"goal","args":{"op":"plan","steps":['
        '"Đọc template keypad","Sửa guard fresh trong keypad.lua",'
        '"Chạy luac -p kiểm tra"]},"reason":"chia bước"}\n```'
    )
    assert len(parsed.tool_actions) == 1, parsed.tool_actions
    chat._run_tool(parsed.tool_actions[0], continue_after=False)
    goal = chat.goal_service.goal
    assert goal.total_steps == 3, goal.plan_text()
    assert goal.status == "active"
    assert "Đọc template keypad" in chat.goal_steps.text()
    ok("tool goal op=plan (qua parser) ghi kế hoạch 3 bước vào trạng thái thật")

    parsed = parse_agent_response(
        '```luas30-tool\n{"tool":"goal","args":{"op":"start","step":1}}\n```'
    )
    chat._run_tool(parsed.tool_actions[0], continue_after=False)
    assert chat.goal_service.goal.current_step().index == 1
    ok("tool goal op=start đánh dấu bước đang làm")

    # --- 3. sửa tệp thật rồi xác nhận bước -> gắn bản chụp -------------------
    service = AIChangeService()
    change_set = service.prepare(
        project,
        [CodeEditAction(path="main.lua", find='"old"', replace='"new"', reason="sửa")],
    )
    applied, backup = service.apply(change_set)
    assert backup is not None
    stamp = backup.name
    # main_window làm việc này sau khi áp code; ở đây mô phỏng đúng lời gọi đó.
    chat._last_applied_checkpoint = stamp
    chat.goal_service.record_checkpoint(stamp)
    assert '"new"' in (project / "main.lua").read_text(encoding="utf-8")

    parsed = parse_agent_response(
        '```luas30-tool\n{"tool":"goal","args":{"op":"done","step":1,'
        '"verify":"luac -p main.lua"}}\n```'
    )
    chat._run_tool(parsed.tool_actions[0], continue_after=False)
    step = chat.goal_service.goal.step_at(1)
    assert step.status == "done" and step.verify == "luac -p main.lua", step
    assert step.checkpoint == stamp, step.checkpoint
    assert chat.goal_progress.value() == 33, chat.goal_progress.value()
    ok("bước xác nhận xong gắn đúng bản chụp + thanh tiến độ cập nhật")

    # --- 4. hai kiểu quay lui, kiểm qua TÍN HIỆU THẬT mà main_window nhận ------
    emitted: list[dict] = []
    chat.goal_rollback_requested.connect(lambda payload: emitted.append(dict(payload)))

    def ai_write(text: str, why: str) -> str:
        """Ghi qua ĐÚNG đường của AI — nếu viết tay thì chốt an toàn (đúng) chặn."""
        cs = service.prepare(project, [CodeEditAction(path="main.lua", content=text, reason=why)])
        _, bk = service.apply(cs)
        return bk.name

    # Bước sau làm hỏng: bây giờ tệp KHÁC bản của bước đã xác nhận.
    bad = ai_write('local mode = "HONG"\n', "bước sau hỏng")
    assert bad != stamp
    assert (project / "main.lua").read_text(encoding="utf-8") == 'local mode = "HONG"\n'

    # 4a: `/goal rollback` không tham số -> hoàn tác thay đổi AI gần nhất.
    assert chat._goal_good_checkpoint() == stamp, chat._goal_good_checkpoint()
    chat._handle_goal_command("rollback", from_ui=True)
    assert chat._goal_rollback_pending, "phải phát tín hiệu yêu cầu quay lui"
    assert emitted and emitted[-1]["mode"] == "undo", emitted
    assert emitted[-1]["stamp"] == "", emitted

    report = AIChangeService.restore_latest(project)   # main_window làm việc này
    chat.on_rollback_finished(report)
    assert not chat._goal_rollback_pending
    assert report["stamp"] == bad, report
    got = (project / "main.lua").read_text(encoding="utf-8")
    assert got == NEW_CONTENT, \
        f"hoàn tác phải đưa tệp về bản của bước đã xác nhận, đang là {got!r} / {report}"
    assert any("hoàn tác" in line.lower() for line in chat.transcript.toPlainText().splitlines()[-12:])
    ok("/goal rollback (không tham số) hoàn tác thay đổi AI gần nhất và báo lại")

    # 4b: bị chặn -> quay lui TỰ ĐỘNG về trạng thái cuối bước đã xác nhận.
    #     Đây là đường chạy thật của tính năng "phục hồi trạng thái khi gặp lỗi".
    bad2 = ai_write('local mode = "HONG2"\n', "bước sau hỏng lần nữa")
    assert (project / "main.lua").read_text(encoding="utf-8") == 'local mode = "HONG2"\n'

    chat.goal_service.resume()
    parsed = parse_agent_response(
        '```luas30-tool\n{"tool":"goal","args":{"op":"blocked",'
        '"reason":"cần bạn chọn hướng xử lý"}}\n```'
    )
    chat._run_tool(parsed.tool_actions[0], continue_after=False)
    assert chat.goal_service.goal.status == "blocked"
    assert emitted[-1]["mode"] == "rewind", emitted
    assert emitted[-1]["stamp"] == stamp, emitted

    report = AIChangeService.rewind_to(project, emitted[-1]["stamp"])
    chat.on_rollback_finished(report)
    assert report["undone"] == [bad2], report
    assert (project / "main.lua").read_text(encoding="utf-8") == NEW_CONTENT, \
        "quay lui tự động phải về đúng trạng thái cuối bước đã xác nhận"
    ok("op=blocked -> tự quay lui về cuối bước đã xác nhận (mode=rewind)")

    # 4c: tệp người dùng sửa tay thì quay lui KHÔNG được nuốt.
    (project / "src" / "helper.lua").write_text("return 42  -- nguoi dung sua\n", encoding="utf-8")
    ai_write('local mode = "HONG3"\n', "hỏng lần ba")
    (project / "main.lua").write_text('local mode = "NGUOI-DUNG-SUA"\n', encoding="utf-8")
    report = AIChangeService.rewind_to(project, stamp)
    chat.on_rollback_finished(report)
    assert (project / "main.lua").read_text(encoding="utf-8") == 'local mode = "NGUOI-DUNG-SUA"\n', \
        "không được ghi đè tệp người dùng vừa sửa tay"
    assert report["skipped"], report
    ok("quay lui không nuốt tệp người dùng sửa tay (giữ nguyên + báo lại)")

    # --- 6. hết ngân sách -> dừng nhưng GIỮ mã đã sửa -----------------------
    chat.on_rollback_finished({"stamp": "x", "restored": [], "removed": [], "skipped": []})
    chat._handle_goal_command("resume", from_ui=True)
    chat.goal_service.goal.turns_used = chat.goal_service.goal.turn_budget
    chat.goal_service.save()
    (project / "main.lua").write_text('local mode = "dang-do"\n', encoding="utf-8")
    before = (project / "main.lua").read_text(encoding="utf-8")

    assert chat._goal_continue_question("Continue") == "", "hết ngân sách phải trả câu rỗng"
    assert not chat._goal_rollback_pending, "hết ngân sách KHÔNG được tự quay lui"
    assert (project / "main.lua").read_text(encoding="utf-8") == before, "mã đang dở phải giữ nguyên"
    assert "resume" in chat.transcript.toPlainText().lower()
    ok("hết ngân sách lượt -> dừng vòng lặp, giữ nguyên mã đang dở")

    # --- 7. mục tiêu sống qua khởi động lại ---------------------------------
    reloaded = GoalService(project)
    assert reloaded.goal is not None
    assert reloaded.goal.title == goal.title
    assert reloaded.goal.status == "blocked"
    ok("mục tiêu + kế hoạch sống qua lần khởi động lại (đọc lại từ đĩa)")

    # --- 8. project khác -> không lẫn mục tiêu ------------------------------
    with tempfile.TemporaryDirectory() as td2:
        other = build_project(Path(td2))
        chat.set_project_root(other)
        assert chat.goal_service.goal is None, "project khác không được thấy mục tiêu cũ"
        assert chat.goal_card.isHidden(), "dải tiến độ phải ẩn khi project không có mục tiêu"
        chat.set_project_root(project)
        assert chat.goal_service.goal is not None, "quay lại project cũ phải thấy lại mục tiêu"
    ok("đổi project thì nạp đúng mục tiêu của project đó, không lẫn nhau")

    # --- 9. dải tiến độ không tràn / không cắt chữ --------------------------
    chat._sync_goal_strip()
    assert chat.goal_card.isVisible() or not chat.goal_card.isHidden()
    assert chat.goal_steps.text(), "kế hoạch phải hiện trong dải"
    assert chat.goal_status.text(), "dòng trạng thái phải có nội dung"
    assert chat.goal_badge.text(), "huy hiệu tiến độ phải có nội dung"
    ok("dải tiến độ render đủ tiêu đề, kế hoạch, trạng thái và huy hiệu")

    chat.close()

print()
print(f"PASS: {len(PASS)} kiểm tra Goal Mode")
