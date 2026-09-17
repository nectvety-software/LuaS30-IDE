# LuaS30 Engine validation

PASS: standalone tree
PASS: no MRE static library includes/links in native runtime
PASS: bundled Lua 5.1.5 source
PASS: raw Lua resource mode does not require luac.exe

Python tools: PASS (py_compile)

Host GCC syntax-only checks:
- coremre_entry.c: PASS
- coremre_imports.c: PASS
- coremre_bridge.c: PASS
- coremre_lua.c: PASS
