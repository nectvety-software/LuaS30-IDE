# Chay VXP tren VXPEmu, guim phim qua PostMessage, chan PrintWindow tung buoc.
# Dung: python emu_test.py <file.vxp> <out_prefix> [script]
# script: cu phap "key[:hold_sec][,key[:hold_sec]...]"; key la 0-9/*/#
import subprocess, sys, time, ctypes
from ctypes import wintypes
from PIL import Image

u = ctypes.windll.user32
g = ctypes.windll.gdi32
# Windows scale 125%: if this process is DPI-unaware, GetClientRect returns
# virtualized 240x320 and PrintWindow clips the physical 300x400 window to
# its top-left -> bottom 64 logical rows vanish. Become DPI-aware first.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    u.SetProcessDPIAware()

EMU_DIR = r"D:\MRE\LuaS30-IDE\emulator"
VK = {str(d): 0x60 + d for d in range(10)}
VK["*"] = 0x6A
VK["#"] = 0x6B

WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101


class RECT(ctypes.Structure):
    _fields_ = [("l", wintypes.LONG), ("t", wintypes.LONG),
                ("r", wintypes.LONG), ("b", wintypes.LONG)]


def find_window(pid):
    h = u.FindWindowW("VXPEmu Screen - VXPEmu", None)
    if h:
        return h
    # Qt build: top-level window of our process, e.g. class Qt670QWindowIcon
    found = []
    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(hw, l):
        p = wintypes.DWORD()
        u.GetWindowThreadProcessId(hw, ctypes.byref(p))
        if p.value == pid and u.IsWindowVisible(hw):
            cls = ctypes.create_unicode_buffer(256)
            u.GetClassNameW(hw, cls, 256)
            if cls.value.startswith("Qt"):
                found.append(hw)
        return True

    u.EnumWindows(EnumProc(cb), 0)
    return found[0] if found else None


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


def capture(hwnd, path):
    r = RECT()
    u.GetClientRect(hwnd, ctypes.byref(r))
    w, h = r.r - r.l, r.b - r.t
    hwnd_win = u.GetParent(hwnd) or hwnd
    screen_dc = u.GetDC(hwnd_win)
    mem = g.CreateCompatibleDC(screen_dc)
    bmp = g.CreateCompatibleBitmap(screen_dc, w, h)
    old = g.SelectObject(mem, bmp)
    u.PrintWindow(hwnd_win, mem, 2)
    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(bmi)
    bmi.biWidth, bmi.biHeight = w, -h
    bmi.biPlanes, bmi.biBitCount, bmi.biCompression = 1, 32, 0
    buf = ctypes.create_string_buffer(w * h * 4)
    g.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bmi), 0)
    img = Image.frombytes("RGB", (w, h), buf.raw, "raw", "BGRX")
    img.save(path)
    g.SelectObject(mem, old)
    g.DeleteObject(bmp)
    g.DeleteDC(mem)
    u.ReleaseDC(hwnd_win, screen_dc)


def send(hwnd, key, hold=0.35):
    vk = VK[key]
    u.PostMessageW(hwnd, WM_KEYDOWN, vk, 1)
    time.sleep(hold)
    u.PostMessageW(hwnd, WM_KEYUP, vk, 0xC0000001)
    time.sleep(0.15)


def main():
    vxp, prefix = sys.argv[1], sys.argv[2]
    script = sys.argv[3] if len(sys.argv) > 3 else "5,5,5"
    proc = subprocess.Popen([EMU_DIR + r"\VXPEmu.exe", vxp,
                             "--autostart", "--screen-only"], cwd=EMU_DIR)
    hwnd = None
    for _ in range(60):
        hwnd = find_window(proc.pid)
        if hwnd:
            break
        time.sleep(0.5)
    if not hwnd:
        print("ERROR: VXPEmu window not found")
        return 1
    time.sleep(3.0)
    capture(hwnd, prefix + "_boot.png")
    print("captured boot")
    i = 0
    for step in script.split(","):
        key, _, hold = step.partition(":")
        i += 1
        send(hwnd, key.strip(), float(hold or 0.35))
        capture(hwnd, f"{prefix}_{i:02d}_{key.strip()}.png")
        print("captured", key.strip())
    time.sleep(0.5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
