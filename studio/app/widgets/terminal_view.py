from __future__ import annotations

import os
import re
from pathlib import Path

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
    QVBoxLayout, QWidget,
)

from app.ui import palette
from app.ui.icons import apply_icon


_ANSI = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_DONE_PREFIX = "__LUAS30_DONE__:"


class TerminalSurface(QPlainTextEdit):
    """VS Code-like single terminal surface.

    Shell output and the editable command line live in the same QPlainTextEdit.
    Only text after the current prompt is editable.
    """

    command_submitted = Signal(str)
    clear_requested = Signal()
    interrupt_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TerminalSurface")
        self.setMaximumBlockCount(8000)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabChangesFocus(False)

        self._history: list[str] = []
        self._history_index = 0
        self._input_start: int | None = None
        self._prompt = ""

        self._default_format = QTextCharFormat()
        self._default_format.setForeground(QColor(palette.TEXT_2))
        self._prompt_format = QTextCharFormat()
        self._prompt_format.setForeground(QColor(palette.INFO))
        self._input_format = QTextCharFormat()
        self._input_format.setForeground(QColor(palette.SYN_FUNC))
        self._success_format = QTextCharFormat()
        self._success_format.setForeground(QColor(palette.GREEN_LIGHT))
        self._error_format = QTextCharFormat()
        self._error_format.setForeground(QColor(palette.RED))
        self._warning_format = QTextCharFormat()
        self._warning_format.setForeground(QColor(palette.AMBER))

    def input_active(self) -> bool:
        return self._input_start is not None

    def append_output(self, text: str) -> None:
        if not text:
            return
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        for line in text.splitlines(keepends=True) or [text]:
            low = line.lower()
            fmt = self._default_format
            if "[error]" in low or " error:" in low or "failed" in low:
                fmt = self._error_format
            elif "[warn" in low or " warning:" in low:
                fmt = self._warning_format
            elif "[ok]" in low or "[pass]" in low or "succeeded" in low:
                fmt = self._success_format
            cursor.insertText(line, fmt)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def show_prompt(self, prompt: str) -> None:
        self._prompt = prompt
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Keep prompts visually separate from output that did not end in LF.
        document_text = self.toPlainText()
        if document_text and not document_text.endswith("\n"):
            cursor.insertText("\n")

        cursor.insertText(prompt, self._prompt_format)
        cursor.setCharFormat(self._input_format)
        self.setTextCursor(cursor)
        self.setCurrentCharFormat(self._input_format)
        self._input_start = cursor.position()
        self._history_index = len(self._history)
        self.ensureCursorVisible()
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def suspend_input(self) -> None:
        self._input_start = None

    def current_input(self) -> str:
        if self._input_start is None:
            return ""
        cursor = self.textCursor()
        end = self.document().characterCount() - 1
        cursor.setPosition(self._input_start)
        cursor.setPosition(max(self._input_start, end), QTextCursor.MoveMode.KeepAnchor)
        return cursor.selectedText().replace("\u2029", "\n")

    def replace_current_input(self, value: str) -> None:
        if self._input_start is None:
            return
        cursor = self.textCursor()
        end = self.document().characterCount() - 1
        cursor.setPosition(self._input_start)
        cursor.setPosition(max(self._input_start, end), QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(value)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_terminal(self) -> None:
        self.clear()
        self._input_start = None

    def commit_external_command(self, command: str) -> None:
        """Render a programmatic command on the live prompt without emitting submit."""
        value = str(command or "")
        if self._input_start is not None:
            self.replace_current_input(value)
        else:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            if self.toPlainText() and not self.toPlainText().endswith("\n"):
                cursor.insertText("\n")
            cursor.insertText(value, self._input_format)
            self.setTextCursor(cursor)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText("\n")
        self.setTextCursor(cursor)
        self._input_start = None
        self.ensureCursorVisible()

    def _ensure_editable_cursor(self) -> QTextCursor:
        cursor = self.textCursor()
        if self._input_start is None:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            return cursor

        if cursor.selectionStart() < self._input_start or cursor.position() < self._input_start:
            cursor.clearSelection()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
        return cursor

    def _submit(self) -> None:
        if self._input_start is None:
            return
        command = self.current_input()
        if command.strip() and (not self._history or self._history[-1] != command):
            self._history.append(command)
        self._history_index = len(self._history)

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText("\n")
        self.setTextCursor(cursor)
        self._input_start = None
        self.command_submitted.emit(command)

    def _history_up(self) -> None:
        if self._input_start is None or not self._history:
            return
        self._history_index = max(0, self._history_index - 1)
        self.replace_current_input(self._history[self._history_index])

    def _history_down(self) -> None:
        if self._input_start is None or not self._history:
            return
        self._history_index = min(len(self._history), self._history_index + 1)
        value = "" if self._history_index >= len(self._history) else self._history[self._history_index]
        self.replace_current_input(value)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        mods = event.modifiers()

        # Standard terminal conveniences.
        if mods & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_L:
                self.clear_requested.emit()
                return
            if key == Qt.Key.Key_C and not self.textCursor().hasSelection():
                self.interrupt_requested.emit()
                return
            if key == Qt.Key.Key_V:
                if self._input_start is None:
                    return
                self._ensure_editable_cursor()
                text = QApplication.clipboard().text()
                # Keep one editable shell command line. Newline paste becomes a
                # sequence of commands separated by the platform shell separator.
                separator = " & " if os.name == "nt" else " ; "
                text = re.sub(r"[\r\n]+", separator, text)
                self.insertPlainText(text)
                return
            if key == Qt.Key.Key_A and self._input_start is not None:
                cursor = self.textCursor()
                end = self.document().characterCount() - 1
                cursor.setPosition(self._input_start)
                cursor.setPosition(max(self._input_start, end), QTextCursor.MoveMode.KeepAnchor)
                self.setTextCursor(cursor)
                return

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._submit()
            return
        if key == Qt.Key.Key_Up:
            self._history_up()
            return
        if key == Qt.Key.Key_Down:
            self._history_down()
            return

        if self._input_start is None:
            # Shell is executing a command. Output remains selectable/copyable,
            # but normal text does not mutate old terminal history.
            if key in (
                Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Home,
                Qt.Key.Key_End, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown,
            ) or (mods & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_C):
                super().keyPressEvent(event)
            return

        cursor = self._ensure_editable_cursor()

        if key == Qt.Key.Key_Home:
            cursor.setPosition(self._input_start)
            self.setTextCursor(cursor)
            return

        if key == Qt.Key.Key_Backspace:
            if cursor.hasSelection():
                if cursor.selectionStart() < self._input_start:
                    cursor.clearSelection()
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    self.setTextCursor(cursor)
                    return
            elif cursor.position() <= self._input_start:
                return

        if key == Qt.Key.Key_Left and not cursor.hasSelection() and cursor.position() <= self._input_start:
            return

        # Any printable edit that has a selection reaching terminal history is
        # redirected to the live command line.
        if cursor.hasSelection() and cursor.selectionStart() < self._input_start:
            cursor.clearSelection()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)

        super().keyPressEvent(event)


class IntegratedTerminal(QWidget):
    status_message = Signal(str)
    state_changed = Signal(str)
    command_started = Signal(str, str)
    command_finished = Signal(str, int, str, str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("IntegratedTerminal")
        self.project_root: Path | None = None
        self.process: QProcess | None = None
        self._encoding = "utf-8"
        self._shell_name = "Terminal"
        self._current_cwd = Path.cwd()
        self._stream_buffer = ""
        self._waiting_for_marker = False
        self._active_command = ""
        self._active_origin = "user"
        self._command_capture = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        toolbar = QFrame()
        toolbar.setObjectName("TerminalToolbar")
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(5, 2, 5, 2)
        row.setSpacing(3)
        self.title = QLabel("TERMINAL")
        self.title.setObjectName("TerminalTitle")
        self.state = QLabel("Stopped")
        self.state.setObjectName("TerminalState")
        row.addWidget(self.title)
        row.addWidget(self.state)
        row.addStretch(1)

        new_btn = QPushButton("New")
        new_btn.setObjectName("PanelToolButton")
        apply_icon(new_btn, "add", 13)
        kill_btn = QPushButton("Kill")
        kill_btn.setObjectName("PanelToolButton")
        apply_icon(kill_btn, "stop", 13)
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("PanelToolButton")
        apply_icon(clear_btn, "delete", 13)
        new_btn.clicked.connect(self.new_terminal)
        kill_btn.clicked.connect(self.kill_terminal)
        clear_btn.clicked.connect(self.clear)
        row.addWidget(new_btn)
        row.addWidget(kill_btn)
        row.addWidget(clear_btn)
        root.addWidget(toolbar)

        # One terminal surface, just like VS Code. There is intentionally no
        # separate command QLineEdit at the bottom.
        self.surface = TerminalSurface()
        self.surface.command_submitted.connect(self.send_command)
        self.surface.clear_requested.connect(self.clear)
        self.surface.interrupt_requested.connect(self.interrupt)
        root.addWidget(self.surface, 1)

        # Compatibility aliases for existing Studio code/plugins.
        self.output = self.surface
        self.input = self.surface

    @property
    def running(self) -> bool:
        return bool(self.process and self.process.state() != QProcess.ProcessState.NotRunning)

    def set_project_root(self, root: Path | None) -> None:
        self.project_root = Path(root).resolve() if root else None
        if self.project_root and not self.running:
            self._current_cwd = self.project_root

    def _shell(self) -> tuple[str, list[str], str]:
        if os.name == "nt":
            comspec = os.environ.get("COMSPEC") or "cmd.exe"
            # /D disables AutoRun, /Q disables command echo. `prompt $S` keeps
            # cmd's own prompt visually silent because LuaS30 renders its prompt.
            return comspec, ["/D", "/Q", "/K", "prompt $S"], Path(comspec).name
        shell = os.environ.get("SHELL") or "/bin/sh"
        return shell, ["-i"], Path(shell).name

    def _prompt(self) -> str:
        cwd = str(self._current_cwd)
        return f"{cwd}> " if os.name == "nt" else f"{cwd}$ "

    def ensure_started(self) -> None:
        if not self.running:
            self.start_terminal()
        else:
            if not self.surface.input_active() and not self._waiting_for_marker:
                self.surface.show_prompt(self._prompt())
            self.surface.setFocus(Qt.FocusReason.OtherFocusReason)

    def start_terminal(self) -> None:
        if self.running:
            return
        program, args, label = self._shell()
        self._shell_name = label
        self._current_cwd = self.project_root or Path.cwd()
        self._stream_buffer = ""
        self._waiting_for_marker = False

        process = QProcess(self)
        self.process = process
        process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        process.readyReadStandardOutput.connect(lambda p=process: self._read_stdout(p))
        process.readyReadStandardError.connect(lambda p=process: self._read_stderr(p))
        process.started.connect(lambda p=process: self._started(p))
        process.finished.connect(lambda code, status, p=process: self._finished(p, code, status))
        process.errorOccurred.connect(lambda error, p=process: self._process_error(p, error))

        env = QProcessEnvironment.systemEnvironment()
        env.insert("LUAS30_ENGINE", "1")
        env.insert("PYTHONUTF8", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        if os.name == "nt":
            env.insert("PROMPT", " ")
        if os.name != "nt":
            env.insert("PS1", "")
            env.insert("PS2", "")
        if self.project_root:
            env.insert("LUAS30_PROJECT_ROOT", str(self.project_root))
            process.setWorkingDirectory(str(self.project_root))
        process.setProcessEnvironment(env)

        self.surface.append_output(f"[terminal] starting {label}\n")
        process.start(program, args)

    def new_terminal(self) -> None:
        self.kill_terminal(silent=True)
        self.surface.append_output("\n[terminal] new session\n")
        self.start_terminal()

    def kill_terminal(self, silent: bool = False) -> None:
        process = self.process
        self.surface.suspend_input()
        self._waiting_for_marker = False
        self._active_command = ""
        self._active_origin = "user"
        self._command_capture = ""
        if not process:
            if not silent:
                self.surface.append_output("[terminal] no active session\n")
            return
        if process.state() != QProcess.ProcessState.NotRunning:
            process.terminate()
            if not process.waitForFinished(800):
                process.kill()
                process.waitForFinished(800)
        process.deleteLater()
        self.process = None
        self.state.setText("Stopped")
        self.state_changed.emit("stopped")
        if not silent:
            self.surface.append_output("[terminal] session stopped\n")

    def shutdown(self) -> None:
        self.kill_terminal(silent=True)

    def clear(self) -> None:
        active = self.surface.input_active()
        self.surface.clear_terminal()
        if self.running and active and not self._waiting_for_marker:
            self.surface.show_prompt(self._prompt())

    def interrupt(self) -> None:
        if not self.running or not self.process:
            return
        # QProcess does not provide a portable Windows GenerateConsoleCtrlEvent
        # equivalent for a pipe-backed child. Sending ETX works for shells/tools
        # that consume control characters from stdin; otherwise Kill remains
        # available in the toolbar.
        self.process.write(b"\x03")
        self.status_message.emit("Ctrl+C sent to terminal")

    def cancel_ai_command(self) -> bool:
        """Stop the currently running AI terminal command immediately.

        The integrated shell is restarted lazily on the next command. Killing the
        shell is intentional here because Ctrl+C is not reliable for a pipe-backed
        QProcess on Windows. User-originated terminal work is never stopped.
        """
        if not self._waiting_for_marker or self._active_origin != "ai":
            return False
        self.surface.append_output("\n[AI] stop requested\n")
        self.kill_terminal(silent=True)
        self.surface.append_output("[terminal] AI command stopped\n")
        self.status_message.emit("AI terminal command stopped")
        return True

    def run_ai_command(self, command: str, cwd: str | Path | None = None) -> bool:
        """Run an AI-approved command in the same visible integrated shell.

        The command is never hidden: it is printed to the terminal and emits lifecycle
        signals so ChatAI can receive the result. Only one command can run at a time.
        """
        if self._waiting_for_marker:
            return False
        command = str(command or "").strip()
        if not command:
            return False

        display_command = command
        if cwd:
            target = Path(cwd).expanduser().resolve()
            if os.name == "nt":
                escaped = str(target).replace('"', '""')
                command = f'cd /d "{escaped}" && {command}'
            else:
                escaped = str(target).replace("'", "'\\''")
                command = f"cd '{escaped}' && {command}"

        self.ensure_started()
        self.surface.commit_external_command(display_command)
        return self.send_command(
            command,
            origin="ai",
            display_command=display_command,
        )

    def send_command(
        self,
        command: str,
        origin: str = "user",
        display_command: str | None = None,
    ) -> bool:
        if self._waiting_for_marker:
            self.status_message.emit("Terminal is busy; wait for the current command to finish.")
            return False
        if not self.running:
            self.start_terminal()
        if not self.process or not self.running:
            self.surface.append_output("[terminal] shell is not running\n")
            return False

        command = command.rstrip("\r\n")
        shown = str(display_command or command)
        if not command.strip():
            self.surface.show_prompt(self._prompt())
            return True

        if command.strip().lower() in {"cls", "clear"} and origin == "user":
            self.clear()
            self.surface.show_prompt(self._prompt())
            return True

        self._active_command = shown
        self._active_origin = str(origin or "user")
        self._command_capture = ""
        self._waiting_for_marker = True
        self.command_started.emit(self._active_command, self._active_origin)

        if os.name == "nt":
            payload = (
                command
                + "\r\n"
                + "@echo.\r\n"
                + f"@echo {_DONE_PREFIX}%ERRORLEVEL%:%CD%\r\n"
            )
        else:
            payload = (
                command
                + "\n"
                + "printf '\\n"
                + _DONE_PREFIX
                + "%s:%s\\n' \"$?\" \"$PWD\"\n"
            )
        self.process.write(payload.encode(self._encoding, errors="replace"))
        return True

    def _decode(self, data: bytes) -> str:
        text = data.decode(self._encoding, errors="replace")
        return _ANSI.sub("", text).replace("\r\n", "\n").replace("\r", "\n")

    def _capture_command_output(self, text: str) -> None:
        if not self._waiting_for_marker or not text:
            return
        self._command_capture += text
        if len(self._command_capture) > 1_000_000:
            self._command_capture = self._command_capture[-1_000_000:]

    def _consume_stdout(self, text: str) -> None:
        if not text:
            return
        self._stream_buffer += text

        while "\n" in self._stream_buffer:
            line, self._stream_buffer = self._stream_buffer.split("\n", 1)
            marker_line = line.lstrip()
            if marker_line.startswith(_DONE_PREFIX):
                payload = marker_line[len(_DONE_PREFIX):]
                parts = payload.split(":", 1)
                try:
                    exit_code = int(parts[0].strip()) if parts else -1
                except ValueError:
                    exit_code = -1
                if len(parts) == 2 and parts[1].strip():
                    self._current_cwd = Path(parts[1].strip())

                command = self._active_command
                origin = self._active_origin
                output = self._command_capture.rstrip()
                cwd = str(self._current_cwd)
                self._waiting_for_marker = False
                self._active_command = ""
                self._active_origin = "user"
                self._command_capture = ""
                self.command_finished.emit(command, exit_code, cwd, output, origin)
                self.surface.show_prompt(self._prompt())
                continue

            rendered = line + "\n"
            self._capture_command_output(rendered)
            self.surface.append_output(rendered)

    def _read_stdout(self, process: QProcess) -> None:
        self._consume_stdout(self._decode(bytes(process.readAllStandardOutput())))

    def _read_stderr(self, process: QProcess) -> None:
        text = self._decode(bytes(process.readAllStandardError()))
        self._capture_command_output(text)
        self.surface.append_output(text)

    def _started(self, process: QProcess) -> None:
        if process is not self.process:
            return
        self.state.setText(self._shell_name)
        self.state_changed.emit("running")
        self.status_message.emit(f"Terminal started: {self._shell_name}")
        self.surface.show_prompt(self._prompt())

    def _finished(self, process: QProcess, exit_code: int, _status) -> None:
        self._read_stdout(process)
        self._read_stderr(process)
        if self._stream_buffer:
            self.surface.append_output(self._stream_buffer)
            self._stream_buffer = ""
        self.surface.suspend_input()
        self.surface.append_output(f"\n[terminal] exited with code {exit_code}\n")
        process.deleteLater()
        if process is self.process:
            self.process = None
            self._waiting_for_marker = False
            self.state.setText("Stopped")
            self.state_changed.emit("stopped")

    def _process_error(self, process: QProcess, _error) -> None:
        self.surface.append_output(f"[terminal error] {process.errorString()}\n")

    # Compatibility with the old terminal API.
    def _append(self, text: str) -> None:
        self.surface.append_output(text)
