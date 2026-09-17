# LuaS30 Engine 1.9.6 — Clean Startup Tabs

- Startup/restart no longer reopens source file tabs.
- Startup/restart no longer recreates untitled editor tabs.
- Removed automatic `main.lua` fallback during workspace restore.
- Session save filters file/untitled tabs from startup state.
- Older session files containing document tabs are accepted, but those entries are skipped.
- Current project, tool tabs, editor groups, Explorer/Activity Bar state and bottom-panel
  state remain persistent.
- Welcome remains the default startup landing tab.
