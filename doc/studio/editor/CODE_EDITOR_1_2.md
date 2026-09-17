# LuaS30 Studio 1.2 — Code Editor

This release adds the first real desktop editing module on top of LuaS30 IDE 1.1.

## Implemented

- Project Tree based on `QFileSystemModel`.
- Double-click files to open them.
- Context menu: New File, New Folder, Rename, Delete, Open in Explorer.
- Multi-tab editor with closable/reorderable tabs.
- Modified `*` indicator and unsaved-change prompt.
- Lua 5.1 syntax highlighting: keywords, built-ins, numbers, strings, comments,
  multiline `--[[ ... ]]` comments, functions and table fields.
- Line numbers and current-line highlight.
- Open / Save / Save As / Save All.
- Shortcuts:
  - `Ctrl+N` new file
  - `Ctrl+O` open file
  - `Ctrl+S` save
  - `Ctrl+Shift+S` save as
  - `Ctrl+Alt+S` save all
  - `Ctrl+Shift+O` open project
  - `Ctrl+K` focus global search field
- Status bar with line, column, selection count, UTF-8 and Lua 5.1.
- Auto indentation after Lua `then`, `do`, `function`, and `repeat`.
- Four-space Tab insertion.
- Integrates with existing `build_only.bat` / `build.bat` if ARM GCC is installed
  under `toolchain/arm-gcc`.

## Start

```bat
run_studio.bat
```

The launcher creates `.venv`, installs PySide6 if necessary, then opens the desktop app.
PySide6 is a desktop-only dependency; the generated VXP runtime remains separate and does not
include PySide6.
