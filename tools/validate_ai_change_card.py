"""validate_ai_change_card.py — card tổng hợp 'Đã sửa N tệp +X -Y' trong Chat AI.

Kiểm tra: khi AI áp code edit, transcript render card kiểu Cline/Cursor
(header + tổng dòng xanh/đỏ + nút Review + danh sách từng tệp + link bung gọn),
main_window luồn số dòng +/− từng tệp và giữ bản đã áp để Review mở lại diff.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []


def check(ok: bool, label: str) -> None:
    print(("  [OK  ] " if ok else "  [FAIL] ") + label)
    if not ok:
        errors.append(label)


chat = (ROOT / "studio/app/views/ai_chat_view.py").read_text(encoding="utf-8")
mw = (ROOT / "studio/app/vxpui/main_window.py").read_text(encoding="utf-8")

check(
    "def _change_card_html" in chat and "def _insert_change_card" in chat,
    "AIChatView có bộ dựng/chèn card thay đổi",
)
check(
    'self.transcript.setOpenLinks(False)' in chat
    and "anchorClicked.connect(self._on_transcript_anchor)" in chat,
    "transcript nối anchorClicked cho nút trên card",
)
check(
    "x-luas30://review/" in chat and "x-luas30://more/" in chat
    and "CARD_VISIBLE_FILES = 3" in chat,
    "card có link Review + bung/gọn 'Hiển thị thêm N tệp'",
)
check(
    'if role == "card":' in chat,
    "_render_history dựng lại card khi chuyển phiên",
)
check(
    "def on_code_changes_applied(" in chat
    and "files: list | None = None" in chat
    and 'self._change_cards[card_id] = {"files": entries, "expanded": False}' in chat,
    "on_code_changes_applied nhận stats từng tệp và tạo card",
)
check(
    'if str(item.get("role") or "") in {"user", "assistant"}' in chat,
    "entry card không lọt vào payload gửi provider",
)
check(
    'self.ai_chat.on_code_changes_applied(paths, str(backup or ""), files=files' in mw,
    "main_window truyền +/− từng tệp khi áp code",
)
check(
    "self._ai_last_applied = change_set" in mw
    and "view.mark_applied(self._ai_last_applied_backup)" in mw,
    "Review trên card mở lại diff của đợt đã áp",
)

print("\n== KẾT QUẢ ==")
if errors:
    print("FAIL:")
    for e in errors:
        print(" -", e)
    raise SystemExit(1)
print("FAIL: không có")
