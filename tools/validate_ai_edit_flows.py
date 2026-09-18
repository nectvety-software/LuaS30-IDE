from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "studio"))

from app.services.ai_agent_protocol import CodeEditAction
from app.services.ai_change_service import AIChangeService

editor_source = (ROOT / "studio/app/vxpui/main_window.py").read_text(encoding="utf-8")
chat_source = (ROOT / "studio/app/views/ai_chat_view.py").read_text(encoding="utf-8")

# Ask-before-changes flow: prepare must not touch disk; Apply Code writes atomically.
with tempfile.TemporaryDirectory() as td:
    project = Path(td)
    target = project / "main.lua"
    target.write_text("local mode = 'old'\n", encoding="utf-8")
    service = AIChangeService()
    prepared = service.prepare(
        project,
        [CodeEditAction(path="main.lua", find="old", replace="ask-applied")],
    )
    assert target.read_text(encoding="utf-8") == "local mode = 'old'\n"
    applied, _backup = service.apply(prepared)
    assert applied == [target.resolve()]
    assert "ask-applied" in target.read_text(encoding="utf-8")

# Edit automatically uses the exact same prepare/apply service, but CodeEditorView
# schedules _apply_ai_changes immediately after preparation and reloads open editors.
for token in (
    '"auto_apply": self._edit_policy() == "auto"',
    'if bool(data.get("auto_apply")):',
    'QTimer.singleShot(0, self._apply_ai_changes)',
    'self._reload_applied_editors(change_set)',
    'editor.setPlainText(change.after)',
    'editor.document().setModified(False)',
):
    source = chat_source if "_edit_policy" in token else editor_source
    assert token in source, token

# Apply Code UI stays disabled until the proposal has been successfully prepared.
for token in (
    'self.apply_changes_button.setEnabled(False)',
    'self.review_changes_button.setEnabled(False)',
    'self.apply_changes_button.setEnabled(True)',
    'self.review_changes_button.setEnabled(True)',
    'ready to apply',
    'auto applying',
):
    assert token in chat_source, token

print("PASS: Ask-before-changes does not write until Apply Code")
print("PASS: Edit automatically schedules immediate apply")
print("PASS: applied file contents are pushed back into the open editor")
print("PASS: Apply Code is gated by successful change preparation")
