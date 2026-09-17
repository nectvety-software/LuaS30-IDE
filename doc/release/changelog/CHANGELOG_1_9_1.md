# LuaS30 Engine 1.9.1 — Workspace Session Restore

- Added automatic VS Code-like workspace session persistence.
- Added real multi-group editor workspace with horizontal editor groups.
- Added View → Split Editor Right and Close Editor Group.
- Restores current project, open source/tool/untitled tabs, tab order, active tab and active group.
- Restores editor-group splitter sizes.
- Restores sidebar visibility, Explorer/Search selection and width.
- Restores bottom panel visibility, active OUTPUT/BUILD/PROBLEMS tab and height.
- Added debounce session autosave on tab/editor/layout/project changes.
- Session is stored under `%APPDATA%\LuaS30Engine\config\workspace_session.json`.
- Missing files are skipped safely during restore.
