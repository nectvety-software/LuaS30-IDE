from __future__ import annotations

from pathlib import Path
import shutil

from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from app.ui.icons import apply_icon
from app.vxpui.custom_dialog import ConfirmDialog, FilePickerDialog, NoticeDialog

IMAGE = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
OPTIMIZABLE = {".png", ".jpg", ".jpeg", ".bmp"}
ASSET = IMAGE | {".mp3", ".wav", ".aac", ".amr", ".mid", ".midi", ".txt", ".bin", ".dat"}


class AssetsView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.root: Path | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("ASSETS")
        title.setObjectName("ViewTitle")
        header.addWidget(title)
        header.addStretch(1)
        # Cột trái chỉ ~190–300px rộng — nút icon-only + tooltip để không bao giờ
        # bị cắt chữ ("Impor", "Optimize Se", "Refresl").
        add = QPushButton()
        add.setToolTip("Import assets")
        add.setAccessibleName("Import")
        apply_icon(add, "add", 14)
        optimize = QPushButton()
        optimize.setToolTip("Optimize Selected")
        optimize.setAccessibleName("Optimize Selected")
        apply_icon(optimize, "build", 14)
        refresh = QPushButton()
        refresh.setToolTip("Refresh")
        refresh.setAccessibleName("Refresh")
        apply_icon(refresh, "refresh", 14)
        for button in (add, optimize, refresh):
            button.setFixedWidth(34)
        add.clicked.connect(self.add_asset)
        optimize.clicked.connect(self.optimize_selected)
        refresh.clicked.connect(self.refresh)
        header.addWidget(add)
        header.addWidget(optimize)
        header.addWidget(refresh)
        layout.addLayout(header)

        splitter = QSplitter()
        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setIconSize(QSize(56, 56))
        self.list.setGridSize(QSize(112, 86))
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.itemSelectionChanged.connect(self.preview)
        self.list.itemDoubleClicked.connect(self.open_selected)
        splitter.addWidget(self.list)

        panel = QFrame()
        panel.setObjectName("Panel")
        side = QVBoxLayout(panel)
        side.setContentsMargins(8, 8, 8, 8)
        self.preview_label = QLabel("Select an asset")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(230, 200)
        self.preview_label.setWordWrap(True)
        self.meta = QLabel("")
        self.meta.setObjectName("Muted")
        self.meta.setWordWrap(True)
        delete = QPushButton("Remove")
        apply_icon(delete, "delete", 14)
        delete.clicked.connect(self.remove_selected)
        side.addWidget(self.preview_label, 1)
        side.addWidget(self.meta)
        side.addWidget(delete)
        splitter.addWidget(panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

    def set_project(self, root: Path | None) -> None:
        self.root = Path(root).resolve() if root else None
        self.refresh()

    def assets_dir(self) -> Path | None:
        if not self.root:
            return None
        directory = self.root / "assets"
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def refresh(self) -> None:
        self.list.clear()
        directory = self.assets_dir()
        if not directory:
            return
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in ASSET:
                continue
            relative = path.relative_to(directory).as_posix()
            item = QListWidgetItem(relative)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(relative)
            if path.suffix.lower() in IMAGE:
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    item.setIcon(QIcon(pixmap.scaled(
                        56, 56,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )))
            self.list.addItem(item)

    def add_asset(self) -> None:
        directory = self.assets_dir()
        if not directory:
            return
        files = FilePickerDialog.get_open_file_names(
            self, "Import assets", str(Path.home()),
            "Assets (*.png *.jpg *.jpeg *.bmp *.gif *.mp3 *.wav *.aac *.amr *.mid *.midi *.txt *.bin *.dat);;All Files (*)",
        )
        for file_name in files:
            src = Path(file_name)
            dst = directory / src.name
            index = 2
            while dst.exists():
                dst = directory / f"{src.stem}_{index}{src.suffix}"
                index += 1
            shutil.copy2(src, dst)
        self.refresh()

    def selected_path(self) -> Path | None:
        item = self.list.currentItem()
        return Path(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def preview(self) -> None:
        path = self.selected_path()
        if not path:
            return
        self.meta.setText(f"{path.name}\n{path.stat().st_size / 1024:.1f} KB\n{path}")
        if path.suffix.lower() in IMAGE:
            pixmap = QPixmap(str(path))
            self.preview_label.setPixmap(pixmap.scaled(
                300, 300,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            self.meta.setText(self.meta.text() + f"\n{pixmap.width()} x {pixmap.height()} px")
        else:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(path.suffix.upper().lstrip(".") + " asset")

    def open_selected(self, *_args) -> None:
        path = self.selected_path()
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def remove_selected(self) -> None:
        path = self.selected_path()
        if not path:
            return
        if ConfirmDialog.ask(
            "Remove asset", f"Delete {path.name} from this project?",
            self, confirm_text="Yes", danger=True,
        ):
            path.unlink(missing_ok=True)
            self.refresh()
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("Select an asset")
            self.meta.clear()

    def optimize_selected(self) -> None:
        path = self.selected_path()
        if not path:
            NoticeDialog("Optimize Asset", "Select an image first.", self).exec()
            return
        if path.suffix.lower() not in OPTIMIZABLE:
            NoticeDialog(
                "Optimize Asset",
                "Only PNG/JPG/BMP images are optimized by the built-in safe optimizer.",
                self,
            ).exec()
            return

        image = QImage(str(path))
        if image.isNull():
            NoticeDialog("Optimize Asset", "The selected image could not be decoded.", self, warning=True).exec()
            return

        before = path.stat().st_size
        temp = path.with_name(path.name + ".luas30.tmp")
        fmt = path.suffix.lower().lstrip(".").upper()
        if fmt == "JPG":
            fmt = "JPEG"
        quality = 88 if fmt == "JPEG" else -1
        if not image.save(str(temp), fmt.encode("ascii"), quality):
            temp.unlink(missing_ok=True)
            NoticeDialog("Optimize Asset", "Qt could not re-encode this image.", self, warning=True).exec()
            return

        after = temp.stat().st_size
        if after < before:
            backup = path.with_suffix(path.suffix + ".bak")
            shutil.copy2(path, backup)
            temp.replace(path)
            backup.unlink(missing_ok=True)
            self.refresh()
            NoticeDialog(
                "Optimize Asset",
                f"Optimized {path.name}: {before / 1024:.1f} KB -> {after / 1024:.1f} KB.",
                self,
            ).exec()
        else:
            temp.unlink(missing_ok=True)
            NoticeDialog(
                "Optimize Asset",
                "The re-encoded image was not smaller, so the original file was kept.",
                self,
            ).exec()
