# LuaS30 Engine 1.8.2 — Runtime Compatibility Layer

- Added `ls30_compat_report` and compatibility levels: full/degraded/incompatible.
- Added native-vs-effective capability detection.
- Added conservative same-signature ABI alias resolution and alias hit reporting.
- Added safe fallbacks for graphics helpers, text metrics, resource init, file commit,
  rename, removable-drive lookup, audio state/control, logging, ticks, exit and touch.
- Added software line/fill fallbacks so firmware only needs one basic primitive.
- Added Lua `engine.runtime_compat()` and richer `engine.device_info()`.
- Added `has_touch`, `has_rename`, `has_removable`, `has_log`, `runtime_compatible`.
- Kept one canonical generic VXP artifact; no per-device VXP variants.
