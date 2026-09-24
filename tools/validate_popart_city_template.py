"""Template "Pop Art City 3D" — 3 chỗ đăng ký, kỷ luật API, và CHẠY THẬT.

Validator này canh template pop-art/pseudo-3D. Ba nhóm kiểm tra:

1. Hợp đồng đăng ký: `PROJECT_TEMPLATE_OPTIONS` (dialog) <-> `PROJECT_TEMPLATES`
   (session) <-> `templates/PopArtCity3D/`. Quên một chỗ là hỏng IM LẶNG: combo
   hiện mục chọn sai, hoặc create_project() ném "Unknown project template".

2. Kỷ luật của runtime MRE — đây là loại lỗi mà kiểm tra cú pháp không thấy:
   * Lua 5.1 (vendor/lua-5.1.5): không `//`, không `goto`, không `table.unpack`.
   * Runtime CHỈ mở base/table/string/math (engine/src/runtime_lua.c) => không
     `os`, không `io`. Dùng `os.time()` để seed random là chết ngay trên máy.
   * Không có `pixel`/`vline`/`hline` (engine/src/runtime_bridge.c) — gọi vào là
     nil, hỏng im lặng.
   * Không tự gọi `engine.flush`: runtime đã `flush_frame()` mỗi vòng
     (engine/src/runtime_lua.c).

3. CHẠY THẬT: biên dịch từng tệp bằng luac 5.1 rồi chạy tools/popart_city_check.lua
   trên stub engine. Không có Lua 5.1 thì SKIP (không FAIL) — nhưng phần tĩnh
   vẫn phải xanh.

    py -3.12 tools/validate_popart_city_template.py
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TID = "popart-city-3d"
DIRNAME = "PopArtCity3D"
TPL = ROOT / "templates" / DIRNAME

errors: list[str] = []
notes: list[str] = []


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------- 1. dang ky
def module_literal(source: str, name: str):
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    return None


dialog = read(ROOT / "studio/app/ui/mediatek_mre_dialog.py")
session = read(ROOT / "studio/app/core/project_session.py")

options = module_literal(dialog, "PROJECT_TEMPLATE_OPTIONS")
mapping = module_literal(session, "PROJECT_TEMPLATES")

if options is None:
    errors.append("khong doc duoc PROJECT_TEMPLATE_OPTIONS (mediatek_mre_dialog.py)")
if mapping is None:
    errors.append("khong doc duoc PROJECT_TEMPLATES (project_session.py)")

entry = None
if options:
    for item in options:
        if isinstance(item, tuple) and len(item) == 3 and item[0] == TID:
            entry = item
            break
    if entry is None:
        errors.append(f"dialog khong chao template {TID!r}")
    else:
        if not entry[1].strip() or not entry[2].strip():
            errors.append(f"{TID!r} co nhan/mo ta rong")
        if "3D" not in entry[1] and "3D" not in entry[2]:
            errors.append(f"{TID!r} khong noi ro day la 3D trong nhan/mo ta")

if mapping and mapping.get(TID) != DIRNAME:
    errors.append(f"PROJECT_TEMPLATES[{TID!r}] phai la {DIRNAME!r}, "
                  f"dang la {mapping.get(TID)!r}")

if not TPL.is_dir():
    errors.append(f"thieu thu muc templates/{DIRNAME}")

# ------------------------------------------------------------------ 2. tep
REQUIRED = [
    "project.json", "conf.lua", "main.lua", "README.md",
    "src/popart.lua", "src/city.lua", "src/render.lua",
    "src/hud.lua", "src/player.lua", "src/keypad.lua",
]
for rel in REQUIRED:
    if not (TPL / rel).is_file():
        errors.append(f"templates/{DIRNAME}/{rel} thieu")

# keypad.lua la HOP DONG dung chung — chep lai thi phai y nguyen ban.
canon = ROOT / "templates/keypad-demo/src/keypad.lua"
mine = TPL / "src/keypad.lua"
if canon.is_file() and mine.is_file():
    a = canon.read_bytes().replace(b"\r\n", b"\n")
    b = mine.read_bytes().replace(b"\r\n", b"\n")
    if a != b:
        errors.append("src/keypad.lua da bi sua khac ban chuan "
                      "(templates/keypad-demo/src/keypad.lua)")

# ------------------------------------------------------------- 3. project.json
appids: dict[int, str] = {}
for descriptor in sorted((ROOT / "templates").glob("*/project.json")):
    try:
        payload = json.loads(read(descriptor))
    except ValueError as exc:
        errors.append(f"{descriptor.parent.name}/project.json khong phai JSON: {exc}")
        continue
    aid = payload.get("appid")
    if aid is None:
        errors.append(f"{descriptor.parent.name}/project.json thieu appid")
        continue
    if aid in appids:
        errors.append(f"appid trung {aid}: {appids[aid]} va {descriptor.parent.name}")
    appids[aid] = descriptor.parent.name

project = json.loads(read(TPL / "project.json")) if (TPL / "project.json").is_file() else {}
if project:
    for key in ("appid", "ram_kb", "screen_width", "screen_height", "fps",
                "compat_profile", "mediatek_chipset", "app_version"):
        if key not in project:
            errors.append(f"project.json thieu khoa {key!r}")
    if project.get("ram_kb") != 1024:
        errors.append(f"ram_kb phai la 1024, dang la {project.get('ram_kb')!r}")
    if project.get("compat_profile") != "nokia225-rm1011":
        errors.append("compat_profile phai la nokia225-rm1011 (NOKIA225_PROFILE)")

conf = read(TPL / "conf.lua") if (TPL / "conf.lua").is_file() else ""
for token, why in (("screen_width = 240", "be ngang 240"),
                   ("screen_height = 320", "be cao 320"),
                   ("fps = 15", "15 FPS")):
    if token not in conf:
        errors.append(f"conf.lua thieu {why} ({token})")

# --------------------------------------------------- 4. ky luat runtime MRE
LUA_FILES = sorted(TPL.rglob("*.lua"))


def strip_lua(source: str) -> str:
    """Bo chu thich va chuoi khoi nguon Lua truoc khi quet token cam.

    Buoc nay BAT BUOC, khong phai cho dep: chinh comment giai thich "khong duoc
    dung os.time()" lai chua chuoi `os.time()`. Quet thang thi guard tu to cao
    chinh no — dung cai bay "guard liet ke token cam thi chinh no chua token do"
    da tung mac o validator khac trong repo.
    """
    out: list[str] = []
    i, n = 0, len(source)
    while i < n:
        # Chu thich: --[[ ... ]] / --[=[ ... ]=] / -- den het dong
        if source.startswith("--", i):
            m = re.match(r"--(\[=*\[)", source[i:])
            if m:
                close = "]" + "=" * (len(m.group(1)) - 2) + "]"
                j = source.find(close, i + m.end())
                i = n if j < 0 else j + len(close)
            else:
                j = source.find("\n", i)
                i = n if j < 0 else j
            out.append(" ")
            continue
        # Chuoi nhay don / nhay kep
        if source[i] in "\"'":
            quote = source[i]
            j = i + 1
            while j < n and source[j] != quote:
                if source[j] == "\\":
                    j += 1
                j += 1
            i = min(j + 1, n)
            out.append(" ")
            continue
        # Chuoi long bracket [[ ... ]] / [=[ ... ]=]
        m = re.match(r"\[=*\[", source[i:])
        if m:
            close = "]" + "=" * (len(m.group(0)) - 2) + "]"
            j = source.find(close, i + m.end())
            i = n if j < 0 else j + len(close)
            out.append(" ")
            continue
        out.append(source[i])
        i += 1
    return "".join(out)

# `os` / `io` khong duoc mo trong runtime => phai khong bao gio xuat hien.
BANNED_RUNTIME = [
    (re.compile(r"\bos\s*\."), "os.* (runtime khong mo thu vien os)"),
    (re.compile(r"\bio\s*\."), "io.* (runtime khong mo thu vien io)"),
    (re.compile(r"\bos\.time\b"), "os.time (khong co os)"),
]
# Ham khong ton tai trong bang dang ky cua runtime_bridge.c.
BANNED_API = [
    (re.compile(r"\bengine\s*\.\s*(pixel|vline|hline|set_pixel)\b"),
     "engine.pixel/vline/hline khong ton tai trong API"),
    (re.compile(r"\bE\s*\.\s*(pixel|vline|hline|set_pixel)\b"),
     "engine.pixel/vline/hline khong ton tai trong API"),
    (re.compile(r"\bengine\s*\.\s*flush\s*\("),
     "dung goi engine.flush — runtime da flush moi vong"),
    (re.compile(r"\bE\s*\.\s*flush\s*\("),
     "dung goi engine.flush — runtime da flush moi vong"),
]
# Cu phap Lua 5.2+ se khong qua duoc luac 5.1, nhung bao som thi de sua hon.
BANNED_SYNTAX = [
    # `a // b` co dau cach hai ben; `a///b` thi khong phai phep chia nguyen.
    (re.compile(r"(?<!/)//(?![/*])"), "toan tu chia nguyen // (Lua 5.2+)"),
    (re.compile(r"\bgoto\b"), "goto (Lua 5.2+)"),
    (re.compile(r"::\s*\w+\s*::"), "nhan ::label:: (Lua 5.2+)"),
    (re.compile(r"\btable\s*\.\s*unpack\b"), "table.unpack (Lua 5.2+; 5.1 la unpack)"),
    (re.compile(r"\bmath\s*\.\s*type\b"), "math.type (Lua 5.3+)"),
    (re.compile(r"\bbit32\b"), "bit32 (Lua 5.2)"),
]

for path in LUA_FILES:
    rel = path.relative_to(ROOT).as_posix()
    text = strip_lua(read(path))
    for pattern, why in BANNED_RUNTIME + BANNED_API + BANNED_SYNTAX:
        if pattern.search(text):
            errors.append(f"{rel}: dung {why}")

# ------------------------------------- 4b. ten trong bang mau PHAI co that
#
# ⚠️ Loi da mac that, va no IM LANG qua ca harness lan validator nay:
# `main.lua` goi `P.C.gold`, nhung `gold` CHI co trong `HUD.C` — `popart.lua`
# khong dinh nghia no. Lua tra ve nil, `E.text(x, y, s, nil)` di vao
# `luaL_checknumber(L, 4)` cua runtime_bridge.c => "bad argument #4" va CA MAN
# HINH HUONG DAN chet (chi lo ra khi chay VXPEmu that).
#
# Phep kiem tra duoi day bat dung lop loi do, khong can chay gi.

def defined_colour_keys(path: Path, prefix: str) -> set[str]:
    """Ten mau duoc dinh nghia trong mot module (`M.C.<ten> = ...`)."""
    if not path.is_file():
        return set()
    return set(re.findall(re.escape(prefix) + r"\.(\w+)\s*=", read(path)))


COLOUR_TABLES = {
    "P.C": (defined_colour_keys(TPL / "src" / "popart.lua", "M.C"), "src/popart.lua"),
    "HUD.C": (defined_colour_keys(TPL / "src" / "hud.lua", "M.C"), "src/hud.lua"),
}

for prefix, (keys, owner) in COLOUR_TABLES.items():
    if not keys:
        errors.append(f"khong doc duoc bang mau {prefix} tu {owner}")
        continue
    for path in LUA_FILES:
        rel = path.relative_to(ROOT).as_posix()
        text = strip_lua(read(path))
        for name in sorted(set(re.findall(re.escape(prefix) + r"\.(\w+)", text))):
            if name not in keys:
                errors.append(f"{rel}: {prefix}.{name} khong co trong {owner} "
                              f"(se la nil -> 'bad argument #N' tren may that)")

# README phai noi that ve pseudo-3D, khong tha noi "3D that".
readme = read(TPL / "README.md") if (TPL / "README.md").is_file() else ""
if readme:
    for token in ("raycast", "pseudo", "240x320"):
        if token.lower() not in readme.lower():
            errors.append(f"README thieu noi dung bat buoc: {token!r}")
    if not re.search(r"kh[oô]ng c[oó]\s+(alpha|GPU|đa gi[aá]c)", readme, re.IGNORECASE):
        errors.append("README phai noi ro gioi han that (khong alpha / khong GPU)")

# -------------------------------------------------------- 5. Lua 5.1 binaries
def find_lua(name: str) -> Path | None:
    env = os.environ.get("LUA_BIN")
    if env:
        p = Path(env)
        if p.is_file() and p.name.startswith(name):
            return p
        alt = p.with_name(name + p.suffix)
        if alt.is_file():
            return alt
    for rel in (f"build/_lua51/{name}.exe", f"tools/lua51/{name}.exe",
                f"vendor/lua-5.1.5/src/{name}.exe",
                f"build/_lua51/{name}", f"vendor/lua-5.1.5/src/{name}"):
        p = ROOT / rel
        if p.is_file():
            return p
    return None


luac = find_lua("luac")
lua = find_lua("lua")
compiled = 0
if luac is None:
    notes.append("SKIP: khong tim thay luac 5.1 — bo qua buoc bien dich")
else:
    for path in LUA_FILES:
        proc = subprocess.run([str(luac), "-p", str(path)], capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            errors.append(f"{path.relative_to(ROOT).as_posix()} khong bien dich duoc: "
                          f"{(proc.stderr or proc.stdout).strip()[:200]}")
        else:
            compiled += 1

harness_out = ""
if lua is None:
    notes.append("SKIP: khong tim thay lua 5.1 — bo qua harness chay that")
else:
    proc = subprocess.run([str(lua), str(ROOT / "tools/popart_city_check.lua")],
                          cwd=str(TPL), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=600)
    harness_out = proc.stdout + proc.stderr
    if proc.returncode != 0:
        errors.append("harness tools/popart_city_check.lua DO")
        for line in harness_out.splitlines():
            if line.startswith("FAIL"):
                errors.append("  " + line)
    elif "PASS: Pop Art City 3D" not in harness_out:
        errors.append("harness khong in ra dong PASS mong doi")

# ------------------------------------------------------------------ ket qua
if errors:
    print("FAIL")
    for item in errors:
        print(" -", item)
    raise SystemExit(1)

print(f"PASS: template {TID!r} duoc chao boi dialog va PROJECT_TEMPLATES")
print(f"PASS: templates/{DIRNAME} du {len(REQUIRED)} tep bat buoc, appid khong trung")
print("PASS: src/keypad.lua van la ban chuan cua hop dong phim")
print("PASS: conf.lua 240x320 @ 15 FPS, project.json 1024KB / nokia225-rm1011")
print("PASS: khong dung os/io, khong pixel/vline/hline, khong tu flush")
print("PASS: khong co cu phap Lua 5.2+ (//, goto, ::label::, table.unpack)")
print("PASS: moi ten trong bang mau (P.C.* / HUD.C.*) deu co that")
print(f"PASS: {compiled}/{len(LUA_FILES)} tep Lua bien dich duoc bang luac 5.1")
if lua is not None:
    checks = re.search(r"TONG: (\d+) kiem tra", harness_out)
    print(f"PASS: harness chay that — {checks.group(1) if checks else '?'} kiem tra, 0 loi")
for note in notes:
    print(note)
