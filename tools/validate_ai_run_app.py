#!/usr/bin/env python3
"""validate_ai_run_app.py — Chat AI chạy thử game/app (build + VXPEmu + ảnh khói).

Chạy (script tự đặt `offscreen`, không cần biến môi trường):

    py -3.12 -u tools/validate_ai_run_app.py

Tính năng cần guard: người dùng (qua `/run` / nút quick-action) HOẶC AI Agent
(qua tool `run_app`) có thể build project đang mở rồi chạy nó trên VXPEmu ở chế
độ screen-only và chụp một ảnh "smoke" để kiểm chứng app thật sự chạy. Đây là
chuỗi BẤT ĐỒNG BỘ đi qua 4 tệp, rất dễ đứt ở một mắt nào đó mà không ai nhìn thấy:

  1. Protocol phải ĐĂNG KÝ tool `run_app` và DẠY model cách phát khối
     ```luas30-tool{"tool":"run_app"...}``` — nếu thiếu, model không bao giờ gọi.
  2. AIChatView phải có đường async: request → giữ nút "đang làm việc" → kết quả
     về qua on_run_app_finished (in dòng lỗi nếu fail, rồi mới hoàn nguyên nút).
  3. MainWindow phải NỐI callback và dựng pipeline build → launch → settle →
     capture → report, kèm các nhánh lỗi (build fail / emu chết trước khi chụp).
  4. VxpEmuWindow phải có capture_to_file trả về đường dẫn để làm bằng chứng.

Guard kiểm hai tầng: TĨNH (đủ 4 mắt xích còn nguyên) và HÀNH VI (dựng AIChatView
thật, nối callback giả, chạy cả hai đường `/run` và tool `run_app`, khẳng định
nút giữ trạng thái làm việc khi đang chờ và hoàn nguyên khi có kết quả).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "studio"))

PROTOCOL = ROOT / "studio" / "app" / "services" / "ai_agent_protocol.py"
VIEW = ROOT / "studio" / "app" / "views" / "ai_chat_view.py"
MAIN = ROOT / "studio" / "app" / "vxpui" / "main_window.py"
EMU = ROOT / "studio" / "app" / "widgets" / "vxp_emu_window.py"

FAILS: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label} {detail}", flush=True)
    if not ok:
        FAILS.append(label)


def check_static() -> None:
    print("-- A. tĩnh: 4 mắt xích của chuỗi run/test --", flush=True)

    proto = PROTOCOL.read_text(encoding="utf-8")
    check('protocol: run_app nằm trong WORKBENCH_TOOL_NAMES',
          re.search(r'WORKBENCH_TOOL_NAMES\s*=\s*\([^)]*"run_app"', proto) is not None)
    check('protocol: prompt dạy model phát tool run_app',
          '"tool":"run_app"' in proto and "Run/test tool" in proto)
    check('protocol: dạy cả op stop', 'op "stop"' in proto)

    view = VIEW.read_text(encoding="utf-8")
    for token in (
        "def set_run_app(",
        "def set_run_app_stopper(",
        "def request_run_app(",
        "def on_run_app_finished(",
        'tool == "run_app"',
        '"/run"',
        '("Chạy thử game/app", "run", "/run")',
        "self._awaiting_run_app",
    ):
        check(f"view: còn {token}", token in view)
    # Plan mode cấm chạy; không có project thì phải in dòng lỗi (không treo nút).
    check("view: request_run_app chặn Plan mode",
          'current_access_mode() == "plan"' in view)
    check("view: hoàn nguyên nút khi pipeline fail",
          view.count("self._set_agent_active(False)") >= 3)

    main = MAIN.read_text(encoding="utf-8")
    for token in (
        "def _run_and_capture_app(",
        "def _stop_ai_run_app(",
        "def _ai_capture_and_report(",
        "def _report_ai_run(",
        "ai_chat.set_run_app(self._run_and_capture_app)",
        "ai_chat.set_run_app_stopper(self._stop_ai_run_app)",
        "self.runner.run(Path(project))",
        "QTimer.singleShot(2600, self._ai_capture_and_report)",
        ".on_run_app_finished(",
    ):
        check(f"main_window: còn {token}", token in main)
    # Nhánh lỗi phải có: build fail và emu dừng trước khi chụp.
    check("main_window: báo lỗi khi build fail",
          re.search(r"self\._ai_run_active and not success", main) is not None)
    check("main_window: báo lỗi khi giả lập dừng sớm",
          "Giả lập dừng trước khi kịp chụp" in main)

    emu = EMU.read_text(encoding="utf-8")
    check("vxp_emu_window: có capture_to_file trả bool",
          "def capture_to_file(" in emu)


def check_behavior() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

    import tempfile

    from PySide6.QtWidgets import QApplication

    from app.services.ai_agent_protocol import ToolAction
    from app.views.ai_chat_view import AIChatView

    print("-- B. hành vi offscreen: giữ nút khi chờ, hoàn nguyên khi có kết quả --", flush=True)
    app = QApplication.instance() or QApplication(sys.argv)

    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)

        chat = AIChatView(ROOT)
        chat.show()                       # offscreen: cần ancestor hiện để isVisible thật
        app.processEvents()
        chat.set_project_root(project)
        chat._set_access_mode("edit_auto")

        continues: list[str] = []
        requests: list[str] = []
        chat._queue_continue = lambda q="", **k: continues.append(str(q))  # type: ignore
        chat._start_request = lambda q="", **k: requests.append(str(q))     # type: ignore

        # ---- Đường 1: người dùng gõ /run (continue_agent=False) ----
        started: dict[str, str] = {}

        def fake_run(reason: str) -> bool:
            started["reason"] = reason
            return True

        chat.set_run_app(fake_run)
        chat.prompt.setPlainText("/run")
        chat.send()
        app.processEvents()

        check("/run gọi đúng callback pipeline", "reason" in started, str(started))
        check("khi đang chờ: nút giữ trạng thái làm việc", chat._agent_active is True)
        check("khi đang chờ: cờ awaiting bật", chat._awaiting_run_app is True)
        check("/run KHÔNG bắn request provider (không vào model)", requests == [])

        shot = project / "build" / "smoke" / "run-test.png"
        chat.on_run_app_finished(True, "Đã build và chạy game/app trên VXPEmu", str(shot))
        app.processEvents()

        html = chat.transcript.toHtml()
        check("kết quả /run hiện trong transcript", "chạy game/app" in html)
        check("đường dẫn ảnh chụp được ghi ra", shot.name in html)
        check("sau khi xong (user path): hoàn nguyên nút", chat._agent_active is False)
        check("user path KHÔNG tự continue vào model", continues == [])

        # ---- Đường 2: AI Agent phát tool run_app (continue_agent=True) ----
        continues.clear()
        started.clear()
        chat.set_run_app(lambda reason: True)
        chat._run_tools([ToolAction(tool="run_app", args={"op": "run"},
                                    reason="smoke")], continue_after=True)
        app.processEvents()
        check("tool run_app giữ nút làm việc khi chờ", chat._agent_active is True)
        check("tool run_app defer: chưa continue ngay", continues == [])

        chat.on_run_app_finished(True, "App chạyOK", "")
        app.processEvents()
        check("tool run_app xong: đưa kết quả về cho agent (continue)",
              any("Continue" in c or "run" in c.lower() for c in continues), str(continues))
        check("continue-agent path: nút vẫn đang làm việc (do _queue_continue bật)",
              chat._agent_active is True)

        # ---- Đường 3: lỗi pipeline phải in DÒNG LỖI đỏ + hoàn nguyên nút ----
        continues.clear()
        chat.set_run_app(lambda reason: True)
        chat.request_run_app("x", continue_agent=True)
        app.processEvents()
        chat.on_run_app_finished(False, "Giả lập dừng trước khi kịp chụp ảnh", "")
        app.processEvents()
        err = chat.transcript.toHtml()
        check("khi fail: có dòng lỗi (màu đỏ)", "Lỗi" in err and "dừng trước khi kịp" in err)
        check("khi fail: KHÔNG continue vào model", continues == [])
        check("khi fail: hoàn nguyên nút", chat._agent_active is False)

        # ---- Đường 4: Plan mode không được chạy build/giả lập ----
        chat._set_access_mode("plan")
        calls: list[str] = []
        chat.set_run_app(lambda reason: calls.append("ran") or True)
        ok = chat.request_run_app("try", continue_agent=False)
        app.processEvents()
        check("Plan mode: từ chối chạy", ok is False and calls == [])

        # ---- Đường 5: chưa có callback thì báo lỗi, không treo nút ----
        chat._set_access_mode("full")
        chat2 = AIChatView(ROOT)
        chat2.show()
        app.processEvents()
        chat2.set_project_root(project)
        chat2._set_access_mode("full")
        ok2 = chat2.request_run_app("try", continue_agent=False)
        app.processEvents()
        check("thiếu callback: request trả False", ok2 is False)
        check("thiếu callback: nút không kẹt làm việc", chat2._agent_active is False)

        chat.shutdown()
        chat2.shutdown()


def main() -> int:
    check_static()
    try:
        check_behavior()
    except ImportError as exc:
        print(f"  [SKIP] bỏ phần hành vi: {exc}", flush=True)

    print("\n== KẾT QUẢ ==", flush=True)
    # Đừng in "FAIL: khong co" khi mọi thứ đạt — đọc log sẽ tưởng hỏng.
    if FAILS:
        print(f"FAIL: {len(FAILS)} mục", flush=True)
        for item in FAILS:
            print("  -", item, flush=True)
    else:
        print("PASS: khong co loi", flush=True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
