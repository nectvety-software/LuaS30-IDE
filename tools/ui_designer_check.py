#!/usr/bin/env python3
"""
ui_designer_check.py — Kiểm thử UI Designer của LuaS30 Studio, không cần màn hình.

Chạy:

    set QT_QPA_PLATFORM=offscreen
    set QT_QPA_FONTDIR=C:\\Windows\\Fonts
    py -3.12 studio\\..\\tools\\ui_designer_check.py            # chỉ kiểm tra
    py -3.12 tools\\ui_designer_check.py --shots <thư mục>      # + xuất ảnh PNG

`QT_QPA_FONTDIR` là BẮT BUỘC: thiếu nó, nền offscreen của Qt nạp 0 font, mọi
glyph thành ô vuông, mà ảnh vẫn lưu được nên lỗi xảy ra âm thầm.

Script dựng project tạm trong %TEMP%, chạy hết các luồng của designer rồi dọn
sạch. Nó KHÔNG chạm vào project thật của người dùng.

Phần kiểm tra gồm:
  1. tạo project -> sinh `.luas30/ui_design.json`
  2. thêm thành phần, đổi ID -> đồng bộ ngay xuống tệp
  3. nhập tài nguyên (ảnh) -> copy vào assets/ và đặt lên canvas
  4. tạo / đổi tên / nhân bản / xoá màn hình (main bị khoá)
  5. xuất `ui_design.lua` và kiểm tra cú pháp bằng luac nếu tìm thấy
  6. migrate tệp v1 và chịu được tệp JSON hỏng / item rác
  7. (tuỳ chọn) render ảnh widget + dialog để soi bố cục
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "studio"
sys.path.insert(0, str(STUDIO))

# luac đi kèm toolchain của engine, nếu có — dùng để kiểm cú pháp tệp sinh ra
LUAC_CANDIDATES = [
    ROOT / "toolchain" / "luac" / "luac.exe",
    ROOT / "tools" / "luac" / "luac.exe",
    Path("D:/MRE/lua-engine/mre-core/luac/luac.exe"),
]

FAILS: list[str] = []


def check(label: str, cond: bool, extra: str = "") -> bool:
    if not cond:
        FAILS.append(label)
    print(f"  [{'OK  ' if cond else 'FAIL'}] {label} {extra}", flush=True)
    return bool(cond)


def make_project(tag: str) -> Path:
    project = Path(tempfile.mkdtemp(prefix=f"luas30_check_{tag}_"))
    for rel in ("src", "assets"):
        (project / rel).mkdir(parents=True, exist_ok=True)
    (project / "project.json").write_text('{"name": "check"}\n', encoding="utf-8")
    return project


def make_image(path: Path, color: int = 0xFF2E7D32) -> None:
    from PySide6.QtGui import QImage

    image = QImage(12, 12, QImage.Format_RGB32)
    image.fill(color)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(path))


# ---------------------------------------------------------------- kiểm tra luồng

def run_flows(view_cls, design_path, export_path, ui_dir, filename) -> Path:
    from PySide6.QtWidgets import QDialog

    import app.views.ui_designer.designer_view as dv
    import app.views.ui_designer.import_dialog as import_dialog_mod

    print("\n-- 1. project mới --", flush=True)
    project = make_project("main")
    view = view_cls()
    view.set_project(project)
    check("sinh .luas30/ui_design.json", design_path(project).is_file())
    check("có màn hình main", view.store.screen_ids() == ["main"],
          str(view.store.screen_ids()))

    print("\n-- 2. thêm thành phần + đồng bộ ID --", flush=True)
    for token in ("button", "label", "card", "progress"):
        view._add_component(token)
    ids = view._screen_ids()
    check("thêm đủ 4 thành phần", len(ids) == 4, str(ids))
    on_disk = json.loads(design_path(project).read_text(encoding="utf-8"))
    check("ghi ngay xuống đĩa khi ID đổi",
          len(on_disk["screens"][0]["items"]) == 4,
          str(len(on_disk["screens"][0]["items"])))
    target = sorted(view.scene.widget_items(), key=lambda it: it.zValue())[0]
    view._on_id_edited(target, "btn_start")
    check("đổi ID thành công", "btn_start" in view._screen_ids(),
          str(view._screen_ids()))

    print("\n-- 3. nhập tài nguyên --", flush=True)
    source = Path(tempfile.mkdtemp(prefix="luas30_check_src_")) / "menu_button.png"
    make_image(source)

    class FakeImportDialog:
        def __init__(self, parent=None, project_root=None, kind="image"):
            from app.views.ui_designer.asset_import import import_files

            self.imported = import_files(project_root, [source], "ui")

        def exec(self):
            return QDialog.DialogCode.Accepted

    real = import_dialog_mod.ImportAssetDialog
    import_dialog_mod.ImportAssetDialog = FakeImportDialog
    try:
        keys = view._run_import("image")
    finally:
        import_dialog_mod.ImportAssetDialog = real
    check("copy ảnh vào assets/ui",
          (project / "assets" / "ui" / "menu_button.png").is_file())
    check("trả về đường dẫn tương đối", keys == ["assets/ui/menu_button.png"],
          str(keys))

    print("\n-- 4. CRUD màn hình --", flush=True)
    view._ask_screen_name = lambda *a, **k: "menu"
    view.create_screen()
    check("tạo màn hình menu", view.store.screen_ids() == ["main", "menu"],
          str(view.store.screen_ids()))
    view._add_component("card")
    before_rename = view._screen_ids()
    view._ask_screen_name = lambda *a, **k: "menu_main"
    view.rename_screen()
    check("đổi tên màn hình", view.store.screen_ids() == ["main", "menu_main"],
          str(view.store.screen_ids()))
    check("thành phần giữ nguyên sau đổi tên", view._screen_ids() == before_rename,
          f"{before_rename} -> {view._screen_ids()}")
    view._ask_screen_name = lambda *a, **k: "menu_copy"
    view.duplicate_screen()
    check("nhân bản màn hình",
          "menu_copy" in view.store.screen_ids(), str(view.store.screen_ids()))
    view._open_screen("main")
    view.delete_screen()
    check("KHÔNG xoá được main", "main" in view.store.screen_ids())
    view._open_screen("menu_copy")
    real_confirm = dv.confirm_dialog
    dv.confirm_dialog = lambda *a, **k: True
    try:
        view.delete_screen()
    finally:
        dv.confirm_dialog = real_confirm
    check("xoá được màn hình phụ", "menu_copy" not in view.store.screen_ids(),
          str(view.store.screen_ids()))

    print("\n-- 5. xuất Lua --", flush=True)
    view.export_lua()
    lua = export_path(project)
    check("sinh ui_design.lua", lua.is_file())
    text = lua.read_text(encoding="utf-8") if lua.is_file() else ""
    for needle in ("function M.draw", "function M.hit", "function M.get",
                   '["main"]', '["menu_main"]'):
        check(f"lua chứa {needle}", needle in text)
    luac = next((p for p in LUAC_CANDIDATES if p.is_file()), None)
    if luac is None:
        print("  [SKIP] không tìm thấy luac để kiểm cú pháp", flush=True)
    else:
        proc = subprocess.run([str(luac), "-p", str(lua)],
                              capture_output=True, text=True)
        check(f"luac chấp nhận ui_design.lua ({luac.parent.name})",
              proc.returncode == 0, (proc.stderr or "").strip())

    print("\n-- 6. tương thích ngược & tệp hỏng --", flush=True)
    old = make_project("v1")
    (old / ui_dir).mkdir(parents=True, exist_ok=True)
    (old / ui_dir / filename).write_text(json.dumps({
        "version": 1,
        "canvas": [240, 320],
        "items": [
            {"type": "button", "text": "OK", "x": 10, "y": 20, "w": 60, "h": 24},
            {"type": "label", "text": "Hi", "x": 10, "y": 60, "w": 60, "h": 18},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    legacy = view_cls()
    legacy.set_project(old)
    check("v1 -> màn hình main", legacy.store.screen_ids() == ["main"])
    check("v1 -> nạp đủ thành phần", len(legacy._screen_ids()) == 2,
          str(legacy._screen_ids()))
    legacy.export_lua()
    upgraded = json.loads(design_path(old).read_text(encoding="utf-8"))
    check("v1 được nâng lên version 2", upgraded.get("version") == 2)
    check("v1 giữ nội dung chữ",
          upgraded["screens"][0]["items"][0].get("text") == "OK")

    broken = make_project("broken")
    (broken / ui_dir).mkdir(parents=True, exist_ok=True)
    (broken / ui_dir / filename).write_text("{ not json", encoding="utf-8")
    view_broken = view_cls()
    view_broken.set_project(broken)
    check("JSON hỏng không làm sập view",
          view_broken.store.screen_ids() == ["main"])
    check("có báo lỗi đọc tệp", bool(view_broken.store.error),
          repr(view_broken.store.error))

    (broken / ui_dir / filename).write_text(json.dumps({
        "version": 2,
        "screens": [{"id": "main", "items": [
            {"x": 1}, "rác", {"type": "button", "x": 5, "y": 5}]},
            "không phải dict"],
    }, ensure_ascii=False), encoding="utf-8")
    view_dirty = view_cls()
    view_dirty.set_project(broken)
    ids_dirty = view_dirty._screen_ids()
    check("bỏ qua item rác", len(ids_dirty) == 1, str(ids_dirty))
    check("item thiếu name tự sinh ID theo loại",
          bool(ids_dirty) and ids_dirty[0].startswith("button_"), str(ids_dirty))

    print("\n-- 6b. ảnh AI tạo: nạp từ đĩa khi registry trống --", flush=True)
    from app.views.ui_designer import items as items_mod
    from app.views.ui_designer.items import DesignerItem, clear_images

    # DesignerItem.from_dict phải tự nạp bitmap từ gốc project khi `src` trỏ tới
    # tệp có thật nhưng CHƯA có trong registry — chính là lỗi "AI tạo ảnh xong
    # UI Designer chỉ vẽ placeholder núi".
    aip = make_project("ai_img")
    make_image(aip / "assets" / "sprites" / "photo_hero.png", 0xFFE0567A)
    (aip / ui_dir).mkdir(parents=True, exist_ok=True)
    (aip / ui_dir / filename).write_text(json.dumps({
        "version": 2, "canvas": [240, 320], "current": "main",
        "screens": [{"id": "main", "items": [
            {"type": "image", "name": "photo_hero", "x": 40, "y": 40,
             "w": 56, "h": 56, "src": "assets/sprites/photo_hero.png"}]}],
    }, ensure_ascii=False), encoding="utf-8")
    clear_images()
    raw = {"type": "image", "name": "photo_hero", "x": 40, "y": 40, "w": 56,
           "h": 56, "src": "assets/sprites/photo_hero.png"}
    it = DesignerItem.from_dict(raw, base_dir=aip)
    check("from_dict nạp ảnh từ đĩa khi registry trống",
          it.image is not None and not it.image.isNull())
    check("ảnh nạp xong được đăng ký để dùng chung",
          items_mod.image_for_src(raw["src"]) is not None)

    # Luồng thật: designer mở project (chưa có ảnh) -> AI ghi asset + thiết kế
    # -> sync + reload_current_screen phải dựng lại canvas với bitmap thật.
    clear_images()
    live = view_cls()
    live.set_project(aip)          # registry + canvas đã nạp ảnh
    live_img = next((i for i in live.scene.widget_items()
                     if i.widget_type == "image"), None)
    check("mở project: ảnh AI hiển thị trên canvas",
          live_img is not None and live_img.image is not None
          and not live_img.image.isNull())

    return project


# ---------------------------------------------------------------- ảnh render

def run_shots(view_cls, out_dir: Path) -> None:
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QToolBar

    print("\n-- 7. render ảnh --", flush=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    project = make_project("shot")
    make_image(project / "assets" / "ui" / "btn.png", 0xFF3A6EA5)

    view = view_cls()
    view.set_project(project)
    for token in ("button", "label", "checkbox", "textbox", "progress", "slider",
                  "switch", "panel", "card", "row", "divider", "canvas", "rect",
                  "image"):
        view._add_component(token)
    positions = [(8, 8), (8, 40), (8, 64), (8, 92), (8, 124), (8, 140), (8, 164),
                 (8, 190), (100, 8), (8, 220), (8, 240), (100, 220), (8, 260),
                 (140, 8)]
    items = sorted(view.scene.widget_items(), key=lambda it: it.zValue())
    for item, (x, y) in zip(items, positions):
        item.setPos(x, y)
    view.scene.clearSelection()
    view.resize(1400, 800)
    view.show()
    view.ensurePolished()

    shot = out_dir / "designer.png"
    view.grab().save(str(shot))
    print("  saved", shot, flush=True)

    check("palette rộng 212", view.palette.width() == 212,
          f"w={view.palette.width()}")
    check("layers rộng 212", view.layers.width() == 212,
          f"w={view.layers.width()}")
    check("canvas còn chỗ (>=240px)", view.view.width() >= 240,
          f"w={view.view.width()}")
    check("layers không tràn ra ngoài",
          view.layers.geometry().right() <= view.width(),
          f"right={view.layers.geometry().right()} w={view.width()}")
    toolbar = view.findChild(QToolBar, "DesignerToolbar")
    check("toolbar có >= 9 nút", toolbar is not None and len(toolbar.actions()) >= 9,
          f"n={len(toolbar.actions()) if toolbar else 0}")

    # quét khối sáng (rò theme sáng vào UI tối), bỏ qua vùng canvas vì thành phần
    # progress/slider/switch vẽ knob TRẮNG một cách hợp lệ
    canvas_rect = QRect(view.view.mapTo(view, QPoint(0, 0)), view.view.size())
    hits = []
    pixmap = view.grab()
    image = pixmap.toImage()
    block = 24
    for by in range(0, pixmap.height(), block):
        for bx in range(0, pixmap.width(), block):
            if canvas_rect.intersects(QRect(bx, by, block, block)):
                continue
            values = []
            for y in range(by, min(by + block, pixmap.height()), 4):
                for x in range(bx, min(bx + block, pixmap.width()), 4):
                    c = image.pixelColor(x, y)
                    values.append(0.299 * c.red() + 0.587 * c.green()
                                  + 0.114 * c.blue())
            if values and sum(values) / len(values) > 150 and min(values) > 140:
                hits.append((bx, by))
    check("không có khối sáng ở phần chrome", not hits, f"hits={hits[:6]}")

    from app.views.ui_designer.import_dialog import ImportAssetDialog
    from app.views.ui_designer.modal import ModalDialog
    from app.views.ui_designer.screen_bar import ScreenNameDialog

    dialogs = [
        ("dialog_screen_name.png",
         ScreenNameDialog("Tạo màn hình mới",
                          "Màn hình được lưu trong .luas30/ui_design.json.",
                          "menu", {"main"}, view, ok_text="Tạo màn hình")),
        ("dialog_import.png",
         ImportAssetDialog(view, project_root=project, kind="image",
                           initial_files=[project / "assets" / "ui" / "btn.png"])),
        ("dialog_confirm.png",
         ModalDialog("Xoá màn hình", "Xoá màn hình 'menu' khỏi project?", view,
                     width=440)),
    ]
    for name, dialog in dialogs:
        dialog.resize(560, 560)
        dialog.show()
        path = out_dir / name
        dialog.grab().save(str(path))
        print("  saved", path, flush=True)
        dialog.close()


# ---------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shots", metavar="THƯ_MỤC",
                        help="xuất ảnh render vào thư mục này")
    parser.add_argument("--keep", action="store_true",
                        help="giữ lại project tạm để xem tay")
    args = parser.parse_args()

    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication

    from app.ui.theme import APP_STYLE
    from app.views.ui_designer import UIDesignerWidget
    from app.views.ui_designer.design_store import (
        DESIGN_FILENAME, UI_DIR, design_path,
    )
    from app.views.ui_designer.lua_export import export_path

    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)

    families = len(QFontDatabase.families())
    print(f"LuaS30 UI Designer — kiểm thử offscreen (font: {families} họ)")
    if families == 0:
        print("  !! QT_QPA_FONTDIR chưa đặt — glyph sẽ là ô vuông")

    projects = []
    try:
        projects.append(run_flows(UIDesignerWidget, design_path, export_path,
                                  UI_DIR, DESIGN_FILENAME))
        if args.shots:
            run_shots(UIDesignerWidget, Path(args.shots))
    finally:
        if not args.keep:
            for project in projects:
                shutil.rmtree(project, ignore_errors=True)
        else:
            print("\nproject tạm:", *projects, sep="\n  ", flush=True)

    print("\n== KẾT QUẢ ==", flush=True)
    print("FAIL:", FAILS or "không có", flush=True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
