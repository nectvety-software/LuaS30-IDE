"""validate_ai_reasoning_effect.py — hiệu ứng suy luận của AI Agent trong Chat AI.

Kiểm tra (theo ảnh mẫu người dùng cung cấp):
  1. Dòng "đang suy nghĩ" có icon braille quay + bộ đếm "Bước i", hiện/ẩn theo
     vòng đời agent (`_set_agent_active` bật/tắt QTimer).
  2. Mỗi lượt chạy tool thêm khối thu gọn "Đã chạy N công cụ" vào transcript,
     bấm mở ra xem tên tool + lý do (anchor x-luas30://step/, dựng lại trong
     _render_history khi chuyển phiên).
  3. AI bị ép trả lời bằng TIẾNG VIỆT qua _system_prompt.
  4. Có style cho các widget mới trong theme.
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
theme = (ROOT / "studio/app/ui/theme.py").read_text(encoding="utf-8")

# 1. Thinking strip + animation lifecycle.
check(
    "self.thinking_frame = QFrame()" in chat
    and "self.thinking_spinner = QLabel(" in chat
    and "self.thinking_label = QLabel(" in chat,
    "Chat AI có khung 'đang suy nghĩ' (spinner + nhãn)",
)
check(
    "def _tick_thinking" in chat and "def _set_think_phase" in chat
    and "self._think_timer.timeout.connect(self._tick_thinking)" in chat,
    "Có QTimer quay icon + hàm đổi pha suy luận",
)
check(
    "self._think_timer.start()" in chat and "self._think_timer.stop()" in chat,
    "_set_agent_active bật/tắt animation theo vòng đời agent",
)
check(
    'range(0x280B, 0x2815)' in chat,
    "Spinner braille dựng bằng code điểm (an toàn encoding)",
)

# 2. Collapsible "Đã chạy N công cụ" step blocks.
check(
    "def _insert_step_block" in chat and "def _step_block_html" in chat,
    "Chat AI có bộ dựng/chèn khối bước thu gọn",
)
check(
    'x-luas30://step/' in chat and 'elif kind == "step":' in chat,
    "Khối bước có anchor bung/gọn xử lý trong _on_transcript_anchor",
)
check(
    'if role == "step":' in chat and 'self._history.append({"role": "step"' in chat,
    "_render_history dựng lại khối bước khi chuyển phiên",
)
check(
    "Đã chạy {len(tools)} công cụ" in chat,
    "Nhãn khối bước bằng tiếng Việt ('Đã chạy N công cụ')",
)
check(
    "self._insert_step_block(" in chat and 'self._set_think_phase("tools")' in chat,
    "_run_tools chèn khối bước + chuyển pha 'tools'",
)

# 3. Vietnamese answer enforcement.
check(
    "NGÔN NGỮ (BẮT BUỘC)" in chat and "TIẾNG VIỆT" in chat,
    "_system_prompt bắt buộc model trả lời bằng tiếng Việt",
)

# 4. Theme styles for the new widgets.
check(
    "QFrame#AIThinkingFrame" in theme
    and "QLabel#AIThinkingSpinner" in theme
    and "QLabel#AIThinkingLabel" in theme,
    "theme.py có style cho khung 'đang suy nghĩ'",
)

print("\n== KẾT QUẢ ==")
if errors:
    print("FAIL:")
    for e in errors:
        print(" -", e)
    raise SystemExit(1)
print("FAIL: không có")
