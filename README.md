# LuaS30 IDE 1.15.0 – AI Workbench v1

**LuaS30 IDE** là IDE + Native SDK + build pipeline dành cho ứng dụng/game Lua
chạy theo workflow VXP trên thiết bị S30+/MRE-style.

Bản 1.6.1 là bản cập nhật tài liệu và hướng dẫn phát triển cho kiến trúc
**LuaS30 Native SDK** của v1.6.

## Thành phần chính

- **LuaS30 Studio**: giao diện desktop kiểu VS Code bằng PySide6.
- **Code Editor**: Project Explorer dạng cây thư mục, tabs, Lua highlighting,
  autocomplete, Find/Replace, minimap, diagnostics, Go to Definition,
  project-wide search, Console/Build Log.
- **LuaS30 Native SDK**: API C riêng `ls30_*`, không build dựa vào vendor MRE
  headers hoặc `percommon.a` / `peraudio.a`.
- **Lua 5.1.5**: source được bundle trong `vendor/lua-5.1.5/`.
- **ARM GCC**: toolchain ARM nằm trong `toolchain/arm-gcc/`.
- **VXP pipeline**: compile ARM ELF → verify ELF → pack VXP → optional IMSI bind
  (không ký) → SHA-256 → optional emulator.
- **Device profiles**: profile JSON cho target chung và thiết bị cụ thể.
- **Asset Manager / UI Designer / Emulator workflow** trong Studio.
- **Smart Launcher**: kiểm tra dependency, chỉ update khi cần và hỗ trợ offline.

## Kiến trúc

```text
Lua project
    │
    ▼
engine.* / mre.*
    │
    ▼
LuaS30 Runtime
    │
    ▼
LuaS30 Native SDK (ls30_*)
    │
    ▼
ABI Resolver
    │
    ▼
VXP-capable firmware
```

LuaS30 sở hữu lớp SDK/API phía engine. Tuy nhiên firmware của điện thoại vẫn là
ranh giới hệ điều hành bắt buộc cung cấp display, keypad, timer, resource, file,
audio và các dịch vụ runtime khác.

## Khởi động Studio

Trên Windows:

```bat
run.bat
```

Các mode launcher:

```bat
run.bat --offline
run.bat --online
run.bat --deps-only
run.bat --force-deps
```

Launcher sử dụng:

```text
%APPDATA%\LuaS30IDE\
├── config\
├── logs\
├── cache\
├── temp\
├── backups\
└── venv\
```

Project người dùng được tạo tại:

```text
Documents\LuaS30IDE\<ProjectName>\
```

## Tạo project

```bat
new_project.bat MyGame
```

Hoặc chọn **File → New Project** trong Studio.

Project tối thiểu:

```text
MyGame/
├── project.json
├── conf.lua
├── main.lua
├── src/
└── assets/
```

## Build VXP

Build + chạy VXP vừa tạo trong emulator:

```bat
build.bat "Documents\LuaS30IDE\MyGame"
```

Chỉ build:

```bat
build_only.bat "Documents\LuaS30IDE\MyGame"
```

Build CLI đầy đủ:

```bat
python tools\build.py ^
  --project "Documents\LuaS30IDE\MyGame" ^
  --toolchain "toolchain\arm-gcc" ^
  --profile generic-vxp-qvga ^
  --no-run
```

Target Nokia 225 Dual SIM có thể dùng profile:

```text
nokia-225-dual-sim
```

và tùy firmware có thể cần device/SIM binding. Xem `doc/build/BUILD_VXP.md` và
`doc/platform/DEVICE_COMPATIBILITY.md`.

## Lua API

API native chính nằm trong global table:

```lua
engine
```

Alias tương thích:

```lua
mre
```

Ví dụ:

```lua
local E = engine

local bg = E.color(24, 40, 32)
local white = E.color(255, 255, 255)

function E.draw()
    E.clear(bg)
    E.text(8, 8, "Hello S30+", white)
end
```

Xem `doc/reference/API.md`.

## Tài liệu

Bắt đầu tại:

- [`doc/INDEX.md`](doc/INDEX.md) — mục lục tài liệu.
- [`doc/getting-started/QUICKSTART.md`](doc/getting-started/QUICKSTART.md) — chạy Studio và tạo app đầu tiên.
- [`doc/architecture/ARCHITECTURE.md`](doc/architecture/ARCHITECTURE.md) — kiến trúc engine/runtime/SDK.
- [`doc/sdk/NATIVE_SDK_1_6.md`](doc/sdk/NATIVE_SDK_1_6.md) — Native SDK / ABI boundary.
- [`doc/reference/API.md`](doc/reference/API.md) — Lua API.
- [`doc/build/BUILD_VXP.md`](doc/build/BUILD_VXP.md) — build/pack/verify/run.
- [`doc/studio/STUDIO_GUIDE.md`](doc/studio/STUDIO_GUIDE.md) — giao diện Studio.
- [`doc/platform/DEVICE_COMPATIBILITY.md`](doc/platform/DEVICE_COMPATIBILITY.md) — profile/porting.
- [`doc/support/TROUBLESHOOTING.md`](doc/support/TROUBLESHOOTING.md) — xử lý lỗi.
- [`doc/ai/SKILL.md`](doc/ai/SKILL.md) — hướng dẫn cho coding agent/AI khi phát triển repository.
- [`doc/ai/PROMPT.md`](doc/ai/PROMPT.md) — master prompt để tiếp tục phát triển LuaS30 IDE.

## Kiểm tra source

```bat
python tools\validate_tree.py
python tools\validate_native_sdk.py
python tools\validate_complete.py
```

`run.bat` cũng chạy validation trước khi mở Studio.

## Third-party components

Thông tin ghi công nằm trong:

```text
doc/legal/THIRD_PARTY_NOTICES.md
vendor\lua-5.1.5\COPYRIGHT
```

Trong Studio có thể xem **About → Environment / Credits**.

## Nguyên tắc compatibility

Không được kết luận rằng một VXP chắc chắn chạy trên mọi điện thoại chỉ vì:

- ELF hợp lệ;
- emulator chạy;
- hoặc build thành công.

Mỗi firmware VXP có thể khác nhau về ABI, RAM, audio codec, resource format,
binding policy và symbol availability. Release cho máy thật phải được smoke-test
trên chính thiết bị mục tiêu.


## Studio icon policy

Studio controls use the centralized font-icon layer in `studio/app/ui/icons.py`.
Emoji are not used as UI icons. On Windows the engine uses installed
Segoe Fluent Icons or Segoe MDL2 Assets, without bundling font files.


## Documentation layout

Ngoại trừ `README.md` này, toàn bộ tài liệu Markdown của project được quản lý tại:

```text
doc/
```

Mục lục chính:

```text
doc/INDEX.md
```

Các nhóm chính gồm Getting Started, Architecture, SDK, API Reference, Platform,
Build, Launcher, Studio, Development, AI instructions, Legal và Release History.


## Compact Workbench 1.7

Studio 1.7 uses one command source per function:

- Activity Bar: Explorer, Search, Assets, UI Designer, Emulator, Settings.
- Bottom Panel: Output, Build, Problems.
- Run menu: Build/Run/Stop only.
- Tools menu: validation/cleanup/folders.
- About menu: documentation/environment/credits.
- Build and emulator are backed by `BuildService` and `EmulatorService`, not placeholder screens.
- The emulator screen shows the real last VXP, SHA-256 and process state instead of a fake phone preview.


## AI Agent project creation protocol

Before an AI coding agent creates or scaffolds a project with LuaS30 IDE, it must
read these files in order:

```text
doc/ai/SKILL.md
doc/ai/PROMPT.md
```

The agent must then choose an explicit target mode/profile instead of guessing hardware
compatibility. Project code should depend only on LuaS30's stable engine API on the
target side; device differences are isolated in profiles/adapters and the Native SDK ABI
boundary.


## Release hardening 1.8 — no signing

**LuaS30 IDE không ký VXP.** Không có lõi ký, không có khóa, không có cờ `--cert100-key`
trong repo. `build/<ProjectName>.vxp` luôn là bản **chưa ký** (`cert-id 1`, khối chữ ký
rỗng), dành cho emulator và máy dev/engineering.

Hệ quả cần nói rõ: firmware retail có siết certificate trust sẽ **từ chối mở** file chưa
ký. Nếu cần ký thì phải làm **ngoài repo này**, bằng công cụ do người vận hành kiểm soát —
nhờ vậy máy build bị lộ cũng không tạo được gói được tin cậy.

```bat
python tools\build.py --project PROJECT --toolchain toolchain\arm-gcc ^
  --release --no-run
```

`--release` chỉ bật hardening (strip ký hiệu native, bảo vệ Lua), sinh SHA-256 và ghi
VXP/release manifest. Nó **không** ký.

Xem `doc/build/RELEASE_AND_HARDENING.md`.


## Single VXP model 1.8.1

LuaS30 produces one canonical application artifact:

```text
build/<ProjectName>.vxp
```

There is no normal per-device VXP option and no device suffix in the filename.
Compatibility differences are handled by the runtime capability layer, Native SDK and
ABI resolver.

`--device-imsi` binds a SIM IMSI into tag `0x12` for install-time binding. Binding is
**not** signing: the file stays unsigned.


## Runtime compatibility layer 1.8.2

The single VXP now performs firmware compatibility resolution at startup:

```text
capability detection -> ABI aliases -> safe fallbacks
```

Applications still build to one `build/<ProjectName>.vxp`. Device API differences are
handled inside the engine instead of creating per-device VXP variants.

See `doc/sdk/RUNTIME_COMPATIBILITY_1_8_2.md`.


## Runtime compatibility matrix 1.8.3

Run:

```bat
python tools\runtime_compat_matrix.py
```

The report records native/effective capabilities, exact selected ABI aliases, active
fallbacks, missing required groups, compatibility level and final result for every MRE
firmware manifest under `compat/mre/`.

Bundled manifests are synthetic regression fixtures; real firmware results require an
observed exported-symbol inventory.

See `doc/sdk/RUNTIME_COMPAT_MATRIX_1_8_3.md`.
\n\n## Portable ARM GCC compile fix 1.8.4\n\nThe bundled Windows GCC is self-contained, but its `cc1.exe` backend loads runtime DLLs\nfrom `toolchain/arm-gcc/bin`. LuaS30 now prepends the bundled toolchain directories to the\nchild-process `PATH` before compilation and runs a trivial ARM compile preflight before\ncompiling the Native SDK. This avoids requiring a global MSYS2/GCC installation or a\nmanual PATH edit.\n\nIf the preflight fails, run:\n\n```bat\npython tools\\toolchain_doctor.py --toolchain toolchain\\arm-gcc\n```\n

## Tabbed Workbench 1.9

LuaS30 Studio now uses one VS Code-style editor area. Source files and tool features share
the same closable tab strip instead of switching the entire workspace to separate pages.

Activity Bar tools open/focus tabs:

```text
Project Storage
Assets
UI Designer
Emulator
Settings
```

Every feature under the `Tools` menu also opens a tab:

```text
Project Doctor
Runtime Compatibility Matrix
Toolchain Doctor
```

`Project Storage` manages projects under `Documents\LuaS30IDE` with scan, search,
open, import, duplicate, rename, delete, reveal and build-artifact status.

Build/Output/Problems remain in the integrated bottom panel, avoiding duplicate Build or
Console pages.


## Workspace session restore 1.9.1

Studio now automatically restores the current project, open file/tool tabs, active tab, real editor groups, sidebar and bottom-panel state from `%APPDATA%\LuaS30IDE\config\workspace_session.json`.

Use **View → Split Editor Right** to create another editor group.


## VS Code-like Welcome / Project Hub 1.9.2

On a cold start, LuaS30 Studio opens the `Welcome` tab first. It contains:

- New Project;
- Open Project Folder;
- Import into Project Storage;
- recent managed projects;
- storage path/count/size/build summary;
- current workspace status;
- Manage Project Storage.

The checkbox `Show Welcome page on startup` is enabled by default. If disabled, the
workspace-session system restores the previously active editor/tool tab instead.

The Welcome tab is pinned to index 0 of editor group 0 when it is created. Existing
source/tool tabs and editor groups are still restored in the background.


## Integrated Terminal and Console 1.9.3

LuaS30 Studio now has a VS Code-style bottom panel with:

```text
CONSOLE | BUILD | PROBLEMS | TERMINAL
```

Shortcuts:

```text
Ctrl+J        Toggle Bottom Panel
Ctrl+Shift+Y  Toggle Console
Ctrl+`        Toggle Terminal
Ctrl+Shift+`  New Terminal
```

The Terminal is a real persistent shell process started in the current project directory.
On Windows it uses `%COMSPEC%`/`cmd.exe`; the panel can create, stop and clear the shell.
Panel visibility and the active Console/Build/Problems/Terminal tab are saved in the
workspace session.


## Project Hub clean layout 1.9.4

`Welcome` and `Project Storage` are now clean full-width project-management screens.

While either page is active, Studio temporarily hides editor-only chrome:

```text
Activity Bar
Explorer / Search sidebar
Find / Replace bar
Console / Build / Problems / Terminal panel
```

Returning to a source editor restores the exact sidebar and bottom-panel visibility the
user had before entering the Project Hub. The temporary hub layout is not written over
the editor layout in `workspace_session.json`.


## Clean startup tabs 1.9.6

LuaS30 Studio no longer reopens source documents after application startup or restart.

The startup session still restores:

```text
current project
editor-group layout
tool tabs
Explorer / Activity Bar preferences
bottom-panel state
window/session layout
```

but it does not restore:

```text
file tabs
untitled editor tabs
main.lua fallback
```

Welcome remains the default startup landing tab. Files open only after the user explicitly
selects one from Explorer/Search/Recent actions or uses Open File.


## MRE GCC build fix 1.9.7

The portable ARM GCC preflight no longer writes a literal `\n` into its generated C
source. It now compiles and links a real multiline `gcc_entry` probe using the same
ARMv5TE/PIC/little-endian MRE GCC profile as the runtime build.

`tools/toolchain_doctor.py` was fixed at the same time and now checks the linker in
addition to GCC/cc1/assembler.

See `doc/build/MRE_GCC_BUILD_1_9_7.md`.


## Startup screen setting 1.9.8

`Settings -> Startup screen` now provides three explicit startup modes:

```text
Welcome
Project Hub
Empty Editor
```

`Empty Editor` restores project/layout preferences but opens no source file and no tool
page. Source/untitled tabs remain excluded from startup restore in all three modes.

The old `Show Welcome page on startup` checkbox was removed from Welcome so startup
behavior has one source of truth in Settings.


## Multi-toolchain MRE profiles 1.10.0

LuaS30 now supports selectable MRE compiler profiles:

```text
ARM GCC
RVDS / RVCT
ARM ADS 1.2
Auto Detect
```

The same runtime exports `gcc_entry`, `rvct_entry` and `ads_entry`, each routed through a
shared LuaS30 bootstrap. Settings can select the compiler profile and toolchain root.

ARM GCC remains the bundled/validated path. RVDS and ADS1.2 require the user's legitimate
local ARM toolchain installation.

See `doc/build/TOOLCHAIN_PROFILES_1_10_0.md`.


## Compact bottom panel 1.10.1

The Console / Build / Problems / Terminal area is hidden by default on every application
startup, even if it was visible before the previous shutdown.

Use:

```text
Ctrl+`        Toggle Terminal
Ctrl+Shift+Y  Toggle Console
Ctrl+J        Toggle Panel
```

The bottom panel now has a close button in its top-right corner. Hiding the Terminal does
not kill its shell process; reopening the panel returns to the same terminal session.

The panel opens at a compact height, remains resizable with the vertical splitter, and
remembers the preferred height without automatically reopening on the next launch.

Global editor/page scrollbars were reduced to 7 px for a cleaner VS Code-like layout.


## Direct terminal input 1.10.2

The integrated Terminal no longer uses a separate one-line textbox.

Commands are typed directly into the terminal surface after the current working-directory
prompt, matching the interaction model of VS Code's integrated terminal.

```text
C:\Users\user\Documents\LuaS30IDE\prj> python tools\build.py ...
```

Supported terminal editing:

```text
Enter       run current command
Up / Down   command history
Home        jump to start of editable command
Ctrl+A      select current command only
Ctrl+V      paste into current command
Ctrl+L      clear terminal
Ctrl+C      copy selection, otherwise send ETX to the shell
```

Previous terminal output is protected from accidental editing.


## Colored panel, HEX viewer and unique AppID 1.10.3

The Compact Bottom Panel now color-codes build/console output:

```text
red      errors/failures
yellow   warnings
green    OK/PASS/success
cyan     commands/RUN
blue     BUILD/TOOLCHAIN/EMU/INFO
purple   section headings
```

When Run/Emulator is requested, the panel opens the new `HEX` tab for the exact VXP from
the sync manifest. The viewer is paged in 64 KiB chunks and displays offset, hexadecimal
bytes and ASCII without loading a huge VXP into one text document.

Every newly created managed project receives a new numeric AppID. Duplicate and Import
also receive a new AppID; Rename preserves the existing AppID.


## AI Workbench 1.11.0

The editor now uses the VS Code-like layout `Explorer | [Editor + Compact Bottom Panel] | Chat AI`.
The bottom panel is physically limited to the center editor column.

Right-click any editor/tool tab for `Close`, `Close Others`, or `Close All Tabs`.
Close All applies across editor groups and still prompts for unsaved source documents.

ChatAI supports OpenAI, Anthropic, Google Gemini, OpenAI-compatible endpoints, and Ollama.
API keys are session/environment only and are never persisted by LuaS30.

Automatic ChatAI context can inspect project structure, active/relevant source code,
SKILLS.md / SKILL.md / PROMPT.md, plus engine `doc/ai/SKILL.md` and `PROMPT.md`.
Common secret files such as `.env`, credentials and private-key filenames are excluded.


## Series 30+ high compatibility 1.12.0

LuaS30 now distinguishes two runtime build backends:

```text
standalone        LuaS30 dynamic firmware-symbol resolver
s30plus-native    ARM GCC + real MRE SDK headers/libs + MRE scatter script
```

`auto` prefers `s30plus-native` whenever a valid `MRE_SDK` is available.

For Nokia 225 Dual SIM RM-1011 use:

```text
S30+ compatibility = Nokia 225 Dual SIM RM-1011
Compiler            = ARM GCC
Screen              = 240x320
Entry chain          = gcc_entry -> vm_main
```

The native path links the user's MRE SDK `per*.a` libraries and its `scat.ld`, while Lua
game/application code continues to use the LuaS30 `engine.*` API.

Nokia retail firmware commonly requires an IMSI-bound install VXP. LuaS30 keeps the
canonical build VXP unchanged and can additionally create `build/device/*.nokia225.vxp`
when a session-only IMSI is supplied. The IMSI is never written to manifests/config files.


## MediaTek MRE project wizard 1.13.0

`New Project` now opens the MediaTek MRE SDK configuration modal immediately instead of
showing a small project-name prompt first. The dialog follows the supplied reference video
and configures the packaging/runtime metadata before the project folder is created.

Fields:

```text
APPNAME
APPVER
VENDOR
Resolution
MediaTek chipset
Heap RAM
```

The wizard includes these MediaTek presets:

```text
MTK6260  (Nokia 220, 225)
MTK6261  (Nokia 3310 3G, 216)
MTK6250  (Q-Mobile, K-Touch)
MTK6225  (Legacy MRE 2.0)
```

Selecting MTK6260 writes the `nokia225-rm1011` compatibility profile. Other modern
MediaTek presets use `s30plus-native`; MTK6225 also uses the native MRE SDK backend but
with the lighter `File ProMng` API tag.

Every new project still receives a fresh AppID. The wizard writes its configuration to
both `project.json` and `.luas30/mre_sdk.json`, while keeping the generated AppID intact.
The build tool now honors a project's compatibility profile whenever the CLI/Studio
compatibility setting remains `auto`.


## AI Agent Activity + Shell Control 1.14.0

ChatAI can now show an `AI ACTIVITY · REASONING SUMMARY` stream and can control the
visible integrated Terminal through an approval-based agent protocol.

The activity stream intentionally does **not** expose private/raw chain-of-thought. It
shows concise high-level summaries such as context files inspected, plan/result summaries,
shell proposals and shell exit status.

Shell permissions are session-only:

```text
Disabled
Ask before running        (default)
Auto-run safe commands
```

AI shell commands always execute in the same Compact Bottom Panel `TERMINAL` the user can
see. In Ask mode the command appears in a Shell Request card with Run/Reject controls.
Potentially destructive commands require an additional confirmation. Auto mode only runs
commands classified as safe/read-only.

After an AI-approved shell command finishes, its bounded/redacted result is returned to
the model and the agent can continue. Common secret-bearing environment values are
redacted before shell output is sent to a remote provider.

## AI Workbench v1 — 1.15.0

LuaS30 AI Workbench v1 upgrades the right Chat sidebar into an agent-style coding workspace.
It keeps the existing codebase context, SKILL(S).md/PROMPT.md loading and visible integrated
Terminal, then adds provider testing, access modes and reviewable code changes.

### Access modes

```text
Ask before changes   review code edits and shell requests before execution
Edit automatically   apply validated project edits automatically; shell still asks
Plan mode            analysis/planning only; no code edits or shell actions
Full access          auto-apply validated edits and run non-sensitive project shell commands
```

Dangerous or secret-bearing shell commands still require explicit confirmation even in
Full access.

### Provider Settings

`AI Provider Settings` is a frameless modal with:

```text
Provider
Model
Base URL
API key (session only)
Timeout
Allow shell requests
Allow code-change proposals
Show reasoning summary/activity trace
```

Buttons:

```text
Test Connection
Apply
Save & Close
Cancel
```

API keys are not written to LuaS30 configuration files.

### AI code changes

Models can propose project-relative edits through the `luas30-edit` protocol. LuaS30
validates every target path, blocks common secret/VCS/generated locations and prepares a
VS Code-style `AI Changes` diff tab before manual application.

The diff tab contains current/proposed panes and an `Apply Code` button. Applied existing
files are backed up under:

```text
.luas30/ai-backups/<timestamp>/
```

before atomic replacement.

## Bản quyền

© Qeafivels All rights reserved. — <https://qeafivels.com/>

LuaS30 IDE (Studio, LuaS30 Native SDK/API, build tooling, template, tài liệu và
asset của dự án) là tài sản của Qeafivels. Không được sao chép, sửa đổi, phát
hành, cấp phép lại hay tạo tác phẩm phái sinh, toàn bộ hoặc một phần, nếu không
có sự cho phép trước bằng văn bản của Qeafivels. Chi tiết: [`LICENSE`](LICENSE).

Các thành phần bên thứ ba được dùng/bundle **không** thuộc phạm vi thông báo
trên và vẫn theo giấy phép riêng của chúng — xem
[`doc/legal/THIRD_PARTY_NOTICES.md`](doc/legal/THIRD_PARTY_NOTICES.md). Giấy phép
Lua 5.1.5 đi kèm ở [`vendor/lua-5.1.5/COPYRIGHT`](vendor/lua-5.1.5/COPYRIGHT).

Thông tin bản quyền này cũng hiện trong ứng dụng tại **About → About**.

