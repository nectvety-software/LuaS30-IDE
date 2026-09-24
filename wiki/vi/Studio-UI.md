# Giao diện Studio

> **Ngôn ngữ:** Tiếng Việt · [English](../en/Studio-UI.md)

LuaS30 Studio dùng layout kiểu VS Code.

```text
┌──────────────────────────────────────────────────────────┐
│ Menu Bar + Command Center                                │
├──────┬──────────┬──────────────────────────────┬─────────┤
│ Act. │ Side     │ Editor Tabs                  │ Chat AI │
│ Bar  │ Bar      │  main.lua                    │         │
│      │ Explorer │  Project Storage             │         │
│      │ Search   │  UI Designer                 │         │
│      │          │                              │         │
│      │          ├──────────────────────────────┤         │
│      │          │ CONSOLE | BUILD | PROBLEMS   │         │
│      │          │ TERMINAL                     │         │
├──────┴──────────┴──────────────────────────────┴─────────┤
│ Status Bar                                               │
└──────────────────────────────────────────────────────────┘
```

Bottom panel bị giới hạn **vật lý** trong cột editor ở giữa, không tràn xuống
dưới sidebar ChatAI.

## Activity Bar

| Mục | Mở tab |
|---|---|
| Explorer | Cây file thật của project |
| Search | Tìm kiếm toàn project |
| Assets | Quản lý resource |
| UI Designer | Thiết kế màn hình 240×320 |
| Emulator | Trạng thái VXP và tiến trình |
| Settings | Cấu hình |

Mỗi mục mở/focus **một tab** trong dải tab editor. Chọn lại công cụ đang mở sẽ
focus tab có sẵn, không tạo tab trùng. Đóng tab công cụ thì chọn lại sẽ tạo mới.

Menu **Tools** chỉ chứa công cụ mở tab thật:

```text
Project Doctor
Runtime Compatibility Matrix
Toolchain Doctor
```

Lệnh chỉ chạy một lần (ví dụ Clean Build) nằm ở menu **Run**; lệnh mở thư mục
project/build nằm ở **File** hoặc Command Palette.

## Explorer

Explorer là filesystem tree thật, hỗ trợ:

- expand/collapse, New File, New Folder, Rename, Delete, Open;
- Copy Path, Copy Relative Path, Reveal in File Explorer, Refresh;
- ẩn/hiện thư mục generated.

Ẩn mặc định: `.git`, `.venv`, `__pycache__`, `.idea`, `.pytest_cache`.
Thư mục generated có thể ẩn thêm: `build`, `release`, `dist`.

## Code Editor

- multi-tab, dirty marker, save/save as/save all;
- Lua syntax highlighting, autocomplete Lua và `engine.*`;
- Find/Replace, minimap;
- inline diagnostics và tab Problems;
- Go to Definition, tìm kiếm toàn project;
- status line/column.

Nhấp chuột phải vào tab để **Close**, **Close Others**, **Close All Tabs**.
Close All áp dụng cho mọi editor group và vẫn hỏi trước nếu có file chưa lưu.

## Bottom Panel

```text
CONSOLE | BUILD | PROBLEMS | TERMINAL
```

| Phím | Tác dụng |
|---|---|
| `Ctrl+J` | Bật/tắt bottom panel |
| `Ctrl+Shift+Y` | Bật/tắt Console |
| ``Ctrl+` `` | Bật/tắt Terminal |
| ``Ctrl+Shift+` `` | Tạo terminal mới |

Đặc điểm:

- panel **ẩn mặc định** mỗi lần khởi động, kể cả lần trước đang mở;
- có nút đóng ở góc trên phải, mở lại thì trở về đúng phiên terminal cũ;
- ẩn Terminal **không** giết tiến trình shell;
- mở ở chiều cao gọn, kéo splitter để đổi, nhớ chiều cao nhưng không tự mở lại.

Terminal là shell thật, chạy trong thư mục project hiện tại (trên Windows dùng
`%COMSPEC%`/`cmd.exe`). Gõ lệnh **trực tiếp trên bề mặt terminal** sau prompt,
không có ô nhập riêng:

```text
C:\Users\user\Documents\LuaS30IDE\prj> python tools\build.py ...
```

| Phím | Tác dụng |
|---|---|
| `Enter` | chạy lệnh hiện tại |
| `Up` / `Down` | lịch sử lệnh |
| `Home` | về đầu lệnh đang sửa |
| `Ctrl+A` | chọn riêng lệnh hiện tại |
| `Ctrl+V` | dán vào lệnh hiện tại |
| `Ctrl+L` | xoá terminal |
| `Ctrl+C` | copy vùng chọn, nếu không có thì gửi ETX cho shell |

Output cũ được bảo vệ khỏi sửa nhầm. Panel tô màu output:

```text
đỏ      lỗi / thất bại
vàng    cảnh báo
xanh lá OK / PASS / success
cyan    lệnh / RUN
xanh dương BUILD / TOOLCHAIN / EMU / INFO
tím     tiêu đề mục
```

## Project Storage

Được backed bởi `Documents\LuaS30IDE` và thao tác filesystem thật:

- quét project được quản lý (đệ quy);
- lọc theo project / path / AppID;
- tạo project mới từ template của engine;
- import project LuaS30 có sẵn vào storage;
- mở project;
- nhân bản **không** kèm dữ liệu `build`/`release` sinh ra;
- đổi tên thư mục project và tên trong `project.json`;
- xoá **chỉ** thư mục project LuaS30 đã xác minh;
- Reveal trong file explorer của hệ điều hành;
- hiển thị thời gian sửa, dung lượng, số file và VXP mới nhất.

Khi chuyển project, chỉ **tab source** bị đóng (sau khi kiểm tra file chưa lưu).
Tab công cụ vẫn mở và tự refresh theo project mới.

## UI Designer

Designer tập trung vào màn hình nhỏ **240×320** (QVGA của Nokia S30+).

```text
[toolbar]  màn hình mới · lưu+xuất Lua · nhập ảnh · nhập âm thanh · hít dính · zoom
[MÀN HÌNH] chọn màn hình · [+] tạo mới · [⋮] đổi tên / nhân bản / xoá / mở thư mục
[breadcrumb]
[THÀNH PHẦN]  [canvas 240×320]  [INSPECTOR]  [LỚP · ID]
```

- **Canvas** — khung điện thoại 240×320, kéo-thả thành phần, hít dính căn chỉnh
  (đường xanh = thẳng hàng thành phần, đường vàng = thẳng với khung). Zoom
  `Ctrl +/−`, giữ `Alt` khi kéo để tạm tắt hít dính. Khi kéo từ palette, khung
  màn hình sáng lên (nét liền — nơi sẽ nhận thành phần) và bóng thành phần hiện
  ở vị trí sắp rơi (nét gạch) kèm nhãn `x, y  w×h`. Thả ở đâu thành phần cũng bị
  kẹp nằm trọn trong khung.
- **THÀNH PHẦN** — 18 loại chia 3 nhóm (GIAO DIỆN / BỐ CỤC / ĐỒ HỌA), cộng ảnh
  và âm thanh quét từ `assets/`. Kéo vào canvas hoặc bấm để thêm.
- **INSPECTOR** — ID, vị trí, kích thước, màu tô, góc xoay, nội dung chữ.
- **LỚP · ID** — thứ tự lớp (trên cùng vẽ sau), đổi ID bằng kích đúp, nhân bản
  (`Ctrl+D`), xoay (`Ctrl+Shift+R`), đưa ra trước / ra sau (`Ctrl+Shift+↑/↓`).
- **Đa màn hình** — màn hình khởi động luôn là `main`, không đổi tên và không
  xoá được.

File do designer ghi:

```text
<project>/.luas30/ui_design.json   nguồn sự thật (JSON, mọi màn hình)
<project>/ui_design.lua            sinh ra khi bấm "Lưu + xuất Lua"
```

`ui_design.lua` chứa cả dữ liệu lẫn bộ vẽ dùng API LuaS30:

```lua
local ui = require("ui_design")

function engine.draw()
    ui.draw("main")
end

local item = ui.get("main", "btn_start")
local top  = ui.hit("main", touch_x, touch_y)   -- dùng cho cảm ứng
```

Giới hạn: `engine` của LuaS30 chỉ vẽ hình chữ nhật trục thẳng, **không có phép
xoay**. Thành phần có `rot` 90/270 được vẽ với chiều rộng/cao hoán đổi; góc khác
được vẽ như không xoay.

## Emulator

Run action mở đúng **final VXP vừa build**. Build/Run dùng hash (SHA-256) để
tránh emulator chạy nhầm artifact cũ. Khi Run, panel tự mở tab `HEX` cho đúng VXP
trong sync manifest; HEX viewer phân trang 64 KiB, hiện offset + byte hex + ASCII.

> Emulator pass **không** thay thế test trên thiết bị thật.

### Vỏ máy giả lập

Cửa sổ giả lập được vẽ như một chiếc điện thoại: màn hình 240×320 ở giữa, **bàn
phím 21 phím** ở dưới, và một **rail icon dọc bên phải** (kiểu LDPlayer) gồm 7
công cụ — chạy/dừng, nạp `.vxp`, chụp màn hình, mở thư mục ảnh, quay video, xoay,
toàn màn hình.

Rail **chỉ hiện icon**; **rê chuột** lên một icon thì tên công cụ hiện trong bong
bóng bên cạnh. Icon đổi theo trạng thái thật (`play` ↔ `stop`, có viền nhấn khi
công cụ đang bật).

Trong thân máy có **hàng trạng thái**: dòng trên báo cửa sổ VXPEmu đã được nhúng
vào shell hay chưa, dòng dưới hiện `240×320 · 15 FPS`.

### Bàn phím trong emulator

**Rê chuột lên một phím** thì **tên phím** hiện ra ngay trên hàng trạng thái (tên
theo hợp đồng Lua: `up`, `softleft`, `ok`…), kèm chữ nhỏ nếu phím có (`2 · abc`).
Phím đang trỏ cũng sáng lên để bạn biết tên đó ứng với phím nào. Cách này được
chọn thay vì tooltip hệ điều hành vì tooltip trễ và có thể bị cửa sổ khác che.

**Phím giữ được.** Nhấn giữ một phím thì app nhận đúng trạng thái *đang giữ* —
`engine.keypressed` và `engine.keyreleased` thành cặp, bảng `held` trong
`keypad.lua` hoạt động thật.

> ⚠️ **Phím `#` không gửi được vào VXPEmu.** Đây là giới hạn của chính emulator,
> không phải lỗi cấu hình: nút `#` vẫn có trên vỏ máy nhưng bị **làm mờ** và chỉ
> chạy trên thiết bị thật. Xem [`doc/ai/Keypad.md`](../../doc/ai/Keypad.md) §6.

> ⚠️ **`print()` của Lua không hiện ở đâu** khi chạy trên VXPEmu. Muốn quan sát
> giá trị trong lúc chạy thì phải **vẽ lên màn hình**, đừng trông vào log.

Tài liệu chi tiết (kể cả các bẫy khi đo pixel offscreen):
[`doc/studio/EMULATOR_SHELL_FRAME_1_0_2.md`](../../doc/studio/EMULATOR_SHELL_FRAME_1_0_2.md).

## Settings

`Settings` chứa đường dẫn, target profile, compiler profile/toolchain root và
build preferences. Cấu hình riêng của project nằm ở `project.json`, không
hard-code trong Studio.

**Settings → Startup screen** có ba chế độ:

```text
Welcome        trang chào, quản lý project
Project Hub    Project Storage toàn màn hình
Empty Editor   mở editor trống, không mở file nào
```

Cả ba chế độ đều **không** khôi phục tab source khi khởi động; chỉ khôi phục
project, layout editor group, tab công cụ, tuỳ chọn Explorer/Activity Bar,
trạng thái bottom panel và layout cửa sổ.

## About

Menu **About** có bốn mục: **About LuaS30 IDE**, **Environment**, **Credits**,
**Paths**. Mục Credits đồng bộ với
[`doc/legal/THIRD_PARTY_NOTICES.md`](../../doc/legal/THIRD_PARTY_NOTICES.md).

Thông tin bản quyền **© Qeafivels All rights reserved.** và website
<https://qeafivels.com/> hiển thị ở đáy mọi tab của hộp thoại About.

## Theme & palette

Chuẩn thiết kế của Studio lấy từ hộp thoại **Cấu hình MediaTek MRE SDK**: nền
slate xanh đêm (`#07101f` lõm / `#111827` mặt phẳng), viền `#273449`–`#334155`,
chữ sáng `#f8fafc`, accent **cam** `#f59e0b`, bo góc 8–12px, ô nhập cao 34px.

### Một nguồn màu duy nhất

```text
studio/app/ui/palette.py   <- nguồn sự thật, khai báo mọi màu
studio/app/ui/theme.py     <- QSS dùng @TOKEN, KHÔNG viết hex trực tiếp
```

`theme.py` viết QSS với placeholder `@TEN_TOKEN`; `_substitute()` thay bằng giá
trị trong `palette.py` lúc import. Token lạ thì **raise lỗi ngay** — cố ý
fail-loud, vì Qt gặp khai báo sai sẽ âm thầm bỏ **toàn bộ** rule đó và giao diện
hỏng mà không có thông báo nào.

Thang nền từ lõm ra nổi:

```text
BG_INK -> BG_ALT -> BG_SURFACE -> BG_RAISED -> BG_HOVER -> BG_PRESSED
```

Ô nhập, editor, terminal, canvas dùng `BG_INK`; panel và dialog dùng
`BG_SURFACE`; menu/popup/toolbar dùng `BG_RAISED`. Bo góc chỉ có **ba** giá trị:
6px (ô điều khiển), 8px (card), 12px (dialog).

### Màu chrome và màu nội dung — không được lẫn

- **Màu chrome** là màu của chính IDE (nền, viền, chữ, nút, viền chọn, tay cuộn).
  Bắt buộc lấy từ `palette.py`.
- **Màu nội dung** là màu của *game* mà Studio đang vẽ hộ. Không theo palette IDE.

Ví dụ: `items.C_ACCENT = #007acc` là màu nút/checkbox bên trong khung game, phải
khớp `lua_export.ACCENT`. Đổi nó sang cam là đổi màu game thật, không phải đổi
theme. Kiểm chứng nhanh: xuất `ui_design.lua` rồi soi — không được có `#f59e0b`.

### Đối tượng do Qt tự tạo

Nút đóng tab mặc định do Qt vẽ (`QStyle::SP_TabCloseButton`, dấu X nền đỏ) và
xuất hiện cả khi không nạp stylesheet. Cách đúng là **tự sở hữu widget**
(`StudioTabBar` / `_TabCloseButton` trong `studio/app/editor/editor_tabs.py`),
không tô lại bằng `QTabBar::close-button { background: transparent; }` — cách đó
xoá được nền đỏ nhưng mất luôn vùng bấm và glyph.

### Nền của chính widget, không chỉ subcontrol

QSS chỉ tô những gì được khai báo. Nếu chỉ style `::section` mà không style chính
`QHeaderView`, vùng sau section cuối rơi về palette mặc định **sáng** và tạo dải
trắng. Cùng họ lỗi nên rà cả `QTabBar`, `QTableView`, `QTreeView`,
`QListWidget`, `QScrollArea`.

### Kiểm tra theme

```text
QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
  py -3.12 -u tools/studio_theme_check.py
```

Thêm `--shots <thư_mục>` để lưu ảnh chụp, `--static-only` để chỉ chạy phần kiểm
tra tĩnh (không cần Qt). Bốn nhóm kiểm tra: tĩnh, tương phản WCAG, render
offscreen (quét "khối sáng"), và nút đóng tab.

## Font icons

Studio **không** dùng emoji làm icon. Icon được tạo lúc chạy từ font hệ thống
Windows qua `studio/app/ui/icons.py`, theo thứ tự ưu tiên:

```text
Segoe Fluent Icons -> Segoe MDL2 Assets -> Segoe UI Symbol (fallback)
```

Không có file font icon nào được bundle hoặc xuất ra từ gói engine.

Xem thêm [`doc/studio/STUDIO_GUIDE.md`](../../doc/studio/STUDIO_GUIDE.md).
