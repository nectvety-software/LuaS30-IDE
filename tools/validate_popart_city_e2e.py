#!/usr/bin/env python3
"""E2E that: template PopArtCity3D -> build that -> VXPEmu that -> doc framebuffer.

Vi sao phai co script nay (khong thay duoc bang kiem tra tinh hay harness Lua):

  * `print()` cua Lua KHONG toi duoc log cua VXPEmu (runtime goi `ls30_log_info`
    -> `_vm_log_info`, ma VXPEmu chi export `vm_app_log`) nen phai DOC PIXEL.
  * Harness Lua chay tren bang `engine` gia: no khong biet font that, khong biet
    framebuffer that, va (truoc khi duoc siet) khong kiem tra kieu tham so. Loi
    "bad argument #4" vi `P.C.gold` khong ton tai da lot qua ca harness lan
    validator tinh, chi lo ra o day.
  * Anh chup man hinh tinh cho thay dong chu tran ra ngoai 240 px — harness
    khong the thay vi no uoc luong be rong font bang mot hang so.

Mau duoc doi chieu theo dung duong di that cua mau:
    RGB888 -> LS30_RGB565 (sdk/luas30/include/ls30/graphics.h) -> hien thi
Bang mau KHONG chep tay: doc thang tu `templates/PopArtCity3D/src/popart.lua`
(va `hud.lua`) de chi co MOT nguon.

Tu SKIP (exit 0) khi thieu VXPEmu / toolchain ARM / MRE SDK / man hinh that.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TEMPLATE = ROOT / "templates" / "PopArtCity3D"
PROJECT_NAME = "Pop Art City 3D"

#: Du an nem de build. ⚠️ PHAI nam trong thu muc temp cua OS, KHONG phai `build/`.
#:
#: `build/_popart_e2e` lam script chet sau ~10 lan chay: hook `[safe-delete]` cua host
#: (`cli/vendor/shim/sitecustomize.py` + `safe-delete-bulk-guard.cjs`) chan `shutil.rmtree`
#: khi NGAN SACH XOA THEO LUOT vuot `CODEBUDDY_SAFE_DELETE_BULK_THRESHOLD` (50 muc), va
#: no thoat bang `SystemExit(1)` — script chet voi exit 1 ma KHONG co thong bao nao
#: (stderr bi nuot), nen trong nhu "E2E that bai vi ly do khac".
#:
#: `_should_bypass_safe_delete()` mien hoan toan moi duong dan nam trong temp cua OS
#: => khong bao gio hoi guard. Day cung la quy uoc da co cua repo
#: (`tools/validate_project_templates_e2e.py` dung `tempfile.TemporaryDirectory()`).
PROJ = Path(tempfile.gettempdir()) / "luas30_popart_e2e"

#: Anh chup nam NGOAI `PROJ` (trong `build/`, vai tep PNG, chi ghi de chu khong bao gio
#: xoa hang loat) de `build/_rp_popart_e2e.py` doc lai duoc giua cac luot.
SHOTS = ROOT / "build" / "_popart_e2e_shots"

#: Framebuffer that cua template (conf.lua + project.json).
FB_W, FB_H = 240, 320

errors: list[str] = []
notes: list[str] = []


def check(label: str, ok: bool, detail=None) -> bool:
    if not ok:
        errors.append(label)
    extra = "" if detail is None else f"  [{detail}]"
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label}{extra}")
    return ok


def reset_scratch() -> bool:
    """Don thu muc nem truoc khi copytree.

    Bat `SystemExit` cua hook `[safe-delete]` va bao ro nguyen nhan thay vi de
    ca script chet lang le voi exit 1 (xem ghi chu o `PROJ`). Neu thu muc nem
    khong nam trong temp cua OS thi ham nay TU CHOI xoa — day la ham y: neu ai do
    doi `PROJ` ve `build/`, loi phai lo ra ngay chu khong thanh loi kho hieu.
    """
    if not PROJ.exists():
        return True
    tmp_root = Path(tempfile.gettempdir()).resolve()
    try:
        PROJ.resolve().relative_to(tmp_root)
    except ValueError:
        print(f"  [!!  ] {PROJ} khong nam trong temp cua OS ({tmp_root}).")
        print("  [!!  ] Hook [safe-delete] se chan rmtree khi so muc > nguong theo luot.")
        print("  [!!  ] Doi PROJ ve tempfile.gettempdir() thay vi build/.")
        return False
    try:
        shutil.rmtree(PROJ)
    except SystemExit:
        print("  [!!  ] Hook [safe-delete] chan xoa hang loat (ngan sach theo luot da het).")
        return False
    except OSError as exc:
        print(f"  [!!  ] khong xoa duoc {PROJ}: {exc}")
        return False
    return True


# =========================================================================== mau

def pack565(r: int, g: int, b: int) -> int:
    """`LS30_RGB565` — sdk/luas30/include/ls30/graphics.h dong 13.

    Khong phai 565 chuan: bit 1..0 cua kenh G bi bo, va 3 bit cao cua G nam o
    3 bit thap cua byte cao. Chep nguyen cong thuc, khong "sua cho dung".
    """
    return ((((r & 0xF8) + ((g & 0xE0) >> 5)) << 8) + ((g & 0x1C) << 3) + (b >> 3))


def expand565(v: int) -> tuple[int, int, int]:
    """Giai ma 565 nguoc ra 888 bang phep DICH (do duoc: 31 -> 248, khong phai 255)."""
    return (((v >> 11) & 0x1F) << 3, ((v >> 5) & 0x3F) << 2, (v & 0x1F) << 3)


def on_device(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Mau se THUC SU hien ra tren framebuffer VXPEmu."""
    return expand565(pack565(*rgb))


def parse_palette():
    """Doc bang mau tu nguon Lua, khong chep tay gia tri hex."""
    src = (TEMPLATE / "src" / "popart.lua").read_text(encoding="utf-8")

    flat = {}
    for name, r, g, b in re.findall(
            r"M\.C\.(\w+)\s*=\s*E\.color\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", src):
        flat[name] = (int(r), int(g), int(b))

    def bands(var: str):
        block = re.search(r"M\.C\." + var + r" = \{\}\s*\ndo\n(.*?)\nend", src, re.S)
        if not block:
            raise SystemExit(f"khong doc duoc M.C.{var} tu popart.lua")
        return [(int(r), int(g), int(b)) for r, g, b in re.findall(
            r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}", block.group(1))]

    builds = [(n, (int(r), int(g), int(b)))
              for n, r, g, b, _ in re.findall(
                  r'\{\s*name\s*=\s*"(\w+)"\s*,\s*r\s*=\s*(\d+)\s*,\s*g\s*=\s*(\d+)\s*,'
                  r'\s*b\s*=\s*(\d+)\s*,\s*hs\s*=\s*([\d.]+)\s*\}', src)]

    fog = re.search(r"local FOG = \{\s*(\d+),\s*(\d+),\s*(\d+)\s*\}", src)
    mix = re.search(r"local SHADE_MIX = \{([^}]*)\}", src)
    dim = re.search(r"local SHADE_DIM = \{([^}]*)\}", src)
    if not (fog and mix and dim):
        raise SystemExit("khong doc duoc FOG / SHADE_MIX / SHADE_DIM tu popart.lua")

    def nums(m):
        return [float(x) for x in m.group(1).replace(" ", "").split(",") if x]

    return {
        "flat": flat,
        "sky": bands("sky"),
        "floor": bands("floor"),
        "builds": builds,
        "fog": tuple(int(x) for x in fog.groups()),
        "mix": nums(mix),
        "dim": nums(dim),
    }


def parse_hud_palette():
    """Bang mau cua HUD (`src/hud.lua`) — thanh HP doi mau theo ti le, nen phai
    biet ca ba mau `hp_hi` / `hp_mid` / `hp_lo` chu khong chi mot."""
    src = (TEMPLATE / "src" / "hud.lua").read_text(encoding="utf-8")
    out = {}
    for name, r, g, b in re.findall(
            r"M\.C\.(\w+)\s*=\s*E\.color\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", src):
        out[name] = (int(r), int(g), int(b))
    if not {"hp_hi", "hp_mid", "hp_lo"}.issubset(out):
        raise SystemExit("khong doc duoc hp_hi/hp_mid/hp_lo tu hud.lua")
    return out


def shade_rgb(pal, rgb, level):
    """Ban chep cua `M.shade_rgb` trong popart.lua (khong co cach nao khac: harness
    Lua khong goi duoc tu Python). Kiem tra tinh dung dan o `sanity_shade`."""
    t = pal["mix"][level]
    k = (1 - t) * pal["dim"][level]
    return tuple(max(0, min(255, int(v * k + f * t + 0.5)))
                 for v, f in zip(rgb, pal["fog"]))


def sanity_shade(pal) -> None:
    """Mo hinh mau phai tai tao duoc mau DO THAT tren man hinh.

    (248,44,120) = hong nong o muc 0  — do tu anh chup tieu de.
    (176,36,104) = hong nong o muc 1  — do tu khung hinh choi (11.4% so pixel).
    Neu phep chep `shade_rgb` sai thi moi phep kiem tra phia sau deu vo nghia.
    """
    hot = pal["flat"]["hot"]
    check("M1 mo hinh mau: hot muc 0 = (248,44,120) nhu do duoc",
          on_device(shade_rgb(pal, hot, 0)) == (248, 44, 120),
          on_device(shade_rgb(pal, hot, 0)))
    check("M2 mo hinh mau: hot muc 1 = (176,36,104) nhu do duoc",
          on_device(shade_rgb(pal, hot, 1)) == (176, 36, 104),
          on_device(shade_rgb(pal, hot, 1)))
    check("M3 mo hinh mau: muc 0 phai giu nguyen mau goc",
          shade_rgb(pal, hot, 0) == hot, shade_rgb(pal, hot, 0))


# ================================================================ framebuffer

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


def raw_grab(hwnd: int, out: Path):
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


#: `PrintWindow` doi khi tra ve be mat CU (thanh tieu de Qt + ruot den) neu cua so
#: dang duoc ve lai. Do duoc that. Nen: chup lai cho toi khi khung hinh trong nhu
#: mot framebuffer that.
BLACKISH = 0.90


def frame_stats(img):
    """(so mau khac nhau, ty le den tuyet doi, co muc chu sang o tren cung khong)."""
    width, height = img.size
    px = img.load()
    seen = set()
    black = 0
    top_ink = 0
    top = max(1, int(height * 40 / FB_H))
    for y in range(height):
        for x in range(width):
            c = px[x, y]
            seen.add(c)
            if c == (0, 0, 0):
                black += 1
            elif y < top and sum(c) > 200:
                top_ink += 1
    total = width * height
    return len(seen), black / total, top_ink


def looks_like_framebuffer(img) -> bool:
    distinct, black_ratio, _ = frame_stats(img)
    return distinct >= 5 and black_ratio < BLACKISH


def looks_like_error_screen(img) -> bool:
    """Man hinh loi cua runtime: nen den tuyet doi + mot dong chu trang tren cung.

    Day cung la hinh dang cua be mat CU ma `PrintWindow` tra ve, nen phai phan
    biet bang cach chup lai vai lan (xem `grab_game`).
    """
    distinct, black_ratio, top_ink = frame_stats(img)
    return black_ratio >= BLACKISH and top_ink > 20


def grab_game(hwnd: int, name: str, tries: int = 8, settle=0.3):
    """Chup cho toi khi khung hinh trong nhu framebuffer that."""
    out = SHOTS / f"{name}.png"
    img = None
    for _ in range(tries):
        img = raw_grab(hwnd, out)
        if looks_like_framebuffer(img):
            return img
        time.sleep(settle)
    return img


# ------------------------------------------------------------------ phan tich

class Frame:
    """Khung hinh da chieu ve toa do FRAMEBUFFER (khong phai toa do cua so)."""

    def __init__(self, img):
        self.img = img
        self.w, self.h = img.size
        self.scale = self.w / FB_W
        self.px = img.load()

    def at(self, x_fb, y_fb):
        # Lam tron LEN nua: `round()` cua Python lam tron ve so chan, nen toa do
        # roi dung vao .5 (hay gap o ty le 1.25) bi lech len mot pixel — du de
        # truot mot vien den day 2 px.
        x = min(self.w - 1, max(0, int(x_fb * self.scale + 0.5)))
        y = min(self.h - 1, max(0, int(y_fb * self.scale + 0.5)))
        return self.px[x, y]

    def count_near(self, colour, tol=4, region=None):
        """So pixel (theo fb px) gan mau nay."""
        x0, y0, x1, y1 = region or (0, 0, FB_W, FB_H)
        hit = 0
        for y in range(int(y0 * self.scale), int(y1 * self.scale)):
            for x in range(int(x0 * self.scale), int(x1 * self.scale)):
                c = self.px[x, y]
                if (abs(c[0] - colour[0]) <= tol and abs(c[1] - colour[1]) <= tol
                        and abs(c[2] - colour[2]) <= tol):
                    hit += 1
        return hit / (self.scale * self.scale)

    def ink_columns(self, y0_fb, y1_fb, min_sum=200):
        """Khoang x (fb) co pixel 'chu' trong dai y — de phat hien chu tran man hinh."""
        xs = []
        for y in range(int(y0_fb * self.scale), int(y1_fb * self.scale)):
            for x in range(self.w):
                if sum(self.px[x, y]) > min_sum:
                    xs.append(x)
        if not xs:
            return None
        return min(xs) / self.scale, max(xs) / self.scale

    def diff(self, other) -> float:
        """Ty le pixel khac nhau (0..1) — dung de chung minh khung hinh DA DOI."""
        if self.img.size != other.img.size:
            return 1.0
        a, b = self.img.load(), other.img.load()
        n = 0
        for y in range(self.h):
            for x in range(self.w):
                if a[x, y] != b[x, y]:
                    n += 1
        return n / (self.w * self.h)


# ------------------------------------------------- phan loai man hinh tu pixel
#
# ⚠️ KHONG suy man hinh tu thu tu da bam phim. Da mac that: sau khi tu man hinh
# huong dan quay ve bang tam dung, con tro VAN o muc "HUONG DAN", nen bam ok lan
# nua lai vao huong dan — phep kiem tra "khac bang tam dung >= 20%" van XANH
# trong khi man hinh dang sai. Phai doc pixel moi biet dang o dau.

def classify(fr: "Frame", pal, hud) -> str:
    """Tra ve "title" / "play" / "pause" / "help" / "?" — doc tu chinh khung hinh."""
    total = FB_W * FB_H
    ca = fr.count_near(on_device(pal["flat"]["check_a"]), tol=3)
    cb = fr.count_near(on_device(pal["flat"]["check_b"]), tol=3)
    if (ca + cb) / total > 0.5:
        return "help"
    if has_hp_bar(fr, pal, hud):
        return "play"
    if fr.count_near(on_device(pal["flat"]["deep"]), tol=3) / total >= 0.15:
        return "pause"
    if fr.count_near(on_device(pal["flat"]["hot"]), tol=4) >= 3000:
        return "title"
    return "?"


#: Mau ruot hop le cua thanh HP. Thanh chi day MOT PHAN khi hp < 100 (dam tuong
#: mat HP), nen khong duoc doi hoi ruot dong nhat — da mac that: sau khi xe dam
#: tuong, hp tut con 89% va phep phan loai "?" oan cho khung hinh choi.
def hp_bar_colours(pal, hud):
    return {on_device(hud["hp_hi"]), on_device(hud["hp_mid"]), on_device(hud["hp_lo"]),
            on_device(pal["flat"]["bar_bg"])}


def has_hp_bar(fr: "Frame", pal, hud) -> bool:
    """Thanh HP: dai 72x8 o (158,260) voi vien den hai ben.

    Dung HINH DANG + vien, khong chi dung mau: mot buc tuong gan cung co the phu
    kin mot hang ngang bang MOT mau, nhung khong tao ra vien den hai ben.
    """
    ink = on_device(pal["flat"]["ink"])

    def is_ink(x, y):
        p = fr.at(x, y)
        return all(abs(p[i] - ink[i]) <= 3 for i in range(3))

    if not (is_ink(157, 263) and is_ink(230, 263)):
        return False
    inner = {fr.at(x, y) for y in (261, 263, 265) for x in range(160, 228, 4)}
    return bool(inner) and inner <= hp_bar_colours(pal, hud)


def sky_bands_present(fr: "Frame", pal, min_px: int = 400) -> int:
    """So dai troi (trong 6 dai cua bang mau) thuc su hien ra."""
    return sum(1 for c in pal["sky"] if fr.count_near(on_device(c)) > min_px)


def strong_shades(fr: "Frame", pal, min_px: int = 60):
    """Cac sac do tuong (6 loai x 4 muc) hien ra du day pixel."""
    out = []
    for name, rgb in pal["builds"]:
        for lvl in range(4):
            if fr.count_near(on_device(shade_rgb(pal, rgb, lvl))) >= min_px:
                out.append(f"{name}{lvl}")
    return out


def ink_band_count(fr: "Frame", pal, y0: int = 30, y1: int = 241) -> int:
    """So dai y co vien den cua dinh tuong — dau vet cua raycasting.

    Gioi han y de loai chip ten khu (y 6..24) va HUD (y >= 244); neu khong thi
    phep dem chi tinh luon muc chu cua HUD.
    """
    ink = on_device(pal["flat"]["ink"])
    ys = [y for y in range(y0, y1)
          if fr.count_near(ink, tol=3, region=(0, y, FB_W, y + 1)) >= 3]
    bands, prev = 0, -99
    for y in ys:
        if y - prev > 3:
            bands += 1
        prev = y
    return bands


def hp_fill_px(fr: "Frame", pal, hud) -> int:
    """So pixel ruot thanh HP dang la mau chi so (khong phai long thanh)."""
    fills = {on_device(hud["hp_hi"]), on_device(hud["hp_mid"]), on_device(hud["hp_lo"])}
    n = 0
    for y in range(260, 268):
        for x in range(158, 230):
            if fr.at(x, y) in fills:
                n += 1
    return n


# =================================================================== moi truong

def resolve_emulator():
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


def resolve_mre_sdk():
    for candidate in (os.environ.get("LUAS30_MRE_SDK"),
                      "D:/MRE/GameLib/vxp_port/sdk",
                      ROOT / "toolchain" / "mre-sdk",
                      ROOT / "vendor" / "mre-sdk"):
        if not candidate:
            continue
        root = Path(candidate)
        if (root / "include" / "vmsys.h").is_file() \
                and (root / "lib" / "MRE30" / "armgcc" / "percommon.a").is_file() \
                and (root / "scat.ld").is_file():
            return root
    return None


def load_native_window():
    path = ROOT / "studio" / "app" / "core" / "native_window.py"
    spec = importlib.util.spec_from_file_location("_ls30_native_window_popart", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


# ======================================================================= main

def main() -> int:
    emulator = resolve_emulator()
    if emulator is None:
        print("SKIP: khong thay VXPEmu.exe (dat LUAS30_EMULATOR neu nam cho khac)")
        return 0
    toolchain = ROOT / "toolchain" / "arm-gcc"
    if not (toolchain / "bin" / "arm-none-eabi-gcc.exe").is_file():
        print(f"SKIP: khong thay toolchain ARM tai {toolchain}")
        return 0
    mre_sdk = resolve_mre_sdk()
    if mre_sdk is None:
        print("SKIP: khong thay MRE SDK (include/vmsys.h + lib/MRE30/armgcc/"
              "percommon.a + scat.ld); dat LUAS30_MRE_SDK")
        return 0
    try:
        from PySide6.QtWidgets import QApplication, QWidget
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        print(f"SKIP: thieu thu vien ({exc})")
        return 0
    if os.environ.get("QT_QPA_PLATFORM", "").startswith("offscreen"):
        print("SKIP: can man hinh that cho SetParent (bo QT_QPA_PLATFORM=offscreen)")
        return 0
    if not (TEMPLATE / "main.lua").is_file():
        print(f"SKIP: khong thay template tai {TEMPLATE}")
        return 0

    pal = parse_palette()
    hud = parse_hud_palette()
    print(f"bang mau doc tu popart.lua: {len(pal['flat'])} mau phang, "
          f"{len(pal['sky'])} dai troi, {len(pal['floor'])} dai san, "
          f"{len(pal['builds'])} loai nha")
    sanity_shade(pal)

    # ---------------------------------------------------------------- build
    if not reset_scratch():
        print(f"\nFAIL: khong don duoc thu muc nem {PROJ}")
        return 1
    shutil.copytree(TEMPLATE, PROJ)
    print(f"\n[build] {PROJ}")
    result = subprocess.run(
        [sys.executable, "-u", str(ROOT / "tools" / "build.py"),
         "--project", str(PROJ), "--toolchain", str(toolchain),
         "--compat-profile", "nokia225-rm1011", "--mre-sdk", str(mre_sdk),
         "--no-run"],
        cwd=str(ROOT), capture_output=True, text=True)
    if result.returncode != 0:
        print((result.stdout or "")[-1500:])
        print((result.stderr or "")[-800:])
        print(f"\nFAIL: build that bai (exit {result.returncode})")
        return 1
    vxp = PROJ / "build" / f"{PROJECT_NAME}.vxp"
    if not check(f"build sinh ra {vxp.name}", vxp.is_file()):
        print(f"\nFAIL ({len(errors)} loi)")
        return 1

    # ---------------------------------------------------------------- chay
    nw = load_native_window()
    app = QApplication.instance() or QApplication([])

    class ScreenHost(QWidget):
        def __init__(self):
            super().__init__()
            self.setFixedSize(FB_W, FB_H)

    host = ScreenHost()
    host.show()
    host.activateWindow()
    app.processEvents()

    subprocess.run(["taskkill", "/F", "/IM", "VXPEmu.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    time.sleep(0.4)
    proc = subprocess.Popen([str(emulator), str(vxp), "--autostart", "--testapi",
                             "--screen-only"], cwd=str(emulator.parent))
    hwnd = None
    deadline = time.time() + 30
    while time.time() < deadline:
        hwnd = nw.find_main_window(proc.pid)
        if hwnd:
            break
        time.sleep(0.25)
    if not hwnd:
        proc.kill()
        print("FAIL: khong tim thay cua so VXPEmu theo PID")
        return 1

    check("nhung duoc cua so VXPEmu vao shell (SetParent)",
          nw.embed(hwnd, int(host.winId()), FB_W, FB_H))
    for _ in range(40):
        app.processEvents()
        time.sleep(0.15)
    host.activateWindow()
    for _ in range(10):
        app.processEvents()
        time.sleep(0.1)

    rect = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    cw, ch = int(rect.right - rect.left), int(rect.bottom - rect.top)
    # Do duoc: VXPEmu giu ty le 1.25 (240x320 -> 300x400) du MoveWindow xin 240x320.
    check("khung framebuffer lap kin cua so (khong bi keo meo)",
          cw / ch == FB_W / FB_H, f"{cw}x{ch}")

    def settle(n=10):
        for _ in range(n):
            app.processEvents()
            time.sleep(0.12)

    def snap(name: str, tries: int = 8) -> Frame:
        settle()
        img = grab_game(hwnd, name, tries=tries)
        if looks_like_error_screen(img):
            print(f"  [!!  ] {name}: MAN HINH LOI CUA RUNTIME (xem {SHOTS / (name + '.png')})")
            errors.append(f"{name}: runtime bao loi (man hinh den + chu trang)")
        return Frame(img)

    def key(code: int, hold_s: float = 0.0) -> None:
        nw.send_key_down(hwnd, code)
        if hold_s:
            time.sleep(hold_s)
        nw.send_key_up(hwnd, code)

    try:
        # ============================================================ A. tieu de
        print("\n== A. man hinh tieu de (boot) ==")
        title = snap("01_title")
        check("A1 khung hinh boot khong phai man hinh loi",
              not looks_like_error_screen(title.img))

        sky = sky_bands_present(title, pal)
        print("     dai troi co mat: "
              + str([(c, int(title.count_near(on_device(c)))) for c in pal["sky"]]))
        check("A2 nhin thay it nhat 4 dai troi (nen pop-art duoc ve)",
              sky >= 4, sky)

        hot_px = title.count_near(on_device(pal["flat"]["hot"]))
        check("A3 bang tieu de co vien hong nong (>= 3000 px)", hot_px >= 3000,
              int(hot_px))

        foot = title.ink_columns(296, 314)
        if foot is None:
            check("A4 dong chan trang tieu de co chu", False, "khong thay pixel chu")
        else:
            x0, x1 = foot
            print(f"     chan trang: x {x0:.1f} .. {x1:.1f} (framebuffer 0..239)")
            check("A4 dong chan trang KHONG bi cat (khong cham mep man hinh)",
                  x0 >= 2.0 and x1 <= 237.0, f"{x0:.1f}..{x1:.1f}")
        check("A5 phan loai dung man hinh tieu de", classify(title, pal, hud) == "title",
              classify(title, pal, hud))

        # ============================================================== B. choi
        print("\n== B. bam ok -> man hinh choi (3D) ==")
        key(nw.MRE_KEY_OK)
        play = snap("02_play")
        check("B1 ok dua sang man hinh choi", classify(play, pal, hud) == "play",
              classify(play, pal, hud))
        check("B2 khung hinh choi khac han tieu de (>= 20%)",
              title.diff(play) >= 0.20, f"{title.diff(play):.1%}")

        # 24 sac do nha (6 loai x 4 muc) — bang chung ca duong ong shade/fog chay.
        strong = strong_shades(play, pal)
        print(f"     sac do nha co mat: {len(strong)}/24")
        check("B3 it nhat 8 sac do tuong (tron truoc voi fog) hien ra",
              len(strong) >= 8, f"{len(strong)}/24")

        # Vien den tren dinh tuong: dau vet cua raycasting la dinh tuong CAO THAP
        # KHAC NHAU theo cot, khong phai mot duong ngang.
        bands = ink_band_count(play, pal)
        print(f"     so dai y co vien den (y 30..240): {bands}")
        check("B4 vien den cua dinh tuong nam o >= 8 do cao KHAC NHAU "
              "(dau vet raycasting)", bands >= 8, bands)

        fill = hp_fill_px(play, pal, hud)
        check("B5 HUD ve thanh HP (ruot thanh chiem >= 300 px)",
              fill >= 300, int(fill))

        # ============================================================= C. lai xe
        print("\n== C. giu up 2s -> xe chay ==")
        nw.send_key_down(hwnd, nw.MRE_KEY_UP)
        settle(20)
        nw.send_key_up(hwnd, nw.MRE_KEY_UP)
        drive = snap("03_drive")
        check("C1 van o man hinh choi", classify(drive, pal, hud) == "play",
              classify(drive, pal, hud))
        check("C2 giu up lam doi khung nhin 3D (>= 8%)", play.diff(drive) >= 0.08,
              f"{play.diff(drive):.1%}")

        print("\n== D. giu left 1.5s -> lai xe ==")
        nw.send_key_down(hwnd, nw.MRE_KEY_LEFT)
        settle(14)
        nw.send_key_up(hwnd, nw.MRE_KEY_LEFT)
        turn = snap("04_turn")
        check("D1 van o man hinh choi", classify(turn, pal, hud) == "play",
              classify(turn, pal, hud))
        check("D2 giu left lam doi khung nhin 3D (>= 8%)",
              drive.diff(turn) >= 0.08, f"{drive.diff(turn):.1%}")

        # ============================================================ E. tam dung
        print("\n== E. softleft -> tam dung ==")
        key(nw.MRE_KEY_LEFT_SOFT)
        pause = snap("05_pause")
        check("E1 softleft mo bang tam dung", classify(pause, pal, hud) == "pause",
              classify(pause, pal, hud))
        deep = pause.count_near(on_device(pal["flat"]["deep"]))
        ratio = deep / (FB_W * FB_H)
        check("E2 bang tam dung ve de len 3D (mau 'deep' >= 15% khung hinh)",
              ratio >= 0.15, f"{ratio:.1%}")
        check("E3 khong co man hinh loi khi vao tam dung",
              not looks_like_error_screen(pause.img))

        # =========================================================== F. huong dan
        print("\n== F. down + ok -> man hinh huong dan ==")
        key(nw.MRE_KEY_DOWN)                       # TIEP TUC -> HUONG DAN
        key(nw.MRE_KEY_OK)
        help_frame = snap("06_help")
        check("F1 mo duoc man hinh huong dan", classify(help_frame, pal, hud) == "help",
              classify(help_frame, pal, hud))
        check("F2 man hinh huong dan KHONG loi runtime (loi 'bad argument #4' "
              "vi P.C.gold tung lam chet man hinh nay)",
              not looks_like_error_screen(help_frame.img))

        # Phep kiem tra ma harness Lua KHONG THE lam: be rong chu that. Man hinh
        # huong dan chi co nen caro toi + chu, nen BAT KY pixel sang nao cham mep
        # man hinh deu la chu bi tran.
        edge = help_frame.ink_columns(0, FB_H, min_sum=200)
        if edge is None:
            check("F3 man hinh huong dan co chu", False, "khong thay pixel chu")
        else:
            x0, x1 = edge
            print(f"     chu huong dan: x {x0:.1f} .. {x1:.1f} (framebuffer 0..239)")
            check("F3 chu huong dan KHONG tran ra ngoai man hinh",
                  x0 >= 2.0 and x1 <= 237.0, f"{x0:.1f}..{x1:.1f}")

        # ==================================================== G. quay lai tam dung
        print("\n== G. ok -> quay lai bang tam dung ==")
        key(nw.MRE_KEY_OK)
        back = snap("07_back_to_pause")
        check("G1 ok tu huong dan quay ve dung bang tam dung",
              classify(back, pal, hud) == "pause", classify(back, pal, hud))

        # =========================================================== H. tiep tuc
        print("\n== H. up + ok (TIEP TUC) -> quay lai choi ==")
        # ⚠️ Phai bam `up`: khi quay ve bang tam dung, con tro VAN o muc "HUONG
        # DAN" (muc 2). Bam ok luon la lai vao huong dan — da mac that, va phep
        # kiem tra "khac bang tam dung" van xanh trong khi man hinh sai.
        key(nw.MRE_KEY_UP)
        key(nw.MRE_KEY_OK)
        resumed = snap("08_resume")
        check("H1 TIEP TUC quay lai man hinh choi", classify(resumed, pal, hud) == "play",
              classify(resumed, pal, hud))
        check("H2 khung hinh choi khac han bang tam dung (>= 20%)",
              pause.diff(resumed) >= 0.20, f"{pause.diff(resumed):.1%}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        host.close()

    print(f"\nanh chup: {SHOTS}")
    if errors:
        print(f"\nFAIL ({len(errors)} loi):")
        for item in errors:
            print("  -", item)
        return 1
    print("PASS: template chay that tren VXPEmu — tieu de, 3D raycast, lai xe, "
          "tam dung, huong dan; doc bang pixel framebuffer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
