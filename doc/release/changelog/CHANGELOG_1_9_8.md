# LuaS30 Engine 1.9.8 — Startup Screen Setting

- Added Settings -> Startup screen.
- Added Welcome startup mode.
- Added Project Hub startup mode.
- Added Empty Editor startup mode.
- Empty Editor restores project/layout but restores no file, untitled or tool tabs.
- Removed duplicate `Show Welcome page on startup` checkbox from Welcome.
- Added migration from legacy `show_start_page`.
- Persisted selection as `startup.mode`.
- Preserved the clean-start rule that source files never reopen automatically.
