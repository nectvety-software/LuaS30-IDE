from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'studio'))

from app.services.ai_agent_protocol import CodeEditAction, parse_agent_response
from app.services.ai_change_service import AIChangeService

sample = '''Answer\n```luas30-edit\n[{"path":"main.lua","find":"old","replace":"new","reason":"fix"}]\n```'''
parsed = parse_agent_response(sample)
assert parsed.visible_text == 'Answer'
assert len(parsed.code_edits) == 1
assert parsed.code_edits[0].path == 'main.lua'

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    target = root/'main.lua'
    target.write_text('local value = "old"\n', encoding='utf-8')
    service = AIChangeService()
    change_set = service.prepare(
        root,
        [CodeEditAction(path='main.lua', find='old', replace='new', reason='fix')],
    )
    assert change_set.changed_files == 1
    assert 'new' in change_set.changes[0].after
    applied, backup = service.apply(change_set)
    assert applied == [target.resolve()]
    assert 'new' in target.read_text(encoding='utf-8')
    assert backup is not None and (backup/'main.lua').is_file()
    assert 'old' in (backup/'main.lua').read_text(encoding='utf-8')

    try:
        service.prepare(root, [CodeEditAction(path='../escape.lua', content='bad')])
    except ValueError:
        pass
    else:
        raise AssertionError('path traversal was not blocked')

    try:
        service.prepare(root, [CodeEditAction(path='.env', content='SECRET=x')])
    except ValueError:
        pass
    else:
        raise AssertionError('secret file target was not blocked')

print('PASS: luas30-edit blocks parse')
print('PASS: find/replace change set prepares and applies')
print('PASS: existing files are backed up before atomic replacement')
print('PASS: project traversal and secret-file targets are blocked')
