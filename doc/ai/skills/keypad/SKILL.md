---
name: keypad
description: Prompt điều khiển bàn phím S30+/VXP cho AI Agent: tên phím Lua thật (up/down/left/right/ok/softleft/softright/back/clear/0-9/*/#), bảng nút vật lý, cặp keypressed/keyreleased, alias số, menu mẫu (Nokia 225 RM-1011)
---

# Keypad S30+ — prompt cho AI Agent

Dùng skill này khi viết/sửa code xử lý phím cho game/app LuaS30 trên điện
thoại phím cứng (Nokia 225 Dual SIM RM-1011 và máy S30+/MRE-style). Nguồn
thật: `doc/reference/API.md` + `doc/ai/Keypad.md` + `src/engine.lua` của
project đang mở.

## Hợp đồng phím (bắt buộc)

Runtime chỉ gửi tên phím chữ thường qua:

```lua
function engine.keypressed(k) end
function engine.keyreleased(k) end
```

Tập tên duy nhất tồn tại: `up down left right ok softleft softright clear
back 0 1 2 3 4 5 6 7 8 9 * #`. Các hằng `KEY_UP`, `KEY_OK`... chỉ là nhãn
tài liệu cho nút vật lý — KHÔNG viết `key == "KEY_UP"`, `"LEFT"`,
`"SOFTLEFT"` trong code Lua. Luôn `k = tostring(k):lower()` trước khi so.

## Bảng nút vật lý → tên Lua

D-Pad lên/xuống/trái/phải → `up`/`down`/`left`/`right`. Center OK → `ok`.
Softkey trái/phải → `softleft`/`softright` (trái = menu, phải = back).
Số `1`–`9` → `"1"`–`"9"` (`2/8/4/6/5` dự phòng D-Pad/OK).
`0` → `"0"`. `*` → `"*"`. `#` → `"#"`.
Xem bảng đầy đủ 21 nút ở `doc/ai/Keypad.md` mục 1.

## Quy tắc bắt buộc

1. Cặp pressed/released: giữ bảng trạng thái (`true`/`false`), không suy
   diễn "đang giữ" từ một sự kiện.
2. Không chuột/touch — mọi tương tác qua D-Pad + softkey + phím số.
3. Di chuyển chấp nhận cả hai bộ (`up`/`2`, `down`/`8`, `left`/`4`,
   `right`/`6`, `ok`/`5`).
4. Không bịa tên phím; nghi ngờ thì grep `src/engine.lua` của project.
5. Menu: lên/xuống wrap-around, `ok` chọn, `softright`/`back` thoát,
   vẽ con trỏ bằng `rect`/`text`.

## Mẫu chuẩn

```lua
local keys = {}
function engine.keypressed(k) keys[tostring(k):lower()] = true end
function engine.keyreleased(k) keys[tostring(k):lower()] = false end
```

## Mẫu có sẵn trong repo

Template dự án **Keypad Demo** (`templates/keypad-demo`, chọn được trong
`Cấu hình MediaTek MRE SDK`) hiện thực đủ tài liệu này: `src/keypad.lua`
(bảng trạng thái + cờ `fresh` + alias số + `drawPad`), `main.lua` (menu
wrap-around, kiểm tra phím, nhập số). Chép `src/keypad.lua` sang project khác
là xong phần keypad.

## Kiểm chứng

- Không còn chuỗi `"KEY_*"` hay tên phím HOA trong Lua.
- Test stub: gọi `engine.keypressed("down")`, assert `menu_index` đổi.
- Chạy được trên emulator với bàn phím `VXPEmu` / `PhoneKeypad`.
- Không cần máy thật: `py -3.12 tools/validate_project_templates_e2e.py`
  (tạo dự án thật từ template rồi chạy `tools/keypad_template_check.lua`).
