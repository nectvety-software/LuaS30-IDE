"""
guides.py — Đường dóng căn chỉnh (smart guides) kiểu Figma / Photoshop.

Khi kéo một thành phần trên canvas, nó tự "hít" (snap) vào vị trí thẳng hàng
với các thành phần khác hoặc với khung màn hình 240×320; đồng thời một đường
GẠCH NÉT hiện ra cho biết đang dóng theo mép nào:

  * XANH  `palette.GREEN` — dóng với MỘT THÀNH PHẦN KHÁC (mép hoặc tâm)
  * VÀNG  `palette.AMBER` — dóng với KHUNG MÀN HÌNH (tâm hoặc 4 mép)

Mỗi trục được giải độc lập, dóng 3 mép của vật đang kéo (đầu / giữa / cuối)
với 3 mép của từng vật tham chiếu — kể cả dóng chéo kiểu mép trái của vật này
thẳng với mép phải của vật kia.

Module này chỉ chứa HÌNH HỌC: không vẽ, không phụ thuộc widget, nên kiểm thử
được bằng số thuần (xem `_guides_check.py`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.ui import palette
from PySide6.QtCore import QRectF

# ---------------------------------------------------------------- hằng số

# Ngưỡng bắt dính, tính bằng px màn hình (đơn vị scene). Bằng đúng bước lưới
# nền GRID=4 nên hai cơ chế không giành nhau: lưới làm tròn, dóng tinh chỉnh.
SNAP_TOLERANCE = 4.0

# đường dóng được kéo dài quá hai đầu một chút cho dễ thấy
GUIDE_PAD = 6.0
MIN_GUIDE_LEN = 10.0

KIND_OBJECT = "object"   # dóng với thành phần khác -> xanh
KIND_FRAME = "frame"     # dóng với khung màn hình -> vàng

AXIS_V = "v"   # đường DỌC: x cố định, kéo dài theo trục y
AXIS_H = "h"   # đường NGANG: y cố định, kéo dài theo trục x

GUIDE_OBJECT_COLOR = "palette.GREEN"
GUIDE_FRAME_COLOR = "palette.AMBER"

# Thứ tự ưu tiên khi hai phương án CÙNG độ lệch: tâm-trước, rồi mép cùng tên,
# rồi mép khác tên. Chỉ số mép: 0 = đầu (trái/trên), 1 = giữa, 2 = cuối.
_PAIR_RANK = {
    (1, 1): 0,                      # tâm ↔ tâm  (dóng "chắc" nhất)
    (0, 0): 1, (2, 2): 1,           # trái↔trái, phải↔phải
    (0, 2): 2, (2, 0): 2,           # trái↔phải (dóng so le)
}
_PAIR_RANK_DEFAULT = 3              # mọi cặp dính tới tâm của vật kia


@dataclass(frozen=True)
class Guide:
    """Một đường dóng cần vẽ.

    `axis`  — 'v' (đường dọc, `pos` là toạ độ x) hoặc 'h' (đường ngang, `pos` là y)
    `pos`   — toạ độ trên trục cố định
    `start` — mép bắt đầu của đoạn kẻ (trên trục còn lại)
    `end`   — mép kết thúc
    `kind`  — KIND_OBJECT (xanh) hoặc KIND_FRAME (vàng)
    """

    axis: str
    pos: float
    start: float
    end: float
    kind: str = KIND_OBJECT

    @property
    def length(self) -> float:
        return abs(self.end - self.start)

    @property
    def is_frame(self) -> bool:
        return self.kind == KIND_FRAME


# ---------------------------------------------------------------- hình học

def rotated_size(w: float, h: float, rotation: float) -> tuple[float, float]:
    """Kích thước hộp bao theo trục toạ độ của hình (w, h) sau khi xoay."""
    if not rotation:
        return float(w), float(h)
    a = math.radians(rotation)
    c, s = abs(math.cos(a)), abs(math.sin(a))
    return w * c + h * s, w * s + h * c


def bounds_at(rect: QRectF, rotation: float, pos) -> QRectF:
    """Hộp bao của `rect` khi item nằm ở `pos` và xoay `rotation`.

    Gốc xoay là TÂM hình chữ nhật (xem `DesignerItem.set_angle`), nên hộp bao
    vẫn canh tâm tại `pos + rect.center()` và vượt ra mỗi phía (bw − w) / 2.
    """
    if not rotation:
        return QRectF(pos.x(), pos.y(), rect.width(), rect.height())
    bw, bh = rotated_size(rect.width(), rect.height(), rotation)
    cx = pos.x() + rect.width() / 2.0
    cy = pos.y() + rect.height() / 2.0
    return QRectF(cx - bw / 2.0, cy - bh / 2.0, bw, bh)


def edges(rect: QRectF, axis: str) -> tuple[float, float, float]:
    """Ba mép của `rect` trên một trục: (đầu, giữa, cuối)."""
    if axis == AXIS_V:
        return rect.left(), rect.center().x(), rect.right()
    return rect.top(), rect.center().y(), rect.bottom()


def _solve_axis(rect: QRectF, refs, axis: str, tolerance: float):
    """Phương án dóng tốt nhất trên MỘT trục. Trả (delta, (pos, kind)) hoặc (0, None)."""
    mine = edges(rect, axis)
    best = None   # ((|delta|, rank), delta, pos, kind)
    for ref_rect, kind in refs:
        theirs = edges(ref_rect, axis)
        for mi, mval in enumerate(mine):
            for ti, tval in enumerate(theirs):
                delta = tval - mval
                if abs(delta) > tolerance:
                    continue
                key = (abs(delta), _PAIR_RANK.get((mi, ti), _PAIR_RANK_DEFAULT))
                if best is None or key < best[0]:
                    best = (key, delta, tval, kind)
    if best is None:
        return 0.0, None
    _key, delta, pos, kind = best
    return delta, (pos, kind)


def _make_guide(snapped: QRectF, refs, axis: str, match) -> Guide:
    """Dựng đường dóng, kéo dài qua MỌI đối tượng cùng nằm trên vị trí đó."""
    pos, kind = match
    participants = [snapped]
    for ref_rect, _kind in refs:
        if any(abs(v - pos) <= 0.5 for v in edges(ref_rect, axis)):
            participants.append(ref_rect)

    if axis == AXIS_V:
        lo = min(r.top() for r in participants)
        hi = max(r.bottom() for r in participants)
    else:
        lo = min(r.left() for r in participants)
        hi = max(r.right() for r in participants)

    lo -= GUIDE_PAD
    hi += GUIDE_PAD
    if hi - lo < MIN_GUIDE_LEN:
        mid = (lo + hi) / 2.0
        lo, hi = mid - MIN_GUIDE_LEN / 2.0, mid + MIN_GUIDE_LEN / 2.0
    return Guide(axis=axis, pos=float(pos), start=float(lo), end=float(hi), kind=kind)


def solve(rect: QRectF, refs, tolerance: float = SNAP_TOLERANCE):
    """Tìm độ dịch nhỏ nhất để `rect` dóng thẳng hàng với `refs`.

    `refs` là danh sách `(QRectF, kind)`. Nên đặt khung màn hình LÊN ĐẦU danh
    sách: khi hai phương án cùng độ lệch thì phương án gặp trước thắng, mà dóng
    theo khung (vàng) là thông tin đáng chú ý hơn dóng theo một thành phần.

    Trả `(dx, dy, [Guide, ...])`; không có phương án nào trong ngưỡng thì
    `(0.0, 0.0, [])`.
    """
    if not refs:
        return 0.0, 0.0, []

    dx, v_match = _solve_axis(rect, refs, AXIS_V, tolerance)
    dy, h_match = _solve_axis(rect, refs, AXIS_H, tolerance)

    snapped = rect.translated(dx, dy)
    guides: list[Guide] = []
    if v_match is not None:
        guides.append(_make_guide(snapped, refs, AXIS_V, v_match))
    if h_match is not None:
        guides.append(_make_guide(snapped, refs, AXIS_H, h_match))
    return dx, dy, guides


def describe(guides) -> str:
    """Mô tả ngắn các đường dóng (dùng cho log / thông báo trạng thái)."""
    if not guides:
        return ""
    parts = []
    for g in guides:
        where = "dọc" if g.axis == AXIS_V else "ngang"
        what = "khung" if g.is_frame else "thành phần"
        parts.append(f"{where} {g.pos:.0f} ({what})")
    return ", ".join(parts)
