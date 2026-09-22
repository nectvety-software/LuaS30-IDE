"""Validate end-to-end: template du an Keypad Demo + khung basic.

Kiem tra that, khong chi doc code:
  1. MediaTekMREConfigDialog co muc "Keypad Demo" trong combo template.
  2. ProjectSession.create_project(template_name="keypad-demo") tao duoc du an
     that: copy template, rewrite identity (appid moi), merge wizard metadata,
     ghi .luas30/mre_sdk.json.
  3. Lua cua du an VUA TAO chay dung hop dong phim — chay
     tools/keypad_template_check.lua bang Lua 5.1 neu tim thay binary.
  4. templates/basic (khung ma MOI du an moi deu copy) van nap/ve/xu ly phim
     dung — chay tools/basic_template_check.lua.

Lua 5.1 la tuy chon: dat bien moi truong LUA_BIN, hoac build tu
vendor/lua-5.1.5/src (xem header tools/keypad_template_check.lua). Khong co
binary thi cac buoc Lua bao SKIP chu khong bao FAIL.

Chay:  py -3.12 tools/validate_project_templates_e2e.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'studio'))

errors: list[str] = []
TEMPLATE_ID = 'keypad-demo'
TEMPLATE_APPID = 586534797


def find_lua() -> Path | None:
    env = os.environ.get('LUA_BIN')
    candidates = [Path(env)] if env else []
    candidates += [
        ROOT / 'build' / '_lua51' / 'lua.exe',
        ROOT / 'tools' / 'lua51' / 'lua.exe',
        ROOT / 'vendor' / 'lua-5.1.5' / 'src' / 'lua.exe',
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate
    found = shutil.which('lua') or shutil.which('lua5.1')
    return Path(found) if found else None


def run_harness(cwd: Path, harness: Path, label: str, lua: Path | None) -> None:
    """Chay mot harness Lua trong `cwd`; thieu binary thi SKIP, khong FAIL."""
    if lua is None:
        print(f'SKIP: khong tim thay Lua 5.1 cho "{label}" (dat LUA_BIN de chay)')
        return
    result = subprocess.run(
        [str(lua), str(harness)], cwd=str(cwd), capture_output=True, text=True,
    )
    tail = (result.stdout or '').strip().splitlines()[-3:]
    if result.returncode != 0:
        errors.append(f'{label} FAIL:\n    ' + '\n    '.join(tail))
    else:
        print(f'{label}: ' + ' | '.join(tail))


LUA = find_lua()
HARNESS_KEYPAD = ROOT / 'tools' / 'keypad_template_check.lua'
HARNESS_BASIC = ROOT / 'tools' / 'basic_template_check.lua'


# --- 1. Dialog: combo template phai co muc moi -----------------------------
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QPA_FONTDIR', 'C:/Windows/Fonts')

from PySide6.QtWidgets import QApplication  # noqa: E402

import app.core.project_session as ps  # noqa: E402
from app.ui.mediatek_mre_dialog import (  # noqa: E402
    PROJECT_TEMPLATE_OPTIONS,
    MediaTekMREConfigDialog,
)

app = QApplication.instance() or QApplication([])

dialog = MediaTekMREConfigDialog()
combo = dialog.template
ids = [combo.itemData(i) for i in range(combo.count())]
labels = [combo.itemText(i) for i in range(combo.count())]

if TEMPLATE_ID not in ids:
    errors.append(f'combo template thieu {TEMPLATE_ID!r}: {ids}')
else:
    index = ids.index(TEMPLATE_ID)
    if 'Keypad Demo' not in labels[index]:
        errors.append(f'nhan combo sai: {labels[index]!r}')

if [tid for tid, _, _ in PROJECT_TEMPLATE_OPTIONS] != ids:
    errors.append('thu tu combo khong khop PROJECT_TEMPLATE_OPTIONS')
dialog.close()

# --- 2. Tao du an that trong temp dir --------------------------------------
with tempfile.TemporaryDirectory() as td:
    sandbox = Path(td)
    projects = sandbox / 'projects'
    config = sandbox / 'config'

    # Redirect: khong bao gio cham vao thu vien du an / studio.ini that.
    ps.projects_root = lambda: projects
    ps.config_dir = lambda: config

    def _ensure() -> None:
        projects.mkdir(parents=True, exist_ok=True)
        config.mkdir(parents=True, exist_ok=True)

    ps.ensure_user_dirs = _ensure

    session = ps.ProjectSession(ROOT)
    name = 'KeypadDemoE2E'
    try:
        info = session.create_project(
            name,
            metadata={
                'app_version': '9.9.9',
                'vendor': 'E2E',
                'mediatek_chipset': 'MTK6260',
                'resolution': '240x320',
                'ram_kb': 1024,
            },
            sdk_metadata={'schema': 1, 'appname': name, 'heap_kb': 1024},
            template_name=TEMPLATE_ID,
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(f'create_project that bai: {type(exc).__name__}: {exc}')
        info = None

    if info is not None:
        project = info.root
        for rel in ('project.json', 'conf.lua', 'main.lua',
                    'src/keypad.lua', 'src/engine.lua'):
            if not (project / rel).is_file():
                errors.append(f'du an tao ra thieu {rel}')

        descriptor = project / 'project.json'
        payload = json.loads(descriptor.read_text(encoding='utf-8'))
        if payload.get('name') != name:
            errors.append(f'project.json name = {payload.get("name")!r}, mong doi {name!r}')
        if payload.get('template') != TEMPLATE_ID:
            errors.append(f'project.json template = {payload.get("template")!r}')
        if payload.get('appid') == TEMPLATE_APPID:
            errors.append('appid khong duoc cap moi (van bang appid cua template)')
        if not isinstance(payload.get('appid'), int):
            errors.append(f'project.json appid khong hop le: {payload.get("appid")!r}')
        for key, value in (('app_version', '9.9.9'), ('vendor', 'E2E'),
                           ('mediatek_chipset', 'MTK6260'), ('ram_kb', 1024)):
            if payload.get(key) != value:
                errors.append(f'wizard metadata khong merge: {key}={payload.get(key)!r}')

        sdk = project / '.luas30' / 'mre_sdk.json'
        if not sdk.is_file():
            errors.append('thieu .luas30/mre_sdk.json')
        else:
            try:
                sdk_payload = json.loads(sdk.read_text(encoding='utf-8'))
            except ValueError as exc:
                errors.append(f'mre_sdk.json khong phai JSON: {exc}')
            else:
                if sdk_payload.get('appname') != name:
                    errors.append('mre_sdk.json appname khong dung')

        # --- 3. Chay harness Lua tren chinh du an vua tao ------------------
        run_harness(project, HARNESS_KEYPAD, 'Lua harness tren du an vua tao', LUA)

# --- 4. Khung basic (moi du an moi deu copy no) van chay dung --------------
run_harness(ROOT / 'templates' / 'basic', HARNESS_BASIC,
            'Lua harness templates/basic', LUA)

if errors:
    print('FAIL')
    for item in errors:
        print(' -', item)
    raise SystemExit(1)

print('PASS: combo template co muc "Keypad Demo" dung thu tu')
print('PASS: create_project(template_name="keypad-demo") tao du an that')
print('PASS: appid duoc cap moi, wizard metadata duoc merge, mre_sdk.json duoc ghi')
