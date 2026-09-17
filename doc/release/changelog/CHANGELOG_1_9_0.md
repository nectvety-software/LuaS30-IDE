# LuaS30 Engine 1.9.0 — Tabbed Workspace + Project Storage

## Workbench
- Removed whole-workspace switching for Assets, Designer, Emulator and Settings.
- Source files and persistent tools now share one closable/movable editor tab strip.
- Added keyed tool tabs so opening a feature focuses the existing instance.
- Added Toolchain Doctor as a real tab backed by `toolchain_doctor.py`.
- Project Doctor and Runtime Compatibility Matrix now open result tabs.
- Tools menu now contains tab-based diagnostic features only.
- Build/Output/Problems remain integrated in the bottom panel.

## Project Storage
- Added a managed project-storage tab for `Documents\\LuaS30Engine`.
- Added project scan/search, open, import, duplicate, rename, delete and reveal.
- Added project size, file count, modified time, App ID and last VXP visibility.
- Added guarded deletion and generated-folder exclusion during import/duplicate.
- Project switching closes only source tabs and keeps tool tabs alive.

## Architecture
- Added `ProjectLibraryService` as non-UI project storage logic.
- Added `EditorTabs.open_tool_tab()` / `tool_widget()` / `close_file_tabs()`.
- Added project-close/reset support for Explorer/Search/ProjectIndex.
- Native SDK/VXP ABI is unchanged.
