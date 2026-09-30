"""Validate skill vpe-assets cho AI Agent (Pixel_Editor -> LuaS30)."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
errors=[]
skill=ROOT/'doc/ai/skills/vpe-assets/SKILL.md'
prompt=ROOT/'doc/ai/PROMPT.md'
if not skill.is_file():
    errors.append('missing doc/ai/skills/vpe-assets/SKILL.md')
body=skill.read_text(encoding='utf-8-sig') if skill.is_file() else ''
if not body.startswith('---') or '\nname: vpe-assets\n' not in body.split('---')[1]:
    errors.append('skill thieu frontmatter name: vpe-assets')
if 'description:' not in (body.split('---')[1] if body.startswith('---') else ''):
    errors.append('skill thieu description')
for t in ('VPE565','vpe_tool.py','inspect','atlas','tileset','header',
          'engine.image','colorkey','integer scale','nearest',
          'Documents\\VPE Pixel','tools/build.py'):
    if t not in body:errors.append(f'skill thieu {t!r}')
text=prompt.read_text(encoding='utf-8') if prompt.is_file() else ''
for t in ('## 30. VPE ASSETS','vpe-assets','vpe_tool.py'):
    if t not in text:errors.append(f'PROMPT.md thieu directive {t!r}')
print('validate_vpe_assets_skill:', 'PASS' if not errors else 'FAIL')
for e in errors:print(' -',e)
sys.exit(1 if errors else 0)
