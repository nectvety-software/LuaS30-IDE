from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []
chat = (ROOT/'studio/app/views/ai_chat_view.py').read_text(encoding='utf-8')
dialog = (ROOT/'studio/app/views/ai_provider_dialog.py').read_text(encoding='utf-8')
provider = (ROOT/'studio/app/services/ai_provider_service.py').read_text(encoding='utf-8')
protocol = (ROOT/'studio/app/services/ai_agent_protocol.py').read_text(encoding='utf-8')
changes = (ROOT/'studio/app/services/ai_change_service.py').read_text(encoding='utf-8')
diff = (ROOT/'studio/app/views/ai_diff_view.py').read_text(encoding='utf-8')
editor = (ROOT/'studio/app/views/code_editor_view.py').read_text(encoding='utf-8')
main = (ROOT/'studio/app/ui/main_window.py').read_text(encoding='utf-8')

credential = (ROOT/'studio/app/services/ai_credential_store.py').read_text(encoding='utf-8')
sessions = (ROOT/'studio/app/services/ai_session_service.py').read_text(encoding='utf-8')
tools = (ROOT/'studio/app/services/ai_tool_service.py').read_text(encoding='utf-8')
for token in ('ai_credentials.json', 'save_key', 'load_key', 'delete_key'):
    if token not in credential:
        errors.append('Credential store missing: '+token)
for token in ('ai_sessions.json', 'list_sessions', 'set_active', 'rename', 'delete'):
    if token not in sessions:
        errors.append('Chat session store missing: '+token)
for token in ('class AIReadOnlyToolService', 'def _read', 'def _grep', 'def _glob'):
    if token not in tools:
        errors.append('Read-only agent tools missing: '+token)

for token in (
    'Ask before changes', 'Edit automatically', 'Plan mode', 'Full access',
    'CODE CHANGES', 'Apply Code', 'Review Changes', 'open_provider_settings',
):
    if token not in chat:
        errors.append('ChatAI v1 missing: '+token)

for token in ('Test Connection','Apply','Save & Close','AIConnectionTestThread'):
    if token not in dialog:
        errors.append('Provider dialog missing: '+token)

cfg = provider.split('class ProviderConfig',1)[1].split('class AIProviderConfigStore',1)[0]
if 'api_key:' in cfg:
    errors.append('ProviderConfig should keep credentials in the dedicated credential store')
for token in ('enable_shell','enable_code_edits','show_reasoning','test_provider_connection'):
    if token not in provider:
        errors.append('Provider service missing: '+token)

for token in ('class CodeEditAction','EDIT_RE','```luas30-edit','code_edits'):
    if token not in protocol:
        errors.append('Edit protocol missing: '+token)

for token in (
    'class AIChangeService', '.luas30', 'ai-backups', 'os.replace',
    'Absolute AI edit path is not allowed', 'AI edit escaped the project root',
):
    if token not in changes:
        errors.append('AIChangeService missing: '+token)

for token in ('class AIDiffView','CURRENT','PROPOSED','Apply Code','mark_applied'):
    if token not in diff:
        errors.append('AI diff view missing: '+token)

for token in (
    'self.ai_chat.changes_proposed.connect(self._prepare_ai_changes)',
    'def _apply_ai_changes', 'def _reject_ai_changes', 'def _show_ai_diff',
):
    if token not in editor:
        errors.append('CodeEditorView AI change wiring missing: '+token)

if 'VERSION = "1.15.0"' not in main:
    errors.append('MainWindow version is not 1.15.0')

if errors:
    print('FAIL')
    for error in errors:
        print(' -', error)
    raise SystemExit(1)

print('PASS: four access modes are installed under ChatAI composer')
print('PASS: provider dialog includes Test / Apply / Save & Close')
print('PASS: provider preferences stay separate from dedicated local JSON credentials')
print('PASS: structured AI edit protocol is installed')
print('PASS: project-scoped atomic AI change service with backups is installed')
print('PASS: VS Code-like AI Changes review tab is installed')
print('PASS: persistent JSON API credentials and project chat sessions are installed')
print('PASS: read/grep/glob agent tools are installed')
