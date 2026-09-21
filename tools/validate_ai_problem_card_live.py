#!/usr/bin/env python3
"""validate_ai_problem_card_live.py — Thẻ lỗi PROBLEM trong Chat AI cập nhật REALTIME.

Chạy (script tự đặt offscreen):

    py -3.12 -u tools/validate_ai_problem_card_live.py

Trước đây mỗi lần áp code lại chèn MỘT thẻ "N lỗi cần sửa" TINH (snapshot), thẻ cũ
đứng im nên sau khi sửa xong người dùng không thấy trạng thái đổi. Nay Chat AI giữ
MỘT thẻ SỐNG: khớp theo CHỮ KÝ (severity + đường dẫn tương đối + thông điệp — KHÔNG
theo số dòng vì nó nhảy khi sửa). Lỗi biến mất -> '✓ Đã sửa' (gạch ngang); lỗi mới ->
thêm vào; hết sạch -> '✓ Đã sửa hết'. Làm tươi cả khi áp code (report_errors_after_change)
LẪN khi editor phát diagnostics_changed (main_window nối, có throttle 400ms).

Guard hai tầng: TĨNH (mắt xích view + main_window còn nguyên) + HÀNH VI offscreen
(dựng AIChatView thật, đổi bảng PROBLEMS giả định, khẳng định đếm lại + đã sửa + hết).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "studio"))

VIEW = ROOT / "studio" / "app" / "views" / "ai_chat_view.py"
MAIN = ROOT / "studio" / "app" / "vxpui" / "main_window.py"

FAILS: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label} {detail}", flush=True)
    if not ok:
        FAILS.append(label)


def check_static() -> None:
    print("-- A. tĩnh: mắt xích thẻ sống --", flush=True)
    view = VIEW.read_text(encoding="utf-8")
    for token in (
        "def _problem_row_sig(",
        "def has_problem_card(",
        "def refresh_problem_card(",
        "def _open_first_live_problem(",
        'self._live_problem_card = ""',
        '"resolved":',
        "Đã sửa hết",
        "đã sửa",
    ):
        check(f"view: còn {token}", token in view)
    check("view: report_errors_after_change dùng refresh_problem_card",
          re.search(r"def report_errors_after_change.*?refresh_problem_card\(auto_open=True\)",
                    view, re.DOTALL) is not None)
    check("view: chữ ký KHÔNG dùng số dòng",
          re.search(r"def _problem_row_sig.*?_line, _column", view, re.DOTALL) is not None)
    check("view: tool problems gọi refresh_problem_card",
          "if tool == \"problems\" and tone == \"success\":" in view
          and "self.refresh_problem_card()" in view)
    check("view: openfile anchor vẫn đọc rows theo idx",
          'x-luas30://openfile/{pb_id}:{idx}' in view)

    main = MAIN.read_text(encoding="utf-8")
    for token in (
        "def _refresh_ai_problem_card(",
        "self._ai_problem_timer",
        "if self.ai_chat.has_problem_card():",
        "self.ai_chat.refresh_problem_card()",
    ):
        check(f"main_window: còn {token}", token in main)
    # diagnostics_changed phải mồi cho timer (realtime khi gõ/sửa).
    check("main_window: _diagnostics_changed mồi timer realtime",
          re.search(r"def _diagnostics_changed.*?self\._ai_problem_timer\.start\(\)",
                    main, re.DOTALL) is not None)


def check_behavior() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
    import tempfile

    from PySide6.QtWidgets import QApplication

    from app.views.ai_chat_view import AIChatView

    print("-- B. hành vi offscreen: đếm lại + Đã sửa + hết sạch --", flush=True)
    app = QApplication.instance() or QApplication(sys.argv)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        chat = AIChatView(root)
        chat.show()
        app.processEvents()
        chat.set_project_root(root)

        state = {"rows": []}
        chat.set_problems_rows_provider(lambda: list(state["rows"]))
        opened: list[tuple] = []
        chat.set_open_location_provider(lambda p, l, c=1: opened.append((str(p), int(l))))

        def row(msg, path="main.lua", line=5, sev="error"):
            return (sev, root / path, line, 1, msg)

        check("chưa có lỗi: report trả False, không có thẻ",
              chat.report_errors_after_change() is False and chat.has_problem_card() is False)

        # Hai lỗi -> thẻ sống, 'còn 2 lỗi'
        state["rows"] = [row("undefined variable x"), row("missing end")]
        check("2 lỗi: report True", chat.report_errors_after_change() is True)
        check("2 lỗi: có thẻ sống", chat.has_problem_card() is True)
        check("2 lỗi: header 'còn 2 lỗi'", "còn 2 lỗi" in chat.transcript.toPlainText())
        first_card = chat._live_problem_card

        # Sửa 1 lỗi (dòng của lỗi còn lại nhảy 5->99) -> vẫn MỘT thẻ, 'đã sửa 1'
        state["rows"] = [row("missing end", line=99)]
        chat.refresh_problem_card()
        html = chat.transcript.toPlainText()
        check("sau sửa: VẪN một thẻ duy nhất", list(chat._problem_blocks.keys()) == [first_card])
        check("sau sửa: 'còn 1 lỗi' + '1 đã sửa'", "còn 1 lỗi" in html and "1 đã sửa" in html)
        check("sau sửa: dòng nhảy vẫn khớp theo signature (không tính 2 lần đã sửa)",
              "1 đã sửa" in html and "2 đã sửa" not in html)

        # Thêm lỗi mới -> gộp, 'còn 2 · 1 đã sửa'
        state["rows"] = [row("missing end", line=99), row("type mismatch")]
        chat.refresh_problem_card()
        html2 = chat.transcript.toPlainText()
        check("lỗi mới được thêm realtime", "còn 2 lỗi" in html2 and "1 đã sửa" in html2)

        # Hết sạch -> 'Đã sửa hết'
        state["rows"] = []
        chat.refresh_problem_card()
        check("hết lỗi: 'Đã sửa hết'", "Đã sửa hết" in chat.transcript.toPlainText())
        check("hết lỗi: refresh trả False", chat.refresh_problem_card() is False)

        # auto_open nhảy tới lỗi ĐẦU CÒN MỞ (bỏ qua mục đã sửa)
        state["rows"] = [row("boom", path="a.lua", line=7)]
        chat.report_errors_after_change()
        check("auto_open mở đúng lỗi đầu còn lại", bool(opened) and opened[-1][1] == 7)

        # Phiên mới xoá thẻ sống
        chat.new_chat()
        app.processEvents()
        check("new_chat hoàn nguyên thẻ sống", chat.has_problem_card() is False)

        chat.shutdown()


def main() -> int:
    check_static()
    try:
        check_behavior()
    except ImportError as exc:
        print(f"  [SKIP] bỏ phần hành vi: {exc}", flush=True)
    print("\n== KẾT QUẢ ==", flush=True)
    print("FAIL:", FAILS or "khong co", flush=True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
