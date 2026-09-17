# LuaS30 Tabbed Workspace 1.9

## Goal

Replace whole-workspace tool pages with VS Code-style editor-area tabs while preserving
one owner for each command/function.

## Tab ownership

Source tabs are `EditorPane` widgets. Tool tabs are ordinary QWidget views registered by
stable keys through `EditorTabs.open_tool_tab()`.

```text
assets
projects
designer
emulator
settings
project-doctor
compat-matrix
toolchain-doctor
```

Opening the same key focuses the existing tab. The editor tab bar therefore prevents
multiple duplicate instances of the same tool.

## Menu ownership

```text
File  -> project/file lifecycle + folder reveal
Edit  -> editor commands
View  -> command palette/sidebar/bottom-panel visibility
Run   -> Build/Run/Clean/Stop
Tools -> tab-based diagnostic tools only
About -> documentation/environment/credits
```

The Activity Bar is the navigation owner for Explorer, Search, Project Storage, Assets,
UI Designer, Emulator and Settings.

## Project Storage service

`studio/app/services/project_library.py` implements project discovery and storage
operations independently of the UI.

Storage root:

```text
Documents\LuaS30IDE
```

Deletion is guarded: the service refuses to delete the storage root or a folder without
`project.json`.

Project duplication/import excludes generated and environment directories such as
`build`, `release`, `.git`, `.venv` and `__pycache__`.

## Project switching

Project changes use `EditorTabs.close_file_tabs()`. Unsaved source files still receive
the normal Save/Discard/Cancel confirmation. Tool tabs remain open and receive the new
project root through their `set_project()` methods.

This avoids both lost edits and repeated tool-page construction during normal project
switching.
