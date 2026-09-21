"""Validate watcher PID gia lap: tat/crash -> Stopped, khong ket Running."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
errors=[]
src=(ROOT/'studio/app/services/emulator_service.py').read_text(encoding='utf-8')
for t in ('def pid_alive','GetExitCodeProcess','_start_watching','_stop_watching',
          '_watch_tick','_watched_pid','_WATCH_INTERVAL_MS','Trạng thái: Stopped'):
    if t not in src:errors.append(f'emulator_service.py thieu {t!r}')
print('validate_emulator_watch:', 'PASS' if not errors else 'FAIL')
for e in errors:print(' -',e)
sys.exit(1 if errors else 0)
