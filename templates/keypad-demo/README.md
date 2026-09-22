# Keypad Demo — template LuaS30 / MRE

Template minh hoạ **hợp đồng phím S30+** cho điện thoại phím cứng (Nokia 225
Dual SIM RM-1011 và máy S30+/MRE-style). Nguồn thật của hợp đồng:

- [`doc/ai/Keypad.md`](../../doc/ai/Keypad.md) — bảng 21 nút + quy tắc + mẫu chuẩn
- [`doc/ai/skills/keypad/SKILL.md`](../../doc/ai/skills/keypad/SKILL.md) — bản nạp máy cho AI Agent
- [`doc/reference/API.md`](../../doc/reference/API.md) — mục `## Input`
- `engine/src/runtime_lua.c` → `key_name()` — bảng tên phim thật của runtime

## Hợp đồng phím

Runtime **chỉ** gửi tên phím chữ thường qua hai callback:

```lua
function engine.keypressed(k) end
function engine.keyreleased(k) end
```

Tập tên duy nhất tồn tại:

```text
up  down  left  right  ok  softleft  softright  clear  back  0-9  *  #
```

Các hằng như `KEY_UP`, `KEY_OK`, `KEY_SOFT_LEFT` trong tài liệu chỉ là **nhãn
cho nút vật lý**, không phải identifier Lua. Không bao giờ viết
`if k == "KEY_UP"` / `"LEFT"` / `"SOFTLEFT"`. Luôn chuẩn hoá trước khi so:

```lua
k = tostring(k):lower()
```

## Cấu trúc

```text
keypad-demo/
├── conf.lua            240x320, 15 fps
├── project.json        appid riêng, compat_profile nokia225-rm1011
├── main.lua            MENU -> { Kiem tra phim | Nhap so | Huong dan | Thoat }
└── src/
    ├── keypad.lua      hợp đồng phím: bảng trạng thái, alias số, vẽ bàn phím
    └── engine.lua      helper mỏng quanh `engine`
```

`src/keypad.lua` là phần đáng chép sang project khác:

| Hàm | Việc |
| :--- | :--- |
| `K.press(raw)` / `K.release(raw)` | chuẩn hoá tên phím, trả `(tên, fresh)`; tên lạ bị bỏ |
| `K.down("up", "2")` | `true` nếu **một trong** các phím đang được giữ |
| `K.up()` `K.downKey()` `K.left()` `K.right()` `K.ok()` | D-Pad + alias số `2/8/4/6/5` |
| `K.options()` / `K.back()` | softkey trái = menu, softkey phải = back |
| `K.digit(k)` | trả `"0".."9"` nếu là phím số |
| `K.reset()` | gỡ trạng thái khi đổi màn hình / `resume` |
| `K.drawPad(x, y, cw, ch, gap, colors)` | vẽ bàn phím vật lý bằng `rect`/`text` |

`K.press()` trả thêm cờ `fresh` vì runtime có thể gửi lại `keypressed` cho phím
đang giữ (sự kiện repeat). Hành động một lần (OK, softkey, `clear`, `#`, `*`)
phải chặn bằng `fresh`; điều hướng để repeat cho cuộn nhanh.

## Quy tắc template này tuân theo

1. Giữ bảng trạng thái pressed/released — không suy diễn "đang giữ" từ một sự kiện.
2. Không chuột/touch: mọi tương tác qua D-Pad + softkey + phím số.
3. Di chuyển chấp nhận cả D-Pad lẫn phím số dự phòng.
4. Softkey trái = menu/help, softkey phải = back — không đảo ngược.
5. Không bịa tên phím: tên ngoài danh sách trên bị `K.press()` bỏ qua.
6. Menu wrap-around lên/xuống; con trỏ vẽ bằng `rect`/`text`, không dùng ảnh.
7. Nhập liệu: digit nối chuỗi, `clear` xoá 1 ký tự, `#` xoá hết (ghi rõ trong
   màn hình "Huong dan").

## Build thử

```bash
python tools/build.py --project templates/keypad-demo \
  --toolchain toolchain/arm-gcc --compat-profile nokia225-rm1011 --no-run
```

## Kiểm chứng

Ba lớp, chạy được thật:

```bash
# 1. Hợp đồng phím trong tài liệu + code template (không cần dependency)
python tools/validate_keypad_skill.py

# 2. Ba chỗ đăng ký template khớp nhau: dialog / PROJECT_TEMPLATES / templates/
python tools/validate_mre_project_wizard.py

# 3. End-to-end: mở dialog thật, tạo dự án thật từ template này, rồi chạy
#    tools/keypad_template_check.lua trên chính dự án vừa tạo
py -3.12 tools/validate_project_templates_e2e.py
```

Lớp 3 cần **Lua 5.1** để chạy harness. Đặt `LUA_BIN` trỏ tới `lua.exe`, hoặc
build từ source trong repo (không có binary thì bước Lua báo `SKIP`):

```bash
cd vendor/lua-5.1.5/src
gcc -O2 -w -o lua.exe $(ls *.c | grep -v -E '^(lua|luac)\.c$') lua.c -lm
```

`tools/keypad_template_check.lua` chạy 37 assert bằng stub `engine`: wrap-around
menu (cả D-Pad lẫn alias số), giữ/nhả nhiều phím, tên phím không tồn tại bị bỏ
qua, chữ HOA vẫn được nhận sau `:lower()`, digit/`clear`/`#`, và cờ `fresh` chặn
hành động lặp khi runtime gửi lại `keypressed`.
