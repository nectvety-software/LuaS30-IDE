"""
canvas.py — Canvas UI Designer kiểu Figma: nền canvas tối palette.BG_INK, "frame"
màn hình 240×320 với border xanh + label kích thước phía trên (như Figma frame),
rulers tọa độ, dot-grid nền.

Thao tác thêm thành phần:
- Kéo thả từ palette → thành phần rơi đúng vị trí con trỏ (kẹp trong màn hình,
  bắt dính lưới 4px), có khung xem trước khi đang kéo.
- Bấm 1 lần trong palette → thêm vào chỗ trống gần giữa màn hình.
- Delete/Backspace → xoá thành phần đang chọn.
"""
from pathlib import Path

from app.ui import palette
from PySide6.QtCore import QPointF, Qt, QRectF, Signal
from PySide6.QtGui import (
    QBrush, QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QPixmap,
)
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsRectItem, QGraphicsPathItem, QGraphicsTextItem

from .guides import (
    AXIS_H, AXIS_V, GUIDE_FRAME_COLOR, GUIDE_OBJECT_COLOR, KIND_FRAME,
    KIND_OBJECT, SNAP_TOLERANCE, solve,
)
from .items import (
    LAYER_Z_BASE, LAYER_Z_STEP, DesignerItem, SCREEN_H, SCREEN_W,
    clamp_to_screen, default_rect, default_text, fit_in_screen,
    is_sprite_token, is_valid_id, snap, sprite_entry, sprite_key, sprite_token,
    unique_id,
)
from .widgets_palette import MIME_TYPE

ZOOM = 2.0  # phóng to 2x cho dễ thao tác trên PC

# Khung màn hình dùng làm vật tham chiếu cho đường dóng tâm/mép (màu vàng).
SCREEN_RECT = QRectF(0, 0, SCREEN_W, SCREEN_H)


def snapping_bypassed() -> bool:
    """Giữ Alt trong lúc kéo = tạm thời không hít dính (kiểu Figma).

    Đọc trực tiếp bàn phím thay vì theo dõi sự kiện: người dùng có thể nhấn/thả
    Alt GIỮA CHỪNG mà không cần nhả chuột.
    """
    from PySide6.QtWidgets import QApplication
    return bool(QApplication.keyboardModifiers() & Qt.AltModifier)


def token_size(token: str) -> tuple[float, float]:
    """Kích thước mặc định của một token palette ('button' hoặc 'sprite:<key>')."""
    if is_sprite_token(token):
        entry = sprite_entry(sprite_key(token))
        image = entry.get("image") if entry else None
        if image is not None and not image.isNull():
            return fit_in_screen(float(image.width()), float(image.height()))
        return 32.0, 32.0
    return default_rect(token)


class PhoneBezel(QGraphicsPathItem):
    """Vỏ máy feature phone (kiểu Nokia S30+) bao quanh màn hình 240×320."""

    def __init__(self):
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(-16, -30, SCREEN_W + 32, SCREEN_H + 32 + 28), 18, 18)
        super().__init__(path)
        self.setPen(QPen(QColor(palette.BORDER_STRONG), 2))
        self.setBrush(QBrush(QColor(palette.BG_ALT)))
        self.setZValue(-20)

        # khe loa thoại phía trên màn hình
        speaker = QGraphicsPathItem(self)
        sp = QPainterPath()
        sp.addRoundedRect(QRectF(SCREEN_W / 2 - 26, -21, 52, 6), 3, 3)
        speaker.setPath(sp)
        speaker.setPen(Qt.NoPen)
        speaker.setBrush(QBrush(QColor(palette.BG_INK)))

        # cụm phím điều hướng phía dưới màn hình
        nav = QGraphicsPathItem(self)
        np = QPainterPath()
        np.addRoundedRect(QRectF(SCREEN_W / 2 - 46, SCREEN_H + 6, 92, 20), 10, 10)
        np.addRoundedRect(QRectF(SCREEN_W / 2 - 30, SCREEN_H + 11, 60, 10), 5, 5)
        nav.setPath(np)
        nav.setPen(QPen(QColor(palette.BORDER_STRONG), 1.4))
        nav.setBrush(QBrush(QColor(palette.BG_SURFACE)))


class ScreenFrame(QGraphicsRectItem):
    """Khung màn hình 240x320, kiểu Figma frame (nền tối theo theme IDE)."""

    def __init__(self):
        super().__init__(0, 0, SCREEN_W, SCREEN_H)
        self.setPen(QPen(QColor(palette.BORDER_STRONG), 1))
        self.setBrush(QBrush(QColor(palette.BG_INK)))  # nền màn hình tối, hợp theme IDE
        self.setZValue(-10)

        # label kích thước phía trên frame
        self.size_label = QGraphicsTextItem(f"{SCREEN_W} × {SCREEN_H}")
        self.size_label.setDefaultTextColor(QColor(palette.TEXT_4))
        from PySide6.QtGui import QFont
        self.size_label.setFont(QFont("Inter", 6))
        self.size_label.setPos(0, -12)
        self.size_label.setParentItem(self)


class DesignerScene(QGraphicsScene):
    itemSelected = Signal(object)  # DesignerItem hoặc None
    widgetAdded = Signal(object)   # DesignerItem vừa được thêm
    layersChanged = Signal()       # danh sách lớp đổi: thêm/xoá/đổi thứ tự/xoay
    # BẤT KỲ thay đổi nào làm nội dung tệp .lua khác đi — kể cả kéo thành phần
    # hay sửa ô trong INSPECTOR (những thao tác KHÔNG phát `layersChanged`).
    # Đây là tín hiệu để tự động lưu biết "canvas đang bẩn".
    contentChanged = Signal()

    def __init__(self):
        super().__init__(-44, -52, SCREEN_W + 88, SCREEN_H + 110)
        self.setBackgroundBrush(QBrush(QColor(palette.BG_INK)))
        self._bezel = PhoneBezel()
        self.addItem(self._bezel)
        self._screen = ScreenFrame()
        self.addItem(self._screen)
        # đường dóng căn chỉnh đang hiện (view đọc để vẽ ở drawForeground)
        self._guides: list = []
        # bật/tắt hít dính — nút nam châm trên toolbar điều khiển
        self.snapping = True
        # True khi đang NẠP hàng loạt (mở tệp / dựng màn hình trống): mọi thông
        # báo thay đổi bị nuốt, nếu không thì vừa mở tệp đã bị coi là "bẩn" và
        # tự động lưu ghi đè ngược lại chính tệp vừa đọc.
        self.bulk = False
        self.selectionChanged.connect(self._on_selection_changed)
        # mọi thay đổi cấu trúc lớp (thêm/xoá/đổi thứ tự/xoay) đều làm nội dung
        # tệp .lua khác đi -> coi là "bẩn". Kéo/nhập liệu phát riêng từ item.
        self.layersChanged.connect(self.notify_content_changed)

    # ------------------------------------------------ thông báo thay đổi
    def begin_bulk(self):
        """Bắt đầu nạp hàng loạt — tạm nuốt mọi thông báo thay đổi."""
        self.bulk = True

    def end_bulk(self):
        self.bulk = False

    def notify_content_changed(self):
        """Nội dung sẽ khác đi trên đĩa — phát cho tầng tự động lưu."""
        if self.bulk:
            return
        self.contentChanged.emit()

    def _on_selection_changed(self):
        items = self.selectedItems()
        self.itemSelected.emit(items[0] if items else None)

    # ------------------------------------------------ đường dóng căn chỉnh
    def guides(self) -> list:
        """Các đường dóng đang hiện (rỗng khi không kéo gì)."""
        return self._guides

    def set_guides(self, guides):
        """Thay danh sách đường dóng rồi yêu cầu vẽ lại."""
        guides = list(guides or ())
        if guides == self._guides:
            return
        self._guides = guides
        self.update()

    def clear_guides(self):
        self.set_guides(())

    def alignment_refs(self, exclude=None) -> list:
        """Vật tham chiếu để dóng: khung màn hình TRƯỚC, rồi các thành phần khác.

        Khung đứng đầu vì khi hai phương án cùng độ lệch thì phương án gặp trước
        thắng — dóng theo khung (đường vàng) là thông tin đáng chú ý hơn.
        Chỉ lấy thành phần ĐANG HIỆN: lớp bị ẩn không được kéo vật khác theo.
        """
        refs = [(SCREEN_RECT, KIND_FRAME)]
        for item in self.widget_items():
            if item is exclude or not item.isVisible():
                continue
            refs.append((item.aligned_bounds(), KIND_OBJECT))
        return refs

    def snap_item(self, item: DesignerItem, x: float, y: float) -> tuple[float, float]:
        """Vị trí đã hít dính cho `item` khi đang bị kéo — cập nhật đường dóng.

        Thứ tự quan trọng: hít dính TRƯỚC rồi mới kẹp vào màn hình. Nếu bước kẹp
        làm mất đúng vị trí vừa dóng (vật quá to so với chỗ còn lại) thì bỏ luôn
        đường dóng — thà không vẽ còn hơn vẽ một đường nói dối.
        """
        if not self.snapping or snapping_bypassed():
            self.clear_guides()
            return x, y
        refs = self.alignment_refs(exclude=item)
        if not refs:
            self.clear_guides()
            return x, y

        box = item.aligned_bounds(QPointF(x, y))
        dx, dy, guides = solve(box, refs, tolerance=SNAP_TOLERANCE)
        nx, ny = x + dx, y + dy

        if item.rotation():
            cx, cy = item._clamp_for_rotation(nx, ny)
        else:
            cx, cy = clamp_to_screen(nx, ny, item.rect().width(), item.rect().height())
        if (cx, cy) != (nx, ny):
            guides = []
        self.set_guides(guides)
        return cx, cy

    # ------------------------------------------------ thêm thành phần
    def drop_origin_for(self, w: float, h: float, cx: float, cy: float,
                        with_guides: bool = False) -> tuple[float, float]:
        """Góc trên-trái khi thả thành phần cỡ (w, h) tại tâm (cx, cy).

        `with_guides=True` (khung xem trước khi kéo từ palette) thì hít dính
        luôn và cập nhật đường dóng, để thấy trước đúng chỗ thành phần sẽ nằm.
        """
        x, y = snap(cx - w / 2), snap(cy - h / 2)
        x, y = clamp_to_screen(x, y, w, h)
        if not with_guides:
            return x, y
        if not self.snapping or snapping_bypassed():
            self.clear_guides()
            return x, y

        refs = self.alignment_refs()
        dx, dy, guides = solve(QRectF(x, y, w, h), refs, tolerance=SNAP_TOLERANCE)
        nx, ny = clamp_to_screen(x + dx, y + dy, w, h)
        if (nx, ny) != (x + dx, y + dy):
            guides = []
        self.set_guides(guides)
        return nx, ny

    def drop_origin(self, widget_type: str, cx: float, cy: float) -> tuple[float, float]:
        """Góc trên-trái khi thả thành phần tại tâm (cx, cy) — bắt dính + kẹp màn hình."""
        w, h = token_size(widget_type)
        return self.drop_origin_for(w, h, cx, cy)

    def _make_item(self, token: str, x: float, y: float) -> DesignerItem:
        w, h = token_size(token)
        if is_sprite_token(token):
            entry = sprite_entry(sprite_key(token)) or {}
            item = DesignerItem("image", x, y, w, h, "",
                                image=entry.get("image"), src=entry.get("src", ""))
            # ID lấy theo TÊN TỆP ảnh (game_background.png -> game_background_12),
            # không lấy cả đường dẫn assets/background/... (ID sẽ dài ngoẵng)
            stem = Path(entry.get("src") or entry.get("key") or "image").stem
            item.set_name(f"{stem}_{item.seq}")
        else:
            item = DesignerItem(token, x, y, w, h, default_text(token))
        # ID phải là duy nhất trong scene (và là định danh Lua hợp lệ)
        item.set_name(unique_id(item.name, self.taken_names()))
        self.addItem(item)
        self.clearSelection()
        item.setSelected(True)
        # thành phần vừa thêm luôn nằm TRÊN CÙNG (đầu danh sách LAYERS)
        self._assign_z([item] + [it for it in self.layer_items() if it is not item])
        self.widgetAdded.emit(item)
        self.layersChanged.emit()
        return item

    def add_token(self, token: str, x: float, y: float) -> DesignerItem:
        """Thả một token palette (thành phần hoặc sprite) tại điểm (x, y)."""
        w, h = token_size(token)
        px, py = self.drop_origin_for(w, h, x, y)
        return self._make_item(token, px, py)

    def add_token_at(self, token: str, x: float, y: float) -> DesignerItem:
        """Thả token tại ĐÚNG góc trên-trái đã tính sẵn (đã hít dính + kẹp).

        Dùng cho đường thả thật: khung xem trước đã hít dính ở `drop_origin_for`
        rồi, nếu tính lại từ toạ độ con trỏ thì thành phần sẽ rơi lệch khỏi chỗ
        người dùng vừa thấy.
        """
        w, h = token_size(token)
        px, py = clamp_to_screen(x, y, w, h)
        return self._make_item(token, px, py)

    def add_widget(self, widget_type: str, x: float, y: float) -> DesignerItem:
        """Thả thành phần tại điểm (x, y) trong scene — tâm thành phần ở điểm đó."""
        return self.add_token(widget_type, x, y)

    def _free_spot(self, w: float, h: float) -> tuple[float, float]:
        """Dò vị trí trống gần giữa màn hình (cho thao tác bấm-thêm trong palette)."""
        occupied = [it.sceneBoundingRect() for it in self.widget_items()]
        cx, cy = SCREEN_W / 2 - w / 2, SCREEN_H / 2 - h / 2
        for radius in range(0, 10):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if max(abs(dx), abs(dy)) != radius:
                        continue
                    x, y = snap(cx + dx * 14), snap(cy + dy * 14)
                    x, y = clamp_to_screen(x, y, w, h)
                    probe = QRectF(x, y, w, h)
                    if not any(probe.intersects(r) for r in occupied):
                        return x, y
        return clamp_to_screen(snap(cx), snap(cy), w, h)

    def add_token_centered(self, token: str) -> DesignerItem:
        """Bấm trong palette → đặt vào chỗ trống gần giữa màn hình."""
        w, h = token_size(token)
        x, y = self._free_spot(w, h)
        return self._make_item(token, x, y)

    def add_widget_centered(self, widget_type: str) -> DesignerItem:
        return self.add_token_centered(widget_type)

    def add_sprite_centered(self, key: str) -> DesignerItem:
        """Sprite vừa áp dụng từ Sprite Editor → đặt ngay lên canvas."""
        return self.add_token_centered(sprite_token(key))

    def widget_items(self):
        return [it for it in self.items() if isinstance(it, DesignerItem)]

    def clear_widgets(self):
        for it in self.widget_items():
            self.removeItem(it)
        self.clear_guides()
        self.layersChanged.emit()

    def remove_items(self, items) -> int:
        """Xoá các DesignerItem được chỉ định, trả về số lượng đã xoá."""
        count = 0
        for it in list(items):
            if isinstance(it, DesignerItem):
                self.removeItem(it)
                count += 1
        if count:
            self.clear_guides()
            self._assign_z()
            self.layersChanged.emit()
        return count

    # ------------------------------------------------ lớp (z-order)
    def layer_items(self) -> list[DesignerItem]:
        """Mọi thành phần, xếp TRÊN trước — đúng thứ tự bảng LAYERS kiểu Photoshop.

        Cùng z-value thì thành phần tạo sau nằm trên (dùng `seq` để phá hoà, vì
        QGraphicsScene.items() không đảm bảo thứ tự giữa các item cùng z).
        """
        return sorted(self.widget_items(),
                      key=lambda it: (it.zValue(), getattr(it, "seq", 0)),
                      reverse=True)

    def _assign_z(self, order: list[DesignerItem] | None = None):
        """Gán lại z-value liên tục theo thứ tự TRÊN-trước (order[0] là trên cùng)."""
        if order is None:
            order = self.layer_items()
        n = len(order)
        for index, item in enumerate(order):
            # order[0] = trên cùng -> z lớn nhất
            item.setZValue(LAYER_Z_BASE + (n - 1 - index) * LAYER_Z_STEP)

    def set_layer_order(self, order: list[DesignerItem]):
        """Áp thứ tự lớp mới (order[0] là trên cùng) — dùng khi kéo-thả trong bảng."""
        valid = [it for it in order if isinstance(it, DesignerItem)]
        known = set(self.widget_items())
        # thành phần không có trong danh sách (nếu có) đẩy xuống dưới cùng
        valid += [it for it in self.layer_items() if it not in valid and it in known]
        self._assign_z(valid)
        self.layersChanged.emit()

    def move_layer(self, item: DesignerItem, delta: int) -> bool:
        """Dịch lớp lên/xuống `delta` bậc. delta > 0 = lên trên (ra trước)."""
        order = self.layer_items()
        if item not in order or delta == 0:
            return False
        i = order.index(item)
        j = max(0, min(len(order) - 1, i - delta))
        if i == j:
            return False
        order.pop(i)
        order.insert(j, item)
        self._assign_z(order)
        self.layersChanged.emit()
        return True

    def bring_to_front(self, item: DesignerItem) -> bool:
        return self.move_layer(item, len(self.widget_items()))

    def send_to_back(self, item: DesignerItem) -> bool:
        return self.move_layer(item, -len(self.widget_items()))

    # ------------------------------------------------ ID thành phần
    def taken_names(self) -> set[str]:
        """Tập ID đang dùng trong scene (để cấp ID mới không trùng)."""
        return {it.name for it in self.widget_items()}

    def rename_item(self, item: DesignerItem, new_name: str) -> tuple[bool, str]:
        """Đổi ID thành phần — CỬA DUY NHẤT để đổi tên, dùng chung mọi lối vào.

        Trả (thành công, thông báo lỗi). Kiểm tra hai điều:
          * ID phải là định danh Lua hợp lệ (`[A-Za-z_][A-Za-z0-9_]*`) vì nó
            được ghi vào mã ở khoá `name` và `ui.<id>`;
          * ID không được trùng với thành phần khác trong scene.

        KHÔNG phát `layersChanged` — tên không phải trạng thái vẽ, nên bảng
        LAYERS tự cập nhật hàng tại chỗ (tránh dựng lại danh sách ngay trong
        slot `itemChanged` của chính nó). Nơi gọi khác thì tự `refresh()`.
        """
        if not isinstance(item, DesignerItem):
            return False, "đối tượng không phải thành phần UI"
        name = str(new_name or "").strip()
        if not name:
            return False, "ID không được để trống"
        if not is_valid_id(name):
            return False, ("ID chỉ gồm chữ, số và '_', và phải bắt đầu bằng "
                           "chữ hoặc '_' (VD: btn_start)")
        if name == item.name:
            return True, ""
        if name in self.taken_names():
            return False, f"ID '{name}' đã được dùng cho thành phần khác"
        item.set_name(name)
        return True, ""

    # ------------------------------------------------ nhân bản / xoay
    def duplicate_item(self, item: DesignerItem, offset: float = 8.0) -> DesignerItem | None:
        """Nhân bản một thành phần, lệch nhẹ để thấy ngay bản mới."""
        if not isinstance(item, DesignerItem):
            return None
        clone = DesignerItem.from_dict(item.to_dict())
        # bản sao phải có ID RIÊNG (không đè lên bản gốc trong mã Lua)
        clone.set_name(unique_id(item.name, self.taken_names()))
        # đặt ngay trên bản gốc trong bảng lớp
        order = self.layer_items()
        index = order.index(item) if item in order else 0
        order.insert(index, clone)
        self.addItem(clone)
        clone.setPos(item.pos().x() + offset, item.pos().y() + offset)
        self._assign_z(order)
        self.clearSelection()
        clone.setSelected(True)
        self.widgetAdded.emit(clone)
        self.layersChanged.emit()
        return clone

    def rotate_item(self, item: DesignerItem, delta: float = 90.0) -> bool:
        """Xoay thành phần quanh tâm (mặc định 90° mỗi lần bấm)."""
        if not isinstance(item, DesignerItem):
            return False
        item.rotate_by(delta)
        self.layersChanged.emit()
        return True

    def resize_to_fit_screen(self) -> int:
        """Thu mọi thành phần quá khổ về trong màn hình 240×320."""
        fixed = 0
        for it in self.widget_items():
            w, h = it.rect().width(), it.rect().height()
            nw, nh = fit_in_screen(w, h)
            if (nw, nh) != (w, h):
                it.set_size(nw, nh)
                fixed += 1
        return fixed


class DesignerView(QGraphicsView):
    MIN_ZOOM = 0.45
    MAX_ZOOM = 2.0

    def __init__(self, scene: DesignerScene, parent=None):
        super().__init__(scene, parent)
        self._scene = scene
        self.setAcceptDrops(True)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor(palette.BG_INK)))
        # canvas scroll không viền, hiện thanh cuộn mỏng khi cần
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setAlignment(Qt.AlignCenter)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)

        # dot grid nền (kiểu Figma) vẽ bằng background brush pattern
        pm = QPixmap(16, 16)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setPen(QColor(palette.BORDER))
        p.drawPoint(0, 0)
        p.end()
        self.setBackgroundBrush(QBrush(pm))
        self._fit_pending = True

        # trạng thái kéo-thả
        self._drag_type: str | None = None
        self._drop_pos = None
        # góc trên-trái đã hít dính của khung xem trước (tính ở _begin_drop để
        # drawForeground chỉ việc vẽ, không phải sửa trạng thái scene mỗi lần vẽ)
        self._drop_origin: tuple[float, float] | None = None

    # ---------------- auto fit ----------------
    def showEvent(self, event):
        super().showEvent(event)
        self._fit_to_view()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_to_view()

    def _fit_to_view(self):
        """Canh vừa toàn bộ 'điện thoại' 240×320 vào khung canvas (có lề)."""
        rect = self.sceneRect()
        if rect.isEmpty():
            return
        vw = self.viewport().width()
        vh = self.viewport().height()
        if vw < 20 or vh < 20:
            return
        zoom = min(vw / (rect.width() * 1.12), vh / (rect.height() * 1.12))
        zoom = max(self.MIN_ZOOM, min(zoom, self.MAX_ZOOM))
        self.resetTransform()
        self.scale(zoom, zoom)
        self.centerOn(rect.center())

    def zoom_in(self):
        self._apply_zoom(1.15)

    def zoom_out(self):
        self._apply_zoom(1 / 1.15)

    def reset_zoom(self):
        self._fit_to_view()

    def _apply_zoom(self, factor):
        current = self.transform().m11()
        target = max(self.MIN_ZOOM, min(current * factor, self.MAX_ZOOM * 1.6))
        if abs(target - current) < 1e-4:
            return
        self.scale(target / current, target / current)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self._apply_zoom(1.12 if event.angleDelta().y() > 0 else 1 / 1.12)
            event.accept()
            return
        super().wheelEvent(event)

    # ---------------- bàn phím ----------------
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            removed = self._scene.remove_items(self._scene.selectedItems())
            if removed:
                event.accept()
                return
        super().keyPressEvent(event)

    # ---------------- kéo thả từ palette ----------------
    def _begin_drop(self, event):
        self._drag_type = bytes(event.mimeData().data(MIME_TYPE)).decode("utf-8")
        self._drop_pos = self.mapToScene(event.position().toPoint())
        w, h = token_size(self._drag_type)
        # hít dính + đường dóng cho chính khung xem trước, để thấy trước đúng
        # chỗ thành phần sẽ nằm chứ không phải đoán
        self._drop_origin = self._scene.drop_origin_for(
            w, h, self._drop_pos.x(), self._drop_pos.y(), with_guides=True)
        self.viewport().update()

    def _clear_drop(self):
        self._drag_type = None
        self._drop_pos = None
        self._drop_origin = None
        self._scene.clear_guides()
        self.viewport().update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_TYPE):
            self._begin_drop(event)
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_TYPE):
            self._begin_drop(event)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._clear_drop()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(MIME_TYPE):
            self._clear_drop()
            return
        token = bytes(event.mimeData().data(MIME_TYPE)).decode("utf-8")
        if self._drop_origin is not None:
            # rơi đúng chỗ khung xem trước đã hít dính
            x, y = self._drop_origin
            self._scene.add_token_at(token, x, y)
        else:
            scene_pos = self.mapToScene(event.position().toPoint())
            self._scene.add_token(token, scene_pos.x(), scene_pos.y())
        self._clear_drop()
        self.setFocus()
        event.acceptProposedAction()

    def drawForeground(self, painter, rect):
        """Vẽ lớp phủ: đường dóng căn chỉnh + khung xem trước khi kéo từ palette."""
        super().drawForeground(painter, rect)
        self._draw_guides(painter)
        self._draw_drop_preview(painter)

    def _draw_guides(self, painter):
        """Đường căn gạch nét: XANH khi dóng với thành phần khác, VÀNG khi dóng
        với tâm/mép khung màn hình."""
        guides = self._scene.guides()
        if not guides:
            return
        painter.save()
        painter.setBrush(Qt.NoBrush)
        for guide in guides:
            color = QColor(GUIDE_FRAME_COLOR if guide.kind == KIND_FRAME
                           else GUIDE_OBJECT_COLOR)
            pen = QPen(color)
            # bút cosmetic: nét và đoạn gạch giữ nguyên độ dày/độ dài trên màn
            # hình dù canvas đang phóng to hay thu nhỏ
            pen.setCosmetic(True)
            pen.setWidthF(1.0)
            pen.setStyle(Qt.CustomDashLine)
            pen.setDashPattern([5.0, 4.0])
            painter.setPen(pen)
            if guide.axis == AXIS_V:
                painter.drawLine(QPointF(guide.pos, guide.start),
                                 QPointF(guide.pos, guide.end))
            else:
                painter.drawLine(QPointF(guide.start, guide.pos),
                                 QPointF(guide.end, guide.pos))
        painter.restore()

    def _draw_drop_preview(self, painter):
        """Phản hồi khi kéo thành phần từ palette: KHUNG MÀN HÌNH sáng lên (nơi
        sẽ nhận thành phần) + bóng thành phần ở đúng chỗ nó sắp rơi + nhãn toạ độ.

        Khung và bóng phải khác kiểu nét: khung là nét LIỀN (nói "đây là cái
        khung sẽ nhận"), bóng là nét GẠCH (nói "cái này sắp rơi vào đó"). Trước
        đây cả hai đều gạch nét xanh nên nhìn không phân biệt được.
        """
        if not self._drag_type or self._drop_pos is None:
            return
        painter.save()

        w, h = token_size(self._drag_type)
        if self._drop_origin is not None:
            x, y = self._drop_origin
        else:
            x, y = self._scene.drop_origin_for(w, h, self._drop_pos.x(),
                                               self._drop_pos.y())

        # 1. khung màn hình 240×320 — viền liền + nền xanh rất nhạt
        painter.setPen(QPen(QColor(palette.ACCENT), 1.6))
        painter.setBrush(QBrush(QColor(79, 140, 255, 18)))
        painter.drawRect(SCREEN_RECT)

        # 2. bóng thành phần tại đúng vị trí đã hít dính
        painter.setPen(QPen(QColor(palette.AMBER), 1.2, Qt.DashLine))
        painter.setBrush(QBrush(QColor(79, 140, 255, 60)))
        box = QRectF(x, y, w, h)
        painter.drawRoundedRect(box, 3, 3)

        # sprite: vẽ luôn bitmap mờ để thấy trước kết quả
        if is_sprite_token(self._drag_type):
            entry = sprite_entry(sprite_key(self._drag_type)) or {}
            image = entry.get("image")
            if image is not None and not image.isNull():
                painter.setOpacity(0.75)
                painter.drawImage(box, image)
                painter.setOpacity(1.0)

        # 3. nhãn "x, y  w×h" — biết chắc nó sẽ rơi ở đâu, không phải đoán
        self._draw_drop_badge(painter, box)
        painter.restore()

    def _draw_drop_badge(self, painter, box: QRectF):
        """Nhãn toạ độ/kích thước nổi phía trên bóng thành phần.

        Vẽ trong hệ toạ độ scene nên phải tự chọn cỡ chữ nhỏ (view thường phóng
        1,6×) — và tự lật xuống dưới khi bóng đã sát mép trên khung.
        """
        text = (f"{round(box.x())}, {round(box.y())}   "
                f"{round(box.width())}×{round(box.height())}")
        font = QFont("Segoe UI", 6)
        painter.setFont(font)
        metrics = QFontMetricsF(font)
        pad = 3.0
        tw = metrics.horizontalAdvance(text)
        th = metrics.height()
        bw, bh = tw + pad * 2, th + pad * 0.6

        bx = box.x()
        bx = min(bx, SCREEN_W - bw)          # đừng tràn ra ngoài khung
        by = box.y() - bh - 3.0              # mặc định: ngay trên bóng
        if by < 0:                           # hết chỗ trên -> lật xuống dưới
            by = box.bottom() + 3.0
        badge = QRectF(bx, by, bw, bh)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(79, 140, 255, 235)))
        painter.drawRoundedRect(badge, 2.5, 2.5)
        painter.setPen(QPen(QColor(palette.BG_SURFACE)))
        painter.drawText(badge, int(Qt.AlignCenter), text)
