from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

COMPAT_PROFILE_IDS = (
    "auto",
    "standalone",
    "s30plus-native",
    "nokia225-rm1011",
)

S30PLUS_GCC_DEFINES = (
    "-D_MINIGUI_LIB_",
    "-D_USE_MINIGUIENTRY",
    "-D_NOUNIX_",
    "-D_FOR_WNC",
    "-D__MRE_SDK__",
    "-D__MRE_VENUS_NORMAL__",
    "-D__MMI_MAINLCD_240X320__",
    "-DMRE",
    "-DGCC",
    "-D__MRE_COMPILER_GCC__",
    "-DLUAS30_ENGINE",
    "-DLUAS30_NATIVE_SDK",
    "-DLUAS30_S30PLUS_COMPAT",
)

NOKIA225_PROFILE = {
    "id": "nokia225-rm1011",
    "model": "Nokia 225 Dual SIM",
    "rm": "RM-1011",
    "platform": "Series 30+ / MediaTek MRE",
    "screen_width": 240,
    "screen_height": 320,
    "preferred_ram_kb": 1024,
    "preferred_fps": 15,
    "api": "Audio File ProMng",
    "requires_imsi_for_typical_retail_install": True,
}


@dataclass(frozen=True)
class MRESDKLayout:
    root: Path
    include_dir: Path
    lib_dir: Path
    scat_ld: Path
    libraries: tuple[Path, ...]
    percommon: Path
    evidence: str


def _walk_find(root: Path, name: str, max_depth: int = 7) -> Path | None:
    root = Path(root).expanduser().resolve()
    wanted = name.lower()
    root_depth = len(root.parts)
    for base, dirs, files in os.walk(root):
        depth = len(Path(base).parts) - root_depth
        if depth >= max_depth:
            dirs[:] = []
        for item in files:
            if item.lower() == wanted:
                return (Path(base)/item).resolve()
    return None


def _find_include_dir(root: Path) -> Path | None:
    candidates = [
        root/"include",
        root/"Include",
        root/"MRE_SDK"/"include",
    ]
    for candidate in candidates:
        if (candidate/"vmsys.h").is_file():
            return candidate.resolve()
    found = _walk_find(root, "vmsys.h")
    return found.parent if found else None


def _find_lib_dir(root: Path) -> Path | None:
    candidates = [
        root/"lib"/"MRE30"/"armgcc",
        root/"lib",
        root/"Lib"/"MRE30"/"armgcc",
        root/"Lib",
    ]
    for candidate in candidates:
        if (candidate/"percommon.a").is_file():
            return candidate.resolve()
    found = _walk_find(root, "percommon.a")
    return found.parent if found else None


def _find_scat(root: Path, lib_dir: Path | None) -> Path | None:
    candidates = [
        root/"scat.ld",
        root/"common"/"scat.ld",
        root/"lib"/"scat.ld",
        root/"lib"/"MRE30"/"armgcc"/"scat.ld",
        lib_dir/"scat.ld" if lib_dir else None,
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate.resolve()
    return _walk_find(root, "scat.ld")


def _layout_at(root: Path | str) -> MRESDKLayout | None:
    """Doc mot thu muc va tra ve layout MRE SDK neu no dung chuan."""
    base = Path(root).expanduser()
    try:
        base = base.resolve()
    except OSError:
        return None
    if not base.is_dir():
        return None

    include_dir = _find_include_dir(base)
    lib_dir = _find_lib_dir(base)
    scat = _find_scat(base, lib_dir)
    if not include_dir or not lib_dir or not scat:
        return None

    percommon = lib_dir/"percommon.a"
    if not percommon.is_file():
        return None

    libs = tuple(sorted(lib_dir.glob("*.a"), key=lambda p: p.name.lower()))
    if not libs:
        return None

    return MRESDKLayout(
        root=base,
        include_dir=include_dir,
        lib_dir=lib_dir,
        scat_ld=scat,
        libraries=libs,
        percommon=percommon,
        evidence="MRE SDK include + ARM GCC static libraries + scat.ld",
    )


# --------------------------------------------------------------------- tim SDK
#
# LuaS30 khong phan phoi lai MRE SDK (xem doc/platform/S30PLUS_HIGH_COMPAT_1_12_0.md):
# nguoi dung phai tu chi vao ban cai cua minh. Truoc day CHI co --mre-sdk va bien
# MRE_SDK duoc doc, nen ai da cau hinh trong Studio roi ma chay build.py / build.bat
# tu dong lenh van bao thieu SDK -- GUI thi truyen --mre-sdk con CLI thi khong.
# Nay CLI doc dung cung nguon Studio ghi ra, cong them vai vi tri quy uoc.

IMPORT_SOURCE_MARKER = ".import-source"


def _engine_root() -> Path:
    return Path(__file__).resolve().parent.parent


def studio_session_paths() -> list[Path]:
    """Cac duong dan `workspace_session.json` co the co cua LuaS30 Studio.

    Phai khop studio/app/core/paths.py (`app_data_root()` + `config_dir()`).
    tools/ khong duoc import studio/ -- build phai chay doc lap, khong co PySide6
    -- nen chep lai dung logic do thay vi goi sang. Sua paths.py thi sua ca day.

    Ten moi `LuaS30IDE` xet truoc, roi den ten cu `LuaS30Engine`: build co the
    chay khi Studio chua kip doi ten (paths.py chi doi ten luc khoi dong), va o
    day CO Y khong tu doi ten -- tools/ khong duoc dung vao du lieu nguoi dung.
    """
    bases: list[Path] = []
    override = os.environ.get("LUAS30_APPDATA")
    if override:
        bases.append(Path(override).expanduser())
    else:
        if os.name == "nt":
            for key in ("APPDATA", "LOCALAPPDATA"):
                value = os.environ.get(key)
                if value:
                    bases.append(Path(value))
        xdg = os.environ.get("XDG_CONFIG_HOME")
        bases.append(Path(xdg) if xdg else Path.home()/".config")

    roots: list[Path] = []
    for base in bases:
        for folder in ("LuaS30IDE", "LuaS30Engine"):
            candidate = base/folder
            if candidate not in roots:
                roots.append(candidate)
    return [root/"config"/"workspace_session.json" for root in roots]


def studio_mre_sdk_root() -> Path | None:
    """Gia tri `build.mre_sdk_root` ma Studio luu lai (Settings > MRE SDK)."""
    for path in studio_session_paths():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        build = data.get("build") if isinstance(data, dict) else None
        value = build.get("mre_sdk_root") if isinstance(build, dict) else None
        if value:
            return Path(str(value)).expanduser()
    return None


def toolchain_import_source(toolchain: Path | str | None) -> Path | None:
    """Thu muc toolchain duoc copy tu do (xem toolchain/import_from_old_engine.bat).

    Toolchain va MRE SDK nam canh nhau trong mot ban dump engine
    (`mre-core/gcc` va `mre-core/sdk`), nen biet nguon copy la suy ra duoc SDK.
    """
    if not toolchain:
        return None
    toolchain = Path(toolchain)
    for base in (toolchain, toolchain.parent):
        try:
            text = (base/IMPORT_SOURCE_MARKER).read_text(encoding="utf-8-sig").strip()
        except OSError:
            continue
        if text:
            return Path(text).expanduser()
    return None


def mre_sdk_candidates(*, toolchain: Path | str | None = None) -> list[tuple[str, Path]]:
    """Noi se tim MRE SDK, theo thu tu uu tien. Tra ve (nhan, duong dan).

    Dung cho ca viec do lan viec bao loi: nguoi dung can biet da tim o dau.
    """
    engine = _engine_root()
    items: list[tuple[str, Path]] = []

    env = os.environ.get("MRE_SDK", "").strip()
    if env:
        items.append(("MRE_SDK environment variable", Path(env).expanduser()))

    studio = studio_mre_sdk_root()
    if studio:
        items.append(("LuaS30 Studio setting (Settings > MRE SDK)", studio))

    for label, path in (
        ("engine drop-in toolchain/mre-sdk", engine/"toolchain"/"mre-sdk"),
        ("engine drop-in vendor/mre-sdk", engine/"vendor"/"mre-sdk"),
        ("engine drop-in mre-sdk", engine/"mre-sdk"),
    ):
        items.append((label, path))

    if toolchain:
        toolchain = Path(toolchain)
        items.append(("next to toolchain", toolchain/"mre-sdk"))
        items.append(("next to toolchain", toolchain.parent/"mre-sdk"))

    source = toolchain_import_source(toolchain)
    if source:
        items.append(("next to toolchain import source", source.parent/"sdk"))
        items.append(("next to toolchain import source", source.parent/"mre-sdk"))
        items.append(("next to toolchain import source", source/"sdk"))

    seen: set[str] = set()
    unique: list[tuple[str, Path]] = []
    for label, path in items:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append((label, path))
    return unique


def discover_mre_sdk(*, toolchain: Path | str | None = None) -> MRESDKLayout | None:
    for _label, path in mre_sdk_candidates(toolchain=toolchain):
        layout = _layout_at(path)
        if layout:
            return layout
    return None


def mre_sdk_search_report(
    *,
    toolchain: Path | str | None = None,
    explicit: Path | str | None = None,
) -> str:
    """Bang ke noi da tim, de nhet vao thong bao loi khi khong thay SDK."""
    lines: list[str] = []
    if explicit:
        # Nguoi dung go --mre-sdk bang tay: neu no sai thi phai noi ro, khong
        # duoc lang le liet ke cac vi tri khac roi bo quen duong dan ho da go.
        lines.append(f"  - [missing] --mre-sdk (as passed): {Path(explicit)}")
    for label, path in mre_sdk_candidates(toolchain=toolchain):
        mark = "found" if path.is_dir() else "missing"
        lines.append(f"  - [{mark}] {label}: {path}")
    return "\n".join(lines)


def detect_mre_sdk(
    root: Path | str | None = None,
    *,
    toolchain: Path | str | None = None,
) -> MRESDKLayout | None:
    """root != None: chi kiem tra dung thu muc do. root rong: tu di tim."""
    if root:
        return _layout_at(root)
    return discover_mre_sdk(toolchain=toolchain)


def resolve_compat_profile(
    requested: str,
    *,
    compiler_profile: str,
    mre_sdk: MRESDKLayout | None,
    mre_sdk_search: str = "",
) -> str:
    requested = str(requested or "auto").lower()
    if requested not in COMPAT_PROFILE_IDS:
        raise ValueError(f"Unknown S30+ compatibility profile: {requested}")

    if requested == "standalone":
        return requested

    if requested in {"s30plus-native", "nokia225-rm1011"}:
        if compiler_profile != "gcc":
            raise RuntimeError(
                f"{requested} currently requires the ARM GCC compiler profile."
            )
        if not mre_sdk:
            detail = mre_sdk_search or "  (no search locations were configured)"
            raise RuntimeError(
                f"{requested} requires an MRE SDK root containing include/vmsys.h, "
                "percommon.a (normally lib/MRE30/armgcc) and scat.ld.\n"
                f"Searched:\n{detail}\n"
                "Fix any one of these, then rebuild:\n"
                "  --mre-sdk PATH            pass it explicitly\n"
                "  MRE_SDK=PATH              set the environment variable\n"
                "  Settings > MRE SDK        point LuaS30 Studio at your SDK\n"
                "  toolchain/mre-sdk         drop the SDK next to the engine"
            )
        return requested

    # auto: prefer the native MRE SDK path for GCC when available. This mirrors
    # known working S30+/MRE projects more closely than a pure symbol-resolver build.
    if compiler_profile == "gcc" and mre_sdk:
        return "s30plus-native"
    return "standalone"


def native_compile_flags() -> list[str]:
    return [
        "-c",
        "-fpic",
        "-march=armv5te",
        "-mfloat-abi=soft",
        "-mlittle-endian",
        "-Os",
        "-fvisibility=hidden",
        "-fdata-sections",
        "-ffunction-sections",
        "-fno-strict-aliasing",
        "-std=gnu99",
        *S30PLUS_GCC_DEFINES,
    ]


def native_link_flags(sdk: MRESDKLayout) -> list[str]:
    # Keep close to current working community MRE GCC recipes:
    # PIC/PIE, pcc struct return, section GC, SDK scatter script and SDK libs.
    #
    # -nostartfiles: toolchain arm-none-eabi di kem KHONG co crti.o/crtn.o, nen
    # danh sach startfile mac dinh cua GCC that bai ngay ("cannot find crti.o").
    # Profil standalone (toolchain_profiles.py) da dung co nay tu truoc; thieu no
    # o nhanh native khien moi lan build nokia225-rm1011 deu dut o buoc link.
    # scat.ld cua SDK tu lo phan khoi tao, nen bo startfile la dung.
    return [
        "-nostartfiles",
        "-fpic",
        "-fpcc-struct-return",
        "-pie",
        "-Wl,--gc-sections",
        "-Wl,--strip-debug",
        "-Wl,--no-warn-rwx-segment",
        "-T", str(sdk.scat_ld),
    ]


def cxx_library_search_args(toolchain_root: Path | str | None) -> list[str]:
    """Thu muc tim libstdc++ cho toolchain arm-none-eabi.

    Toolchain nay dat thu vien C++ trong thu muc multilib
    (`arm-none-eabi/lib/arm/v5te/softfp/`) chu KHONG phai `arm-none-eabi/lib/`
    goc -- va GCC bao multi-directory la `.` -- nen linker khong bao gio tim
    thay `-lstdc++` neu chi dua vao duong dan mac dinh.

    Thu tu -L rat quan trong: cac thu muc -L luon duoc tim TRUOC thu muc mac dinh
    cua GCC. Vi vay phai liet ke thu muc `lib/` goc (ban soft, dung voi
    -mfloat-abi=soft) TRUOC, roi moi den thu muc multilib. Neu khong, `-lm` se
    lay nham ban softfp va sai ABI truyen tham so dau phay dong.
    """
    if not toolchain_root:
        return []
    root = Path(toolchain_root).expanduser()
    base = root / "arm-none-eabi" / "lib"
    if not base.is_dir():
        return []

    args: list[str] = []
    if any(base.glob("libm.a")):
        args += ["-L", str(base.resolve())]

    # Cac thu muc con chua libstdc++.a (multilib). Duyet nong truoc, co gioi han.
    for cxx in sorted(base.rglob("libstdc++.a")):
        args += ["-L", str(cxx.parent.resolve())]
    return args


def native_library_args(sdk: MRESDKLayout,
                        toolchain_root: Path | str | None = None) -> list[str]:
    # Static MRE libraries have circular references; GNU groups make the order robust.
    return [
        "-Wl,--start-group",
        *(str(path) for path in sdk.libraries),
        *cxx_library_search_args(toolchain_root),
        "-lstdc++",
        "-lm",
        "-Wl,--end-group",
    ]
