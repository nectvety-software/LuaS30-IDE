# Validation 1.11.0

```text
Python AST: PASS (93 files)
validate_ai_workbench.py: PASS
validate_ai_context.py: PASS
validate_hex_panel_appid.py: PASS
validate_direct_terminal.py: PASS
validate_compact_bottom_panel.py: PASS
validate_terminal_console.py: PASS
validate_multi_toolchain.py: PASS
Center-only bottom panel check: PASS
AI key persistence check: PASS
Markdown layout: PASS
```

Scope: tab context menu, center-only Compact Bottom Panel, ChatAI sidebar, provider transports and bounded codebase context. Actual provider network calls and interactive Qt resizing still require a Windows smoke test with user credentials/local models.
