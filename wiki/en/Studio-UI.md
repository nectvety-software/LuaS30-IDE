# Studio UI

> **Language:** English · [Tiếng Việt](../vi/Studio-UI.md)

LuaS30 Studio uses a VS Code-style layout.

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

The bottom panel is **physically** limited to the centre editor column; it does not
extend under the ChatAI sidebar.

## Activity Bar

| Item | Opens a tab for |
|---|---|
| Explorer | The project's real filesystem tree |
| Search | Project-wide search |
| Assets | Resource management |
| UI Designer | 240×320 screen design |
| Emulator | VXP artifact and process state |
| Settings | Configuration |

Each item opens/focuses **one tab** in the editor tab strip. Selecting a tool that is
already open focuses its existing tab instead of creating a duplicate. Closing a tool
tab releases the view; selecting the tool again recreates it.

The **Tools** menu contains only features that open real tabs:

```text
Project Doctor
Runtime Compatibility Matrix
Toolchain Doctor
```

Command-only utilities (for example Clean Build) live under **Run**; commands that
reveal project/build folders live under **File** or the Command Palette.

## Explorer

Explorer is a real filesystem tree and supports:

- expand/collapse, New File, New Folder, Rename, Delete, Open;
- Copy Path, Copy Relative Path, Reveal in File Explorer, Refresh;
- hiding/showing generated folders.

Hidden by default: `.git`, `.venv`, `__pycache__`, `.idea`, `.pytest_cache`.
Generated folders that can be hidden: `build`, `release`, `dist`.

## Code Editor

- multi-tab, dirty marker, save/save as/save all;
- Lua syntax highlighting, Lua and `engine.*` autocomplete;
- Find/Replace, minimap;
- inline diagnostics and a Problems tab;
- Go to Definition, project-wide search;
- status line/column.

Right-click a tab for **Close**, **Close Others**, **Close All Tabs**. Close All
applies across editor groups and still prompts for unsaved documents.

## Bottom Panel

```text
CONSOLE | BUILD | PROBLEMS | TERMINAL
```

| Shortcut | Action |
|---|---|
| `Ctrl+J` | Toggle bottom panel |
| `Ctrl+Shift+Y` | Toggle Console |
| ``Ctrl+` `` | Toggle Terminal |
| ``Ctrl+Shift+` `` | New Terminal |

Behaviour:

- the panel is **hidden by default** on every startup, even if it was open before;
- it has a close button in its top-right corner, and reopening returns to the same
  terminal session;
- hiding the Terminal does **not** kill its shell process;
- it opens at a compact height, stays resizable via the splitter, remembers the
  preferred height, and does not auto-reopen next launch.

The Terminal is a real shell started in the current project directory (on Windows it
uses `%COMSPEC%`/`cmd.exe`). Commands are typed **directly into the terminal
surface** after the prompt — there is no separate one-line textbox:

```text
C:\Users\user\Documents\LuaS30IDE\prj> python tools\build.py ...
```

| Key | Action |
|---|---|
| `Enter` | run the current command |
| `Up` / `Down` | command history |
| `Home` | jump to the start of the editable command |
| `Ctrl+A` | select the current command only |
| `Ctrl+V` | paste into the current command |
| `Ctrl+L` | clear the terminal |
| `Ctrl+C` | copy the selection, otherwise send ETX to the shell |

Previous output is protected from accidental editing. The panel colour-codes output:

```text
red      errors / failures
yellow   warnings
green    OK / PASS / success
cyan     commands / RUN
blue     BUILD / TOOLCHAIN / EMU / INFO
purple   section headings
```

## Project Storage

Backed by `Documents\LuaS30IDE` with real filesystem operations:

- scan managed projects recursively;
- filter by project / path / AppID;
- create a new project from the engine template;
- import an existing LuaS30 project into managed storage;
- open a project;
- duplicate **without** generated `build`/`release` data;
- rename the project folder and the name in `project.json`;
- delete **only** verified managed LuaS30 project folders;
- reveal in the OS file explorer;
- show modified time, disk usage, file count and the latest VXP artifact.

Switching projects closes only **source** tabs (after an unsaved-change check). Tool
tabs stay open and refresh their project context.

## UI Designer

The designer focuses on the small **240×320** screen (Nokia S30+ QVGA).

```text
[toolbar]  new screen · save+export Lua · import image · import audio · snap · zoom
[SCREENS]  screen combo · [+] create · [⋮] rename / duplicate / delete / open folder
[breadcrumb]
[COMPONENTS]  [240×320 canvas]  [INSPECTOR]  [LAYERS · ID]
```

- **Canvas** — a 240×320 phone frame; drag components in, with snapping guides
  (blue lines align to other components, yellow lines align to the frame). Zoom with
  `Ctrl +/−`; hold `Alt` while dragging to temporarily disable snapping. While
  dragging from the palette the screen frame highlights (solid outline — where the
  component will land) and a ghost shows the drop position (dashed) with an
  `x, y  w×h` label. Dropping anywhere clamps the component fully inside the frame.
- **COMPONENTS** — 18 types in 3 groups (UI / LAYOUT / GRAPHICS), plus images and
  audio scanned from `assets/`. Drag onto the canvas or click to add.
- **INSPECTOR** — ID, position, size, fill colour, rotation, text content.
- **LAYERS · ID** — layer order (topmost draws last), double-click to rename the ID,
  duplicate (`Ctrl+D`), rotate (`Ctrl+Shift+R`), bring forward / send backward
  (`Ctrl+Shift+↑/↓`).
- **Multiple screens** — the startup screen is always `main` and cannot be renamed
  or deleted.

Files written by the designer:

```text
<project>/.luas30/ui_design.json   source of truth (JSON, all screens)
<project>/ui_design.lua            generated by "Save + Export Lua"
```

`ui_design.lua` contains both the data and a renderer built on the LuaS30 API:

```lua
local ui = require("ui_design")

function engine.draw()
    ui.draw("main")
end

local item = ui.get("main", "btn_start")
local top  = ui.hit("main", touch_x, touch_y)   -- for touch input
```

Limitation: LuaS30's `engine` draws axis-aligned rectangles only — there is **no
rotation primitive**. Components with `rot` 90/270 are drawn with width/height
swapped; other angles are drawn unrotated.

## Emulator

The Run action opens the **exact final VXP just built**. Build/Run compares SHA-256
hashes so the emulator cannot launch a stale artifact. On Run, the panel opens the
`HEX` tab for the VXP named in the sync manifest; the viewer pages in 64 KiB chunks
and shows offset, hex bytes and ASCII.

> Emulator success does **not** replace testing on real hardware.

## Settings

`Settings` holds paths, target profile, compiler profile/toolchain root and build
preferences. Project-specific configuration belongs in `project.json`, not
hard-coded in Studio.

**Settings → Startup screen** offers three modes:

```text
Welcome        welcome page with project management
Project Hub    full-width Project Storage
Empty Editor   open an empty editor, no file
```

All three modes **exclude** source tabs from startup restore. They restore only the
current project, editor-group layout, tool tabs, Explorer/Activity Bar preferences,
bottom-panel state and window layout.

## About

The **About** menu has four entries: **About LuaS30 IDE**, **Environment**,
**Credits**, **Paths**. The Credits tab is kept in sync with
[`doc/legal/THIRD_PARTY_NOTICES.md`](../../doc/legal/THIRD_PARTY_NOTICES.md).

The copyright line **© Qeafivels All rights reserved.** and the website
<https://qeafivels.com/> appear at the bottom of every About tab.

## Theme & palette

Studio's design standard comes from the **MediaTek MRE SDK configuration** dialog:
dark blue-slate surfaces (`#07101f` recessed / `#111827` flat), borders
`#273449`–`#334155`, light text `#f8fafc`, an **amber** accent `#f59e0b`, 8–12px
corner radii and 34px-tall inputs.

### A single colour source

```text
studio/app/ui/palette.py   <- source of truth, declares every colour
studio/app/ui/theme.py     <- QSS uses @TOKEN, NEVER raw hex
```

`theme.py` writes QSS with `@TOKEN` placeholders; `_substitute()` resolves them from
`palette.py` at import time. An unknown token **raises immediately** — deliberately
fail-loud, because Qt silently drops the **entire** rule when it meets an invalid
declaration, breaking the UI with no message at all.

The surface ramp runs from recessed to raised:

```text
BG_INK -> BG_ALT -> BG_SURFACE -> BG_RAISED -> BG_HOVER -> BG_PRESSED
```

Inputs, editor, terminal and canvas use `BG_INK`; panels and dialogs use
`BG_SURFACE`; menus/popups/toolbars use `BG_RAISED`. There are only **three** corner
radii: 6px (controls), 8px (cards), 12px (dialogs).

### Chrome colour vs content colour — never mix them

- **Chrome colour** is the IDE's own colour (background, borders, text, buttons,
  selection outline, scrollbars). It must come from `palette.py`.
- **Content colour** is the colour of the *game* Studio is drawing for. It must not
  follow the IDE palette.

Example: `items.C_ACCENT = #007acc` is the colour of buttons/checkboxes inside the
game frame and must match `lua_export.ACCENT`. Changing it to amber changes the real
game's colour, not the theme. Quick check: export `ui_design.lua` and inspect it — it
must not contain `#f59e0b`.

### Objects Qt draws itself

The tab close button is drawn by Qt (`QStyle::SP_TabCloseButton`, a red-backed X) and
appears even with no stylesheet loaded. The correct fix is to **own the widget**
(`StudioTabBar` / `_TabCloseButton` in `studio/app/editor/editor_tabs.py`), not to
repaint it with `QTabBar::close-button { background: transparent; }` — that removes
the red background but also loses the click area and the glyph.

### The widget's own background, not just its subcontrols

QSS only paints what is declared. If you style only `::section` and not
`QHeaderView` itself, the area after the last section falls back to the default —
which is **light** — producing a white stripe. Same family of bug, so check
`QTabBar`, `QTableView`, `QTreeView`, `QListWidget` and `QScrollArea` too.

### Checking the theme

```text
QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
  py -3.12 -u tools/studio_theme_check.py
```

Add `--shots <dir>` to save screenshots, `--static-only` to run only the static
checks (no Qt needed). There are four groups: static checks, WCAG contrast,
offscreen render (light-block scanning), and the tab close button.

## Font icons

Studio does **not** use emoji as icons. Icons are built at runtime from Windows
system icon fonts through `studio/app/ui/icons.py`, in preference order:

```text
Segoe Fluent Icons -> Segoe MDL2 Assets -> Segoe UI Symbol (fallback)
```

No icon font file is bundled with or exported from the engine package.

See also [`doc/studio/STUDIO_GUIDE.md`](../../doc/studio/STUDIO_GUIDE.md).
