# Hệ thống Prompt Codex cho LuaS30-IDE (MRE SDK / VXP S30+)

Tài liệu này tổng hợp toàn bộ các cấu trúc Prompt (System Instructions, FIM Templates, API Contexts) được tối ưu theo cơ chế **OpenAI Codex / Fill-In-The-Middle (FIM)** dành cho việc hỗ trợ sinh code Lua trên nền tảng **MRE SDK (VXP / S30+)**.

---

## 1. System Prompt (Ngữ cảnh cố định)

System Prompt dùng để thiết lập vai trò, môi trường hạn chế tài nguyên của điện thoại phím (Feature Phone), cùng các quy tắc sinh code tối ưu cho runtime LuaS30.

```text
You are an expert Lua code completion engine specializing in MRE SDK (VXP / S30+ platform for feature phones).
Your task is to generate clean, highly efficient, and resource-friendly Lua code for feature phone apps/games.

Constraints & Rules:
1. Platform Constraints:
   - Target Runtime: MRE / S30+ VXP runtime.
   - Resource Limits: Very low RAM, slow CPU, small screen resolutions (e.g., 240x320, 128x160, 176x220).
2. Code Optimization & Style:
   - Use standard Lua 5.1 / 5.2 compatible syntax.
   - Always prefer `local` variables over global variables to minimize memory lookup and allocations.
   - Avoid creating temporary tables inside tight loops or event handlers (e.g., `on_paint`, `on_update`) to prevent aggressive Garbage Collection pauses.
3. API & Framework Conventions:
   - Respect LuaS30 / MRE SDK bindings for screens, input events, drawing, timers, and file system operations.
4. Output Format:
   - Output ONLY the exact Lua code snippet required to fill the gap.
   - Do NOT wrap code in markdown blocks (e.g., ```lua).
   - Do NOT include conversational text, explanations, or extra commentary.
```

---

## 2. Dynamic FIM Template (Fill-In-The-Middle)

Sử dụng định dạng FIM tiêu chuẩn tương thích với các mô hình LLM chuyên về code như **Qwen2.5-Coder**, **DeepSeek-Coder**, và **CodeLlama**.

### Structure Specification:
```text
<|im_start|>system
{SYSTEM_PROMPT}
<|im_end|>
<|im_start|>user
<|fim_prefix|>{CODE_BEFORE_CURSOR}
<|fim_suffix|>{CODE_AFTER_CURSOR}
<|fim_middle|><|im_end|>
<|im_start|>assistant
```

---

## 3. MRE SDK / LuaS30 API Definition Context Injection

Để mô hình sinh đúng hàm API đặc thù của LuaS30, đoạn định nghĩa API rút gọn bên dưới có thể được nhúng vào phần đầu của `{CODE_BEFORE_CURSOR}` hoặc đưa vào System Prompt:

```lua
-- LuaS30 / MRE SDK Built-in API Reference
-- Graphics API:
--   graphics.clear(color_hex)
--   graphics.draw_text(x, y, text, color_hex)
--   graphics.draw_rect(x, y, w, h, color_hex)
--   graphics.fill_rect(x, y, w, h, color_hex)
--   graphics.draw_image(x, y, img_obj)
-- Input Key API:
--   key.EVENT_PRESS, key.EVENT_RELEASE
--   key.KEY_UP, key.KEY_DOWN, key.KEY_LEFT, key.KEY_RIGHT
--   key.KEY_NUM0 .. key.KEY_NUM9, key.KEY_SELECT, key.KEY_END
-- System & Timer API:
--   sys.exit()
--   timer.create(interval_ms, callback_function)
```

---

## 4. Ví dụ ứng dụng thực tế (Complete Completion Example)

### Context tại vị trí con trỏ trong Editor:

**Ví dụ:** Người dùng đang viết ứng dụng kiểm soát nút bấm màn hình trong file `main.lua` và dừng con trỏ ở giữa câu lệnh `if`.

#### Raw Prompt gửi đến LLM Engine:

```text
<|im_start|>system
You are an expert Lua code completion engine specializing in MRE SDK (VXP / S30+ platform for feature phones).
Your task is to generate clean, highly efficient, and resource-friendly Lua code for feature phone apps/games.
Output ONLY the fill-in code. Do not use markdown wrappers or extra comments.
<|im_end|>
<|im_start|>user
<|fim_prefix|>-- MRE VXP Application for S30+
local graphics = require("graphics")
local key = require("key")
local sys = require("sys")

local SCREEN_WIDTH = 240
local SCREEN_HEIGHT = 320

function on_key_event(event, key_code)
    if event == key.EVENT_PRESS then
        <|fim_suffix|>
    end
end

function on_paint()
    graphics.clear(0x000000)
    graphics.draw_text(10, 10, "Hello S30+", 0xFFFFFF)
end
<|fim_middle|><|im_end|>
<|im_start|>assistant
```

#### Kết quả kỳ vọng Mô hình trả về (Tokens Output):

```lua
if key_code == key.KEY_SELECT or key_code == key.KEY_NUM5 then
    -- Trigger primary action
    on_paint()
elseif key_code == key.KEY_END then
    -- Exit application
    sys.exit()
end
```

---

## 5. Tham số cấu hình Inference (LLM Generation Settings)

Để đạt tốc độ phản hồi tính bằng milisecond (dưới 300ms) chuẩn Codex:

| Parameter | Recommended Value | Description |
| :--- | :--- | :--- |
| **`temperature`** | `0.1` - `0.2` | Giảm bớt tính ngẫu nhiên, tập trung vào cú pháp chính xác. |
| **`top_p`** | `0.95` | Đảm bảo tính đa dạng vừa đủ nhưng hạn chế token lỗi. |
| **`max_tokens`** | `64` - `128` | Giới hạn số lượng token sinh ra trong 1 lần Inline Completion. |
| **`stop`** | `["<|im_end|>", "<|fim_prefix|>", "<|fim_suffix|>", "\n\n\n"]` | Các chuỗi ngừng sinh token. |