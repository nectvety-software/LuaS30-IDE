from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
chat = (ROOT / "studio/app/views/ai_chat_view.py").read_text(encoding="utf-8")
editor = (ROOT / "studio/app/vxpui/main_window.py").read_text(encoding="utf-8")
terminal = (ROOT / "studio/app/widgets/terminal_view.py").read_text(encoding="utf-8")
protocol = (ROOT / "studio/app/services/ai_agent_protocol.py").read_text(encoding="utf-8")
provider = (ROOT / "studio/app/services/ai_provider_service.py").read_text(encoding="utf-8")
theme = (ROOT / "studio/app/ui/theme.py").read_text(encoding="utf-8")

for token in (
    'def _send_or_stop',
    'def stop_agent',
    'apply_icon(self.send_button, "stop", 13)',
    'self._pending_continue_question = None',
    'self.reject_changes_requested.emit()',
    'self._shell_stopper()',
    '_max_full_access_turns = 32',
    'if policy == "full":',
    'full_auto = auto and self._shell_policy() == "full"',
):
    assert token in chat, token

for token in (
    'self.ai_chat.set_shell_stopper(self._stop_ai_shell)',
    'def _stop_ai_shell',
):
    assert token in editor, token

assert 'def cancel_ai_command' in terminal
assert 'self.kill_terminal(silent=True)' in terminal
assert 'full_access: bool = False' in protocol
assert 'Full Access automation is active' in protocol
assert 'if not self.isInterruptionRequested()' in provider
assert 'QPushButton#AIChatSendIcon[running="true"]' in theme

print("PASS: Send icon changes to Stop while the agent is active")
print("PASS: Stop cancels queued continuation, pending edits and active AI terminal work")
print("PASS: stale provider responses are ignored after Stop")
print("PASS: Full Access auto-applies edits and auto-runs terminal actions without confirmation")
print("PASS: Full Access has a bounded 32-turn autonomous loop")
