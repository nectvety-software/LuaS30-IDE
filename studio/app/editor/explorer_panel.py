from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.ui.icons import apply_icon

from app.editor.project_tree import ProjectTree


class ExplorerPanel(QFrame):
    file_activated = Signal(object)
    status_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ExplorerPanel")
        self.project_root: Path | None = None
        self._title_base = "EXPLORER"

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("ExplorerHeader")
        row = QHBoxLayout(header)
        row.setContentsMargins(8, 3, 4, 3)
        row.setSpacing(2)

        self.title = QLabel("EXPLORER")
        self.title.setObjectName("SidePanelTitle")
        row.addWidget(self.title, 1)

        self.new_file = QPushButton("")
        apply_icon(self.new_file, "new_file", 14)
        self.new_file.setToolTip("New File")
        self.new_folder = QPushButton("")
        apply_icon(self.new_folder, "new_folder", 14)
        self.new_folder.setToolTip("New Folder")
        self.collapse = QPushButton("")
        apply_icon(self.collapse, "collapse", 14)
        self.collapse.setToolTip("Collapse Folders")
        self.refresh = QPushButton("")
        apply_icon(self.refresh, "refresh", 14)
        self.refresh.setToolTip("Refresh")

        for button in (self.new_file, self.new_folder, self.collapse, self.refresh):
            button.setObjectName("ExplorerToolButton")
            button.setFixedSize(24, 22)
            row.addWidget(button)

        self.tree = ProjectTree()
        root.addWidget(header)
        root.addWidget(self.tree, 1)

        self.tree.file_activated.connect(self.file_activated)
        self.tree.status_message.connect(self.status_message)
        self.refresh.clicked.connect(self.tree.refresh)
        self.collapse.clicked.connect(self.tree.collapse_all_folders)
        self.new_file.clicked.connect(self._new_file)
        self.new_folder.clicked.connect(self._new_folder)

    def set_project_root(self, root: str | Path) -> None:
        self.project_root = Path(root).resolve()
        self._set_title(self.project_root.name.upper())
        self.tree.set_project_root(self.project_root)
        self.tree.show()


    def clear_project(self) -> None:
        self.project_root = None
        self._set_title("NO PROJECT")
        self.tree.clear_project_root()
        self.tree.hide()

    def _set_title(self, text: str) -> None:
        self._title_base = text
        self.title.setToolTip(text)
        self._update_title_text()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_title_text()

    def _update_title_text(self) -> None:
        """Elide tên dự án bằng '…' khi cột hẹp (QLabel không tự làm việc này)."""
        buttons_width = 4 * 24 + 3 * 2 + 8 + 4  # 4 nút + spacing + lề hàng
        available = self.width() - buttons_width - 12  # padding-left của label
        metrics = self.title.fontMetrics()
        self.title.setText(
            metrics.elidedText(self._title_base, Qt.TextElideMode.ElideRight, max(24, available))
        )

    def _base(self) -> Path | None:
        selected = self.tree.selected_path()
        if selected and selected.is_file():
            return selected.parent
        return selected or self.project_root

    def _new_file(self) -> None:
        base = self._base()
        if base:
            self.tree._new_file(base)

    def _new_folder(self) -> None:
        base = self._base()
        if base:
            self.tree._new_folder(base)
