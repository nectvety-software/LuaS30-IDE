# Validation 1.15.0

```text
Python AST: PASS (107 files)
validate_agent_protocol.py: PASS
validate_ai_agent_protocol.py: PASS
validate_ai_agent_shell.py: PASS
validate_ai_change_service.py: PASS
validate_ai_context.py: PASS
validate_ai_workbench.py: PASS
validate_ai_workbench_v1.py: PASS
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
Provider API-key persistence scan: PASS
Four access modes scan: PASS
AI edit atomic/backup scan: PASS
Raw chain-of-thought prohibition scan: PASS
Markdown layout: PASS
```

Scope: AI Workbench v1 access modes, provider test/apply dialog, structured code-edit protocol, review diff surface, atomic apply/backup, existing shell-agent safety boundaries and full regression validator suite. PySide6 GUI rendering and live provider/network interaction still require a Windows smoke test with the user's own provider credentials/local endpoint.
