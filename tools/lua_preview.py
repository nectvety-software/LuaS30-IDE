"""lua_preview.py -- chay thu Lua cua mot project LuaS30 ngay tren may tinh.

Muc dich: bat loi truoc khi build VXP va nap vao dien thoai. Script nay KHONG
thay the emulator hay may that -- no chay Lua 5.1 that (qua lupa.lua51) tren mot
ban mo phong thuan Python cua API `engine.*`, ve khung hinh ra PNG.

Nhung gi no THUC SU kiem duoc:
  * loi runtime Lua: nil arithmetic, chi so sai, string.format sai kieu...
  * bo cuc: co gi ve tran ra ngoai 240x320 khong, co de len nhau khong
  * luong ban phim: bam phim roi man hinh co doi dung khong
  * logic phu thuoc font (vi du set_font chi co 3 co that)

Nhung gi no KHONG kiem duoc:
  * so do font THAT cua firmware -- xem FONT_BUCKETS ben duoi, day la mo hinh
  * toc do, bo nho, hanh vi driver man hinh that

Dung:
    python tools/lua_preview.py --project DIR --out DIR
    python tools/lua_preview.py --project DIR --out DIR --script "down,ok,right,back"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from lupa import lua51
except ImportError:  # pragma: no cover
    print("Thieu lupa. Cai bang: pip install lupa", file=sys.stderr)
    raise SystemExit(2)

# --------------------------------------------------------------------- hang so

W, H = 240, 320

# Mo hinh 3 co chu cua runtime (engine/src/runtime_bridge.c, l_set_font):
#     n <= 8 -> SMALL, n <= 12 -> MEDIUM, n > 12 -> LARGE
# Moi co: (ten, be rong moi ky tu, chieu cao dong)
# DAY LA MO HINH, khong phai so do tu firmware that.
FONT_BUCKETS = (
    ("SMALL", 6, 8),
    ("MEDIUM", 8, 12),
    ("LARGE", 11, 16),
)

CAP_AUDIO = 0x0001
CAP_FILES = 0x0002
CAP_IMAGES = 0x0004
CAP_TOUCH = 0x0008
CAP_RENAME = 0x0010
CAP_REMOVABLE = 0x0020
CAP_LOG = 0x0040


def font_index(n: float) -> int:
    n = int(n)
    if n <= 8:
        return 0
    if n <= 12:
        return 1
    return 2


def rgb565(r: int, g: int, b: int) -> int:
    """Sao y LS30_RGB565 trong sdk/luas30/include/ls30/graphics.h."""
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return ((((r & 0xF8) + ((g & 0xE0) >> 5)) << 8)
            + ((g & 0x1C) << 3) + (b >> 3))


# --------------------------------------------------------------------- canvas

class Canvas:
    """Khung framebuffer 240x320 theo RGB565, giong lop layer cua runtime."""

    def __init__(self):
        self.w, self.h = W, H
        self.px = [0] * (W * H)          # mau packed
        self.draws = 0                   # so lenh ve -- de phat hien vong lap nong
        self.oob = []                    # lenh ve tran ra ngoai man hinh
        self.texts = []                  # (x, y, chuoi, co) -- de kiem tra

    def clear(self, c):
        self.px = [c] * (W * H)
        # Xoa ca danh sach chu: moi khung hinh ve lai tu dau (E.draw goi clear
        # truoc tien), nen chu cua khung truoc khong duoc dinh lai vao anh.
        # Neu quen buoc nay, save_png se ve chong chu cua MOI khung da qua.
        self.texts = []
        self.draws += 1

    def _track(self, x, y, w, h, kind):
        self.draws += 1
        if w <= 0 or h <= 0:
            return False
        if x < 0 or y < 0 or x + w > self.w or y + h > self.h:
            if len(self.oob) < 40:
                self.oob.append((kind, x, y, w, h))
            # runtime that bi clip_ok() chan -> khong ve. Mo phong y nguyen.
            return False
        return True

    def rect(self, x, y, w, h, c):
        x, y, w, h = int(x), int(y), int(w), int(h)
        if not self._track(x, y, w, h, "rect"):
            return
        for yy in range(y, y + h):
            base = yy * W
            for xx in range(x, x + w):
                self.px[base + xx] = c

    def frame(self, x, y, w, h, c):
        """LS30 frame: vien 1px ve BEN TRONG hinh chu nhat."""
        x, y, w, h = int(x), int(y), int(w), int(h)
        if w <= 0 or h <= 0:
            return
        self.draws += 1
        for xx in range(x, x + w):
            for yy in (y, y + h - 1):
                if 0 <= xx < W and 0 <= yy < H:
                    self.px[yy * W + xx] = c
        for yy in range(y, y + h):
            for xx in (x, x + w - 1):
                if 0 <= xx < W and 0 <= yy < H:
                    self.px[yy * W + xx] = c

    def line(self, x0, y0, x1, y1, c):
        """Bresenham, giong software_line_from_fill trong sdk/luas30/src/api.c."""
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        self.draws += 1
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            if 0 <= x0 < W and 0 <= y0 < H:
                self.px[y0 * W + x0] = c
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def text(self, x, y, s, c, fi):
        """Ghi nhan de ve sau; do rong = so ky tu * be rong co (khop text_width)."""
        x, y = int(x), int(y)
        self.draws += 1
        name, adv, _fh = FONT_BUCKETS[fi]
        if y < 0 or y >= H or x >= W:
            if len(self.oob) < 40:
                self.oob.append(("text", x, y, len(s) * adv, _fh))
        self.texts.append((x, y, s, fi, c))


# --------------------------------------------------------------------- runtime

class Sim:
    def __init__(self, project: Path, verbose: bool = True):
        self.project = Path(project)
        self.verbose = verbose
        self.canvas = Canvas()
        self.font = 0
        self.t = 0
        self.exited = False
        self.logs = []
        self.loaded = {}
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        self._install()

    # ---------------------------------------------------------- API engine
    def _install(self):
        lua = self.rt
        g = lua.globals()
        engine = lua.table()
        g.engine = engine
        g.mre = engine

        cv = self.canvas

        def _col(idx, *rest):
            """Giong lua_color(): nhan so packed, hoac bo 3 so (r,g,b)."""
            if len(rest) >= 2 and all(isinstance(v, (int, float)) for v in rest[:2]):
                return rgb565(idx, rest[0], rest[1])
            return int(idx)

        engine.color = lambda r, g, b: rgb565(r, g, b)
        engine.clear = lambda *a: cv.clear(_col(*a))
        engine.rect = lambda *a: cv.rect(a[0], a[1], a[2], a[3], _col(*a[4:]))
        engine.frame = lambda *a: cv.frame(a[0], a[1], a[2], a[3], _col(*a[4:]))
        engine.line = lambda *a: cv.line(a[0], a[1], a[2], a[3], _col(*a[4:]))

        def _text(x, y, s, *rest):
            c = _col(*rest) if rest else 0xFFFF
            cv.text(x, y, s, c, self.font)

        engine.text = _text

        def _set_font(n=8):
            self.font = font_index(n)

        engine.set_font = _set_font
        engine.text_width = lambda s: len(s) * FONT_BUCKETS[self.font][1]
        engine.font_height = lambda: FONT_BUCKETS[self.font][2]
        engine.flush = lambda: None

        engine.tick_ms = lambda: int(self.t)
        engine.log = self._log
        engine.exit = self._exit

        engine.capabilities = lambda: (CAP_AUDIO | CAP_FILES | CAP_IMAGES
                                       | CAP_RENAME | CAP_LOG)
        engine.device_info = self._device_info
        engine.runtime_compat = self._runtime_compat

        engine.W = W
        engine.H = H
        engine.version = "LuaS30 IDE/1.8.2 RuntimeCompat"
        engine.has_audio = True
        engine.has_files = True
        engine.has_images = True
        engine.has_touch = False
        engine.has_rename = True
        engine.has_removable = False
        engine.has_log = True
        engine.runtime_compatible = True

        g.print = self._log
        g.require = self._require
        g.package_loaded = lua.table()

    def _log(self, *args):
        msg = " ".join(str(a) for a in args)
        self.logs.append(msg)
        if self.verbose:
            print("    [lua] " + msg, flush=True)

    def _exit(self):
        self.exited = True

    def _device_info(self):
        return self.rt.table_from({
            "family": "nokia225-rm1011",
            "width": W, "height": H,
            "preferred_fps": 15, "recommended_ram_kb": 1024,
            "capabilities": CAP_AUDIO | CAP_FILES | CAP_IMAGES | CAP_RENAME | CAP_LOG,
            "native_capabilities": CAP_AUDIO | CAP_FILES | CAP_IMAGES,
            "fallback_mask": 0, "missing_required": 0,
            "abi_alias_count": 12,
            "compatibility": "full",
        })

    def _runtime_compat(self):
        return self.rt.table_from({
            "compatible": True, "level": "full",
            "native_capabilities": CAP_AUDIO | CAP_FILES | CAP_IMAGES,
            "capabilities": CAP_AUDIO | CAP_FILES | CAP_IMAGES | CAP_RENAME | CAP_LOG,
            "alias_count": 12, "fallback_mask": 0, "missing_required": 0,
        })

    # ---------------------------------------------------------- require
    def _require(self, mod):
        """Giong load_module_resource(): 'src.a.b' -> src/a/b.lub roi src/a/b.lua."""
        mod = str(mod)
        if mod in self.loaded:
            return self.loaded[mod]
        base = mod.replace(".", "/")
        for ext in (".lub", ".lua"):
            path = self.project / (base + ext)
            if path.is_file():
                src = path.read_text(encoding="utf-8-sig")
                chunk = self.rt.eval("function(s, n) return loadstring(s, n) end")(
                    src, base + ext)
                val = chunk()
                if val is None:
                    val = True
                self.loaded[mod] = val
                return val
        raise lua51.LuaError("module '%s' missing" % mod)

    # ---------------------------------------------------------- chay
    def run_file(self, rel: str):
        path = self.project / rel
        src = path.read_text(encoding="utf-8-sig")
        chunk = self.rt.eval("function(s, n) return loadstring(s, n) end")(src, rel)
        return chunk()

    def call(self, name: str, *args):
        fn = self.rt.globals().engine[name]
        if fn is None:
            return None
        return fn(*args)

    def frame(self, dt: float = 1 / 15.0):
        self.t += int(dt * 1000)
        self.call("update", dt)
        self.canvas.draws = 0
        self.call("draw")

    def screen_title(self) -> str:
        """Chuoi tren thanh tieu de -- text dau tien cua khung hinh hien tai.

        main.lua ve titlebar truoc khi goi screen.draw(), nen phan tu dau tien
        trong canvas.texts chinh la ten man hinh dang mo. Dung de phat hien di
        nham trong kich ban phim.
        """
        for (_x, _y, s, _fi, _c) in self.canvas.texts:
            return str(s)
        return "(khong co)"

    def key(self, name: str, hold_frames: int = 2):
        self.call("keypressed", name)
        for _ in range(hold_frames):
            self.frame()
        self.call("keyreleased", name)
        for _ in range(hold_frames):
            self.frame()

    # ---------------------------------------------------------- xuat anh
    def save_png(self, path: Path, scale: int = 1):
        """Xuat khung hinh hien tai ra PNG.

        `scale` phong to nguyen khoi (NEAREST) VA ve chu to theo dung ti le.
        Can thiet vi co SMALL cua thiet bi chi cao ~6px -- o ti le 1:1, chu so
        bi nhoe thanh vet, doc ra sai (vi du "3168" trong nhu "-4864").
        Phong to nguyen khoi giu dung bo cuc, khong lam lech vi tri.
        """
        from PIL import Image, ImageDraw, ImageFont

        scale = max(1, int(scale))
        img = Image.new("RGB", (W * scale, H * scale), (0, 0, 0))
        px = img.load()
        for y in range(H):
            base = y * W
            for x in range(W):
                v = self.canvas.px[base + x]
                r5 = (v >> 11) & 31
                g6 = (v >> 5) & 63
                b5 = v & 31
                rgb = (r5 * 255 // 31, g6 * 255 // 63, b5 * 255 // 31)
                for dy in range(scale):
                    row = (y * scale + dy) * W * scale
                    for dx in range(scale):
                        px[x * scale + dx, y * scale + dy] = rgb

        draw = ImageDraw.Draw(img)
        fonts = {}
        try:
            for i, (_n, _adv, fh) in enumerate(FONT_BUCKETS):
                fonts[i] = ImageFont.truetype("C:/Windows/Fonts/consola.ttf",
                                              max(6, fh - 2) * scale)
        except OSError:
            for i in range(len(FONT_BUCKETS)):
                fonts[i] = ImageFont.load_default()

        for (x, y, s, fi, c) in self.canvas.texts:
            r5 = (c >> 11) & 31
            g6 = (c >> 5) & 63
            b5 = c & 31
            draw.text((x * scale, y * scale), s,
                      fill=(r5 * 255 // 31, g6 * 255 // 63, b5 * 255 // 31),
                      font=fonts[fi])
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(path))


# --------------------------------------------------------------------- main

# Ten phim nhu "*" hoac "#" khong the dung lam ten file tren Windows.
SAFE_KEY_NAMES = {"*": "star", "#": "hash", "+": "plus", "?": "qmark",
                  ":": "colon", "/": "slash", "\\": "backslash",
                  '"': "quote", "<": "lt", ">": "gt", "|": "pipe"}


def safe_name(label: str) -> str:
    """Doi nhan buoc thanh ten file an toan tren moi he dieu hanh."""
    out = []
    for ch in label:
        if ch in SAFE_KEY_NAMES:
            out.append(SAFE_KEY_NAMES[ch])
        elif ch.isalnum() or ch in "-_.":
            out.append(ch)
        else:
            out.append("_")
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Chay thu Lua cua project LuaS30")
    ap.add_argument("--project", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None,
                    help="thu muc ghi PNG (bo qua = khong xuat anh)")
    ap.add_argument("--script", default="",
                    help="chuoi phim, phan cach bang dau phay: down,ok,right,back")
    ap.add_argument("--frames", type=int, default=2,
                    help="so khung hinh chay cho moi buoc (mac dinh 2)")
    ap.add_argument("--scale", type=int, default=3,
                    help="phong to anh xuat ra (mac dinh 3 -- chu 6px doc duoc)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    project = args.project.resolve()
    if not (project / "main.lua").is_file():
        print("Khong thay main.lua trong", project, file=sys.stderr)
        return 2

    sim = Sim(project, verbose=not args.quiet)
    out = args.out
    if out:
        out = out.resolve()

    print(f"== LuaS30 preview: {project.name} ==", flush=True)

    steps = [("00_boot", None)]
    if args.script:
        for i, k in enumerate(args.script.split(","), 1):
            k = k.strip()
            if k:
                steps.append((f"{i:02d}_{k}", k))

    worst_draws = 0
    for label, keyname in steps:
        if keyname is None:
            sim.run_file("conf.lua")
            sim.run_file("main.lua")
            sim.call("load")
        else:
            sim.key(keyname, args.frames)

        for _ in range(args.frames):
            sim.frame()

        worst_draws = max(worst_draws, sim.canvas.draws)
        note = ""
        if sim.canvas.oob:
            note = f"  !! {len(sim.canvas.oob)} lenh ve TRAN man hinh"
        print(f"  [{label}] man={sim.screen_title()!r} "
              f"lenh ve={sim.canvas.draws}{note}", flush=True)
        if out:
            sim.save_png(out / f"{safe_name(label)}.png", args.scale)

    # ---- tong ket ----
    print("\n== KET QUA ==")
    problems = []
    if sim.canvas.oob:
        problems.append(f"{len(sim.canvas.oob)} lenh ve tran man hinh")
        for kind, x, y, w, h in sim.canvas.oob[:8]:
            print(f"   tran: {kind} x={x} y={y} w={w} h={h}")
    if sim.exited:
        print("   ung dung da goi engine.exit() -- binh thuong neu ban bam '0'")
    if not problems:
        print("   khong phat hien loi runtime / tran bo cuc")
    if out:
        print(f"   anh: {out}")
    print(f"   lenh ve nhieu nhat 1 khung: {worst_draws}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
