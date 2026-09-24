#!/usr/bin/env python3
"""validate_task_chip_dismiss.py — chip tác vụ: đóng được bằng X, và TẮT khi hết việc.

Lỗi người dùng báo (lần 1): chạy Run → build xong, VXPEmu mở; đóng cửa sổ giả lập
thì chip "Lua → VXP • <dự án>" vẫn nằm trên header và bấm X không có gì xảy ra.

Hai nguyên nhân, cả hai đều HỎNG IM LẶNG (không exception, không log):

  1. `LuaRunner._on_build_finished` `return` sớm khi `post_action == "vxpemu"` nên
     KHÔNG phát `finished` → `MainWindow._on_runner_finished` (nơi duy nhất gọi
     `task_progress.finish`) không bao giờ chạy cho tác vụ Run.
  2. Nút X chỉ phát `cancel_requested` → `runner.stop()` → `build_service.cancel()`;
     lúc đó build đã xong nên `cancel()` no-op ⇒ chip kẹt vĩnh viễn.

Lỗi người dùng báo (lần 2): tắt giả lập xong mà thông báo đó vẫn còn. Hợp đồng chốt
lại: `_on_vxpemu_stopped(0)` ⇒ `dismiss()` — tắt HẲN, không nán lại. Nhưng mã thoát
khác 0 thì vẫn phải `finish(False, ...)` và HIỆN, vì ẩn đi là giấu mất sự cố.

Chạy:

    QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
        py -3.12 -u tools/validate_task_chip_dismiss.py

Chỉ dựng `BottomTaskProgress` thật trên nền offscreen + runner giả — KHÔNG dựng
`MainWindow`, nên không đụng config thật và không chạy build/giả lập nào.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "studio"
sys.path.insert(0, str(STUDIO))

errors: list[str] = []

# --------------------------------------------------------------- A. Hợp đồng tĩnh
chip_src = (STUDIO / "app/vxpui/task_progress.py").read_text(encoding="utf-8")
main_src = (STUDIO / "app/vxpui/main_window.py").read_text(encoding="utf-8")
runner_src = (STUDIO / "app/vxpui/lua_runner.py").read_text(encoding="utf-8")

for token in (
    "cancel_button.clicked.connect(self._on_cancel_clicked)",
    "def _on_cancel_clicked",
    "def dismiss",
    "def is_active",
    "def set_cancel_hint",
    "self._active = False",
):
    if token not in chip_src:
        errors.append(f"task_progress.py thiếu hợp đồng đóng chip: {token!r}")

for name, token in (
    ("_on_vxpemu_stopped", "task_progress.dismiss("),
    ("_on_vxpemu_stopped", "task_progress.finish("),
    ("_on_vxpemu_started", "task_progress.set_phase("),
    ("_on_vxpemu_started", "set_cancel_hint("),
):
    start = main_src.find(f"def {name}")
    if start == -1:
        errors.append(f"main_window.py không còn {name}()")
        continue
    block = main_src[start:main_src.find("\n    def ", start + 1)]
    if token not in block:
        errors.append(f"{name}() phải chốt chip tác vụ ({token!r})")

# Bẫy gốc vẫn còn: Run mở VXPEmu thì `finished` không được phát ⇒ móc ở
# `_on_vxpemu_stopped` là bắt buộc, đừng xoá nhầm thành "code chết".
if 'self._post_action == "vxpemu" and not self._stopping' not in runner_src:
    errors.append("lua_runner.py: nhánh Run->VXPEmu đã đổi, xem lại móc chốt chip")

# ------------------------------------------------------------ B. Hành vi thật
# Chạy cả khi phần tĩnh đã FAIL: bài kiểm hành vi phải tự bắt được lỗi, không
# được "mượn" kết luận của phần tĩnh.
try:
    from PySide6.QtWidgets import QApplication, QWidget

    from app.vxpui.task_progress import BottomTaskProgress
except Exception as exc:  # noqa: BLE001 - báo rõ thiếu môi trường Qt
    errors.append(f"không dựng được chip tác vụ ngoài màn hình: {exc}")
    QApplication = None  # type: ignore[assignment]

if QApplication is not None:
    app = QApplication.instance() or QApplication([])

    class FakeRunner:
        """Giống LuaRunner: stop() chỉ làm gì đó khi build còn chạy."""

        def __init__(self) -> None:
            self.build_active = False
            self.calls = 0

        def stop(self) -> None:
            self.calls += 1
            if not self.build_active:
                return  # build_service.cancel() no-op, không phát tín hiệu nào

    host = QWidget()
    host.resize(1200, 700)
    host.show()

    chip = BottomTaskProgress(host)
    chip.attach_to_host(host)
    runner = FakeRunner()
    chip.cancel_requested.connect(runner.stop)

    title = "Lua → VXP • SouthernCardRush-v0.3.2"

    def check(label: str, ok: bool) -> None:
        if not ok:
            errors.append(label)

    def active() -> bool:
        # getattr: bản cũ không có is_active() — bài kiểm vẫn phải chạy hết để
        # liệt kê đủ lỗi thay vì nổ AttributeError giữa đường.
        probe = getattr(chip, "is_active", None)
        return bool(probe()) if callable(probe) else False

    # 1. Tác vụ chạy -> chip hiện.
    chip.begin(title)
    app.processEvents()
    check("begin() không hiện chip", chip.isVisible())
    check("begin() không đánh dấu tác vụ đang chạy", active())

    # 2. Bấm X khi không còn gì để huỷ (đúng cảnh trong ảnh) -> phải đóng.
    chip.cancel_button.click()
    app.processEvents()
    check("bấm X mà chip không đóng (lỗi người dùng báo)", not chip.isVisible())
    check("bấm X khi tác vụ đang chạy không phát cancel_requested", runner.calls == 1)

    # 3. Xong việc: X vẫn bấm được và đóng ngay, không phải chờ hẹn giờ tự ẩn.
    chip.begin(title)
    chip.finish(True, "Đã dừng giả lập")
    app.processEvents()
    check("finish() khoá nút X (X phải luôn đóng được)", chip.cancel_button.isEnabled())
    check("finish() không hẹn giờ tự ẩn", chip._hide_timer.isActive())
    check("hẹn giờ tự ẩn quá ngắn", chip._hide_timer.interval() >= 1000)
    chip.cancel_button.click()
    app.processEvents()
    check("sau finish() bấm X không đóng chip", not chip.isVisible())
    check("tác vụ đã xong mà vẫn phát cancel_requested", runner.calls == 1)

    # 4. Hẹn giờ tự ẩn vẫn hoạt động khi người dùng không bấm gì.
    chip.begin(title)
    chip.finish(False, "Giả lập lỗi")
    chip._hide_timer.timeout.emit()
    app.processEvents()
    check("hết hẹn giờ mà chip không tự ẩn", not chip.isVisible())

    # 5. Chip không được chết hẳn sau khi bị đóng.
    chip.begin(title)
    app.processEvents()
    check("begin() sau khi đóng không hiện lại chip", chip.isVisible())
    check("begin() sau khi đóng không bật lại nút X", chip.cancel_button.isEnabled())
    check("begin() sau khi đóng vẫn giữ trạng thái cũ", active())

    # ------------------------------------------- C. Móc thật của MainWindow
    # Gọi thẳng `MainWindow._on_vxpemu_stopped` trên một stub: đây là móc chốt chip
    # cho tác vụ Run, phải chứng minh nó thật sự chốt chứ không chỉ "có chữ trong file".
    import tempfile
    import types

    sandbox = Path(tempfile.mkdtemp(prefix="luas30_chip_"))
    os.environ.setdefault("LUAS30_APPDATA", str(sandbox / "appdata"))
    os.environ.setdefault("LUAS30_PROJECTS", str(sandbox / "projects"))
    try:
        from app.vxpui.main_window import VxpMainWindow as MainWindow
    except Exception as exc:  # noqa: BLE001 - thiếu môi trường thì báo, không im
        errors.append(f"không nạp được MainWindow để kiểm móc chốt chip: {exc}")
        MainWindow = None  # type: ignore[assignment]

    if MainWindow is not None:

        class _Panel:
            code = -1
            started: tuple[str, int] | None = None

            def process_stopped(self, code: int) -> None:
                self.code = code

            def process_started(self, artifact: str, pid: int) -> None:
                self.started = (artifact, pid)

        class _Stub:
            def _set_console_visible(self, _visible: bool) -> None:
                pass

        def stub_for(runner_running: bool) -> object:
            stub = _Stub()
            stub.vxpemu_panel = _Panel()
            stub.bottom = types.SimpleNamespace(setCurrentWidget=lambda _w: None)
            stub._vxp_emu_window = None
            stub._ai_run_active = False
            stub._ai_run_started = False
            stub._ai_run_reported = True
            stub._project_meta = {}
            stub.task_progress = BottomTaskProgress(host)
            stub.task_progress.attach_to_host(host)
            stub.task_progress.begin(title)
            stub.runner = types.SimpleNamespace(is_running=runner_running)
            return stub

        # Tắt giả lập: build đã dừng, VXPEmu vừa tắt -> thông báo tác vụ phải TẮT
        # HẲN theo, không nán lại trên header (lỗi người dùng báo).
        stub = stub_for(runner_running=False)
        check("chip chưa hiện trước khi tắt giả lập", stub.task_progress.isVisible())
        MainWindow._on_vxpemu_stopped(stub, 0)
        app.processEvents()
        check("tắt giả lập mà chip vẫn nằm trên header (lỗi người dùng báo)",
              not stub.task_progress.isVisible())
        check("tắt giả lập mà chip vẫn 'đang chạy'",
              not stub.task_progress.is_active())
        check("tắt giả lập mà chip vẫn hẹn giờ nán lại",
              not stub.task_progress._hide_timer.isActive())

        # Lỗi khởi động KHÁC tắt bình thường: phải hiện, ẩn đi là giấu mất sự cố.
        stub_err = stub_for(runner_running=False)
        MainWindow._on_vxpemu_stopped(stub_err, 1)
        app.processEvents()
        check("mã thoát khác 0 mà chip không báo lỗi",
              "lỗi" in stub_err.task_progress.title_label.text().lower())
        check("lỗi giả lập mà chip bị ẩn đi (giấu mất sự cố)",
              stub_err.task_progress.isVisible())

        # Build còn chạy (panel VXPEmu bị 'Dừng' trong lúc build) -> KHÔNG được chốt.
        stub_busy = stub_for(runner_running=True)
        MainWindow._on_vxpemu_stopped(stub_busy, 0)
        app.processEvents()
        check("build còn chạy mà chip đã bị chốt sớm", stub_busy.task_progress.is_active())

        # Nhãn nút X phải khớp việc X làm được: build xong thì X chỉ còn là "đóng".
        hint_stub = stub_for(runner_running=True)
        MainWindow._on_vxpemu_started(hint_stub, "C:/tmp/demo.vxp", 0)
        app.processEvents()
        check("VXPEmu chạy mà nhãn nút X vẫn hứa 'dừng tác vụ'",
              "dừng" not in hint_stub.task_progress.cancel_button.toolTip().lower())

if errors:
    print("FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("PASS: bấm X luôn đóng được chip tác vụ")
print("PASS: tác vụ Run chốt chip khi VXPEmu dừng (finished không được phát)")
print("PASS: chip hiện lại bình thường ở tác vụ kế tiếp")
