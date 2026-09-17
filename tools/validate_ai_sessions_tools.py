from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "studio"))

from app.services.ai_agent_protocol import parse_agent_response
from app.services.ai_credential_store import AICredentialStore
from app.services.ai_session_service import AIChatSessionStore
from app.services.ai_tool_service import AIReadOnlyToolService

with tempfile.TemporaryDirectory() as td:
    base = Path(td)

    creds = AICredentialStore(base / "ai_credentials.json")
    creds.save_key("openai", "sk-test-local-json")
    assert creds.load_key("openai") == "sk-test-local-json"
    assert "openai" in creds.providers()
    creds.delete_key("openai")
    assert creds.load_key("openai") == ""

    sessions = AIChatSessionStore(base / "ai_sessions.json")
    project = base / "project"
    project.mkdir()
    first = sessions.create(project, provider="openai", model="demo", access_mode="edit_auto")
    sessions.update(
        first.id,
        messages=[
            {"role": "user", "content": "Fix main.lua"},
            {"role": "assistant", "content": "Prepared changes"},
            {"role": "user", "content": "internal tool result", "_internal": True},
        ],
    )
    resumed = sessions.active(project)
    assert resumed is not None and resumed.id == first.id
    assert resumed.title.startswith("Fix main.lua")
    second = sessions.create(project, title="Second")
    assert sessions.active(project).id == second.id
    assert sessions.set_active(project, first.id)
    assert sessions.active(project).id == first.id
    assert len(sessions.list_sessions(project)) == 2
    assert sessions.rename(first.id, "Main fix").title == "Main fix"

    (project / "main.lua").write_text(
        "local value = 42\nfunction draw()\n  return value\nend\n",
        encoding="utf-8",
    )
    (project / "util.lua").write_text("return { value = 42 }\n", encoding="utf-8")
    tools = AIReadOnlyToolService(max_output=4000)
    parsed = parse_agent_response(
        '```luas30-tool\n{"tool":"grep","args":{"pattern":"value","include":"**/*.lua"},"reason":"find value"}\n```'
    )
    assert len(parsed.tool_actions) == 1
    grep_result = tools.execute(project, parsed.tool_actions[0])
    assert "main.lua:1" in grep_result
    assert "util.lua:1" in grep_result

    parsed_read = parse_agent_response(
        '```luas30-tool\n{"tool":"read","args":{"path":"main.lua","start_line":1,"end_line":2}}\n```'
    )
    read_result = tools.execute(project, parsed_read.tool_actions[0])
    assert "local value = 42" in read_result

    parsed_glob = parse_agent_response(
        '```luas30-tool\n{"tool":"glob","args":{"pattern":"**/*.lua"}}\n```'
    )
    glob_result = tools.execute(project, parsed_glob.tool_actions[0])
    assert "main.lua" in glob_result and "util.lua" in glob_result

print("PASS: API keys save/load/delete in local JSON")
print("PASS: project-scoped chat sessions create/resume/switch/rename")
print("PASS: OpenCode-inspired read/grep/glob agent tools parse and execute")
