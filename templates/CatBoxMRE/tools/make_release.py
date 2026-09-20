from pathlib import Path
import shutil,subprocess,sys,zipfile,json
R=Path(__file__).resolve().parents[1]
subprocess.check_call([sys.executable,str(R/'tools/check_nokia225_config.py')])
subprocess.check_call([sys.executable,str(R/'tools/bundle_main.py')])
subprocess.check_call([sys.executable,str(R/'tools/memory_guard.py')])
subprocess.check_call([sys.executable,str(R/'tools/validate_project.py')])
subprocess.check_call([sys.executable,str(R/'tools/smoke_test.py')])
meta=json.loads((R/'project.json').read_text(encoding='utf-8'))
version=str(meta.get('app_version') or meta.get('version') or '0.1.3')
out=R/'release'; shutil.rmtree(out,ignore_errors=True); out.mkdir()
for p in ['project.json','conf.lua','main.lua','NOKIA225_SETUP.md']:
    shutil.copy2(R/p,out/p)
(out/'assets').mkdir(); shutil.copy2(R/'assets/sprite_atlas.png',out/'assets/sprite_atlas.png')
(out/'.luas30').mkdir(); shutil.copy2(R/'.luas30/mre_sdk.json',out/'.luas30/mre_sdk.json')
(out/'README_RELEASE.txt').write_text(
    f'CatBoxMRE {version} VXP-ready source for Nokia 225 Dual SIM RM-1011 / MTK6260. '
    'Open/import with LuaS30 Studio. Boot log: catbox_boot.log.\n',encoding='utf-8')
zip_path=R.parent/f'CatBoxMRE_Nokia225_v{version}_VXP-ready.zip'
if zip_path.exists(): zip_path.unlink()
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for f in out.rglob('*'):
        if f.is_file(): z.write(f,f.relative_to(out))
print('Release:',zip_path)
