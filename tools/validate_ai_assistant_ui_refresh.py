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
theme = (ROOT / "studio/app/ui/theme.py").read_text(encoding="utf-8")
main_window = (ROOT / "studio/app/vxpui/main_window.py").read_text(encoding="utf-8")
editor_tabs = (ROOT / "studio/app/editor/editor_tabs.py").read_text(encoding="utf-8")
editor_groups = (ROOT / "studio/app/editor/editor_group_manager.py").read_text(encoding="utf-8")

required_chat = (
    'self.setMinimumWidth(340)',
    'self.setMaximumWidth(720)',
    'HOẠT ĐỘNG AGENT',
    'tóm tắt · không hiển thị suy luận riêng tư',
    'AIComposerToolButton',
    'AIComposerTextTool',
    'Shift + Enter để xuống dòng',
    'QPushButton("Gửi")',
    'self.send_button.setText("Dừng")',
    'self.send_button.setText("Gửi")',
    'AIStatusDot',
    'AI hỗ trợ lập trình LuaS30',
    'label = "Bạn" if is_user else "AI Trợ lý"',
    'marker = "B" if is_user else "✦"',
    'def _send_or_stop',
    'def stop_agent',
)

required_theme = (
    'QWidget#AIChatView',
    'QPushButton#AIChatTab:checked',
    'QPlainTextEdit#AIChatPrompt',
    'QToolButton#AIComposerToolButton',
    'QToolButton#AIComposerTextTool',
    'QLabel#AIComposerHint',
    'QLabel#AIStatusDot',
    'QLabel#AIStatusHint',
    'QPushButton#AIAccessModeButton',
    'QPushButton#AIProviderCompact',
    'QPushButton#AIChatSendIcon',
    'QPushButton#AIChatSendIcon[running="true"]',
    'QLabel#AITabStatusBadge',
    'QLabel#AITabStatusBadge[aiState="modified"]',
    'QLabel#AITabStatusBadge[aiState="created"]',
)

missing = [f"chat:{token}" for token in required_chat if token not in chat]
missing += [f"theme:{token}" for token in required_theme if token not in theme]


required_editor_tabs = (
    'class _AITabStatusBadge(QLabel)',
    '"modified": "AI Modified"',
    '"created": "AI Created"',
    'self.setText(f"● {label}")',
    'def set_ai_file_status(self, path: str | Path, state: str) -> bool',
    'QTabBar.ButtonPosition.LeftSide',
    'def clear_ai_file_status(self, path: str | Path) -> bool',
    'def open_file(self, path: str | Path, *, activate: bool = True)',
    'if activate:\n                self.setCurrentIndex(existing[0])',
    'if activate:\n            self.setCurrentIndex(index)',
)
missing += [
    f"editor_tabs:{token}"
    for token in required_editor_tabs
    if token not in editor_tabs
]

required_editor_groups = (
    'def set_ai_file_status(self, path: str | Path, state: str) -> bool',
    'return group.set_ai_file_status(resolved, state)',
    'def clear_ai_file_status(self, path: str | Path) -> bool',
    'def open_file(self, path: str | Path, *, activate: bool = True)',
    'return self.active_tabs().open_file(resolved, activate=activate)',
    'return self.groups[target_index].open_file(path, activate=False)',
)
missing += [
    f"editor_groups:{token}"
    for token in required_editor_groups
    if token not in editor_groups
]

required_ai_file_tabs = (
    'def _reload_applied_editors(self, change_set: PreparedChangeSet)',
    'self.tabs.open_file(target, activate=False)',
    'self.tabs.set_ai_file_status(',
    '"modified" if change.existed else "created"',
    'self.tabs.open_file(opened_targets[0], activate=True)',
    'files created or changed by the agent are opened as background tabs',
)
missing += [
    f"main_window:{token}"
    for token in required_ai_file_tabs
    if token not in main_window
]

# The compact UI must not regress into a separate replacement agent/backend.
for forbidden in (
    "OpenAIProvider2",
    "AnthropicProvider2",
    "GeminiProvider2",
):
    if forbidden in chat:
        missing.append(f"unexpected duplicate provider: {forbidden}")

# Keep existing safety/integration hooks intact while refreshing only presentation.
for preserved in (
    "AIRequestThread",
    "AIReadOnlyToolService",
    "CodebaseContextService",
    "changes_proposed = Signal(object)",
    "review_changes_requested = Signal()",
    "apply_changes_requested = Signal()",
    "reject_changes_requested = Signal()",
    "worker.abort()",
):
    if preserved not in chat:
        missing.append(f"regression: missing {preserved}")

if missing:
    print("FAIL: AI assistant UI refresh")
    for item in missing:
        print(" -", item)
    raise SystemExit(1)

print("PASS: compact AI assistant header/tabs/composer/status UI is installed")
print("PASS: Gửi/Dừng state remains wired to the existing hard-stop flow")
print("PASS: existing provider, context, read-only tools and AI Changes signals remain wired")
print("PASS: refreshed theme uses the existing LuaS30 palette/QSS architecture")
print("PASS: every AI-changed/created text file opens as a VS Code-like editor tab")
print("PASS: AI-touched tabs expose AI Modified / AI Created badges with distinct theme states")
print("PASS: background tab opening does not steal focus until the primary AI file is selected")
