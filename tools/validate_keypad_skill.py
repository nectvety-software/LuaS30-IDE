"""Validate prompt/skill keypad cho AI Agent + code keypad trong template du an."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
errors = []

keypad = ROOT / 'doc/ai/Keypad.md'
skill = ROOT / 'doc/ai/skills/keypad/SKILL.md'
api = ROOT / 'doc/reference/API.md'

for p in (keypad, skill):
    if not p.is_file():
        errors.append(f'missing {p.relative_to(ROOT)}')

text = keypad.read_text(encoding='utf-8') if keypad.is_file() else ''
body = skill.read_text(encoding='utf-8-sig') if skill.is_file() else ''

# frontmatter skill cho SkillService
if not body.startswith('---') or '\nname: keypad\n' not in body.split('---')[1]:
    errors.append('skill thieu frontmatter name: keypad')
if 'description:' not in (body.split('---')[1] if body.startswith('---') else ''):
    errors.append('skill thieu description')

# ten phim Lua phai khop API.md
for name in ('up', 'down', 'left', 'right', 'ok', 'softleft', 'softright',
             'clear', 'back', 'keypressed', 'keyreleased'):
    if name not in text:
        errors.append(f'Keypad.md thieu ten phim {name!r}')
    if name not in body:
        errors.append(f'skill thieu ten phim {name!r}')

# canh bao khong dung KEY_* lam identifier Lua
if 'KEY_*' not in text:
    errors.append('Keypad.md thieu canh bao KEY_*')

# bang 21 nut
if text.count('KEY_') < 15:
    errors.append('Keypad.md thieu bang nut vat ly')

# API van dong bo
apimd = api.read_text(encoding='utf-8') if api.is_file() else ''
for name in ('softleft', 'softright', 'clear', 'back'):
    if name not in apimd:
        errors.append(f'API.md khong con ten phim {name!r} (lech contract)')

# --- Code keypad trong template du an ------------------------------------
# Checklist doc/ai/Keypad.md muc 4: khong con chuoi "KEY_*" hay ten phim HOA
# trong code Lua. Comment duoc phep nhac ten hang (vi du trong muc "SAI"),
# nen phai boc comment truoc khi soi.

KEYPAD_NAMES = ('up', 'down', 'left', 'right', 'ok', 'softleft', 'softright',
                'clear', 'back',
                '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '#')

UPPERCASE_KEYS = ('UP', 'DOWN', 'LEFT', 'RIGHT', 'OK', 'SOFTLEFT', 'SOFTRIGHT',
                  'SOFT_RIGHT', 'BACK', 'CLEAR', 'STAR', 'HASH')

MAIN_LUA = (
    ROOT / 'templates/basic/main.lua',
    ROOT / 'templates/keypad-demo/main.lua',
)
CONTRACT_LUA = ROOT / 'templates/keypad-demo/src/keypad.lua'


def strip_lua_comments(src: str) -> str:
    """Bo comment Lua de chi soi phan CODE that.

    Heuristic: trong cac template keypad khong co chuoi nao chua '--', nen cat
    tu lan xuat hien dau tien cua '--' tren moi dong la du va an toan.
    """
    src = re.sub(r'--\[\[.*?\]\]', '', src, flags=re.S)
    return '\n'.join(line.split('--', 1)[0] for line in src.splitlines())


def scan_lua(path: Path) -> str:
    if not path.is_file():
        errors.append(f'missing {path.relative_to(ROOT)}')
        return ''
    code = strip_lua_comments(path.read_text(encoding='utf-8'))
    rel = path.relative_to(ROOT)

    hit = re.search(r'KEY_[A-Z0-9_]*', code)
    if hit:
        errors.append(f'{rel}: nhan nut vat ly {hit.group(0)!r} dung trong code Lua')
    for name in UPPERCASE_KEYS:
        if re.search(r'==\s*"%s"' % name, code):
            errors.append(f'{rel}: so sanh voi ten phim HOA "{name}"')
    return code


for path in MAIN_LUA:
    code = scan_lua(path)
    if not code:
        continue
    rel = path.relative_to(ROOT)
    for hook in ('keypressed', 'keyreleased'):
        if hook not in code:
            errors.append(f'{rel}: thieu {hook}')
    if 'lower()' not in code and 'src.keypad' not in code:
        errors.append(f'{rel}: khong chuan hoa ten phim '
                      '(thieu tostring(k):lower() hoac require("src.keypad"))')

contract = scan_lua(CONTRACT_LUA)
if contract:
    for name in KEYPAD_NAMES:
        if f'"{name}"' not in contract:
            errors.append(f'templates/keypad-demo/src/keypad.lua thieu ten phim {name!r}')
    for fn in ('press', 'release', 'reset', 'down', 'digit', 'drawPad'):
        if f'function M.{fn}' not in contract:
            errors.append(f'templates/keypad-demo/src/keypad.lua thieu ham {fn}')

print('validate_keypad_skill:', 'PASS' if not errors else 'FAIL')
for e in errors:
    print(' -', e)
sys.exit(1 if errors else 0)
