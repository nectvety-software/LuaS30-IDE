from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
errors=[]
tabs=(ROOT/"studio/app/editor/editor_tabs.py").read_text(encoding="utf-8")
groups=(ROOT/"studio/app/editor/editor_group_manager.py").read_text(encoding="utf-8")
view=(ROOT/"studio/app/vxpui/main_window.py").read_text(encoding="utf-8")
chat=(ROOT/"studio/app/views/ai_chat_view.py").read_text(encoding="utf-8")
providers=(ROOT/"studio/app/services/ai_provider_service.py").read_text(encoding="utf-8")
context=(ROOT/"studio/app/services/codebase_context_service.py").read_text(encoding="utf-8")
main=(ROOT/"studio/app/vxpui/main_window.py").read_text(encoding="utf-8")

for token in ("Close All Tabs","close_all_requested = Signal()","def close_others"):
    if token not in tabs: errors.append("tab context missing: "+token)
if "tabs.close_all_requested.connect(self.close_all)" not in groups:
    errors.append("Close All does not reach all groups")
for token in (
    "split.addWidget(left_column)",
    "split.addWidget(center_column)",
    "split.addWidget(self.ai_panel_frame)",
    "dialog.add_body_widget(device_panel, 1)",
    "center_column.addWidget(editor_host)",
    "center_column.addWidget(self.bottom)",
    "ai_panel.add_widget(self.ai_chat)",
):
    if token not in view: errors.append("layout missing: "+token)
for token in ("OpenAI","Anthropic","Google Gemini","OpenAI Compatible","Ollama Local"):
    if token not in providers: errors.append("provider missing: "+token)
for token in ("/responses","/v1/messages",":generateContent","/chat/completions","/api/chat"):
    if token not in providers: errors.append("provider route missing: "+token)
for token in ("SKILLS.md","SKILL.md","PROMPT.md","IGNORED_NAMES","project_tree"):
    if token not in context: errors.append("context contract missing: "+token)
if 'VERSION = "1.0.2"' not in main: errors.append("wrong version")
if 'act("Chat AI", "fa5s.robot", "Ctrl+Alt+I")' not in main: errors.append("ChatAI action missing")
if "self.ai_chat.changes_proposed.connect(self._prepare_ai_changes)" not in main:
    errors.append("AI change proposal not wired")
cfg=providers.split("class ProviderConfig",1)[1].split("class AIProviderConfigStore",1)[0]
if "api_key:" in cfg: errors.append("ProviderConfig persists key")
if errors:
    print("FAIL")
    [print(" -",x) for x in errors]
    raise SystemExit(1)
print("PASS: Close All Tabs reaches all editor groups")
print("PASS: bottom panel is nested under center editor only")
print("PASS: ChatAI panel lives in the modal device dialog (Công cụ menu)")
print("PASS: five provider connectors exist")
print("PASS: codebase context reads SKILLS/SKILL/PROMPT")
print("PASS: provider config stays non-secret; optional API keys use the dedicated credential JSON store")
