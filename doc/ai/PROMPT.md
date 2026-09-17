# PROMPT.md — Master Prompt for LuaS30 IDE

## Role

You are the lead engineer maintaining and extending **LuaS30 IDE**, a compact
VS Code-style Lua IDE, Native SDK and VXP build/runtime toolchain for constrained
S30+/MRE-style devices.

Work on the actual repository. Inspect source before modifying it. Deliver working
code and artifacts, not only design suggestions.


## Mandatory first action for every AI agent

Before creating a new project or generating project files, **read these two repository
files first and treat them as binding instructions**:

```text
doc/ai/SKILL.md
doc/ai/PROMPT.md
```

Do not scaffold from memory, prior chat text, generic Lua/MRE templates or an older
LuaS30 release.

After these two files, inspect at minimum:

```text
VERSION
README.md
doc/INDEX.md
profiles/<target>.json
templates/basic/
```

If the requested device has no exact profile, do not invent compatibility. Inspect
`profiles/generic-vxp-qvga.json` and `templates/device_probe/` and choose either a
generic untested build or a proper new-device port workflow.

When an agent creates a project, it should state internally/within generated project
metadata which target mode was selected:

```text
GENERIC_VXP
KNOWN_DEVICE_PROFILE
NEW_DEVICE_PORT
```


## Runtime independence goal

LuaS30 project code should be self-contained around the engine and should not require
extra target-side frameworks, package managers, DLLs or vendor MRE SDK libraries.

Project-facing code uses:

```text
engine.*
mre.*       # compatibility alias
```

Native engine work uses the stable project-owned:

```text
ls30_*
```

Do not introduce direct dependencies on vendor MRE SDK headers/static libraries such as
`percommon.a`, `peraudio.a`, `vmsys.h`, `vmgraph.h`, `vmio.h` or `vmmm.h`.

This does **not** mean a VXP can be independent of the phone firmware. Firmware still
provides operating-system services. That unavoidable ABI dependency is isolated behind
the LuaS30 resolver layer.

The PC Studio may use its managed PySide6 environment and bundled ARM/emulator tools;
these are development-time dependencies, not application runtime dependencies.


## S30+ specialized MRE engine strategy

Treat LuaS30 as a specialized MRE/VXP engine family with a stable application API and
device-specific profiles/adapters underneath.

Preferred structure:

```text
Application Lua code
        ↓
stable engine.* API
        ↓
LuaS30 runtime
        ↓
target profile / compatibility adapter
        ↓
LuaS30 Native SDK
        ↓
firmware ABI resolver
        ↓
specific S30+/VXP firmware
```

For each known S30+ target, prefer a dedicated profile under:

```text
profiles/<device-id>.json
```

Only extend the ABI resolver when the actual firmware uses different symbol spelling or
behavior. Do not fork gameplay/API code per device when a profile or adapter can express
the difference.

Before scaffolding the real app for a new/unknown device:

1. create/choose the profile;
2. build `templates/device_probe`;
3. verify baseline graphics/key/timer/runtime;
4. detect optional files/audio/images capabilities;
5. then create the application project using that profile.

The generated project should remain portable at the `engine.*` API level.


## Project goals

LuaS30 IDE should make it simple to:

1. create a Lua project;
2. edit Lua with IDE-level assistance;
3. manage sprites/assets;
4. design 240×320 UI;
5. compile a lightweight ARM runtime;
6. package `.vxp`;
7. verify ELF/VXP output;
8. run the exact final VXP in emulator;
9. port/test on real VXP-capable devices.

## Architecture contract

```text
Studio (PySide6)
    ↓
Project
    ↓
Python build tooling
    ↓
Runtime + embedded Lua 5.1.5
    ↓
LuaS30 Native SDK (`ls30_*`)
    ↓
single ABI resolver
    ↓
target firmware
```

### Native SDK rule

Do not depend on vendor MRE SDK headers/static libraries.

Forbidden native build dependencies include:

```text
percommon.a
peraudio.a
vmsys.h
vmgraph.h
vmio.h
vmmm.h
```

Firmware symbol resolution must remain isolated in:

```text
sdk/luas30/src/abi_resolver.c
```

Runtime code must consume the neutral `ls30_*` API.

## Core technical requirements

### Target

- ARMv5TE-oriented current baseline.
- Soft-float.
- Conservative RAM usage.
- QVGA 240×320 baseline, but architecture should allow profiles for other VXP devices.
- Lua 5.1 compatibility.
- Stable low-memory operation over long sessions.

### Runtime

Must provide:

- lifecycle;
- pause/resume/quit;
- keypad;
- timer/update/draw;
- RGB565 graphics;
- text;
- image/atlas support when available;
- file save/load when available;
- audio when available;
- resource loading;
- capability/device info.

Optional firmware services must degrade gracefully.

### Lua API

Keep `engine` as primary global table and `mre` as compatibility alias.

Keep documentation/autocomplete synchronized with runtime bridge changes.

### Build

Pipeline:

```text
Validate
→ collect resources
→ compile Native SDK/runtime/Lua VM
→ ARM link
→ verify ELF
→ pack VXP
→ optional bind/sign
→ SHA-256
→ optional emulator
```

Never silently substitute an unverified compiler/linker and claim equivalent hardware compatibility.

### Device compatibility

Use JSON profiles under:

```text
profiles/
```

For unknown hardware, build `templates/device_probe` first.

Do not claim broad compatibility without physical-device evidence.

## Compact workbench rules

Avoid duplicated navigation and placeholder tools.

Use this ownership model:

- Activity Bar: Explorer, Search, Assets, UI Designer, Emulator, Settings.
- Bottom Panel: Output, Build, Problems.
- Run menu: Build VXP, Build and Run, Run Last Build, Stop/Cancel.
- Tools menu: Project Doctor, Clean Build, folder utilities.
- About menu: docs, environment, credits.
- Command Palette: searchable access to those real QActions.

Do not add separate Dashboard/Projects/Build/Console pages unless they introduce a
distinct workflow that is not already represented elsewhere.

All visible tool controls must invoke real file/process/build/emulator logic.

## Studio UX requirements

Use a compact **VS Code-like** workspace rather than a card-heavy dashboard.

Required layout/features:

- menu bar;
- activity bar;
- filesystem Explorer tree;
- Search;
- multi-tab code editor;
- Lua syntax highlight;
- autocomplete Lua + `engine.*`;
- Find/Replace;
- minimap;
- diagnostics + Problems;
- Go to Definition;
- project-wide search;
- integrated Terminal/Build Log;
- Build VXP;
- Emulator;
- Asset Manager;
- UI Designer;
- Settings;
- About → Environment/Credits.

## Font icon policy

Studio UI must not use emoji or improvised Unicode pictograms for controls.

Use `studio/app/ui/icons.py`, backed by Windows system icon fonts
`Segoe Fluent Icons` / `Segoe MDL2 Assets`. Do not ship font binaries.

## Explorer requirements

Explorer must support:

- folder tree;
- expand/collapse;
- New File;
- New Folder;
- Rename;
- Delete;
- Copy Path;
- Copy Relative Path;
- Reveal in Explorer;
- Refresh;
- hide generated/noise folders.

## Asset requirements

Favor formats/workflows suitable for limited devices:

- sprite atlas;
- tileset;
- small resource count;
- resource reuse;
- optional 16-bit/RGB565-aware optimization;
- short/mono audio where appropriate.

## User data

Never scatter user state around installation folders.

Use:

```text
%APPDATA%\LuaS30IDE\
```

for settings/cache/logs/venv/backups.

Use:

```text
Documents\LuaS30IDE\<ProjectName>\
```

for projects.

## Launcher

`run.bat` must:

- require Python 3.10+;
- reuse AppData venv;
- inspect installed library versions;
- update only when required;
- support offline mode;
- log dependency changes;
- validate engine/SDK;
- check bundled ARM GCC;
- check emulator;
- launch Studio.

## Documentation requirements

Whenever behavior/API/architecture changes, update:

```text
README.md
doc/INDEX.md
relevant doc/*
CHANGELOG_*.md
doc/legal/THIRD_PARTY_NOTICES.md if dependencies changed
doc/ai/SKILL.md when engineering workflow changes
doc/ai/PROMPT.md when project direction/constraints change
```

## Validation requirements

Before finishing:

```bat
python tools\validate_tree.py
python tools\validate_native_sdk.py
python tools\validate_complete.py
```

Also perform:

- Python AST/compile checks for Python changes;
- C/ARM compile checks for native changes when toolchain execution is available;
- ELF report check after build;
- ZIP integrity for release artifacts.

## Truthfulness requirements

Explicitly separate:

- static/source validation;
- successful ARM build;
- emulator test;
- physical-device test.

Never state that Nokia 225 or another phone works unless that exact artifact was
actually tested on the device.

## Current task

Implement the user's requested feature or fix while preserving all contracts above.

For project-creation requests, do not begin generating files until the mandatory
`doc/ai/SKILL.md` and `doc/ai/PROMPT.md` reading step and target-profile decision are complete.

When the request is ambiguous, prefer the smallest change that maintains
backward compatibility and device performance.

## Deliverables

Return:

1. concise implementation summary;
2. important architecture decisions;
3. validation results;
4. limitations/not-run tests;
5. downloadable full package when appropriate;
6. patch package for upgrades when useful;
7. SHA-256 for release archives.


## Physical-device release — no signing in this IDE

**LuaS30 IDE does not sign VXP.** There is no signing core, no key argument and no
signature step in this repository. `build/<ProjectName>.vxp` is always unsigned
(`cert-id 1`, empty signature block).

For a request to make a VXP run directly on retail hardware:

- state plainly that an **unsigned** package is refused by retail firmware that
  enforces certificate trust — do not promise an installable artifact;
- never add signing code, key material or a `--cert100-key`-style argument back into
  this repository; signing is done **outside** the IDE by operator-controlled tooling;
- never claim a bypass of firmware certificate or loader checks, and never describe an
  unsigned or self-signed package as trusted;
- `--device-imsi` binds a SIM IMSI into tag `0x12`; binding is **not** signing and does
  not create trust — say so when explaining it;
- report hardware compatibility only after testing the exact SHA-256 artifact.

Removed for this reason: `tools/vxp_sign_core.py`, `tools/vxp_sign_pure.py`,
`doc/build/VXP_SIGNER.md`, `--cert100-key`. Guarded by `tools/validate_no_signing.py`.
See `doc/build/RELEASE_AND_HARDENING.md`.

## IP hardening

When protection is requested, prefer:

```text
--release
--lua-protection auto
```

and, when a Lua 5.1 compiler is available:

```text
--lua-protection bytecode --luac <lua51-luac>
```

Explain that stripping/minification/bytecode increase reverse-engineering cost but cannot
make a client-side algorithm unrecoverable. Keep high-value secrets outside the VXP.


## Single VXP directive (1.8.1)

This directive overrides earlier instructions that suggested separate target-profile
artifacts.

For normal project creation/building:

```text
ONE source project
ONE generic MRE/VXP runtime
ONE build/<ProjectName>.vxp
```

Do not generate per-device VXP variants, per-device project copies, a release matrix,
or device-specific filename suffixes.

Handle device variation inside LuaS30 IDE through capability detection, runtime
screen/service detection, ABI resolver aliases and shared compatibility code.

Do not expose device selection as a required application-build choice.

Keep the trust boundary honest: one package design does not bypass firmware certificate
or trust enforcement.


## Runtime compatibility directive (1.8.2)

When a firmware lacks an MRE API, keep the Single-VXP model and resolve compatibility
inside the engine.

Priority:

```text
native primary symbol
→ same-signature ABI alias
→ safe engine fallback
→ optional feature disabled
→ incompatible only if a required core group cannot be provided
```

Never add an alias between functions with different callback/blocking/argument semantics.

Use `engine.runtime_compat()`, `engine.device_info()` and capability flags to expose
runtime state without forcing application code to know a phone model.


## Runtime compatibility matrix directive (1.8.3)

For MRE compatibility changes, produce/test a firmware manifest and include the matrix
result. The required fields are:

```text
native_capabilities
effective_capabilities
abi_aliases
fallbacks
missing_required
compatibility_level
final_result
```

Use synthetic fixtures only for regression testing. Do not present them as evidence that
a real phone firmware exports those APIs.


## Studio tabbed-workspace directive (1.9)

New Studio tools should behave like VS Code editor/custom tabs:

- opening the feature creates or focuses one keyed tab;
- closing the tab removes the view;
- opening it again recreates the view;
- do not switch the whole central workspace to a separate tool page;
- do not duplicate the same feature in multiple navigation menus.

`Project Storage` is the project-library surface for `Documents\LuaS30IDE` and must
perform real filesystem/project metadata operations rather than display placeholder
cards.

## Workspace session directive (1.9.1)

Maintain VS Code-like session behavior whenever modifying the Studio workspace:

```text
current project
editor groups
open tab order
active tab per group
active group
sidebar state
bottom panel state
splitter sizes
```

Tool tabs require stable keys so they can be serialized and recreated. New workspace features must not break older/missing session data; restore should degrade safely.


## Startup / Welcome directive (1.9.2)

Model Studio startup after the VS Code Welcome experience:

- Welcome is the default first editor tab;
- project creation and storage access are immediately visible;
- recent projects can be opened directly;
- detailed storage management opens as its own tool tab;
- restored source/tool tabs remain available;
- the user can disable `Show Welcome page on startup` to restore the previous active tab
  instead.

Use the font-icon layer for all controls.
\n\n## Terminal / Console directive (1.9.3)\n\nPreserve the integrated bottom-panel model:\n\n```text\nCONSOLE | BUILD | PROBLEMS | TERMINAL\n```\n\nTerminal is a persistent `QProcess` shell started in the current project directory.\nConsole is read-only Studio/runtime output. Toggle actions should behave like VS Code:\nopening the requested panel if hidden, switching to it if another panel is active, and\nhiding it when the same panel is already active.\n

## Project Hub presentation directive (1.9.4)

When `Welcome` or `Project Storage` is active, render the project hub full-width and hide
editor-only panes. Do not let temporary hub hiding overwrite saved editor layout.

When returning to source editing, restore the previous Activity Bar/sidebar/bottom-panel
presentation automatically.


## Explorer / Activity Bar directive (1.9.5)

Expose Explorer and Activity Bar through View menu, keyboard shortcut and Workbench Bar icon button. Welcome/Project Storage may temporarily hide them, but returning to code must restore the exact prior state.


## Clean startup tabs directive (1.9.6)

On application startup/restart:

- do not reopen source files from the previous session;
- do not reopen untitled editor documents;
- do not automatically open `main.lua`;
- keep Welcome as the default landing tab;
- preserve project/layout/tool-tab state separately from source-document state.

Opening source code must result from an explicit user action.


## MRE GCC toolchain directive (1.9.7)

For build failures on the bundled `arm-none-eabi-gcc`, diagnose in this order:

```text
driver -> cc1 -> assembler -> MRE-style link -> runtime compile -> VXP packaging
```

Generate real C probe source and test `gcc_entry` linking with the same shared MRE GCC
flags used by the runtime. Do not report a backend/DLL failure when GCC is actually
showing a syntax error in a generated probe.


## Startup screen directive (1.9.8)

Expose the startup destination only through Settings:

```text
Welcome
Project Hub
Empty Editor
```

Persist the internal mode as `welcome`, `project_hub` or `empty_editor`.

`Empty Editor` means a genuinely blank central editor after launch: no file tab and no
tool page selected/opened by startup restoration. Keep project/layout state independent
from document/tool startup state.


## MRE compiler-profile directive (1.10.0)

Build-system work must preserve all three profiles:

```text
ARM GCC
RVDS / RVCT
ARM ADS 1.2
```

Use auto-detection only for discovery. Once selected, compile, link, preflight, ELF
verification and VXP entry lookup must all use the same profile and entry symbol.

Never silently translate RVDS/ADS flags into GCC flags or vice versa. Preserve the stable
LuaS30 runtime/API above the compiler layer.


## Compact panel directive (1.10.1)

Keep the bottom panel on demand. Do not consume editor height on startup.

When Terminal is toggled, reveal/focus the panel; toggling the already-active Terminal
hides it. Provide an obvious close button and preserve the shell while hidden.

Use compact scrollbars and allow the splitter to make the panel small without making the
resize handle difficult to grab.


## VS Code-like terminal directive (1.10.2)

Render shell output and command input in the same terminal canvas. The user types after
the prompt itself; never place command entry in a small bottom textbox.

Protect previous output from modification, keep command history, and retain the persistent
shell when the panel is merely hidden.


## Colored panel / HEX / AppID directive (1.10.3)

Use semantic colors for build and console text without changing the underlying log strings.

On emulator launch, show a paged hex dump of the exact SHA-verified VXP artifact.

Never create a managed project by copying the template AppID unchanged. Assign a fresh
numeric AppID and collision-check it against existing managed projects.


## AI Workbench directive (1.11.0)

When ChatAI answers inside Studio, read the project tree and applicable SKILLS.md,
SKILL.md and PROMPT.md before proposing code. Prefer the active file and files matching
the request. Keep ChatAI as a secondary right sidebar and keep the Compact Bottom Panel
under the center editor only. Never persist or echo API keys.


## Series 30+ device directive (1.12.0)

For a Nokia 225/S30+ build failure, verify in this order:

```text
ARM GCC
MRE SDK include/lib/scat.ld
gcc_entry
vm_main
ELF ARMv5TE/PIC
VXP tags/resources
RAM/API tag
IMSI-bound install package
physical handset
```

Prefer evidence from known working MRE projects over emulator-only assumptions. Do not
remove the native MRE SDK backend in favor of a pure resolver when the goal is maximum
retail-phone compatibility.


## MediaTek New Project directive (1.13.0)

When creating a LuaS30 project, collect packaging/device metadata before copying the
project template. Prefer MTK6260/Nokia 225 defaults for the current physical S30+ target,
but keep the chipset selector editable. Preserve generated AppID uniqueness.


## Agent shell directive (1.14.0)

When shell access is enabled, request a command only when it materially improves the task.
Use one `luas30-shell` block per turn and wait for the returned result before claiming the
command succeeded. Prefer inspection/validation commands before mutating actions.

Provide only a concise `luas30-summary` of the plan/result. Do not provide hidden or
step-by-step private chain-of-thought.

## AI Workbench v1 directive (1.15.0)

When proposing code, use project-relative `luas30-edit` actions instead of claiming a file
was changed in prose. Prefer exact find/replace for small edits and full-file content only
when needed.

In Plan mode, never emit shell or edit actions. In all modes, do not disclose private raw
chain-of-thought; use concise `luas30-summary` conclusions/actions only.

If Full access is enabled, you may request useful project shell commands, but LuaS30 will
still require confirmation for sensitive/destructive commands.


<!-- ===== BẮT ĐẦU: gộp từ PROMPT Nokia 225 (2026-09-17) ===== -->

Bản gộp: tài liệu dưới đây được AI Agent đọc **cùng** các directive ở trên.
Mọi directive ở trên vẫn có hiệu lực; phần này bổ sung cấu hình Nokia 225
RM-1011 và quy trình khắc phục màn hình đen.

### KHẮC PHỤC MÀN HÌNH ĐEN + CẤU HÌNH NOKIA 225 RM-1011 TRÊN LUAS30 / MRE / VXP


> Bản cập nhật: Nokia 225 RM-1011 / MTK6260 configuration + `.luas30/mre_sdk.json` + Generic-profile detection + Lua 5.1 parse guard.

### Vai trò

Bạn là **Senior Embedded Game Engineer / LuaS30 Runtime Engineer** chuyên:

- Nokia S30+
- **Nokia 225 Dual SIM RM-1011**
- MediaTek MRE / VXP
- **MTK6260** / MTK6261
- Lua 5.1
- LuaS30 Engine
- MREmu
- hệ thống QVGA 240×320
- thiết bị RAM thấp khoảng 1 MB
- game chạy mục tiêu khoảng 15 FPS

Nhiệm vụ của bạn là **sửa trực tiếp project hiện tại đang bị lỗi màn hình đen khi chạy trên LuaS30/MREmu/VXP**.

Không được chỉ giải thích lý thuyết.  
Phải kiểm tra source thật, tìm đúng nguyên nhân, sửa code, thêm test và tạo lại bản release.

---

## 0. CẤU HÌNH NOKIA 225 BẮT BUỘC TRƯỚC KHI DEBUG GAME

Project mục tiêu hiện tại là:

```text
Model          Nokia 225 Dual SIM
Type           RM-1011
Platform       Series 30+ / MediaTek MRE
Chipset        MTK6260
Display        240×320 QVGA
CPU            ARMv5TE
Endian         little
Code model     PIC / PIE
Lua            5.1
Target FPS     15
Heap RAM       1024 KB
MRE API        Audio File ProMng
Compat profile nokia225-rm1011
```

Nếu thanh trạng thái của LuaS30 IDE/VXPEmu vẫn hiện:

```text
MRE/VXP Generic
```

thì **không được tiếp tục kết luận gameplay hoặc renderer đã sai**.

Phải kiểm tra lại project metadata trước.

Đối với project Nokia 225, `project.json` phải có ít nhất:

```json
{
  "name": "CatBoxMRE",
  "app_version": "0.1.3",
  "vendor": "VXPstore",
  "appid": 123456789,
  "ram_kb": 1024,
  "screen_width": 240,
  "screen_height": 320,
  "resolution": "240x320",
  "mediatek_chipset": "MTK6260",
  "compat_profile": "nokia225-rm1011",
  "mre_api": "Audio File ProMng"
}
```

`appid` phải là số dương hợp lệ của project hiện tại.

Không hard-code lại AppID của project khác.

Project được tạo từ LuaS30 IDE phải có thêm:

```text
.luas30/
    mre_sdk.json
```

Không được bỏ thư mục `.luas30` khi copy source vào project do IDE tạo.

`project.json` và `.luas30/mre_sdk.json` phải mô tả cùng một target:

```text
240x320
MTK6260
1024 KB
nokia225-rm1011
Audio File ProMng
Nokia 225 / RM-1011
```

Nếu hai file lệch nhau, ưu tiên sửa cấu hình project thay vì sửa gameplay.

---

## 0.1. CÁCH TẠO PROJECT ĐÚNG TRONG LUAS30 IDE

Khi tạo mới:

```text
File
→ New Project
→ Cấu hình MediaTek MRE SDK
```

Điền:

```text
APPNAME      CatBoxMRE
APPVER       phiên bản hiện tại
VENDOR       VXPstore hoặc vendor của project

Resolution   240x320 (QVGA - Chuẩn Nokia)
Chipset      MTK6260 (Nokia 220, 225)
Heap RAM     1024 KB
```

Sau đó nhấn:

```text
Lưu thiết lập
```

IDE phải tự tạo:

```text
project.json
.luas30/mre_sdk.json
AppID riêng
```

Sau đó mới copy:

```text
main.lua
main_dev.lua
src/
assets/
docs/
tools/
conf.lua
```

vào project.

**Không xóa `.luas30`.**

Sau khi copy xong:

1. đóng project;
2. mở lại project;
3. kiểm tra project metadata;
4. Build lại;
5. chỉ Run VXP vừa build xong.

---

## 0.2. BẮT BUỘC KIỂM TRA PROFILE TRƯỚC BUILD

Thêm script:

```text
tools/check_nokia225_config.py
```

Script phải kiểm:

```text
project.json tồn tại
.luas30/mre_sdk.json tồn tại

screen_width  == 240
screen_height == 320
resolution    == 240x320
ram_kb        == 1024
chipset       == MTK6260
profile       == nokia225-rm1011
MRE API       == Audio File ProMng
```

Nếu sai:

```text
FAIL
```

Build phải dừng.

Ví dụ:

```text
[PASS] project compat_profile
[PASS] project chipset
[PASS] project resolution
[PASS] project RAM
[PASS] project MRE API
[PASS] studio compat_profile
[PASS] studio chipset
[PASS] studio resolution
[PASS] studio RAM
[PASS] studio device

NOKIA225_CONFIG_OK
```

Nếu IDE/build vẫn chọn Generic:

```text
[FAIL] Expected nokia225-rm1011 but active profile is Generic
```

Không được tiếp tục đóng gói release.

---

## 0.3. KHÔNG DÙNG “GENERIC” ĐỂ XÁC NHẬN NOKIA 225

Phân biệt rõ:

```text
Generic MRE/VXP
```

và:

```text
Nokia 225 RM-1011 / nokia225-rm1011
```

Generic có thể hữu ích cho emulator/research nhưng không được dùng như bằng chứng rằng project đã cấu hình đúng Nokia 225.

Nếu mục tiêu là Nokia 225:

```text
compat_profile = nokia225-rm1011
```

phải xuất hiện trong metadata project.

Nếu build system hỗ trợ native MRE SDK profile, profile Nokia 225 phải được chọn rõ.

Nếu SDK cần thiết chưa tồn tại, build phải báo lỗi sớm thay vì tự đổi im lặng sang Generic.

---

## 0.4. KIỂM TRA FILE ẨN `.luas30`

Trên Windows Explorer, `.luas30` có thể bị bỏ sót khi copy ZIP/thư mục.

Phải xác nhận:

```text
CatBoxMRE/
├── .luas30/
│   └── mre_sdk.json
├── project.json
├── conf.lua
├── main.lua
└── ...
```

Nếu source ZIP thiếu `.luas30/mre_sdk.json`, hãy tạo lại từ wizard hoặc bổ sung đúng metadata.

Không dùng project ZIP bị mất hidden configuration để test compatibility.

---

## 1. TRIỆU CHỨNG CẦN KHẮC PHỤC

Project có thể:

- build thành công;
- không báo syntax error;
- Lua có thể đã load;
- nhưng MREmu hoặc thiết bị chỉ hiển thị **màn hình đen**;
- không thấy splash;
- không thấy menu;
- không thấy text;
- không thấy sprite;
- game dường như không render frame.

Không được mặc định cho rằng đây là lỗi asset.

Phải kiểm tra theo thứ tự:

1. lifecycle callback;
2. graphics API;
3. clear/framebuffer;
4. flush/present;
5. màu RGB565;
6. input callback;
7. image API;
8. runtime error bị nuốt;
9. asset;
10. memory/OOM.

---

## 2. NGUYÊN NHÂN QUAN TRỌNG CẦN KIỂM TRA ĐẦU TIÊN

LuaS30 hiện tại sử dụng global table:

```lua
engine
```

Lifecycle chuẩn:

```lua
function engine.load()
end

function engine.update(dt)
end

function engine.draw()
end

function engine.keypressed(key)
end

function engine.keyreleased(key)
end

function engine.pause()
end

function engine.resume()
end

function engine.quit()
end
```

KHÔNG được chỉ dựa vào:

```lua
function update(dt)
end

function draw()
end

function key_down(k)
end
```

nếu runtime không gọi các callback toàn cục đó.

Nếu project đang có:

```lua
function update(dt)
    Game.update(dt)
end

function draw()
    Game.draw()
end
```

thì phải tạo bridge đúng chuẩn:

```lua
local runtime_engine = engine

function runtime_engine.load()
    Game.init()
end

function runtime_engine.update(dt)
    Game.update(dt or (1 / 15))
end

function runtime_engine.draw()
    Game.draw()
end

function runtime_engine.keypressed(key)
    Engine.key_down(key)
end

function runtime_engine.keyreleased(key)
    Engine.key_up(key)
end
```

Không overwrite mất các hàm graphics có sẵn của `engine`.

---

## 3. KHÔNG ĐƯỢC GHI ĐÈ GLOBAL `engine`

Đây là lỗi cực kỳ nguy hiểm.

Ưu tiên kiểm tra trực tiếp:

```lua
if type(engine) ~= "table" then
    error("LuaS30 engine table is missing")
end
```

Không phụ thuộc bắt buộc vào `_G`, `rawget(_G, ...)` hoặc cơ chế global lookup không cần thiết nếu runtime đã cung cấp trực tiếp `engine`.

Sai:

```lua
engine = {}
```

hoặc:

```lua
Engine = engine
engine = {}
```

nếu điều này làm mất API native runtime.

Global `engine` được LuaS30 Runtime cung cấp.

Project nên dùng wrapper riêng:

```lua
Engine = Engine or {}
```

và giữ:

```lua
local Native = engine
```

Ví dụ:

```lua
Engine.native = engine
```

Không được phá:

```lua
engine.rect
engine.text
engine.clear
engine.flush
engine.image
engine.image_region
engine.tick_ms
engine.exit
```

---

## 3.1. KIỂM TRA LUA 5.1 PARSE TRƯỚC KHI DEBUG RENDER

Một lỗi parse trong `main.lua` có thể tạo đúng triệu chứng:

```text
VXPEmu Running
màn hình đen
không có splash
không có log từ Lua
```

Phải kiểm tra các từ khóa Lua dùng sai làm key.

Sai:

```lua
local keys = {
    return = "5"
}
```

`return` là keyword Lua.

Đúng:

```lua
local keys = {
    ["return"] = "5"
}
```

Các keyword phải chú ý:

```text
and
break
do
else
elseif
end
false
for
function
if
in
local
nil
not
or
repeat
return
then
true
until
while
```

Bắt buộc parse/check production `main.lua` trước khi chạy emulator.

Nếu có Lua 5.1 compiler/interpreter:

```text
luac -p main.lua
```

hoặc test tương đương.

Không debug framebuffer trước khi source đã parse PASS.

---

## 4. SỬA GRAPHICS ADAPTER

Không được giả định graphics API là global function như:

```lua
draw_rect(...)
vm_graphic_fill_rect(...)
draw_text(...)
image_load(...)
```

LuaS30 hiện tại ưu tiên:

```lua
engine.clear(color)
engine.rect(x, y, w, h, color)
engine.text(x, y, text, color)
engine.image(x, y, path)
engine.image_region(path, sx, sy, sw, sh, dx, dy)
engine.flush()
```

Wrapper phải ưu tiên LuaS30 `engine.*`.

Ví dụ:

```lua
Engine = Engine or {}

local native = engine

function Engine.init()
    Engine.native = native

    Engine.api_clear = native and native.clear
    Engine.api_rect = native and native.rect
    Engine.api_text = native and native.text
    Engine.api_image = native and native.image
    Engine.api_image_region = native and native.image_region
    Engine.api_flush = native and native.flush
    Engine.api_tick = native and native.tick_ms
    Engine.api_exit = native and native.exit
end
```

---

## 5. BẮT BUỘC CLEAR FRAME

Trong mỗi frame phải có clear trước khi render.

Ví dụ:

```lua
function Render.draw(g)
    Engine.clear(0x87CEEB)

    -- draw background
    -- draw map
    -- draw actors
    -- draw UI
end
```

Hoặc trong wrapper:

```lua
function Engine.clear(color)
    if Engine.native and type(Engine.native.clear) == "function" then
        Engine.native.clear(Engine.to_native_color(color))
        return true
    end

    if Engine.native and type(Engine.native.rect) == "function" then
        Engine.native.rect(0, 0, 240, 320, Engine.to_native_color(color))
        return true
    end

    return false
end
```

Nếu không clear framebuffer đúng cách, emulator có thể tiếp tục hiển thị nền đen.

---

## 6. BẮT BUỘC FLUSH / PRESENT FRAME

Sau khi render toàn bộ frame:

```lua
Engine.flush()
```

Wrapper:

```lua
function Engine.flush()
    local n = Engine.native

    if n and type(n.flush) == "function" then
        n.flush()
        return true
    end

    return false
end
```

Luồng draw chuẩn:

```lua
function engine.draw()
    Game.draw()
    Engine.flush()
end
```

Hoặc:

```lua
function Game.draw()
    Render.draw(Game)
    Engine.flush()
end
```

Chỉ gọi **một lần mỗi frame**.

Không gọi flush cho từng sprite.

---

## 7. RGB888 VS RGB565

Không được giả định màu:

```lua
0xRRGGBB
```

được native runtime hiểu trực tiếp.

Nhiều MRE/LuaS30 backend dùng RGB565.

Phải có convert:

```lua
function Engine.rgb565(rgb)
    local r = math.floor(rgb / 65536) % 256
    local g = math.floor(rgb / 256) % 256
    local b = rgb % 256

    local r5 = math.floor(r * 31 / 255)
    local g6 = math.floor(g * 63 / 255)
    local b5 = math.floor(b * 31 / 255)

    return r5 * 2048 + g6 * 32 + b5
end
```

Tốt hơn nếu runtime có:

```lua
engine.color(r, g, b)
```

thì ưu tiên:

```lua
function Engine.color(rgb)
    local r = math.floor(rgb / 65536) % 256
    local g = math.floor(rgb / 256) % 256
    local b = rgb % 256

    if Engine.native and type(Engine.native.color) == "function" then
        return Engine.native.color(r, g, b)
    end

    return Engine.rgb565(rgb)
end
```

Cache màu thường dùng:

```lua
Engine.colors = {
    BLACK = Engine.color(0x000000),
    WHITE = Engine.color(0xFFFFFF),
    SKY   = Engine.color(0x87CEEB),
    GRASS = Engine.color(0x55C96A),
}
```

Không convert màu hàng nghìn lần mỗi frame nếu tránh được.

---

## 8. TEXT PHẢI CÓ FALLBACK

Wrapper:

```lua
function Engine.text(x, y, s, color)
    local n = Engine.native

    if n and type(n.text) == "function" then
        n.text(
            math.floor(x),
            math.floor(y),
            tostring(s),
            Engine.color(color or 0xFFFFFF)
        )
        return true
    end

    return false
end
```

Nếu text không hiện nhưng rect vẫn hiện:

- không được kết luận là toàn bộ renderer hỏng;
- debug bằng hình chữ nhật trước;
- sau đó kiểm tra font/text API.

---

## 9. TEST RENDER TỐI THIỂU TRƯỚC GAMEPLAY

Trước khi load toàn game, tạo test đơn giản:

```lua
function engine.load()
end

function engine.update(dt)
end

function engine.draw()
    engine.clear(engine.color(20, 30, 40))

    engine.rect(
        20,
        20,
        100,
        50,
        engine.color(255, 0, 0)
    )

    engine.text(
        30,
        90,
        "VIDEO OK",
        engine.color(255, 255, 255)
    )

    engine.flush()
end
```

Nếu test này vẫn đen:

KHÔNG sửa gameplay.

Phải điều tra:

- runtime graphics bridge;
- framebuffer;
- layer;
- flush;
- emulator compatibility;
- profile device.

Nếu test này hiện:

renderer native OK.

Sau đó mới đưa game code trở lại.

---

## 10. BOOT SELF TEST

Thêm boot diagnostics trong 2–3 giây đầu:

```lua
BOOT = {
    rect = false,
    text = false,
    image = false,
    flush = false
}
```

Splash debug:

```lua
function DebugBoot.draw()
    Engine.clear(0x102030)

    BOOT.rect = Engine.rect(8, 8, 40, 20, 0xFF0000)
    BOOT.text = Engine.text(8, 36, "BOOT", 0xFFFFFF)

    Engine.flush()
end
```

Nếu hỗ trợ log:

```lua
engine.log("BOOT rect=" .. tostring(BOOT.rect))
engine.log("BOOT text=" .. tostring(BOOT.text))
```

Không tạo string log liên tục trong gameplay.

Chỉ log startup / lỗi.

---

## 11. INPUT PHẢI DÙNG TÊN PHÍM ĐÚNG

LuaS30 có thể gửi:

```text
up
down
left
right
ok
softleft
softright
back
clear
0 1 2 3 4 5 6 7 8 9
*
#
```

Không được chỉ kiểm:

```lua
"LEFT"
"RIGHT"
"UP"
"SOFTLEFT"
```

Wrapper phải normalize.

Ví dụ:

```lua
local key_alias = {
    left = "LEFT",
    right = "RIGHT",
    up = "UP",
    down = "DOWN",
    ok = "5",
    softleft = "SOFTLEFT",
    softright = "SOFTRIGHT",
    back = "BACK"
}

function Engine.key_down(k)
    k = tostring(k):lower()

    local mapped = key_alias[k] or k

    Engine.keys[k] = true
    Engine.keys[mapped] = true
end

function Engine.key_up(k)
    k = tostring(k):lower()

    local mapped = key_alias[k] or k

    Engine.keys[k] = false
    Engine.keys[mapped] = false
end
```

---

## 12. IMAGE API PHẢI LÀ OPTIONAL

Game không được đen màn hình chỉ vì atlas lỗi.

Sai:

```lua
atlas = engine.image_load("sprite.png")
engine.image_region(atlas, ...)
```

nếu API đó không tồn tại.

Đúng:

```lua
Sprites.atlas_enabled = false

function Sprites.load()
    if not Engine.has_images() then
        return
    end

    Sprites.atlas_enabled = true
end
```

Draw:

```lua
if not Sprites.draw("cat", x, y) then
    Render.draw_cat_procedural(x, y)
end
```

Nếu image API lỗi một lần:

```lua
Sprites.atlas_enabled = false
```

Không `pcall()` image API lỗi lại mỗi frame.

---

## 13. KHÔNG ĐƯỢC DÙNG ASSET LỖI LÀM BLOCK STARTUP

Startup phải hoạt động dù:

```text
assets/sprite_atlas.png
```

không load được.

Splash/menu phải có thể render bằng:

```lua
rect()
text()
```

Nếu thiếu ảnh:

```text
ATLAS OFF
```

nhưng game vẫn chạy.

---

## 14. KHÔNG NUỐT LỖI GAMEPLAY BẰNG `pcall`

Không được làm:

```lua
pcall(function()
    Game.update(dt)
    Game.draw()
end)
```

rồi bỏ qua error.

Điều này có thể tạo triệu chứng:

```text
màn hình đen
không log
không crash rõ ràng
```

`pcall` chỉ dùng tại boundary:

- image loading;
- audio API;
- file I/O;
- optional native capability.

Gameplay Lua phải báo lỗi rõ khi development.

---

## 15. BOOT ERROR SCREEN

Nếu có lỗi startup được phát hiện, không giữ màn hình đen.

Thêm state:

```lua
Game.boot_error = nil
```

Nếu critical API thiếu:

```lua
Game.boot_error = "NO GRAPHICS API"
```

Draw fallback:

```lua
if Game.boot_error then
    if Engine.can_rect() then
        Engine.clear(0x000000)
        Engine.rect(4, 4, 232, 80, 0x660000)
        Engine.text(10, 10, "BOOT ERROR", 0xFFFFFF)
        Engine.text(10, 30, Game.boot_error, 0xFFFFFF)
        Engine.flush()
    end
    return
end
```

Mục tiêu là:

**không bao giờ silent black screen nếu graphics cơ bản vẫn hoạt động.**

---

## 16. KHỞI TẠO ĐÚNG THỨ TỰ

Startup nên là:

```text
runtime engine available
↓
Engine.init()
↓
verify graphics
↓
init cached colors
↓
Save.load()
↓
Sprites.load()
↓
Audio.init()
↓
Game.init()
↓
state = splash
```

Không load atlas trước khi Engine wrapper biết capability.

Không load resource nhiều lần.

---

## 17. SỬA `bundle_main.py`

Production vẫn phải single-file.

Thứ tự bundle cần hợp lý:

```python
ORDER = [
    "engine",
    "stage_data",
    "sprites",
    "audio",
    "save",
    "debug",
    "render",
    "game",
]
```

Cuối `main.lua` phải cài callback LuaS30.

Ví dụ:

```lua
local LS30 = engine

if type(LS30) == "table" then

    function LS30.load()
        Game.init()
    end

    function LS30.update(dt)
        Game.update(dt or (1 / 15))
    end

    function LS30.draw()
        Game.draw()
        Engine.flush()
    end

    function LS30.keypressed(k)
        Engine.key_down(k)
    end

    function LS30.keyreleased(k)
        Engine.key_up(k)
    end

end
```

Nếu cần backward compatibility desktop stub, có thể thêm:

```lua
function update(dt)
    Game.update(dt or (1 / 15))
end

function draw()
    Game.draw()
end
```

nhưng callback `engine.*` phải là callback chính trên LuaS30.

---

## 18. MAIN_DEV VÀ MAIN PRODUCTION PHẢI CÙNG HÀNH VI

Không để:

```text
main_dev.lua chạy
main.lua đen màn hình
```

Phải có test cho **production `main.lua` thật**.

Test phải mô phỏng:

```lua
require = nil
package = nil
dofile = nil
loadfile = nil
```

nhưng vẫn cung cấp:

```lua
engine = {
    clear = ...,
    rect = ...,
    text = ...,
    flush = ...,
    color = ...
}
```

Sau load phải assert:

```lua
assert(type(engine.load) == "function")
assert(type(engine.update) == "function")
assert(type(engine.draw) == "function")
assert(type(engine.keypressed) == "function")
assert(type(engine.keyreleased) == "function")
```

---

## 19. SMOKE TEST BẮT BUỘC PHÁT HIỆN MÀN HÌNH ĐEN

Stub engine phải đếm draw call.

Ví dụ:

```lua
TEST = {
    clear = 0,
    rect = 0,
    text = 0,
    flush = 0
}

engine = {}

function engine.color(r,g,b)
    return 0
end

function engine.clear(c)
    TEST.clear = TEST.clear + 1
end

function engine.rect(x,y,w,h,c)
    TEST.rect = TEST.rect + 1
end

function engine.text(x,y,s,c)
    TEST.text = TEST.text + 1
end

function engine.flush()
    TEST.flush = TEST.flush + 1
end
```

Sau:

```lua
engine.load()

for i = 1, 60 do
    engine.update(1/15)
    engine.draw()
end
```

Bắt buộc:

```lua
assert(TEST.clear > 0)
assert(TEST.rect > 0)
assert(TEST.text > 0)
assert(TEST.flush > 0)
```

Nếu:

```text
clear == 0
rect == 0
flush == 0
```

thì test phải:

```text
FAIL: BLACK SCREEN RENDER PATH
```

Không được báo test PASS.

---

## 20. TEST GAMEPLAY SAU KHI RENDER PASS

Sau boot test:

```lua
engine.keypressed("ok")
engine.update(1/15)
engine.keyreleased("ok")
```

Kiểm tra state:

```lua
splash → menu
menu → play
```

Tiếp theo mô phỏng:

```text
right
jump
pause
resume
restart
```

Kiểm tra draw vẫn tăng.

---

## 21. TEST 26 LEVEL

Nếu project có 26 màn:

- validate tất cả stage;
- không stage nào có enemy vượt pool;
- không box vượt pool;
- spawn/goal nằm trong map;
- `solids` có kích thước hợp lệ;
- hazard đúng định dạng;
- goal không nằm ngoài width.

Không cần play tự động hoàn chỉnh từng màn để test startup, nhưng phải test load toàn bộ:

```lua
for i=1,#StageData.stages do
    Game.load_level(i)
    engine.update(1/15)
    engine.draw()
end
```

Không màn nào được crash hoặc mất renderer.

---

## 22. RAM / OOM KHÔNG ĐƯỢC LÀM MÀN HÌNH ĐEN

Không tạo table mới hàng loạt mỗi frame.

Không tạo:

```lua
{x,y,w,h}
```

hàng nghìn lần trong draw loop nếu có thể tránh.

Object động dùng pool.

Atlas load một lần.

Không `collectgarbage("collect")` mỗi frame.

Incremental GC khoảng:

```text
2–4 giây
```

Full GC chỉ ở:

- load level;
- quay menu;
- restart;
- explicit debug.

---

## 23. DEBUG OVERLAY

Giữ:

```text
# = toggle debug
* = next page
9 = force GC
```

Thêm thông tin:

```text
DRAW OK
CLEAR count
RECT count
TEXT count
FLUSH count
ATLAS ON/OFF
ENGINE API OK/FAIL
```

Nếu native runtime không cung cấp draw counters thì debug chỉ hiển thị capability.

---

## 24. THỨ TỰ CHẨN ĐOÁN KHI VẪN ĐEN

Nếu sau sửa vẫn đen:

### A. Kiểm tra lifecycle

Log:

```text
LOAD
UPDATE
DRAW
```

Nếu không có DRAW:

lỗi callback/runtime.

### B. DRAW có chạy nhưng không thấy gì

Test:

```lua
engine.clear(RED)
engine.flush()
```

Nếu vẫn đen:

lỗi framebuffer/flush/profile.

### C. Clear hiện nhưng rect không hiện

Kiểm tra:

```lua
engine.rect
RGB565
clip
layer
```

### D. Rect hiện nhưng text không hiện

Chỉ sửa font/text API.

### E. Procedural art hiện nhưng atlas không hiện

Chỉ sửa image capability/path/decoder.

### F. Emulator hiện nhưng thiết bị thật đen

Đây là vấn đề profile/firmware ABI.

Không sửa gameplay để chữa lỗi ABI.

---

## 25. KHÔNG ĐƯỢC OVERCLAIM

Phân biệt:

```text
HOST_TESTED
EMULATOR_ONLY
BOOTS_ON_HARDWARE
SMOKE_TESTED
ENDURANCE_TESTED
```

Nếu chưa chạy trên Nokia thật:

không được tuyên bố hardware-compatible.

Nếu chỉ chạy Lua stub:

chỉ được nói:

```text
host/runtime API smoke test passed
```

---

## 26. FILE CẦN KIỂM TRA / SỬA

Ít nhất kiểm tra:

```text
main.lua
main_dev.lua
src/engine.lua
src/game.lua
src/render.lua
src/sprites.lua
src/debug.lua
tools/bundle_main.py
tools/smoke_test.py
tools/validate_project.py
tools/check_nokia225_config.py
project.json
.luas30/mre_sdk.json
conf.lua
```

Nếu project đang dùng LuaS30 Engine repository thì cũng kiểm:

```text
doc/ai/SKILL.md
doc/ai/PROMPT.md
doc/API.md
profiles/<target>.json
templates/basic/
engine/src/runtime_lua.c
engine/src/runtime_bridge.c
```

Không sửa runtime native nếu lỗi chỉ nằm ở project callback.

---

## 27. ACCEPTANCE CRITERIA

Chỉ xem là sửa xong khi:

- `project.json` xác nhận `MTK6260`;
- `project.json` xác nhận `240x320`;
- `project.json` xác nhận `ram_kb = 1024`;
- `project.json` xác nhận `compat_profile = nokia225-rm1011`;
- `.luas30/mre_sdk.json` tồn tại và đồng bộ;
- Nokia 225 config validator PASS;
- IDE/build không âm thầm fallback sang Generic;

- startup không còn màn hình đen;
- `engine.load()` được runtime gọi;
- `engine.update()` được runtime gọi;
- `engine.draw()` được runtime gọi;
- `engine.clear()` chạy;
- có ít nhất một `rect()` hiện;
- `engine.flush()` chạy;
- splash xuất hiện;
- menu xuất hiện;
- input `ok/left/right/up/down` hoạt động;
- game vào được level;
- atlas hỏng vẫn có procedural art;
- audio thiếu vẫn chạy;
- save thiếu vẫn chạy;
- production `main.lua` không cần `src/*.lua`;
- production chạy với:

```lua
require = nil
package = nil
dofile = nil
loadfile = nil
```

- smoke test phát hiện được trường hợp draw call bằng 0;
- load được toàn bộ level;
- không tạo object tăng vô hạn;
- không dùng full GC mỗi frame.

---

## 28. KẾT QUẢ PHẢI TRẢ VỀ

Sau khi sửa hãy cung cấp:

1. nguyên nhân màn hình đen;
2. danh sách file đã sửa;
3. diff quan trọng;
4. Source ZIP;
5. VXP-ready ZIP;
6. kết quả validator;
7. kết quả black-screen smoke test;
8. draw-call report;
9. compatibility status;
10. hướng dẫn chạy MREmu.

Ví dụ report:

```text
BLACK SCREEN FIX REPORT

Lifecycle:
engine.load          PASS
engine.update        PASS
engine.draw          PASS
engine.keypressed    PASS
engine.keyreleased   PASS

Graphics:
engine.clear         PASS
engine.rect          PASS
engine.text          PASS
engine.flush         PASS

Runtime smoke:
clear calls          > 0
rect calls           > 0
text calls           > 0
flush calls          > 0

Production bundle:
require=nil          PASS
package=nil          PASS
dofile=nil           PASS
loadfile=nil         PASS

Atlas missing:
procedural fallback  PASS

Result:
BLACK SCREEN PATH FIXED
```

---

## 28.1. BÁO CÁO CẤU HÌNH NOKIA 225 BẮT BUỘC

Report cuối phải có thêm:

```text
NOKIA 225 CONFIG REPORT

Device:
model               Nokia 225 Dual SIM
type                RM-1011
chipset             MTK6260
resolution          240x320
heap                1024 KB
cpu                 ARMv5TE
lua                 5.1

Project:
project.json         PASS
.luas30/mre_sdk.json PASS
compat_profile       nokia225-rm1011
mre_api              Audio File ProMng
AppID                valid unique positive id

Runtime:
engine table         PASS
Lua parse            PASS
load callback        PASS
draw callback        PASS
flush                PASS

IDE:
generic fallback     NO
nokia profile        ACTIVE/CONFIGURED

Result:
NOKIA225_CONFIG_OK
```

Nếu không xác minh được profile thực tế mà IDE dùng:

```text
PROFILE STATUS: UNRESOLVED
```

Không ghi `PASS`.

---

## 28.2. NẾU VẪN ĐEN SAU KHI PROFILE ĐÚNG

Chỉ sau khi Nokia 225 config PASS mới tiếp tục theo thứ tự:

```text
1. main.lua parse
2. engine lifecycle bind
3. engine.load log
4. engine.draw log
5. engine.clear
6. engine.rect
7. engine.flush
8. RGB565
9. clip / framebuffer
10. text
11. image atlas
12. gameplay
```

Tạo boot markers:

```text
[CatBox] BIND
[CatBox] LOAD ENTER
[CatBox] LOAD OK
[CatBox] DRAW1 ENTER
[CatBox] DRAW1 CLEAR
[CatBox] DRAW1 RECT
[CatBox] DRAW1 FLUSH
[CatBox] DRAW1 OK
```

Ý nghĩa:

```text
không có BIND
→ main.lua chưa load / parse fail

có BIND nhưng không LOAD
→ runtime lifecycle binding sai

có LOAD nhưng không DRAW1
→ draw callback/runtime timer sai

có DRAW1 ENTER nhưng không CLEAR
→ wrapper graphics lỗi

có CLEAR/RECT nhưng màn hình vẫn đen
→ framebuffer / layer / present / emulator profile

có FLUSH và procedural rect hiện
→ core renderer OK, kiểm asset sau
```

Không sửa gameplay trước khi xác định được mốc lỗi.

---

## 29. YÊU CẦU CUỐI

Hãy sửa trực tiếp project hiện tại.

Không viết lại project từ đầu nếu không cần.

Không xóa gameplay hiện có.

Không giảm số level.

Không thay đổi phong cách game nếu không liên quan lỗi.

Ưu tiên:

1. Nokia 225 project/profile đúng;
2. production `main.lua` parse PASS;
3. lifecycle đúng;
4. render được;
5. `clear/rect/flush` hoạt động;
6. tương thích LuaS30;
7. không OOM;
8. input;
9. asset;
10. hiệu ứng.

Nếu phát hiện nguyên nhân khác với dự đoán ban đầu, hãy sửa theo source thực tế và cập nhật lại báo cáo.

**Không kết thúc công việc khi game vẫn có thể mở ra màn hình đen.**
