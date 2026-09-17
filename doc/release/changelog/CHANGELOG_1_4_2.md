# LuaS30 Engine 1.4.2

- Added requirement-aware dependency manager.
- `run.bat` no longer downloads/upgrades Python packages on every launch.
- Added automatic offline fallback and explicit `--offline` mode.
- Added `--online`, `--deps-only`, and `--force-deps` launcher modes.
- Added persistent dependency change log and JSON environment state.
- Launcher log is now append-only across sessions.
- `ensurepip` is used only when pip is actually missing.
- `env_check.py` now reads the engine version from `VERSION`.
