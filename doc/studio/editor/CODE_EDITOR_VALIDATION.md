# Code Editor 1.2 validation

- Python source files parsed with `ast.parse`: PASS.
- `python -m compileall studio`: PASS.
- Project Tree module: present.
- Multi-tab Editor module: present.
- Lua 5.1 syntax highlighter: present.
- Open / Save / Save As / Save All: present.
- Status bar line / column / selection reporting: present.
- Line numbers and current-line highlighting: present.

Runtime UI launch was not performed in the build container because PySide6 is not installed there. `run_studio.bat` creates a venv and installs the desktop-only PySide6 dependency on Windows. The VXP runtime itself remains independent of PySide6.
