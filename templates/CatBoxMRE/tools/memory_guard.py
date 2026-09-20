#!/usr/bin/env python3
from pathlib import Path
import shutil,subprocess,sys,tempfile,re
R=Path(__file__).resolve().parents[1]
main=R/'main.lua'
if not main.exists():
    raise SystemExit('main.lua missing')
size=main.stat().st_size
MAX_SOURCE=92_000
if size>MAX_SOURCE:
    raise SystemExit(f'MEMORY_GUARD_FAIL source={size} > {MAX_SOURCE} bytes')
print(f'[PASS] main.lua source {size} bytes <= {MAX_SOURCE}')

lua=shutil.which('lua5.1') or shutil.which('lua') or shutil.which('texlua')
if lua:
    probe="""collectgarbage('collect')\nlocal b=collectgarbage('count')\nlocal f,e=loadfile(arg[1]); assert(f,e)\ncollectgarbage('collect')\nlocal a=collectgarbage('count')\nprint(string.format('COMPILE_DELTA_KB=%.1f',a-b))\n"""
    with tempfile.NamedTemporaryFile('w',suffix='.lua',delete=False,encoding='utf-8') as f:
        f.write(probe); tmp=f.name
    r=subprocess.run([lua,tmp,str(main)],capture_output=True,text=True)
    Path(tmp).unlink(missing_ok=True)
    if r.returncode!=0:
        print(r.stdout); print(r.stderr,file=sys.stderr); raise SystemExit(r.returncode)
    print(r.stdout.strip())
    m=re.search(r'COMPILE_DELTA_KB=([0-9.]+)',r.stdout)
    if m and float(m.group(1))>285.0:
        raise SystemExit('MEMORY_GUARD_FAIL compile delta exceeds 285 KB host regression budget')
else:
    print('[WARN] Lua interpreter not found; compile-heap regression check skipped')
print('MEMORY_GUARD_OK')
