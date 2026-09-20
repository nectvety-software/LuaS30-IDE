# Keypad Prompt — AI Agent điều khiển bàn phím S30+ / VXP

Prompt này dạy AI Agent viết code xử lý phím cho game/app LuaS30 chạy trên
điện thoại phím cứng (Nokia 225 Dual SIM RM-1011 và máy S30+/MRE-style).
Đọc cùng `doc/ai/SKILL.md` + `doc/ai/PROMPT.md`. Bản nạp máy của ChatAI nằm ở
`doc/ai/skills/keypad/SKILL.md` (cùng nội dung, thêm frontmatter).

## 0. Hợp đồng phím (bắt buộc)

Runtime LuaS30 **chỉ gửi tên phím chữ thường** qua hai callback, xem
`doc/reference/API.md`:

```lua
function engine.keypressed(k) end
function engine.keyreleased(k) end
```

Tập tên phím duy nhất được phép dùng trong code Lua:

```text
up
down
left
right
ok
softleft
softright
clear
back
0 1 2 3 4 5 6 7 8 9
*
#
```

Các hằng `KEY_UP`, `KEY_OK`... trong bảng dưới là **nhãn tài liệu cho nút
vật lý, KHÔNG phải identifier Lua**. Không bao giờ viết:

```lua
if key == "KEY_UP" then end      -- SAI: runtime không gửi chuỗi này
if key == "LEFT" then end        -- SAI: sai chữ hoa, sai tên
if key == "SOFTLEFT" then end    -- SAI: tên đúng là "softleft"
```

Luôn chuẩn hoá trước khi so sánh:

```lua
k = tostring(k):lower()
```

## 1. Bảng nút vật lý → tên Lua → cách dùng

| STT | Nút phần cứng | Nhãn tài liệu | Tên Lua (`k`) | Nhóm | Cách dùng khuyến nghị trong app/game |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | D-Pad Lên | `KEY_UP` | `up` | Điều hướng | Đi lên / chọn item phía trên |
| 2 | D-Pad Xuống | `KEY_DOWN` | `down` | Điều hướng | Đi xuống / chọn item phía dưới |
| 3 | D-Pad Trái | `KEY_LEFT` | `left` | Điều hướng | Sang trái / lật trang / giảm chỉ số |
| 4 | D-Pad Phải | `KEY_RIGHT` | `right` | Điều hướng | Sang phải / lật trang / tăng chỉ số |
| 5 | Phím Center (OK) | `KEY_OK` | `ok` | Điều hướng | Xác nhận / action chính (nhảy, bắn, tương tác) |
| 6 | Softkey Trái | `KEY_SOFT_LEFT` | `softleft` | Chức năng | Mở menu Options / kỹ năng phụ |
| 7 | Softkey Phải | `KEY_SOFT_RIGHT` | `softright` | Chức năng | Trở về / hủy thao tác |
| 8 | Phím số `1` | `KEY_1` | `1` | Số | Chéo trái-lên / gán skill 1 |
| 9 | Phím số `2` | `KEY_2` | `2` | Số | Đi lên (dự phòng `up`) |
| 10 | Phím số `3` | `KEY_3` | `3` | Số | Chéo phải-lên / gán skill 2 |
| 11 | Phím số `4` | `KEY_4` | `4` | Số | Sang trái (dự phòng `left`) |
| 12 | Phím số `5` | `KEY_5` | `5` | Số | Center/OK (dự phòng `ok`) |
| 13 | Phím số `6` | `KEY_6` | `6` | Số | Sang phải (dự phòng `right`) |
| 14 | Phím số `7` | `KEY_7` | `7` | Số | Chéo trái-xuống / gán skill 3 |
| 15 | Phím số `8` | `KEY_8` | `8` | Số | Đi xuống (dự phòng `down`) |
| 16 | Phím số `9` | `KEY_9` | `9` | Số | Chéo phải-xuống / gán skill 4 |
| 17 | Phím số `0` | `KEY_0` | `0` | Số | Nhập số 0 / đổi nhanh vũ khí |
| 18 | Phím `*` | `KEY_STAR` | `*` | Đặc biệt | Tạm dừng / bật HUD / đổi kiểu nhập |
| 19 | Phím `#` | `KEY_HASH` | `#` | Đặc biệt | Bật/tắt âm / xoá ký tự nhập liệu |
| 20 | Phím Back/Clear | `KEY_BACK` | `back` | Chức năng | Thoát màn hình hiện tại về menu |
| 21 | Phím Clear | `KEY_CLEAR` | `clear` | Chức năng | Xoá ký tự / huỷ nhập liệu |

## 2. Quy tắc bắt buộc

1. **Cặp pressed/released**: giữ bảng trạng thái, set `true` ở
   `keypressed`, `false` ở `keyreleased`. Không suy diễn "đang giữ" từ một
   sự kiện đơn.
2. **Không chuột/touch**: không giả lập tap/click/drag. Mọi tương tác đi qua
   D-Pad + softkey + phím số.
3. **Alias số**: gameplay di chuyển nên chấp nhận cả hai bộ
   (`up`/`2`, `down`/`8`, `left`/`4`, `right`/`6`, `ok`/`5`) để chơi được
   khi D-Pad liệt một hướng.
4. **Softkey trái = menu**, softkey phải = back. Không đảo ngược hai phím này.
5. **Không bịa tên phím**: tên nào không có trong mục 0 thì không tồn tại.
   Khi nghi ngờ, mở `src/engine.lua` của project và grep tên hàm/key thật.
6. **Menu điều hướng**: lên/xuống đổi chỉ số có wrap-around, `ok` chọn,
   `softright`/`back` thoát. Vẽ con trỏ chọn bằng `rect`/`text`, không phụ
   thuộc ảnh.
7. **Nhập liệu**: digit nối chuỗi, `clear` xoá một ký tự, `#` xoá hết hoặc
   mute (chọn một, ghi rõ trong help của app).

## 3. Mẫu wrapper chuẩn

```lua
local keys = {}

function engine.keypressed(k)
    k = tostring(k):lower()
    keys[k] = true
end

function engine.keyreleased(k)
    k = tostring(k):lower()
    keys[k] = false
end

local function down(...)
    for i = 1, select("#", ...) do
        if keys[select(i, ...)] then return true end
    end
    return false
end

function input_up() return down("up", "2") end
function input_down() return down("down", "8") end
function input_left() return down("left", "4") end
function input_right() return down("right", "6") end
function input_ok() return down("ok", "5") end
```

Menu mẫu:

```lua
menu_index = 1
local items = {"Start", "Help", "Exit"}

function engine.keypressed(k)
    k = tostring(k):lower()
    if k == "up" or k == "2" then
        menu_index = menu_index - 1
        if menu_index < 1 then menu_index = #items end
    elseif k == "down" or k == "8" then
        menu_index = menu_index + 1
        if menu_index > #items then menu_index = 1 end
    elseif k == "ok" or k == "5" then
        menu_select(menu_index)
    elseif k == "softright" or k == "back" then
        menu_back()
    elseif k == "softleft" then
        menu_options()
    end
end
```

## 4. Checklist kiểm chứng

- [ ] Không còn chuỗi `"KEY_*"` hay tên phím HOA trong code Lua.
- [ ] Mọi `keypressed` đều có `keyreleased` đối xứng (trừ phím tác vụ một lần).
- [ ] Menu wrap-around lên/xuống, `ok` chọn, `softright` thoát — test bằng stub
      gọi `engine.keypressed("down")` rồi assert `menu_index`.
- [ ] Di chuyển chấp nhận cả D-Pad lẫn phím số dự phòng.
- [ ] Không có handler chuột/touch.
- [ ] Chạy được trên emulator với bàn phím thật của `VXPEmu` / `PhoneKeypad`.
