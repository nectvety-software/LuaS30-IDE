# Changelog — LuaS30 IDE

Mọi thay đổi đáng chú ý của IDE, engine và Studio. Dạng tóm tắt
(Keep a Changelog); chi tiết đầy đủ của từng bản nằm trong
[`doc/release/changelog/`](doc/release/changelog/) và
kết quả kiểm tra tương ứng trong [`doc/release/validation/`](doc/release/validation/).

Phiên bản phát hành Studio là `VERSION` (hiện là **1.0.1**); các mốc
1.x bên dưới là dòng tính năng của engine/workbench được giữ nguyên
theo tên tệp tài liệu gốc.

## [1.0.1] — 2026-09-19 · Studio chrome VXPEngine

- Port giao diện VXPEngine 1:1 vào `studio/app/vxpui/`: cửa sổ frameless
  với `CustomTitleBar` (menu bar nhúng), họ `CustomDialog`,
  `WindowStateController`, edge-resize thủ công — lõi Lua giữ nguyên.
- Icon không còn phụ thuộc QtAwesome lúc chạy packaged: fallback glyph
  Segoe MDL2 / Fluent (`app/ui/icons.py` + `app/vxpui/icons.py`).
- Panel THIẾT BỊ · VXPEMU chuyển thành hộp thoại application-modal mở từ
  menu "Công cụ" (Ctrl+Alt+D); đóng = ẩn để EmulatorView không bị phá huỷ.
- `AssetsStudioWindow`: cửa sổ top-level riêng kiểu Photoshop
  (Ctrl+Alt+U) gộp Assets + UI Designer, có title bar/menu/geometry riêng.
- Hộp thoại modal "TÀI NGUYÊN · ASSETS" (Ctrl+Alt+R): chọn ảnh chèn thẳng
  vào canvas hoặc import tệp — palette THÀNH PHẦN đồng bộ ngay để kéo-thả.
- CHAT AI là cột phải của workspace theo đúng mô hình panel Chat của
  VS Code (Ctrl+Alt+I), không còn nằm trong hộp thoại thiết bị.
- `AIChatView` dựng lại theo ảnh mẫu: header "AI Trợ lý", tab đoạn
  Chat/Context/Tools, welcome card + lưới 6 nút hành động nhanh, thẻ
  "Ngữ cảnh" và composer bo góc với pill model + nút gửi cyan.
- Vùng soạn thảo đồng bộ ảnh mẫu: thêm `ActivityBar` 46px bên trái
  (Explorer · Search · Console · Chat AI · Cài đặt), header Explorer
  động "EXPLORER - <TÊN DỰ ÁN>", tab mã có icon theo loại tệp + vạch
  accent cyan trên tab đang mở, status bar thêm badge `UTF-8` và
  `Spaces: 4`.
- Chuẩn tiện ích mở rộng mới: mọi thư mục `extensions/<id>/` có
  `extension.json` được `ExtensionService` tự phát hiện, hiện động trong
  menu "Công cụ → Tiện ích mở rộng", mở thành tab công cụ
  `extension:<id>` (lưu/restore qua workspace session).
- Trang "Cửa hàng tiện ích mở rộng" (`ExtensionMarketView`) dạng card nền
  tối theo ảnh mẫu: ô icon bo góc, tên, mô tả hai dòng, hàng
  "from · version · added", nút `+` mở tiện ích; tab `extensions-market`
  được lưu lại giữa các phiên.
- `ExtensionHostView`: host QWebEngineView + cầu nối QWebChannel
  `window.luaS30` (extension/project/notify/writeFiles); ghi tệp bị giới
  hạn trong thư mục dự án, chặn `..`, tên tuyệt đối, tệp bí mật; trang
  nhận sự kiện `luas30-bridge-ready`.
- `sprite-sheet.html` → extension chuẩn đầu tiên
  `extensions/sprite-sheet/` (manifest + `ui/index.html` + `SKILLS.md`),
  bổ sung nút "Ghi vào dự án (PNG + atlas.json)" xuất thẳng sprite vào
  `assets/sprites/` của dự án đang mở.
- ChatAI chuyên Lua S30+ MRE VXP: thêm công cụ đọc-lõi `engine`
  (read/list/glob/grep trong templates·sdk·engine·compat·doc/ai·extensions),
  ngữ cảnh nhúng `<installed_extensions>` + `<engine_core>` (ranh giới
  Lua→C thật: `engine.lua` wrapper mỏng quanh bảng `engine` đăng ký trong
  `engine/src/runtime_lua.c`), SKILLS.md của extension được nạp làm luật
  agent, system prompt yêu cầu kiểm chứng API bằng tool `engine` thay vì
  giả định hàm mobile-Lua/love2d.
- Sửa resolve màu icon, pipeline build UTF-8 và khôi phục đường dẫn
  toolchain (commits 71e0c25, 0cf75b9).


## 1.15.0 — AI Workbench v1

- Added AI access selector under the ChatAI prompt.
- Added Ask before changes, Edit automatically, Plan mode and Full access modes.
- Kept sensitive/dangerous shell commands confirmation-gated in Full access.
- Replaced inline provider drawer with a custom AI Provider Settings dialog.
- Added Test Connection, Apply and Save & Close provider actions.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_15_0.md) (+11 mục khác)

## 1.15.0 · Agent Editor Fix — AI Agent Editor Apply Fix

- AI providers that ignore the `luas30-edit` protocol and return a normal fenced source block can now be recovered into an edit proposal for the active project file.
- Generated source no longer has to remain only in the Chat transcript when the request clearly asks to create, fix, update, refactor, or otherwise modify code.
- `Ask before changes` keeps the recovered edit pending for review/apply.
- `Edit automatically` and `Full access` continue through the existing automatic apply pipeline, writing the project file and refreshing any open editor buffer.
- Explanation/review prompts are excluded from fallback recovery to avoid accidental file replacement.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_15_0_AGENT_EDITOR_FIX.md) (+3 mục khác)

## 1.14.0 — AI Agent Activity + Shell

- Added collapsible AI Activity / Reasoning Summary panel.
- Added explicit policy against raw/private chain-of-thought display.
- Added `luas30-summary` response protocol.
- Added `luas30-shell` JSON action protocol.
- Added Shell access modes: Disabled, Ask, Auto Safe.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_14_0.md) (+8 mục khác)

## 1.13.0 — MediaTek MRE Project Wizard

- Replaced the old one-line New Project name prompt with a custom MediaTek MRE SDK modal.
- Added APPNAME, APPVER and VENDOR fields.
- Added screen-resolution preset selection.
- Added MTK6260, MTK6261, MTK6250 and MTK6225 presets.
- Added Heap RAM presets with chipset-specific recommended defaults.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_13_0.md) (+7 mục khác)

## 1.12.0 — Series 30+ High Compatibility

- Added S30+ compatibility profiles: auto, standalone, s30plus-native, nokia225-rm1011.
- Added native MRE SDK layout detection.
- Added ARM GCC high-compatibility MRE compile defines.
- Added native linking against local MRE SDK per*.a libraries and SDK scat.ld.
- Added explicit `vm_main()` application entry.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_12_0.md) (+8 mục khác)

## 1.11.0 — AI Workbench

- Added tab right-click Close / Close Others / Close All Tabs.
- Close All Tabs reaches every editor group.
- Rebuilt workbench as Explorer | center editor | ChatAI.
- Compact Bottom Panel is now center-only.
- Added ChatAI secondary sidebar and Ctrl+Alt+I.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_11_0.md) (+5 mục khác)

## 1.10.3 — Colored Panel / HEX / Unique AppID

- Added semantic colors to Console and Build log output.
- Added colored direct-terminal prompt/output.
- Added HEX tab to Compact Bottom Panel.
- Added 64 KiB paged VXP hex viewer with offset/hex/ASCII columns.
- Run/Emulator automatically loads and selects the exact manifest VXP in HEX.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_10_3.md) (+5 mục khác)

## 1.10.2 — Direct Integrated Terminal

- Removed the separate terminal command QLineEdit.
- Added `TerminalSurface`, a direct-edit QPlainTextEdit.
- Commands are typed directly after the cwd prompt.
- Protected terminal history from normal edits.
- Added Up/Down command history in the terminal surface.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_10_2.md) (+6 mục khác)

## 1.10.1 — Compact Bottom Panel

- Bottom Console/Build/Problems/Terminal panel is hidden on every startup.
- Terminal toggle opens/focuses the panel and hides it when invoked again.
- Added top-right Close Panel button.
- Hiding Terminal does not kill its QProcess shell.
- Added compact 145 px default reveal height and 72 px minimum.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_10_1.md) (+4 mục khác)

## 1.10.0 — Multi-Toolchain MRE Profiles

- Added `tools/toolchain_profiles.py`.
- Added ARM GCC, RVDS/RVCT and ARM ADS1.2 compiler profiles.
- Added `--compiler-profile auto|gcc|rvds|ads12`.
- Added `--entry-symbol` override.
- Added nested toolchain detection for gcc/readelf, armcc/armlink/fromelf and tcc.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_10_0.md) (+9 mục khác)

## 1.9.8 — Startup Screen Setting

- Added Settings -> Startup screen.
- Added Welcome startup mode.
- Added Project Hub startup mode.
- Added Empty Editor startup mode.
- Empty Editor restores project/layout but restores no file, untitled or tool tabs.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_8.md) (+4 mục khác)

## 1.9.7 — MRE GCC Build Fix

- Fixed literal `\n` being written into generated GCC probe C source.
- Fixed the same probe-source bug in `toolchain_doctor.py`.
- Added shared MRE GCC compile/link flag definitions.
- Added `MRE`, `GCC` and `__MRE_COMPILER_GCC__` compile defines.
- Preflight now verifies GCC driver, cc1, assembler and the MRE-style linker path.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_7.md) (+3 mục khác)

## 1.9.6 — Clean Startup Tabs

- Startup/restart no longer reopens source file tabs.
- Startup/restart no longer recreates untitled editor tabs.
- Removed automatic `main.lua` fallback during workspace restore.
- Session save filters file/untitled tabs from startup state.
- Older session files containing document tabs are accepted, but those entries are skipped.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_6.md) (+2 mục khác)

## 1.9.5 — Explorer / Activity Bar Toggles

- Added Workbench Bar Explorer button.
- Added Workbench Bar Activity Bar button.
- `Ctrl+B` toggles Explorer / Primary Side Bar.
- `Ctrl+Alt+A` toggles Activity Bar.
- Both actions are in View and Command Palette.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_5.md) (+2 mục khác)

## 1.9.4 — Project Hub Clean Layout

- Welcome and Project Storage now use a clean full-width central layout.
- Activity Bar is hidden on Project Hub pages.
- Explorer/Search sidebar is hidden on Project Hub pages.
- Find/Replace bar is hidden on Project Hub pages.
- Console/Build/Problems/Terminal bottom panel is hidden on Project Hub pages.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_4.md) (+3 mục khác)

## 1.9.3 — Integrated Terminal / Console

- Added real integrated Terminal based on QProcess.
- Added Console and Terminal toggle actions in View.
- Added top-level Terminal menu with New/Kill/Clear actions.
- Added Ctrl+J panel toggle, Ctrl+Shift+Y Console toggle, Ctrl+` Terminal toggle and
- Bottom panel is hidden by default in a new workspace.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_3.md) (+3 mục khác)

## 1.9.2 — Welcome / Project Hub

- Added VS Code-like `Welcome` startup tab.
- Welcome opens at tab index 0 of editor group 0.
- Added New Project, Open Folder, Import into Storage and Manage Storage start actions.
- Added Recent project list backed by managed Project Storage.
- Added Project Storage count/size/build summary and current-workspace card.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_2.md) (+5 mục khác)

## 1.9.1 — Workspace Session Restore

- Added automatic VS Code-like workspace session persistence.
- Added real multi-group editor workspace with horizontal editor groups.
- Added View → Split Editor Right and Close Editor Group.
- Restores current project, open source/tool/untitled tabs, tab order, active tab and active group.
- Restores editor-group splitter sizes.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_1.md) (+5 mục khác)

## 1.9.0 — Tabbed Workspace + Project Storage

- Removed whole-workspace switching for Assets, Designer, Emulator and Settings.
- Source files and persistent tools now share one closable/movable editor tab strip.
- Added keyed tool tabs so opening a feature focuses the existing instance.
- Added Toolchain Doctor as a real tab backed by `toolchain_doctor.py`.
- Project Doctor and Runtime Compatibility Matrix now open result tabs.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_0.md) (+11 mục khác)

## 1.8.4 — Portable ARM GCC Compile Fix

- Fixed portable ARM GCC child backend/DLL lookup on Windows.
- Build process now prepends bundled `arm-gcc/bin` and `arm-none-eabi/bin` to its local PATH.
- Added automatic GCC driver/cc1/assembler compile preflight.
- Added `tools/toolchain_doctor.py`.
- Build failures now include compiler stderr in the raised error message.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_4.md) (+2 mục khác)

## 1.8.3 — Runtime Compatibility Matrix

- Added `compat/runtime_abi_contract.json`.
- Added per-firmware MRE symbol manifests under `compat/mre/`.
- Added host-side runtime compatibility evaluator.
- Matrix rows report native/effective capabilities, selected ABI aliases, activated
- Added JSON, CSV and text matrix reports.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_3.md) (+4 mục khác)

## 1.8.2 — Runtime Compatibility Layer

- Added `ls30_compat_report` and compatibility levels: full/degraded/incompatible.
- Added native-vs-effective capability detection.
- Added conservative same-signature ABI alias resolution and alias hit reporting.
- Added safe fallbacks for graphics helpers, text metrics, resource init, file commit,
- Added software line/fill fallbacks so firmware only needs one basic primitive.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_2.md) (+3 mục khác)

## 1.8.1 — Single VXP

- Removed normal per-device VXP build selection.
- Removed `build_matrix.py`.
- Removed `--profile`, `--imsi` and device-bound application artifact mode from the normal builder.
- Canonical final artifact is always `build/<ProjectName>.vxp`.
- Templates no longer contain `target_profile`.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_1.md) (+5 mục khác)

## 1.8.0 — Release Security

- Added explicit signing modes: dev, device-bound, cert100.
- Added profile-level direct-run signing policy.
- `--release` refuses signing modes that the selected profile does not declare trusted.
- Added VXP structure/trailer inspection and release manifests.
- Added multi-target `build_matrix.py` for separate device-specific artifacts.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_0.md) (+7 mục khác)

## 1.7.1 — AI Agent Project Protocol

- Added a mandatory two-file preflight: `doc/ai/SKILL.md`, then `doc/ai/PROMPT.md`.
- Added `doc/ai/README.md` as the AI-agent entry point.
- Agents must inspect the selected target profile and current project template before
- Agents must select `GENERIC_VXP`, `KNOWN_DEVICE_PROFILE` or `NEW_DEVICE_PORT`.
- Target application code is engine-only and should not add external runtime frameworks.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_7_1.md) (+5 mục khác)

## 1.7.0 — Compact Workbench

- Removed duplicate Dashboard, Projects, Build and standalone Console pages.
- Activity Bar now contains only Explorer, Search, Assets, UI Designer, Emulator and Settings.
- Top workbench bar now contains project context + Command Palette only.
- Reduced menu set to File / Edit / View / Run / Tools / About.
- Integrated Output / Build / Problems remains the only log/panel surface.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_7_0.md) (+7 mục khác)

## 1.6.3 — Documentation Layout

- Consolidated all Markdown documentation under `doc/`.
- Kept only root `README.md` outside the documentation tree.
- Replaced the former `docs/` directory with categorized `doc/` subfolders.
- Moved `SKILL.md` and `PROMPT.md` to `doc/ai/`.
- Moved third-party notices to `doc/legal/`.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_6_3.md) (+4 mục khác)

## 1.6.2 — Font Icon UI

- Removed emoji/pictogram-style control text from the Studio.
- Added `studio/app/ui/icons.py`.
- Uses Windows system font icons: Segoe Fluent Icons / Segoe MDL2 Assets.
- No font files are bundled.
- Activity Bar, menus, top command bar, Explorer toolbar, Find/Replace and major

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_6_2.md) (+3 mục khác)

## 1.6.1 — Documentation & Agent Guide

- Rewrote root README around the current v1.6 Native SDK architecture.
- Added `doc/INDEX.md`.
- Added Quick Start, Architecture, Build VXP, Studio Guide, Device Compatibility,
- Expanded Native SDK documentation.
- Updated Lua API reference with `capabilities()` and `device_info()`.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_6_1.md) (+5 mục khác)

## 1.6

- Rebuilt the Explorer as a VS Code-style directory tree.
- Added quick New File/New Folder/Refresh/Collapse controls.
- Added relative path copy, reveal, generated-folder toggle, rename and delete.
- Added `sdk/luas30/` as a project-owned SDK.
- Replaced CoreMRE-facing runtime calls with stable `ls30_*` API calls.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_6.md) (+8 mục khác)

## 1.5 — VS Code-style workspace

- Replaced the wide dashboard/sidebar chrome with a compact VS Code-style workspace.
- Added a top application menu: File, Edit, Selection, View, Go, Run, Terminal, Help, About.
- Added a narrow activity bar for Explorer, Search, Projects, Build, Emulator, Assets, UI Designer, Console and Settings.
- Converted the editor project/search pane to an Explorer-style primary sidebar with hidden internal tabs.
- Reduced oversized headings, rounded dashboard cards and decorative chrome across Studio views.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_5.md) (+5 mục khác)

## 1.4.2

- Added requirement-aware dependency manager.
- `run.bat` no longer downloads/upgrades Python packages on every launch.
- Added automatic offline fallback and explicit `--offline` mode.
- Added `--online`, `--deps-only`, and `--force-deps` launcher modes.
- Added persistent dependency change log and JSON environment state.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_4_2.md) (+3 mục khác)

## Studio 1.3

- Added Lua 5.1 + LuaS30 `engine.*` autocomplete.
- Added current/project symbol completion.
- Added Find/Replace with match highlighting and wrap-around navigation.
- Added low-overhead source minimap.
- Added dependency-free inline Lua structural diagnostics.

→ [Chi tiết](doc/release/changelog/CHANGELOG_STUDIO_1_3.md) (+6 mục khác)
