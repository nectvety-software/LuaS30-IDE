"""Validate skills gameplay + gfx-styles cho AI Agent."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
errors=[]
for name in ('gameplay','gfx-styles'):
    skill=ROOT/f'doc/ai/skills/{name}/SKILL.md'
    if not skill.is_file():
        errors.append(f'missing doc/ai/skills/{name}/SKILL.md')
        continue
    body=skill.read_text(encoding='utf-8-sig')
    if not body.startswith('---') or f'\nname: {name}\n' not in body.split('---')[1]:
        errors.append(f'{name} thieu frontmatter name: {name}')
    if 'description:' not in (body.split('---')[1] if body.startswith('---') else ''):
        errors.append(f'{name} thieu description')
for t in ('Object pool','Platformer','Runner','Puzzle','Battle theo lượt','Save điểm',
          'flush','15 FPS'):
    if t not in (ROOT/'doc/ai/skills/gameplay/SKILL.md').read_text(encoding='utf-8'):
        errors.append(f'gameplay thieu {t!r}')
for t in ('8-bit','2.5D','raycaster','Mode7','isometric','parallax','1 lần/frame'):
    if t not in (ROOT/'doc/ai/skills/gfx-styles/SKILL.md').read_text(encoding='utf-8'):
        errors.append(f'gfx-styles thieu {t!r}')
text=(ROOT/'doc/ai/PROMPT.md').read_text(encoding='utf-8')
for t in ('## 32. GAMEPLAY','skill `gameplay`','skill `vpe-assets`'):
    if t not in text:errors.append(f'PROMPT.md thieu directive {t!r}')
print('validate_game_skills:', 'PASS' if not errors else 'FAIL')
for e in errors:print(' -',e)
sys.exit(1 if errors else 0)
