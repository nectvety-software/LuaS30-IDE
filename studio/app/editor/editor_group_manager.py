from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from .editor_tabs import EditorTabs


class EditorGroupManager(QWidget):
    """VS Code-like editor groups backed by multiple EditorTabs instances."""

    cursor_info_changed = Signal(int, int, int)
    file_opened = Signal(object)
    file_saved = Signal(object)
    current_editor_changed = Signal(object)
    diagnostics_changed = Signal(object, object)
    go_to_definition_requested = Signal(str, object)
    request_find = Signal(bool)
    currentChanged = Signal(int)
    group_structure_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        root.addWidget(self.splitter)
        self.groups: list[EditorTabs] = []
        self._active_group = 0
        self.add_group()

    @property
    def active_group_index(self) -> int:
        return min(self._active_group, max(0, len(self.groups) - 1))

    def active_tabs(self) -> EditorTabs:
        return self.groups[self.active_group_index]

    def add_group(self, after_index: int | None = None) -> EditorTabs:
        tabs = EditorTabs()
        self._wire_group(tabs)
        if after_index is None or after_index >= len(self.groups) - 1:
            self.groups.append(tabs)
            self.splitter.addWidget(tabs)
            self._active_group = len(self.groups) - 1
        else:
            insert_at = max(0, after_index + 1)
            self.groups.insert(insert_at, tabs)
            self.splitter.insertWidget(insert_at, tabs)
            self._active_group = insert_at
        self._normalize_sizes()
        self.group_structure_changed.emit()
        return tabs

    def ensure_group_count(self, count: int) -> None:
        count = max(1, int(count))
        while len(self.groups) < count:
            self.add_group(len(self.groups) - 1)
        while len(self.groups) > count:
            self.remove_group(len(self.groups) - 1, force=True)

    def remove_group(self, index: int, force: bool = False) -> bool:
        if len(self.groups) <= 1:
            return False
        if index < 0 or index >= len(self.groups):
            return False
        tabs = self.groups[index]
        if not force and not tabs.close_all():
            return False
        self.groups.pop(index)
        tabs.setParent(None)
        tabs.deleteLater()
        self._active_group = min(self._active_group, len(self.groups) - 1)
        self._normalize_sizes()
        self.group_structure_changed.emit()
        self._emit_active_state()
        return True

    def split_right(self) -> int:
        current = self.active_group_index
        self.add_group(current)
        return self.active_group_index

    def close_active_group(self) -> bool:
        return self.remove_group(self.active_group_index)

    def set_active_group(self, index: int) -> None:
        if not self.groups:
            return
        self._active_group = max(0, min(int(index), len(self.groups) - 1))
        self._emit_active_state()

    def _wire_group(self, tabs: EditorTabs) -> None:
        tabs.cursor_info_changed.connect(self.cursor_info_changed)
        tabs.file_opened.connect(self.file_opened)
        tabs.file_saved.connect(self.file_saved)
        tabs.current_editor_changed.connect(self.current_editor_changed)
        tabs.diagnostics_changed.connect(self.diagnostics_changed)
        tabs.go_to_definition_requested.connect(self.go_to_definition_requested)
        tabs.request_find.connect(self.request_find)
        tabs.state_changed.connect(self.group_structure_changed)
        tabs.currentChanged.connect(lambda index, t=tabs: self._group_current_changed(t, index))
        tabs.tabBarClicked.connect(lambda _index, t=tabs: self._activate_group_for(t))
        tabs.tabCloseRequested.connect(lambda _index: self.group_structure_changed.emit())
        tabs.close_all_requested.connect(self.close_all)

    def _activate_group_for(self, tabs: EditorTabs) -> None:
        try:
            self._active_group = self.groups.index(tabs)
        except ValueError:
            return
        self._emit_active_state()

    def _group_current_changed(self, tabs: EditorTabs, index: int) -> None:
        self._activate_group_for(tabs)
        self.currentChanged.emit(index)
        self.group_structure_changed.emit()

    def _emit_active_state(self) -> None:
        tabs = self.active_tabs()
        editor = tabs.current_editor()
        self.current_editor_changed.emit(editor)
        self.currentChanged.emit(tabs.currentIndex())

    def _normalize_sizes(self) -> None:
        if self.groups:
            self.splitter.setSizes([1] * len(self.groups))

    # --------- Active-group editor API ---------
    def current_editor(self):
        return self.active_tabs().current_editor()

    def current_tool_key(self):
        return self.active_tabs().current_tool_key()

    def new_file(self):
        return self.active_tabs().new_file()

    def save_current(self) -> bool:
        return self.active_tabs().save_current()

    def save_current_as(self) -> bool:
        return self.active_tabs().save_current_as()

    def save_all(self) -> bool:
        return all(group.save_all() for group in self.groups)

    def open_file(self, path: str | Path, *, activate: bool = True):
        resolved = Path(path).resolve()
        for i, group in enumerate(self.groups):
            found = group.find_editor(resolved)
            if found:
                if activate:
                    self._active_group = i
                    group.setCurrentIndex(found[0])
                return found[1]
        return self.active_tabs().open_file(resolved, activate=activate)

    def open_file_in_group(
        self,
        group_index: int,
        path: str | Path,
        *,
        activate: bool = True,
    ):
        if activate:
            self.set_active_group(group_index)
            return self.active_tabs().open_file(path, activate=True)
        if not self.groups:
            self.add_group()
        target_index = max(0, min(int(group_index), len(self.groups) - 1))
        return self.groups[target_index].open_file(path, activate=False)

    def set_ai_file_status(self, path: str | Path, state: str) -> bool:
        """Apply an AI status badge to the matching file tab in any editor group."""
        resolved = Path(path).resolve()
        for group in self.groups:
            if group.find_editor(resolved):
                return group.set_ai_file_status(resolved, state)
        return False

    def clear_ai_file_status(self, path: str | Path) -> bool:
        resolved = Path(path).resolve()
        for group in self.groups:
            if group.find_editor(resolved):
                return group.clear_ai_file_status(resolved)
        return False

    def open_untitled_in_group(self, group_index: int, text: str = "", modified: bool = True):
        self.set_active_group(group_index)
        editor = self.active_tabs().new_file()
        editor.setPlainText(text)
        editor.document().setModified(bool(modified))
        return editor

    def open_tool_tab(
        self,
        key: str,
        title: str,
        widget_factory,
        icon=None,
        *,
        insert_at: int | None = None,
        activate: bool = True,
    ):
        existing = self.tool_widget(key)
        if existing is not None:
            for i, group in enumerate(self.groups):
                idx = group.indexOf(existing)
                if idx >= 0:
                    if insert_at is not None:
                        target = max(0, min(int(insert_at), group.count() - 1))
                        if idx != target:
                            group.tabBar().moveTab(idx, target)
                            idx = target
                    if activate:
                        self._active_group = i
                        group.setCurrentIndex(idx)
                    return existing
        return self.active_tabs().open_tool_tab(
            key, title, widget_factory, icon,
            insert_at=insert_at, activate=activate,
        )

    def open_tool_tab_in_group(
        self,
        group_index: int,
        key: str,
        title: str,
        widget_factory,
        icon=None,
        *,
        insert_at: int | None = None,
        activate: bool = True,
    ):
        if not self.groups:
            self.add_group()
        target_index = max(0, min(int(group_index), len(self.groups) - 1))
        existing = self.tool_widget(key)
        if existing is not None:
            for i, group in enumerate(self.groups):
                idx = group.indexOf(existing)
                if idx >= 0:
                    if insert_at is not None:
                        target = max(0, min(int(insert_at), group.count() - 1))
                        if idx != target:
                            group.tabBar().moveTab(idx, target)
                            idx = target
                    if activate:
                        self._active_group = i
                        group.setCurrentIndex(idx)
                    return existing
        group = self.groups[target_index]
        widget = group.open_tool_tab(
            key, title, widget_factory, icon,
            insert_at=insert_at, activate=activate,
        )
        if activate:
            self._active_group = target_index
        return widget

    def tool_widget(self, key: str):
        for group in self.groups:
            widget = group.tool_widget(key)
            if widget is not None:
                return widget
        return None

    def focus_tool_tab(self, key: str) -> bool:
        for i, group in enumerate(self.groups):
            if group.focus_tool_tab(key):
                self._active_group = i
                return True
        return False

    def find_next(self):
        editor = self.current_editor()
        return editor

    def count(self) -> int:
        return sum(group.count() for group in self.groups)

    def editor_at(self, flat_index: int):
        index = int(flat_index)
        for group in self.groups:
            if index < group.count():
                return group.editor_at(index)
            index -= group.count()
        return None

    def show_empty_editor(self, close_tool_tabs: bool = False) -> None:
        """Show a blank central editor without opening a document.

        When close_tool_tabs is true, tool tabs restored from the previous session are
        removed so startup can be completely empty while preserving group layout.
        """
        if close_tool_tabs:
            for group in self.groups:
                for index in range(group.count() - 1, -1, -1):
                    if group.editor_at(index) is None:
                        group.close_tab(index)
        self.set_active_group(0)
        for group in self.groups:
            if group.count() == 0:
                group.setCurrentIndex(-1)
        self._emit_active_state()
        self.group_structure_changed.emit()

    def close_file_tabs(self) -> bool:
        return all(group.close_file_tabs() for group in self.groups)

    def close_all(self) -> bool:
        for group in self.groups:
            if not group.close_all():
                return False
        return True

    # --------- Session state ---------
    def session_state(self) -> dict:
        groups = []
        for group_index, tabs in enumerate(self.groups):
            entries = []
            for tab_index in range(tabs.count()):
                editor = tabs.editor_at(tab_index)
                widget = tabs.widget(tab_index)
                if editor is not None:
                    if editor.path:
                        entry = {"type": "file", "path": str(editor.path)}
                    else:
                        entry = {
                            "type": "untitled",
                            "text": editor.toPlainText(),
                            "modified": bool(editor.document().isModified()),
                        }
                else:
                    key = widget.property("luas30ToolKey") if widget else None
                    if not key:
                        continue
                    entry = {"type": "tool", "key": str(key), "title": tabs.tabText(tab_index)}
                entries.append(entry)
            groups.append({
                "id": f"group-{group_index}",
                "tabs": entries,
                "active_tab": max(-1, tabs.currentIndex()),
            })
        return {
            "groups": groups,
            "active_group": self.active_group_index,
            "group_sizes": self.splitter.sizes(),
        }

    def set_group_sizes(self, sizes: list[int]) -> None:
        if sizes and len(sizes) == len(self.groups):
            self.splitter.setSizes([max(1, int(x)) for x in sizes])
