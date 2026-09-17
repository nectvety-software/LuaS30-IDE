from __future__ import annotations

"""Hộp thoại thiết lập lần đầu — quét môi trường rồi cài nốt tự động.

Hiện tự động ~0.8s sau khi Studio mở (lần đầu tiên hoặc version mới),
không bao giờ chặn việc mở IDE. Mở lại bất cứ lúc nào từ Tools menu
"Chạy lại thiết lập lần đầu...".
"""

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.services.environment_setup import (
    EnvironmentInstaller, Requirement, detect_missing, installable,
    is_first_run, mark_setup_done,
)
from app.ui.icons import apply_icon


class _RequirementRow(QFrame):
    toggled = Signal()

    def __init__(self, requirement: Requirement, satisfied: bool) -> None:
        super().__init__()
        self.requirement = requirement
        self.setObjectName("SetupRow")
        self.setProperty("satisfied", "true" if satisfied else "false")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(10)

        self.check = QCheckBox()
        self.check.setChecked(not satisfied and requirement.is_installable)
        self.check.setEnabled(not satisfied and requirement.is_installable)
        self.check.setToolTip("Chọn để cài tự động")
        self.check.toggled.connect(self.toggled.emit)
        layout.addWidget(self.check)

        name = QLabel(requirement.name)
        name.setObjectName("SetupRowName")
        name.setWordWrap(True)
        layout.addWidget(name, 1)

        if satisfied:
            state_text, state_prop = "Đã có", "ok"
        elif requirement.is_installable:
            state_text, state_prop = "Có thể cài tự động", "auto"
        else:
            state_text, state_prop = "Cần làm thủ công", "manual"
        state = QLabel(state_text)
        state.setObjectName("SetupRowState")
        state.setProperty("state", state_prop)
        layout.addWidget(state)

    @property
    def selected(self) -> bool:
        return self.check.isChecked() and self.check.isEnabled()


class SetupDialog(QDialog):
    setup_completed = Signal(bool)

    def __init__(self, engine_root: Path | str, version: str,
                 parent=None, *, force: bool = False) -> None:
        super().__init__(parent)
        self.engine_root = Path(engine_root).resolve()
        self.version = str(version)
        self._force = force
        self._rows: list[_RequirementRow] = []
        self._installer = EnvironmentInstaller(self)
        self._installer.log.connect(self._append_log)
        self._installer.step_started.connect(self._on_step_started)
        self._installer.finished.connect(self._on_install_finished)

        self.setWindowTitle("Thiết lập LuaS30 IDE lần đầu")
        self.resize(640, 560)
        self.setMinimumSize(560, 460)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        intro = QLabel(
            "LuaS30 IDE cần một số thành phần để build và chạy ứng dụng MRE VXP.\n"
            "Dưới đây là kết quả kiểm tra máy của bạn. Những mục có thể cài tự động "
            "đã được chọn sẵn — bấm “Tự động cài đặt” để IDE chạy trình cài "
            "cho bạn (có thể mất vài phút)."
        )
        intro.setObjectName("Muted")
        intro.setWordWrap(True)
        root.addWidget(intro)

        self.status_label = QLabel("Đang kiểm tra môi trường…")
        self.status_label.setObjectName("SetupStatus")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        root.addWidget(self.progress)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 6, 0, 6)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch(1)
        scroll.setWidget(self.list_widget)
        root.addWidget(scroll, 1)

        self.log_label = QLabel("Nhật ký")
        self.log_label.setObjectName("Muted")
        root.addWidget(self.log_label)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(200)
        self.log_view.setMinimumHeight(90)
        root.addWidget(self.log_view)
        self.log_label.hide()
        self.log_view.hide()

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.skip_button = QPushButton("Bỏ qua")
        apply_icon(self.skip_button, "close", 13)
        self.skip_button.clicked.connect(self._skip)
        self.rescan_button = QPushButton("Kiểm tra lại")
        apply_icon(self.rescan_button, "refresh", 13)
        self.rescan_button.clicked.connect(self._scan)
        self.install_button = QPushButton("Tự động cài đặt")
        apply_icon(self.install_button, "play", 13)
        self.install_button.setEnabled(False)
        self.install_button.clicked.connect(self._install_selected)
        self.done_button = QPushButton("Hoàn tất")
        apply_icon(self.done_button, "check", 13)
        self.done_button.clicked.connect(self._finish)
        self.done_button.hide()
        for btn in (self.skip_button, self.rescan_button, self.install_button, self.done_button):
            footer.addWidget(btn)
        root.addLayout(footer)

        # Quét ngay khi hộp thoại đã hiện.
        QTimer.singleShot(0, self._scan)

    # ---------------------------------------------------------------- quét

    def _scan(self) -> None:
        for row in self._rows:
            self.list_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()

        missing = detect_missing(self.engine_root)
        missing_keys = {item.key for item in missing}
        try:
            from app.services.environment_setup import all_requirements
            ordered = all_requirements(self.engine_root)
        except Exception:
            ordered = list(missing)
        for requirement in ordered:
            row = _RequirementRow(requirement, requirement.key not in missing_keys)
            row.toggled.connect(self._refresh_footer)
            self._rows.append(row)
            self.list_layout.insertWidget(len(self._rows) - 1, row)

        installable_count = len(installable(missing))
        if not missing:
            self.status_label.setText("Mọi thành phần môi trường đã sẵn sàng. Bạn có thể bắt đầu.")
        else:
            manual = len(missing) - installable_count
            parts = [f"Thiếu {len(missing)} thành phần"]
            if installable_count:
                parts.append(f"{installable_count} cái có thể cài tự động")
            if manual:
                parts.append(f"{manual} cái cần làm thủ công")
            self.status_label.setText(" · ".join(parts) + ".")
        self._refresh_footer()

    def _refresh_footer(self) -> None:
        selected = [row for row in self._rows if row.selected]
        self.install_button.setEnabled(bool(selected) and not self._installer.is_running)
        self.install_button.setText(
            f"Tự động cài đặt ({len(selected)})" if selected else "Tự động cài đặt")

    # ----------------------------------------------------------------- cài

    def _install_selected(self) -> None:
        selected = [row.requirement for row in self._rows if row.selected]
        if not selected:
            return
        self.log_view.clear()
        self.log_view.show()
        self.log_label.show()
        self.install_button.setEnabled(False)
        self.skip_button.setEnabled(False)
        self.rescan_button.setEnabled(False)
        self.status_label.setText(f"Đang cài {len(selected)} thành phần — vui lòng chờ…")
        if not self._installer.install(selected):
            self.status_label.setText("Không có gói nào có thể cài tự động.")
            self._set_controls_enabled(True)

    def _on_step_started(self, name: str, done: int, total: int) -> None:
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(done - 1)
        self.status_label.setText(f"Đang cài ({done}/{total}): {name}")

    def _on_install_finished(self, ok: bool, results) -> None:
        self.progress.setValue(self.progress.maximum())
        failed = [name for name, code in results if code != 0]
        if ok:
            self.status_label.setText("Đã cài xong mọi thành phần.")
        elif failed:
            self.status_label.setText(
                f"Hoàn tất nhưng {len(failed)} mục lỗi: {', '.join(failed)}. Xem nhật ký bên dưới.")
        else:
            self.status_label.setText("Quá trình cài đặt kết thúc — xem nhật ký để biết chi tiết.")
        self.install_button.hide()
        self.done_button.show()
        self._set_controls_enabled(True)
        self._scan()

    def _append_log(self, line: str) -> None:
        self.log_view.appendPlainText(str(line or ""))

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.skip_button.setEnabled(enabled)
        self.rescan_button.setEnabled(enabled)
        self._refresh_footer()

    # -------------------------------------------------------------- kết thúc

    def _skip(self) -> None:
        self._installer.stop()
        self.reject()

    def _finish(self) -> None:
        self._installer.stop()
        mark_setup_done(self.version)
        self.setup_completed.emit(True)
        self.accept()

    def reject(self) -> None:
        # Đóng bằng X cũng coi như "đã xem" để không hiện lại mãi.
        try:
            self._installer.stop()
            mark_setup_done(self.version)
            self.setup_completed.emit(False)
        finally:
            super().reject()
