from __future__ import annotations

import copy
import json
import os
import shutil
import sys
from pathlib import Path

from app.ui import icons, palette
from PySide6.QtCore import QProcess, QTimer, Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QStatusBar, QToolButton, QVBoxLayout, QWidget,
)

from app.core.paths import resolve_script, tool_python
from app.core.utf8 import decode_process_bytes, utf8_qprocess_environment

from app.core.project_session import ProjectSession
from app.core.workspace_session import WorkspaceSessionStore
from app.services.build_service import BuildService
from app.services.compat_matrix_service import CompatMatrixService
from app.services.emulator_service import EmulatorService
from app.services.project_library import ProjectLibraryService
from app.ui.about_dialog import AboutDialog
from app.ui.command_palette import CommandPalette
from app.ui.icons import apply_action_icon, apply_icon, font_icon
from app.ui.mediatek_mre_dialog import MediaTekMREConfigDialog
from app.views.assets_view import AssetsView
from app.views.code_editor_view import CodeEditorView
from app.views.compat_matrix_view import CompatMatrixView
from app.views.emulator_view import EmulatorView
from app.views.project_doctor_view import ProjectDoctorView
from app.views.project_manager_view import ProjectManagerView
from app.views.settings_view import SettingsView
from app.views.start_page_view import StartPageView
from app.views.toolchain_doctor_view import ToolchainDoctorView
from app.views.ui_designer_view import UIDesignerView


class MainWindow(QMainWindow):
    VERSION = "1.0.1"

    def __init__(self, engine_root: Path) -> None:
        super().__init__()
        self.engine_root = Path(engine_root).resolve()
        self.session = ProjectSession(self.engine_root, self)
        self.workspace_session = WorkspaceSessionStore()
        self._restoring_workspace = False
        self._startup_mode = "welcome"
        self._compiler_profile = "auto"
        self._toolchain_root = self.engine_root / "toolchain" / "arm-gcc"
        self._compat_profile = "auto"
        self._mre_sdk_root: Path | None = None
        self._device_imsi = ""
        self.project_library = ProjectLibraryService(
            self.session.default_projects_root,
            self.engine_root / "templates" / "basic",
        )
        self.build_service = BuildService(self.engine_root, self)
        self.build_service.set_compiler_profile(self._compiler_profile)
        self.build_service.set_toolchain_root(self._toolchain_root)
        self.build_service.set_compat_profile(self._compat_profile)
        self.build_service.set_mre_sdk_root(self._mre_sdk_root)
        self.emulator_service = EmulatorService(self.engine_root, self)
        self.compat_matrix_service = CompatMatrixService(self.engine_root, self)
        self.activity_buttons: dict[str, QToolButton] = {}
        self._project_hub_mode = False
        self._editor_activity_bar_visible = True
        self.run_after_build = False
        self.last_manifest: dict = {}
        self._workspace_save_timer = QTimer(self)
        self._workspace_save_timer.setSingleShot(True)
        self._workspace_save_timer.setInterval(450)
        self._workspace_save_timer.timeout.connect(self._save_workspace_session)

        self.setWindowTitle(f"LuaS30 IDE {self.VERSION}")
        window_icon = icons.app_icon(self.engine_root)
        if not window_icon.isNull():
            self.setWindowIcon(window_icon)
        self.resize(1440, 860)
        self.setMinimumSize(980, 620)

        self._create_actions()
        self._create_menus()

        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_workbench_bar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.activity_bar = self._build_activity_bar()
        body.addWidget(self.activity_bar)

        # v1.9 uses one editor workbench. Files and tools share the same central tab strip.
        self.editor_view = CodeEditorView(self.engine_root)
        body.addWidget(self.editor_view, 1)
        outer.addLayout(body, 1)

        self._create_statusbar()
        self._wire_events()
        self._load_initial_project()

        # Terminal tu chay nen (an, khong can Enter) + dialog thiet lap lan dau.
        QTimer.singleShot(900, self._autostart_terminal)
        QTimer.singleShot(800, self._maybe_first_run_setup)

    # ---------------------------------------------------------------- UI
    def _build_workbench_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("WorkbenchBar")
        bar.setFixedHeight(32)
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 2, 8, 2)
        row.setSpacing(6)

        brand = QLabel()
        brand.setObjectName("WindowBrand")
        brand.setToolTip(f"LuaS30 IDE {self.VERSION}")
        logo = icons.app_logo_pixmap(self.engine_root, height=22, device_ratio=brand.devicePixelRatioF())
        if logo.isNull():
            brand.setText("LuaS30")
        else:
            brand.setPixmap(logo)
            brand.setFixedSize(logo.size())
        self.project_label = QLabel("No Folder")
        self.project_label.setObjectName("ProjectName")

        self.command_button = QPushButton("Command Palette")
        self.command_button.setObjectName("CommandCenter")
        self.command_button.setToolTip("Command Palette (Ctrl+Shift+P)")
        apply_icon(self.command_button, "search", 13)

        self.workbench_state = QLabel("Ready")
        self.workbench_state.setObjectName("WorkbenchState")

        row.addWidget(brand)
        row.addWidget(self.project_label)
        row.addStretch(1)
        row.addWidget(self.command_button, 2)
        row.addStretch(1)

        self._build_menu_tools()
        return bar

    def _build_menu_tools(self) -> None:
        """Gắn cụm nút công cụ + nhãn trạng thái vào góc phải hàng menu `File`.

        Cụm này trước nằm ở cuối `WorkbenchBar`. Chuyển lên hàng menu để nhường
        chỗ cho Command Palette và để cụm khỏi bị bóp ở mép phải cửa sổ — vẫn là
        các nút icon nhỏ, canh phải như cũ.
        """
        cluster = QFrame()
        cluster.setObjectName("MenuToolsCluster")
        row = QHBoxLayout(cluster)
        row.setContentsMargins(6, 0, 6, 0)
        row.setSpacing(4)

        self.build_button = QToolButton()
        self.build_button.setObjectName("WorkbenchLayoutButton")
        self.build_button.setDefaultAction(self.build_action)
        self.build_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.build_button.setAutoRaise(True)

        self.run_button = QToolButton()
        self.run_button.setObjectName("WorkbenchLayoutButton")
        self.run_button.setDefaultAction(self.run_action)
        self.run_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.run_button.setAutoRaise(True)

        self.explorer_toggle_button = QToolButton()
        self.explorer_toggle_button.setObjectName("WorkbenchLayoutButton")
        self.explorer_toggle_button.setDefaultAction(self.toggle_sidebar_action)
        self.explorer_toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.explorer_toggle_button.setAutoRaise(True)
        self.explorer_toggle_button.setToolTip("Toggle Explorer / Primary Side Bar (Ctrl+B)")

        self.activity_toggle_button = QToolButton()
        self.activity_toggle_button.setObjectName("WorkbenchLayoutButton")
        self.activity_toggle_button.setDefaultAction(self.toggle_activity_bar_action)
        self.activity_toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.activity_toggle_button.setAutoRaise(True)
        self.activity_toggle_button.setToolTip("Toggle Activity Bar (Ctrl+Alt+A)")

        self.ai_toggle_button = QToolButton()
        self.ai_toggle_button.setObjectName("WorkbenchLayoutButton")
        self.ai_toggle_button.setDefaultAction(self.toggle_ai_chat_action)
        self.ai_toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.ai_toggle_button.setAutoRaise(True)
        self.ai_toggle_button.setToolTip("Toggle Chat AI (Ctrl+Alt+I)")

        for widget in (
            self.build_button,
            self.run_button,
            self.explorer_toggle_button,
            self.activity_toggle_button,
            self.ai_toggle_button,
            self.workbench_state,
        ):
            row.addWidget(widget)

        self.menu_tools_cluster = cluster
        # Phải giữ tham chiếu Python: setCornerWidget KHÔNG chuyển quyền sở hữu
        # sang C++ (cornerWidget() trả None ngay sau khi set nếu widget không còn
        # ai giữ), nên chỉ dùng biến cục bộ là GC xoá cả cụm widget.
        self.menuBar().setCornerWidget(cluster, Qt.Corner.TopRightCorner)

    def _build_activity_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("ActivityBar")
        bar.setFixedWidth(48)
        col = QVBoxLayout(bar)
        col.setContentsMargins(0, 1, 0, 1)
        col.setSpacing(0)

        items = [
            ("explorer", "folder", "Explorer (Ctrl+Shift+E)"),
            ("search", "search", "Search (Ctrl+Shift+F)"),
            ("projects", "projects", "Project Storage"),
            ("assets", "image", "Assets"),
            ("designer", "designer", "UI Designer"),
            ("emulator", "play", "Emulator"),
            ("ai", "chat", "Chat AI (Ctrl+Alt+I)"),
        ]
        for key, icon_name, tooltip in items:
            button = self._activity_button(icon_name, tooltip)
            button.clicked.connect(lambda _checked=False, k=key: self._activity_clicked(k))
            self.activity_buttons[key] = button
            col.addWidget(button)

        col.addStretch(1)
        settings = self._activity_button("settings", "Settings")
        settings.clicked.connect(lambda: self._activity_clicked("settings"))
        self.activity_buttons["settings"] = settings
        col.addWidget(settings)
        return bar

    @staticmethod
    def _activity_button(icon_name: str, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName("ActivityButton")
        button.setText("")
        apply_icon(button, icon_name, 19, "palette.TEXT_3")
        button.setToolTip(tooltip)
        button.setCheckable(True)
        button.setAutoRaise(True)
        return button

    def _create_actions(self) -> None:
        def action(text: str, shortcut: str | None = None, icon_name: str | None = None) -> QAction:
            obj = QAction(text, self)
            if shortcut:
                obj.setShortcut(QKeySequence(shortcut))
            if icon_name:
                apply_action_icon(obj, icon_name)
            self.addAction(obj)
            return obj

        # File / project
        self.new_project_action = action("New Project...", "Ctrl+Shift+N", "add")
        self.open_project_action = action("Open Folder...", "Ctrl+K, Ctrl+O", "folder_open")
        self.welcome_action = action("Welcome", icon_name="home")
        self.project_storage_action = action("Project Storage", "Ctrl+Alt+P", "projects")
        self.close_project_action = action("Close Project", icon_name="close")
        self.new_file_action = action("New File", "Ctrl+N", "new_file")
        self.open_file_action = action("Open File...", "Ctrl+O", "file")
        self.save_action = action("Save", "Ctrl+S", "save")
        self.save_as_action = action("Save As...", "Ctrl+Shift+S", "save")
        self.save_all_action = action("Save All", "Ctrl+Alt+S", "save")
        self.exit_action = action("Exit", icon_name="close")

        # Edit
        self.undo_action = action("Undo", "Ctrl+Z", "undo")
        self.redo_action = action("Redo", "Ctrl+Y", "redo")
        self.cut_action = action("Cut", "Ctrl+X", "cut")
        self.copy_action = action("Copy", "Ctrl+C", "copy")
        self.paste_action = action("Paste", "Ctrl+V", "paste")
        self.select_all_action = action("Select All", "Ctrl+A", "select_all")
        self.find_action = action("Find", "Ctrl+F", "search")
        self.replace_action = action("Replace", "Ctrl+H", "edit")
        self.find_next_action = action("Find Next", "F3", "chevron_down")
        self.find_prev_action = action("Find Previous", "Shift+F3", "chevron_up")
        self.project_search_action = action("Find in Files", "Ctrl+Shift+F", "search")
        self.definition_action = action("Go to Definition", "F12", "forward")
        self.completion_action = action("Trigger Completion", "Ctrl+Space", "code")

        # View
        self.explorer_action = action("Focus Explorer", "Ctrl+Shift+E", "folder")
        self.toggle_sidebar_action = action("Toggle Explorer / Primary Side Bar", "Ctrl+B", "folder")
        self.toggle_sidebar_action.setCheckable(True)
        self.toggle_sidebar_action.setChecked(True)
        self.toggle_activity_bar_action = action("Toggle Activity Bar", "Ctrl+Alt+A", "menu")
        self.toggle_activity_bar_action.setCheckable(True)
        self.toggle_activity_bar_action.setChecked(True)
        self.toggle_panel_action = action("Toggle Panel", "Ctrl+J")
        self.toggle_console_action = action("Toggle Console", "Ctrl+Shift+Y", "console")
        self.toggle_terminal_action = action("Toggle Terminal", "Ctrl+`", "terminal")
        self.toggle_ai_chat_action = action("Toggle Chat AI", "Ctrl+Alt+I", "chat")
        self.toggle_ai_chat_action.setCheckable(True)
        self.command_palette_action = action("Command Palette", "Ctrl+Shift+P", "search")
        self.split_editor_action = action("Split Editor Right", "Ctrl+\\")
        self.close_editor_group_action = action("Close Editor Group")

        # Run
        self.build_action = action("Build VXP", "Ctrl+Shift+B", "build")
        self.run_action = action("Build and Run", "F5", "play")
        self.run_last_action = action("Run Last Build", "Ctrl+F5", "play")
        self.stop_emulator_action = action("Stop Emulator", "Shift+F5", "stop")
        self.cancel_build_action = action("Cancel Build", icon_name="stop")

        # Integrated terminal / console panel
        self.new_terminal_action = action("New Terminal", "Ctrl+Shift+`", "terminal")
        self.kill_terminal_action = action("Kill Terminal", icon_name="stop")
        self.clear_terminal_action = action("Clear Terminal", icon_name="delete")
        self.clear_console_action = action("Clear Console", icon_name="delete")

        # Tools: selecting a feature opens/focuses an editor-area tab.
        self.project_doctor_action = action("Project Doctor", icon_name="check")
        self.compat_matrix_action = action("Runtime Compatibility Matrix", icon_name="check")
        self.toolchain_doctor_action = action("Toolchain Doctor", icon_name="build")
        self.first_run_setup_action = action("Chạy lại thiết lập lần đầu…", icon_name="settings")
        self.clean_build_action = action("Clean Build Folder", icon_name="delete")
        self.open_project_folder_action = action("Open Project Folder", icon_name="folder_open")
        self.open_build_folder_action = action("Open Build Folder", icon_name="folder_open")
        self.open_emulator_folder_action = action("Open Emulator Folder", icon_name="folder_open")

        # About / Settings
        self.docs_action = action("Documentation", icon_name="file")
        self.environment_action = action("Environment and Libraries", icon_name="settings")
        self.update_environment_action = action("Check & Update Environment…", "Ctrl+U", "sync")
        self.credits_action = action("Credits and Third-party Libraries", icon_name="info")
        self.about_action = action("About LuaS30 IDE", icon_name="info")

    def _create_menus(self) -> None:
        menu = self.menuBar()
        menu.setNativeMenuBar(False)

        file_menu = menu.addMenu("File")
        for obj in (
            self.new_project_action, self.open_project_action, self.welcome_action, self.project_storage_action,
            self.close_project_action, None,
            self.open_project_folder_action, self.open_build_folder_action, None,
            self.new_file_action, self.open_file_action, None,
            self.save_action, self.save_as_action, self.save_all_action, None,
            self.exit_action,
        ):
            file_menu.addSeparator() if obj is None else file_menu.addAction(obj)

        edit_menu = menu.addMenu("Edit")
        for obj in (
            self.undo_action, self.redo_action, None,
            self.cut_action, self.copy_action, self.paste_action, self.select_all_action, None,
            self.find_action, self.replace_action, self.find_next_action, self.find_prev_action,
            self.project_search_action, None, self.definition_action, self.completion_action,
        ):
            edit_menu.addSeparator() if obj is None else edit_menu.addAction(obj)

        view_menu = menu.addMenu("View")
        view_menu.addAction(self.command_palette_action)
        view_menu.addSeparator()
        view_menu.addAction(self.toggle_sidebar_action)
        view_menu.addAction(self.toggle_activity_bar_action)
        view_menu.addAction(self.toggle_panel_action)
        view_menu.addAction(self.toggle_console_action)
        view_menu.addAction(self.toggle_terminal_action)
        view_menu.addAction(self.toggle_ai_chat_action)
        view_menu.addSeparator()
        view_menu.addAction(self.split_editor_action)
        view_menu.addAction(self.close_editor_group_action)

        run_menu = menu.addMenu("Run")
        run_menu.addAction(self.build_action)
        run_menu.addAction(self.run_action)
        run_menu.addAction(self.run_last_action)
        run_menu.addSeparator()
        run_menu.addAction(self.clean_build_action)
        run_menu.addSeparator()
        run_menu.addAction(self.cancel_build_action)
        run_menu.addAction(self.stop_emulator_action)

        terminal_menu = menu.addMenu("Terminal")
        terminal_menu.addAction(self.new_terminal_action)
        terminal_menu.addAction(self.toggle_terminal_action)
        terminal_menu.addSeparator()
        terminal_menu.addAction(self.kill_terminal_action)
        terminal_menu.addAction(self.clear_terminal_action)
        terminal_menu.addSeparator()
        terminal_menu.addAction(self.toggle_console_action)
        terminal_menu.addAction(self.clear_console_action)

        # Every Tools-menu feature is a persistent editor-area tab.
        tools_menu = menu.addMenu("Tools")
        tools_menu.addAction(self.project_doctor_action)
        tools_menu.addAction(self.compat_matrix_action)
        tools_menu.addAction(self.toolchain_doctor_action)
        tools_menu.addSeparator()
        tools_menu.addAction(self.first_run_setup_action)

        settings_menu = menu.addMenu("Settings")
        settings_menu.addAction(self.update_environment_action)
        settings_menu.addSeparator()
        settings_menu.addAction(self.environment_action)
        settings_menu.addAction(self.about_action)

        about_menu = menu.addMenu("About")
        about_menu.addAction(self.docs_action)
        about_menu.addAction(self.environment_action)
        about_menu.addAction(self.credits_action)
        about_menu.addSeparator()
        about_menu.addAction(self.about_action)

    def _create_statusbar(self) -> None:
        bar = QStatusBar()
        bar.setSizeGripEnabled(False)
        self.setStatusBar(bar)
        self.status_state = QLabel("Ready")
        self.status_project = QLabel("No folder")
        self.status_problems = QLabel("0 errors  0 warnings")
        self.status_profile = QLabel("MRE/VXP Generic")
        self.status_language = QLabel("Lua 5.1")
        self.status_cursor = QLabel("Ln 1, Col 1")
        bar.addWidget(self.status_state)
        bar.addWidget(self.status_project)
        bar.addWidget(self.status_problems)
        bar.addPermanentWidget(self.status_profile)
        bar.addPermanentWidget(self.status_language)
        bar.addPermanentWidget(self.status_cursor)

    # ------------------------------------------------------------ wiring
    def _wire_events(self) -> None:
        e = self.editor_view

        self.command_button.clicked.connect(self.show_command_palette)
        self.command_palette_action.triggered.connect(self.show_command_palette)

        self.new_project_action.triggered.connect(self.create_project_from_template)
        self.open_project_action.triggered.connect(self.open_project_dialog)
        self.welcome_action.triggered.connect(lambda: self._open_start_page(activate=True))
        self.project_storage_action.triggered.connect(self._open_project_storage)
        self.close_project_action.triggered.connect(self._close_project)
        self.new_file_action.triggered.connect(e.tabs.new_file)
        self.open_file_action.triggered.connect(self.open_file_dialog)
        self.save_action.triggered.connect(e.tabs.save_current)
        self.save_as_action.triggered.connect(e.tabs.save_current_as)
        self.save_all_action.triggered.connect(e.tabs.save_all)
        self.exit_action.triggered.connect(self.close)

        self.undo_action.triggered.connect(lambda: self._editor_call("undo"))
        self.redo_action.triggered.connect(lambda: self._editor_call("redo"))
        self.cut_action.triggered.connect(lambda: self._editor_call("cut"))
        self.copy_action.triggered.connect(lambda: self._editor_call("copy"))
        self.paste_action.triggered.connect(lambda: self._editor_call("paste"))
        self.select_all_action.triggered.connect(lambda: self._editor_call("selectAll"))
        self.find_action.triggered.connect(lambda: self._show_editor_find(False))
        self.replace_action.triggered.connect(lambda: self._show_editor_find(True))
        self.find_next_action.triggered.connect(e.find_next)
        self.find_prev_action.triggered.connect(e.find_previous)
        self.project_search_action.triggered.connect(self._focus_project_search)
        self.definition_action.triggered.connect(e._go_current_definition)
        self.completion_action.triggered.connect(self._trigger_completion)

        self.explorer_action.triggered.connect(lambda: self._activity_clicked("explorer"))
        self.toggle_sidebar_action.triggered.connect(self._apply_explorer_toggle_action)
        self.toggle_activity_bar_action.triggered.connect(self._apply_activity_bar_toggle_action)
        self.toggle_panel_action.triggered.connect(e.toggle_bottom_panel)
        self.toggle_console_action.triggered.connect(e.toggle_console)
        self.toggle_terminal_action.triggered.connect(e.toggle_terminal)
        self.toggle_ai_chat_action.triggered.connect(self._apply_ai_toggle_action)
        self.new_terminal_action.triggered.connect(e.new_terminal)
        self.kill_terminal_action.triggered.connect(e.kill_terminal)
        self.clear_terminal_action.triggered.connect(e.clear_terminal)
        self.clear_console_action.triggered.connect(e.clear_console)
        self.toggle_sidebar_action.triggered.connect(self._schedule_workspace_save)
        self.toggle_activity_bar_action.triggered.connect(self._schedule_workspace_save)
        self.toggle_ai_chat_action.triggered.connect(self._schedule_workspace_save)
        self.toggle_panel_action.triggered.connect(self._schedule_workspace_save)
        self.toggle_console_action.triggered.connect(self._schedule_workspace_save)
        self.toggle_terminal_action.triggered.connect(self._schedule_workspace_save)
        self.split_editor_action.triggered.connect(self._split_editor_right)
        self.close_editor_group_action.triggered.connect(self._close_editor_group)

        self.build_action.triggered.connect(lambda: self._start_build(False))
        self.run_action.triggered.connect(lambda: self._start_build(True))
        self.run_last_action.triggered.connect(self._run_last_build)
        self.stop_emulator_action.triggered.connect(self.emulator_service.stop)
        self.cancel_build_action.triggered.connect(self.build_service.cancel)

        self.project_doctor_action.triggered.connect(self._open_project_doctor)
        self.compat_matrix_action.triggered.connect(self._open_compat_matrix)
        self.toolchain_doctor_action.triggered.connect(self._open_toolchain_doctor)
        self.first_run_setup_action.triggered.connect(lambda: self._run_first_run_setup(force=True))
        self.clean_build_action.triggered.connect(self._clean_build)
        self.open_project_folder_action.triggered.connect(self._open_project_folder)
        self.open_build_folder_action.triggered.connect(self._open_build_folder)
        self.open_emulator_folder_action.triggered.connect(self._open_emulator_folder)

        self.docs_action.triggered.connect(self._open_docs)
        self.environment_action.triggered.connect(lambda: self.show_about("environment"))
        self.update_environment_action.triggered.connect(self._update_environment)
        self.credits_action.triggered.connect(lambda: self.show_about("credits"))
        self.about_action.triggered.connect(lambda: self.show_about("about"))

        e.cursor_info_changed.connect(self._update_cursor)
        e.problems_changed.connect(self._update_problems)
        e.status_message.connect(self.show_status)
        e.tabs.currentChanged.connect(self._sync_activity_from_current_tab)
        e.connect_workspace_state_changed(self._schedule_workspace_save)
        e.tabs.file_opened.connect(lambda *_: self._schedule_workspace_save())
        e.tabs.file_saved.connect(lambda *_: self._schedule_workspace_save())
        self.session.project_changed.connect(lambda *_: self._schedule_workspace_save())

        self.build_service.started.connect(self._build_started)
        self.build_service.output.connect(self._append_build_output)
        self.build_service.stage_changed.connect(self._build_stage)
        self.build_service.finished.connect(self._build_finished)

        self.emulator_service.output.connect(self._append_output)
        self.emulator_service.state_changed.connect(self._emulator_state)
        self.emulator_service.launched.connect(self._emulator_launched)
        self.emulator_service.failed.connect(self._emulator_failed)

        self.compat_matrix_service.started.connect(self._compat_started)
        self.compat_matrix_service.output.connect(self._compat_output)
        self.compat_matrix_service.finished.connect(self._compat_finished)

    # ------------------------------------------------------------ startup/navigation
    def _resolve_saved_path(self, value: object, *, default: Path | None = None) -> Path | None:
        """Restore a saved path; remap legacy LuaS30-Engine locations onto engine_root."""
        if not value:
            return default.resolve() if default else None
        path = Path(str(value)).expanduser()
        if path.exists():
            return path.resolve()
        parts = list(path.parts)
        for legacy in ("LuaS30-Engine", "LuaS30Engine"):
            if legacy not in parts:
                continue
            tail = Path(*parts[parts.index(legacy) + 1 :])
            candidate = self.engine_root / tail
            if candidate.exists():
                return candidate.resolve()
            break
        return default.resolve() if default else None

    def _load_initial_project(self) -> None:
        saved = self.workspace_session.load()
        startup = saved.get("startup", {}) if isinstance(saved, dict) else {}

        build_settings = saved.get("build", {}) if isinstance(saved, dict) else {}
        self._compiler_profile = str(build_settings.get("compiler_profile") or "auto")
        if self._compiler_profile not in {"auto", "gcc", "rvds", "ads12"}:
            self._compiler_profile = "auto"
        self._toolchain_root = self._resolve_saved_path(
            build_settings.get("toolchain_root"),
            default=self.engine_root / "toolchain" / "arm-gcc",
        )
        self._compat_profile = str(build_settings.get("compat_profile") or "auto")
        if self._compat_profile not in {"auto","standalone","s30plus-native","nokia225-rm1011"}:
            self._compat_profile = "auto"
        self._mre_sdk_root = self._resolve_saved_path(
            build_settings.get("mre_sdk_root"),
        )
        self.build_service.set_compiler_profile(self._compiler_profile)
        self.build_service.set_toolchain_root(self._toolchain_root)
        self.build_service.set_compat_profile(self._compat_profile)
        self.build_service.set_mre_sdk_root(self._mre_sdk_root)

        mode = str(startup.get("mode") or "").strip()
        if mode not in {"welcome", "project_hub", "empty_editor"}:
            # Migration from the old Show Welcome checkbox.
            mode = "welcome" if bool(startup.get("show_start_page", True)) else "empty_editor"
        self._startup_mode = mode

        if saved:
            self._restore_workspace_session(
                saved,
                restore_tool_tabs=(self._startup_mode != "empty_editor"),
            )
            self._activate_startup_mode()
            self._schedule_workspace_save()
            return

        project = self.session.load_initial_project()
        if project:
            self._apply_project(project.root, open_main=False)
        else:
            self.editor_view.clear_project()
            self._reset_project_chrome()

        self._sync_layout_toggle_actions()
        self._activate_startup_mode()
        self._schedule_workspace_save()

    def _activate_startup_mode(self) -> None:
        if self._startup_mode == "project_hub":
            self._open_project_storage(activate=True, group_index=0)
            return
        if self._startup_mode == "empty_editor":
            self._show_empty_editor_startup()
            return
        self._open_start_page(activate=True, group_index=0)

    def _show_empty_editor_startup(self) -> None:
        self._set_project_hub_mode(False)
        self.editor_view.tabs.show_empty_editor(close_tool_tabs=True)
        self._check_activity("explorer" if self.editor_view.sidebar_visible() else None)
        self.show_status("Empty editor startup")

    def _restore_workspace_session(self, state: dict, *, restore_tool_tabs: bool = True) -> None:
        """Restore workspace chrome/project/tool tabs, but never source documents.

        LuaS30 1.9.6 intentionally starts with no .lua/.c/.h/JSON/text editor files
        reopened from the previous process. This keeps startup predictable: Welcome is
        the default landing tab, while project/layout/tool state can still be restored.
        """
        self._restoring_workspace = True
        skipped_source_tabs = 0
        restored_tool_tabs = False
        try:
            project_path = state.get("project")
            project = Path(project_path).expanduser().resolve() if project_path else None
            if project and project.is_dir():
                info = self.session.open_project(project)
                self._apply_project(info.root, open_main=False)
            else:
                self.editor_view.clear_project()
                self._reset_project_chrome()

            editor_state = state.get("editor", {}) if isinstance(state, dict) else {}
            groups_state = editor_state.get("editor_groups", {}) if isinstance(editor_state, dict) else {}
            groups = groups_state.get("groups", []) if isinstance(groups_state, dict) else []
            self.editor_view.tabs.ensure_group_count(max(1, len(groups) or 1))

            for group_index, group_state in enumerate(groups):
                self.editor_view.tabs.set_active_group(group_index)
                for entry in group_state.get("tabs", []):
                    kind = entry.get("type")

                    # Startup policy: source and untitled editor documents are not
                    # reopened after application restart.
                    if kind in {"file", "untitled"}:
                        skipped_source_tabs += 1
                        continue

                    if kind == "tool" and restore_tool_tabs:
                        if self._restore_tool_tab(str(entry.get("key", "")), group_index):
                            restored_tool_tabs = True

                tabs = self.editor_view.tabs.groups[group_index]
                if tabs.count():
                    active_tab = int(group_state.get("active_tab", 0) or 0)
                    tabs.setCurrentIndex(max(0, min(active_tab, tabs.count() - 1)))

            sizes = groups_state.get("group_sizes") if isinstance(groups_state, dict) else None
            if isinstance(sizes, list):
                self.editor_view.tabs.set_group_sizes(sizes)
            self.editor_view.tabs.set_active_group(int(groups_state.get("active_group", 0) or 0))
            self.editor_view.restore_layout_state(editor_state)

            chrome_state = state.get("chrome", {}) if isinstance(state, dict) else {}
            self._editor_activity_bar_visible = bool(
                chrome_state.get("activity_bar_visible", True)
            )
            self._sync_layout_toggle_actions()

            # Deliberately no main.lua fallback here. Startup must not open any file.
            # _load_initial_project() applies the configured startup screen after restore.
            self._sync_activity_from_current_tab(
                self.editor_view.tabs.active_tabs().currentIndex()
            )

            if skipped_source_tabs:
                self._append_output(
                    f"[SESSION] Skipped {skipped_source_tabs} source/untitled tab(s) on startup."
                )
            self.show_status(
                "Workspace restored without reopening source files"
                if skipped_source_tabs else
                "Workspace restored"
            )
        finally:
            self._restoring_workspace = False
            self._schedule_workspace_save()

    def _restore_tool_tab(self, key: str, group_index: int) -> bool:
        self.editor_view.tabs.set_active_group(group_index)
        if key == "welcome":
            return self._open_start_page(activate=True, group_index=group_index) is not None
        if key == "projects":
            return self._open_project_storage(activate=True, group_index=group_index) is not None
        if key == "assets":
            return self._open_assets() is not None
        if key == "designer":
            return self._open_designer() is not None
        if key == "emulator":
            return self._open_emulator() is not None
        if key == "settings":
            return self._open_settings() is not None
        if key == "project-doctor":
            return self._open_project_doctor() is not None
        if key == "compat-matrix":
            return self._open_compat_matrix() is not None
        if key == "toolchain-doctor":
            return self._open_toolchain_doctor() is not None
        return False

    def _schedule_workspace_save(self, *_args) -> None:
        if self._restoring_workspace:
            return
        self._workspace_save_timer.start()

    @staticmethod
    def _startup_safe_editor_state(editor_state: dict) -> dict:
        """Remove document tabs from the persisted startup session.

        Tool tabs, group count/sizes, sidebar state and bottom-panel state remain
        persistent. Source files are intentionally process-local in v1.9.6.
        """
        safe = copy.deepcopy(editor_state) if isinstance(editor_state, dict) else {}
        groups_state = safe.get("editor_groups")
        if not isinstance(groups_state, dict):
            return safe

        groups = groups_state.get("groups")
        if not isinstance(groups, list):
            return safe

        for group in groups:
            if not isinstance(group, dict):
                continue
            tabs = group.get("tabs", [])
            if not isinstance(tabs, list):
                tabs = []
            group["tabs"] = [
                entry for entry in tabs
                if isinstance(entry, dict) and entry.get("type") == "tool"
            ]
            if group["tabs"]:
                group["active_tab"] = max(
                    0,
                    min(int(group.get("active_tab", 0) or 0), len(group["tabs"]) - 1),
                )
            else:
                group["active_tab"] = 0
        return safe

    def _save_workspace_session(self) -> None:
        if self._restoring_workspace:
            return
        editor_state = self._startup_safe_editor_state(
            self.editor_view.workspace_state()
        )
        state = {
            "project": str(self.session.root) if self.session.root else None,
            "editor": editor_state,
            "window": {
                "maximized": self.isMaximized(),
                "width": self.width(),
                "height": self.height(),
            },
            "startup": {
                "mode": self._startup_mode,
                "show_start_page": self._startup_mode == "welcome",
                "restore_source_tabs": False,
            },
            "chrome": {
                "activity_bar_visible": bool(self._editor_activity_bar_visible),
            },
            "build": {
                "compiler_profile": self._compiler_profile,
                "toolchain_root": str(self._toolchain_root),
                "compat_profile": self._compat_profile,
                "mre_sdk_root": str(self._mre_sdk_root) if self._mre_sdk_root else None,
            },
        }
        try:
            self.workspace_session.save(state)
        except OSError as exc:
            self._append_output(f"[SESSION] Could not save workspace: {exc}")

    def _apply_explorer_toggle_action(self, checked: bool) -> None:
        self.editor_view.set_sidebar_visible(bool(checked))
        if self._project_hub_mode:
            self.show_status(
                "Explorer will be shown in the editor." if checked
                else "Explorer will remain hidden in the editor."
            )
        else:
            self.show_status("Explorer shown" if checked else "Explorer hidden")

    def _apply_activity_bar_toggle_action(self, checked: bool) -> None:
        self._editor_activity_bar_visible = bool(checked)
        if not self._project_hub_mode:
            self.activity_bar.setVisible(self._editor_activity_bar_visible)
        if self._project_hub_mode and checked:
            self.show_status("Activity Bar will be shown in the editor.")
        else:
            self.show_status("Activity Bar shown" if checked else "Activity Bar hidden")

    def _apply_ai_toggle_action(self, checked: bool) -> None:
        self.editor_view.set_ai_visible(bool(checked))
        if self._project_hub_mode and checked:
            self.show_status("Chat AI will be shown when returning to the editor.")
        else:
            self.show_status("Chat AI shown" if checked else "Chat AI hidden")

    def _sync_layout_toggle_actions(self) -> None:
        self.toggle_sidebar_action.blockSignals(True)
        self.toggle_sidebar_action.setChecked(self.editor_view.sidebar_visible())
        self.toggle_sidebar_action.blockSignals(False)
        self.toggle_activity_bar_action.blockSignals(True)
        self.toggle_activity_bar_action.setChecked(bool(self._editor_activity_bar_visible))
        self.toggle_activity_bar_action.blockSignals(False)
        if not self._project_hub_mode:
            self.activity_bar.setVisible(bool(self._editor_activity_bar_visible))

    def _split_editor_right(self) -> None:
        self.editor_view.tabs.split_right()
        self.show_status("Editor group created")
        self._schedule_workspace_save()

    def _close_editor_group(self) -> None:
        if not self.editor_view.tabs.close_active_group():
            if len(self.editor_view.tabs.groups) <= 1:
                self.show_status("The last editor group cannot be closed.")
            return
        self.show_status("Editor group closed")
        self._schedule_workspace_save()

    def _activity_clicked(self, key: str) -> None:
        if key == "explorer":
            self._set_project_hub_mode(False)
            self.editor_view.show_explorer()
            self.toggle_sidebar_action.setChecked(True)
            self._check_activity("explorer")
            self._schedule_workspace_save()
            return
        if key == "ai":
            new_state = not self.editor_view.ai_visible()
            self.toggle_ai_chat_action.setChecked(new_state)
            self._apply_ai_toggle_action(new_state)
            self._check_activity("ai" if new_state else None)
            self._schedule_workspace_save()
            return

        if key == "search":
            if not self.session.root:
                self._open_start_page(activate=True)
                self.show_status("Open a project before searching files.")
                return
            self._set_project_hub_mode(False)
            self.editor_view.show_search()
            self.toggle_sidebar_action.setChecked(True)
            self._check_activity("search")
            self._schedule_workspace_save()
            return
        if key == "projects":
            self._open_project_storage()
            return
        if key == "assets":
            self._open_assets()
            return
        if key == "designer":
            self._open_designer()
            return
        if key == "emulator":
            self._open_emulator()
            return
        if key == "settings":
            self._open_settings()
            return

    def _check_activity(self, key: str | None) -> None:
        for name, button in self.activity_buttons.items():
            if name == "ai":
                button.setChecked(self.editor_view.ai_visible())
            else:
                button.setChecked(bool(key) and name == key)

    def _set_project_hub_mode(self, enabled: bool) -> None:
        """Welcome/Project Storage are clean full-width pages.

        Explorer/Search, Activity Bar and the integrated bottom panel are editor
        chrome. They are temporarily hidden while the project hub is active and
        restored exactly as the user left them when returning to source editing.
        """
        enabled = bool(enabled)
        if enabled == self._project_hub_mode:
            return
        self._project_hub_mode = enabled
        self.activity_bar.setVisible((not enabled) and bool(self._editor_activity_bar_visible))
        self.editor_view.set_hub_mode(enabled)
        self._sync_layout_toggle_actions()

        # Editor-only toggles should not make the red editor chrome reappear on
        # the project creation/storage screens.
        for action in (
            self.toggle_panel_action,
            self.toggle_console_action,
            self.toggle_terminal_action,
            self.new_terminal_action,
        ):
            action.setEnabled(not enabled)
        self.toggle_sidebar_action.setEnabled(True)
        self.toggle_activity_bar_action.setEnabled(True)
        self.toggle_ai_chat_action.setEnabled(True)

    def _sync_activity_from_current_tab(self, _index: int) -> None:
        key = self.editor_view.tabs.current_tool_key()

        # Project Hub pages intentionally use the whole central workspace.
        hub_page = key in {"welcome", "projects"}
        self._set_project_hub_mode(hub_page)

        if hub_page:
            self._check_activity(None)
        elif key in self.activity_buttons:
            self._check_activity(key)
        elif self.editor_view.tabs.current_editor() is not None:
            self._check_activity("explorer")
        else:
            self._check_activity(None)

    def show_command_palette(self) -> None:
        commands = [
            self.new_project_action, self.open_project_action, self.welcome_action, self.project_storage_action,
            self.close_project_action, self.new_file_action, self.open_file_action,
            self.save_action, self.save_all_action, self.explorer_action,
            self.project_search_action, self.definition_action, self.completion_action,
            self.toggle_sidebar_action, self.toggle_activity_bar_action, self.toggle_panel_action,
            self.toggle_console_action, self.toggle_terminal_action,
            self.split_editor_action, self.close_editor_group_action,
            self.new_terminal_action, self.kill_terminal_action, self.clear_terminal_action, self.clear_console_action,
            self.build_action, self.run_action, self.run_last_action,
            self.stop_emulator_action, self.cancel_build_action,
            self.project_doctor_action, self.compat_matrix_action, self.toolchain_doctor_action,
            self.clean_build_action, self.open_project_folder_action,
            self.open_build_folder_action, self.open_emulator_folder_action,
            self.docs_action, self.environment_action, self.credits_action, self.about_action,
            self.update_environment_action,
        ]
        palette = CommandPalette(commands, self)
        palette.move(
            self.mapToGlobal(self.rect().center()).x() - palette.width() // 2,
            self.mapToGlobal(self.rect().topLeft()).y() + 85,
        )
        palette.exec()

    # ------------------------------------------------------------ tab factories
    def _open_start_page(
        self,
        *,
        activate: bool = True,
        group_index: int = 0,
    ) -> StartPageView:
        def factory():
            view = StartPageView(self.project_library)
            view.new_project_requested.connect(self.create_project_from_template)
            view.open_folder_requested.connect(self.open_project_dialog)
            view.open_project_requested.connect(self._open_project_from_storage)
            view.manage_projects_requested.connect(self._open_project_storage)
            view.status_message.connect(self.show_status)
            view.set_current_project(self.session.root)
            return view

        view = self.editor_view.open_tool_tab(
            "welcome",
            "Welcome",
            factory,
            font_icon("home", 15),
            insert_at=0,
            activate=activate,
            group_index=group_index,
        )
        if isinstance(view, StartPageView):
            view.set_current_project(self.session.root)
            view.refresh()
        if activate:
            self._set_project_hub_mode(True)
            self._check_activity(None)
        return view

    def _open_project_storage(
        self,
        *,
        activate: bool = True,
        group_index: int | None = None,
    ) -> ProjectManagerView:
        def factory():
            view = ProjectManagerView(self.project_library)
            view.open_project_requested.connect(self._open_project_from_storage)
            view.new_project_requested.connect(self.create_project_from_template)
            view.duplicate_project_requested.connect(self._duplicate_managed_project)
            view.rename_project_requested.connect(self._rename_managed_project)
            view.delete_project_requested.connect(self._delete_managed_project)
            view.status_message.connect(self.show_status)
            view.set_current_project(self.session.root)
            return view

        view = self.editor_view.open_tool_tab(
            "projects",
            "Project Hub",
            factory,
            font_icon("projects", 15),
            activate=activate,
            group_index=group_index,
        )
        if isinstance(view, ProjectManagerView):
            view.set_current_project(self.session.root)
        if activate:
            self._set_project_hub_mode(True)
            self._check_activity(None)
        return view

    def _open_assets(self) -> AssetsView | None:
        if not self.session.root:
            self._open_start_page(activate=True)
            self.show_status("Open a project before using Assets.")
            return None

        def factory():
            view = AssetsView()
            view.set_project(self.session.root)
            return view

        view = self.editor_view.open_tool_tab("assets", "Assets", factory, font_icon("image", 15))
        if isinstance(view, AssetsView):
            view.set_project(self.session.root)
        self._check_activity("assets")
        return view

    def _open_designer(self) -> UIDesignerView | None:
        if not self.session.root:
            self._open_start_page(activate=True)
            self.show_status("Open a project before using UI Designer.")
            return None

        def factory():
            view = UIDesignerView()
            view.logMessage.connect(self._designer_log)
            view.assetsImported.connect(self._on_designer_assets_imported)
            view.set_project(self.session.root)
            return view

        view = self.editor_view.open_tool_tab("designer", "UI Designer", factory, font_icon("designer", 15))
        if isinstance(view, UIDesignerView):
            view.set_project(self.session.root)
        self._check_activity("designer")
        return view

    def _designer_log(self, message: str) -> None:
        """Nhật ký UI Designer -> panel Output; dòng đầu hiện ở thanh trạng thái.

        Thông báo của designer thường nhiều dòng (đường dẫn, tham chiếu Lua), nên
        chỉ đưa dòng đầu lên thanh trạng thái — dán cả khối vào đó sẽ phá bố cục.
        """
        text = (message or "").strip()
        if not text:
            return
        self._append_output(text)
        head = text.splitlines()[0]
        self.status_state.setText(head)
        self.workbench_state.setText(head)
        QTimer.singleShot(2400, self._restore_ready)

    def _on_designer_assets_imported(self) -> None:
        """Designer vừa copy tài nguyên vào assets/ -> quét lại các view theo project.

        Cây EXPLORER tự cập nhật nhờ watcher của QFileSystemModel, nên ở đây chỉ
        cần cho các tab phụ thuộc project (Assets, designer) đọc lại thư mục.
        """
        self._refresh_project_bound_tools()

    def _open_emulator(self) -> EmulatorView:
        def factory():
            view = EmulatorView()
            view.run_last_requested.connect(self._run_last_build)
            view.stop_requested.connect(self.emulator_service.stop)
            view.open_build_folder_requested.connect(self._open_build_folder)
            view.open_emulator_folder_requested.connect(self._open_emulator_folder)
            view.set_project(self.session.root)
            if self.last_manifest:
                view.set_manifest(self.last_manifest)
            return view

        view = self.editor_view.open_tool_tab("emulator", "Emulator", factory, font_icon("play", 15))
        if isinstance(view, EmulatorView):
            view.set_project(self.session.root)
            if self.last_manifest:
                view.set_manifest(self.last_manifest)
        self._check_activity("emulator")
        return view

    def _open_settings(self) -> SettingsView:
        def factory():
            view = SettingsView(
                self.engine_root,
                startup_mode=self._startup_mode,
                compiler_profile=self._compiler_profile,
                toolchain_root=self._toolchain_root,
                compat_profile=self._compat_profile,
                mre_sdk_root=self._mre_sdk_root,
            )
            view.startup_mode_changed.connect(self._set_startup_mode)
            view.compiler_profile_changed.connect(self._set_compiler_profile)
            view.toolchain_root_changed.connect(self._set_toolchain_root)
            view.compat_profile_changed.connect(self._set_compat_profile)
            view.mre_sdk_root_changed.connect(self._set_mre_sdk_root)
            view.device_imsi_changed.connect(self._set_device_imsi)
            return view

        view = self.editor_view.open_tool_tab(
            "settings", "Settings", factory, font_icon("settings", 15)
        )
        if isinstance(view, SettingsView):
            view.set_startup_mode(self._startup_mode)
            view.set_compiler_profile(self._compiler_profile)
            view.set_toolchain_root(self._toolchain_root)
            view.set_compat_profile(self._compat_profile)
            view.set_mre_sdk_root(self._mre_sdk_root)
        self._check_activity("settings")
        return view

    def _set_startup_mode(self, mode: str) -> None:
        mode = str(mode or "welcome")
        if mode not in {"welcome", "project_hub", "empty_editor"}:
            mode = "welcome"
        self._startup_mode = mode
        labels = {
            "welcome": "Welcome",
            "project_hub": "Project Hub",
            "empty_editor": "Empty Editor",
        }
        self._schedule_workspace_save()
        self.show_status(f"Startup screen: {labels[mode]} (applies next launch)")

    def _set_compiler_profile(self, profile: str) -> None:
        profile = str(profile or "auto").lower()
        if profile not in {"auto", "gcc", "rvds", "ads12"}:
            profile = "auto"
        self._compiler_profile = profile
        self.build_service.set_compiler_profile(profile)
        doctor = self.editor_view.tool_widget("toolchain-doctor")
        if isinstance(doctor, ToolchainDoctorView):
            doctor.set_toolchain(self._toolchain_root, profile)
        self._schedule_workspace_save()
        self.show_status(f"Compiler profile: {profile}")

    def _set_toolchain_root(self, root: str) -> None:
        path = Path(root).expanduser().resolve()
        self._toolchain_root = path
        self.build_service.set_toolchain_root(path)
        doctor = self.editor_view.tool_widget("toolchain-doctor")
        if isinstance(doctor, ToolchainDoctorView):
            doctor.set_toolchain(path, self._compiler_profile)
        self._schedule_workspace_save()
        self.show_status(f"Toolchain root: {path}")

    def _set_compat_profile(self, profile: str) -> None:
        profile = str(profile or "auto").lower()
        if profile not in {"auto","standalone","s30plus-native","nokia225-rm1011"}:
            profile = "auto"
        self._compat_profile = profile
        self.build_service.set_compat_profile(profile)
        self._schedule_workspace_save()
        self.show_status(f"S30+ compatibility: {profile}")

    def _set_mre_sdk_root(self, root: str) -> None:
        value = str(root or "").strip()
        self._mre_sdk_root = Path(value).expanduser().resolve() if value else None
        self.build_service.set_mre_sdk_root(self._mre_sdk_root)
        self._schedule_workspace_save()
        self.show_status(
            f"MRE SDK: {self._mre_sdk_root}" if self._mre_sdk_root else "MRE SDK cleared"
        )

    def _set_device_imsi(self, imsi: str) -> None:
        # Sensitive value: memory only, never persisted.
        self._device_imsi = "".join(ch for ch in str(imsi or "") if ch.isdigit())
        self.build_service.set_device_imsi(self._device_imsi)
        self.show_status("Nokia IMSI set for this Studio session" if self._device_imsi else "Nokia IMSI cleared")

    def _open_project_doctor(self) -> ProjectDoctorView | None:
        if not self.session.root:
            self._open_start_page(activate=True)
            self.show_status("Open a project before running Project Doctor.")
            return None

        view = self.editor_view.open_tool_tab(
            "project-doctor", "Project Doctor",
            lambda: ProjectDoctorView(self.engine_root, self.session.root),
            font_icon("check", 15),
        )
        if isinstance(view, ProjectDoctorView):
            view.set_project(self.session.root)
        self._check_activity(None)
        return view

    def _open_compat_matrix(self) -> CompatMatrixView:
        def factory():
            view = CompatMatrixView()
            view.run_requested.connect(self._start_compat_matrix)
            return view

        view = self.editor_view.open_tool_tab(
            "compat-matrix", "Runtime Compatibility", factory, font_icon("check", 15)
        )
        self._check_activity(None)
        report = self.engine_root / "build" / "runtime_compat_matrix" / "runtime_compat_matrix.json"
        if isinstance(view, CompatMatrixView) and report.is_file():
            try:
                view.load_report(report)
            except Exception as exc:
                view.append_output(f"Could not load previous matrix: {exc}")
        return view

    def _open_toolchain_doctor(self) -> ToolchainDoctorView:
        def factory():
            view = ToolchainDoctorView(self.engine_root)
            view.set_toolchain(self._toolchain_root, self._compiler_profile)
            return view

        view = self.editor_view.open_tool_tab(
            "toolchain-doctor", "Toolchain Doctor",
            factory,
            font_icon("build", 15),
        )
        if isinstance(view, ToolchainDoctorView):
            view.set_toolchain(self._toolchain_root, self._compiler_profile)
        self._check_activity(None)
        return view

    # ------------------------------------------------------------ first-run
    def _autostart_terminal(self) -> None:
        """Tu chay shell nen khi Studio mo xong: an, khong can Enter."""
        try:
            self.editor_view.bottom.terminal.autostart_background()
        except Exception:
            pass

    def _run_first_run_setup(self, force: bool = False) -> None:
        """Hien hop thoai thiet lap lan dau (co the goi lai tu Tools menu)."""
        from app.views.setup_dialog import SetupDialog

        try:
            dialog = SetupDialog(self.engine_root, self.VERSION, self, force=force)
            dialog.setup_completed.connect(
                lambda _ok: self.show_status("Environment setup finished"))
            dialog.exec()
        except Exception as exc:
            self.show_status(f"Khong mo duoc thiet lap lan dau: {exc}")

    def _maybe_first_run_setup(self) -> None:
        """Chi hien thiet lap lan dau khi chua ghi nhan hoan tat (khong chan IDE)."""
        try:
            from app.services.environment_setup import is_first_run

            if is_first_run(self.VERSION):
                self._run_first_run_setup()
        except Exception as exc:
            self.show_status(f"Khong the chay thiet lap lan dau: {exc}")

    # ------------------------------------------------------------ project
    def open_project_dialog(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Open LuaS30 Project",
            str(self.session.root or self.session.default_projects_root),
        )
        if folder:
            self._switch_project(Path(folder))

    def _open_project_from_storage(self, path: Path) -> None:
        self._switch_project(Path(path))

    def _switch_project(self, path: Path) -> None:
        if not self.editor_view.tabs.close_file_tabs():
            return
        try:
            info = self.session.open_project(path)
            self._apply_project(info.root)
            self._activity_clicked("explorer")
            self.show_status(f"Project opened: {info.root}")
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Open Project", str(exc))

    def open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open file",
            str(self.session.root or self.session.default_projects_root),
            "Source Files (*.lua *.c *.h *.json *.txt *.md);;All Files (*)",
        )
        if path:
            self._set_project_hub_mode(False)
            self._activity_clicked("explorer")
            self.editor_view.open_file(path)

    def create_project_from_template(self) -> None:
        if not self.editor_view.tabs.close_file_tabs():
            return

        dialog = MediaTekMREConfigDialog(self)
        dialog.set_project_root_preview(str(self.session.default_projects_root))
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        config = dialog.configuration()
        name = config.app_name
        try:
            target = self.session.project_path(name)
            if target.exists():
                raise FileExistsError(target)
            info = self.session.create_project(
                name,
                metadata=config.project_metadata(),
                sdk_metadata=config.sdk_metadata(),
            )
            self._apply_project(info.root)
            self._activity_clicked("explorer")
            try:
                descriptor = json.loads(
                    (info.root / "project.json").read_text(encoding="utf-8-sig")
                )
                appid = descriptor.get("appid")
            except Exception:
                appid = None
            self.show_status(
                f"Project created: {info.root}"
                + (f" | AppID {appid}" if appid else "")
                + f" | {config.chipset_id} | {config.screen_width}x{config.screen_height}"
            )
        except FileExistsError as exc:
            QMessageBox.warning(
                self,
                "New Project",
                f"Project already exists:\n{exc}",
            )
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "New Project", str(exc))

    def _duplicate_managed_project(self, source: Path, new_name: str) -> None:
        source = Path(source).resolve()
        if self.session.root and source == self.session.root:
            if not self.editor_view.tabs.save_all():
                return
        try:
            destination = self.project_library.duplicate(source, new_name)
            manager = self.editor_view.tool_widget("projects")
            if isinstance(manager, ProjectManagerView):
                manager.refresh()
                manager.select_path(destination)
            self.show_status(f"Project duplicated: {destination.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Duplicate Project", str(exc))

    def _rename_managed_project(self, source: Path, new_name: str) -> None:
        source = Path(source).resolve()
        is_current = bool(self.session.root and source == self.session.root)
        if is_current and not self.editor_view.tabs.close_file_tabs():
            return
        try:
            destination = self.project_library.rename(source, new_name)
            if is_current:
                self.session.open_project(destination)
                self._apply_project(destination)
            manager = self.editor_view.tool_widget("projects")
            if isinstance(manager, ProjectManagerView):
                manager.set_current_project(self.session.root)
                manager.select_path(destination)
            self.show_status(f"Project renamed: {destination.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Rename Project", str(exc))

    def _delete_managed_project(self, source: Path) -> None:
        source = Path(source).resolve()
        is_current = bool(self.session.root and source == self.session.root)
        if is_current and not self.editor_view.tabs.close_file_tabs():
            return
        try:
            self.project_library.delete(source)
            if is_current:
                self.session.close_project()
                self.editor_view.clear_project()
                self.last_manifest = {}
                self._reset_project_chrome()
            manager = self.editor_view.tool_widget("projects")
            if isinstance(manager, ProjectManagerView):
                manager.set_current_project(self.session.root)
            self.show_status(f"Project deleted: {source.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Delete Project", str(exc))

    def _close_project(self) -> None:
        if not self.session.root:
            self._open_start_page(activate=True)
            return
        if not self.editor_view.tabs.close_file_tabs():
            return
        self.session.close_project()
        self.editor_view.clear_project()
        self.last_manifest = {}
        self._reset_project_chrome()
        self._refresh_project_bound_tools()
        self._open_start_page(activate=True)
        self.show_status("Project closed")

    def _apply_project(self, path: Path, open_main: bool = True) -> None:
        path = Path(path).resolve()
        self.editor_view.set_project(path, open_main=open_main)
        self.project_label.setText(path.name)
        self.project_label.setToolTip(str(path))
        self.status_project.setText(path.name)
        self.setWindowTitle(f"{path.name} - LuaS30 IDE {self.VERSION}")
        self.status_profile.setText("MRE/VXP Generic")
        self._load_last_manifest(path)
        self._refresh_project_bound_tools()
        self._schedule_workspace_save()

    def _reset_project_chrome(self) -> None:
        self.project_label.setText("No Folder")
        self.project_label.setToolTip("")
        self.status_project.setText("No folder")
        self.status_profile.setText("MRE/VXP Generic")
        self.setWindowTitle(f"LuaS30 IDE {self.VERSION}")

    def _refresh_project_bound_tools(self) -> None:
        root = self.session.root
        for key, cls in (("assets", AssetsView), ("designer", UIDesignerView), ("emulator", EmulatorView)):
            widget = self.editor_view.tool_widget(key)
            if isinstance(widget, cls):
                widget.set_project(root)
        doctor = self.editor_view.tool_widget("project-doctor")
        if isinstance(doctor, ProjectDoctorView):
            doctor.set_project(root)
        manager = self.editor_view.tool_widget("projects")
        if isinstance(manager, ProjectManagerView):
            manager.set_current_project(root)
        start = self.editor_view.tool_widget("welcome")
        if isinstance(start, StartPageView):
            start.set_current_project(root)
            start.refresh()

    def _load_last_manifest(self, project: Path) -> None:
        manifest = project / "build" / "sync_manifest.json"
        if not manifest.is_file():
            self.last_manifest = {}
            return
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["_manifest_path"] = str(manifest)
            self.last_manifest = data
            emu = self.editor_view.tool_widget("emulator")
            if isinstance(emu, EmulatorView):
                emu.set_manifest(data)
        except Exception:
            self.last_manifest = {}

    # ------------------------------------------------------------ editor
    def _current_editor(self):
        return self.editor_view.tabs.current_editor()

    def _editor_call(self, method: str) -> None:
        editor = self._current_editor()
        function = getattr(editor, method, None) if editor else None
        if callable(function):
            function()

    def _show_editor_find(self, replace: bool) -> None:
        if not self.session.root:
            return
        self._activity_clicked("explorer")
        self.editor_view.show_find(replace)

    def _focus_project_search(self) -> None:
        if not self.session.root:
            self._open_project_storage()
            return
        editor = self._current_editor()
        seed = editor.textCursor().selectedText() if editor else ""
        self._activity_clicked("search")
        self.editor_view.focus_project_search(seed)

    def _trigger_completion(self) -> None:
        if not self.session.root:
            return
        editor = self._current_editor()
        if editor:
            editor.completion.show(force=True)

    def _update_cursor(self, line: int, column: int, selected: int) -> None:
        text = f"Ln {line}, Col {column}"
        self.status_cursor.setText(text + (f" ({selected})" if selected else ""))

    def _update_problems(self, errors: int, warnings: int) -> None:
        self.status_problems.setText(f"{errors} errors  {warnings} warnings")

    # ------------------------------------------------------------ build
    def _start_build(self, run_after: bool) -> None:
        project = self.session.root
        if not project:
            self._open_project_storage()
            QMessageBox.warning(self, "Build", "Open a project first.")
            return
        if self.build_service.active:
            self.show_status("A build is already running.")
            return
        if not self.editor_view.tabs.save_all():
            return

        self.run_after_build = run_after
        self.editor_view.clear_build_log()
        self.editor_view.show_bottom_panel()
        self.editor_view.bottom.show_build()
        try:
            self.build_service.start(project)
        except Exception as exc:
            QMessageBox.critical(self, "Build", str(exc))
            self.run_after_build = False

    def _build_started(self) -> None:
        self._set_build_actions(False)
        self.show_status("Build started")
        self.workbench_state.setText("Building")

    def _append_build_output(self, text: str) -> None:
        self.editor_view.append_build_log(text)

    def _build_stage(self, stage: str) -> None:
        self.status_state.setText(stage)
        self.workbench_state.setText(stage)

    def _build_finished(self, success: bool, exit_code: int, manifest: dict) -> None:
        self._set_build_actions(True)
        if success:
            self.last_manifest = dict(manifest)
            emu = self.editor_view.tool_widget("emulator")
            if isinstance(emu, EmulatorView) and manifest:
                emu.set_manifest(manifest)
            self.editor_view.append_build_log(f"\n[BUILD] Completed successfully (exit {exit_code}).")
            self.show_status("Build succeeded")
            if self.run_after_build:
                self.run_after_build = False
                self._launch_manifest(manifest)
        else:
            self.editor_view.append_build_log(f"\n[BUILD] Failed (exit {exit_code}).")
            self.show_status(f"Build failed ({exit_code})")
            self.run_after_build = False
        self.workbench_state.setText("Ready" if success else "Build failed")

    def _set_build_actions(self, enabled: bool) -> None:
        self.build_action.setEnabled(enabled)
        self.run_action.setEnabled(enabled)
        self.cancel_build_action.setEnabled(not enabled)

    def _run_last_build(self) -> None:
        if not self.session.root:
            self._open_project_storage()
            QMessageBox.warning(self, "Emulator", "Open a project first.")
            return
        if not self.last_manifest:
            self._load_last_manifest(self.session.root)
        if not self.last_manifest:
            QMessageBox.information(self, "Emulator", "No verified build manifest exists yet.")
            return
        self._launch_manifest(self.last_manifest)

    def _launch_manifest(self, manifest: dict) -> None:
        if not manifest:
            QMessageBox.warning(self, "Emulator", "Build finished but no sync manifest was produced.")
            return

        # Show the exact VXP bytes that are about to be launched. The HEX tab
        # is tied to the same manifest artifact verified by EmulatorService.
        vxp = Path(str(manifest.get("vxp", ""))).expanduser()
        if vxp.is_file():
            self._set_project_hub_mode(False)
            self.editor_view.show_hex(vxp)

        self._open_emulator()
        self.emulator_service.launch_manifest(manifest)

    def _emulator_state(self, state: str) -> None:
        emu = self.editor_view.tool_widget("emulator")
        if isinstance(emu, EmulatorView):
            emu.set_state(state)
        self.status_state.setText(f"Emulator: {state}")

    def _emulator_launched(self, manifest: dict) -> None:
        self.last_manifest = dict(manifest)
        emu = self.editor_view.tool_widget("emulator")
        if isinstance(emu, EmulatorView):
            emu.set_manifest(manifest)
        vxp = Path(str(manifest.get("vxp", ""))).expanduser()
        if vxp.is_file():
            self.editor_view.bottom.hex_view.set_file(vxp)
        self.show_status("Emulator started with SHA-verified VXP / HEX loaded")

    def _emulator_failed(self, message: str) -> None:
        self._append_output(f"[EMU ERROR] {message}")
        QMessageBox.warning(self, "Emulator", message)

    # ------------------------------------------------------------ tools
    def _start_compat_matrix(self) -> None:
        view = self._open_compat_matrix()
        if self.compat_matrix_service.active:
            self.show_status("Compatibility matrix is already running.")
            return
        view.set_running()
        try:
            self.compat_matrix_service.start()
        except Exception as exc:
            QMessageBox.critical(self, "Runtime Compatibility Matrix", str(exc))

    def _compat_started(self) -> None:
        self.show_status("Runtime compatibility matrix started")

    def _compat_output(self, text: str) -> None:
        self._append_output(text)
        view = self.editor_view.tool_widget("compat-matrix")
        if isinstance(view, CompatMatrixView):
            view.append_output(text)

    def _compat_finished(self, success: bool, exit_code: int, report_path: Path) -> None:
        view = self.editor_view.tool_widget("compat-matrix")
        if success:
            if isinstance(view, CompatMatrixView):
                try:
                    view.load_report(report_path)
                except Exception as exc:
                    view.append_output(f"Report load failed: {exc}")
            self.show_status("Runtime compatibility matrix completed")
        else:
            if isinstance(view, CompatMatrixView):
                view.append_output(f"Matrix failed with exit code {exit_code}")
            self.show_status(f"Compatibility matrix failed ({exit_code})")

    def _clean_build(self) -> None:
        project = self.session.root
        if not project:
            return
        build = project / "build"
        if not build.exists():
            self.show_status("Build folder is already clean.")
            return
        if QMessageBox.question(
            self, "Clean Build", f"Delete generated build folder?\n{build}"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            shutil.rmtree(build)
            self.last_manifest = {}
            emu = self.editor_view.tool_widget("emulator")
            if isinstance(emu, EmulatorView):
                emu.set_project(project)
            manager = self.editor_view.tool_widget("projects")
            if isinstance(manager, ProjectManagerView):
                manager.refresh()
            self.show_status("Build folder cleaned.")
        except OSError as exc:
            QMessageBox.critical(self, "Clean Build", str(exc))

    def _open_project_folder(self) -> None:
        if self.session.root:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.session.root)))

    def _open_build_folder(self) -> None:
        if not self.session.root:
            return
        build = self.session.root / "build"
        build.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(build)))

    def _open_emulator_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.engine_root / "emulator")))

    # ------------------------------------------------------------ docs/about
    def show_about(self, tab: str = "about") -> None:
        AboutDialog(self.engine_root, self, start_tab=tab).exec()

    def _open_docs(self) -> None:
        for path in (self.engine_root / "doc" / "INDEX.md", self.engine_root / "README.md"):
            if path.is_file():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
                return
        QMessageBox.information(self, "Documentation", "Documentation file not found.")

    def _update_environment(self) -> None:
        """Settings → Check & Update Environment: refresh Python libs / resources."""
        script = resolve_script(self.engine_root / "tools", "dependency_manager")
        if not script.is_file():
            QMessageBox.warning(
                self,
                "Update Environment",
                "dependency_manager not found in tools/.",
            )
            return
        if getattr(self, "_env_update_proc", None) is not None:
            return
        proc = QProcess(self)
        self._env_update_proc = proc
        proc.setWorkingDirectory(str(self.engine_root))
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.setProcessEnvironment(utf8_qprocess_environment())
        args = [
            str(script),
            "--requirements", str(self.engine_root / "requirements-studio.txt"),
            "--python", tool_python(self.engine_root),
            "--mode", "online",
            "--force",
        ]
        self.editor_view.show_bottom_panel()
        self.editor_view.bottom.show_console()
        self.editor_view.clear_console()
        self._append_output("[ENV] Checking and updating environment libraries...\n")
        proc.readyReadStandardOutput.connect(
            lambda: self._append_output(decode_process_bytes(proc.readAllStandardOutput()))
        )

        def _done(code: int, _status) -> None:
            self._env_update_proc = None
            if code == 0:
                self._append_output("[ENV] Environment libraries are up to date.\n")
                self.show_status("Environment libraries OK")
            else:
                self._append_output(f"[ENV] Update finished with exit code {code}.\n")
                self.show_status(f"Environment update exit {code}")
            proc.deleteLater()

        proc.finished.connect(_done)
        proc.start(tool_python(self.engine_root), args)
        if not proc.waitForStarted(3000):
            self._env_update_proc = None
            self._append_output("[ENV] Unable to start dependency manager.\n")
            proc.deleteLater()

    # ------------------------------------------------------------ output/status
    def _append_output(self, text: str) -> None:
        self.editor_view.append_console(text)

    def show_status(self, message: str) -> None:
        self.status_state.setText(message)
        self.workbench_state.setText(message)
        self._append_output(message)
        QTimer.singleShot(2400, self._restore_ready)

    def _restore_ready(self) -> None:
        if not self.build_service.active:
            self.status_state.setText("Ready")
            if self.workbench_state.text() not in {"Running", "Launching"}:
                self.workbench_state.setText("Ready")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.build_service.active:
            answer = QMessageBox.question(
                self, "Build in progress",
                "A build is still running. Cancel it and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.build_service.cancel()
        self._save_workspace_session()
        if self.editor_view.can_close():
            self.editor_view.shutdown()
            event.accept()
        else:
            event.ignore()
