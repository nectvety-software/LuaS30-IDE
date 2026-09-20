#!/usr/bin/env python3
from pathlib import Path
import json,re,sys
R=Path(__file__).resolve().parents[1]
errors=[]
required=['project.json','conf.lua','main.lua','main_dev.lua','src/engine.lua','src/game.lua','src/render.lua','src/99_entry.lua','assets/sprite_atlas.png']
for rel in required:
    if not (R/rel).exists(): errors.append('missing '+rel)
try:
    p=json.loads((R/'project.json').read_text(encoding='utf-8'))
    if p.get('entry')!='main.lua': errors.append('entry must be main.lua')
    if p.get('type')!='application': errors.append('project type must be application for LuaS30 Studio')
    t=p.get('target',{})
    if not isinstance(t,dict): errors.append('target must be an object')
    else:
        if (t.get('screen_width'),t.get('screen_height'))!=(240,320): errors.append('screen must be 240x320')
        if t.get('target_fps')!=15: errors.append('target FPS must be 15')
        if t.get('target_ram_kb')!=512: errors.append('target RAM must be 512 KB')
    if not p.get('compat_profile'): errors.append('compat_profile missing')
    if not isinstance(p.get('appid'),int): errors.append('appid missing')
except Exception as e:
    errors.append('project.json invalid: '+str(e))
main=(R/'main.lua').read_text(encoding='utf-8') if (R/'main.lua').exists() else ''
for banned in ('require','dofile','loadfile'):
    if re.search(r'\b'+banned+r'\s*\(',main): errors.append('main.lua contains runtime loader: '+banned)
for needle in ('life.load = function() boot() end','life.draw = function() CatBoxRuntime.draw() end','Engine.boot_log("DRAW1 ENTER")','Engine.flush()'):
    if needle not in main: errors.append('missing runtime binding: '+needle)
if '_G' in main or 'rawget(' in main: errors.append('production main.lua still depends on _G/rawget')
if errors:
    print('VALIDATION FAILED')
    for e in errors: print(' -',e)
    sys.exit(1)
print('VALIDATION OK')
