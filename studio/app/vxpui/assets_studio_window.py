"""Cửa sổ "TÀI NGUYÊN · UI DESIGNER" — bố cục kiểu Photoshop, chrome VXPEngine.

UI Designer chiếm toàn cửa sổ (palette "THÀNH PHẦN" là cột trái của chính nó).
Panel TÀI NGUYÊN không còn nằm chen trong dock hai tab nữa — tab đó quá hẹp và
luôn bị che; thay vào đó là một HỘP THOẠI MODAL (CustomDialog, cùng kiểu với
hộp thoại THIẾT BỊ · VXPEMU) mở từ menu "Tài nguyên": chọn ảnh trong project
rồi bấm "Chèn vào giữa màn hình", hoặc nhập tệp mới — palette được đồng bộ ngay
để kéo-thả nhanh.  Cửa sổ đóng = ẩn (widget designer giữ nguyên bản vẽ chưa lưu).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QEvent, Qt, Signal
from PySide6.QtGui import QAction, QCursor, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QFrame,
    QMenuBar,
    QVBoxLayout,
    QWidget,
)

from app.vxpui.custom_dialog import CustomDialog
from app.vxpui.icons import icon
from app.vxpui.title_bar import CustomTitleBar
from app.vxpui.window_state_controller import WindowStateController
from app.views.assets_view import IMAGE, AssetsView
from app.views.ui_designer_view import UIDesignerView

RESIZE_MARGIN = 6


class _StudioWindowState(WindowStateController):
    """Placement state riêng — không đụng key của cửa sổ chính."""

    SETTINGS_GEOMETRY = "vxpui/assets_studio/qt_geometry"
    SETTINGS_NORMAL_GEOMETRY = "vxpui/assets_studio/normal_geometry"
    SETTINGS_MAXIMIZED = "vxpui/assets_studio/maximized"
    SETTINGS_LAST_STATE = "vxpui/assets_studio/last_state"


class _PickerAssetsView(AssetsView):
    """AssetsView trong hộp thoại chọn — mọi lần dựng lại danh sách cũng là
    lúc báo designer đăng ký tệp mới vào palette (kéo-thả được ngay)."""

    changed = Signal()

    def refresh(self) -> None:
        super().refresh()
        self.changed.emit()


class AssetsStudioWindow(QWidget):
    def __init__(self, owner: QWidget, engine_root: Path) -> None:
        super().__init__(None)
        self.owner = owner
        self.engine_root = Path(engine_root).resolve()
        self.setObjectName("AssetsStudioWindow")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1360, 820)
        self.setMinimumSize(760, 520)

        outer = QVBoxLayout(self)
        self.outer_layout = outer
        outer.setContentsMargins(RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN)
        self.root_frame = QFrame()
        self.root_frame.setObjectName("RootFrame")
        self.root_frame.setMouseTracking(True)
        outer.addWidget(self.root_frame)

        root_layout = QVBoxLayout(self.root_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self, title="TÀI NGUYÊN · UI DESIGNER")
        self.title_bar.btn_info.setVisible(False)
        self.title_bar.logo_button.setToolTip("Về cửa sổ LuaS30 IDE")
        self.window_state_controller = _StudioWindowState(
            window=self,
            title_bar=self.title_bar,
            outer_layout=self.outer_layout,
            root_frame=self.root_frame,
            normal_margin=RESIZE_MARGIN,
            parent=self,
        )
        self.title_bar.minimizeRequested.connect(self.window_state_controller.minimize)
        self.title_bar.maximizeRestoreRequested.connect(
            self.window_state_controller.toggle_maximize_restore
        )
        self.title_bar.closeRequested.connect(self.close)
        self.title_bar.homeRequested.connect(self._focus_owner)
        root_layout.addWidget(self.title_bar)
        self.title_bar.set_home_mode(False)

        # ------------------------------------------------- Photoshop-style body
        # UI Designer chiếm toàn cửa sổ; TÀI NGUYÊN là hộp thoại modal riêng
        # (giống hộp THIẾT BỊ · VXPEMU) — chọn ảnh chèn vào canvas hoặc nhập
        # tệp mới, palette đồng bộ ngay sau mỗi lần danh sách thay đổi.
        self.assets = _PickerAssetsView()
        self.designer = UIDesignerView()
        self.assets.setMinimumSize(560, 420)
        self.assets.changed.connect(self.designer.sync_project_assets)
        root_layout.addWidget(self.designer, 1)

        self.assets_dialog = CustomDialog(
            "TÀI NGUYÊN · ASSETS", self, width=700, height=680,
            resizable=True, modal=True,
        )
        self.assets_dialog.setObjectName("AssetsPickerDialog")
        self.assets_dialog.set_close_handler(self.assets_dialog.hide)
        self.assets_dialog.add_body_widget(self.assets, 1)
        insert_btn = self.assets_dialog.add_footer_button(
            "Chèn vào giữa màn hình", accent=True, icon_name="fa5s.plus")
        insert_btn.setToolTip(
            "Đặt ảnh đang chọn lên canvas của màn hình hiện tại.\n"
            "Tệp chưa đăng ký sẽ được nạp vào palette THÀNH PHẦN trước.")
        insert_btn.clicked.connect(self._insert_selected_asset)
        close_btn = self.assets_dialog.add_footer_button(
            "Đóng", ghost=True, icon_name="fa5s.times")
        close_btn.clicked.connect(self.assets_dialog.hide)

        # Menu cần AssetsView + UIDesignerView đã tồn tại ở trên.
        self.menu_bar = self._build_menu_bar()
        self.title_bar.set_menu_bar(self.menu_bar)

    # ------------------------------------------------------------- picker
    def _open_assets_dialog(self) -> None:
        self.assets_dialog.show()
        self.assets_dialog.raise_()
        self.assets_dialog.activateWindow()

    def _insert_selected_asset(self) -> None:
        path = self.assets.selected_path()
        if path is None:
            return
        if path.suffix.lower() not in IMAGE:
            self.designer.logMessage.emit(
                f"[UI DESIGNER] '{path.name}' không phải ảnh — "
                f"chỉ ảnh mới chèn vào canvas được")
            return
        if self.designer.place_project_image(path):
            self.assets_dialog.hide()
            self.raise_()
            self.activateWindow()
        else:
            self.designer.logMessage.emit(
                "[UI DESIGNER] Chưa mở project — không chèn được ảnh")

    # ------------------------------------------------------------------ menus
    def _build_menu_bar(self) -> QMenuBar:
        menu_bar = QMenuBar()
        menu_bar.setNativeMenuBar(False)
        menu_bar.setObjectName("MainMenuBar")

        def act(title: str, icon_name: str = "", shortcut: str = "") -> QAction:
            action = QAction(icon(icon_name) if icon_name else QIcon(), title, self)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            return action

        def assets_action(fn) -> "object":
            """Hành động trên panel TÀI NGUYÊN: bật hộp thoại trước rồi mới chạy."""
            def _run():
                self._open_assets_dialog()
                fn()
            return _run

        assets_menu = menu_bar.addMenu("Tài nguyên")
        picker_action = act("Chọn / quản lý tài nguyên…", "fa5s.th",
                            "Ctrl+Alt+R")
        picker_action.triggered.connect(self._open_assets_dialog)
        assets_menu.addAction(picker_action)
        assets_menu.addSeparator()
        import_action = act("Nhập asset vào assets/…", "fa5s.download")
        import_action.triggered.connect(assets_action(self.assets.add_asset))
        assets_menu.addAction(import_action)
        optimize_action = act("Tối ưu asset đang chọn", "fa5s.magic")
        optimize_action.triggered.connect(assets_action(self.assets.optimize_selected))
        assets_menu.addAction(optimize_action)
        preview_action = act("Mở xem trước / mở trong editor", "fa5s.external-link-alt")
        preview_action.triggered.connect(assets_action(self.assets.open_selected))
        assets_menu.addAction(preview_action)
        assets_menu.addSeparator()
        remove_action = act("Xoá asset đang chọn", "fa5s.trash-alt")
        remove_action.triggered.connect(assets_action(self.assets.remove_selected))
        assets_menu.addAction(remove_action)
        assets_menu.addSeparator()
        refresh_action = act("Làm mới tài nguyên", "fa5s.sync-alt", "F5")
        refresh_action.triggered.connect(assets_action(self.assets.refresh))
        assets_menu.addAction(refresh_action)

        design_menu = menu_bar.addMenu("Thiết kế")
        save_action = act("Lưu + xuất Lua", "fa5s.save", "Ctrl+S")
        save_action.triggered.connect(self._designer_save)
        design_menu.addAction(save_action)
        images_action = act("Nhập ảnh vào màn hình…", "fa5s.image")
        images_action.triggered.connect(self.designer.import_images)
        design_menu.addAction(images_action)
        audio_action = act("Nhập âm thanh…", "fa5s.music")
        audio_action.triggered.connect(self.designer.import_audio)
        design_menu.addAction(audio_action)

        window_menu = menu_bar.addMenu("Cửa sổ")
        close_action = act("Đóng cửa sổ", "fa5s.times", "Ctrl+W")
        close_action.triggered.connect(self.close)
        window_menu.addAction(close_action)
        return menu_bar

    def _designer_save(self) -> None:
        export = getattr(self.designer, "export_lua", None)
        if callable(export):
            export()

    # ------------------------------------------------------------------ focus
    def _focus_owner(self) -> None:
        self.owner.showNormal()
        self.owner.raise_()
        self.owner.activateWindow()

    # -------------------------------------------------------------- lifecycle
    def show_studio(self) -> None:
        if not self.isVisible():
            self.window_state_controller.show_window()
        else:
            self.raise_()
            self.activateWindow()

    def set_project(self, root: Path | None) -> None:
        resolved = Path(root).resolve() if root else None
        # Designer trước: assets.set_project → refresh → changed →
        # designer.sync_project_assets phải thấy đúng root hiện hành.
        self.designer.set_project(resolved)
        self.assets.set_project(resolved)
        self.title_bar.set_project_name(f"{resolved.name} • VXP UI" if resolved else "")

    def closeEvent(self, event) -> None:
        # Ẩn thay vì phá huỷ: bản vẽ chưa lưu của designer phải còn nguyên.
        event.ignore()
        self.window_state_controller.save_persisted_placement()
        self.hide()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self.window_state_controller.handle_window_state_change()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self.window_state_controller.handle_geometry_change()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.window_state_controller.handle_geometry_change()

    # ------------------------------------------------------------ edge resize
    def _edge_at(self, position: QPoint) -> str | None:
        if self.isMaximized():
            return None
        rect = self.rect()
        margin = RESIZE_MARGIN
        left = position.x() <= margin
        right = position.x() >= rect.width() - margin
        top = position.y() <= margin
        bottom = position.y() >= rect.height() - margin
        if top and left: return "top_left"
        if top and right: return "top_right"
        if bottom and left: return "bottom_left"
        if bottom and right: return "bottom_right"
        if left: return "left"
        if right: return "right"
        if top: return "top"
        if bottom: return "bottom"
        return None

    _CURSORS = {
        "left": Qt.CursorShape.SizeHorCursor,
        "right": Qt.CursorShape.SizeHorCursor,
        "top": Qt.CursorShape.SizeVerCursor,
        "bottom": Qt.CursorShape.SizeVerCursor,
        "top_left": Qt.CursorShape.SizeFDiagCursor,
        "bottom_right": Qt.CursorShape.SizeFDiagCursor,
        "top_right": Qt.CursorShape.SizeBDiagCursor,
        "bottom_left": Qt.CursorShape.SizeBDiagCursor,
    }

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._edge_at(event.position().toPoint())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._drag_start_geo = self.geometry()
                self._drag_start_pos = event.globalPosition().toPoint()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if getattr(self, "_resizing", False) and getattr(self, "_resize_edge", None):
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            geometry = self._drag_start_geo
            x, y, width, height = (
                geometry.x(), geometry.y(), geometry.width(), geometry.height()
            )
            edge = self._resize_edge
            min_width, min_height = self.minimumWidth(), self.minimumHeight()
            if "left" in edge:
                new_width = max(min_width, width - delta.x())
                x += width - new_width
                width = new_width
            if "right" in edge:
                width = max(min_width, width + delta.x())
            if "top" in edge:
                new_height = max(min_height, height - delta.y())
                y += height - new_height
                height = new_height
            if "bottom" in edge:
                height = max(min_height, height + delta.y())
            self.setGeometry(x, y, width, height)
            event.accept()
            return
        edge = self._edge_at(event.position().toPoint())
        self.setCursor(QCursor(self._CURSORS.get(edge, Qt.CursorShape.ArrowCursor)))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._resizing = False
        self._resize_edge = None
        super().mouseReleaseEvent(event)
