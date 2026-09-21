#!/usr/bin/env python3
"""validate_about_credits.py — About phải luôn hiện bản quyền + website nhà phát hành.

Chạy (script tự đặt `offscreen`, không cần biến môi trường):

    py -3.12 -u tools/validate_about_credits.py

Vì sao cần guard này: dòng "© Qeafivels All rights reserved." và link website là
thông báo pháp lý/quảng bá. Chúng nằm trong HTML dựng bằng f-string nên có thể
biến mất **im lặng** khi ai đó sửa lại đoạn văn bản, và không có test nào khác
trong repo chạm tới hộp thoại About. Guard kiểm hai tầng:

  1. TĨNH — hằng số còn nguyên, cả tab About lẫn Credits đều nội suy chúng, màu
     link lấy từ token palette (không chép hex), và file pháp lý khớp nội dung.
  2. RENDER — dựng hộp thoại thật, khẳng định dòng bản quyền HIỆN và không bị
     elide, bấm link đi đúng tới `QDesktopServices.openUrl`, và cả 4 tab render
     không rò theme sáng.

Điểm dễ sai đã tính trước: `QLabel`/`QTextBrowser` tô thẻ `<a>` bằng
`QPalette::Link`, KHÔNG theo `color` của QSS — nên màu phải đặt ngay trong thẻ
`<a>`. Guard vì thế khẳng định màu nằm trong chính HTML của link.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "studio"))

ABOUT_SRC = ROOT / "studio" / "app" / "ui" / "about_dialog.py"
NOTICES = ROOT / "doc" / "legal" / "THIRD_PARTY_NOTICES.md"

VENDOR = "Qeafivels"
COPYRIGHT = f"© {VENDOR} All rights reserved."
WEBSITE = "https://qeafivels.com/"

FAILS: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label} {detail}", flush=True)
    if not ok:
        FAILS.append(label)


def check_source() -> None:
    print("-- A. nguồn --", flush=True)
    src = ABOUT_SRC.read_text(encoding="utf-8")

    for token in (
        f'VENDOR = "{VENDOR}"',
        'COPYRIGHT = f"© {VENDOR} All rights reserved."',
        f'WEBSITE = "{WEBSITE}"',
        "palette.ACCENT_HOVER",
        "QDesktopServices.openUrl",
        "def _legal_row",
        "def _legal_footer",
        "def _open_website",
        "def _wire_links",
        "def _link_label",
    ):
        check(f"còn hợp đồng About: {token}", token in src)

    # Một nguồn duy nhất: header dùng thẳng hằng số, tab About nội suy vào
    # f-string, tab Credits đặt dòng bản quyền ở QLabel ngoài vùng cuộn.
    check("header hiện thẳng hằng số bản quyền", "QLabel(COPYRIGHT)" in src)
    check("header dùng _link_label cho website",
          '_link_label(_link(), "AboutLink")' in src)
    check("cả 3 QTextBrowser đi qua _wire_links (không tab nào là ngoại lệ)",
          src.count("_wire_links(QTextBrowser())") == 3,
          f"n={src.count('_wire_links(QTextBrowser())')}")
    check("không chép lại chuỗi bản quyền bằng tay",
          src.count("All rights reserved") == 1,
          f"n={src.count('All rights reserved')}")

    about = src[src.find("def _about_tab"):src.find("def _environment_tab")]
    check("tab About nội suy {COPYRIGHT}", "{COPYRIGHT}" in about)
    check("tab About nội suy {_link()}", "{_link()}" in about)

    # Bài học từ lần render đầu: nhét dòng bản quyền vào ĐÁY tài liệu Credits thì
    # nó nằm dưới đáy khung cuộn — `toPlainText()` vẫn chứa nên test nội dung báo
    # xanh, nhưng người dùng không thấy. Nó phải nằm ngoài vùng cuộn.
    credits = src[src.find("def _credits_tab"):src.find("def _paths_tab")]
    check("tab Credits đặt bản quyền NGOÀI vùng cuộn",
          "_legal_footer()" in credits and "{COPYRIGHT}" not in credits)

    # Màu theo TOKEN, không theo hex chép tay (hex bằng giá trị palette vẫn là
    # hex chết: lần đổi palette sau sẽ bỏ quên chỗ này).
    hexes = re.findall(r"#[0-9a-fA-F]{6}", src)
    check("about_dialog.py không hard-code hex", not hexes, str(hexes[:4]))

    # Đặt ở dòng luật: dòng bản quyền phải nằm NGOÀI QTabWidget nên thấy ở mọi tab.
    head = src.find("root.addLayout(self._legal_row())")
    tabs = src.find("self.tabs = QTabWidget()")
    check("dòng bản quyền được thêm TRƯỚC khu tab (hiện ở mọi tab)",
          -1 < head < tabs, f"legal@{head} tabs@{tabs}")

    notices = NOTICES.read_text(encoding="utf-8")
    check("THIRD_PARTY_NOTICES.md có bản quyền", COPYRIGHT in notices)
    check("THIRD_PARTY_NOTICES.md có website", WEBSITE in notices)

    # Bản quyền + website là thông báo pháp lý, giữ ở HAI mặt phẳng có thẩm quyền:
    # trong app (About) và ở gốc repo (LICENSE). README chỉ ghi công + trỏ tới
    # LICENSE — không tuyên bố bản quyền bao trùm (khớp chủ trương "Ghi công").
    license_file = ROOT / "LICENSE"
    check("có file LICENSE ở gốc repo", license_file.is_file())
    if license_file.is_file():
        text = license_file.read_text(encoding="utf-8")
        check("LICENSE có bản quyền", COPYRIGHT in text)
        check("LICENSE có website", WEBSITE in text)
        check("LICENSE nêu rõ thành phần bên thứ ba KHÔNG thuộc phạm vi",
              "THIRD_PARTY_NOTICES.md" in text)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    check("README trỏ tới LICENSE", "](LICENSE)" in readme)
    check("README không tuyên bố bản quyền bao trùm",
          COPYRIGHT not in readme and WEBSITE not in readme)

    paths = src[src.find("def _paths_tab"):]
    check("tab Paths có dòng License (project)",
          '("License (project)"' in paths and 'self.engine_root / "LICENSE"' in paths)


def check_render() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

    from PySide6.QtCore import QPoint, QUrl, Qt
    from PySide6.QtGui import QDesktopServices, QFontDatabase
    from PySide6.QtWidgets import QApplication, QTextBrowser

    import studio_theme_check as H
    from app.ui import palette
    from app.ui.about_dialog import COPYRIGHT as C, WEBSITE as W, AboutDialog
    from app.ui.theme import APP_STYLE

    print("-- B. render offscreen --", flush=True)
    app = QApplication(sys.argv)
    # App thật (studio/main.py) nạp APP_STYLE + dark_theme.qss gộp một lần;
    # Chrome frameless của CustomDialog sống nhờ dark_theme.qss, nên validator
    # phải mô phỏng đúng cả hai lớp, nếu không sẽ soi theme ở môi trường giả.
    qss = ROOT / "studio" / "app" / "vxpui" / "resources" / "dark_theme.qss"
    app.setStyleSheet(APP_STYLE + "\n" + qss.read_text(encoding="utf-8"))

    check("nạp được font hệ thống (cần QT_QPA_FONTDIR)",
          len(QFontDatabase.families()) > 0, f"families={len(QFontDatabase.families())}")
    check("hằng số khớp nguồn tĩnh", C == COPYRIGHT and W == WEBSITE, f"{C!r} {W!r}")

    dlg = AboutDialog(ROOT)          # crash-test thứ tự dựng widget
    dlg.resize(720, 620)
    dlg.show()
    app.processEvents()

    check("nhãn bản quyền hiện và đúng chuỗi",
          dlg.copyright_label.isVisible() and dlg.copyright_label.text() == COPYRIGHT,
          repr(dlg.copyright_label.text()))
    check("nhãn bản quyền không bị elide",
          dlg.copyright_label.width() >= dlg.copyright_label.sizeHint().width(),
          f"{dlg.copyright_label.width()} vs {dlg.copyright_label.sizeHint().width()}")

    html = dlg.website_label.text()
    check("nhãn website hiện", dlg.website_label.isVisible())
    check("nhãn website có href", f'href="{WEBSITE}"' in html, html[:110])
    check("nhãn website không bị elide",
          dlg.website_label.width() >= dlg.website_label.sizeHint().width(),
          f"{dlg.website_label.width()} vs {dlg.website_label.sizeHint().width()}")
    check("màu link theo token palette", palette.ACCENT_HOVER in html,
          f"ACCENT_HOVER={palette.ACCENT_HOVER}")

    # Bấm THẬT: chặn cửa sổ mở ra ngoài, chỉ ghi lại URL.
    opened: list[str] = []
    real_open = QDesktopServices.openUrl
    QDesktopServices.openUrl = staticmethod(lambda u: opened.append(u.toString()))
    try:
        dlg.website_label.linkActivated.emit(WEBSITE)
        app.processEvents()
        check("QLabel.linkActivated -> mở website", opened == [WEBSITE], str(opened))

        opened.clear()
        browsers = dlg.findChildren(QTextBrowser)
        for b in browsers:
            b.anchorClicked.emit(QUrl(WEBSITE))
        app.processEvents()
        check("mọi QTextBrowser mở link ra ngoài",
              len(opened) == len(browsers) and all(u == WEBSITE for u in opened),
              f"{len(opened)}/{len(browsers)}")
        check("link trong tài liệu KHÔNG điều hướng nội bộ",
              all(not b.isBackwardAvailable() for b in browsers))
    finally:
        QDesktopServices.openUrl = real_open

    # Nội dung hai tab. Quan trọng: kiểm NỘI DUNG là chưa đủ — phải kiểm cả
    # người dùng có NHÌN THẤY hay không.
    dlg.tabs.setCurrentIndex(0)
    app.processEvents()
    about_page = dlg.tabs.currentWidget()
    about_browser = about_page.findChildren(QTextBrowser)[0]
    plain = about_browser.toPlainText()
    check("tab About: có dòng bản quyền", COPYRIGHT in plain)
    check("tab About: có website", WEBSITE in plain)
    check("tab About: link là <a href> thật", f'href="{WEBSITE}"' in about_browser.toHtml())
    # Nếu tài liệu dài quá khung thì dòng cuối nằm dưới đáy và phải cuộn mới thấy.
    about_scroll = about_browser.verticalScrollBar().maximum()
    check("tab About: dòng bản quyền không bị đẩy xuống dưới tầm nhìn",
          about_scroll == 0, f"scroll_max={about_scroll}")

    dlg.tabs.setCurrentIndex(2)
    app.processEvents()
    credits_browser = dlg.tabs.currentWidget().findChildren(QTextBrowser)[0]
    check("tab Credits: bản quyền KHÔNG nằm trong vùng cuộn",
          COPYRIGHT not in credits_browser.toPlainText())

    footer = dlg.credits_legal_label
    check("tab Credits: dòng bản quyền đang HIỆN", footer.isVisible())
    check("tab Credits: dòng bản quyền có website", WEBSITE in footer.text())
    check("tab Credits: dòng bản quyền không bị elide",
          footer.width() >= footer.sizeHint().width(),
          f"{footer.width()} vs {footer.sizeHint().width()}")
    fb = footer.mapTo(dlg, QPoint(0, 0))
    check("tab Credits: dòng bản quyền nằm trong khung hộp thoại",
          fb.y() >= 0 and fb.y() + footer.height() <= dlg.height(),
          f"y={fb.y()} h={footer.height()} dlg_h={dlg.height()}")

    # Tab Paths có thêm dòng "License (project)" -> phải vẫn thấy hết, không tràn.
    dlg.tabs.setCurrentIndex(3)
    app.processEvents()
    paths_browser = dlg.tabs.currentWidget().findChildren(QTextBrowser)[0]
    check("tab Paths: có dòng LICENSE",
          "License (project)" in paths_browser.toPlainText()
          and "LICENSE" in paths_browser.toPlainText())
    paths_scroll = paths_browser.verticalScrollBar().maximum()
    check("tab Paths: thấy hết các dòng, không phải cuộn",
          paths_scroll == 0, f"scroll_max={paths_scroll}")

    # Cả 4 tab phải sạch rò theme sáng.
    for name, idx in (("about", 0), ("environment", 1), ("credits", 2), ("paths", 3)):
        dlg.tabs.setCurrentIndex(idx)
        app.processEvents()
        pm = dlg.grab()
        blocks = H.light_blocks(pm)
        bands = H.light_bands(pm)
        check(f"tab {name}: không có khối sáng", not blocks, str(blocks[:4]))
        check(f"tab {name}: không có dải sáng mỏng", not bands, str(bands[:4]))

    dlg.tabs.setCurrentIndex(0)
    app.processEvents()
    legal_y = dlg.copyright_label.mapTo(dlg, QPoint(0, 0)).y()
    tabs_y = dlg.tabs.mapTo(dlg, QPoint(0, 0)).y()
    check("dòng bản quyền nằm TRÊN khu tab", legal_y < tabs_y, f"{legal_y} < {tabs_y}")
    web = dlg.website_label
    web_right = web.mapTo(dlg, QPoint(0, 0)).x() + web.width()
    check("website không tràn mép phải", web_right <= dlg.width() - 20,
          f"right={web_right} w={dlg.width()}")
    check("bản quyền và website cùng hàng",
          abs(web.mapTo(dlg, QPoint(0, 0)).y() - legal_y) <= 6)
    check("website nằm bên phải dòng bản quyền",
          web.mapTo(dlg, QPoint(0, 0)).x()
          > dlg.copyright_label.mapTo(dlg, QPoint(0, 0)).x())


def main() -> int:
    check_source()
    try:
        check_render()
    except ImportError as exc:
        print(f"  [SKIP] bỏ phần render: {exc}", flush=True)

    print("\n== KẾT QUẢ ==", flush=True)
    print("FAIL:", FAILS or "không có", flush=True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
