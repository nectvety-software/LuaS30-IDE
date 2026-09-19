# Project Structure

> **Language:** English · [Tiếng Việt](../vi/Project-Structure.md)

This page describes two different things: the **IDE repository layout** (where the
engine lives) and the **layout of a user project** (where your game lives).

## IDE repository

```text
LuaS30-IDE/
├── VERSION · LICENSE · README.md · CHANGELOG.md · requirements-studio.txt
├── run.bat                 launcher
├── new_project.bat         create a project
├── build.bat / build_only.bat / build_single_exe.bat
├── LuaS30-IDE.cmd · .vbs · install_silent.cmd   post-install entry points
├── app-icon/               logo packaged into the exe/MSI
├── build/                  build output, runtime compat matrix
├── compat/                 synthetic MRE firmware manifests
├── doc/                    all markdown documentation (index: doc/INDEX.md;
│                           detailed changelog + validation: doc/release/)
├── emulator/               VXP emulator
├── engine/
│   ├── src/                runtime_entry.c, runtime_lua.c, runtime_bridge.c
│   └── linker/             luas30.ld
├── packaging/              Inno Setup / WiX for the MSI build
├── profiles/               device compatibility profiles (JSON)
├── sdk/luas30/
│   ├── include/ls30/       api.h base.h events.h graphics.h filesystem.h audio.h device.h compat.h
│   └── src/                abi_resolver.c  <- the portability boundary
├── studio/                 LuaS30 Studio (PySide6, PC only)
├── templates/              basic/ and device_probe/
├── toolchain/arm-gcc/      bundled ARM GCC
├── tools/                  build tooling + validators
├── vendor/lua-5.1.5/       Lua 5.1.5 source
└── wiki/                   bilingual wiki (vi/ + en/, strict 1-1 pairs)
```

`studio/` is **PC only** — PySide6 is never packaged into a VXP.

## User project

```text
Documents\LuaS30IDE\<ProjectName>\
├── project.json            build metadata
├── conf.lua                runtime configuration
├── main.lua                entry script
├── src/                    Lua modules
├── assets/                 images, audio, resources
├── .luas30/                IDE-private data
│   ├── ui_design.json
│   ├── mre_sdk.json
│   └── ai-backups/<timestamp>/
└── build/                  generated build output
```

### `project.json`

Example, from `templates/basic/project.json`:

```json
{
  "name": "LuaS30 Demo",
  "vendor": "LuaS30",
  "appid": 262567,
  "ram_kb": 1024,
  "screen_width": 240,
  "screen_height": 320,
  "fps": 15,
  "runtime_target": "mre-s30plus",
  "single_vxp": true,
  "compat_profile": "auto",
  "mre_api": "Audio File ProMng",
  "app_version": "1.0.0",
  "mediatek_chipset": "MTK6260",
  "mediatek_chipset_label": "MTK6260  (Nokia 220, 225)",
  "resolution": "240x320",
  "resolution_label": "240x320  (QVGA - Chuẩn Nokia)"
}
```

| Field | Meaning |
|---|---|
| `name` | display name of the application |
| `vendor` | developer name |
| `appid` | numeric AppID. **Every new project gets a fresh AppID.** Duplicate and Import also assign a new AppID; Rename **preserves** it |
| `ram_kb` | heap RAM granted to the runtime |
| `screen_width` / `screen_height` | resolution (S30+ is typically 240×320) |
| `fps` | target FPS; `dt` passed to `engine.update(dt)` is derived from it |
| `runtime_target` | runtime backend |
| `single_vxp` | always `true` — the single-VXP model |
| `compat_profile` | `auto` lets the build choose from the project configuration |
| `mre_api` | API permission group written into the manifest |
| `mediatek_chipset` | chipset chosen in the wizard |

**Project-specific** configuration belongs here, not hard-coded in Studio.

### `conf.lua`

```lua
config = {
    name = "LuaS30 Demo",
    screen_width = 240,
    screen_height = 320,
    fps = 15
}
return config
```

### `main.lua`

The entry script. The runtime calls callbacks on the global `engine`:

```lua
local E = engine
local bg = E.color(35, 83, 47)
local white = E.color(255, 255, 255)

function E.load()
    E.set_font(8)
end

function E.update(dt)
    -- dt-based logic
end

function E.draw()
    E.clear(bg)
    E.text(4, 4, "Hello", white)
end

function E.keypressed(k)
    if k == "0" then E.exit() end
end
```

Full lifecycle: `load()`, `update(dt)`, `draw()`, `keypressed(key)`,
`keyreleased(key)`, `pause()`, `resume()`, `quit()`.

### `src/` and `require()`

LuaS30 provides a resource-based `require()`:

```lua
local Player = require("src.player")
```

The runtime prefers `src/player.lub` and falls back to `src/player.lua`, which lets
development mode pack raw Lua without a host `luac`.

### `assets/`

Images, audio and resources. Paths in Lua are **relative to the project**:

```lua
engine.image(10, 10, "assets/image.png")
engine.audio_play("assets/sfx/select.mp3")
```

For S30+ prefer atlases, small images, RGB565-friendly art, short/mono audio and
asset reuse.

### `.luas30/`

IDE-private data, **not** game source:

| File | Contents |
|---|---|
| `ui_design.json` | source of truth for the UI Designer (v2, multi-screen). Generates `ui_design.lua` |
| `mre_sdk.json` | MediaTek MRE SDK configuration written by the wizard |
| `ai-backups/<timestamp>/` | copies of files before the AI Agent overwrites them |

### `build/`

Generated, safe to delete. When Project Storage **duplicates** a project it does not
copy `build`/`release` data.

## Paths and overrides

```text
%APPDATA%\LuaS30IDE\        config, logs, cache, temp, backups, venv
Documents\LuaS30IDE\        managed projects
```

Environment overrides (portable/test):

```text
LUAS30_APPDATA
LUAS30_DOCUMENTS
LUAS30_PROJECTS
```

Studio resolves the real Windows Documents folder, so a redirected Documents folder
works correctly.

## Dependency policy

Target-side code uses **only** LuaS30's stable API:

```text
engine.*     primary API
mre.*        compatibility alias
ls30_*       Native SDK layer when native extension work is required
```

Do not introduce on the target side:

```text
third-party Lua package managers
dynamic native libraries
vendor MRE SDK header packs
percommon.a / peraudio.a
direct firmware imports from application code
```

"Engine-only" means **no extra application runtime dependency and no vendor MRE SDK
build dependency** — not that the phone can run without its own firmware. Firmware
remains the unavoidable operating-system boundary for display, keypad, timers,
resources, files and audio.

See also [`doc/architecture/ARCHITECTURE.md`](../../doc/architecture/ARCHITECTURE.md)
and [`doc/configuration/USER_PATHS.md`](../../doc/configuration/USER_PATHS.md).
