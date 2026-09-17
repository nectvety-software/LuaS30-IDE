# LuaS30 Engine 1.7.0 — Compact Workbench

## UI
- Removed duplicate Dashboard, Projects, Build and standalone Console pages.
- Activity Bar now contains only Explorer, Search, Assets, UI Designer, Emulator and Settings.
- Top workbench bar now contains project context + Command Palette only.
- Reduced menu set to File / Edit / View / Run / Tools / About.
- Integrated Output / Build / Problems remains the only log/panel surface.
- Reduced spacing, activity-bar width and bottom-panel default height.

## Real logic
- Added `BuildService` using QProcess + `tools/build.py`.
- Added `EmulatorService` using SHA-verified `tools/run_emulator.py`.
- Added Project Doctor with actual project/config/artifact checks.
- Emulator page displays real VXP/SHA/PID metadata instead of a fake preview.
- Asset Manager adds safe optimize-if-smaller logic.
- UI Designer now saves `.luas30/ui_design.json`, reloads it and exports Lua.

## Architecture
No LuaS30 Native SDK ABI change.
