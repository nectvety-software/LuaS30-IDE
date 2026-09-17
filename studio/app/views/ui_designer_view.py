"""
ui_designer_view.py — Điểm vào của tab UI Designer.

Bản đầu tiên (v1.7.0) là một designer tối giản nằm gọn trong tệp này: 5 loại
thành phần, kéo thả cơ bản, lưu `.luas30/ui_design.json`. Nay UI Designer đầy
đủ nằm trong package `app/views/ui_designer/`, nên tệp này chỉ còn là lớp mỏng
giữ nguyên API mà `app/ui/main_window.py` đang dùng:

    from app.views.ui_designer_view import UIDesignerView
    view = UIDesignerView()
    view.set_project(root)

Xem `app/views/ui_designer/__init__.py` để biết cấu trúc package.
"""

from __future__ import annotations

from app.views.ui_designer import UIDesignerWidget

# Tên cũ — MainWindow và `_refresh_project_bound_tools` đều tham chiếu tên này.
UIDesignerView = UIDesignerWidget

__all__ = ["UIDesignerView", "UIDesignerWidget"]
