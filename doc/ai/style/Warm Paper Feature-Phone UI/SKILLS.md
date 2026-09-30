# SKILLS.md — Kỹ năng thực thi Warm Paper Feature-Phone UI / LuaS30

> **Tệp chỉ dẫn thường trực ở ROOT CỦA DỰ ÁN ỨNG DỤNG**, đi cùng `PROMPT.md`. Đây không phải `doc/ai/SKILL.md` nền tảng của LuaS30 IDE. Nếu cần skill kích hoạt theo yêu cầu, xem `skills/warm-feature-phone-ui/SKILL.md` tùy chọn trong gói phân phối.
>
> **Đã đối chiếu:** `LuaS30-IDE/main@9ff9e5702a6065a5c7e9abc426040c4979f911df`, ngày 28/09/2026. Luôn đọc và ưu tiên tệp source **đang cài** nếu khác phiên bản này.

## 0. Thứ tự ưu tiên và kiểm tra ban đầu

1. Đọc `LuaS30-IDE/doc/ai/SKILL.md` → `LuaS30-IDE/doc/ai/PROMPT.md` **trước khi scaffold hay sửa lớn**. Xem `VERSION`, `README.md`, `doc/INDEX.md`, `doc/reference/API.md`, `doc/ai/Keypad.md`.
2. Xem `templates/basic/`, `templates/keypad-demo/`, `profiles/generic-vxp-qvga.json`, `tools/build.py`, `tools/run_emulator.py`. Nếu nhắm thiết bị cụ thể, kiểm tra profile phù hợp; không suy diễn hỗ trợ máy thật.
3. Đọc **bản thực tế** của `project.json`, `conf.lua`, `main.lua`, `src/engine.lua` và các module hiện hữu của app. Sau đó đọc `PROMPT.md` và file này.
4. Chọn target mode `GENERIC_VXP` / `KNOWN_DEVICE_PROFILE` / `NEW_DEVICE_PORT`; demo không có chứng cứ thiết bị thực thì dùng `GENERIC_VXP`. Dự án source `engine.*` giữ độc lập khỏi `sdk/`, `engine/`, vendor SDK và code Studio PySide6.
5. Nếu tài liệu upstream dẫn đến file không có trên checkout, **kiểm tra có tồn tại** rồi đọc script nguồn thay thế. Tại snapshot đã kiểm tra, `doc/build/BUILD_VXP.md` được liên kết trong README/INDEX nhưng **không tồn tại**; đọc `tools/build.py`, `build*.bat` và `doc/ai/skills/vxp-build-run/SKILL.md` thay vì phỏng đoán.

**Phạm vi:** viết/điều chỉnh ứng dụng VXP trong root project người dùng. Không tự cập nhật `studio/app/ui/palette.py`: đó là **theme IDE** và không liên quan bảng màu app được renderer Lua vẽ. Không tự thay `doc/ai/SKILL.md`, `doc/ai/PROMPT.md` của IDE.

## 1. Skill: dựng project đúng cấu trúc và gói runtime

Wizard `ProjectSession.create_project()` copy một trong các template của `PROJECT_TEMPLATES`, cấp **appid mới** và có thể ghi `.luas30/mre_sdk.json` khi có metadata; không tự sao chép `appid` từ `templates/basic/project.json` sang các dự án khác. Đối với app mới, ưu tiên `basic` hoặc `keypad-demo`.

```text
app-root/
  project.json              # metadata do wizard cấp/điều chỉnh
  conf.lua                  # name, screen_width, screen_height, fps
  main.lua                  # entry thật; loader tìm main.lub/main.lua ở ROOT
  PROMPT.md / SKILLS.md     # chỉ dẫn AI cấp app
  src/
    engine.lua              # template cấp sẵn; đọc trước khi sửa
    theme.lua               # token và cache màu RGB565
    renderer.lua            # primitive UI + viewport
    text_layout.lua         # đo, wrap, phân trang, UTF-8
    keypad.lua              # xem templates/keypad-demo/src/keypad.lua
    app_state.lua           # điều phối screen
    chat_model.lua          # dữ liệu hội thoại và bản DEMO
    storage.lua             # optional: gate has_files
    transport_mock.lua      # offline DEMO
    screens/*.lua           # chỉ module cần thiết
  assets/                   # optional: icons/sfx nhỏ
  tests/                    # test matrix / host harness, build bỏ qua
  .luas30/                  # wizard / UI Designer quản lý khi dùng
  ui_design.lua             # chỉ khi export UI Designer
  build/                    # output sinh bởi builder; không chỉnh tay
```

`require("src.theme")` tìm resource `src/theme.lub` rồi `src/theme.lua`; **không** `require("theme")` nếu file ở `src/theme.lua` và chưa có quy ước search khác trong source hiện cài. Main nằm root; để main trong src có thể **build xanh nhưng runtime báo `main.lua missing`**. Nếu không cần phân tách module cho dự án nhỏ thì giảm số module, nhưng vẫn giữ entry và API như trên.

`tools/build.py::prepare_resources()` tại snapshot chỉ đóng gói `.lua` và những asset có đuôi `.png`, `.bmp`, `.gif`, `.mp3`, `.wav`, `.aac`, `.amr`, `.mid`, `.midi`, `.txt`, `.bin`, `.dat`. Các thư mục `build`, `release`, `saves`, `tests`, `backups`, `.git`, `.luas30` bị loại. Vì vậy **không** trông đợi `PROMPT.md`, `SKILLS.md`, `.luas30/ui_design.json` hoặc nội dung `tests/` xuất hiện trong VXP; mã `ui_design.lua` sau khi export thì được pack như Lua thông thường.

`project.json` giữ `single_vxp: true`, `compat_profile: "auto"` cho app generic trừ khi build hiện hành chỉ rõ chế độ khác; đồng bộ cấu hình `conf.lua` (width/height/FPS), tăng `app_version` khi phát hành và bảo toàn `appid` đã cấp. Profile JSON `profiles/generic-vxp-qvga.json` là dữ liệu tương thích/tham chiếu, **không** có cờ CLI `--profile generic-vxp-qvga` trong `tools/build.py` hiện tại.

## 2. Skill: bảng màu và renderer hiệu năng thấp

**Design tokens** đối chiếu trực tiếp từ `emir/claude-s40/app/src/.../Theme.java`:

| Token | Light | Dark |
|---|---|---|
| bg | `#FAF6EF` | `#141417` |
| surface | `#FFFFFF` | `#25252B` |
| border | `#E4DCCD` | `#34343C` |
| ink | `#26252C` | `#ECE8E1` |
| muted | `#7C766B` | `#9A958C` |
| accent | `#C96442` | `#E08A6B` |
| accentInk | `#FFFFFF` | `#1A1210` |
| bar | `#26252C` | `#0B0B0D` |
| barInk | `#FFFFFF` | `#F4EFE6` |
| selection | `#F6E3D9` | `#33272A` |
| error | `#B3261E` | `#FF8A7A` |
| errorBg | `#FBE4E1` | `#3A2323` |

**Module chạy Lua 5.1**, chỉ sử dụng API được tài liệu hóa:

```lua
-- src/theme.lua
local E = engine
local T = {}
local rgb = {
  light = {
    bg={250,246,239}, surface={255,255,255}, border={228,220,205},
    ink={38,37,44}, muted={124,118,107}, accent={201,100,66},
    accentInk={255,255,255}, bar={38,37,44}, barInk={255,255,255},
    selection={246,227,217}, error={179,38,30}, errorBg={251,228,225}
  },
  dark = {
    bg={20,20,23}, surface={37,37,43}, border={52,52,60},
    ink={236,232,225}, muted={154,149,140}, accent={224,138,107},
    accentInk={26,18,16}, bar={11,11,13}, barInk={244,239,230},
    selection={51,39,42}, error={255,138,122}, errorBg={58,35,35}
  }
}
local cache = {}
function T.get(mode)
  mode = mode == "dark" and "dark" or "light"
  if cache[mode] then return cache[mode] end
  local c = {}
  for key, value in pairs(rgb[mode]) do
    c[key] = E.color(value[1], value[2], value[3])
  end
  cache[mode] = c
  return c
end
return T
```

Phép đo trên RGB565 có thể làm những màu RGB24 tương đối gần nhau trở nên khó phân biệt; khi test screenshot, ưu tiên độ tương phản/khả năng đọc hơn tính chính xác từng RGB24.

**Primitive thật của LuaS30**: `engine.color`, `clear`, `rect`, `frame`, `line`, `text`, `set_font`, `text_width`, `font_height`, `flush`; ảnh (`image`, `image_region`) chỉ sau `has_images`. **Không có `roundRect`, `clip`, `drawImageScaled` trong API công khai đã kiểm tra.** Tránh tạo table/chuỗi động mỗi lần `draw`.

```lua
-- src/renderer.lua — ví dụ hình học không cần sprite
local E = engine
local R = {}
function R.box(x,y,w,h,fill,border)
  if w <= 0 or h <= 0 then return end
  E.rect(x,y,w,h,fill)
  if border then E.frame(x,y,w,h,border) end
end
function R.header(title,c,w)
  local height = 36
  E.rect(0,0,w,height,c.bar)
  E.text(8,10,title,c.barInk)
  return height
end
function R.status(text,c,w,h)
  local sh = 20
  E.rect(0,h-sh,w,sh,c.surface)
  E.line(0,h-sh,w-1,h-sh,c.border)
  E.text(6,h-sh+4,text,c.muted)
  return sh
end
return R
```

Tham số `w,h` lấy từ `engine.W or 240`, `engine.H or 320` và kiểm tra chiều cao font thực. Ví dụ trên là **sườn kỹ thuật**, chưa xử lý text dài; caller phải `fit` chuỗi theo `E.text_width()` trước khi vẽ. Không vẽ thanh softkey riêng nếu firmware/emulator đã hiển thị thanh đó.

**Viewport guard vì không có clip công khai:** trước khi vẽ dòng văn bản, kiểm tra `line.y >= viewport.top` và `line.y + lineHeight <= viewport.bottom`. Với khối nền giao viewport, tính lại hình chữ nhật đã clamp trong viewport; vẽ dòng bị cắt thì bỏ qua hoặc layout trang mới, không mặc định engine có scissor. Bỏ qua message block hoàn toàn ngoài vùng nhìn thấy. Cache font, màu, line layout; hiệu ứng thời gian dùng `update(dt)` hoặc `tick_ms()` để điều khiển, không phụ thuộc FPS chính xác của máy.

## 3. Skill: text layout, UTF-8 và chế độ đọc

1. Đặt `engine.set_font(size)` trước khi lấy `engine.text_width(str)` và `engine.font_height()`. Đo **pixel** trên chính font active; không tính width theo số byte hoặc ký tự.
2. Tách paragraph theo ký tự xuống dòng và giữ các đoạn trống. Hỗ trợ bullet `- ` và số `1. `/`1) ` bằng marker và hanging indent, tối đa hai cấp; ưu tiên giữ văn bản rõ khi bề ngang hẹp.
3. Lua 5.1 không tích hợp `utf8` module. Khi cắt chuỗi cần dùng điểm kết thúc UTF-8 hợp lệ; ưu tiên wrap nguyên từ, fallback cắt từng **codepoint** (chỉ sau kiểm tra boundary) khi không có khoảng trắng. Không cắt ngẫu nhiên `string.sub(text, 1, N)` nếu chứa dấu.
4. Cache `lines` theo `message_id`, độ rộng bubble, text revision và font preset; không wrap lại toàn bộ transcript mỗi `draw()`.
5. Bubble tối đa **84% W**, lề ngoài **6 px**, padding trong **5–6 px**, khoảng cách khối **6 px**. Bạn gửi: bên phải trên accent với `accentInk`; phản hồi: bên trái trên surface/ink; error dùng errorBg/error.
6. Reading mode bỏ bubble, lề **8 px**, header mỏng và vạch tiến độ trang. Chỉ dàn trang từ **dòng nguyên vẹn**, lưu offset của dòng đầu đang xem để reflow đúng chỗ khi đổi font hoặc sau khi dữ liệu thêm vào.
7. Những ca bắt buộc: 1 từ rất dài, câu Việt có dấu, Anh, đoạn trống, bullet/số, ký tự không có trong font, 50+ dòng, nội dung rỗng. Nếu font thiết bị không hỗ trợ Unicode đầy đủ, ghi kết quả rõ thay vì tuyên bố đã xử lý.

## 4. Skill: keypad + state machine đúng hợp đồng

`doc/ai/Keypad.md` quy định tên phím **chữ thường**: `up/down/left/right/ok/softleft/softright/clear/back/0..9/*/#`. Callback:

```lua
function engine.keypressed(key) end
function engine.keyreleased(key) end
function engine.pause() end
function engine.resume() end
```

Khi nhận sự kiện, chuẩn hóa `tostring(k):lower()`; state machine chỉ có **một** dispatcher. Xem/copy `templates/keypad-demo/src/keypad.lua` khi tạo wrapper để dùng hệ thống alias/held/fresh hiện có; đừng tự tạo bản thứ hai nếu template đã đáp ứng. `up/2`, `down/8`, `left/4`, `right/6`, `ok/5` có thể cùng một chức năng tùy state; **cấm** double-dispatch nếu host gửi nhiều mã cho một lần bấm. Trong `COMPOSE`, phím số dành cho text input nên không dùng alias menu. `softleft` hành động/menu, `softright` quay lại. `clear` xóa một ký tự khi đang soạn.

| State | D-pad | OK hoặc 5 | Soft-left | Soft-right | Shortcut tùy chọn |
|---|---|---|---|---|---|
| HOME | ↑↓ chọn | mở | chọn/options | thoát | số nếu không trùng alias |
| CHAT | ↑↓ cuộn | mở composer/action | viết/options | home | `7` đọc, `9` font |
| COMPOSE | điều khiển ký tự/con trỏ | chốt mục | gửi DEMO | hủy | digits T9, clear xóa |
| READING | ↑↓/←→ trang | hành động tin | options | chat | `9` font |
| SETTINGS | ↑↓ chọn/←→ đổi | chốt | lưu | home | — |

Hạn chế emulator ở snapshot tài liệu: `#` **không bơm ổn định** qua vỏ Studio → VXPEmu; không đặt chức năng cốt lõi chỉ ở `#`. Kiểm tra `templates/keypad-demo` và emulator hiện tại trước khi gán. Xóa bảng phím đang giữ khi `pause`, `resume`, `go(newScreen)`; chặn auto-repeat của gửi, retry và xóa dữ liệu.

## 5. Skill: UI Designer / Assets — khi nào nên dùng

LuaS30 Studio có UI Designer xuất dữ liệu vào `<project>/.luas30/ui_design.json` và Lua sang `<project>/ui_design.lua` (xem `studio/app/views/ui_designer/lua_export.py`). Chỉ `require("ui_design")` **sau khi đã export**; file được sinh tự động thì không chỉnh tay. `ui.draw("main")` có thể phù hợp trang tĩnh, còn chat động/scroll nên vẽ bằng `src/renderer.lua` và `src/text_layout.lua`.

UI Designer chỉ hỗ trợ hình chữ nhật trục thẳng của engine; rotate 90°/270° có thể chuyển kích thước nhưng không phải renderer tổng quát. Assets chỉ dùng khi cần; làm icon bằng primitive giảm dependency `has_images`. Nếu dùng ảnh/âm thanh: đặt trong `assets/` và kiểm tra `engine.has_images` / `engine.has_audio`; firmware/codec có thể khác thiết bị. Không mang palette **chrome** của Studio (`studio/app/ui/palette.py`) sang app; màu của game/app là dữ liệu nội dung khác nhau.

## 6. Skill: mock transport, lưu trữ và quyền riêng tư

- `transport_mock.lua`: dữ liệu có nhãn `[DEMO]`/`Mock`, không biểu diễn là phản hồi AI thật; chặn double-send và retry trùng.
- API `doc/reference/API.md` đã đối chiếu **không công bố HTTP/TLS bridge**; không gọi `engine.http`/`engine.network_*` tự nghĩ. Tích hợp mạng thành task mới sau khi đọc source và test bridge, xác thực HTTPS, idempotency, timeout.
- Không đóng gói API key, mật khẩu, token hoặc dữ liệu cá nhân vào mã/asset/log/screenshot/report. Nếu cần dùng AI thật, xử lý key phía server và xin chấp thuận trước khi gọi dịch vụ tính phí.
- Storage chỉ sau `engine.has_files`; dùng đúng `file_exists/read/write/delete` nếu khả dụng và xử lý lỗi/đầy bộ nhớ. Không mặc định có API chọn thẻ SD, tạo thư mục, rename hoặc sync cloud. Nếu RAM-only, UI phải ghi rõ lịch sử không bền vững.
- Audio/image chỉ bật theo capability; không có capability thì fallback primitive/im lặng thay vì crash. Không buộc người dùng xem splash và animation dài khi thiết bị chậm.

## 7. Skill: lệnh build/run đã kiểm chứng từ source

**Chạy từ thư mục root LuaS30-IDE trên Windows**; thay `C:\path\...` bằng đường dẫn thật, không chép nguyên vào code dự án:

```bat
REM A. Build không chạy emulator
build_only.bat "C:\path\to\Projects\MyApp"

REM B. Build và chạy chính VXP vừa tạo
build.bat "C:\path\to\Projects\MyApp"

REM C. Tương đương CLI: --project VÀ --toolchain đều bắt buộc
python tools\build.py --project "C:\path\to\Projects\MyApp" --toolchain "toolchain\arm-gcc" --compiler-profile auto --compat-profile auto --no-run
```

`--compiler-profile`: `auto|gcc|rvds|ads12`; `--compat-profile`: `auto|standalone|s30plus-native|nokia225-rm1011`. **Không có `--profile` cho profile JSON** trong script hiện đã rà soát. Chỉ dùng native/vendor-toolchain path khi môi trường và quyền truy cập thực sự cho phép; app UI thông thường giữ `auto`.

Kiểm tra `<project>/build/<ProjectName>.vxp`, `<project>/build/sync_manifest.json`, SHA-256 và báo cáo ELF/VXP sau build. Đây là **một VXP canonical chưa ký**; `--device-imsi` (nếu được cung cấp qua đường an toàn) chỉ sinh một bản phụ bind ở `build/device/`, **không ký** và không bảo đảm retail chấp nhận. Không tự gắn cờ `--cert100-key`/`--sign` hoặc tuyên bố tương thích Nokia 225 từ emulator.

**Chạy VXP đã build:**

```bat
python tools\run_emulator.py --vxp "C:\path\to\Projects\MyApp\build\MyApp.vxp" --sha256 <SHA256_VERIFIED> --manifest "C:\path\to\Projects\MyApp\build\sync_manifest.json"
```

`run_emulator.py` có `--vxp` **bắt buộc**, `--sha256`, `--manifest`, `--emulator`, `--keep-old` tùy chọn. Script kiểm hash rồi **khởi chạy**, không chụp màn hình tự động. Với AI Workbench hỗ trợ `/run` hoặc tool `run_app`, có thể dùng pipeline smoke có ảnh ở `<project>/build/smoke/`; chỉ tuyên bố có ảnh nếu lệnh trả về ảnh thật. Khi tự thử bấm phím, giao diện debug overlay hữu dụng hơn chỉ dùng `print()`, vì bản VXPEmu hiện có thể không nhận đường log firmware `print()`.

**Validator đúng phạm vi:**

- Code app: Lua 5.1 syntax/harness trên root project; kiểm `require("src.*")`, layout/token/key dispatcher, capability guards.
- Nếu **thay template/keypad của IDE**: chạy `python tools/validate_keypad_skill.py` và `py -3.12 tools/validate_project_templates_e2e.py` (lệnh thứ hai cần PySide6; Lua harness báo SKIP nếu thiếu Lua 5.1).
- Nếu **thay source IDE**, ở root IDE chạy `python tools/validate_tree.py`, `python tools/validate_native_sdk.py`, `python tools/validate_complete.py`. `validate_complete.py` còn đòi ARM toolchain/emulator được deploy; thiếu file phải ghi `NOT RUN`/`BLOCKED`, không ghi PASS giả.
- Tác vụ emulator: kiểm đúng path/hash trong `sync_manifest.json`; ảnh Home sáng/tối, Chat ngắn/dài, Reading, Compose, Settings, Error; thử giữ/thả và Back. Test `#` trên thiết bị thật nếu emulator hiện tại vẫn bị giới hạn.

**Ma trận xuất kết quả** (`PASS`, `FAIL` hoặc `NOT RUN` + log/ảnh/điều kiện):

| Gate | Nội dung |
|---|---|
| STATIC | cú pháp Lua 5.1, tên API, `require`, main root, token/font |
| INPUT | D-pad, 2/4/5/6/8 alias không double, softkeys, giữ/nhả, compose |
| VISUAL | hai theme, header/status, bubble <= 84%, 50+ dòng, reading |
| CAPABILITY | `has_files/images/audio` false đều có fallback |
| BUILD | toolchain preflight, VXP report, hash/manifest khớp |
| EMULATOR | đúng VXP vừa build; ảnh và điều khiển thực tế |
| DEVICE | test thật đúng SHA/firmware nếu có; nếu không `NOT RUN` |
| PERFORMANCE | FPS/RAM/GC/10 phút **chỉ** nếu có harness đo thật |

Khi báo cáo, tách bốn tầng: tĩnh → ARM build → VXPEmu → thiết bị vật lý; **không** dùng kết quả tầng trước để tự đánh dấu PASS tầng sau.

## 8. Handoff và các điều cấm

Bàn giao cần `TARGET/MODE`, `PATHS MODIFIED`, `DESIGN CHOICES`, `KEY MAP`, `VALIDATION COMMAND+EXIT`, `FINAL VXP+SHA`, `SCREENSHOTS OR NOT RUN`, `DEVICE STATUS`, `KNOWN ISSUES`. Nếu có thay đổi source IDE thật, nêu riêng; không âm thầm sửa global agent contract/IDE theme.

Không dùng tên/logo/đồ họa thương hiệu tham khảo cho app phân phối; không tự commit/push; không tạo ảnh/số đo/log hoặc tuyên bố tương thích từ suy đoán. Nếu cần tăng độ giống về **bố cục**, ưu tiên header, dòng menu 2 cấp, palette, bubble 84%, reading view và điều khiển phím thay vì chép pixel/logo của app gốc.
