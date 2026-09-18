"""
designer_view.py — Ghép palette + canvas + inspector thành UI Designer hoàn chỉnh.

Bố cục (giống bản lua-engine): toolbar nhỏ → thanh MÀN HÌNH → breadcrumb → thân
gồm [palette | canvas | inspector | LAYERS].

KHÁC BIỆT VỀ LƯU TRỮ so với bản gốc: bản gốc ghi mỗi màn hình thành hai tệp
trong `src/ui/` (`<tên>.ui.dtfe` + `<tên>.lua`). Studio LuaS30 gói tất cả vào
một tệp `.luas30/ui_design.json` và sinh một tệp `ui_design.lua` để game nạp —
xem `design_store.py`. Vì vậy ở đây màn hình được định danh bằng **id** (chuỗi)
chứ không phải đường dẫn tệp, và không còn tệp logic riêng để đồng bộ ID.

Đổi ID thành phần ở bảng LAYERS hoặc ô ID trong INSPECTOR sẽ ghi lại
`ui_design.json` ngay, nên tệp trên đĩa luôn khớp canvas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.ui import palette
from PySide6.QtCore import QSize, Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QToolBar,
    QVBoxLayout, QWidget,
)

from . import icons_compat as icons
from .asset_import import (
    KIND_AUDIO, KIND_IMAGE, audio_entry, audio_key, audio_token, is_audio_token,
    register_audio, scan_project_audio, scan_project_images,
)
from .canvas import DesignerScene, DesignerView
from .design_store import (
    DESIGN_FILENAME, EXPORT_FILENAME, MAIN_SCREEN_ID, UI_DIR, DesignStore,
    export_path, items_to_scene, relative_to_project, scene_to_items,
)
from .items import image_for_src, image_token, load_image, register_asset
from .layers_panel import LayersPanel
from .lua_export import export_lua
from .modal import confirm_dialog
from .properties_panel import PropertiesPanel
from .screen_bar import ScreenBar, ScreenNameDialog, screen_slug
from .widgets_palette import WidgetsPalette


class UIDesignerWidget(QWidget):
    """UI Designer đầy đủ — xem docstring đầu tệp."""

    logMessage = Signal(str)
    assetsImported = Signal()      # báo MainWindow dựng lại cây EXPLORER
    screensChanged = Signal()      # màn hình được tạo / đổi tên / nhân bản / xoá
    dirtyChanged = Signal(bool)    # canvas có thay đổi chưa ghi xuống đĩa
    designSaved = Signal(object)   # đường dẫn vừa ghi (ui_design.json / .lua)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.store = DesignStore()
        self.current_screen: Optional[str] = None
        self._last_ids: list[str] = []
        self._dirty = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- toolbar ----
        toolbar = QToolBar()
        toolbar.setObjectName("DesignerToolbar")
        toolbar.setMovable(False)
        # icon phải được RENDER đúng 20px rồi mới cho hiển thị 20px — nếu render
        # 16px rồi để Qt phóng lên, glyph sẽ nhoè
        toolbar.setIconSize(QSize(icons.ICON_TOOLBAR, icons.ICON_TOOLBAR))

        tb_new = toolbar.addAction(
            icons.icon_file("palette.TEXT_2", icons.ICON_TOOLBAR), "Màn hình mới",
            self.new_screen)
        tb_new.setToolTip("Xoá canvas, bắt đầu màn hình mới (chưa lưu)")
        tb_save = toolbar.addAction(
            icons.icon_save("palette.TEXT_2", icons.ICON_TOOLBAR), "Lưu + xuất Lua",
            self.export_lua)
        tb_save.setToolTip(f"Ghi {DESIGN_FILENAME} và sinh {EXPORT_FILENAME}")
        toolbar.addSeparator()
        tb_img = toolbar.addAction(
            icons.icon_image("palette.TEXT_2", icons.ICON_TOOLBAR), "Nhập ảnh",
            self.import_images)
        tb_img.setToolTip("Nhập ảnh từ ngoài vào assets/ của project")
        tb_audio = toolbar.addAction(
            icons.icon_play("palette.TEXT_2", icons.ICON_TOOLBAR), "Nhập âm thanh",
            self.import_audio)
        tb_audio.setToolTip("Nhập âm thanh vào assets/sfx hoặc assets/music")
        toolbar.addSeparator()
        # hít dính căn chỉnh: bật/tắt đường dóng khi kéo thành phần
        self.snap_action = toolbar.addAction(
            icons.icon_magnet("palette.ACCENT", icons.ICON_TOOLBAR), "Hít dính")
        self.snap_action.setCheckable(True)
        self.snap_action.setChecked(True)
        self.snap_action.setToolTip(
            "Bật/tắt hít dính căn chỉnh (mặc định BẬT)\n\n"
            "Khi kéo thành phần, nó tự dóng thẳng hàng với:\n"
            "  • thành phần khác — đường gạch nét XANH\n"
            "  • tâm / 4 mép khung màn hình — đường gạch nét VÀNG\n"
            "Giữ Alt khi kéo để tạm thời không hít dính.")
        self.snap_action.toggled.connect(self._toggle_snapping)

        toolbar.addSeparator()
        tb_zoom_out = toolbar.addAction(
            icons.icon_zoom_out("palette.TEXT_2", icons.ICON_TOOLBAR), "", self._zoom_out)
        tb_zoom_out.setToolTip("Thu nhỏ (Ctrl+−)")
        tb_fit = toolbar.addAction(
            icons.icon_frame("palette.TEXT_2", icons.ICON_TOOLBAR), "", self._zoom_fit)
        tb_fit.setToolTip("Canh vừa khung")
        tb_zoom_in = toolbar.addAction(
            icons.icon_zoom_in("palette.TEXT_2", icons.ICON_TOOLBAR), "", self._zoom_in)
        tb_zoom_in.setToolTip("Phóng to (Ctrl++)")
        outer.addWidget(toolbar)

        # ---- thanh MÀN HÌNH: chọn / tạo / đổi tên / nhân bản / xoá ----
        self.screen_bar = ScreenBar()
        self.screen_bar.screenSelected.connect(self._on_screen_selected)
        self.screen_bar.createRequested.connect(self.create_screen)
        self.screen_bar.renameRequested.connect(self.rename_screen)
        self.screen_bar.duplicateRequested.connect(self.duplicate_screen)
        self.screen_bar.deleteRequested.connect(self.delete_screen)
        self.screen_bar.revealRequested.connect(self.reveal_design)
        outer.addWidget(self.screen_bar)

        # ---- breadcrumb ----
        self.title_label = QLabel("  Chưa có màn hình UI nào được mở")
        self.title_label.setObjectName("DesignerBreadcrumb")
        outer.addWidget(self.title_label)

        # ---- thân ----
        body = QWidget()
        body_layout = QHBoxLayout(body)
        self.body_layout = body_layout
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.palette = WidgetsPalette()
        self.palette.addRequested.connect(self._add_component)
        body_layout.addWidget(self.palette)

        self.scene = DesignerScene()
        self.view = DesignerView(self.scene)
        self.scene.widgetAdded.connect(self._on_widget_added)
        body_layout.addWidget(self.view, 1)

        self.properties = PropertiesPanel()
        self.scene.itemSelected.connect(self.properties.set_item)
        body_layout.addWidget(self.properties)

        # ---- bảng LAYERS kiểu Photoshop (thứ tự lớp / nhân bản / xoay / đổi ID) ----
        self.layers = LayersPanel()
        self.layers.logMessage.connect(self.logMessage)
        self.layers.itemRenamed.connect(self._on_item_renamed)
        self.layers.attach(self.scene)
        body_layout.addWidget(self.layers)

        # đổi ID ở ô "ID" trong INSPECTOR cũng đi qua cùng một đường
        self.properties.idEdited.connect(self._on_id_edited)

        self._last_ids = self._screen_ids()
        self.scene.layersChanged.connect(self._on_layers_changed)
        self.scene.contentChanged.connect(self._mark_dirty)

        outer.addWidget(body, 1)

        self._install_shortcuts()

    def _install_shortcuts(self):
        """Ctrl+D nhân bản lớp, Ctrl+Shift+↑/↓ đưa lớp ra trước / ra sau, Ctrl+Shift+R xoay.

        Đặt context WidgetShortcut nên chỉ ăn khi con trỏ đang ở UI Designer —
        không tranh chấp với Ctrl+R (Build + Package + Run) của cả IDE.
        """
        from PySide6.QtGui import QKeySequence, QShortcut

        def bind(seq: str, slot):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ShortcutContext.WidgetShortcut)
            sc.activated.connect(slot)
            return sc

        self._shortcuts = [
            bind("Ctrl+D", self.layers.duplicate_layer),
            bind("Ctrl+Shift+Up", self.layers.raise_layer),
            bind("Ctrl+Shift+Down", self.layers.lower_layer),
            bind("Ctrl+Shift+R", self.layers.rotate_layer),
        ]

    def take_properties_panel(self):
        """Nhả PropertiesPanel khỏi layout để MainWindow đưa vào cột INSPECTOR.

        Signal scene.itemSelected -> panel.set_item vẫn giữ nguyên sau khi
        widget được reparent, nên bảng thuộc tính hoạt động bình thường.
        """
        panel = self.properties
        if panel is None:
            return None
        self.body_layout.removeWidget(panel)
        panel.setParent(None)
        return panel

    # ---------------------------------------------------------------- trạng thái bẩn
    @property
    def has_unsaved_changes(self) -> bool:
        return self._dirty

    def _mark_dirty(self):
        if self._dirty:
            return
        self._dirty = True
        self.dirtyChanged.emit(True)

    def _mark_clean(self):
        if not self._dirty:
            return
        self._dirty = False
        self.dirtyChanged.emit(False)

    # ---------------------------------------------------------------- ghi thiết kế
    def _screen_ids(self) -> list[str]:
        """ID mọi thành phần, theo THỨ TỰ VẼ (dưới trước) — khớp tệp thiết kế."""
        return [it.name for it in
                sorted(self.scene.widget_items(), key=lambda it: it.zValue())]

    def _flush_canvas(self) -> bool:
        """Canvas -> store cho màn hình đang mở (không ghi đĩa)."""
        if self.current_screen is None:
            return False
        self.store.set_screen_items(self.current_screen, scene_to_items(self.scene))
        return True

    def save_design(self, silent: bool = False) -> bool:
        """Ghi `.luas30/ui_design.json`. Trả False + log khi không ghi được."""
        self._flush_canvas()
        if self.store.save():
            self._last_ids = self._screen_ids()
            self._mark_clean()
            return True
        self.logMessage.emit(f"[UI DESIGNER] {self.store.error}")
        return False

    def auto_save(self) -> list:
        """Ghi thiết kế KHÔNG hỏi gì (tự động lưu).

        Canvas RỖNG và chưa có màn hình nào thì không ghi — người dùng vừa bấm
        "Màn hình mới" mà tự động lưu lại đẻ ra màn hình rỗng thì thật khó hiểu.
        """
        if self.current_screen is None and not self.scene.widget_items():
            return []
        if not self.save_design(silent=True):
            return []
        path = self.store.root / UI_DIR / DESIGN_FILENAME if self.store.root else None
        return [path] if path else []

    # ---------------------------------------------------------------- đồng bộ ID
    def _sync_design(self):
        """ID thành phần vừa đổi -> ghi lại tệp thiết kế cho khớp canvas."""
        if self.scene.bulk:
            return
        if self.current_screen is None:
            self.logMessage.emit(
                "[UI DESIGNER] ID đã đổi nhưng chưa có màn hình nào — bấm "
                "'Lưu + xuất Lua' để tạo màn hình, sau đó ID sẽ tự đồng bộ.")
            return
        if self.save_design(silent=True):
            self.logMessage.emit(
                f"[UI DESIGNER] Đã đồng bộ ID vào {UI_DIR}/{DESIGN_FILENAME}")

    def _on_item_renamed(self, item, old_id: str, new_id: str):
        """Bảng LAYERS vừa đổi ID."""
        self.logMessage.emit(f"[UI DESIGNER] Đổi ID '{old_id}' → '{new_id}'")
        self._sync_design()

    def _on_id_edited(self, item, raw: str):
        """Ô 'ID' trong INSPECTOR vừa sửa xong."""
        old = item.name
        ok, err = self.scene.rename_item(item, raw)
        if not ok:
            self.logMessage.emit(f"[UI DESIGNER] Không đổi được ID: {err}")
        self.layers.refresh()
        self.properties.set_item(item)
        if ok and item.name != old:
            self.logMessage.emit(f"[UI DESIGNER] Đổi ID '{old}' → '{item.name}'")
            self._sync_design()

    def _on_layers_changed(self):
        """Thêm / nhân bản / xoá thành phần -> ghi lại thiết kế nếu đã có màn hình."""
        if self.scene.bulk:
            return
        ids = self._screen_ids()
        if ids == self._last_ids:
            return   # chỉ đổi thứ tự / xoay / ẩn-hiện: ID không đổi
        self._sync_design()

    # ---------------------------------------------------------------- thêm/xoá
    def _add_component(self, token: str):
        """Bấm trong palette → thêm thành phần (hoặc ảnh) vào chỗ trống gần giữa."""
        if is_audio_token(token):
            # âm thanh không phải thành phần UI: in tham chiếu Lua ra Console
            entry = audio_entry(audio_key(token)) or {}
            self.logMessage.emit(
                f"[UI DESIGNER] Âm thanh '{entry.get('title', '')}' — tham chiếu Lua:\n"
                f"    engine.audio_play(\"{entry.get('src', '')}\")")
            return
        item = self.scene.add_token_centered(token)
        self.view.setFocus()
        self.logMessage.emit(
            f"[UI DESIGNER] Đã thêm {item.widget_type} tại "
            f"({round(item.pos().x())}, {round(item.pos().y())})")

    def add_sprite(self, key: str):
        """Nhận sprite vừa vẽ ở Sprite Editor: đưa vào palette + đặt lên canvas."""
        self.palette.add_sprite(key)
        item = self.scene.add_sprite_centered(key)
        self.view.setFocus()
        self._refresh_breadcrumb()
        self.logMessage.emit(
            f"[UI DESIGNER] Đã thêm sprite '{key}' vào thành phần "
            f"({round(item.rect().width())}×{round(item.rect().height())})")
        return item

    def add_asset(self, key: str, place: bool = False):
        """Nhận ảnh vừa nhập từ ngoài: thêm vào palette (và tuỳ chọn đặt lên canvas)."""
        self.palette.refresh_assets(focus=image_token(key))
        if not place:
            return None
        return self.scene.add_token_centered(image_token(key))

    # ---------------------------------------------------------------- màn hình UI
    def refresh_screens(self):
        """Nạp danh sách màn hình của project vào thanh MÀN HÌNH."""
        self.screen_bar.set_project(self.store.root, self.store.screen_ids(),
                                    self.current_screen)

    def _refresh_breadcrumb(self):
        if self.current_screen is None:
            self.title_label.setText("  Màn hình mới (chưa lưu)")
            return
        root = self.store.root
        location = f"{UI_DIR}/{DESIGN_FILENAME}" if root is not None else ""
        self.title_label.setText(f"  {self.current_screen}   ·   {location}")

    def _taken_names(self, exclude: str | None = None) -> set[str]:
        return {sid for sid in self.store.screen_ids()
                if exclude is None or sid != exclude}

    def _ask_screen_name(self, title: str, message: str, initial: str,
                         exclude: str | None = None,
                         ok_text: str = "Tạo màn hình") -> str:
        dialog = ScreenNameDialog(title, message, initial,
                                  self._taken_names(exclude), self.window(),
                                  ok_text=ok_text)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return ""
        return dialog.result_name

    def _require_project(self) -> bool:
        if self.store.root is None or not self.store.root.is_dir():
            QMessageBox.information(
                self, "Chưa mở project",
                "Hãy mở một project trước — thiết kế và tài nguyên đều phải "
                "được lưu trong project đó.")
            return False
        return True

    def _load_screen(self, screen_id: str):
        """Nạp một màn hình từ store lên canvas."""
        items = self.store.screen_items(screen_id)
        items_to_scene(items, self.scene)
        self.current_screen = screen_id
        self.store.set_current(screen_id)
        self.scene.clearSelection()
        self._last_ids = self._screen_ids()
        self._refresh_breadcrumb()
        self._mark_clean()

    def _open_screen(self, screen_id: str, flush: bool = True):
        if flush:
            self.save_design(silent=True)
        self._load_screen(screen_id)
        self.refresh_screens()
        self.logMessage.emit(f"[UI DESIGNER] Đã mở màn hình '{screen_id}'")

    def create_screen(self):
        """Nút [+] — tạo màn hình mới trong `ui_design.json` của project."""
        if not self._require_project():
            return
        name = self._ask_screen_name(
            "Tạo màn hình mới",
            f"Màn hình được lưu trong {UI_DIR}/{DESIGN_FILENAME} cùng các màn "
            "hình khác của project. Màn hình khởi động luôn là main — không "
            "đổi tên được.",
            "screen")
        if not name:
            return
        if name.lower() == MAIN_SCREEN_ID:
            self.logMessage.emit(
                f"[UI DESIGNER] '{MAIN_SCREEN_ID}' là màn hình khởi động — "
                "hãy chọn tên khác.")
            return
        if self.store.has_screen(name):
            self.logMessage.emit(f"[UI DESIGNER] Màn hình '{name}' đã tồn tại.")
            return
        # lưu màn hình đang vẽ TRƯỚC khi thêm màn hình mới
        self.save_design(silent=True)
        self.store.add_screen(name)
        if not self.store.save():
            self.logMessage.emit(f"[UI DESIGNER] {self.store.error}")
            return
        self.logMessage.emit(f"[UI DESIGNER] Đã tạo màn hình '{name}'")
        self.screensChanged.emit()
        self._open_screen(name, flush=False)

    def rename_screen(self):
        """Đổi tên màn hình đang mở."""
        if self.current_screen is None:
            self.logMessage.emit("[UI DESIGNER] Chưa có màn hình nào để đổi tên.")
            return
        if self.current_screen == MAIN_SCREEN_ID:
            self.logMessage.emit(
                f"[UI DESIGNER] Màn hình '{MAIN_SCREEN_ID}' là màn hình khởi "
                "động — không thể đổi tên.")
            return
        old_id = self.current_screen
        name = self._ask_screen_name(
            "Đổi tên màn hình",
            "ID thành phần không đổi — chỉ tên màn hình trong thiết kế được "
            "cập nhật. Màn hình main không đổi tên được.",
            old_id, exclude=old_id, ok_text="Đổi tên")
        if not name or name == old_id:
            return
        if name.lower() == MAIN_SCREEN_ID:
            self.logMessage.emit(
                f"[UI DESIGNER] Không thể đổi tên thành '{MAIN_SCREEN_ID}'.")
            return
        self.save_design(silent=True)
        if not self.store.rename_screen(old_id, name):
            self.logMessage.emit(
                f"[UI DESIGNER] Không đổi tên được '{old_id}' → '{name}'.")
            return
        if not self.store.save():
            self.logMessage.emit(f"[UI DESIGNER] {self.store.error}")
            return
        self.current_screen = name
        self._refresh_breadcrumb()
        self.refresh_screens()
        self.logMessage.emit(
            f"[UI DESIGNER] Đổi tên màn hình '{old_id}' → '{name}'")
        self.screensChanged.emit()

    def duplicate_screen(self):
        """Nhân bản màn hình đang mở thành một màn hình mới."""
        if self.current_screen is None:
            self.logMessage.emit("[UI DESIGNER] Chưa có màn hình nào để nhân bản.")
            return
        old_id = self.current_screen
        initial = self.store.unique_id(f"{old_id}_copy")
        name = self._ask_screen_name(
            "Nhân bản màn hình",
            "Bản sao chứa toàn bộ thành phần của màn hình gốc, để bạn chỉnh "
            "tiếp mà không đụng bản gốc.",
            initial, ok_text="Nhân bản")
        if not name:
            return
        if self.store.has_screen(name):
            self.logMessage.emit(f"[UI DESIGNER] Màn hình '{name}' đã tồn tại.")
            return
        # ghi canvas hiện tại xuống store trước khi chép, để bản sao có cả
        # những thay đổi chưa lưu của màn hình gốc
        self.save_design(silent=True)
        if not self.store.duplicate_screen(old_id, name):
            self.logMessage.emit("[UI DESIGNER] Không nhân bản được màn hình.")
            return
        if not self.store.save():
            self.logMessage.emit(f"[UI DESIGNER] {self.store.error}")
            return
        self.logMessage.emit(f"[UI DESIGNER] Đã nhân bản '{old_id}' → '{name}'")
        self.screensChanged.emit()
        self._open_screen(name, flush=False)

    def delete_screen(self):
        """Xoá màn hình đang mở khỏi project (có xác nhận)."""
        if self.current_screen is None:
            self.logMessage.emit("[UI DESIGNER] Chưa có màn hình nào để xoá.")
            return
        if self.current_screen == MAIN_SCREEN_ID:
            self.logMessage.emit(
                f"[UI DESIGNER] Màn hình '{MAIN_SCREEN_ID}' là màn hình khởi "
                "động — không thể xoá.")
            return
        screen_id = self.current_screen
        if not confirm_dialog(
                self.window(), "Xoá màn hình",
                f"Xoá màn hình '{screen_id}' khỏi project?\n\n"
                "Thao tác này không hoàn tác được. Các màn hình khác không bị "
                "ảnh hưởng.", "Xoá"):
            return
        # phát TRƯỚC khi sửa để MainWindow kịp sao lưu lúc dữ liệu còn nguyên
        self.screensChanged.emit()
        if not self.store.delete_screen(screen_id):
            self.logMessage.emit(f"[UI DESIGNER] Không xoá được '{screen_id}'.")
            return
        self.store.save()
        self.current_screen = None
        self.scene.clear_widgets()
        self._last_ids = []
        self._mark_clean()
        self._refresh_breadcrumb()
        self.refresh_screens()
        self.logMessage.emit(f"[UI DESIGNER] Đã xoá màn hình '{screen_id}'")
        self.screensChanged.emit()

    def reveal_design(self):
        """Mở thư mục `.luas30` của project bằng trình quản lý tệp."""
        if self.store.root is None:
            self.logMessage.emit("[UI DESIGNER] Chưa mở project.")
            return
        folder = self.store.root / UI_DIR
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        self.logMessage.emit(f"[UI DESIGNER] Mở thư mục thiết kế {folder}")

    def _on_screen_selected(self, screen_id):
        """Combo màn hình đổi lựa chọn -> mở màn hình đó lên canvas."""
        screen_id = str(screen_id)
        if self.current_screen == screen_id:
            return
        self._open_screen(screen_id)

    def new_screen(self):
        """Canvas trắng cho màn hình mới (chưa lưu)."""
        self.save_design(silent=True)
        self.scene.clear_widgets()
        self.current_screen = None
        self._last_ids = []
        self._mark_clean()
        self._refresh_breadcrumb()
        self.refresh_screens()

    def open_screen(self, screen_id: Optional[str] = None):
        """Mở màn hình theo id; không truyền thì hỏi chọn trong danh sách."""
        if screen_id is None:
            screen_id = self.screen_bar.current_id()
        if not screen_id:
            self.logMessage.emit(
                "[UI DESIGNER] Chưa có màn hình nào để mở — bấm + để tạo mới.")
            return
        if not self.store.has_screen(screen_id):
            self.logMessage.emit(f"[UI DESIGNER] Không có màn hình '{screen_id}'.")
            return
        self._open_screen(screen_id)

    # ---------------------------------------------------------------- project
    def set_project(self, root):
        """Ghi nhớ project, bảo đảm màn hình main tồn tại, quét tài nguyên.

        MainWindow gọi hàm này HAI lần khi mở tab (một lần trong factory, một
        lần sau khi tab đã có). Nếu project không đổi thì chỉ làm mới danh sách
        màn hình + tài nguyên — nạp lại từ đĩa ở lần gọi thứ hai sẽ nuốt mất
        thao tác người dùng vừa làm trên canvas.
        """
        new_root = Path(root).resolve() if root else None
        if new_root is not None and new_root == self.store.root:
            self.sync_project_assets()
            self.refresh_screens()
            return

        self.store.set_project(new_root)
        if self.store.error:
            self.logMessage.emit(f"[UI DESIGNER] {self.store.error}")
        self.current_screen = None
        self.scene.clear_widgets()
        self._last_ids = []
        self._mark_clean()

        if self.store.root is None:
            self._refresh_breadcrumb()
            self.refresh_screens()
            return

        self.store.ensure_main()
        self.sync_project_assets()
        # mở đúng màn hình đã mở lần trước (khoá "current" trong tệp thiết kế)
        screen_id = self.store.current_id()
        if self.store.has_screen(screen_id):
            self._load_screen(screen_id)
        self.refresh_screens()

    def sync_project_assets(self):
        """Quét assets/ của project -> đăng ký ảnh & âm thanh vào palette."""
        if self.store.root is None or not self.store.root.is_dir():
            return 0
        added = 0
        for info in scan_project_images(self.store.root):
            rel = info["rel"]
            if image_for_src(rel) is not None:
                continue
            image = load_image(info["path"])
            if image is None:
                continue
            register_asset(rel, rel.rsplit("/", 1)[-1], image, rel,
                           rel.rsplit("/", 1)[0] if "/" in rel else "assets")
            added += 1
        for info in scan_project_audio(self.store.root):
            rel = info["rel"]
            if audio_entry(rel) is not None:
                continue
            register_audio(rel, rel.rsplit("/", 1)[-1], rel, info["size"])
            added += 1
        self.palette.refresh_assets()
        return added

    # ---------------------------------------------------------------- nhập tài nguyên
    def _run_import(self, kind: str):
        """Mở hộp thoại nhập, copy tệp vào đúng thư mục rồi đăng ký vào palette."""
        from .import_dialog import ImportAssetDialog

        dialog = ImportAssetDialog(self.window(), project_root=self.store.root,
                                   kind=kind)
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.imported:
            return []

        keys = []
        for info in dialog.imported:
            rel = info["rel"]
            if kind == KIND_IMAGE:
                image = load_image(info["dest"])
                register_asset(rel, rel.rsplit("/", 1)[-1], image, rel,
                               rel.rsplit("/", 1)[0] if "/" in rel else "assets")
            else:
                register_audio(rel, rel.rsplit("/", 1)[-1], rel, info["size"])
            keys.append(rel)
            self.logMessage.emit(f"[UI DESIGNER] Đã nhập {rel}")

        last = keys[-1]
        focus = image_token(last) if kind == KIND_IMAGE else audio_token(last)
        self.palette.refresh_assets(focus=focus)
        self.assetsImported.emit()

        # ảnh: đặt luôn một bản lên canvas cho thấy kết quả ngay
        if kind == KIND_IMAGE:
            item = self.scene.add_token_centered(image_token(last))
            self.view.setFocus()
            self._refresh_breadcrumb()
            self.logMessage.emit(
                f"[UI DESIGNER] Đã đặt '{last.rsplit('/', 1)[-1]}' lên canvas "
                f"({round(item.rect().width())}×{round(item.rect().height())})")
        else:
            self.logMessage.emit(
                f"[UI DESIGNER] Đã thêm {len(keys)} tệp âm thanh vào nhóm ÂM THANH")
        return keys

    def import_images(self):
        """Nhập ảnh ngoài vào assets/ của project."""
        if self._require_project():
            self._run_import(KIND_IMAGE)

    def import_audio(self):
        """Nhập âm thanh ngoài vào assets/sfx hoặc assets/music."""
        if self._require_project():
            self._run_import(KIND_AUDIO)

    def place_project_image(self, path) -> bool:
        """Hộp thoại TÀI NGUYÊN chọn ảnh → đăng ký nếu thiếu rồi đặt vào canvas.

        Trả False khi tệp không phải ảnh trong project (icon chưa tải, pdf,
        nhạc…) — người gọi chịu trách nhiệm báo cho người dùng biết.
        """
        if self.store.root is None or not self.store.root.is_dir():
            return False
        try:
            rel = Path(path).resolve().relative_to(
                self.store.root.resolve()).as_posix()
        except (OSError, ValueError):
            return False
        if image_for_src(rel) is None:
            self.sync_project_assets()
        entry = image_for_src(rel)
        if entry is None:
            return False
        self.scene.add_token_centered(image_token(entry["key"]))
        self.view.setFocus()
        self._refresh_breadcrumb()
        self.logMessage.emit(
            f"[UI DESIGNER] Đã đặt '{entry['title']}' lên canvas")
        return True

    def _on_widget_added(self, _item):
        """Kéo-thả xong: cập nhật breadcrumb để người dùng biết màn hình đã đổi."""
        self._refresh_breadcrumb()

    # ---------------------------------------------------------------- zoom / snapping
    def _zoom_in(self):
        self.view.zoom_in()

    def _zoom_out(self):
        self.view.zoom_out()

    def _zoom_fit(self):
        self.view.reset_zoom()

    def _toggle_snapping(self, enabled: bool):
        """Bật/tắt hít dính căn chỉnh; tắt thì xoá luôn đường dóng đang hiện."""
        self.scene.snapping = bool(enabled)
        self.scene.clear_guides()
        self.snap_action.setIcon(
            icons.icon_magnet("palette.ACCENT" if enabled else "palette.TEXT_5"))
        self.logMessage.emit(
            f"[UI DESIGNER] Hít dính căn chỉnh: {'BẬT' if enabled else 'TẮT'}")

    # ---------------------------------------------------------------- xuất
    def export_lua(self):
        """Ghi `.luas30/ui_design.json` rồi sinh `ui_design.lua` cho game."""
        if not self._require_project():
            return
        if not self.save_design(silent=True):
            return
        target = export_lua(self.store)
        if target is None:
            self.logMessage.emit(f"[UI DESIGNER] {self.store.error}")
            return
        self._refresh_breadcrumb()
        self.refresh_screens()
        self.designSaved.emit(target)
        self.logMessage.emit(
            f"[UI DESIGNER] Đã lưu {UI_DIR}/{DESIGN_FILENAME} và sinh "
            f"{relative_to_project(self.store.root, target)}")
