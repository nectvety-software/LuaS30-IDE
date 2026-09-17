# LuaS30 Engine 1.4 validation

- Complete file-set: PASS (24/24 required components)
- Python AST/syntax: PASS
- Python compileall: PASS
- Core native C syntax-only: PASS for coremre_entry.c, coremre_imports.c, coremre_bridge.c, coremre_lua.c
- Bundled ARM GCC: present
- Bundled VXPEmu + Qt + Unicorn: present
- Code Editor v1.3 modules: present
- Asset Manager: present
- UI Designer 240x320: present
- Build/Run SHA sync: present

Windows execution of `run.bat`, ARM GCC and VXPEmu must be performed on Windows because the bundled binaries are Windows executables.
