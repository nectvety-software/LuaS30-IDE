"""
widgets_palette.py — Palette thành phần của UI Designer kiểu App Inventor/vxpflow:

- Cây nhóm (GIAO DIỆN / BỐ CỤC / ĐỒ HỌA) thu gọn được + ô tìm kiếm.
- Kéo thả vào canvas: `_PaletteTree.startDrag` set MIME riêng + ảnh ghost là
  chính thành phần đó (không phải icon chung).
- Bấm 1 lần cũng thêm được vào giữa màn hình.

LƯU Ý: `startDrag` phải override trên chính QTreeWidget — bản trước đặt nó trên
QWidget cha nên Qt dùng drag mặc định, MIME_TYPE không bao giờ được set và
kéo thả không hoạt động.
"""
from __future__ import annotations

from PySide6.QtCore import QMimeData, QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QDrag, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QGraphicsScene, QHBoxLayout, QLabel, QLineEdit,
    QStyle, QStyledItemDelegate, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget
)

from app.ui import palette
from . import items as _items
from .icons_compat import ICON as ICON_PX
from .items import (
    ASSET_REGISTRY, COMPONENTS, GROUP_ASSETS, GROUP_DRAWN, GROUPS,
    SPRITE_REGISTRY, DesignerItem, default_rect, default_text, image_entries,
    image_entry, is_image_token, image_key, image_token,
)
from .asset_import import AUDIO_REGISTRY, audio_key, audio_token, is_audio_token
from .tokens import ACCENT, BG_HOVER, TEXT_2, TEXT_3, TEXT_4

MIME_TYPE = "application/x-nokialua-widget"

# Ô ảnh xem trước trong palette / bảng LỚP: cao đúng bằng icon chuẩn (16px),
# rộng hơn một chút (22px) để Nút bấm / Hàng ngang còn nhìn ra hình dạng — nhét
# một thành phần 78×24 vào ô vuông 16px thì chỉ còn một vạch cao ~4px.
PREVIEW_W = 22
PREVIEW_H = ICON_PX
# ảnh bóng ma bám con trỏ lúc kéo (chỉ để nhìn, không phải icon giao diện)
DRAG_GHOST_PX = 32

ROLE_TYPE = Qt.UserRole
ROLE_VI = Qt.UserRole + 1
ROLE_EN = Qt.UserRole + 2
ROLE_DESC = Qt.UserRole + 3

# mô tả ngắn cho từng thành phần (tooltip + dòng phụ trong palette)
DESCRIPTIONS = {
    "button": "Nút nhấn kích hoạt sự kiện bấm phím/cảm ứng",
    "label": "Hiển thị đoạn văn bản hoặc tiêu đề",
    "checkbox": "Hộp chọn bật/tắt (true/false)",
    "textbox": "Ô nhập văn bản từ bàn phím S30+",
    "image": "Hiển thị hình ảnh / icon",
    "progress": "Thanh tiến trình 0–100%",
    "slider": "Thanh trượt chọn giá trị",
    "switch": "Công tắc bật/tắt dạng gạt",
    "panel": "Khung nền nhóm nội dung",
    "card": "Thẻ nội dung có tiêu đề",
    "row": "Nhóm con theo hàng ngang",
    "column": "Nhóm con theo cột dọc",
    "divider": "Đường kẻ phân cách",
    "spacer": "Khoảng trống đẩy bố cục",
    "canvas": "Vùng vẽ tự do (grid)",
    "sprite": "Nhân vật / vật thể game",
    "tile": "Ô gạch nền 16×16",
    "rect": "Hình chữ nhật màu",
}

_preview_cache: dict[str, QPixmap] = {}


def _render_sprite_pixmap(image, size: int, height: int | None = None) -> QPixmap:
    """Thu sprite vẽ tay vào ô `size`×`height`, giữ pixel sắc nét."""
    height = size if height is None else int(height)
    pm = QPixmap(size, height)
    pm.fill(Qt.transparent)
    if image is None or image.isNull():
        return pm
    p = QPainter(pm)
    p.setRenderHint(QPainter.SmoothPixmapTransform, False)
    margin = max(1.0, min(size, height) * 0.10)
    box_w, box_h = size - margin * 2, height - margin * 2
    w, h = image.width(), image.height()
    scale = min(box_w / w, box_h / h)
    tw, th = max(1.0, w * scale), max(1.0, h * scale)
    p.drawImage(QRectF((size - tw) / 2.0, (height - th) / 2.0, tw, th), image)
    p.end()
    return pm


def _render_audio_pixmap(size: int, height: int | None = None) -> QPixmap:
    """Nốt nhạc đơn sắc cho dòng âm thanh trong palette."""
    from . import icons_compat as icons
    height = size if height is None else int(height)
    pm = QPixmap(size, height)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    inner = max(9, min(size, height) - 6)
    pm2 = icons.colored_pixmap(icons.path_music, "palette.ACCENT", size=inner, stroke=1.8)
    p.drawPixmap((size - inner) // 2, (height - inner) // 2, pm2)
    p.end()
    return pm


def preview_pixmap(token: str, size: int = PREVIEW_W,
                   height: int | None = None) -> QPixmap:
    """Render chính thành phần đó thành pixmap — icon palette đúng bằng kết quả.

    `token` nhận loại thành phần ('button'), token ảnh ('img:abc') và
    token âm thanh ('audio:abc').

    `size` là BỀ RỘNG ô, `height` là CHIỀU CAO — bỏ trống `height` thì ô vuông.
    Hàng palette dùng ô 22×16 chứ không vuông: Nút bấm là 78×24, nhét vào ô
    vuông 16px theo tỉ lệ thì chỉ còn một vạch cao ~4px, không ra hình dạng gì.
    """
    height = size if height is None else int(height)
    key = f"{token}@{size}x{height}"
    if key in _preview_cache:
        return _preview_cache[key]

    if is_image_token(token):
        entry = image_entry(image_key(token))
        pm = _render_sprite_pixmap(entry.get("image") if entry else None, size, height)
        _preview_cache[key] = pm
        return pm

    if is_audio_token(token):
        pm = _render_audio_pixmap(size, height)
        _preview_cache[key] = pm
        return pm

    w, h = default_rect(token)
    scene = QGraphicsScene()
    # Dựng item tạm chỉ để lấy ảnh — KHÔNG được tiêu số của bộ đếm ID, nếu không
    # thành phần đầu tiên người dùng thêm sẽ có ID nhảy cách quãng.
    snapshot = _items.peek_name_counters()
    item = DesignerItem(token, 0, 0, w, h, default_text(token))
    _items.restore_name_counters(snapshot)
    item.setSelected(False)
    scene.addItem(item)
    pm = QPixmap(size, height)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    # lề co giãn theo cỡ ô — lề cứng 3px ăn mất gần nửa ô khi ô chỉ 16px
    margin = max(1.0, min(size, height) * 0.10)
    scene.render(p, QRectF(margin, margin, size - margin * 2, height - margin * 2),
                 QRectF(0, 0, w, h), Qt.KeepAspectRatio)
    p.end()
    scene.removeItem(item)
    _preview_cache[key] = pm
    return pm


def clear_preview_cache():
    _preview_cache.clear()


class _PaletteDelegate(QStyledItemDelegate):
    """Item 2 dòng: tên tiếng Việt + mô tả; nhóm là nhãn xám in hoa.

    Màu lấy trực tiếp từ token theme (không dùng option.palette) — palette của
    QStyleOptionViewItem không đáng tin khi app đang chạy QSS.
    """

    C_GROUP = QColor(TEXT_4)
    C_NAME = QColor(TEXT_2)
    C_DESC = QColor(TEXT_3)
    C_HOVER = QColor(BG_HOVER)

    def sizeHint(self, option, index) -> QSize:
        # hàng thành phần 24px một dòng, hàng nhóm 22px — mật độ kiểu VS Code
        if index.data(ROLE_TYPE):
            return QSize(180, 24)
        return QSize(180, 22)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = option.rect
        wtype = index.data(ROLE_TYPE)

        if not wtype:
            # ---- hàng nhóm ----
            font = painter.font()
            font.setPointSizeF(7.6)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(self.C_GROUP))
            painter.drawText(rect.adjusted(8, 0, -8, 0),
                             int(Qt.AlignLeft | Qt.AlignVCenter),
                             str(index.data(Qt.DisplayRole)).upper())
            painter.restore()
            return

        hovered = bool(option.state & QStyle.State_MouseOver)
        selected = bool(option.state & QStyle.State_Selected)
        if selected or hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(ACCENT) if selected else self.C_HOVER))
            painter.setOpacity(0.30 if selected else 0.55)
            painter.drawRoundedRect(rect.adjusted(3, 2, -3, -2), 5, 5)
            painter.setOpacity(1.0)

        pm = preview_pixmap(str(wtype), PREVIEW_W, PREVIEW_H)
        painter.drawPixmap(rect.left() + 7,
                           rect.top() + (rect.height() - PREVIEW_H) // 2, pm)

        text_left = rect.left() + 7 + PREVIEW_W + 6
        vi = str(index.data(ROLE_VI) or "")
        en = str(index.data(ROLE_EN) or "")
        # mô tả đầy đủ nằm ở tooltip của hàng (xem `_widget_item`), không chiếm
        # thêm một dòng — hàng một dòng mới giữ được mật độ kiểu VS Code
        font = painter.font()
        font.setPointSizeF(8.2)
        font.setBold(True)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        name_w = metrics.horizontalAdvance(vi)
        painter.setPen(QPen(self.C_NAME))
        painter.drawText(QRectF(text_left, rect.top(), name_w + 4, rect.height()),
                         int(Qt.AlignLeft | Qt.AlignVCenter), vi)

        # tên tiếng Anh mờ nối sau tên tiếng Việt: "Nút bấm  Button"
        tail_left = text_left + name_w + 7
        tail_w = rect.right() - tail_left - 8
        if tail_w > 14:
            font.setBold(False)
            painter.setFont(font)
            painter.setPen(QPen(self.C_DESC))
            metrics = painter.fontMetrics()
            painter.drawText(QRectF(tail_left, rect.top(), tail_w, rect.height()),
                             int(Qt.AlignLeft | Qt.AlignVCenter),
                             metrics.elidedText(en, Qt.ElideRight, int(tail_w)))
        painter.restore()


class _PaletteTree(QTreeWidget):
    """Cây palette — override startDrag để set MIME riêng + ghost đúng thành phần."""

    def startDrag(self, supported_actions):
        item = self.currentItem()
        if item is None:
            return
        wtype = item.data(0, ROLE_TYPE)
        if not wtype:
            return
        # âm thanh chỉ để tham chiếu — không kéo thả vào canvas
        if is_audio_token(wtype):
            return
        mime = QMimeData()
        mime.setData(MIME_TYPE, str(wtype).encode("utf-8"))

        # ảnh "bóng ma" theo con trỏ khi kéo — to hơn icon hàng một chút để thấy
        # rõ đang cầm cái gì, nhưng không còn to gấp ba như trước
        pm = preview_pixmap(str(wtype), DRAG_GHOST_PX)
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(pm)
        drag.setHotSpot(QPoint(pm.width() // 2, pm.height() // 2))
        drag.exec(Qt.CopyAction)


class WidgetsPalette(QWidget):
    """Panel thành phần bên trái của UI Designer."""

    addRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DesignerPalette")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(212)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("THÀNH PHẦN")
        header.setObjectName("PanelHeaderTitle")
        header.setContentsMargins(10, 8, 10, 4)
        layout.addWidget(header)

        search_row = QWidget()
        search_layout = QHBoxLayout(search_row)
        search_layout.setContentsMargins(8, 0, 8, 6)
        search_layout.setSpacing(6)
        self.search = QLineEdit()
        self.search.setObjectName("PaletteSearch")
        self.search.setPlaceholderText("Tìm thành phần…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        search_layout.addWidget(self.search)
        layout.addWidget(search_row)

        self.tree = _PaletteTree()
        self.tree.setObjectName("PaletteTree")
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(10)
        self.tree.setIconSize(QSize(PREVIEW_W, PREVIEW_H))
        self.tree.setItemDelegate(_PaletteDelegate(self.tree))
        self.tree.setDragEnabled(True)
        self.tree.setDragDropMode(QAbstractItemView.DragOnly)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.setExpandsOnDoubleClick(False)
        self._build_tree()
        layout.addWidget(self.tree, 1)

        hint = QLabel("Kéo thả vào màn hình, hoặc bấm để thêm")
        hint.setObjectName("PaletteHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

    # ------------------------------------------------ dựng cây
    def _build_tree(self):
        self.tree.clear()
        for group_id, group_title in GROUPS:
            parent = self._group_item(group_title)
            for wtype, info in COMPONENTS.items():
                if info.get("group") != group_id:
                    continue
                self._widget_item(parent, wtype, info.get("vi", wtype),
                                  info.get("en", wtype),
                                  DESCRIPTIONS.get(wtype, ""))

        # ảnh đã đăng ký: sprite vẽ tay + ảnh nhập từ ngoài vào assets/
        for group, title in ((GROUP_DRAWN, GROUP_DRAWN[1]),
                             (GROUP_ASSETS, GROUP_ASSETS[1])):
            entries = [e for e in image_entries() if e.get("group") == group[0]]
            if not entries:
                continue
            parent = self._group_item(title)
            for entry in entries:
                img = entry.get("image")
                size = f"{img.width()}×{img.height()} px" if img is not None else ""
                folder = entry.get("folder") or ""
                desc = " · ".join(x for x in (size, folder) if x)
                self._widget_item(parent, image_token(entry["key"]), entry["title"],
                                  "Ảnh", desc or "Ảnh trong project")
            parent.setExpanded(True)

        # âm thanh đã nhập: chỉ để tham chiếu, không kéo thả được vào canvas
        if AUDIO_REGISTRY:
            parent = self._group_item("ÂM THANH")
            for entry in AUDIO_REGISTRY.values():
                self._widget_item(parent, audio_token(entry["key"]), entry["title"],
                                  "Audio", entry.get("src", ""), draggable=False)
            parent.setExpanded(True)

        self.tree.expandAll()

    def _group_item(self, title: str) -> QTreeWidgetItem:
        parent = QTreeWidgetItem(self.tree)
        parent.setData(0, ROLE_TYPE, "")
        parent.setData(0, Qt.DisplayRole, title)
        parent.setFlags(Qt.ItemIsEnabled)
        font = parent.font(0)
        font.setBold(True)
        parent.setFont(0, font)
        return parent

    def _widget_item(self, parent: QTreeWidgetItem, token: str, vi: str,
                     en: str, desc: str, draggable: bool = True) -> QTreeWidgetItem:
        child = QTreeWidgetItem(parent)
        child.setData(0, ROLE_TYPE, token)
        child.setData(0, Qt.DisplayRole, vi)
        child.setData(0, ROLE_VI, vi)
        child.setData(0, ROLE_EN, en)
        child.setData(0, ROLE_DESC, desc)
        tip = f"{vi} ({en})\n{desc}" if desc else f"{vi} ({en})"
        if not draggable:
            tip += "\nBấm để in tham chiếu Lua ra Console"
        child.setToolTip(0, tip)
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if draggable:
            flags |= Qt.ItemIsDragEnabled
        child.setFlags(flags)
        return child

    # ------------------------------------------------ ảnh / sprite mới
    def add_sprite(self, key: str):
        """Sprite vừa áp dụng từ Sprite Editor: dựng lại cây + cuộn tới nó."""
        self.refresh_assets(focus=image_token(key))

    def add_asset(self, key: str):
        """Ảnh vừa nhập từ ngoài: dựng lại cây + cuộn tới nó."""
        self.refresh_assets(focus=image_token(key))

    def add_audio(self, key: str):
        self.refresh_assets(focus=audio_token(key))

    def refresh_assets(self, focus: str = ""):
        """Dựng lại cây palette sau khi thêm ảnh/âm thanh mới."""
        clear_preview_cache()
        self._build_tree()
        self.search.clear()
        if focus:
            self._reveal(focus)

    def _reveal(self, token: str):
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            for j in range(group.childCount()):
                child = group.child(j)
                if child.data(0, ROLE_TYPE) == token:
                    group.setExpanded(True)
                    self.tree.setCurrentItem(child)
                    self.tree.scrollToItem(child)
                    return

    _reveal_sprite = _reveal

    # ------------------------------------------------ tìm kiếm
    def _filter(self, text: str):
        query = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            visible_children = 0
            for j in range(group.childCount()):
                child = group.child(j)
                haystack = " ".join([
                    str(child.data(0, ROLE_VI) or ""),
                    str(child.data(0, ROLE_EN) or ""),
                    str(child.data(0, ROLE_DESC) or ""),
                    str(child.data(0, ROLE_TYPE) or ""),
                ]).lower()
                match = (not query) or (query in haystack)
                child.setHidden(not match)
                if match:
                    visible_children += 1
            group.setHidden(visible_children == 0)
            if query and visible_children:
                group.setExpanded(True)

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int):
        wtype = item.data(0, ROLE_TYPE)
        if wtype:
            self.addRequested.emit(str(wtype))
