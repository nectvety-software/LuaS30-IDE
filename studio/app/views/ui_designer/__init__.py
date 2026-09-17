"""
ui_designer — UI Designer đầy đủ của LuaS30 Studio.

Port từ `D:/MRE/lua-engine/app/ui/ui_designer/` (bản NokiaLua/2Dutiful) sang
quy ước của LuaS30 Studio:

    canvas.py            scene + khung điện thoại 240x320, hít dính, zoom, kéo thả
    items.py             catalog thành phần + cách vẽ từng loại
    guides.py            thuật toán đường dóng căn chỉnh
    widgets_palette.py   palette kéo thả + tìm kiếm
    layers_panel.py      bảng LAYERS (thứ tự lớp, đổi ID, nhân bản, xoay)
    properties_panel.py  INSPECTOR (vị trí, kích thước, màu, chữ)
    screen_bar.py        thanh đa màn hình (chọn / tạo / đổi tên / nhân bản / xoá)
    designer_view.py     ghép tất cả thành widget hoàn chỉnh

    design_store.py      lưu `.luas30/ui_design.json`   <- thay lua_export.py gốc
    lua_export.py        sinh `ui_design.lua` cho game
    asset_import.py      copy ảnh/âm thanh vào assets/ của project
    import_dialog.py     hộp thoại nhập tài nguyên

    tokens.py            design token khớp bảng màu Studio (thay theme.py gốc)
    icons_compat.py      adapter icon glyph (thay icons Lucide của gốc)
    modal.py             hộp thoại modal dùng chung
    color_button.py      ô chọn màu cho INSPECTOR

Điểm vào là `UIDesignerWidget` (xem `designer_view.py`).
"""

from .designer_view import UIDesignerWidget

# Tên cũ mà `app/ui/main_window.py` đang import.
UIDesignerView = UIDesignerWidget

__all__ = ["UIDesignerWidget", "UIDesignerView"]
