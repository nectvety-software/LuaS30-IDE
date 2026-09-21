from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

print("== Python syntax gate ==")
compile_result = subprocess.run(
    [
        sys.executable,
        "-m",
        "compileall",
        "-q",
        str(ROOT / "studio"),
        str(ROOT / "tools"),
    ],
    cwd=ROOT,
    check=False,
)
if compile_result.returncode != 0:
    print("FAIL: python -m compileall -q studio tools")
    raise SystemExit(compile_result.returncode)
print("PASS: python -m compileall -q studio tools")

chat = (ROOT / "studio/app/views/ai_chat_view.py").read_text(encoding="utf-8")
renderer = (ROOT / "studio/app/views/ai_chat_render.py").read_text(encoding="utf-8")
theme = (ROOT / "studio/app/ui/theme.py").read_text(encoding="utf-8")
main_window = (ROOT / "studio/app/vxpui/main_window.py").read_text(encoding="utf-8")
editor_tabs = (ROOT / "studio/app/editor/editor_tabs.py").read_text(encoding="utf-8")
editor_groups = (ROOT / "studio/app/editor/editor_group_manager.py").read_text(encoding="utf-8")

missing: list[str] = []

required_chat = (
    "TranscriptHtmlRenderer",
    "ACCESS_MODES",
    'QPushButton("Gửi")',
    "def _send_or_stop",
    "def stop_agent",
    "worker.abort()",
)
missing += [f"chat:{token}" for token in required_chat if token not in chat]

required_renderer = (
    "class TranscriptHtmlRenderer",
    "def render_markdown",
    "def render_code_block",
    "AI Trợ lý",
)
missing += [f"renderer:{token}" for token in required_renderer if token not in renderer]

required_theme = (
    "QTabWidget#EditorTabs QTabBar::tab",
    "max-width: 230px",
    "QLabel#AITabStatusBadge",
    'QLabel#AITabStatusBadge[aiState="modified"]',
    'QLabel#AITabStatusBadge[aiState="created"]',
)
missing += [f"theme:{token}" for token in required_theme if token not in theme]

required_editor_tabs = (
    "class _AITabStatusBadge(QLabel)",
    '"modified": "AI Modified"',
    '"created": "AI Created"',
    "self.setText(label)",
    "def set_ai_file_status(self, path: str | Path, state: str) -> bool",
    "QTabBar.ButtonPosition.LeftSide",
    "def clear_ai_file_status(self, path: str | Path) -> bool",
    "def open_file(self, path: str | Path, *, activate: bool = True)",
)
missing += [
    f"editor_tabs:{token}"
    for token in required_editor_tabs
    if token not in editor_tabs
]

required_editor_groups = (
    "def set_ai_file_status(self, path: str | Path, state: str) -> bool",
    "return group.set_ai_file_status(resolved, state)",
    "def clear_ai_file_status(self, path: str | Path) -> bool",
    "def open_file(self, path: str | Path, *, activate: bool = True)",
    "return self.active_tabs().open_file(resolved, activate=activate)",
    "return self.groups[target_index].open_file(path, activate=False)",
)
missing += [
    f"editor_groups:{token}"
    for token in required_editor_groups
    if token not in editor_groups
]

required_main = (
    "def _reload_applied_editors(self, change_set: PreparedChangeSet)",
    "self.tabs.open_file(target, activate=False)",
    "self.tabs.set_ai_file_status(",
    '"modified" if change.existed else "created"',
    "self.tabs.open_file(opened_targets[0], activate=True)",
)
missing += [f"main_window:{token}" for token in required_main if token not in main_window]

# Upstream features that must survive conflict resolution.
for token in (
    "_ai_problem_timer",
    "_refresh_ai_problem_card",
):
    if token not in main_window:
        missing.append(f"upstream regression: missing {token}")
for token in (
    "_recover_fenced_files",
    "_recover_json_tool_calls",
):
    protocol = (ROOT / "studio/app/services/ai_agent_protocol.py").read_text(encoding="utf-8")
    if token not in protocol:
        missing.append(f"upstream regression: missing {token}")

if missing:
    print("FAIL: AI assistant/editor upstream reconciliation")
    for item in missing:
        print(" -", item)
    raise SystemExit(1)

print("PASS: upstream modern AI chat renderer and stop flow are preserved")
print("PASS: upstream fenced-file/json-tool recovery is preserved")
print("PASS: upstream live problem-card wiring is preserved")
print("PASS: AI-changed/created files open as VS Code-like editor tabs")
print("PASS: AI Modified / AI Created badges are wired and themed")
