from pathlib import Path
import ast,sys
ROOT=Path(__file__).resolve().parent.parent
required=[
 'run.bat','build.bat','build_only.bat','studio/main.py','studio/app/ui/main_window.py',
 'studio/app/views/code_editor_view.py','studio/app/editor/explorer_panel.py','studio/app/editor/project_tree.py',
 'studio/app/views/assets_view.py','studio/app/views/ui_designer_view.py',
 'sdk/luas30/include/ls30/api.h','sdk/luas30/src/abi_resolver.c','sdk/luas30/src/api.c',
 'engine/src/runtime_entry.c','engine/src/runtime_bridge.c','engine/src/runtime_lua.c',
 'vendor/lua-5.1.5/src/lua.h','tools/build.py','tools/run_emulator.py','tools/env_check.py',
 'toolchain/arm-gcc/bin/arm-none-eabi-gcc.exe','toolchain/arm-gcc/bin/arm-none-eabi-readelf.exe',
 'emulator/VXPEmu.exe','emulator/Qt6Core.dll','emulator/Qt6Gui.dll','emulator/Qt6Widgets.dll','emulator/unicorn.dll','emulator/platforms/qwindows.dll'
]
missing=[x for x in required if not (ROOT/x).is_file()]
errors=[]
for p in list((ROOT/'studio').rglob('*.py'))+list((ROOT/'tools').glob('*.py')):
    try:ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
    except Exception as e:errors.append(f'{p.relative_to(ROOT)}: {e}')
print('LuaS30 IDE 1.6 NativeSDK validation')
print('Required files:',len(required)-len(missing),'/',len(required))
print('Python syntax:', 'PASS' if not errors else 'FAIL')
if missing:
    print('Missing:');[print(' -',x) for x in missing]
if errors:
    print('Syntax errors:');[print(' -',x) for x in errors]
raise SystemExit(1 if missing or errors else 0)
