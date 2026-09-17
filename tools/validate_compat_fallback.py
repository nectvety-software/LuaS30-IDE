"""Validate fallback standalone khi project xin native nhung thieu MRE SDK."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
errors=[]
build=(ROOT/'tools/build.py').read_text(encoding='utf-8')
for t in ('explicit_native=requested_compat in',
          'Fallback sang backend',
          'Chi --compat-profile native explicit moi giu loi strict',
          'if compat_profile=="nokia225-rm1011" or project_compat=="nokia225-rm1011"'):
    if t not in build:errors.append(f'build.py thieu {t!r}')
compat=(ROOT/'tools/s30plus_compat.py').read_text(encoding='utf-8')
if 'requires an MRE SDK root containing' not in compat:
    errors.append('s30plus_compat mat loi strict cho native explicit')
print('validate_compat_fallback:', 'PASS' if not errors else 'FAIL')
for e in errors:print(' -',e)
sys.exit(1 if errors else 0)
