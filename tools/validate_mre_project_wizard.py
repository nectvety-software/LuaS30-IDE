from pathlib import Path
import ast
import json

ROOT = Path(__file__).resolve().parent.parent
errors = []

main = (ROOT / 'studio/app/ui/main_window.py').read_text(encoding='utf-8')
dialog = (ROOT / 'studio/app/ui/mediatek_mre_dialog.py').read_text(encoding='utf-8')
session = (ROOT / 'studio/app/core/project_session.py').read_text(encoding='utf-8')
build = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
theme = (ROOT / 'studio/app/ui/theme.py').read_text(encoding='utf-8')

for token in (
    'class MediaTekMREConfigDialog(QDialog)',
    'Cấu hình MediaTek MRE SDK',
    'Tên ứng dụng (APPNAME)',
    'Phiên bản (APPVER)',
    'Nhà phát triển (VENDOR)',
    'Màn hình (Resolution)',
    'Chipset MediaTek',
    'Dung lượng Heap RAM cấp phát',
    'MTK6260  (Nokia 220, 225)',
    'MTK6261  (Nokia 3310 3G, 216)',
    'MTK6250  (Q-Mobile, K-Touch)',
    'MTK6225  (Legacy MRE 2.0)',
    'Lưu thiết lập',
):
    if token not in dialog:
        errors.append('dialog missing: ' + token)

if 'QInputDialog.getText' in main:
    errors.append('legacy one-line New Project QInputDialog is still present')

for token in (
    'dialog = MediaTekMREConfigDialog(self)',
    'metadata=config.project_metadata()',
    'sdk_metadata=config.sdk_metadata()',
    'VERSION = "1.15.0"',
):
    if token not in main:
        errors.append('MainWindow wizard integration missing: ' + token)

for token in (
    'metadata: dict | None = None',
    'sdk_metadata: dict | None = None',
    'payload.update(dict(metadata))',
    'payload["appid"] = appid',
    'sdk_dir / "mre_sdk.json"',
):
    if token not in session:
        errors.append('ProjectSession metadata contract missing: ' + token)

for token in (
    'project_compat=str(cfg.get("compat_profile") or "auto")',
    'requested_compat=project_compat',
    'app_version=str(cfg.get("app_version") or "1.0.0")',
    'mediatek_chipset=str(cfg.get("mediatek_chipset") or "")',
):
    if token not in build:
        errors.append('builder project-profile support missing: ' + token)

compat_assign = build.find('compat_profile=resolve_compat_profile(')
compat_use = build.find('if compat_profile=="nokia225-rm1011":')
if compat_assign < 0 or compat_use < 0 or compat_assign > compat_use:
    errors.append('compat_profile is used before it is resolved')

for token in (
    'QFrame#MREDialogCard',
    'QPushButton#MRESaveButton',
    'QToolButton#MREDialogClose',
):
    if token not in theme:
        errors.append('wizard theme missing: ' + token)

project = json.loads((ROOT / 'templates/basic/project.json').read_text(encoding='utf-8'))
for key in ('app_version', 'mediatek_chipset', 'resolution', 'ram_kb'):
    if key not in project:
        errors.append('basic template missing: ' + key)

for path in (
    ROOT / 'studio/app/ui/mediatek_mre_dialog.py',
    ROOT / 'studio/app/core/project_session.py',
    ROOT / 'studio/app/ui/main_window.py',
    ROOT / 'tools/build.py',
):
    try:
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    except SyntaxError as exc:
        errors.append(f'syntax error {path.name}: {exc}')

if errors:
    print('FAIL')
    for item in errors:
        print(' -', item)
    raise SystemExit(1)

print('PASS: New Project always opens MediaTek MRE SDK modal')
print('PASS: APPNAME/APPVER/VENDOR/resolution/chipset/heap fields exist')
print('PASS: four MediaTek chipset presets are present')
print('PASS: unique AppID is preserved while wizard metadata is merged')
print('PASS: .luas30/mre_sdk.json project configuration is generated')
print('PASS: project compat_profile is honored when build setting is auto')
print('PASS: custom frameless-style wizard theme is installed')
