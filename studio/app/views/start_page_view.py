from __future__ import annotations

from pathlib import Path

from app.ui import palette
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget, QInputDialog,
)

from app.services.project_library import ProjectLibraryService
from app.ui.icons import apply_icon, font_icon


class StartPageView(QWidget):
    """VS Code-like startup page backed by LuaS30 Project Storage."""

    new_project_requested = Signal()
    open_folder_requested = Signal()
    open_project_requested = Signal(object)
    manage_projects_requested = Signal()
    status_message = Signal(str)

    ROLE_PATH = int(Qt.ItemDataRole.UserRole) + 71

    def __init__(
        self,
        service: ProjectLibraryService,
        *,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.current_project: Path | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("StartPageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(scroll)

        surface = QWidget()
        surface.setObjectName("StartPage")
        scroll.setWidget(surface)

        page = QVBoxLayout(surface)
        page.setContentsMargins(42, 34, 42, 22)
        page.setSpacing(20)

        content = QWidget()
        content.setObjectName("StartPageContent")
        content.setMaximumWidth(1120)
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(20)

        # Hero
        hero = QHBoxLayout()
        hero.setSpacing(12)
        logo = QLabel()
        logo.setObjectName("StartLogo")
        logo.setPixmap(font_icon("code", 34, "palette.ACCENT").pixmap(34, 34))
        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel("LuaS30 IDE")
        title.setObjectName("StartHeroTitle")
        subtitle = QLabel("MRE / VXP development workspace")
        subtitle.setObjectName("StartHeroSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        hero.addWidget(logo, 0, Qt.AlignmentFlag.AlignTop)
        hero.addLayout(titles)
        hero.addStretch(1)
        body.addLayout(hero)

        columns = QHBoxLayout()
        columns.setSpacing(52)

        # Left: Start + Recent
        left = QVBoxLayout()
        left.setSpacing(8)
        start_title = QLabel("Start")
        start_title.setObjectName("StartSectionTitle")
        left.addWidget(start_title)

        new_btn = self._link_button("New Project...", "new_file")
        open_btn = self._link_button("Open Project Folder...", "folder_open")
        import_btn = self._link_button("Import into Project Storage...", "projects")
        storage_btn = self._link_button("Manage Project Storage...", "projects")

        new_btn.clicked.connect(self.new_project_requested)
        open_btn.clicked.connect(self.open_folder_requested)
        import_btn.clicked.connect(self.import_project)
        storage_btn.clicked.connect(self.manage_projects_requested)

        for button in (new_btn, open_btn, import_btn, storage_btn):
            left.addWidget(button)

        left.addSpacing(14)
        recent_title = QLabel("Recent")
        recent_title.setObjectName("StartSectionTitle")
        left.addWidget(recent_title)

        self.recent = QListWidget()
        self.recent.setObjectName("RecentProjects")
        self.recent.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.recent.setMinimumHeight(220)
        self.recent.setMaximumHeight(280)
        self.recent.itemActivated.connect(self._open_recent_item)
        self.recent.itemDoubleClicked.connect(self._open_recent_item)
        left.addWidget(self.recent)

        more_btn = self._link_button("More...", "forward")
        more_btn.clicked.connect(self.manage_projects_requested)
        left.addWidget(more_btn, 0, Qt.AlignmentFlag.AlignLeft)
        left.addStretch(1)

        # Right: storage cards / quick workspace status
        right = QVBoxLayout()
        right.setSpacing(10)
        storage_title = QLabel("Project Storage")
        storage_title.setObjectName("StartSectionTitle")
        right.addWidget(storage_title)

        storage_card = QFrame()
        storage_card.setObjectName("StartCard")
        storage_layout = QVBoxLayout(storage_card)
        storage_layout.setContentsMargins(14, 12, 14, 12)
        storage_layout.setSpacing(8)

        card_head = QHBoxLayout()
        card_icon = QLabel()
        card_icon.setPixmap(font_icon("projects", 20, "palette.ACCENT").pixmap(20, 20))
        card_title = QLabel("LuaS30 Projects")
        card_title.setObjectName("StartCardTitle")
        card_head.addWidget(card_icon)
        card_head.addWidget(card_title)
        card_head.addStretch(1)
        storage_layout.addLayout(card_head)

        self.storage_path = QLabel(str(self.service.projects_root))
        self.storage_path.setObjectName("StartPath")
        self.storage_path.setWordWrap(True)
        self.storage_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        storage_layout.addWidget(self.storage_path)

        stats = QHBoxLayout()
        self.project_count = QLabel("0 projects")
        self.project_count.setObjectName("StartMetric")
        self.storage_size = QLabel("0 B")
        self.storage_size.setObjectName("StartMetric")
        self.build_count = QLabel("0 builds")
        self.build_count.setObjectName("StartMetric")
        stats.addWidget(self.project_count)
        stats.addWidget(self.storage_size)
        stats.addWidget(self.build_count)
        stats.addStretch(1)
        storage_layout.addLayout(stats)

        actions = QHBoxLayout()
        manage = QPushButton("Manage Projects")
        manage.setObjectName("StartCardButton")
        apply_icon(manage, "projects", 14)
        reveal = QPushButton("Open Storage Folder")
        reveal.setObjectName("StartCardButton")
        apply_icon(reveal, "folder_open", 14)
        manage.clicked.connect(self.manage_projects_requested)
        reveal.clicked.connect(self.open_storage_folder)
        actions.addWidget(manage)
        actions.addWidget(reveal)
        actions.addStretch(1)
        storage_layout.addLayout(actions)
        right.addWidget(storage_card)

        workspace_title = QLabel("Workspace")
        workspace_title.setObjectName("StartSectionTitle")
        right.addWidget(workspace_title)

        self.workspace_card = QFrame()
        self.workspace_card.setObjectName("StartCard")
        workspace_layout = QVBoxLayout(self.workspace_card)
        workspace_layout.setContentsMargins(14, 12, 14, 12)
        workspace_layout.setSpacing(7)
        self.current_name = QLabel("No project opened")
        self.current_name.setObjectName("StartCardTitle")
        self.current_path = QLabel("Create a project or open one from Project Storage.")
        self.current_path.setObjectName("StartPath")
        self.current_path.setWordWrap(True)
        workspace_layout.addWidget(self.current_name)
        workspace_layout.addWidget(self.current_path)
        right.addWidget(self.workspace_card)

        quick_title = QLabel("Quick Start")
        quick_title.setObjectName("StartSectionTitle")
        right.addWidget(quick_title)

        single_vxp = QFrame()
        single_vxp.setObjectName("StartCard")
        sv = QVBoxLayout(single_vxp)
        sv.setContentsMargins(14, 11, 14, 11)
        sv.setSpacing(4)
        h = QLabel("Single VXP workflow")
        h.setObjectName("StartCardTitle")
        d = QLabel("One Lua project, one generic MRE/VXP artifact, runtime capability detection.")
        d.setObjectName("StartPath")
        d.setWordWrap(True)
        sv.addWidget(h)
        sv.addWidget(d)
        right.addWidget(single_vxp)
        right.addStretch(1)

        columns.addLayout(left, 5)
        columns.addLayout(right, 5)
        body.addLayout(columns)

        startup_hint = QLabel("Startup screen can be changed in Settings.")
        startup_hint.setObjectName("Muted")
        body.addWidget(startup_hint, 0, Qt.AlignmentFlag.AlignHCenter)

        # Center page inside wide editors.
        center = QHBoxLayout()
        center.addStretch(1)
        center.addWidget(content, 1)
        center.addStretch(1)
        page.addStretch(1)
        page.addLayout(center)
        page.addStretch(2)

        self.refresh()

    @staticmethod
    def _link_button(text: str, icon_name: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("StartLinkButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_icon(button, icon_name, 15, "palette.ACCENT")
        return button

    @staticmethod
    def _format_size(value: int) -> str:
        size = float(max(0, value))
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024.0 or unit == "GB":
                return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{value} B"

    def set_current_project(self, path: Path | None) -> None:
        self.current_project = Path(path).resolve() if path else None
        if self.current_project:
            self.current_name.setText(self.current_project.name)
            self.current_path.setText(str(self.current_project))
        else:
            self.current_name.setText("No project opened")
            self.current_path.setText("Create a project or open one from Project Storage.")
        self.refresh()

    def refresh(self) -> None:
        records = self.service.scan()
        total_size = sum(record.size_bytes for record in records)
        builds = sum(1 for record in records if record.has_build)

        self.project_count.setText(f"{len(records)} project" + ("" if len(records) == 1 else "s"))
        self.storage_size.setText(self._format_size(total_size))
        self.build_count.setText(f"{builds} build" + ("" if builds == 1 else "s"))

        selected = None
        current = self.recent.currentItem()
        if current:
            selected = current.data(self.ROLE_PATH)

        self.recent.clear()
        for record in records[:8]:
            item = QListWidgetItem()
            item.setText(f"{record.display_name}\n{record.root}")
            item.setToolTip(str(record.root))
            item.setData(self.ROLE_PATH, str(record.root))
            item.setIcon(font_icon("folder", 15, "palette.ACCENT"))
            item.setSizeHint(item.sizeHint().expandedTo(item.sizeHint()))
            self.recent.addItem(item)
            if selected and str(record.root) == selected:
                self.recent.setCurrentItem(item)

        if not records:
            item = QListWidgetItem("No projects in storage yet.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.recent.addItem(item)

    def _open_recent_item(self, item: QListWidgetItem) -> None:
        value = item.data(self.ROLE_PATH)
        if value:
            self.open_project_requested.emit(Path(str(value)))

    def import_project(self) -> None:
        source = QFileDialog.getExistingDirectory(self, "Import LuaS30 Project")
        if not source:
            return
        source_path = Path(source).resolve()
        if not (source_path / "project.json").is_file():
            QMessageBox.warning(self, "Import Project", "Selected folder has no project.json.")
            return
        name, ok = QInputDialog.getText(
            self, "Import Project", "Storage project name:", text=source_path.name
        )
        if not ok:
            return
        try:
            destination = self.service.import_project(source_path, name.strip())
            self.refresh()
            self.status_message.emit(f"Imported project: {destination.name}")
            self.open_project_requested.emit(destination)
        except Exception as exc:
            QMessageBox.critical(self, "Import Project", str(exc))

    def open_storage_folder(self) -> None:
        self.service.projects_root.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.service.projects_root)))
