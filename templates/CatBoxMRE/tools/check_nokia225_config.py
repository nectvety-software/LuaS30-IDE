#!/usr/bin/env python3
from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[1]
errors=[]
try:
    p=json.loads((R/'project.json').read_text(encoding='utf-8'))
except Exception as e:
    print('[FAIL] project.json:',e); raise SystemExit(2)
try:
    s=json.loads((R/'.luas30/mre_sdk.json').read_text(encoding='utf-8'))
except Exception as e:
    print('[FAIL] .luas30/mre_sdk.json:',e); raise SystemExit(2)
checks={
 'project compat_profile': p.get('compat_profile')=='nokia225-rm1011',
 'project chipset': p.get('mediatek_chipset')=='MTK6260',
 'project resolution': p.get('resolution')=='240x320' and p.get('screen_width')==240 and p.get('screen_height')==320,
 'project RAM': p.get('ram_kb')==512,
 'project MRE API': p.get('mre_api')=='Audio File ProMng',
 'studio compat_profile': s.get('compat_profile')=='nokia225-rm1011',
 'studio chipset': (s.get('mediatek_chipset') or s.get('chipset'))=='MTK6260',
 'studio resolution': s.get('screen_width')==240 and s.get('screen_height')==320,
 'studio RAM': (s.get('ram_kb') or s.get('heap_kb'))==512,
 'studio device': s.get('device_type')=='RM-1011',
}
for name,ok in checks.items():
    print(('[PASS] ' if ok else '[FAIL] ')+name)
    if not ok: errors.append(name)
if errors:
    print('NOKIA225_CONFIG_FAIL',len(errors)); sys.exit(1)
print('NOKIA225_CONFIG_OK')
