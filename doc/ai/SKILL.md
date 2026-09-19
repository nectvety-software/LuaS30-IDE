# SKILL.md — LuaS30 IDE Development Skill

## Purpose

Use this skill when implementing, debugging, reviewing, packaging or documenting
**LuaS30 IDE**, its Studio, Native SDK, runtime, VXP build pipeline, emulator
workflow or Lua projects targeting VXP/S30+ devices.

This file defines repository-specific engineering rules. Treat repository source
as authoritative when it conflicts with assumptions.


## Mandatory AI Agent preflight

This repository uses a mandatory two-file agent contract.

**Before an AI agent creates, scaffolds, imports, migrates, generates or substantially
modifies any LuaS30 project, the agent must read both files in this order:**

```text
1. doc/ai/SKILL.md
2. doc/ai/PROMPT.md
```

After reading them, the agent must inspect the current engine source/config that is
relevant to the requested target. Do not create a project from remembered conventions,
old chat context, generic MRE knowledge or an older LuaS30 version.

For a new project, the minimum preflight is:

```text
doc/ai/SKILL.md
doc/ai/PROMPT.md
VERSION
README.md
doc/INDEX.md
profiles/<selected-target>.json
templates/basic/
```

If the exact target profile does not exist, inspect:

```text
profiles/generic-vxp-qvga.json
templates/device_probe/
sdk/luas30/include/ls30/
sdk/luas30/src/abi_resolver.c
```

Then either:

- use the conservative generic profile and clearly mark hardware compatibility as untested; or
- add a dedicated target profile/adapter first, validate it, then scaffold the application.

An agent must never skip this preflight merely because the requested project appears
small or similar to a previous project.


## Target dependency policy

### Application projects must be engine-only

A project created for a phone target should depend on the LuaS30 IDE API, not on
external runtime packages or vendor MRE SDK headers/libraries.

For target-side Lua/native project code, prefer:

```text
engine.*
mre.*              # compatibility alias only
ls30_*             # Native SDK layer when native extension work is required
```

Do not introduce device-side dependencies such as:

```text
third-party Lua package managers
dynamic native libraries
vendor MRE SDK header packs
percommon.a
peraudio.a
direct firmware imports from application code
```

The PC development environment may still use the bundled/managed Studio dependencies,
ARM toolchain and emulator. "No dependency" in this project means **no extra application
runtime dependency and no vendor MRE SDK build dependency**, not that the phone can run
without its own firmware services.

The device firmware remains the unavoidable operating-system boundary for screen,
keypad, timers, resources, files, audio and other platform services.


## Dedicated MRE engine per S30+ target

LuaS30 is allowed to specialize for individual VXP/MRE-capable S30+ devices without
forking the Lua game API.

Use this layering:

```text
Game / App
    ↓
stable engine.* Lua API
    ↓
LuaS30 Runtime
    ↓
device-specific LuaS30 profile/adapter
    ↓
LuaS30 Native SDK (ls30_*)
    ↓
single firmware ABI resolver boundary
    ↓
target S30+/VXP firmware
```

A target specialization should be data/adapter driven wherever possible.

Preferred locations:

```text
profiles/<device-id>.json
sdk/luas30/src/abi_resolver.c       # symbol aliases / ABI binding only
sdk/luas30/include/ls30/            # stable public Native SDK API
templates/device_probe/             # capability verification
```

Do not duplicate the entire engine for every phone unless the ABI/runtime genuinely
requires an incompatible implementation. Keep the project-facing API stable and isolate
differences below it.

### Device target decision

Before creating a project, determine one of these target modes:

```text
GENERIC_VXP
KNOWN_DEVICE_PROFILE
NEW_DEVICE_PORT
```

- `GENERIC_VXP`: use the conservative generic profile; no hardware compatibility claim.
- `KNOWN_DEVICE_PROFILE`: scaffold using the exact profile.
- `NEW_DEVICE_PORT`: create/test a profile and device probe before building the real app.

For a new device port, record compatibility using:

```text
UNTESTED
EMULATOR_ONLY
BOOTS_ON_HARDWARE
SMOKE_TESTED
ENDURANCE_TESTED
```


## Current architecture

```text
LuaS30 Studio
    ↓
Project files
    ↓
tools/build.py
    ↓
LuaS30 Runtime + Lua 5.1.5
    ↓
LuaS30 Native SDK (ls30_*)
    ↓
abi_resolver.c
    ↓
VXP-capable device firmware
```

## Authoritative files

Before changing a subsystem, inspect:

```text
VERSION
README.md
doc/INDEX.md

sdk/luas30/include/ls30/
sdk/luas30/src/abi_resolver.c
sdk/luas30/src/api.c

engine/src/runtime_entry.c
engine/src/runtime_lua.c
engine/src/runtime_bridge.c
engine/linker/luas30.ld

tools/build.py
tools/verify_elf.py
tools/vxp_pack.py
tools/run_emulator.py

profiles/*.json
templates/basic/
templates/device_probe/

studio/app/
```

## Non-negotiable rules

### 1. Do not reintroduce vendor MRE SDK build dependencies

Native build must not depend on:

```text
percommon.a
peraudio.a
vmsys.h
vmgraph.h
vmio.h
vmmm.h
```

### 2. Isolate firmware ABI

Firmware symbol names belong in:

```text
sdk/luas30/src/abi_resolver.c
```

Runtime code should call only `ls30_*` APIs.

If a firmware service is optional, expose a capability instead of making startup
depend on it.

### 3. Preserve Lua 5.1 compatibility

Do not silently introduce Lua 5.2+ syntax or APIs.

### 4. Preserve low-memory design

For S30+ targets:

- avoid allocations inside frame loops;
- avoid creating transient Lua tables every frame;
- cache RGB565 colors;
- reuse buffers/objects;
- prefer sprite atlas/tilemap;
- render only visible objects;
- keep audio/images optional;
- use conservative FPS/profile defaults.

### 5. Preserve user paths

Persistent app data:

```text
%APPDATA%\LuaS30IDE
```

Projects:

```text
Documents\LuaS30IDE\<ProjectName>
```

Do not put user settings, venv, cache or saves into the engine installation unless
the file is intentionally part of the shipped engine.

### 6. Build the exact artifact that is tested

Build → final VXP → SHA-256 → emulator must reference the same final file.

Do not claim emulator/device testing for a different or stale VXP.

### 7. Do not overclaim compatibility

Use these statuses:

```text
UNTESTED
EMULATOR_ONLY
BOOTS_ON_HARDWARE
SMOKE_TESTED
ENDURANCE_TESTED
```

A valid ELF or emulator boot is not proof that a physical Nokia/S30+ target works.

### 8. Keep credits current

When dependencies change, update:

```text
doc/legal/THIRD_PARTY_NOTICES.md
Studio About/Credits
doc/
```


### 9. UI icon policy

Do not use emoji or ad-hoc Unicode pictograms as Studio controls.

Use the centralized font-icon layer:

```text
studio/app/ui/icons.py
```

Preferred Windows font families:

```text
Segoe Fluent Icons
Segoe MDL2 Assets
```

Do not bundle or redistribute font files. Text arrows/separators are acceptable only
as content, not as substitutes for toolbar/menu icons.


### 10. Compact workbench command ownership

Avoid duplicate whole-screen tools and duplicate command buttons.

Canonical UI ownership:

```text
Activity Bar -> navigation only
Editor Bottom Panel -> Output / Build / Problems
Run menu -> build/emulator commands
Tools menu -> project validation/cleanup/folder utilities
About menu -> documentation/environment/credits
Command Palette -> searchable access to existing QAction commands
```

Do not create a separate Build page or Console page when the integrated bottom panel
already owns those functions. New buttons must execute real logic, not visual placeholders.

## Standard task workflow

### Step 1 — Read the agent contract and inspect

Before creating or modifying a project, read:

```text
doc/ai/SKILL.md
doc/ai/PROMPT.md
```

Then read the current implementation, selected device profile and relevant template.
Do not assume an older conversation description still matches repository source.

### Step 2 — Plan minimal architecture impact

Determine whether the change belongs in:

- Studio;
- build tooling;
- runtime;
- Native SDK;
- ABI resolver;
- device profile;
- Lua template/project.

### Step 3 — Implement

Keep changes modular. Do not duplicate firmware bindings in multiple source files.

### Step 4 — Validate

At minimum run:

```bat
python tools\validate_tree.py
python tools\validate_native_sdk.py
python tools\validate_complete.py
```

Also run Python syntax/compile checks for Studio/tooling changes.

For native changes, compile with bundled ARM GCC on Windows when available and
review ELF output.

### Step 5 — Test

Choose the correct level:

- source/unit validation;
- build;
- emulator;
- physical target.

For unknown phones, test `templates/device_probe` first.

### Step 6 — Document

Update relevant API/architecture/build/device docs and changelog.

## Native feature recipe

When adding a firmware-facing feature:

1. Add neutral type/constant declarations under `sdk/luas30/include/ls30/`.
2. Add public `ls30_*` function declaration.
3. Bind target symbol(s) only in `abi_resolver.c`.
4. Implement wrapper in SDK source.
5. Add capability bit if optional.
6. Add Lua bridge function only if Lua scripts need it.
7. Add autocomplete/docs if Lua API changed.
8. Add validation.
9. Test probe/emulator/hardware as appropriate.

## Studio feature recipe

For Studio UI/editor features:

- follow the compact VS Code-style UI;
- avoid large dashboard cards unless the view specifically needs them;
- keep Explorer/editor central;
- send build/search work off the UI thread where practical;
- write logs into the integrated bottom panel;
- preserve keyboard shortcuts;
- store per-user state under AppData.

## VXP build recipe

Use:

```bat
build_only.bat PROJECT_DIR
```

or:

```bat
python tools\build.py ^
  --project PROJECT_DIR ^
  --toolchain toolchain\arm-gcc ^
  --profile generic-vxp-qvga ^
  --no-run
```

Then inspect:

- ELF report;
- output VXP;
- SHA-256;
- sync manifest if emulator was used.

## Definition of done

A task is done only when:

- the mandatory `SKILL.md` + `PROMPT.md` preflight was followed for project-generation work;
- the selected target mode/profile is recorded and not guessed;

- source changes are complete;
- no forbidden Native SDK dependency is introduced;
- validation passes;
- documentation/changelog matches behavior;
- generated archives pass ZIP integrity;
- hardware/emulator claims accurately reflect what was actually tested.

## Response expectations for coding agents

When handing back work:

1. state what changed;
2. state validation actually performed;
3. state what could not be executed in the current environment;
4. provide full package and/or patch artifact;
5. do not fabricate successful hardware tests, compiler runs or emulator runs.


## Signing and direct-run safety contract

AI agents must never promise or implement a certificate/trust bypass in order to make a
VXP install on arbitrary retail devices.

For physical-device release work:

1. select the exact device profile;
2. read its `signing` policy;
3. use only a signing/binding mode the profile declares as accepted;
4. run `--release`;
5. inspect the generated VXP report and release manifest;
6. hardware-test the exact SHA-256 artifact before raising compatibility status.

If a firmware requires an unavailable manufacturer/developer credential, report that
constraint. Do not replace it with a self-signed key and claim equivalent trust.

For many devices, build separate profile-specific artifacts with `build_matrix.py`.

## Reverse-engineering protection contract

Agents may use legitimate IP-hardening features:

- stripped Lua 5.1 bytecode;
- Lua source comment/whitespace minification;
- native `--strip-unneeded`;
- hidden native visibility;
- release hashes/manifests.

Do not claim these make reverse engineering impossible. Do not embed signing private keys,
API secrets or server-side trust secrets into a VXP.


## Single-VXP project creation rule (1.8.1)

This rule supersedes earlier per-device release guidance.

AI Agents must create one project and one generic VXP build path.

Do not:

```text
create one project copy per phone
create one VXP filename per phone
ask the user to select a device profile for normal project builds
use build_matrix.py
bind the normal project artifact to a specific phone/SIM
```

The canonical output is:

```text
build/<ProjectName>.vxp
```

Handle device variation centrally in LuaS30 IDE through runtime capability detection,
the Native SDK and ABI resolver.

Do not claim that one generic VXP implies universal firmware trust. Portability of the
package and firmware acceptance/signing policy are separate concerns.


## Runtime compatibility implementation rule (1.8.2)

For Single-VXP firmware compatibility work, AI Agents must follow this order:

1. add/verify capability detection;
2. add a conservative ABI alias only when the alternate symbol uses the same expected signature;
3. add a fallback only when behavior can be safely emulated without guessing a firmware ABI;
4. expose the resulting state through `engine.runtime_compat()` if Lua code may need it;
5. keep the application artifact generic.

Do not solve a missing firmware API by creating a device-specific VXP or by casting a
different-signature function to the expected ABI.

Optional APIs should degrade gracefully. Required core groups must remain explicit and
must make compatibility `incompatible` when no safe fallback exists.


## Runtime compatibility matrix rule (1.8.3)

When adding or changing an ABI alias, capability rule, required runtime group or fallback:

1. update the target C runtime implementation;
2. update `compat/runtime_abi_contract.json` when symbol resolution changed;
3. add or update a firmware fixture/observed manifest under `compat/mre/`;
4. run `tools/runtime_compat_matrix.py`;
5. run `tools/validate_runtime_matrix.py`;
6. inspect native capabilities, selected aliases, fallbacks, level and final result.

Never label a synthetic fixture as real firmware evidence. Real firmware manifests must
use `evidence: observed` and must come from an actual exported-symbol inventory.


## Studio tab ownership rule (1.9)

When adding a Studio feature, decide whether it is a command or a persistent view.

Persistent tools must open through `EditorTabs.open_tool_tab(key, ...)` so the same key
focuses an existing tab instead of creating another page/window.

Canonical ownership:

```text
Activity Bar -> Explorer/Search + tool-tab navigation
Editor tab strip -> source editors + persistent tool views
Bottom Panel -> Output / Build / Problems only
Run menu -> build/run/clean/stop commands
Tools menu -> features that open tool tabs only
```

Do not reintroduce a `QStackedWidget` page switch for Assets, Designer, Emulator,
Settings, diagnostics or Project Storage.

Project-management operations must use the managed storage service and preserve unsaved
source files before rename/delete/switch operations.

## Workspace session rule (1.9.1)

When changing Studio tabs, editor groups, sidebar or bottom-panel architecture, preserve workspace-session compatibility.

Session state lives in:

```text
%APPDATA%\LuaS30IDE\config\workspace_session.json
```

Any new persistent tool tab must have a stable `luas30ToolKey` and must be restorable through `MainWindow._restore_tool_tab()`.

Do not store session state inside a user project. Project source and IDE session state are separate concerns.

Restore must tolerate missing project/files/tools without preventing Studio startup.


## Studio startup page rule (1.9.2)

The default Studio cold-start experience is the `Welcome` / Project Hub tab.

Agents modifying Studio startup must preserve:

```text
Welcome tab at group 0 / tab index 0
New Project
Open Project Folder
Import into Project Storage
Recent projects
Project Storage summary
Show Welcome page on startup
```

Workspace session restore still restores all editor groups/tabs in the background.
When `Show Welcome page on startup` is disabled, preserve the restored active tab.
Do not replace the full Project Storage manager with the Welcome page; Welcome is the
landing hub and Project Storage remains the detailed management tool.
\n\n## Integrated panel rule (1.9.3)\n\nStudio uses a VS Code-style bottom panel. Keep these canonical surfaces:\n\n```text\nCONSOLE\nBUILD\nPROBLEMS\nTERMINAL\n```\n\n`Console` is Studio/runtime log output. `Terminal` must be a real shell process, not a\nfake command parser. Panel toggles must preserve workspace-session state. Do not create\na duplicate standalone Terminal/Console editor tab when the bottom-panel surface already\nowns the workflow.\n

## Project Hub layout rule (1.9.4)

`Welcome` and `Project Storage` are project-management pages, not source-editor pages.

AI Agents changing Studio layout must keep these pages free of editor-only chrome:

```text
Activity Bar
Explorer / Search sidebar
Find / Replace
Bottom Console / Build / Problems / Terminal
```

The hide/show transition must be presentation-only. Preserve the editor's real sidebar
and panel visibility in workspace session state, then restore it when the user returns to
a source tab.


## Persistent editor chrome rule (1.9.5)

Explorer and Activity Bar visibility are independent persistent user preferences. Keep `Ctrl+B` for Explorer and `Ctrl+Alt+A` for Activity Bar. Project Hub may hide them physically but must not overwrite their saved editor state.


## Clean startup editor rule (1.9.6)

AI Agents modifying workspace/session behavior must preserve this invariant:

```text
STARTUP OR RESTART MUST NOT AUTO-OPEN SOURCE FILES
```

Do not restore persisted `file` or `untitled` tabs and do not automatically open
`main.lua` as a fallback.

It is valid to restore project context, editor-group layout, tool tabs, Explorer/Activity
Bar preferences and bottom-panel state. Source documents must require an explicit user
action after startup.


## MRE GCC build rule (1.9.7)

When modifying ARM GCC build/preflight code:

- generated C probe files must contain real line endings, never literal `\\n` text;
- preflight must test compile and link, not only `gcc --version`;
- use the shared MRE GCC flag functions so probe/runtime flags cannot silently diverge;
- preserve ARMv5TE, PIC, little-endian and `gcc_entry` linker semantics;
- do not add vendor MRE static-library/header dependencies to solve a toolchain problem.

The bundled compiler path is GCC. ADS/RVDS are architectural references only unless
their legal toolchains are explicitly provided by the user.


## Startup-screen preference rule (1.9.8)

AI Agents modifying Studio startup must preserve exactly three supported modes:

```text
welcome
project_hub
empty_editor
```

The setting belongs in Settings and is persisted as `startup.mode`.

Do not reintroduce a second startup checkbox on Welcome.

For every mode, startup/restart must continue to skip source and untitled editor tabs.
`empty_editor` additionally must not restore tool tabs or auto-open `main.lua`.


## Multi-toolchain MRE rule (1.10.0)

AI Agents must treat compiler choice as a build profile, not as an application fork.

Supported profile ids:

```text
gcc
rvds
ads12
auto
```

Keep compiler flags, tool detection and entry conventions centralized in
`tools/toolchain_profiles.py`.

Entry conventions:

```text
gcc   -> gcc_entry
rvds  -> rvct_entry
ads12 -> ads_entry (LuaS30 compatibility convention; overridable)
```

Do not claim ADS/RVDS execution was validated unless the actual proprietary compiler and
linker were run. They are not bundled with LuaS30.

Do not add cracked, redistributed or unlicensed proprietary ARM binaries to the repository.


## Bottom panel UX rule (1.10.1)

Console / Build / Problems / Terminal must be hidden by default after application startup.

Agents must preserve:

```text
Ctrl+`        terminal toggle
Ctrl+Shift+Y  console toggle
Ctrl+J        panel toggle
top-right panel close button
```

The panel may remember its active tab and preferred height, but startup restore must not
automatically make the panel visible.

Panel close is a visibility action, not a terminal-process kill action.


## Integrated terminal interaction rule (1.10.2)

The terminal must use one direct-edit surface. Do not reintroduce a separate command
QLineEdit or textbox below the output.

Preserve these invariants:

```text
historical output = selectable but protected from normal edits
current prompt line = editable
Enter = submit
Up/Down = history
Ctrl+L = clear
Ctrl+` = show/focus terminal
```

A hidden terminal remains alive until Kill Terminal is requested.


## Bottom panel HEX / AppID rules (1.10.3)

Preserve these invariants:

```text
BottomPanel tabs:
CONSOLE | BUILD | PROBLEMS | TERMINAL | HEX
```

Emulator Run must load the exact manifest VXP into HEX before launch.

Do not dump arbitrarily large VXP files into one Qt document; keep the HEX view paged.

Managed project identity rule:

```text
New / Duplicate / Import -> assign a new unused AppID
Rename / Open            -> preserve AppID
```

AppID uniqueness is checked against project.json files in the managed project storage.


## AI Workbench rules (1.11.0)

Keep the layout `Explorer | [Editor + Bottom Panel] | Chat AI`. The Compact Bottom Panel
must not span under Explorer or ChatAI.

Every tab strip must provide a right-click `Close All Tabs` command reaching all editor
groups while preserving unsaved-document confirmation.

ChatAI must load project/engine SKILLS.md, SKILL.md and PROMPT.md when present. Treat those
documents as instructions and ordinary source files as reference data.

Never persist provider API keys in workspace/session/provider config files. Exclude common
secret/credential/private-key files from codebase context.


## Physical S30+ compatibility rule (1.12.0)

When the target is real Series 30+ hardware, especially Nokia 225 Dual SIM RM-1011:

- prefer `s30plus-native` / `nokia225-rm1011` over the standalone resolver when a local
  MRE SDK is available;
- preserve the `gcc_entry -> vm_main -> luas30_runtime_main` entry chain;
- use ARMv5TE, PIC, little-endian and 240x320 Nokia defines;
- use the MRE SDK scatter script and its ARM GCC `per*.a` static libraries;
- keep IMSI as session-only sensitive data and never write the raw value into project,
  session, manifest, docs or logs;
- distinguish canonical VXP from optional device-install IMSI-bound VXP;
- never claim physical compatibility merely because VXPEmu/MoDis or static validation passes.


## MediaTek project creation rule (1.13.0)

All managed New Project entry points must open `MediaTekMREConfigDialog` before creating the
project folder. Do not restore the old `QInputDialog` project-name-only flow.

The wizard must preserve:

```text
APPNAME
APPVER
VENDOR
Resolution
MediaTek chipset
Heap RAM
unique auto AppID
```

Write the configuration to both `project.json` and `.luas30/mre_sdk.json`.

If Studio/CLI compatibility remains `auto`, the builder must honor the project's
`compat_profile`; an explicit user-selected build profile remains the override.

Do not fabricate undocumented VXP binary tags for APPVER. Preserve APPVER in metadata and
manifests until a verified binary tag mapping is available.


## AI reasoning-summary and shell rules (1.14.0)

ChatAI must never expose or request private raw chain-of-thought. The Studio may show only
concise, high-level reasoning/activity summaries intended for the user.

Shell control invariants:

```text
shell permission default = Ask before running
AI command executes in visible IntegratedTerminal
one shell action per model turn
AI-origin result only is returned to ChatAI
agent loop <= 6 turns per user request
```

Auto mode may execute only commands classified as safe/read-only. Sensitive, project-
mutating and dangerous commands require user approval. Dangerous commands require a
second explicit confirmation.

Never send raw environment secrets, API keys, passwords, IMSI, tokens or private keys to
an AI provider. Redact common secret environment values from shell output before returning
it to a remote model.

## AI Workbench v1 rules (1.15.0)

Preserve the four access modes:

```text
ask       -> review code + approve shell
edit_auto -> auto code + approve shell
plan      -> no edit/shell actions
full      -> auto code + auto safe/project shell, but sensitive/dangerous still confirm
```

Never interpret Full access as permission to bypass project-root edit boundaries, secret
redaction, destructive-command confirmation or API-key non-persistence.

AI code modifications must use the structured `luas30-edit` protocol and pass through
`AIChangeService`. Do not let provider text write arbitrary paths directly.

Keep the `AI Changes` diff review surface and backup existing files before replacement.

Provider Settings must expose Test Connection, Apply and Save & Close. API keys entered in
that dialog are session-only.

## Lua programming for S30+ MRE .vxp (ChatAI specialization)

ChatAI trong Studio làm việc chuyên cho **Lua 5.1 trên Nokia S30+ MRE**, chạy
trên VXPEngine 240x320 — không phải Love2D, không phải Android, không phải
Lua 5.3/5.4. Quy tắc bắt buộc:

1. **Chỉ dùng API có thật.** Trước khi sửa code chạm engine, đọc lõi bằng tool
   `engine` (khối `luas30-tool`, op `read`/`grep`/`glob`/`list`, đường dẫn tương
   đối IDE-root, chỉ các thư mục `templates`, `sdk`, `engine`, `compat`,
   `doc/ai`, `extensions`). Nguồn sự thật:
   - `templates/basic/src/engine.lua` — wrapper Lua mỏng quanh bảng global
     `engine`; đây là API mức dự án mà `main.lua`/`src/` thật sự gọi.
   - `engine/src/runtime_lua.c` — chỗ đăng ký bảng global `engine` (C→Lua);
     mọi hàm `engine.*` có thật đều được ghi danh tại đây, và hàm nào không xuất
     hiện ở đó thì **không tồn tại** để gọi.
   - `sdk/luas30/abi/symbols.json` — bảng ký hiệu MRE ABI mà runtime ánh xạ tới.
   - `compat/devices/` — hồ sơ thiết bị S30+ đã kiểm chứng.
   Bản đồ các tệp này luôn có trong `<engine_core>` của system prompt.
2. **Cấu trúc dự án chuẩn**: `main.lua` (điểm vào) + `conf.lua` (cấu hình
   VXPEngine) + `src/` (module riêng, `require` bằng dấu chấm `/` theo
   project.json) + `project.json` (manifest build .vxp). Giữ tương thích
   Lua 5.1: không goto-labelled kiểu 5.2, không integer division `//`,
   không bitwise operators — dùng `math.floor` và module bit có sẵn.
3. **Bộ nhớ thấp**: tránh bảng lớn tạm thời, tránh chuỗi động trong vòng lặp
   vẽ; tài nguyên ảnh nạp một lần qua engine, giải phóng khi đổi màn hình.
4. **Bàn phím S30+**: chỉ xử lý các khóa engine phát ra (theo `engine.lua`);
   không giả lập chuột/touch.
5. Khi người dùng mô tả công việc khớp một **extension đã cài** (xem
   `<installed_extensions>` trong system prompt), ưu tiên hướng dẫn dùng
   extension đó thay vì viết script cắt/tải/xử lý thủ công.

## Extension system (standard + authoring)

Mỗi extension là một thư mục trong `extensions/<id>/` của bản cài IDE:

- `extension.json` — manifest: `id` (bắt buộc trùng tên thư mục), `name`,
  `version`, `description`, `author`, `type` (hiện chỉ `"webview"`), `entry`
  (đường dẫn HTML tương đối trong thư mục extension), `icon` (tên Font Awesome
  `fa5s.*`), `requiresProject` (mặc định `true`).
- `ui/index.html` — giao diện web, chạy trong QWebEngineView, mở từ
  **Công cụ → Tiện ích mở rộng**.
- `SKILLS.md` (hoặc `SKILL.md`/`PROMPT.md`) — tài liệu mô tả chức năng + hợp
  đồng cầu nối; ChatAI tự nạp làm luật khi trả lời.

Cầu nối Studio tiêm `window.luaS30` (chỉ tồn tại khi mở trong IDE — trang phải
chạy được cả ở trình duyệt thường):

- `luaS30.project(cb)` → `{root, name}` hoặc `{root: null}`.
- `luaS30.writeFiles(files, cb)` → ghi `{path, text}` / `{path, base64}` tương
  đối trong thư mục dự án đang mở; callback `{ok, written, errors}`. Chặn
  đường dẫn thoát dự án, thư mục ẩn/sinh tự động và tệp bí mật.
- `luaS30.notify(message, level)` → status bar Studio.
- Sự kiện `luas30-bridge-ready` báo cầu nối đã sẵn sàng.

Extension hợp lệ được phát hiện động (không cần restart); manifest lỗi bị bỏ
qua và ghi vào `ExtensionService.last_errors`. Mẫu chuẩn đang hoạt động:
`extensions/sprite-sheet/`.
