from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QFontDatabase, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTabWidget,
    QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from app.widgets.terminal_view import IntegratedTerminal
from app.ui import palette
from app.ui.icons import apply_icon


LOG_COLORS = {
    "default": palette.TEXT_2,
    "dim": palette.TEXT_4,
    "info": palette.INFO,
    "command": palette.INFO,
    "success": palette.GREEN_LIGHT,
    "warning": palette.AMBER,
    "error": palette.RED,
    "accent": palette.SYN_KEYWORD,
}


def classify_log_line(line: str) -> str:
    value = line.strip().lower()
    if not value:
        return "default"
    if (
        "[error]" in value
        or " error:" in value
        or value.startswith("error:")
        or "[fail]" in value
        or "failed (" in value
        or "build failed" in value
        or "traceback" in value
    ):
        return "error"
    if "[warning]" in value or "[warn]" in value or " warning:" in value:
        return "warning"
    if (
        value.startswith("[ok]")
        or value.startswith("[pass]")
        or "completed successfully" in value
        or "build succeeded" in value
    ):
        return "success"
    if value.startswith("[run]") or value.startswith("> "):
        return "command"
    if (
        value.startswith("[toolchain]")
        or value.startswith("[build]")
        or value.startswith("[emu]")
        or value.startswith("[session]")
        or value.startswith("[info]")
    ):
        return "info"
    if value.startswith("===") or value.startswith("---"):
        return "accent"
    return "default"


class LogView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        self.text = QPlainTextEdit()
        self.text.setObjectName("LogView")
        self.text.setReadOnly(True)
        self.text.setMaximumBlockCount(5000)
        col.addWidget(self.text, 1)

    def append(self, text: str) -> None:
        if not text:
            return
        # Preserve chunk boundaries while coloring each logical line.
        lines = text.splitlines(keepends=True)
        if not lines:
            lines = [text]
        cursor = self.text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        for line in lines:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(LOG_COLORS[classify_log_line(line)]))
            cursor.insertText(line, fmt)
        if not text.endswith(("\n", "\r")):
            cursor.insertText("\n")
        self.text.setTextCursor(cursor)
        self.text.ensureCursorVisible()

    def clear(self) -> None:
        self.text.clear()


class ProblemsView(QTreeWidget):
    open_problem = Signal(object, int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["Severity", "File", "Line", "Message"])
        self.setColumnWidth(0, 72)
        self.setColumnWidth(1, 160)
        self.setColumnWidth(2, 50)
        self.itemActivated.connect(self._activate)

    def set_diagnostics(self, path: Path | None, diagnostics: list) -> None:
        self.clear()
        if not path:
            return
        for d in diagnostics:
            item = QTreeWidgetItem([d.severity.value.upper(), path.name, str(d.line), d.message])
            item.setData(0, Qt.ItemDataRole.UserRole, (str(path), d.line, d.column))
            if d.severity.value == "error":
                item.setForeground(0, QColor(palette.RED))
            elif d.severity.value == "warning":
                item.setForeground(0, QColor(palette.AMBER))
            else:
                item.setForeground(0, QColor(palette.INFO))
            self.addTopLevelItem(item)

    def _activate(self, item: QTreeWidgetItem, _column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            path, line, column = data
            self.open_problem.emit(Path(path), int(line), int(column))


class HexView(QWidget):
    """Paged read-only VXP binary viewer."""

    PAGE_SIZE = 64 * 1024
    BYTES_PER_LINE = 16

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.path: Path | None = None
        self.file_size = 0
        self.offset = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        toolbar = QFrame()
        toolbar.setObjectName("HexToolbar")
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(5, 2, 5, 2)
        row.setSpacing(4)

        self.file_label = QLabel("No VXP loaded")
        self.file_label.setObjectName("HexFile")
        self.range_label = QLabel("-")
        self.range_label.setObjectName("HexRange")

        self.prev_btn = QPushButton("Prev")
        self.prev_btn.setObjectName("PanelToolButton")
        apply_icon(self.prev_btn, "back", 12)
        self.next_btn = QPushButton("Next")
        self.next_btn.setObjectName("PanelToolButton")
        apply_icon(self.next_btn, "forward", 12)
        self.reload_btn = QPushButton("Reload")
        self.reload_btn.setObjectName("PanelToolButton")
        apply_icon(self.reload_btn, "refresh", 12)

        self.prev_btn.clicked.connect(self.previous_page)
        self.next_btn.clicked.connect(self.next_page)
        self.reload_btn.clicked.connect(self.reload)

        row.addWidget(self.file_label, 1)
        row.addWidget(self.range_label)
        row.addWidget(self.prev_btn)
        row.addWidget(self.next_btn)
        row.addWidget(self.reload_btn)
        root.addWidget(toolbar)

        self.text = QPlainTextEdit()
        self.text.setObjectName("HexView")
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        fixed = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.text.setFont(fixed)
        root.addWidget(self.text, 1)

        self._update_buttons()

    def set_file(self, path: str | Path | None) -> bool:
        if not path:
            self.clear()
            return False
        target = Path(path).expanduser().resolve()
        if not target.is_file():
            self.clear()
            self.file_label.setText(f"Missing: {target.name}")
            self.file_label.setToolTip(str(target))
            return False
        self.path = target
        self.file_size = target.stat().st_size
        self.offset = 0
        self.file_label.setText(target.name)
        self.file_label.setToolTip(str(target))
        self.reload()
        return True

    def clear(self) -> None:
        self.path = None
        self.file_size = 0
        self.offset = 0
        self.file_label.setText("No VXP loaded")
        self.file_label.setToolTip("")
        self.range_label.setText("-")
        self.text.clear()
        self._update_buttons()

    def reload(self) -> None:
        if not self.path or not self.path.is_file():
            self.clear()
            return
        self.file_size = self.path.stat().st_size
        self.offset = min(self.offset, max(0, self.file_size - 1))
        with self.path.open("rb") as handle:
            handle.seek(self.offset)
            data = handle.read(self.PAGE_SIZE)
        self._render(data)
        start = self.offset
        end = self.offset + len(data)
        self.range_label.setText(
            f"0x{start:08X}-0x{end:08X} / {self.file_size:,} B"
        )
        self._update_buttons()

    def _render(self, data: bytes) -> None:
        self.text.clear()
        cursor = self.text.textCursor()
        offset_fmt = QTextCharFormat()
        offset_fmt.setForeground(QColor(palette.INFO))
        hex_fmt = QTextCharFormat()
        hex_fmt.setForeground(QColor(palette.SYN_FUNC))
        zero_fmt = QTextCharFormat()
        zero_fmt.setForeground(QColor(palette.SYN_COMMENT))
        ascii_fmt = QTextCharFormat()
        ascii_fmt.setForeground(QColor(palette.SYN_STRING))

        for index in range(0, len(data), self.BYTES_PER_LINE):
            chunk = data[index:index + self.BYTES_PER_LINE]
            address = self.offset + index
            cursor.insertText(f"{address:08X}  ", offset_fmt)

            for i in range(self.BYTES_PER_LINE):
                if i < len(chunk):
                    value = chunk[i]
                    cursor.insertText(
                        f"{value:02X} ",
                        zero_fmt if value == 0 else hex_fmt,
                    )
                else:
                    cursor.insertText("   ", hex_fmt)

            ascii_text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            cursor.insertText(f" |{ascii_text:<16}|\n", ascii_fmt)

        self.text.setTextCursor(cursor)
        self.text.moveCursor(QTextCursor.MoveOperation.Start)

    def previous_page(self) -> None:
        if not self.path:
            return
        self.offset = max(0, self.offset - self.PAGE_SIZE)
        self.reload()

    def next_page(self) -> None:
        if not self.path:
            return
        if self.offset + self.PAGE_SIZE < self.file_size:
            self.offset += self.PAGE_SIZE
            self.reload()

    def _update_buttons(self) -> None:
        has_file = bool(self.path and self.path.is_file())
        self.prev_btn.setEnabled(has_file and self.offset > 0)
        self.next_btn.setEnabled(
            has_file and self.offset + self.PAGE_SIZE < self.file_size
        )
        self.reload_btn.setEnabled(has_file)


class BottomPanel(QTabWidget):
    open_location = Signal(object, int, int)
    close_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("BottomPanel")

        self.console = LogView()
        self.output = self.console
        self.build_log = LogView()
        self.problems = ProblemsView()
        self.terminal = IntegratedTerminal()
        self.hex_view = HexView()

        self.addTab(self.console, "CONSOLE")
        self.addTab(self.build_log, "BUILD")
        self.addTab(self.problems, "PROBLEMS")
        self.addTab(self.terminal, "TERMINAL")
        self.addTab(self.hex_view, "HEX")
        self.problems.open_problem.connect(self.open_location)

        self.setDocumentMode(True)
        self.tabBar().setExpanding(False)
        self.setMinimumHeight(72)

        self.close_button = QToolButton()
        self.close_button.setObjectName("BottomPanelClose")
        self.close_button.setAutoRaise(True)
        self.close_button.setToolTip("Close Panel (Ctrl+J)")
        apply_icon(self.close_button, "close", 13)
        self.close_button.clicked.connect(self.close_requested)
        self.setCornerWidget(self.close_button, Qt.Corner.TopRightCorner)

    def key_for_widget(self, widget) -> str:
        if widget is self.console:
            return "console"
        if widget is self.build_log:
            return "build"
        if widget is self.problems:
            return "problems"
        if widget is self.terminal:
            return "terminal"
        if widget is self.hex_view:
            return "hex"
        return "console"

    def active_key(self) -> str:
        return self.key_for_widget(self.currentWidget())

    def set_active_key(self, key: str) -> None:
        target = {
            "console": self.console,
            "output": self.console,
            "build": self.build_log,
            "problems": self.problems,
            "terminal": self.terminal,
            "hex": self.hex_view,
        }.get(str(key).lower(), self.console)
        self.setCurrentWidget(target)

    def show_console(self) -> None:
        self.setCurrentWidget(self.console)

    def show_output(self) -> None:
        self.show_console()

    def show_build(self) -> None:
        self.setCurrentWidget(self.build_log)

    def show_terminal(self) -> None:
        self.setCurrentWidget(self.terminal)
        self.terminal.ensure_started()

    def show_hex(self, path: str | Path | None = None) -> bool:
        if path is not None and not self.hex_view.set_file(path):
            return False
        self.setCurrentWidget(self.hex_view)
        return bool(self.hex_view.path)

    def shutdown(self) -> None:
        self.terminal.shutdown()
