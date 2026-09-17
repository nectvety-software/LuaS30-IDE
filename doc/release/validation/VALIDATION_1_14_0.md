# Validation 1.14.0

```text
Python AST: PASS (102 files)
validate_agent_protocol.py: PASS
validate_ai_agent_protocol.py: PASS
validate_ai_agent_shell.py: PASS
validate_ai_context.py: PASS
validate_ai_workbench.py: PASS
validate_clean_startup_tabs.py: PASS
validate_compact_bottom_panel.py: PASS
validate_complete.py: PASS
validate_direct_terminal.py: PASS
validate_hex_panel_appid.py: PASS
validate_layout_toggles.py: PASS
validate_mre_gcc_build.py: PASS
validate_mre_project_wizard.py: PASS
validate_multi_toolchain.py: PASS
validate_native_sdk.py: PASS
validate_portable_toolchain.py: PASS
validate_project_hub_layout.py: PASS
validate_release_security.py: PASS
validate_runtime_compat.py: PASS
validate_runtime_matrix.py: PASS
validate_s30plus_compat.py: PASS
validate_s30plus_sdk_detection.py: PASS
validate_single_vxp.py: PASS
validate_start_page.py: PASS
validate_startup_screen_setting.py: PASS
validate_tabbed_workspace.py: PASS
validate_terminal_console.py: PASS
validate_tree.py: PASS
validate_unique_appid.py: PASS
validate_workbench.py: PASS
validate_workspace_session.py: PASS
Shell permission non-persistence: PASS
Shell secret-output redaction present: PASS
Raw chain-of-thought prohibition present: PASS
Markdown layout: PASS
```

Scope: AI Activity/reasoning-summary protocol, shell permission UI, visible integrated-Terminal execution, command lifecycle capture, risk classification, secret redaction, automatic continuation and regression validators. PySide6 is not installed in this Linux environment, so the Windows Qt rendering and real provider/shell interaction still require a smoke test on the user workstation.
