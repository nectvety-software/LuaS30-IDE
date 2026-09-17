#!/usr/bin/env python3
"""
validate_project_hub_ui.py — Project Hub: cây thư mục bên trái + không rò theme sáng.

Chạy:

    QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
        py -3.12 -u tools/validate_project_hub_ui.py

Dựng THẬT `MainWindow` rồi mở Project Hub, trong sandbox tạm nên không đụng
config thật của người dùng. Kiểm:

  * cây thư mục nằm BÊN TRÁI bảng và cùng một splitter; gốc cây là kho project;
  * bấm một thư mục trong cây thì bảng chọn đúng project tương ứng — kể cả khi
    bấm vào thư mục CON của project (bấm `<project>/build` phải chọn `<project>`);
  * không có khối sáng 24px và không có DẢI sáng mỏng. Dải trắng bên phải hàng
    tiêu đề bảng từng lọt qua phép quét khối, vì hàng tiêu đề chỉ cao ~29px nên
    không khối 24px nào nằm trọn trong đó;
  * vùng tiêu đề nằm SAU cột cuối phải là màu nền đậm, không phải palette mặc
    định (sáng) — đây chính là lỗi gốc.

Phép quét dùng chung `light_blocks` / `light_bands` với `studio_theme_check.py`
để chỉ có MỘT cách định nghĩa "sáng".
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "studio"))

FAILS: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label} {detail}", flush=True)
    if not ok:
        FAILS.append(label)


def main() -> int:
    sandbox = Path(tempfile.mkdtemp(prefix="luas30_hub_ui_"))
    projects = sandbox / "projects"
    os.environ["LUAS30_APPDATA"] = str(sandbox / "appdata")
    os.environ["LUAS30_PROJECTS"] = str(projects)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

    # hai project giả để cả cây lẫn bảng đều có nội dung
    for name in ("alpha", "beta"):
        root = projects / name
        (root / "assets").mkdir(parents=True)
        (root / "build").mkdir()
        (root / "project.json").write_text(
            json.dumps({"name": name, "appid": "1000"}), encoding="utf-8")
        (root / "main.lua").write_text(f"-- {name}\n", encoding="utf-8")

    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QApplication, QSplitter

    import studio_theme_check as H
    from app.ui.main_window import MainWindow
    from app.ui.theme import APP_STYLE

    print(f"config tạm: {sandbox}", flush=True)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)

    window = MainWindow(engine_root=ROOT)
    window.resize(1440, 860)
    window.show()
    window.ensurePolished()
    app.processEvents()

    view = window._open_project_storage()
    app.processEvents()

    print("\n-- A. cây thư mục bên trái --", flush=True)
    check("Project Hub có cây thư mục", hasattr(view, "tree"))
    if not hasattr(view, "tree"):
        print("\nFAIL", flush=True)
        return 1

    tree, table = view.tree, view.table
    check("cây là ProjectTree của Studio", type(tree).__name__ == "ProjectTree",
          type(tree).__name__)
    check("cây đang hiển thị", tree.isVisible())

    tree_pos = tree.mapTo(view, QPoint(0, 0))
    table_pos = table.mapTo(view, QPoint(0, 0))
    check("cây nằm BÊN TRÁI bảng",
          tree_pos.x() + tree.width() <= table_pos.x() + 2,
          f"cây {tree_pos.x()}..{tree_pos.x() + tree.width()} | bảng từ {table_pos.x()}")
    check("cây đủ rộng để đọc", tree.width() >= 180, f"w={tree.width()}")
    check("cây chiếm phần lớn chiều cao",
          tree.height() > view.height() * 0.5,
          f"h={tree.height()} vs {view.height()}")
    check("có splitter để người dùng kéo",
          len(view.findChildren(QSplitter)) == 1,
          f"n={len(view.findChildren(QSplitter))}")

    print("\n-- B. nội dung cây --", flush=True)
    check("gốc cây là kho project", tree.project_root == projects.resolve(),
          str(tree.project_root))
    rows = tree.model().rowCount(tree.rootIndex())
    names = {tree.model().index(r, 0, tree.rootIndex()).data() for r in range(rows)}
    check("cây thấy các project", {"alpha", "beta"} <= names, f"names={sorted(names)}")

    print("\n-- C. bấm trong cây thì soi sang bảng --", flush=True)
    check("bảng có đủ dòng", view.model.rowCount() == 2, f"n={view.model.rowCount()}")

    tree.reveal_path(projects / "beta")
    tree.clicked.emit(tree.currentIndex())
    app.processEvents()
    check("bấm 'beta' -> chọn đúng dòng beta",
          view.selected_path() == (projects / "beta").resolve(),
          str(view.selected_path()))

    tree.reveal_path(projects / "alpha" / "assets")
    tree.clicked.emit(tree.currentIndex())
    app.processEvents()
    check("bấm 'alpha/assets' -> vẫn chọn project alpha",
          view.selected_path() == (projects / "alpha").resolve(),
          str(view.selected_path()))

    print("\n-- D. không rò theme sáng --", flush=True)
    pixmap = window.grab()
    blocks = H.light_blocks(pixmap)
    check("không có khối sáng 24px", not blocks, f"hits={blocks[:6]}")
    bands = H.light_bands(pixmap)
    check("không có dải sáng mỏng", not bands, f"bands={bands[:4]}")

    header = table.horizontalHeader()
    total = sum(table.columnWidth(c) for c in range(table.model().columnCount()))
    image = pixmap.toImage()
    offset = header.mapTo(window, QPoint(0, 0))
    y = offset.y() + header.height() // 2
    samples = {
        image.pixelColor(x, y).name()
        for x in range(offset.x() + total + 10,
                       min(pixmap.width() - 5, offset.x() + table.width()), 40)
    }
    check("tiêu đề sau cột cuối là nền đậm",
          samples == {"#07101f"}, f"cols={samples or 'không lấy được mẫu'}")

    print("\n-- E. tiêu đề bảng dùng nền của chính QHeaderView --", flush=True)
    theme = (ROOT / "studio/app/ui/theme.py").read_text(encoding="utf-8")
    check("theme.py có rule nền QHeaderView (không chỉ ::section)",
          "QHeaderView {" in theme)

    window.close()
    print()
    if FAILS:
        print("FAIL", flush=True)
        for item in FAILS:
            print(" -", item, flush=True)
        return 1

    print("PASS: Project Hub có cây thư mục bên trái, cùng splitter với bảng")
    print("PASS: bấm thư mục trong cây chọn đúng project, kể cả thư mục con")
    print("PASS: không còn dải sáng ở vùng tiêu đề sau cột cuối")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
