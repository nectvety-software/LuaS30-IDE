# LuaS30 Studio 1.3 validation

Validation performed in the build workspace:

- Python AST parse: **30 Python files, 0 syntax errors**.
- `compileall`: **PASS**.
- Local `app.*` import graph: **no missing local modules**.
- Lua structural analyzer smoke test:
  - valid nested function/if script: **0 diagnostics**.
  - invalid script with missing `)` / missing `end`: **diagnostics detected**.
- Project symbol index smoke test: detected `engine.load`, `Player.move`, and local variables and resolved definitions.

PySide6 is not installed in the Linux build workspace, so interactive Qt rendering was not executed here. `run_studio.bat` creates/uses the Windows virtual environment and installs the desktop dependency declared by the Studio package.
