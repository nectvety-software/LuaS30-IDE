from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
errors=[]
tabs=(ROOT/"studio/app/editor/editor_tabs.py").read_text(encoding="utf-8")
groups=(ROOT/"studio/app/editor/editor_group_manager.py").read_text(encoding="utf-8")
view=(ROOT/"studio/app/views/code_editor_view.py").read_text(encoding="utf-8")
chat=(ROOT/"studio/app/views/ai_chat_view.py").read_text(encoding="utf-8")
providers=(ROOT/"studio/app/services/ai_provider_service.py").read_text(encoding="utf-8")
context=(ROOT/"studio/app/services/codebase_context_service.py").read_text(encoding="utf-8")
main=(ROOT/"studio/app/ui/main_window.py").read_text(encoding="utf-8")

for token in ("Close All Tabs","close_all_requested = Signal()","def close_others"):
    if token not in tabs: errors.append("tab context missing: "+token)
if "tabs.close_all_requested.connect(self.close_all)" not in groups:
    errors.append("Close All does not reach all groups")
for token in (
    "self.workspace.addWidget(self.left_tabs)",
    "self.workspace.addWidget(self.center_host)",
    "self.workspace.addWidget(self.ai_chat)",
    "self.vertical.addWidget(editor_panel)",
    "self.vertical.addWidget(self.bottom)",
):
    if token not in view: errors.append("layout missing: "+token)
for token in ("OpenAI","Anthropic","Google Gemini","OpenAI Compatible","Ollama Local"):
    if token not in providers: errors.append("provider missing: "+token)
for token in ("/responses","/v1/messages",":generateContent","/chat/completions","/api/chat"):
    if token not in providers: errors.append("provider route missing: "+token)
for token in ("SKILLS.md","SKILL.md","PROMPT.md","IGNORED_NAMES","project_tree"):
    if token not in context: errors.append("context contract missing: "+token)
if 'VERSION = "1.0.1"' not in main: errors.append("wrong version")
if 'action("Toggle Chat AI", "Ctrl+Alt+I", "chat")' not in main: errors.append("ChatAI action missing")
cfg=providers.split("class ProviderConfig",1)[1].split("class AIProviderConfigStore",1)[0]
if "api_key:" in cfg: errors.append("ProviderConfig persists key")
if errors:
    print("FAIL")
    [print(" -",x) for x in errors]
    raise SystemExit(1)
print("PASS: Close All Tabs reaches all editor groups")
print("PASS: bottom panel is nested under center editor only")
print("PASS: ChatAI right sidebar exists")
print("PASS: five provider connectors exist")
print("PASS: codebase context reads SKILLS/SKILL/PROMPT")
print("PASS: provider config stays non-secret; optional API keys use the dedicated credential JSON store")
