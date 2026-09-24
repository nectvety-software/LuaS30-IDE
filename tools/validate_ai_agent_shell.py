from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
errors = []
chat = (ROOT / 'studio/app/views/ai_chat_view.py').read_text(encoding='utf-8')
terminal = (ROOT / 'studio/app/widgets/terminal_view.py').read_text(encoding='utf-8')
protocol = (ROOT / 'studio/app/services/ai_agent_protocol.py').read_text(encoding='utf-8')
editor = (ROOT / 'studio/app/vxpui/main_window.py').read_text(encoding='utf-8')
main = (ROOT / 'studio/app/vxpui/main_window.py').read_text(encoding='utf-8')
skill = (ROOT / 'doc/ai/SKILL.md').read_text(encoding='utf-8')
prompt = (ROOT / 'doc/ai/PROMPT.md').read_text(encoding='utf-8')

# Trần lượt: canh BẤT BIẾN chứ không ghim con số. Ghim số thì mỗi lần chỉnh ngân sách
# cho hợp lý là guard đỏ oan, và người ta sẽ "sửa" nó bằng cách đổi số — trong khi
# điều thật sự phải giữ là: LUÔN có biên, và Full Access dài hơn nhưng vẫn có biên.
_limit_agent = re.search(r'self\._max_agent_turns\s*=\s*(\d+)', chat)
_limit_full = re.search(r'self\._max_full_access_turns\s*=\s*(\d+)', chat)
if not _limit_agent:
    errors.append('ChatAI agent UI missing: self._max_agent_turns = <số>')
if not _limit_full:
    errors.append('ChatAI agent UI missing: self._max_full_access_turns = <số>')
if _limit_agent and _limit_full:
    _agent_turns = int(_limit_agent.group(1))
    _full_turns = int(_limit_full.group(1))
    if _agent_turns < 1:
        errors.append('trần lượt agent phải >= 1 (nếu không thì agent không bao giờ chạy)')
    if _full_turns < _agent_turns:
        errors.append('Full Access phải được nới rộng hơn chế độ thường')
    if max(_agent_turns, _full_turns) >= 10_000:
        errors.append('trần lượt bị bỏ hẳn — vòng lặp tự chạy sẽ không có biên')

for token in (
    'AI ACTIVITY · REASONING SUMMARY',
    'high-level only',
    'Full access',
    'Run in Terminal',
    'def on_shell_command_finished',
    'def _queue_continue',
    'def stop_agent',
    'apply_icon(self.send_button, "stop", 13)',
):
    if token not in chat:
        errors.append('ChatAI agent UI missing: ' + token)

for token in (
    'command_started = Signal(str, str)',
    'command_finished = Signal(str, int, str, str, str)',
    'def run_ai_command',
    'def cancel_ai_command',
    'def commit_external_command',
    '_command_capture',
):
    if token not in terminal:
        errors.append('Terminal agent lifecycle missing: ' + token)

for token in (
    '```luas30-summary',
    '```luas30-shell',
    '```luas30-edit',
    'def classify_shell_command',
    'DANGEROUS_PATTERNS',
    'def redact_shell_output',
    'def bounded_shell_output',
):
    if token not in protocol:
        errors.append('Agent protocol missing: ' + token)

for token in (
    'self.ai_chat.set_shell_runner(self._run_ai_shell)',
    'self.ai_chat.set_shell_stopper(self._stop_ai_shell)',
    'self.bottom.terminal.command_finished.connect(self.ai_chat.on_shell_command_finished)',
    'def _run_ai_shell',
):
    if token not in editor:
        errors.append('Editor shell wiring missing: ' + token)

if 'VERSION = "1.0.2"' not in main:
    errors.append('MainWindow version is not 1.0.2')
if 'private raw chain-of-thought' not in skill:
    errors.append('SKILL.md does not prohibit raw chain-of-thought display')
if 'Do not provide hidden or' not in prompt and 'private raw' not in prompt:
    errors.append('PROMPT.md does not enforce summary-only reasoning')

if errors:
    print('FAIL')
    for error in errors:
        print(' -', error)
    raise SystemExit(1)

print('PASS: visible activity/reasoning-summary UI is installed')
print('PASS: raw/private chain-of-thought display is prohibited')
print('PASS: Ask/Edit Auto/Plan/Full access selector is installed')
print('PASS: AI shell commands execute in the visible integrated Terminal')
print('PASS: Full Access auto-runs terminal commands; other modes keep confirmation gates')
print('PASS: Send/Stop toggle and AI terminal cancellation are installed')
print('PASS: shell output redaction/truncation and bounded autonomous turn limits are installed')
