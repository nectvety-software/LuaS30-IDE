# LuaS30 Engine 1.4.2 validation

Validation targets for the Smart Launcher release:

- `tools/dependency_manager.py` parses and compiles with Python.
- Satisfied requirement path performs no network probe and no pip install.
- Forced offline + missing dependency returns code 20 without a download attempt.
- `env_check.py` reads the engine version from `VERSION`.
- All Studio/tool Python files pass `compileall`.
- Existing CoreMRE/tree validator passes.
- `run.bat` contains all referenced labels and launcher modes.
