# Getting Started

> **Language:** English · [Tiếng Việt](../vi/Getting-Started.md)

## 1. Requirements

| Item | Requirement |
|---|---|
| Operating system | Windows 10/11 |
| Python | 3.10 or newer |
| PySide6 | `PySide6>=6.7,<7` — the launcher installs it into a private venv |
| ARM GCC | already bundled in `toolchain/arm-gcc/` |
| Emulator | already bundled in `emulator/` |

You do **not** need to install an ARM toolchain or the emulator manually, and you
do **not** need a global PySide6 install — the launcher creates its own virtual
environment.

## 2. Open Studio

```bat
run.bat
```

Launcher modes:

```bat
run.bat --offline      use the cache, never touch the network
run.bat --online       allow dependency checks/updates
run.bat --deps-only    install dependencies and exit
run.bat --force-deps   reinstall dependencies regardless of version
```

Before opening Studio the launcher will:

1. create `%APPDATA%\LuaS30IDE\venv` if missing;
2. check dependency versions (installing only when they do not satisfy);
3. avoid network access when dependencies already match;
4. validate Native SDK / runtime / Studio;
5. check ARM GCC and the emulator;
6. open Studio.

### Per-user data directories

```text
%APPDATA%\LuaS30IDE\
├── config\      studio.ini, workspace_session.json, ai_*.json
├── logs\        launcher.log, environment.json
├── cache\
├── temp\
├── backups\
└── venv\        Python virtual environment
```

The engine installation is kept separate from user data, so the engine folder stays
effectively read-only during normal use. You can override the defaults with the
`LUAS30_APPDATA`, `LUAS30_DOCUMENTS` and `LUAS30_PROJECTS` environment variables
(intended for portable and test environments).

## 3. Create a project

```bat
new_project.bat HelloS30
```

Or in Studio: **File → New Project**.

In Studio, **New Project** first opens the **MediaTek MRE SDK configuration**
dialog so packaging metadata is chosen up front:

```text
APPNAME / APPVER / VENDOR
Resolution
MediaTek chipset
Heap RAM
```

Bundled chipset presets:

| Preset | Typical devices |
|---|---|
| `MTK6260` | Nokia 220, Nokia 225 |
| `MTK6261` | Nokia 3310 3G, Nokia 216 |
| `MTK6250` | Q-Mobile, K-Touch |
| `MTK6225` | Legacy MRE 2.0 |

Selecting `MTK6260` writes the `nokia225-rm1011` compatibility profile. Every new
project receives a **fresh AppID**, and the dialog writes its configuration to both
`project.json` and `.luas30/mre_sdk.json`.

Projects are created at:

```text
Documents\LuaS30IDE\<ProjectName>\
```

Studio resolves the real Windows Documents folder, so a redirected Documents folder
works correctly.

## 4. Key files

```text
HelloS30/
├── project.json     build metadata (name, appid, RAM, resolution, FPS, profile)
├── conf.lua         runtime configuration
├── main.lua         entry script
├── src/             Lua modules loaded through require()
└── assets/          images, audio, resources
```

A minimal `main.lua`:

```lua
local E = engine
local white = E.color(255, 255, 255)
local bg = E.color(20, 45, 35)

function E.draw()
    E.clear(bg)
    E.text(8, 8, "Hello S30+", white)
end

function E.keypressed(key)
    if key == "0" then E.exit() end
end
```

Full details in [Project Structure](Project-Structure.md) and
[`doc/reference/API.md`](../../doc/reference/API.md).

## 5. Build

Build only:

```bat
build_only.bat "%USERPROFILE%\Documents\LuaS30IDE\HelloS30"
```

Build and run the emulator:

```bat
build.bat "%USERPROFILE%\Documents\LuaS30IDE\HelloS30"
```

Build with an explicit toolchain and IMSI:

```bat
build.bat PROJECT_DIR TOOLCHAIN_DIR IMSI
```

Or call the CLI directly:

```bat
python tools\build.py ^
  --project "Documents\LuaS30IDE\HelloS30" ^
  --toolchain toolchain\arm-gcc ^
  --no-run
```

## 6. Output

```text
HelloS30\build\
├── HelloS30.axf
├── HelloS30.elf-report.txt
├── HelloS30.dev.vxp
├── HelloS30.vxp            <- the canonical artifact
├── *.sha256
└── sync_manifest.json
```

> **The VXP is unsigned.** The IDE does not sign. Retail firmware enforcing
> certificate trust will refuse to open it. See [Building VXP](Building-VXP.md).

## 7. Unknown device

Before building a large game for an unfamiliar device, build the probe template:

```text
templates\device_probe\
```

The probe verifies that the runtime starts and that graphics, keypad, timers, and
file/audio/image capabilities and resolution all behave. It separates "the engine
cannot run on this firmware" from "the game logic is broken".

## 8. Next steps

- [Studio UI](Studio-UI.md)
- [Building VXP](Building-VXP.md)
- [`doc/reference/API.md`](../../doc/reference/API.md) — the complete Lua API
- [`doc/platform/DEVICE_COMPATIBILITY.md`](../../doc/platform/DEVICE_COMPATIBILITY.md)
- [`doc/getting-started/QUICKSTART.md`](../../doc/getting-started/QUICKSTART.md)
