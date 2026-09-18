"""Validate hop thoai thiet lap lan dau + policy terminal khong tu chay."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
STUDIO=ROOT/'studio'
errors=[]
def need(path):
    if not (ROOT/path).is_file():errors.append(f'missing {path}')
def has(path,text):
    try:data=(ROOT/path).read_text(encoding='utf-8')
    except Exception as e:errors.append(f'{path}: {e}');return
    if text not in data:errors.append(f'{path} thieu {text!r}')
need('studio/app/views/setup_dialog.py')
need('studio/app/services/environment_setup.py')
need('tools/install_vc_runtime.py')
for t in ('Thiết lập LuaS30 IDE lần đầu','Bỏ qua','Kiểm tra lại','Tự động cài đặt','Hoàn tất',
          'Đã có','Có thể cài tự động','Cần làm thủ công','setup_completed'):
    has('studio/app/views/setup_dialog.py',t)
for t in ('class Requirement','def detect_missing','def installable','def is_first_run',
          'def mark_setup_done','class EnvironmentInstaller','pyside_libs','arm_gcc',
          'emulator','lua_src','build_tools','vc_runtime'):
    has('studio/app/services/environment_setup.py',t)
for t in ('vc_redist','aka.ms', '--check'):
    has('tools/install_vc_runtime.py',t)
for t in ('first_run_setup_action','Chạy lại thiết lập lần đầu','_run_first_run_setup',
          '_maybe_first_run_setup','singleShot(800'):
    has('studio/app/vxpui/main_window.py',t)
for banned in ('_autostart_terminal','autostart_background'):
    data=(ROOT/'studio/app/vxpui/main_window.py').read_text(encoding='utf-8')
    if banned in data:errors.append(f'studio/app/vxpui/main_window.py van con {banned!r}')
for t in ('def ensure_started(self, focus', 'def show_prompt(self, prompt:'):
    has('studio/app/widgets/terminal_view.py',t)
print('validate_setup_dialog:', 'PASS' if not errors else 'FAIL')
for e in errors:print(' -',e)
sys.exit(1 if errors else 0)
