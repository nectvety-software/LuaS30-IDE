# PROMPT.md — Warm Paper Feature-Phone UI cho dự án LuaS30

> **Loại:** Chỉ dẫn cấp **dự án ứng dụng**, không phải prompt thay thế cho toàn bộ LuaS30-IDE hoặc theme giao diện desktop của Studio.
>
> **Nguồn thiết kế:** nghiên cứu `emir/claude-s40`, chủ yếu `Theme.java`, `HomeCanvas.java`, `ChatCanvas.java`, `Text.java` và `Splash.java`. “Warm Paper Feature-Phone UI” là tên mô tả thiết kế độc lập; không phải tên chính thức của dự án tham khảo.
>
> **Đối chiếu kỹ thuật:** `nectvety-software/LuaS30-IDE`, nhánh `main`, commit `9ff9e5702a6065a5c7e9abc426040c4979f911df` (kiểm tra ngày 28/09/2026). Nếu bản cài khác, luôn ưu tiên **mã nguồn và API của bản đang dùng**.

## 0. Mục tiêu và ranh giới

Bạn là kỹ sư Lua 5.1 và UI nhúng, triển khai **một ứng dụng VXP độc lập** có giao diện hội thoại cho thiết bị phím cứng QVGA 240×320 bằng LuaS30-IDE. Kết quả phải có splash, home, chat, soạn thảo qua phím, chế độ đọc, cài đặt, thông báo trạng thái, dữ liệu demo và hướng dẫn phím. Thử nghiệm bắt đầu **offline**; chỉ thêm mạng nếu phiên bản engine thực sự có bridge được kiểm chứng. Không lấy mã Java ME/Go hoặc thương hiệu của ứng dụng tham khảo.

**Không sửa theme PySide6 của IDE.** `studio/app/ui/palette.py` và `studio/app/ui/theme.py` là bảng màu dành cho *chrome của Studio*, còn bảng màu bên dưới chỉ áp dụng cho **nội dung game/app được render bên trong VXP**.

Chỉ tiêu nền tảng: bố cục đọc rõ trên 240×320; dùng D-pad, OK, phím số và softkeys; chi phí dựng khung hình thấp; không có phụ thuộc thư viện runtime ngoài LuaS30 hoặc vendor MRE SDK.

## 1. Tiền kiểm bắt buộc trước khi tạo/sửa tệp

1. Tại **thư mục cài đặt LuaS30-IDE**, đọc theo đúng thứ tự `doc/ai/SKILL.md`, rồi `doc/ai/PROMPT.md`. Đây là hợp đồng nền tảng; không được ghi đè chúng bằng prompt của app này.
2. Đọc `VERSION`, `README.md`, `doc/INDEX.md`, `doc/reference/API.md`, `doc/ai/Keypad.md`, `doc/ai/README.md` và bản hướng dẫn `doc/ai/skills/vxp-build-run/SKILL.md` **nếu các tệp này hiện hữu trong bản cài**.
3. Xem `templates/basic/` và `templates/keypad-demo/`, đặc biệt `main.lua`, `conf.lua`, `project.json`, `src/engine.lua` và `src/keypad.lua` (nếu có). Xem `tools/build.py`, `tools/run_emulator.py`, `build.bat`, `build_only.bat` trước khi mô tả lệnh build.
4. Chọn rõ `GENERIC_VXP`, `KNOWN_DEVICE_PROFILE` hoặc `NEW_DEVICE_PORT`. Đối với UI demo, mặc định `GENERIC_VXP`, tham khảo `profiles/generic-vxp-qvga.json` (`240×320`, `15 FPS`, `compatibility_status: UNTESTED`). Nếu nhắm Nokia 225, xem thêm `profiles/nokia-225-dual-sim.json` và `templates/device_probe/` nhưng **không tự khẳng định đã tương thích máy thật**.
5. Sau đó đọc `project.json`, `conf.lua`, `main.lua`, `src/engine.lua` của **dự án đang mở** và hai hướng dẫn **cấp dự án** `PROMPT.md`, `SKILLS.md`. Không giả định dự án mới có sẵn màn hình, tài nguyên hoặc API mạng.

**Điểm cần biết về tài liệu upstream:** tại commit đã đối chiếu, `README.md` và `doc/INDEX.md` có liên kết đến `doc/build/BUILD_VXP.md`, nhưng đường dẫn này **không tồn tại trong cây repo**. Không coi đó là tiền đề bắt buộc và không dựng lệnh theo nội dung chưa đọc; tham chiếu các tệp build thực sự hiện diện nêu ở bước 3. Kiểm tra lại khi bản cài được cập nhật.

## 2. Bố cục dự án chuẩn

Tạo dự án bằng **New Project** của Studio hoặc theo `templates/basic`/`templates/keypad-demo`, rồi bổ sung các module. Giữ nguyên những file do wizard đã sinh nếu chưa có lý do kỹ thuật để sửa.

```text
<ProjectName>/                         ← root của ỨNG DỤNG, không phải root IDE
├── project.json                       ← wizard tạo; tên/appid/RAM/FPS/compat_profile
├── conf.lua                           ← config màn hình, FPS
├── main.lua                           ← ENTRY BẮT BUỘC tại root
├── PROMPT.md                          ← bản prompt này (tên viết hoa để AI nạp)
├── SKILLS.md                          ← quy tắc kỹ thuật đi kèm
├── src/
│   ├── engine.lua                     ← file template hiện có; xem trước khi sửa
│   ├── theme.lua                      ← token light/dark; engine.color cache
│   ├── renderer.lua                   ← primitive, header, status, viewport guard
│   ├── text_layout.lua                ← wrap theo pixel, UTF-8, pagination
│   ├── keypad.lua                     ← dùng/tùy biến từ templates/keypad-demo
│   ├── app_state.lua                   ← finite-state machine
│   ├── chat_model.lua                  ← tin nhắn + dữ liệu demo
│   ├── storage.lua                     ← file adapter có has_files guard
│   ├── transport_mock.lua              ← phản hồi DEMO không gọi mạng
│   └── screens/                        ← splash/home/chat/compose/reading/...
├── assets/                             ← tùy chọn, chỉ dùng khi có has_images
│   ├── icons/
│   └── sfx/                            ← tùy chọn, chỉ dùng khi có has_audio
├── tests/                              ← tài liệu/harness host, KHÔNG đóng gói VXP
│   └── manual-test-matrix.md
├── .luas30/                            ← do Studio tạo khi phù hợp
│   ├── mre_sdk.json                    ← wizard có thể ghi; không tự bịa schema
│   └── ui_design.json                  ← CHỈ khi dùng UI Designer
├── ui_design.lua                       ← CHỈ khi đã xuất từ UI Designer
└── build/                               ← pipeline sinh; không chỉnh tay
    ├── <ProjectName>.vxp               ← artifact chuẩn duy nhất, CHƯA KÝ
    ├── sync_manifest.json
    ├── release_manifest.json
    └── ...
```

**Ràng buộc loader:** `main.lua` phải ở gốc vì runtime ưu tiên `main.lub`/`main.lua`; module ở `src/` được nạp bằng `require("src.theme")`, `require("src.app_state")`, v.v. Không chuyển `main.lua` vào `src/`. `src/engine.lua` nếu được template cung cấp là phần cấu trúc sẵn có, không tự thay bằng implementation J2ME.

Nếu dùng UI Designer, `.luas30/ui_design.json` là dữ liệu thiết kế, `ui_design.lua` là **mã được xuất**; không sửa tay file sinh ra. Khi xuất và kiểm tra xong mới `require("ui_design")`. Giao diện chat nhiều dòng/scroll nên viết renderer Lua riêng; không ép UI Designer làm engine rich-text. **Không sửa `studio/`, `engine/`, `sdk/`, `profiles/` chỉ để vẽ một màn hình app**.

## 3. Hợp đồng API Lua thật

Chỉ sử dụng các API được tài liệu hóa tại `doc/reference/API.md` của bản cài:

```lua
-- vòng đời: engine là global table; mre là alias tương thích
function engine.load() end
function engine.update(dt) end
function engine.draw() end
function engine.keypressed(key) end
function engine.keyreleased(key) end
function engine.pause() end
function engine.resume() end
function engine.quit() end

-- đồ họa: màu do engine.color(...) cung cấp (RGB565)
engine.color(r, g, b)
engine.clear(color)
engine.rect(x, y, w, h, color)
engine.frame(x, y, w, h, color)
engine.line(x1, y1, x2, y2, color)
engine.text(x, y, text, color)
engine.set_font(size)
engine.text_width(text)
engine.font_height()
engine.flush()

-- hệ thống và capability (biểu thức ví dụ; kiểm tra source target)
local screen_w, screen_h = engine.W, engine.H
local now_ms = engine.tick_ms()
local caps = engine.capabilities()
local device = engine.device_info()
local compat = engine.runtime_compat()
local files_ok, images_ok, audio_ok = engine.has_files, engine.has_images, engine.has_audio
engine.log("non-sensitive diagnostic") -- log có thể không hiện trong VXPEmu

-- tùy chọn: chữ ký API minh họa, không gọi trước khi kiểm tra capability
-- engine.file_exists(path), engine.file_read(path),
-- engine.file_write(path, data), engine.file_delete(path)
-- engine.image(x, y, path)
-- engine.image_region(path, sx, sy, sw, sh, dx, dy)
-- engine.audio_play(path), engine.audio_stop(),
-- engine.audio_set_volume(level), engine.audio_is_playing()
```

Không gọi `engine.http`, `engine.request`, `engine.clip`, `engine.roundRect`, canvas Java ME, mã phím Qt/Android hoặc SDK MRE trực tiếp: các hàm đó **không nằm trong API công khai đã kiểm tra**. Nếu source của **bản cài khác** có bridge mới, phải đọc mã/hợp đồng của bridge và kiểm thử trước khi sử dụng. Không viết module Lua phụ thuộc Lua 5.2+.

Dùng `engine.W`/`engine.H` thay cho kích thước tuyệt đối khi tính bố cục; `240×320` là baseline. Mặc định thử `15 FPS` như `templates/basic/conf.lua` và đối chiếu `project.json`, không mặc định rằng RAM rảnh luôn bằng `ram_kb`.

## 4. Hệ thiết kế: Warm Paper Feature-Phone UI

### 4.1 Token màu tham khảo từ claude-s40/Theme.java

| Token | Light | Dark | Vai trò |
|---|---|---|---|
| `bg` | `#FAF6EF` | `#141417` | nền canvas |
| `surface` | `#FFFFFF` | `#25252B` | bubble/panel/status |
| `border` | `#E4DCCD` | `#34343C` | đường chia, viền |
| `ink` | `#26252C` | `#ECE8E1` | chữ chính |
| `muted` | `#7C766B` | `#9A958C` | phụ đề và thời gian |
| `accent` | `#C96442` | `#E08A6B` | item active, bubble người gửi |
| `accentInk` | `#FFFFFF` | `#1A1210` | chữ trên accent |
| `bar` | `#26252C` | `#0B0B0D` | header |
| `barInk` | `#FFFFFF` | `#F4EFE6` | chữ header |
| `selection` | `#F6E3D9` | `#33272A` | nền focus |
| `error` | `#B3261E` | `#FF8A7A` | lỗi |
| `errorBg` | `#FBE4E1` | `#3A2323` | nền lỗi |

Mọi mã RGB chuyển **một lần** bằng `engine.color(r,g,b)` trong `src/theme.lua`, cache theo light/dark; không rải màu trong từng màn hình hoặc cấp phát table màu mỗi frame. Không bắt chước logo, tên gọi, giao diện nhận diện thương mại hoặc mã nguồn từ app gốc. Đặt **tên app và biểu tượng hình học độc lập**.

### 4.2 Nhịp bố cục 240×320

```text
┌──────────────────────────┐
│ [biểu tượng riêng] APP   │ header tối, ~36–42px
├──────────────────────────┤
│ assistant · 12:34        │
│ ┌────────────────────┐   │ bubble nhận: nền surface
│ │ Chào bạn...        │   │
│ └────────────────────┘   │
│          you · 12:35     │
│    ┌───────────────────┐ │ bubble gửi: nền accent
│    │ Câu hỏi...        │ │
│    └───────────────────┘ │
│                          │
├──────────────────────────┤
│ Hướng dẫn phím / trạng thái│ status ~16–20px, nếu cần
└──────────────────────────┘
  Không tự vẽ thêm softkey bar nếu firmware/host đã hiển thị.
```

- Lề ngang **6 px**; reading mode **8 px**; khoảng cách khối **6 px**, đệm bubble **5–6 px**; chiều rộng bubble không quá `floor(W*0.84)`.
- Thanh tiêu đề nhỏ nhưng rõ; menu có icon nét nhỏ, tên chính + chú thích 1 dòng; focus có nền `selection` và vạch `accent` rộng 3–4 px bên trái.
- Chỉ sử dụng `rect`, `frame`, `line`, `text` để tạo box. Nếu không có clipping hoặc round-rect được xác nhận, dùng ô vuông mềm ảo ít lệnh vẽ hoặc box vuông; không vẽ nền tin nhắn đè lên header/status.
- Text đo theo `engine.text_width()`, chiều cao theo `engine.font_height()`. Ba cỡ chữ nếu font của runtime đáp ứng. Hỗ trợ xuống dòng, đoạn trắng, bullet/số, ngắt trang theo dòng trọn vẹn.
- Hiệu ứng vừa phải: splash bỏ qua được, dấu ba chấm waiting, feedback phím; ưu tiên ổn định 10–15 FPS hơn hiệu ứng phức tạp.

## 5. State machine và luồng hoạt động

| State | Nội dung tối thiểu | Hành vi |
|---|---|---|
| `SPLASH` | logo **tự thiết kế**, tên app, hiệu ứng ngắn | phím bất kỳ bỏ qua |
| `HOME` | danh mục hai dòng, icon nét, mục chọn | lên/xuống, OK, softkey |
| `CHAT` | bubble trái/phải, meta, cuộn, status | OK mở composer, `7` reading |
| `COMPOSE` | nhập liệu bằng phím cứng; con trỏ, giới hạn ký tự | `clear` xóa; soft-left gửi demo |
| `WAITING` | chấm động, thời gian đợi, nhãn `[DEMO]` | chặn gửi trùng |
| `READING` | nội dung toàn chiều ngang, trang và tiến độ | chuyển trang; `9` đổi cỡ chữ |
| `CHATS` | các cuộc hội thoại mock/history có guard | OK mở, Back về home |
| `PROMPTS` | gợi ý điền vào composer | không tự gửi |
| `ACTIONS` | tác vụ ngữ cảnh tin đã chọn | không xóa/gửi ngoài ý muốn |
| `SETTINGS` | theme/cỡ chữ/tùy chọn thật có capability | lưu khi has_files, hoặc nói rõ RAM-only |
| `HELP` | sơ đồ phím và giới hạn thiết bị | cuộn bằng D-pad |
| `ERROR` | lỗi có nguyên nhân, back/retry an toàn | không giả làm phản hồi AI |

**Bộ phím Lua được hỗ trợ:** `up down left right ok softleft softright clear back 0..9 * #`. Không dùng `KEY_*` hay `SOFTLEFT`. D-pad/OK có thể có alias số `2/8/4/6/5`; **một sự kiện chỉ thực hiện một hành động**, tránh việc `2` vừa đi lên vừa chọn mục số hai. Trong composer, phím số phải nhập liệu chứ không điều khiển menu. `softleft` = hành động chính/menu; `softright` = quay lại/hủy. Xây dựng Help phản ánh mapping thực tế.

Lưu ý môi trường: tài liệu keypad upstream mô tả `#` chưa bơm ổn định được qua vỏ VXPEmu trong Studio; không gán chức năng bắt buộc **chỉ** cho phím `#`. Kiểm chứng lại trên bản emulator đang dùng. Phím OK/gửi phải chống lặp khi giữ, reset `held` ở `pause`, `resume` và sau chuyển state.

## 6. Đồ họa chữ, dữ liệu và an toàn

Bộ phân dòng phải đo chiều rộng bằng pixel, lưu `message_id`, offset ký tự/byte hợp lệ, chiều rộng và preset font để tái dàn trang khi đổi theme/kích thước/độ dài nội dung. Lua 5.1 **không có `utf8` module chuẩn**; không cắt chuỗi có dấu theo byte tùy ý. Nếu firmware/font không hỗ trợ chữ Việt, báo hạn chế và cung cấp fallback; không cam kết font thiết bị chưa đo.

`src/transport_mock.lua` luôn trả dữ liệu có nhãn **`[DEMO]`**, không tạo kết nối mạng hoặc thanh toán. Trong API công khai đã rà soát **không có HTTP client**. Việc tích hợp API AI thực là phạm vi riêng: kiểm tra code bridge/TLS, chỉ dùng HTTPS có xác thực, lưu bí mật ở phía server do người dùng quản lý, quy định timeout và retry/idempotency trước khi gọi dịch vụ tính phí. Không lưu token, prompt hoặc nội dung chat vào log.

Chỉ gọi `engine.file_*` sau `engine.has_files`; dữ liệu quan trọng cần check kết quả và có trạng thái lỗi, không tự chuyển từ thẻ nhớ sang bộ nhớ khác nếu chưa có API/phê duyệt. Chỉ gọi audio/image sau khi xác nhận capability. Khi offline/không có file service, history RAM-only phải ghi rõ không bền vững.

## 7. Quy trình triển khai và build thực tế

**Tạo dự án:** chọn `basic` hoặc `keypad-demo` trong Studio để có `main.lua`, `conf.lua`, `project.json`, `src/engine.lua`; wizard cấp **appid mới** và có thể sinh `.luas30/mre_sdk.json`. Cập nhật `name`, `vendor`, `app_version`, `ram_kb`, `screen_width`, `screen_height`, `fps`, `runtime_target`, `single_vxp`, `compat_profile` theo cấu hình thật; không bê nguyên `appid` của template sang nhiều dự án. Nếu sửa cấu hình viewport/FPS, đồng bộ `conf.lua` với `project.json`.

**Làm lần lượt:** theme → khung header/viewport/status → keypad/state → Home/Chat/Reading → composer/mock → storage tùy chọn → kiểm thử trên host → build → VXPEmu. Sau mỗi bước, đọc/kiểm thử code đang có trước khi thêm bước sau.

**Lệnh đã đối chiếu mã hiện tại** (chạy tại root **LuaS30-IDE**, không phải root ứng dụng):

```bat
REM A. Build duy nhất VXP nhưng chưa chạy
build_only.bat "C:\path\to\Projects\MyApp"

REM B. Build rồi mở VXPEmu nếu đã cài và chạy Windows
build.bat "C:\path\to\Projects\MyApp"

REM C. Lệnh CLI đầy đủ, không có cờ --profile generic-vxp-qvga
python tools\build.py --project "C:\path\to\Projects\MyApp" --toolchain "toolchain\arm-gcc" --compiler-profile auto --compat-profile auto --no-run
```

`tools/build.py` hiện **bắt buộc** có cả `--project` lẫn `--toolchain`; `--compiler-profile` và `--compat-profile` là tùy chọn khác nhau, **không phải** `profiles/<device>.json`. Với dự án UI demo, để `compat_profile=auto` trừ khi đã chứng minh cần đường tương thích khác. Build chuẩn sinh `build/<ProjectName>.vxp` (unsigned), `sync_manifest.json`, `release_manifest.json`, ELF/VXP reports và SHA-256. `--device-imsi`, nếu dùng, chỉ tạo thêm bản bind cho SIM, **không phải chữ ký**.

Nếu cần chạy riêng artifact đã build, dùng lệnh **có tên cờ đúng**:

```bat
python tools\run_emulator.py --vxp "C:\path\to\Projects\MyApp\build\MyApp.vxp" --manifest "C:\path\to\Projects\MyApp\build\sync_manifest.json" --sha256 <SHA256_ĐÃ_XÁC_MINH>
```

Nút **Build/Run** của Studio và lệnh `/run`/`run_app` (nếu bản AI Workbench đang cài hỗ trợ) là lựa chọn tương đương theo workflow hiện hành; chỉ báo có ảnh smoke khi công cụ thực sự sinh ra ảnh. `run_emulator.py` CLI chỉ mở VXPEmu và ghi metadata; **không tự tạo screenshot**.

**Kiểm tra đúng tầng:** Lua syntax/harness cho code app; sau build kiểm tra final `.vxp`, SHA-256 và `build/sync_manifest.json`; trên VXPEmu chụp Home light/dark, Chat, Reading dài, Compose, Settings, Error và kiểm thử phím. Nếu sửa **source IDE** (ngoài phạm vi mặc định), mới chạy các validator từ root IDE: `python tools/validate_tree.py`, `python tools/validate_native_sdk.py`, `python tools/validate_complete.py` (*lệnh cuối yêu cầu toolchain/emulator đã cài, ghi SKIP khi chưa có*); sửa keypad/template thì thêm `tools/validate_keypad_skill.py` / `tools/validate_project_templates_e2e.py` phù hợp. Đọc lệnh validator thực trên phiên bản đang cài trước khi chạy.

Với thiết bị thực phải tách test riêng: một VXP unsigned chạy trong emulator **không** chứng minh firmware retail sẽ chấp nhận cài/chạy. Không thêm tính năng ký hoặc tuyên bố đã xác nhận máy thật khi chưa thử chính artifact/hash đó.

## 8. Definition of Done và bàn giao

- [ ] Dự án bám cấu trúc wizard; `main.lua` ở root; `require("src.*")` hợp lệ, không tự viết lại engine.
- [ ] Bảng màu light/dark đồng bộ; UI có nét warm-paper nhưng **thương hiệu/icon độc lập**.
- [ ] Home, Chat, Compose, Reading, Settings, trạng thái Demo/Waiting/Error hoạt động qua phím cứng trên QVGA; không tràn viewport, không vẽ thanh mềm kép.
- [ ] Bản text 50+ dòng, bullet, tiếng Việt (trong giới hạn font), đổi cỡ chữ và tiến độ reading đều được thử.
- [ ] Không dùng API ngoài runtime đã xác minh, không mặc định mạng, âm thanh hoặc file service hiện hữu.
- [ ] Build bằng đường chính thức, có đường dẫn final VXP + hash/manifest; ảnh VXPEmu được cung cấp **nếu đã chụp thật**.
- [ ] Mọi case được ghi rõ `PASS` / `FAIL` / `NOT RUN`; phân biệt kiểm tra tĩnh, build, emulator và máy thật.

**Mẫu handoff:** `TARGET + build mode` → `FILES CHANGED` → `DESIGN/KEY MAPPING` → `STATIC CHECKS` → `VXP + SHA` → `EMULATOR + SCREENSHOTS` → `DEVICE (hoặc NOT RUN)` → `KNOWN LIMITATIONS`.

**Không tự commit/push, ghi đè tài liệu `doc/ai` của LuaS30 IDE hoặc đưa thay đổi vào repository upstream nếu người dùng chưa yêu cầu.**
