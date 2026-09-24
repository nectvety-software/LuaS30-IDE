#!/usr/bin/env python3
"""E2E thật: IDE bơm phím → VXPEmu thật → Lua `engine.keypressed`/`keyreleased`.

Khác `validate_keypad_emulation.py` (kiểm tra tĩnh + widget offscreen), script này
**chạy thật**: build một dự án dò bằng toolchain ARM, mở `VXPEmu.exe` thật, nhúng
cửa sổ vào một widget 240x320 đúng như `ScreenHost` của Studio, rồi bơm phím bằng
chính `studio/app/core/native_window.py`.

Đọc kết quả bằng framebuffer, vì **`print()` của Lua không quan sát được trên
VXPEmu**: runtime gọi `ls30_log_info` → `_vm_log_info`, mà VXPEmu chỉ export
`vm_app_log` (đã kiểm bằng `grep -a _vm_log_info emulator/VXPEmu.exe`) nên lời gọi
là no-op im lặng. Dự án dò vẽ trạng thái phím thành các ô trắng ở góc trái và
script giải mã ngược từ ảnh chụp cửa sổ.

⚠️ Phải chạy ở phiên Windows có màn hình thật (không dùng QT_QPA_PLATFORM=offscreen),
vì `SetParent` cần cửa sổ thật.

Tự SKIP (exit 0) khi thiếu VXPEmu / toolchain ARM / MRE SDK.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

#: Du an do de build. ⚠️ PHAI nam trong temp cua OS, KHONG phai `build/`.
#:
#: `tools/build.py` don `<project>/build/` bang `shutil.rmtree(build, ignore_errors=True)`,
#: nhung `ignore_errors=True` **khong** nuot duoc `SystemExit` — hook `[safe-delete]` cua host
#: chan xoa hang loat khi NGAN SACH XOA THEO LUOT vuot nguong (50 muc) va `exit(2)`, shim doi
#: thanh `SystemExit(1)`. Thu muc `build/<probe>/build/` mot minh da ~62 tep > 50, nen validator
#: nay chi xanh khi tool-call duoc duyet tuong tac; chay ca suite trong MOT luot (khong the duyet)
#: thi no DO voi `build du an do that bai (exit 1)`.
#:
#: `_should_bypass_safe_delete()` mien hoan toan moi duong dan duoi temp cua OS => khong bao gio
#: hoi guard. Cung quy uoc voi `validate_project_templates_e2e.py` va `validate_popart_city_e2e.py`.
PROBE_DIR = Path(tempfile.gettempdir()) / "luas30_kp_keypad_probe"

#: Anh chup giu trong `build/` (vai tep PNG, chi ghi de) de con xem lai khi debug.
SHOT_DIR = ROOT / "build" / "_kp_keypad_probe_shots"
PROBE_NAME = "Keypad Probe"

# Tên phím Lua theo đúng thứ tự `doc/ai/Keypad.md` §0 — dùng để giải mã ô trắng
# thành tên phím.
NAMES = ["up", "down", "left", "right", "ok", "softleft", "softright",
         "clear", "back", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
         "*", "#"]
SLOT_H = 6

#: Toạ độ framebuffer của các điểm chốt và ba dải mã hoá (xem PROBE_MAIN_LUA).
CAL_DOTS = ((40, 40), (150, 40), (40, 200))
COL_HELD, COL_LAST, COL_EVENTS = 5, 21, 37

errors: list[str] = []
notes: list[str] = []


def check(label: str, ok: bool) -> None:
    if not ok:
        errors.append(label)


PROBE_MAIN_LUA = """\
-- Du an do cho validate_keypad_emulation_e2e.py — KHONG phai template phat hanh.
-- Ve trang thai phim len framebuffer vi print() khong toi duoc log cua VXPEmu.
local E = engine
local K = require("src.keypad")

local SLOT_H = 6
local last_index = 0
local events = 0

local function held_list()
    local out = {}
    for _, name in ipairs(K.NAMES) do
        if K.held[name] then out[#out + 1] = name end
    end
    if #out == 0 then return "-" end
    return table.concat(out, " ")
end

local function index_of(name)
    for i, candidate in ipairs(K.NAMES) do
        if candidate == name then return i end
    end
    return 0
end

local function draw_strip()
    local white = E.color(255, 255, 255)
    E.rect(0, 0, 44, #K.NAMES * SLOT_H, E.color(20, 24, 34))
    for i, name in ipairs(K.NAMES) do
        if K.held[name] then
            E.rect(0, (i - 1) * SLOT_H, 10, SLOT_H - 1, white)
        end
    end
    for i = 1, last_index do
        E.rect(16, (i - 1) * SLOT_H, 10, SLOT_H - 1, white)
    end
    for i = 1, math.min(events, #K.NAMES) do
        E.rect(32, (i - 1) * SLOT_H, 10, SLOT_H - 1, white)
    end
end

function E.load()
    E.set_font(8)
end

function E.update(dt)
end

function E.draw()
    E.clear(E.color(8, 10, 16))
    for _, m in ipairs({ {40, 40}, {150, 40}, {40, 200} }) do
        E.rect(m[1], m[2], 6, 6, E.color(255, 60, 60))
    end
    draw_strip()
    local y = #K.NAMES * SLOT_H + 8
    E.text(4, y, "key=" .. (last_index > 0 and K.NAMES[last_index] or "-"),
           E.color(255, 210, 70))
    E.text(4, y + 12, "held=" .. held_list(), E.color(235, 240, 250))
    E.text(4, y + 24, "n=" .. tostring(events), E.color(140, 152, 175))
end

function E.keypressed(raw)
    local k = K.press(raw)
    if not k then return end
    last_index = index_of(k)
    events = events + 1
end

function E.keyreleased(raw)
    K.release(raw)
end

function E.pause()
    K.reset()
end

function E.resume()
    K.reset()
end
"""

PROBE_CONF_LUA = """\
config = {
    name = "Keypad Probe",
    screen_width = 240,
    screen_height = 320,
    fps = 15
}
return config
"""

PROBE_PROJECT_JSON = """\
{
  "name": "Keypad Probe",
  "vendor": "LuaS30",
  "appid": 586534798,
  "ram_kb": 1024,
  "screen_width": 240,
  "screen_height": 320,
  "fps": 15,
  "runtime_target": "mre-s30plus",
  "single_vxp": true,
  "compat_profile": "nokia225-rm1011",
  "mre_api": "Audio File ProMng",
  "app_version": "1.0.0",
  "mediatek_chipset": "MTK6260",
  "mediatek_chipset_label": "MTK6260  (Nokia 220, 225)",
  "resolution": "240x320",
  "resolution_label": "240x320  (QVGA - Chuẩn Nokia)",
  "project_wizard": "mediatek-mre-sdk-v1"
}
"""


# --------------------------------------------------------------- môi trường

def resolve_emulator() -> Path | None:
    for candidate in (os.environ.get("LUAS30_EMULATOR"),
                      ROOT / "emulator" / "VXPEmu.exe",
                      ROOT / "toolchain" / "emulator" / "VXPEmu.exe"):
        if not candidate:
            continue
        path = Path(candidate)
        if path.is_dir():
            path = path / "VXPEmu.exe"
        if path.is_file():
            return path
    return None


def resolve_mre_sdk() -> Path | None:
    """MRE SDK thật (include/vmsys.h + lib/MRE30/armgcc/percommon.a + scat.ld)."""
    candidates = [os.environ.get("LUAS30_MRE_SDK"),
                  "D:/MRE/GameLib/vxp_port/sdk",
                  ROOT / "toolchain" / "mre-sdk",
                  ROOT / "vendor" / "mre-sdk"]
    for candidate in candidates:
        if not candidate:
            continue
        root = Path(candidate)
        if not (root / "include" / "vmsys.h").is_file():
            continue
        if not (root / "lib" / "MRE30" / "armgcc" / "percommon.a").is_file():
            continue
        if not (root / "scat.ld").is_file():
            continue
        return root
    return None


# ------------------------------------------------------------- framebuffer

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
PW_RENDERFULLCONTENT = 0x00000002
SRCCOPY = 0x00CC0020
BI_RGB = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
        ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wt.DWORD * 3)]


def grab(hwnd: int, out: Path):
    from PIL import Image
    rect = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    width = int(rect.right - rect.left)
    height = int(rect.bottom - rect.top)
    hdc = user32.GetDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, width, height)
    gdi32.SelectObject(mem, bmp)
    if not user32.PrintWindow(hwnd, mem, PW_RENDERFULLCONTENT):
        gdi32.BitBlt(mem, 0, 0, width, height, hdc, 0, 0, SRCCOPY)
    info = BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    info.bmiHeader.biWidth = width
    info.bmiHeader.biHeight = -height
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = BI_RGB
    buf = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(mem, bmp, 0, height, buf, ctypes.byref(info), 0)
    img = Image.frombuffer("RGBA", (width, height), buf, "raw", "BGRA", 0, 1).convert("RGB")
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return img


def _safe_name(label: str) -> str:
    """Tên tệp ảnh hợp lệ trên Windows (`*`, `#`, `:`... đều bị cấm)."""
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in label)


def _blobs(img, pred, min_px: int = 12):
    width, height = img.size
    px = img.load()
    seen = bytearray(width * height)
    found = []
    for y0 in range(height):
        for x0 in range(width):
            if seen[y0 * width + x0] or not pred(*px[x0, y0]):
                continue
            stack = [(x0, y0)]
            pts = []
            while stack:
                cx, cy = stack.pop()
                if cx < 0 or cy < 0 or cx >= width or cy >= height:
                    continue
                if seen[cy * width + cx] or not pred(*px[cx, cy]):
                    continue
                seen[cy * width + cx] = 1
                pts.append((cx, cy))
                stack += [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]
            if len(pts) >= min_px:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                found.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
    return found


def _is_red(r, g, b) -> bool:
    return r > 150 and g < 120 and b < 120


def calibrate(img):
    """Giải phép biến đổi framebuffer → cửa sổ từ 3 điểm chốt.

    VXPEmu vẽ framebuffer 240x320 vào cửa sổ có scale ≠ 1 (đo được 1.25 kèm lệch),
    nên toạ độ không dùng trực tiếp được — phải suy ra từ điểm chốt.
    """
    dots = _blobs(img, _is_red)
    if len(dots) != 3:
        return None
    top = sorted(dots, key=lambda p: p[1])[:2]
    origin, right = sorted(top, key=lambda p: p[0])
    down = max(dots, key=lambda p: p[1])
    sx = (right[0] - origin[0]) / (CAL_DOTS[1][0] + 2.5 - (CAL_DOTS[0][0] + 2.5))
    sy = (down[1] - origin[1]) / (CAL_DOTS[2][1] + 2.5 - (CAL_DOTS[0][1] + 2.5))
    ox = origin[0] - (CAL_DOTS[0][0] + 2.5) * sx
    oy = origin[1] - (CAL_DOTS[0][1] + 2.5) * sy
    return sx, sy, ox, oy


def decode(img, cal) -> tuple[set[str], str, int]:
    """Trả về (tập phím đang giữ, tên phím vừa nhận hoặc '-', số sự kiện)."""
    sx, sy, ox, oy = cal
    px = img.load()
    width, height = img.size

    def white_at(fx: float, fy: float) -> bool:
        x, y = int(round(ox + fx * sx)), int(round(oy + fy * sy))
        if not (0 <= x < width and 0 <= y < height):
            return False
        r, g, b = px[x, y]
        return r > 180 and g > 180 and b > 180

    def count(column: int) -> int:
        total = 0
        for i in range(len(NAMES)):
            if white_at(column, i * SLOT_H + 2.5):
                total = i + 1
            else:
                break
        return total

    held = {name for i, name in enumerate(NAMES) if white_at(COL_HELD, i * SLOT_H + 2.5)}
    last = count(COL_LAST)
    events = count(COL_EVENTS)
    return held, (NAMES[last - 1] if last else "-"), events


# ------------------------------------------------------------------ dự án dò

def write_probe() -> bool:
    keypad = ROOT / "templates" / "keypad-demo" / "src" / "keypad.lua"
    if not keypad.is_file():
        notes.append(f"SKIP: không thấy {keypad} (dùng làm module keypad thật)")
        return False
    (PROBE_DIR / "src").mkdir(parents=True, exist_ok=True)
    (PROBE_DIR / "main.lua").write_text(PROBE_MAIN_LUA, encoding="utf-8")
    (PROBE_DIR / "conf.lua").write_text(PROBE_CONF_LUA, encoding="utf-8")
    (PROBE_DIR / "project.json").write_text(PROBE_PROJECT_JSON, encoding="utf-8")
    shutil.copy2(keypad, PROBE_DIR / "src" / "keypad.lua")
    return True


def build_probe(mre_sdk: Path) -> Path | None:
    command = [sys.executable, "-u", str(ROOT / "tools" / "build.py"),
               "--project", str(PROBE_DIR),
               "--toolchain", str(ROOT / "toolchain" / "arm-gcc"),
               "--compat-profile", "nokia225-rm1011",
               "--mre-sdk", str(mre_sdk),
               "--no-run"]
    result = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True)
    if result.returncode != 0:
        errors.append(f"build dự án dò thất bại (exit {result.returncode})")
        print((result.stdout or "")[-1500:])
        print((result.stderr or "")[-800:])
        return None
    vxp = PROBE_DIR / "build" / f"{PROBE_NAME}.vxp"
    check(f"build không sinh ra {vxp.name}", vxp.is_file())
    return vxp if vxp.is_file() else None


def load_native_window():
    path = ROOT / "studio" / "app" / "core" / "native_window.py"
    spec = importlib.util.spec_from_file_location("_ls30_native_window_e2e", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------- main

def main() -> int:
    emulator = resolve_emulator()
    if emulator is None:
        print("SKIP: không thấy VXPEmu.exe (đặt LUAS30_EMULATOR nếu nằm chỗ khác)")
        return 0
    toolchain = ROOT / "toolchain" / "arm-gcc"
    if not (toolchain / "bin" / "arm-none-eabi-gcc.exe").is_file():
        print(f"SKIP: không thấy toolchain ARM tại {toolchain}")
        return 0
    mre_sdk = resolve_mre_sdk()
    if mre_sdk is None:
        print("SKIP: không thấy MRE SDK (include/vmsys.h + lib/MRE30/armgcc/percommon.a "
              "+ scat.ld); đặt LUAS30_MRE_SDK")
        return 0

    try:
        from PySide6.QtWidgets import QApplication, QWidget
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        print(f"SKIP: thiếu thư viện ({exc})")
        return 0

    if os.environ.get("QT_QPA_PLATFORM", "").startswith("offscreen"):
        print("SKIP: cần màn hình thật cho SetParent (bỏ QT_QPA_PLATFORM=offscreen)")
        return 0

    if not write_probe():
        print("\n".join(notes))
        return 0

    print(f"đã dùng VXPEmu: {emulator}")
    print(f"đã dùng MRE SDK: {mre_sdk}")
    vxp = build_probe(mre_sdk)
    if vxp is None:
        print(f"\nFAIL ({len(errors)} lỗi):")
        for item in errors:
            print("  -", item)
        return 1

    nw = load_native_window()
    app = QApplication.instance() or QApplication([])

    class ScreenHost(QWidget):
        def __init__(self):
            super().__init__()
            self.setFixedSize(240, 320)

    host = ScreenHost()
    host.show()
    host.activateWindow()
    app.processEvents()

    subprocess.run(["taskkill", "/F", "/IM", "VXPEmu.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    time.sleep(0.4)
    proc = subprocess.Popen(
        [str(emulator), str(vxp), "--autostart", "--testapi", "--screen-only"],
        cwd=str(emulator.parent),
    )

    hwnd = None
    deadline = time.time() + 30
    while time.time() < deadline:
        hwnd = nw.find_main_window(proc.pid)
        if hwnd:
            break
        time.sleep(0.25)
    if not hwnd:
        proc.kill()
        print("FAIL: không tìm thấy cửa sổ VXPEmu theo PID")
        return 1

    check("SetParent (nhúng VXPEmu vào shell) thất bại",
          nw.embed(hwnd, int(host.winId()), 240, 320))
    for _ in range(40):
        app.processEvents()
        time.sleep(0.15)
    host.activateWindow()
    for _ in range(8):
        app.processEvents()
        time.sleep(0.1)

    state = {"events": 0}
    step = 0

    def snap(label: str, want_held: set[str], want_last: str, *, delta: int | None = None):
        nonlocal step
        step += 1
        for _ in range(8):
            app.processEvents()
            time.sleep(0.1)
        img = grab(hwnd, SHOT_DIR / f"{step:02d}_{_safe_name(label)}.png")
        cal = calibrate(img)
        if cal is None:
            check(f"{label}: không tìm đủ 3 điểm chốt để giải mã framebuffer", False)
            return
        held, last, events = decode(img, cal)
        ok = (held == want_held) and (last == want_last)
        grew = ""
        if delta is not None and events - state["events"] != delta:
            ok = False
            grew = f" [số sự kiện tăng {events - state['events']}, phải là {delta}]"
        state["events"] = events
        print(f"  [{'OK  ' if ok else 'FAIL'}] {label:26s} held={sorted(held)} "
              f"last={last} n={events}{grew}")
        check(f"{label}: held={sorted(held)} last={last!r} (phải là "
              f"held={sorted(want_held)} last={want_last!r})", ok)

    def tap(label: str, code: int, want_held: set[str], want_last: str,
            *, delta: int = 1) -> None:
        nw.send_key_down(hwnd, code)
        nw.send_key_up(hwnd, code)
        snap(label, want_held, want_last, delta=delta)

    def hold(label: str, codes: list[int], want_held: set[str], want_last: str) -> None:
        for code in codes:
            nw.send_key_down(hwnd, code)
        snap(label, want_held, want_last, delta=len(codes))
        for code in reversed(codes):
            nw.send_key_up(hwnd, code)
        snap(label + " (nhả)", set(), want_last, delta=0)

    try:
        snap("boot", set(), "-")
        hold("giữ up", [nw.MRE_KEY_UP], {"up"}, "up")
        hold("giữ down+left", [nw.MRE_KEY_DOWN, nw.MRE_KEY_LEFT],
             {"down", "left"}, "left")
        tap("ok", nw.MRE_KEY_OK, set(), "ok")
        tap("softleft", nw.MRE_KEY_LEFT_SOFT, set(), "softleft")
        tap("softright", nw.MRE_KEY_RIGHT_SOFT, set(), "softright")
        tap("back", nw.MRE_KEY_BACK, set(), "back")
        tap("clear", nw.MRE_KEY_CLEAR, set(), "clear")
        tap("phím 7", 0x37, set(), "7")
        tap("phím *", 0x2A, set(), "*")
        tap("phím 2 (dự phòng D-Pad)", 0x32, set(), "2")
        # `#` KHÔNG gửi được qua cửa sổ: Qt chỉ ra Qt::Key_NumberSign khi Shift
        # THẬT đang giữ, còn gửi VK_SHIFT thì VXPEmu hiểu thành phím mềm phải.
        # Đúng phải là KHÔNG có sự kiện nào và `last` giữ nguyên (không được
        # thành '3', cũng không được sinh thêm 'softright').
        tap("phím # (không gửi được)", 0x23, set(), "2", delta=0)
        tap("phím 0", 0x30, set(), "0")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        host.close()

    print()
    if errors:
        print(f"FAIL ({len(errors)} lỗi):")
        for item in errors:
            print("  -", item)
        return 1
    print("PASS: nhúng VXPEmu thật + bơm phím chạy đúng hết (đọc từ framebuffer)")
    print("      giữ phím → engine.keypressed/keyreleased, tên chữ thường, "
          "nhả ngoài nút cũng nhả")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
