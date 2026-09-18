#!/usr/bin/env python3
"""validate_icon_fonts.py — mọi icon trong Studio phải render được bằng font thật.

Chạy:

    PYTHONUTF8=1 QT_QPA_PLATFORM=offscreen python tools/validate_icon_fonts.py

Ba lớp lỗi từng xảy ra thật và được khoá ở đây:

  A. Tên qtawesome không tồn tại (ví dụ "fa5s.console-screen" là mã FA6) trả về
     QIcon rỗng — người dùng thấy ô trống/mất icon mà không có lỗi nào.
  B. Mã PUA Segoe không có trong font được chọn (ví dụ "delete" từng trỏ
     U+E77D — VẮNG MẶT trong Segoe MDL2 Assets) render thành ô tofu.
     Kiểm tra bằng cmap đọc trực tiếp từ TTF hệ thống, không tin
     QFontDatabase.families() (sai trong offscreen).
  C. Bộ chọn font theo từng glyph (_family_for_char) phải còn đó và phải tìm
     được font chứa mã cho MỌI glyph trong GLYPHS.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "studio"
sys.path.insert(0, str(STUDIO))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FAILS: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label} {detail}", flush=True)
    if not ok:
        FAILS.append(label)


def main() -> int:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)

    # -- A. tên qtawesome dùng trong source phải cho ra pixmap thật ----------
    pattern = re.compile(r'["\'](fa[456]s\.[a-z0-9\-]+)["\']')
    used = sorted({
        name
        for p in STUDIO.rglob("*.py")
        if "__pycache__" not in str(p)
        for name in pattern.findall(p.read_text(encoding="utf-8", errors="ignore"))
    })
    from app.vxpui.icons import icon as chrome_icon

    dead = []
    for name in used:
        qicon = chrome_icon(name)
        pixmap = qicon.pixmap(16, 16)
        if qicon.isNull() or pixmap.isNull():
            dead.append(name)
    check(f"cả {len(used)} tên qtawesome trong source đều render được",
          not dead, f"hỏng={dead}")

    # -- B/C. glyph PUA phải có trong cmap của font hệ thống -----------------
    from app.ui.icons import (
        FONT_CANDIDATES,
        GLYPHS,
        _family_codepoints,
        _family_for_char,
    )

    coverage = {family: _family_codepoints(family) for family in FONT_CANDIDATES}
    check("đọc được cmap ít nhất một font Segoe icon",
          any(coverage.values()),
          str({f: len(c) for f, c in coverage.items()}))

    orphans = []
    for name, char in GLYPHS.items():
        cp = ord(char)
        families = [f for f, cps in coverage.items() if cps and cp in cps]
        chosen = _family_for_char(char)
        chosen_ok = coverage.get(chosen) and cp in coverage[chosen]
        if not families or not chosen_ok:
            orphans.append((name, f"U+{cp:04X}", chosen))
    check("mọi glyph GLYPHS có font chứa mã (chọn theo từng glyph)",
          not orphans, f"tofu={orphans[:6]}")

    # -- D. khoá hai mã từng gây lỗi thật ------------------------------------
    source = (STUDIO / "app/ui/icons.py").read_text(encoding="utf-8")
    check('delete dùng U+E74D (U+E77D không tồn tại trong MDL2)',
          '"delete": "\ue74d"' in source)
    check("bộ chọn font theo glyph còn đó", "def _family_for_char" in source)
    check("terminal action không dùng tên FA6", "fa5s.console-screen" not in
          (STUDIO / "app/vxpui/main_window.py").read_text(encoding="utf-8"))

    # -- E. đường fallback MDL2 khi qtawesome hỏng trong build đóng gói ------
    from app.vxpui import icons as chrome_module

    unmapped = [n for n in used if n.split(".", 1)[-1]
                not in chrome_module._FA5_TO_GLYPH]
    check("mọi tên fa trong source có khoá map fallback tường minh",
          not unmapped, str(unmapped))
    bad_keys = sorted({k for k in chrome_module._FA5_TO_GLYPH.values()
                       if k not in GLYPHS})
    check("khoá map fallback đều tồn tại trong GLYPHS", not bad_keys, str(bad_keys))

    original_qta = chrome_module.qta
    try:
        chrome_module.qta = None
        chrome_module._cached_icon.cache_clear()
        dead_fb = []
        for name in used:
            ic = chrome_module.icon(name)
            if ic.isNull() or ic.pixmap(16, 16).isNull():
                dead_fb.append(name)
        check("fallback MDL2 render đủ mọi tên fa khi qtawesome hỏng",
              not dead_fb, str(dead_fb))
    finally:
        chrome_module.qta = original_qta
        chrome_module._cached_icon.cache_clear()

    print("\n== KẾT QUẢ ==", flush=True)
    print("FAIL:", FAILS or "không có", flush=True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
