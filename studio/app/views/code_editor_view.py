from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QLabel, QSplitter, QTabWidget, QVBoxLayout, QWidget

from app.editor.editor_group_manager import EditorGroupManager
from app.editor.find_replace import FindReplaceBar
from app.editor.project_index import ProjectIndex
from app.editor.project_search import ProjectSearchPanel
from app.editor.explorer_panel import ExplorerPanel
from app.widgets.bottom_panel import BottomPanel
from app.views.ai_chat_view import AIChatView
from app.views.ai_diff_view import AIDiffView
from app.services.ai_change_service import AIChangeService, PreparedChangeSet


class CodeEditorView(QWidget):
    DEFAULT_SIDEBAR_WIDTH = 220
    MIN_SIDEBAR_WIDTH = 175
    MAX_RESTORED_SIDEBAR_WIDTH = 520
    DEFAULT_BOTTOM_PANEL_HEIGHT = 145
    MIN_BOTTOM_PANEL_HEIGHT = 72
    MAX_RESTORED_BOTTOM_PANEL_HEIGHT = 420
    status_message = Signal(str)
    cursor_info_changed = Signal(int, int, int)
    problems_changed = Signal(int, int)

    def __init__(self, engine_root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.engine_root = Path(engine_root).resolve()
        self.project_root: Path | None = None
        self.index = ProjectIndex()
        self.ai_change_service = AIChangeService()
        self._ai_change_set: PreparedChangeSet | None = None

        # Project Hub mode hides editor-only chrome (Explorer/Search + bottom panel)
        # without overwriting the user's editor layout/session preferences.
        self._hub_mode = False
        self._editor_sidebar_visible = True
        self._sidebar_width = self.DEFAULT_SIDEBAR_WIDTH
        self._editor_bottom_visible = False
        self._editor_find_visible = False
        self._bottom_panel_height = self.DEFAULT_BOTTOM_PANEL_HEIGHT
        self._ai_visible = False
        self._hub_ai_visible = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.workspace = QSplitter(Qt.Orientation.Horizontal)
        self.workspace.setChildrenCollapsible(True)
        self.workspace.setHandleWidth(2)

        self.left_tabs = QTabWidget()
        self.left_tabs.setObjectName("SideTabs")
        self.left_tabs.setMinimumWidth(175)
        self.left_tabs.tabBar().hide()
        self.explorer_panel = ExplorerPanel()
        self.project_tree = self.explorer_panel.tree
        self.search_panel = ProjectSearchPanel()
        self.left_tabs.addTab(self.explorer_panel, "Explorer")
        self.left_tabs.addTab(self.search_panel, "Search")

        self.center_host = QFrame()
        self.center_host.setObjectName("CenterWorkbench")
        center_layout = QVBoxLayout(self.center_host)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self.find_bar = FindReplaceBar()
        center_layout.addWidget(self.find_bar)

        # The Compact Bottom Panel belongs only to the center editor column.
        self.vertical = QSplitter(Qt.Orientation.Vertical)
        self.vertical.setChildrenCollapsible(False)
        self.vertical.setHandleWidth(3)

        editor_panel = QFrame()
        editor_panel.setObjectName("EditorPanel")
        editor_layout = QVBoxLayout(editor_panel)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)
        self.tabs = EditorGroupManager()
        editor_layout.addWidget(self.tabs)

        self.bottom = BottomPanel()
        self.vertical.addWidget(editor_panel)
        self.vertical.addWidget(self.bottom)
        self.vertical.setStretchFactor(0, 1)
        self.vertical.setStretchFactor(1, 0)
        self.vertical.setSizes([900, self.DEFAULT_BOTTOM_PANEL_HEIGHT])
        self.bottom.hide()
        center_layout.addWidget(self.vertical, 1)

        self.ai_chat = AIChatView(self.engine_root)
        self.ai_chat.hide()

        self.workspace.addWidget(self.left_tabs)
        self.workspace.addWidget(self.center_host)
        self.workspace.addWidget(self.ai_chat)
        # Do not let dragging/restoring the splitter collapse Explorer to a
        # permanent 0px pane. Ctrl+B remains the explicit hide/show action.
        self.workspace.setCollapsible(0, False)
        self.workspace.setStretchFactor(0, 0)
        self.workspace.setStretchFactor(1, 1)
        self.workspace.setStretchFactor(2, 0)
        self.workspace.setSizes([220, 1100, 0])

        self._editor_sidebar_visible = True
        self._editor_bottom_visible = False
        self._editor_find_visible = self.find_bar.isVisible()
        root.addWidget(self.workspace, 1)

        self.project_tree.file_activated.connect(self.open_file)
        self.explorer_panel.status_message.connect(self.status_message)
        self.tabs.cursor_info_changed.connect(self.cursor_info_changed)
        self.tabs.file_saved.connect(self._file_saved)
        self.tabs.file_opened.connect(lambda p: self.status_message.emit(f"Opened: {p}"))
        self.tabs.current_editor_changed.connect(self._current_editor_changed)
        self.tabs.diagnostics_changed.connect(self._diagnostics_changed)
        self.tabs.go_to_definition_requested.connect(self.go_to_definition)
        self.tabs.request_find.connect(self.show_find)
        self.search_panel.open_result.connect(self.open_location)
        self.search_panel.status_message.connect(self.status_message)
        self.bottom.open_location.connect(self.open_location)
        self.bottom.ask_ai.connect(self._ask_ai_about_problems)
        self.bottom.close_requested.connect(self.hide_bottom_panel)
        self.bottom.terminal.status_message.connect(self.status_message)
        self.ai_chat.status_message.connect(self.status_message)
        self.ai_chat.visibility_requested.connect(self.set_ai_visible)
        self.ai_chat.set_active_editor_provider(self._active_editor_context)
        self.ai_chat.set_shell_runner(self._run_ai_shell)
        self.ai_chat.set_shell_stopper(self._stop_ai_shell)
        self.ai_chat.changes_proposed.connect(self._prepare_ai_changes)
        self.ai_chat.review_changes_requested.connect(self._review_ai_changes)
        self.ai_chat.apply_changes_requested.connect(self._apply_ai_changes)
        self.ai_chat.reject_changes_requested.connect(self._reject_ai_changes)
        self.bottom.terminal.command_finished.connect(self.ai_chat.on_shell_command_finished)
        self.vertical.splitterMoved.connect(self._remember_bottom_panel_height)
        self.workspace.splitterMoved.connect(self._remember_sidebar_width)


    def open_tool_tab(
        self,
        key: str,
        title: str,
        factory,
        icon: QIcon | None = None,
        *,
        insert_at: int | None = None,
        activate: bool = True,
        group_index: int | None = None,
    ):
        if group_index is None:
            return self.tabs.open_tool_tab(
                key, title, factory, icon,
                insert_at=insert_at, activate=activate,
            )
        return self.tabs.open_tool_tab_in_group(
            group_index, key, title, factory, icon,
            insert_at=insert_at, activate=activate,
        )

    def tool_widget(self, key: str):
        return self.tabs.tool_widget(key)

    def clear_project(self) -> None:
        self.project_root = None
        self.explorer_panel.clear_project()
        self.search_panel.clear_root()
        self.index.set_root(None)
        self.bottom.terminal.set_project_root(None)
        self.ai_chat.set_project_root(None)
        self.ai_change_service.reject()
        self._ai_change_set = None
        self.bottom.console.append("Project closed")

    def set_project(self, root: str | Path, open_main: bool = True) -> None:
        path = Path(root).resolve()
        self.project_root = path
        self.explorer_panel.set_project_root(path)
        self.search_panel.set_root(path)
        self.index.set_root(path)
        main_lua = path / "main.lua"
        if open_main and main_lua.is_file():
            self.open_file(main_lua)
        self.bottom.terminal.set_project_root(path)
        self.ai_chat.set_project_root(path)
        self.bottom.console.append(f"Project indexed: {path.name} ({len(self.index.names())} symbols)")

    def set_hub_mode(self, enabled: bool) -> None:
        """Hide editor-only panes while Welcome/Project Storage is active.

        The actual widgets are hidden in hub mode, but the editor's preferred
        sidebar/panel visibility is preserved so session restore is not polluted
        by the temporary Project Hub presentation.
        """
        enabled = bool(enabled)
        if enabled == self._hub_mode:
            return

        if enabled:
            self._editor_sidebar_visible = self.left_tabs.isVisible()
            self._editor_bottom_visible = self.bottom.isVisible()
            self._editor_find_visible = self.find_bar.isVisible()
            self._hub_ai_visible = self.ai_chat.isVisible()
            self._hub_mode = True
            self.left_tabs.hide()
            self.bottom.hide()
            self.find_bar.hide()
            self.ai_chat.hide()
        else:
            self._hub_mode = False
            self.left_tabs.setVisible(self._editor_sidebar_visible)
            if self._editor_sidebar_visible:
                QTimer.singleShot(0, self._apply_sidebar_width)
            if self._editor_bottom_visible:
                self._reveal_bottom_panel()
            else:
                self.bottom.hide()
            # Find/replace is editor-specific and should only return if an
            # actual source editor is available.
            self.find_bar.setVisible(
                self._editor_find_visible and self.tabs.current_editor() is not None
            )
            self.ai_chat.setVisible(self._ai_visible)
            if self._editor_bottom_visible and self.bottom.currentWidget() is self.bottom.terminal:
                self.bottom.terminal.ensure_started()

    def hub_mode(self) -> bool:
        return self._hub_mode

    def _remember_sidebar_width(self, *_args) -> None:
        if self._hub_mode or not self._editor_sidebar_visible or not self.left_tabs.isVisible():
            return
        sizes = self.workspace.sizes()
        if not sizes:
            return
        width = int(sizes[0])
        if width >= self.MIN_SIDEBAR_WIDTH:
            self._sidebar_width = max(
                self.MIN_SIDEBAR_WIDTH,
                min(width, self.MAX_RESTORED_SIDEBAR_WIDTH),
            )

    def _apply_sidebar_width(self) -> None:
        """Restore a usable Explorer/Search width after show/session restore.

        QSplitter remembers a hidden/collapsed pane as size 0.  Simply calling
        QWidget.show() therefore leaves the Explorer technically visible but
        with zero pixels, which looks like an empty Activity Bar.
        """
        if self._hub_mode or not self._editor_sidebar_visible:
            return
        self.left_tabs.show()
        sizes = self.workspace.sizes()
        if len(sizes) < 3:
            sizes = [self.DEFAULT_SIDEBAR_WIDTH, 900, 0]

        current = max(0, int(sizes[0]))
        if current >= self.MIN_SIDEBAR_WIDTH:
            self._sidebar_width = min(current, self.MAX_RESTORED_SIDEBAR_WIDTH)
            return

        target = max(
            self.MIN_SIDEBAR_WIDTH,
            min(int(self._sidebar_width or self.DEFAULT_SIDEBAR_WIDTH), self.MAX_RESTORED_SIDEBAR_WIDTH),
        )
        right = max(0, int(sizes[2])) if self._ai_visible else 0
        total = max(sum(max(0, int(v)) for v in sizes), self.workspace.width(), target + right + 360)
        center = max(360, total - target - right)
        self.workspace.setSizes([target, center, right])

    def show_explorer(self) -> None:
        self.left_tabs.setCurrentIndex(0)
        self._editor_sidebar_visible = True
        if not self._hub_mode:
            self.left_tabs.show()
            QTimer.singleShot(0, self._apply_sidebar_width)

    def show_search(self, seed: str = "") -> None:
        self.left_tabs.setCurrentWidget(self.search_panel)
        self._editor_sidebar_visible = True
        if not self._hub_mode:
            self.left_tabs.show()
            QTimer.singleShot(0, self._apply_sidebar_width)
        self.search_panel.focus_query(seed)

    def _active_editor_context(self):
        editor = self.tabs.current_editor()
        if not editor:
            return None, ""
        return editor.path, editor.toPlainText()

    def _run_ai_shell(self, command: str, cwd: Path | None = None) -> bool:
        # AI commands always run in the same terminal the user can see and interrupt.
        self.bottom.show_terminal()
        self._reveal_bottom_panel()
        return self.bottom.terminal.run_ai_command(command, cwd)

    def _stop_ai_shell(self) -> bool:
        return self.bottom.terminal.cancel_ai_command()

    def _open_editor_text_overrides(self) -> dict[Path, str]:
        values: dict[Path, str] = {}
        for group in self.tabs.groups:
            for index in range(group.count()):
                editor = group.editor_at(index)
                if editor and editor.path:
                    try:
                        values[editor.path.resolve()] = editor.toPlainText()
                    except OSError:
                        continue
        return values

    def _prepare_ai_changes(self, payload: object) -> None:
        if not self.project_root:
            self.ai_chat.on_code_changes_failed("Open a project before applying AI code changes.")
            return
        data = payload if isinstance(payload, dict) else {"edits": payload}
        edits = data.get("edits") or []
        try:
            change_set = self.ai_change_service.prepare(
                self.project_root,
                edits,
                text_overrides=self._open_editor_text_overrides(),
            )
        except Exception as exc:
            self._ai_change_set = None
            self.ai_chat.on_code_changes_failed(str(exc))
            return

        self._ai_change_set = change_set
        self.ai_chat.on_code_changes_prepared(change_set.summary())
        self._show_ai_diff(change_set, activate=not bool(data.get("auto_apply")))
        if bool(data.get("auto_apply")):
            QTimer.singleShot(0, self._apply_ai_changes)

    def _show_ai_diff(
        self,
        change_set: PreparedChangeSet | None = None,
        *,
        activate: bool = True,
    ) -> AIDiffView | None:
        if change_set is None:
            change_set = self._ai_change_set
        if change_set is None:
            return None

        def factory():
            view = AIDiffView()
            view.apply_all_requested.connect(self._apply_ai_changes)
            view.reject_all_requested.connect(self._reject_ai_changes)
            return view

        view = self.open_tool_tab(
            "ai-diff",
            "AI Changes",
            factory,
            activate=activate,
        )
        if isinstance(view, AIDiffView):
            view.set_change_set(change_set)
            return view
        return None

    def _review_ai_changes(self) -> None:
        if not self._ai_change_set:
            self.status_message.emit("No pending AI code changes")
            return
        self._show_ai_diff(self._ai_change_set, activate=True)

    def _reload_applied_editors(self, change_set: PreparedChangeSet) -> None:
        for change in change_set.changes:
            target = change.absolute_path.resolve()
            for group in self.tabs.groups:
                found = group.find_editor(target)
                if not found:
                    continue
                _index, editor = found
                editor.setPlainText(change.after)
                editor.document().setModified(False)
        if self.project_root:
            self.index.set_root(self.project_root)
            self.explorer_panel.tree.refresh()

    def _apply_ai_changes(self) -> None:
        change_set = self._ai_change_set
        if not change_set:
            self.status_message.emit("No pending AI code changes")
            return
        try:
            applied, backup = self.ai_change_service.apply(change_set)
        except Exception as exc:
            self.ai_chat.on_code_changes_failed(str(exc))
            self.status_message.emit(f"AI code apply failed: {exc}")
            return

        self._reload_applied_editors(change_set)
        paths = [path.relative_to(change_set.project_root).as_posix() for path in applied]
        view = self.tool_widget("ai-diff")
        if isinstance(view, AIDiffView):
            view.mark_applied(backup)
        self.ai_chat.on_code_changes_applied(paths, str(backup or ""))
        self.bottom.console.append(
            f"[AI] Applied {len(paths)} code file(s)"
            + (f"; backup: {backup}" if backup else "")
        )
        self._ai_change_set = None
        self.status_message.emit(f"AI code applied: {len(paths)} file(s)")

    def _reject_ai_changes(self) -> None:
        if not self._ai_change_set:
            return
        self.ai_change_service.reject()
        self._ai_change_set = None
        view = self.tool_widget("ai-diff")
        if isinstance(view, AIDiffView):
            view.mark_rejected()
        self.ai_chat.on_code_changes_rejected()
        self.status_message.emit("AI code changes rejected")

    def _ask_ai_about_problems(self, question: str) -> None:
        """Nhan loi trich tu PROBLEMS -> dua sang Chat AI (prefill, khong auto-gui)."""
        if not str(question or "").strip():
            return
        self.status_message.emit("Problem sent to Chat AI — press Enter to ask")
        self.set_ai_visible(True)
        self.ai_chat.prefill_question(question)

    def set_ai_visible(self, visible: bool) -> None:
        self._ai_visible = bool(visible)
        if self._hub_mode:
            self.ai_chat.hide()
            return
        self.ai_chat.setVisible(self._ai_visible)
        if self._ai_visible:
            sizes = self.workspace.sizes()
            total = max(1, sum(sizes) or self.workspace.width())
            left = sizes[0] if len(sizes) >= 1 and self._editor_sidebar_visible else 0
            right = min(390, max(300, total // 4))
            center = max(360, total - left - right)
            self.workspace.setSizes([left, center, right])
            self.ai_chat.prompt.setFocus(Qt.FocusReason.OtherFocusReason)

    def toggle_ai(self) -> None:
        self.set_ai_visible(not self._ai_visible)

    def ai_visible(self) -> bool:
        return bool(self._ai_visible)

    def set_sidebar_visible(self, visible: bool) -> None:
        visible = bool(visible)
        if not visible:
            self._remember_sidebar_width()
        self._editor_sidebar_visible = visible
        if not self._hub_mode:
            self.left_tabs.setVisible(visible)
            if visible:
                QTimer.singleShot(0, self._apply_sidebar_width)

    def sidebar_visible(self) -> bool:
        return bool(self._editor_sidebar_visible)

    def toggle_sidebar(self) -> None:
        self.set_sidebar_visible(not self._editor_sidebar_visible)

    def _remember_bottom_panel_height(self, *_args) -> None:
        if not self.bottom.isVisible():
            return
        sizes = self.vertical.sizes()
        if len(sizes) != 2:
            return
        height = int(sizes[1])
        if height >= self.MIN_BOTTOM_PANEL_HEIGHT:
            self._bottom_panel_height = min(
                height,
                self.MAX_RESTORED_BOTTOM_PANEL_HEIGHT,
            )

    def _apply_bottom_panel_height(self) -> None:
        total = max(1, self.vertical.height())
        target = max(
            self.MIN_BOTTOM_PANEL_HEIGHT,
            min(self._bottom_panel_height, self.MAX_RESTORED_BOTTOM_PANEL_HEIGHT),
        )
        # Keep most of the screen for code, even on smaller displays.
        target = min(target, max(self.MIN_BOTTOM_PANEL_HEIGHT, total // 3))
        self.vertical.setSizes([max(1, total - target), target])

    def _reveal_bottom_panel(self) -> None:
        self._editor_bottom_visible = True
        if self._hub_mode:
            return
        self.bottom.show()
        self._apply_bottom_panel_height()

    def toggle_bottom_panel(self) -> None:
        if self._editor_bottom_visible and self.bottom.isVisible():
            self.hide_bottom_panel()
        else:
            self._reveal_bottom_panel()

    def show_bottom_panel(self) -> None:
        self._reveal_bottom_panel()

    def hide_bottom_panel(self) -> None:
        self._remember_bottom_panel_height()
        self._editor_bottom_visible = False
        self.bottom.hide()

    def show_console(self) -> None:
        self.bottom.show_console()
        self._reveal_bottom_panel()

    def toggle_console(self) -> None:
        is_console = self.bottom.currentWidget() is self.bottom.console
        if self._editor_bottom_visible and self.bottom.isVisible() and is_console:
            self.hide_bottom_panel()
        else:
            self.bottom.show_console()
            self._reveal_bottom_panel()

    def show_terminal(self) -> None:
        self.bottom.show_terminal()
        self._reveal_bottom_panel()

    def toggle_terminal(self) -> None:
        is_terminal = self.bottom.currentWidget() is self.bottom.terminal
        if self._editor_bottom_visible and self.bottom.isVisible() and is_terminal:
            self.hide_bottom_panel()
        else:
            self.bottom.show_terminal()
            self._reveal_bottom_panel()

    def new_terminal(self) -> None:
        self.bottom.setCurrentWidget(self.bottom.terminal)
        self.bottom.terminal.new_terminal()
        self._reveal_bottom_panel()

    def show_hex(self, path: str | Path) -> bool:
        if not self.bottom.show_hex(path):
            return False
        self._reveal_bottom_panel()
        return True

    def kill_terminal(self) -> None:
        self.bottom.terminal.kill_terminal()

    def clear_terminal(self) -> None:
        self.bottom.terminal.clear()

    def clear_console(self) -> None:
        self.bottom.console.clear()

    def open_file(self, path: str | Path) -> None:
        self.tabs.open_file(path)

    def open_location(self, path: str | Path, line: int, column: int = 1) -> None:
        editor = self.tabs.open_file(path)
        if editor:
            editor.goto_line(line, column)

    def show_find(self, replace: bool = False) -> None:
        editor = self.tabs.current_editor()
        if not editor:
            return
        seed = editor.textCursor().selectedText().replace("\u2029", " ")
        self.find_bar.set_editor(editor)
        self._editor_find_visible = True
        if not self._hub_mode:
            self.find_bar.show_find(replace, seed)

    def find_next(self) -> None:
        self.find_bar.find_next()

    def find_previous(self) -> None:
        self.find_bar.find_previous()

    def focus_project_search(self, seed: str = "") -> None:
        self.show_search(seed)

    def _current_editor_changed(self, editor) -> None:
        self.find_bar.set_editor(editor)
        if editor:
            editor.completion.set_project_symbols(self.index.names())

    def _file_saved(self, path: Path) -> None:
        self.index.index_file(path)
        for i in range(self.tabs.count()):
            ed = self.tabs.editor_at(i)
            if ed:
                ed.completion.set_project_symbols(self.index.names())
        self.status_message.emit(f"Saved: {path}")
        self.bottom.console.append(f"Saved: {path}")

    def _diagnostics_changed(self, path, diagnostics) -> None:
        self.bottom.problems.set_diagnostics(path, diagnostics)
        idx = self.bottom.indexOf(self.bottom.problems)
        errors = sum(1 for d in diagnostics if getattr(d.severity, "value", "") == "error")
        warnings = sum(1 for d in diagnostics if getattr(d.severity, "value", "") == "warning")
        self.bottom.setTabText(idx, f"PROBLEMS ({errors + warnings})" if (errors or warnings) else "PROBLEMS")
        self.problems_changed.emit(errors, warnings)

    def _go_current_definition(self) -> None:
        editor = self.tabs.current_editor()
        if editor:
            editor.go_to_definition()

    def go_to_definition(self, symbol: str, current_path) -> None:
        found = self.index.find_definition(symbol, current_path)
        if not found:
            self.status_message.emit(f"Definition not found: {symbol}")
            self.bottom.console.append(f"Definition not found: {symbol}")
            return
        self.open_location(found.path, found.line, found.column)
        self.status_message.emit(f"Definition: {found.name} — {found.path.name}:{found.line}")

    def append_build_log(self, text: str) -> None:
        self.bottom.build_log.append(text)

    def clear_build_log(self) -> None:
        self.bottom.build_log.text.clear()
        self.bottom.show_build()
        self.show_bottom_panel()

    def append_console(self, text: str) -> None:
        self.bottom.console.append(text)

    def workspace_state(self) -> dict:
        return {
            "editor_groups": self.tabs.session_state(),
            "sidebar": {
                "visible": bool(self._editor_sidebar_visible),
                "active": "search" if self.left_tabs.currentWidget() is self.search_panel else "explorer",
                "workspace_sizes": self.workspace.sizes()[:2],
                "preferred_width": int(self._sidebar_width),
            },
            "panel": {
                "visible": bool(self._editor_bottom_visible),
                "active_key": self.bottom.active_key(),
                "active_index": self.bottom.currentIndex(),
                "vertical_sizes": self.vertical.sizes(),
                "preferred_height": int(self._bottom_panel_height),
            },
            "secondary_sidebar": {
                "visible": bool(self._ai_visible),
                "workspace_sizes": self.workspace.sizes(),
            },
        }

    def restore_layout_state(self, state: dict) -> None:
        sidebar = state.get("sidebar", {}) if isinstance(state, dict) else {}
        panel = state.get("panel", {}) if isinstance(state, dict) else {}
        if sidebar.get("active") == "search":
            self.left_tabs.setCurrentWidget(self.search_panel)
        else:
            self.left_tabs.setCurrentWidget(self.explorer_panel)
        self._editor_sidebar_visible = bool(sidebar.get("visible", True))
        preferred_width = sidebar.get("preferred_width", self.DEFAULT_SIDEBAR_WIDTH)
        try:
            preferred_width = int(preferred_width)
        except (TypeError, ValueError):
            preferred_width = self.DEFAULT_SIDEBAR_WIDTH
        self._sidebar_width = max(
            self.MIN_SIDEBAR_WIDTH,
            min(preferred_width, self.MAX_RESTORED_SIDEBAR_WIDTH),
        )
        self.left_tabs.setVisible(self._editor_sidebar_visible and not self._hub_mode)
        secondary = state.get("secondary_sidebar", {}) if isinstance(state, dict) else {}
        workspace_sizes = secondary.get("workspace_sizes") or sidebar.get("workspace_sizes")
        if isinstance(workspace_sizes, list):
            try:
                restored = [max(0, int(v)) for v in workspace_sizes]
            except (TypeError, ValueError):
                restored = []
            if len(restored) == 3:
                if self._editor_sidebar_visible and restored[0] < self.MIN_SIDEBAR_WIDTH:
                    restored[0] = self._sidebar_width
                self.workspace.setSizes(restored)
            elif len(restored) == 2:
                left = restored[0]
                if self._editor_sidebar_visible and left < self.MIN_SIDEBAR_WIDTH:
                    left = self._sidebar_width
                self.workspace.setSizes([left, max(1, restored[1]), 0])
        self._ai_visible = bool(secondary.get("visible", False))
        self.ai_chat.setVisible(self._ai_visible and not self._hub_mode)
        if self._editor_sidebar_visible and not self._hub_mode:
            QTimer.singleShot(0, self._apply_sidebar_width)

        active_key = panel.get("active_key")
        if active_key:
            self.bottom.set_active_key(str(active_key))
        else:
            try:
                index = int(panel.get("active_index", 0))
                if 0 <= index < self.bottom.count():
                    self.bottom.setCurrentIndex(index)
            except (TypeError, ValueError):
                pass

        # v1.10.1 startup policy: the bottom panel is always hidden initially.
        # We still remember its active tab and preferred height, so Ctrl+J /
        # Toggle Terminal opens the same panel at a compact size.
        vertical_sizes = panel.get("vertical_sizes")
        saved_preferred = panel.get("preferred_height")
        if saved_preferred is not None:
            try:
                self._bottom_panel_height = max(
                    self.MIN_BOTTOM_PANEL_HEIGHT,
                    min(int(saved_preferred), self.MAX_RESTORED_BOTTOM_PANEL_HEIGHT),
                )
            except (TypeError, ValueError):
                pass
        elif isinstance(vertical_sizes, list) and len(vertical_sizes) == 2:
            try:
                saved_height = int(vertical_sizes[1])
            except (TypeError, ValueError):
                saved_height = self.DEFAULT_BOTTOM_PANEL_HEIGHT
            if saved_height > 0:
                self._bottom_panel_height = max(
                    self.MIN_BOTTOM_PANEL_HEIGHT,
                    min(saved_height, self.MAX_RESTORED_BOTTOM_PANEL_HEIGHT),
                )
        self._editor_bottom_visible = False
        self.bottom.hide()

    def connect_workspace_state_changed(self, callback) -> None:
        self.tabs.group_structure_changed.connect(callback)
        self.tabs.splitter.splitterMoved.connect(lambda *_: callback())
        self.workspace.splitterMoved.connect(lambda *_: callback())
        self.vertical.splitterMoved.connect(lambda *_: callback())
        self.ai_chat.visibility_requested.connect(lambda *_: callback())
        self.left_tabs.currentChanged.connect(lambda *_: callback())
        self.bottom.currentChanged.connect(lambda *_: callback())
        self.bottom.close_requested.connect(lambda *_: callback())

    def shutdown(self) -> None:
        self.bottom.shutdown()
        self.ai_chat.shutdown()

    def can_close(self) -> bool:
        return self.tabs.close_all()
