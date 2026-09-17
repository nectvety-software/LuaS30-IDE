# LuaS30 Engine 1.9.2 — Welcome / Project Hub

- Added VS Code-like `Welcome` startup tab.
- Welcome opens at tab index 0 of editor group 0.
- Added New Project, Open Folder, Import into Storage and Manage Storage start actions.
- Added Recent project list backed by managed Project Storage.
- Added Project Storage count/size/build summary and current-workspace card.
- Added `Show Welcome page on startup`, enabled by default.
- Workspace-session tabs/groups are still restored in the background.
- When startup Welcome is disabled, the previously active restored editor remains active.
- Closing a project now returns to Welcome rather than forcing the full storage manager.
- Added non-activating/insert-at support for tool tabs.
