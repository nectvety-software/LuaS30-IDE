# LuaS30 Studio Guide

## Layout

Studio dùng layout kiểu VS Code:

```text
Menu Bar
Activity Bar | Side Bar | Editor Area
             |          | Bottom Panel
Status Bar
```

## Explorer

Explorer là filesystem tree thật.

Hỗ trợ:

- expand/collapse folder;
- New File;
- New Folder;
- Rename;
- Delete;
- Open;
- Copy Path;
- Copy Relative Path;
- Reveal in File Explorer;
- Refresh;
- hide/show generated folders.

Ẩn mặc định:

```text
.git
.venv
__pycache__
.idea
.pytest_cache
```

Generated folders có thể ẩn:

```text
build
release
dist
```

## Code Editor

- multi-tab;
- dirty marker;
- save/save as/save all;
- Lua syntax highlighting;
- autocomplete Lua / `engine.*`;
- Find/Replace;
- minimap;
- inline diagnostics;
- Problems;
- Go to Definition;
- project-wide search;
- status line/column.

## Build

Build panel dùng pipeline thật qua `tools/build.py`. Build log được đưa vào bottom panel.

## Emulator

Run action phải mở đúng final VXP vừa build. Build/Run workflow dùng hash để giảm nguy cơ
emulator chạy nhầm artifact cũ.

## Assets

Asset workflow dùng để quản lý resource của project. Với S30+ nên ưu tiên:

- atlas;
- ảnh nhỏ;
- RGB565-friendly art;
- audio ngắn/mono;
- asset reuse.

## UI Designer

Designer tập trung màn hình nhỏ 240×320 (QVGA của Nokia S30+). Bố cục:

```text
[toolbar]  màn hình mới · lưu+xuất Lua · nhập ảnh · nhập âm thanh · hít dính · zoom
[MÀN HÌNH] combo chọn màn hình · [+] tạo mới · [⋮] đổi tên / nhân bản / xoá / mở thư mục
[breadcrumb]
[THÀNH PHẦN]  [canvas 240×320]  [INSPECTOR]  [LỚP · ID]
```

- **Canvas** — khung điện thoại 240×320, kéo-thả thành phần, hít dính căn chỉnh
  (đường xanh = thẳng hàng thành phần, đường vàng = thẳng với khung), zoom
  `Ctrl +/−`, giữ `Alt` khi kéo để tạm tắt hít dính.
  Khi đang kéo từ palette: khung màn hình sáng lên (nét liền — nơi sẽ nhận thành
  phần), bóng thành phần hiện ở đúng vị trí sắp rơi (nét gạch) kèm nhãn
  `x, y  w×h`. Thả ở đâu thành phần cũng bị kẹp nằm trọn trong khung.
- **THÀNH PHẦN** — 18 loại chia 3 nhóm (GIAO DIỆN / BỐ CỤC / ĐỒ HỌA) + ảnh và
  âm thanh quét từ `assets/` của project. Kéo vào canvas hoặc bấm để thêm.
- **INSPECTOR** — ID, vị trí, kích thước, màu tô, góc xoay, nội dung chữ.
- **LỚP · ID** — thứ tự lớp (trên cùng vẽ sau), đổi ID bằng kích đúp, nhân bản
  (`Ctrl+D`), xoay (`Ctrl+Shift+R`), đưa ra trước / ra sau (`Ctrl+Shift+↑/↓`).
- **Đa màn hình** — màn hình khởi động luôn là `main`, không đổi tên và không
  xoá được.

Tệp do designer ghi:

```text
<project>/.luas30/ui_design.json   nguồn sự thật — mọi màn hình (JSON)
<project>/ui_design.lua            sinh ra khi bấm "Lưu + xuất Lua"
```

`ui_design.lua` chứa cả dữ liệu lẫn bộ vẽ dùng API LuaS30, nên game dùng được ngay:

```lua
local ui = require("ui_design")

function engine.draw()
    ui.draw("main")
end

-- tra cứu thành phần theo ID; hit() dành cho cảm ứng
local item = ui.get("main", "btn_start")
local top = ui.hit("main", touch_x, touch_y)
```

Tài nguyên nhập qua designer được copy vào `assets/` của project (xem
`asset_import.py`) để engine nạp bằng đường dẫn tương đối project.

Giới hạn: `engine` của LuaS30 chỉ vẽ hình chữ nhật trục thẳng, không có phép
xoay. Thành phần có `rot` 90/270 được vẽ với chiều rộng/cao hoán đổi; góc khác
được vẽ như không xoay.

Cỡ icon của designer gom về một chỗ — `icons_compat.ICON` (16px),
`ICON_TOOLBAR` (20px), `BTN` (22px) — theo mật độ của VS Code: hàng palette
24px, hàng LỚP 20px, nút nhỏ 22×22. Pixmap glyph được render đúng cỡ hiển thị,
nên đổi cỡ ở đâu thì phải truyền cỡ đó xuống hàm `icons.icon_*` (render 16px
rồi để Qt phóng lên 20px sẽ ra icon nhoè).

## Settings

Settings nên chứa đường dẫn, target profile và build preferences; project-specific setting
nên ở `project.json`, không hard-code trong Studio.

## About

Top menu **About** có:

- About LuaS30 IDE;
- Environment;
- Credits;
- Paths.

Mục Credits phải đồng bộ với `doc/legal/THIRD_PARTY_NOTICES.md`.


## Theme & palette

Chuẩn thiết kế của Studio lấy từ hộp thoại **Cấu hình MediaTek MRE SDK**
(`studio/app/ui/mediatek_mre_dialog.py` + khối QSS `MREDialog*`): nền slate xanh
đêm (`#07101f` lõm / `#111827` mặt phẳng), viền `#273449`–`#334155`, chữ sáng
`#f8fafc`, accent **cam** `#f59e0b`, bo góc 8–12px, ô nhập cao 34px. Mọi bề mặt
khác của Studio được kéo về cùng bảng màu đó.

### Một nguồn màu duy nhất

```text
studio/app/ui/palette.py      <- nguồn sự thật, khai báo mọi màu
studio/app/ui/theme.py        <- QSS dùng @TOKEN, KHÔNG viết hex trực tiếp
```

`theme.py` viết QSS với placeholder `@TEN_TOKEN`; `_substitute()` thay bằng giá
trị trong `palette.py` ngay lúc import. Token lạ thì **raise lỗi ngay** — cố ý
fail-loud, vì Qt gặp khai báo sai sẽ âm thầm bỏ **toàn bộ** rule đó và giao diện
hỏng mà không có thông báo nào.

Thang nền đi từ lõm ra nổi:

```text
BG_INK -> BG_ALT -> BG_SURFACE -> BG_RAISED -> BG_HOVER -> BG_PRESSED
```

Muốn một vùng "sâu hơn" thì lùi về `BG_INK`, muốn "nổi hơn" thì tiến tới
`BG_PRESSED`. Ô nhập, editor, terminal, canvas dùng `BG_INK`; panel và dialog
dùng `BG_SURFACE`; menu/popup/toolbar dùng `BG_RAISED`.

Bo góc chỉ có **ba** giá trị: 6px (ô điều khiển), 8px (card), 12px (dialog).

### Màu chrome và màu nội dung — không được lẫn

Đây là quy tắc dễ vi phạm nhất khi sửa theme:

- **Màu chrome** là màu của chính IDE (nền, viền, chữ, nút, viền chọn thành
  phần, tay cuộn). Bắt buộc lấy từ `palette.py`.
- **Màu nội dung** là màu của *game* mà Studio đang vẽ hộ hoặc đang mô phỏng.
  Không được theo bảng màu IDE.

Các chỗ là màu nội dung, cố ý nằm ngoài palette:

```text
studio/app/editor/lua_highlighter.py     bảng màu cú pháp Lua
studio/app/views/ui_designer/lua_export.py   bảng màu game (sinh ra Lua)
studio/app/views/ui_designer/items.py    xem trước thành phần trong khung 240x320
studio/app/views/ui_designer/color_button.py  dữ liệu swatch màu
studio/app/views/ui_designer/properties_panel.py  DEFAULT_FILL của thành phần mới
```

Ví dụ cụ thể: `items.C_ACCENT = #007acc` là màu của nút/checkbox/progress/slider
**bên trong khung game**, phải khớp `lua_export.ACCENT`. Viền chọn thành phần,
tay nắm và ô xem trước thả thì dùng accent chrome `palette.ACCENT` (cam). Đổi
`C_ACCENT` sang cam là đổi màu game thật, không phải đổi theme.

Kiểm chứng nhanh quy tắc này: xuất `ui_design.lua` rồi soi màu trong đó — không
được có `#f59e0b`.

Trong `theme.py` và code Python, hex trực tiếp chỉ được phép nằm trong
`palette.py`. Ngoại lệ có chủ ý là bảng màu cú pháp `SYN_*` (giữ bảng VS Code
dark+ để code dễ đọc, đã đối chiếu đủ tương phản trên `BG_INK`).

### Đối tượng do Qt tự tạo

Một số điểm trên giao diện **không** do Studio vẽ ra, nên QSS không chạm tới
được. Ví dụ nút đóng tab: mặc định Qt dùng pixmap chuẩn
`QStyle::SP_TabCloseButton` — một dấu X nền đỏ, xuất hiện kể cả khi không nạp
stylesheet nào. Cách xử lý là **tự sở hữu widget** chứ không tô lại: xem
`StudioTabBar` / `_TabCloseButton` trong `studio/app/editor/editor_tabs.py`, tạo
nút riêng rồi `setTabButton()`, và style qua `QToolButton#TabCloseButton`.

Đừng cố sửa bằng `QTabBar::close-button { background: transparent; }` — nó xoá
được nền đỏ nhưng đồng thời làm mất vùng bấm và làm biến mất glyph.

### Nền của CHÍNH widget, không chỉ của subcontrol

QSS chỉ tô những gì được khai báo. Với widget có subcontrol, rất dễ chỉ style
phần tử con rồi tưởng đã xong:

```css
QHeaderView::section { background: @BG_INK; }   /* chỉ các SECTION có thật */
```

Vùng nằm **sau section cuối** (khi các cột cộng lại hẹp hơn bề rộng bảng) do
chính `QHeaderView` vẽ chứ không phải một `::section`, nên nó rơi về palette mặc
định — vốn là màu SÁNG, vì theme này dùng QSS thuần và **không** đặt dark
palette. Kết quả là một dải trắng bên phải hàng tiêu đề. Phải khai báo thêm nền
cho chính widget:

```css
QHeaderView { background: @BG_INK; border: 0; }
```

Đã gặp đúng lỗi này ở Project Hub: 7 cột cộng lại 1075px trong khi header rộng
1152px, thành dải trắng 77px cao 29px. Cùng họ lỗi nên rà cả `QTabBar`,
`QTableView`, `QTreeView`, `QListWidget`, `QScrollArea`: **nếu chỉ thấy
`::subcontrol` mà không có rule cho chính widget thì gần như chắc chắn còn sót
một vùng nền.**

### Kiểm tra

```text
QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
  py -3.12 -u tools/studio_theme_check.py
```

Thêm `--shots <thư_mục>` để lưu ảnh chụp màn hình, `--static-only` để chỉ chạy
phần kiểm tra tĩnh (không cần Qt).

Bốn nhóm kiểm tra:

- **A. tĩnh** — `theme.py` không còn hex trực tiếp; mọi `@TOKEN` đều giải được;
  bo góc chỉ còn 6/8/12; không còn `color: white|black`; mọi hex trong
  `studio/**/*.py` đều thuộc `palette.hex_set()` trừ danh sách `ALLOWLIST` (có
  ghi lý do cho từng file).
- **B. tương phản WCAG** — 14 cặp chữ/nền đạt tỉ lệ >= 4.5:1.
- **C. render offscreen** — dựng thật `MainWindow` và `MediaTekMREConfigDialog`,
  quét "khối sáng" để phát hiện vùng lọt theme sáng, kiểm tra hình học ô nhập và
  chữ trên nút không bị cắt. Nút `MRESaveButton` màu cam là vùng sáng **cố ý**,
  được khai báo miễn trừ bằng `ignore` rect — đừng nới ngưỡng sáng để né nó.
- **D. nút đóng tab** — nút phải là `_TabCloseButton` của Studio, không còn pixel
  X đỏ mặc định của Qt, và bấm vào phải thật sự đóng tab.

Harness chạy với `LUAS30_APPDATA` / `LUAS30_PROJECTS` trỏ vào sandbox tạm nên
không đụng vào cấu hình thật của người dùng.

`ignore` rect ở phần C khai báo theo **toạ độ logic** (hình học widget), còn
`widget.grab()` trả pixmap ở **độ phân giải thiết bị**: trên màn hình scale 125%
(`devicePixelRatio() = 1.25`), hộp thoại 560x509 cho ra pixmap 700x638. Vì vậy
`light_blocks()` phải quy đổi **cả lưới quét lẫn `ignore`** sang pixel thiết bị — nếu
không, vùng miễn trừ lệch khỏi vùng sáng thật và nút cam bị báo nhầm là rò theme sáng.
Lỗi này chỉ lộ ra khi chạy **thiếu** `QT_QPA_PLATFORM=offscreen` (nền tảng thật đọc mức
scale của hệ điều hành); chạy offscreen thì tỉ lệ là 1.0 nên trông vẫn xanh. Đừng "sửa"
bằng cách nới ngưỡng sáng — đó là bịt mắt guard.

Bộ `tools/validate_*.py` cũng phải xanh: các validator không được hard-code hex
(đó chính là nguồn gây lệch màu), mà phải so với `palette.*`.


## Font icons

LuaS30 Studio does not use emoji as toolbar/menu icons.

Icons are created at runtime from Windows system icon fonts through:

```text
studio/app/ui/icons.py
```

Font preference:

```text
Segoe Fluent Icons
Segoe MDL2 Assets
Segoe UI Symbol (fallback)
```

No icon font file is bundled with or exported from the engine package.


## Compact Workbench 1.7

The workbench removes duplicate pages and commands.

```text
Menu Bar
Compact Command Center
Activity Bar | Editor / Tool View
             | Integrated Bottom Panel
Status Bar
```

Canonical ownership:

- Activity Bar: Explorer, Search, Assets, UI Designer, Emulator, Settings.
- Bottom Panel: OUTPUT, BUILD, PROBLEMS.
- Run menu: build/emulator execution.
- Tools menu: Project Doctor, clean build and folder utilities, rerun first-run setup.
- First-run setup: ~0.8s after launch (first time or new version) Studio shows
  "Thiết lập LuaS30 IDE lần đầu" with per-component status
  (Đã có / Có thể cài tự động / Cần làm thủ công) and Bỏ qua / Kiểm tra lại /
  Tự động cài đặt buttons. Rerun anytime from Tools menu.
  Backed by `studio/app/services/environment_setup.py`; VC++ runtime installs
  via `tools/install_vc_runtime.py`. Never blocks IDE startup.
- Integrated terminal autostarts hidden in the background at launch
  (`autostart_background`, no focus steal, no Enter needed).
- About menu: documentation, environment and credits.

The former Dashboard, Projects, Build and standalone Console pages are not part of
the v1.7 workbench because they duplicated existing editor/project/build functions.

### Real execution services

`studio/app/services/build_service.py` invokes `tools/build.py` through QProcess,
streams real compiler/packer output into BUILD and reads the generated sync manifest.

`studio/app/services/emulator_service.py` invokes `tools/run_emulator.py` with the
manifest VXP path and expected SHA-256.

The Emulator view displays the actual VXP artifact/hash/process metadata; it no
longer shows a decorative fake device preview.

`Project Doctor` validates project.json, entry script, target profile, RAM/FPS
hints, asset payload and the SHA of the previous build.


## Tabbed Workbench 1.9

Studio uses one central editor tab strip for both files and tools, matching the behavior
of VS Code custom/editor tabs more closely.

```text
Activity Bar | Explorer/Search | Editor Tabs
                              |  main.lua
                              |  Project Storage
                              |  Assets
                              |  UI Designer
                              |  Emulator
                              |  Project Doctor
                              |  Runtime Compatibility
                              |  Toolchain Doctor
                              |  Settings
                              |
                              +-- OUTPUT / BUILD / PROBLEMS
```

Selecting an Activity Bar tool focuses its existing tab instead of creating duplicates.
Closing a tool tab releases that view; selecting the tool again recreates it.

The `Tools` top menu contains only features that open persistent tabs. Command-only
utilities such as Clean Build are kept under `Run`, while project/build-folder reveal
commands live under `File` or the Command Palette.

### Project Storage

`Project Storage` is backed by `Documents\LuaS30IDE` and provides real filesystem
operations:

- scan managed projects recursively;
- filter by project/path/App ID;
- create a new project through the engine template;
- import an existing LuaS30 project into managed storage;
- open a project;
- duplicate without generated `build/release` data;
- rename the project folder and `project.json` name;
- delete only verified managed LuaS30 project folders;
- reveal the selected project in the OS file explorer;
- show modified time, disk use, file count and latest VXP artifact.

Switching projects closes only source-file tabs after unsaved-change checks. Tool tabs
remain open and refresh their project context.
