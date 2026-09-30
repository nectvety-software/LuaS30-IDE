"""Validate skill sfx cho AI Agent (kawaiiak -> LuaS30)."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
errors=[]
skill=ROOT/'doc/ai/skills/sfx/SKILL.md'
prompt=ROOT/'doc/ai/PROMPT.md'
if not skill.is_file():
    errors.append('missing doc/ai/skills/sfx/SKILL.md')
body=skill.read_text(encoding='utf-8-sig') if skill.is_file() else ''
if not body.startswith('---') or '\nname: sfx\n' not in body.split('---')[1]:
    errors.append('skill thieu frontmatter name: sfx')
if 'description:' not in (body.split('---')[1] if body.startswith('---') else ''):
    errors.append('skill thieu description')
for t in ('VOICES','buildWav','LayerSpec','TARGET_RATE','16 kHz','PCM16',
          'make_','--out','--review','manifest','engine.audio_play',
          'has_audio','byte-identical'):
    if t not in body:errors.append(f'skill thieu {t!r}')
text=prompt.read_text(encoding='utf-8') if prompt.is_file() else ''
for t in ('## 31. SFX','skill `sfx`','engine.audio_play'):
    if t not in text:errors.append(f'PROMPT.md thieu directive {t!r}')
print('validate_sfx_skill:', 'PASS' if not errors else 'FAIL')
for e in errors:print(' -',e)
sys.exit(1 if errors else 0)
