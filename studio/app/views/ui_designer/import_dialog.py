"""
import_dialog.py — Hộp thoại "Nhập tài nguyên" của UI Designer.

Chọn tệp ảnh/âm thanh từ ngoài, chọn đích đến trong cây `assets/` của project,
xem trước đường dẫn sẽ ghi rồi mới copy. Engine nạp tài nguyên bằng đường dẫn
tương đối project (`engine.image(x, y, "assets/ui/btn.png")`), nên tệp phải nằm
trong project chứ không phải ở đâu đó ngoài ổ đĩa.

Đích đến và cách copy do `asset_import.py` quyết định — hộp thoại này chỉ là
phần giao diện.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QSizePolicy, QVBoxLayout, QWidget,
)

from app.vxpui.custom_dialog import FilePickerDialog

from .asset_import import (
    KIND_AUDIO, KIND_IMAGE, TARGETS, TARGET_DIRS, classify, file_filter,
    guess_target, human_size, import_files,
)
from .modal import ModalDialog


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("DialogHint")
    label.setWordWrap(True)
    return label


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("DesignerCard")
    card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(10, 8, 10, 10)
    layout.setSpacing(6)
    label = QLabel(title)
    label.setObjectName("PropName")
    layout.addWidget(label)
    return card, layout


def _row_button(layout: QHBoxLayout, text: str, on_click):
    from PySide6.QtWidgets import QPushButton

    button = QPushButton(text)
    button.setObjectName("GhostButton")
    button.setMinimumHeight(26)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.clicked.connect(on_click)
    layout.addWidget(button)
    return button


class ImportAssetDialog(ModalDialog):
    """Nhập ảnh / âm thanh vào đúng thư mục assets/ của project."""

    def __init__(self, parent=None, project_root=None, kind: str = KIND_IMAGE,
                 initial_files=None):
        title = ("Nhập ảnh vào project" if kind == KIND_IMAGE
                 else "Nhập âm thanh vào project")
        message = ("Tệp sẽ được COPY vào thư mục assets/ của project — engine "
                   "nạp bằng đường dẫn chuẩn, không phải đường dẫn ngoài.")
        super().__init__(title, message, parent, width=560)

        self.project_root = Path(project_root) if project_root else None
        self.kind = kind
        self.imported: list[dict] = []
        self._files: list[Path] = []

        # ---- card: tệp nguồn ----
        src_card, src_layout = _card("Tệp nguồn")
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(78)
        self.file_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection)
        src_layout.addWidget(self.file_list)
        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        _row_button(buttons, "Chọn tệp…", self._pick_files)
        _row_button(buttons, "Bỏ chọn", self._remove_selected)
        buttons.addStretch(1)
        src_layout.addLayout(buttons)
        self.add_body_widget(src_card)

        # ---- card: đích đến ----
        dest_card, dest_layout = _card("Đích đến trong project")
        self.target_combo = QComboBox()
        for key, label, rel in TARGETS.get(kind, []):
            self.target_combo.addItem(f"{label}   →   {rel}/", key)
        self.target_combo.currentIndexChanged.connect(self._refresh_preview)
        dest_layout.addWidget(self.target_combo)

        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        name_row.addWidget(QLabel("Đổi tên"))
        self.rename_edit = QLineEdit()
        self.rename_edit.setPlaceholderText("(giữ nguyên tên tệp gốc)")
        self.rename_edit.textChanged.connect(self._refresh_preview)
        name_row.addWidget(self.rename_edit, 1)
        dest_layout.addLayout(name_row)
        self.add_body_widget(dest_card)

        # ---- card: xem trước ----
        preview_card, preview_layout = _card("Sẽ ghi")
        preview_row = QHBoxLayout()
        preview_row.setSpacing(8)
        self.thumb = QLabel()
        self.thumb.setFixedSize(QSize(56, 56))
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.thumb.setVisible(False)
        preview_row.addWidget(self.thumb)
        self.preview_label = _hint("")
        preview_row.addWidget(self.preview_label, 1)
        preview_layout.addLayout(preview_row)
        self.add_body_widget(preview_card)

        self.add_button("Huỷ", ghost=True, on_click=self.reject)
        self.confirm_btn = self.add_button("Nhập", primary=True,
                                           on_click=self._accept)
        self.confirm_btn.setEnabled(False)

        self.file_list.itemSelectionChanged.connect(self._refresh_preview)
        if initial_files:
            self._set_files([Path(p) for p in initial_files])

    # ------------------------------------------------ chọn tệp
    def _pick_files(self):
        files = FilePickerDialog.get_open_file_names(
            self, "Chọn tệp để nhập", str(Path.home()), file_filter(self.kind))
        if files:
            self._set_files([Path(f) for f in files])

    def _set_files(self, files: list[Path]):
        self._files = []
        self.file_list.clear()
        for path in files:
            if not path.is_file():
                continue
            self._files.append(path)
            item = QListWidgetItem(f"{path.name}   ·   {human_size(path.stat().st_size)}")
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            self.file_list.addItem(item)
        if self.file_list.count():
            self.file_list.setCurrentRow(0)
            # gợi ý đích theo tên tệp đầu tiên
            key = guess_target(self._files[0])
            index = self.target_combo.findData(key)
            if index >= 0:
                self.target_combo.setCurrentIndex(index)
        self._refresh_preview()

    def _remove_selected(self):
        keep = {str(i.data(Qt.ItemDataRole.UserRole))
                for i in self.file_list.selectedItems()}
        self._set_files([p for p in self._files if str(p) not in keep])

    # ------------------------------------------------ xem trước
    def _current_file(self) -> Path | None:
        item = self.file_list.currentItem()
        if item is None:
            return None
        return Path(item.data(Qt.ItemDataRole.UserRole))

    def _preview_paths(self) -> list[str]:
        target = self.target_combo.currentData()
        rel_dir = TARGET_DIRS.get(target, "assets")
        rename = self.rename_edit.text().strip()
        paths = []
        for index, src in enumerate(self._files):
            if rename:
                stem = Path(rename).stem
                name = (f"{stem}{src.suffix}" if len(self._files) == 1
                        else f"{stem}_{index + 1}{src.suffix}")
            else:
                name = src.name
            paths.append(f"{rel_dir}/{name}")
        return paths

    def _refresh_preview(self):
        paths = self._preview_paths()
        if not paths:
            self.preview_label.setText("Chưa chọn tệp nào.")
        elif len(paths) == 1:
            self.preview_label.setText(paths[0])
        else:
            head = "\n".join(f"  {p}" for p in paths[:4])
            more = f"\n  … và {len(paths) - 4} tệp nữa" if len(paths) > 4 else ""
            self.preview_label.setText(f"{len(paths)} tệp:\n{head}{more}")
        self.confirm_btn.setEnabled(bool(paths) and self.project_root is not None)

        current = self._current_file()
        if (self.kind == KIND_IMAGE and current is not None
                and classify(current) == KIND_IMAGE):
            pixmap = QPixmap(str(current))
            if not pixmap.isNull():
                self.thumb.setPixmap(pixmap.scaled(
                    56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation))
                self.thumb.setVisible(True)
                return
        self.thumb.setPixmap(QPixmap())
        self.thumb.setVisible(False)

    # ------------------------------------------------ thực hiện
    def _accept(self):
        if self.project_root is None or not self._files:
            return
        target = self.target_combo.currentData()
        try:
            self.imported = import_files(
                self.project_root, self._files, target,
                rename=self.rename_edit.text().strip())
        except OSError as exc:
            self.preview_label.setText(f"Không copy được tệp: {exc}")
            return
        self.accept()
