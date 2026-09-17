from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'studio'))

from app.services.ai_agent_protocol import (
    parse_agent_response,
    classify_shell_command,
    bounded_shell_output,
)

sample = (
    "Answer text.\n"
    "```luas30-summary\n"
    "- inspect build\n"
    "- run validator\n"
    "```\n"
    "```luas30-shell\n"
    '{"command":"python tools/validate_x.py","cwd":"project","reason":"validate"}\n'
    "```"
)
parsed = parse_agent_response(sample)
assert parsed.visible_text == 'Answer text.'
assert 'inspect build' in parsed.reasoning_summary
assert len(parsed.shell_actions) == 1
assert parsed.shell_actions[0].command == 'python tools/validate_x.py'

assert classify_shell_command('git status')[0] == 'safe'
assert classify_shell_command('rm -rf build')[0] == 'dangerous'
assert classify_shell_command('set')[0] == 'sensitive'
assert classify_shell_command('python tools/build.py --no-run')[0] == 'project'

os.environ['LUAS30_TEST_SECRET_TOKEN'] = 'abcde-12345-secret'
redacted = bounded_shell_output('token=abcde-12345-secret')
assert 'abcde-12345-secret' not in redacted
assert '<redacted:LUAS30_TEST_SECRET_TOKEN>' in redacted

long_value = bounded_shell_output('x' * 30000, limit=1000)
assert len(long_value) < 1200
assert 'truncated' in long_value

print('PASS: summary and shell fenced blocks parse correctly')
print('PASS: safe/project/sensitive/dangerous shell classes')
print('PASS: secret-bearing environment values are redacted')
print('PASS: shell output is bounded before AI continuation')

# Compatibility fallback: providers that ignore the structured edit protocol and
# return a complete fenced active-file body must still create an edit proposal.
old_lua = """-- demo\nlocal E = engine\nfunction E.load()\n  E.set_font(8)\nend\nfunction E.draw()\n  E.clear(E.color(0,0,0))\nend\n"""
plain_code = """Updated the active file.\n```lua\n-- demo fixed\nlocal E = engine\nlocal x = 0\nfunction E.load()\n  E.set_font(8)\nend\nfunction E.update(dt)\n  x = x + 1\nend\nfunction E.draw()\n  E.clear(E.color(0,0,0))\n  E.text(2,2,tostring(x),E.color(255,255,255))\nend\n```\n"""
recovered = parse_agent_response(
    plain_code,
    active_path='main.lua',
    active_text=old_lua,
    user_request='hãy sửa và cập nhật main.lua',
    allow_plain_code_edit=True,
)
assert recovered.recovered_plain_edit is True
assert len(recovered.code_edits) == 1
assert recovered.code_edits[0].path == 'main.lua'
assert 'local x = 0' in (recovered.code_edits[0].content or '')
assert '```lua' not in recovered.visible_text

readonly = parse_agent_response(
    plain_code,
    active_path='main.lua',
    active_text=old_lua,
    user_request='giải thích code này',
    allow_plain_code_edit=True,
)
assert readonly.recovered_plain_edit is False
assert len(readonly.code_edits) == 0
print('PASS: plain fenced source is safely recovered into an active-file edit proposal')
