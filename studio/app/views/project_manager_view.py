from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSortFilterProxyModel, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSplitter, QTableView, QVBoxLayout, QWidget, QInputDialog,
)

from app.editor.project_tree import ProjectTree
from app.services.project_library import ProjectLibraryService, ProjectRecord
from app.ui.icons import apply_icon


class ProjectFilterModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.query_text = ""

    def set_query(self, text: str) -> None:
        self.query_text = text.strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        if not self.query_text:
            return True
        model = self.sourceModel()
        needle = self.query_text
        values = []
        for column in range(min(3, model.columnCount())):
            idx = model.index(row, column, parent)
            values.append(str(model.data(idx) or ""))
        return needle in " ".join(values).lower()


class ProjectManagerView(QWidget):
    open_project_requested = Signal(object)
    new_project_requested = Signal()
    duplicate_project_requested = Signal(object, str)
    rename_project_requested = Signal(object, str)
    delete_project_requested = Signal(object)
    status_message = Signal(str)

    ROLE_PATH = int(Qt.ItemDataRole.UserRole) + 21

    def __init__(self, service: ProjectLibraryService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.current_project: Path | None = None
        self.records: dict[str, ProjectRecord] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 7, 10, 10)
        root.setSpacing(7)

        header = QHBoxLayout()
        title = QLabel("PROJECT STORAGE")
        title.setObjectName("ViewTitle")
        self.storage = QLabel(str(self.service.projects_root))
        self.storage.setObjectName("Muted")
        self.storage.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        header.addWidget(title)
        header.addWidget(self.storage, 1)

        new_btn = QPushButton("New Project")
        apply_icon(new_btn, "add", 14)
        import_btn = QPushButton("Import")
        apply_icon(import_btn, "folder_open", 14)
        refresh_btn = QPushButton("Refresh")
        apply_icon(refresh_btn, "refresh", 14)
        new_btn.clicked.connect(self.new_project_requested)
        import_btn.clicked.connect(self.import_project)
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(new_btn)
        header.addWidget(import_btn)
        header.addWidget(refresh_btn)
        root.addLayout(header)

        # Trái: cây thư mục của kho project. Tái dùng `ProjectTree` của Explorer
        # (QFileSystemModel) thay vì viết cây mới — cùng một cây, cùng cách ẩn
        # `build/`/`.git`/`release`, cùng context menu, nên không có hai hành vi
        # khác nhau cho cùng một việc.
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)

        tree_panel = QFrame()
        tree_panel.setObjectName("Panel")
        tree_layout = QVBoxLayout(tree_panel)
        tree_layout.setContentsMargins(7, 5, 7, 7)
        tree_layout.setSpacing(4)
        tree_title = QLabel("STORAGE TREE")
        tree_title.setObjectName("Muted")
        tree_layout.addWidget(tree_title)
        self.tree = ProjectTree()
        self.tree.setMinimumWidth(180)
        self.tree.status_message.connect(self.status_message)
        self.tree.clicked.connect(self._on_tree_clicked)
        # Cây cho phép tạo/xoá/đổi tên ngay trên đĩa, nên bảng phải quét lại sau
        # đó — nếu không, danh sách project sẽ lệch với thực tế trên đĩa.
        self.tree.path_changed.connect(lambda _path: self.refresh())
        self.tree.set_project_root(self.service.projects_root)
        tree_layout.addWidget(self.tree, 1)
        splitter.addWidget(tree_panel)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(7)

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter projects by name, path or App ID")
        self.summary = QLabel("0 projects")
        self.summary.setObjectName("Muted")
        search_row.addWidget(self.search, 1)
        search_row.addWidget(self.summary)
        right_layout.addLayout(search_row)

        self.model = QStandardItemModel(0, 7, self)
        self.model.setHorizontalHeaderLabels(["Project", "Path", "App ID", "Modified", "Size", "Files", "Build"])
        self.proxy = ProjectFilterModel(self)
        self.proxy.setSourceModel(self.model)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(0, 190)
        self.table.setColumnWidth(1, 430)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 135)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 60)
        self.table.setColumnWidth(6, 90)
        self.table.doubleClicked.connect(lambda _idx: self.open_selected())
        right_layout.addWidget(self.table, 1)

        footer = QFrame()
        footer.setObjectName("Panel")
        row = QHBoxLayout(footer)
        row.setContentsMargins(7, 5, 7, 5)
        row.setSpacing(5)

        open_btn = QPushButton("Open")
        apply_icon(open_btn, "folder_open", 14)
        duplicate_btn = QPushButton("Duplicate")
        apply_icon(duplicate_btn, "copy", 14)
        rename_btn = QPushButton("Rename")
        apply_icon(rename_btn, "edit", 14)
        delete_btn = QPushButton("Delete")
        apply_icon(delete_btn, "delete", 14)
        reveal_btn = QPushButton("Reveal")
        apply_icon(reveal_btn, "open_external", 14)
        open_btn.clicked.connect(self.open_selected)
        duplicate_btn.clicked.connect(self.duplicate_selected)
        rename_btn.clicked.connect(self.rename_selected)
        delete_btn.clicked.connect(self.delete_selected)
        reveal_btn.clicked.connect(self.reveal_selected)
        for button in (open_btn, duplicate_btn, rename_btn, delete_btn, reveal_btn):
            row.addWidget(button)
        row.addStretch(1)
        right_layout.addWidget(footer)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 1100])
        root.addWidget(splitter, 1)

        self.search.textChanged.connect(self._filter)
        self.refresh()

    def set_current_project(self, path: Path | None) -> None:
        self.current_project = Path(path).resolve() if path else None
        self.refresh()
        if self.current_project is not None:
            # "Bạn đang ở đây". Chỉ chạy khi project thật sự đổi (lúc mở project),
            # không chạy theo từng cú bấm trong cây, nên không giành lựa chọn của
            # người dùng.
            self.tree.reveal_path(self.current_project)

    def _filter(self, text: str) -> None:
        self.proxy.set_query(text)
        self.summary.setText(f"{self.proxy.rowCount()} / {self.model.rowCount()} projects")

    def refresh(self) -> None:
        selected = self.selected_path()
        records = self.service.scan()
        self.records = {str(record.root): record for record in records}
        self.model.removeRows(0, self.model.rowCount())
        for record in records:
            name = record.display_name
            if self.current_project and record.root == self.current_project:
                name += "  [CURRENT]"
            row = [
                QStandardItem(name),
                QStandardItem(str(record.root)),
                QStandardItem(record.app_id),
                QStandardItem(record.modified_text),
                QStandardItem(record.size_text),
                QStandardItem(str(record.file_count)),
                QStandardItem(record.vxp_path.name if record.vxp_path else "-"),
            ]
            for item in row:
                item.setEditable(False)
            row[0].setData(str(record.root), self.ROLE_PATH)
            self.model.appendRow(row)
        self.summary.setText(f"{self.proxy.rowCount()} / {len(records)} projects")
        if selected:
            self._select_path(selected)

    def selected_path(self) -> Path | None:
        indexes = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not indexes:
            return None
        source = self.proxy.mapToSource(indexes[0])
        value = self.model.item(source.row(), 0).data(self.ROLE_PATH)
        return Path(value).resolve() if value else None

    def _select_path(self, path: Path) -> None:
        target = str(Path(path).resolve())
        for row in range(self.model.rowCount()):
            if self.model.item(row, 0).data(self.ROLE_PATH) == target:
                proxy = self.proxy.mapFromSource(self.model.index(row, 0))
                if proxy.isValid():
                    self.table.selectRow(proxy.row())
                break

    def _managed_root_for(self, path: Path) -> Path | None:
        """Gốc project đang quản lý chứa `path`, nếu có."""
        candidate = Path(path).resolve()
        for record in self.records.values():
            root = Path(record.root).resolve()
            if candidate == root or root in candidate.parents:
                return root
        return None

    def _on_tree_clicked(self, _index) -> None:
        """Bấm trong cây thì soi sang bảng.

        Thư mục CON của một project cũng tính là project đó — bấm vào
        `<project>/build` thì chọn dòng của chính project ấy, thay vì im lặng
        không làm gì.
        """
        path = self.tree.selected_path()
        if path is None:
            return
        match = self._managed_root_for(path)
        if match is not None:
            self._select_path(match)

    def open_selected(self) -> None:
        path = self.selected_path()
        if path:
            self.open_project_requested.emit(path)

    def import_project(self) -> None:
        source = QFileDialog.getExistingDirectory(self, "Import LuaS30 Project")
        if not source:
            return
        source_path = Path(source)
        if not (source_path / "project.json").is_file():
            QMessageBox.warning(self, "Import Project", "Selected folder has no project.json.")
            return
        name, ok = QInputDialog.getText(self, "Import Project", "Storage project name:", text=source_path.name)
        if not ok:
            return
        try:
            destination = self.service.import_project(source_path, name)
            self.refresh()
            self._select_path(destination)
            self.status_message.emit(f"Imported project: {destination.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Import Project", str(exc))

    def duplicate_selected(self) -> None:
        source = self.selected_path()
        if not source:
            return
        name, ok = QInputDialog.getText(self, "Duplicate Project", "New project name:", text=f"{source.name}_copy")
        if not ok:
            return
        self.duplicate_project_requested.emit(source, name.strip())

    def rename_selected(self) -> None:
        source = self.selected_path()
        if not source:
            return
        name, ok = QInputDialog.getText(self, "Rename Project", "New project name:", text=source.name)
        if not ok or name.strip() == source.name:
            return
        self.rename_project_requested.emit(source, name.strip())

    def delete_selected(self) -> None:
        source = self.selected_path()
        if not source:
            return
        if QMessageBox.question(
            self, "Delete Project",
            f"Delete managed project '{source.name}'?\n\nThis removes the entire project folder and cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self.delete_project_requested.emit(source)

    def select_path(self, path: Path) -> None:
        self._select_path(path)

    def reveal_selected(self) -> None:
        path = self.selected_path()
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
