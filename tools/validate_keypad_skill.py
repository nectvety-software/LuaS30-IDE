"""Validate prompt/skill keypad cho AI Agent."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
errors=[]
keypad=ROOT/'doc/ai/Keypad.md'
skill=ROOT/'doc/ai/skills/keypad/SKILL.md'
api=ROOT/'doc/reference/API.md'
for p in (keypad,skill):
    if not p.is_file():errors.append(f'missing {p.relative_to(ROOT)}')
text=keypad.read_text(encoding='utf-8') if keypad.is_file() else ''
body=skill.read_text(encoding='utf-8-sig') if skill.is_file() else ''
# frontmatter skill cho SkillService
if not body.startswith('---') or '\nname: keypad\n' not in body.split('---')[1]:
    errors.append('skill thieu frontmatter name: keypad')
if 'description:' not in (body.split('---')[1] if body.startswith('---') else ''):
    errors.append('skill thieu description')
# ten phim Lua phai khop API.md
for name in ('up','down','left','right','ok','softleft','softright','clear','back','keypressed','keyreleased'):
    if name not in text:errors.append(f'Keypad.md thieu ten phim {name!r}')
    if name not in body:errors.append(f'skill thieu ten phim {name!r}')
# canh bao khong dung KEY_* lam identifier Lua
if 'KEY_*' not in text:errors.append('Keypad.md thieu canh bao KEY_*')
# bang 21 nut
if text.count('KEY_') < 15:errors.append('Keypad.md thieu bang nut vat ly')
# API van dong bo
apimd=api.read_text(encoding='utf-8') if api.is_file() else ''
for name in ('softleft','softright','clear','back'):
    if name not in apimd:errors.append(f'API.md khong con ten phim {name!r} (lech contract)')
print('validate_keypad_skill:', 'PASS' if not errors else 'FAIL')
for e in errors:print(' -',e)
sys.exit(1 if errors else 0)
