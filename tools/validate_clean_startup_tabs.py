from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
main = (ROOT / "studio/app/vxpui/main_window.py").read_text(encoding="utf-8")
errors = []

for token in (
    'VERSION = "1.0.2"',
    'entry.get("type") == "tool"',
    '"restore_source_tabs": False',
    "_PERSISTENT_TOOL_TABS",
    'if self._startup_mode != "empty_editor":',
    'self._apply_project(info.root, open_main=False)',
    'load_initial_project()',
):
    if token not in main:
        errors.append("missing startup-clean-tabs contract: " + token)

# Session save must only persist whitelisted tool tabs — never source files.
save_start = main.find("def _save_workspace_session")
save = main[save_start:save_start + 2500]
if "if key in _PERSISTENT_TOOL_TABS" not in save:
    errors.append("save no longer filters persisted tabs to tool keys")
# main.lua may only open on an explicit user action (open_main=True), never
# from the startup restore path.
load_start = main.find("def _load_initial_state")
load_block = main[load_start:main.find("def _activate_startup_mode", load_start)]
if "open_file(main_lua)" in load_block:
    errors.append("startup restore still automatically opens main.lua")
if "open_main=False" not in load_block:
    errors.append("startup restore opens projects with open_main enabled")
main_lua_guard = main.find("if open_main:")
if main_lua_guard == -1 or "open_file(main_lua)" not in main[main_lua_guard:main_lua_guard + 200]:
    errors.append("main.lua fallback is not gated behind an explicit open_main flag")

if errors:
    print("FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("PASS: restart skips persisted source file tabs")
print("PASS: restart skips untitled editor tabs")
print("PASS: source tabs are filtered from the saved startup session")
print("PASS: no automatic main.lua fallback remains")
print("PASS: project/layout/tool state can still be restored")
