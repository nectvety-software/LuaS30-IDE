"""Trang "Tiện ích mở rộng" dạng danh sách card kiểu marketplace.

Mỗi tiện ích trong ``extensions/`` (theo chuẩn ``extension.json`` do
``ExtensionService`` khám phá) hiển thị thành một card: ô icon bo góc bên
trái, tên + mô tả hai dòng + hàng "from · version · added", nút mở ở góc
phải — bố cục theo đúng ảnh mẫu người dùng, nền tối dùng token palette.
"""
from __future__ import annotations

import time
from typing import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.vxpui.icons import icon


def _added_label(manifest_path: Path) -> str:
    try:
        added = time.localtime(manifest_path.stat().st_mtime)
        return time.strftime("%d/%m/%Y", added)
    except OSError:
        return ""


def _two_lines(text: str, limit: int = 118) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


class ExtensionCard(QFrame):
    def __init__(self, manifest, on_open: Callable[[str], None], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ExtensionMarketCard")
        self.setFixedHeight(92)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(14)

        tile = QLabel(self)
        tile.setObjectName("ExtensionMarketIcon")
        tile.setFixedSize(46, 46)
        tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile.setPixmap(icon(manifest.icon).pixmap(22, 22))
        layout.addWidget(tile, 0, Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title = QLabel(manifest.name, self)
        title.setObjectName("ExtensionMarketTitle")
        desc = QLabel(_two_lines(manifest.description or manifest.id), self)
        desc.setObjectName("ExtensionMarketDesc")
        desc.setWordWrap(True)
        meta_bits = [f"from {manifest.author or 'không rõ'}", f"v{manifest.version}"]
        added = _added_label(manifest.manifest_path)
        if added:
            meta_bits.append(f"added {added}")
        meta = QLabel(" · ".join(meta_bits), self)
        meta.setObjectName("ExtensionMarketMeta")
        text_col.addWidget(title)
        text_col.addWidget(desc)
        text_col.addWidget(meta)
        layout.addLayout(text_col, 1)

        open_btn = QToolButton(self)
        open_btn.setObjectName("ExtensionMarketOpen")
        open_btn.setFixedSize(34, 34)
        open_btn.setText("+")
        open_btn.setToolTip(f"Mở {manifest.name}")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(lambda _checked=False: on_open(manifest.id))
        layout.addWidget(open_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event) -> None:  # click toàn card = mở
        if event.button() == Qt.MouseButton.LeftButton:
            self.findChild(QToolButton).click()
            event.accept()
            return
        super().mousePressEvent(event)


class ExtensionMarketView(QWidget):
    def __init__(
        self,
        service,
        on_open: Callable[[str], None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ExtensionMarketPage")
        self.service = service
        self.on_open = on_open

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget(self)
        header.setObjectName("ExtensionMarketHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(10)
        intro = QLabel(
            "Tiện ích đặt trong thư mục extensions/ của IDE — mỗi thư mục có "
            "extension.json là xuất hiện ở đây, không cần cài lại.",
            header,
        )
        intro.setObjectName("ExtensionMarketIntro")
        intro.setWordWrap(True)
        refresh = QToolButton(header)
        refresh.setObjectName("ExtensionMarketRefresh")
        refresh.setText("↻")
        refresh.setToolTip("Quét lại thư mục extensions/")
        refresh.setFixedSize(30, 30)
        refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh.clicked.connect(self.reload)
        header_layout.addWidget(intro, 1)
        header_layout.addWidget(refresh, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(header)

        self.scroll = QScrollArea(self)
        self.scroll.setObjectName("ExtensionMarketScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.body = QWidget()
        self.body.setObjectName("ExtensionMarketBody")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(16, 12, 16, 16)
        self.body_layout.setSpacing(10)
        self.scroll.setWidget(self.body)
        root.addWidget(self.scroll, 1)

        self.reload()

    def reload(self) -> None:
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        manifests = self.service.discover(refresh=True)
        if not manifests:
            empty = QLabel(
                "Chưa có tiện ích nào.\n"
                "Tạo thư mục extensions/<tên>/ kèm extension.json rồi bấm ↻."
            )
            empty.setObjectName("ExtensionMarketEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.body_layout.addWidget(empty)
        else:
            for manifest in manifests:
                self.body_layout.addWidget(ExtensionCard(manifest, self.on_open))
        self.body_layout.addStretch(1)
