# LuaS30 Engine 1.9.3 — Integrated Terminal / Console

- Added real integrated Terminal based on QProcess.
- Added Console and Terminal toggle actions in View.
- Added top-level Terminal menu with New/Kill/Clear actions.
- Added Ctrl+J panel toggle, Ctrl+Shift+Y Console toggle, Ctrl+` Terminal toggle and
  Ctrl+Shift+` New Terminal.
- Bottom panel is hidden by default in a new workspace.
- Panel session state now saves `active_key` in addition to legacy numeric index.
- Restoring a visible Terminal panel starts a fresh shell in the current project folder.
- Existing `output` source-level name remains an alias for Console for compatibility.
