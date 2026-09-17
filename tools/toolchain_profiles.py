from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess
from pathlib import Path


PROFILE_IDS = ("auto", "gcc", "rvds", "ads12")


@dataclass(frozen=True)
class Toolchain:
    profile_id: str
    display_name: str
    root: Path
    compiler: Path
    linker: Path
    inspector: Path | None
    stripper: Path | None
    entry_symbol: str
    compiler_family: str
    compile_flags: tuple[str, ...]
    link_flags: tuple[str, ...]
    output_style: str
    evidence: str


def _walk_find(root: Path, names: tuple[str, ...], max_depth: int = 7) -> Path | None:
    root = Path(root).resolve()
    lowered = {name.lower() for name in names}
    direct_dirs = (
        root,
        root / "bin",
        root / "Bin",
        root / "gcc" / "bin",
        root / "ARM" / "ADSv1_2" / "Bin",
        root / "ADSv1_2" / "Bin",
        root / "RVCT" / "Programs",
        root / "Programs",
    )
    for directory in direct_dirs:
        if not directory.is_dir():
            continue
        for name in names:
            p = directory / name
            if p.is_file():
                return p.resolve()

    root_depth = len(root.parts)
    for base, dirs, files in os.walk(root):
        depth = len(Path(base).parts) - root_depth
        if depth >= max_depth:
            dirs[:] = []
        file_map = {name.lower(): name for name in files}
        for wanted in lowered:
            actual = file_map.get(wanted)
            if actual:
                return (Path(base) / actual).resolve()
    return None


def _first(root: Path, *names: str) -> Path | None:
    return _walk_find(root, tuple(names))


def _gcc(root: Path) -> Toolchain | None:
    gcc = _first(root, "arm-none-eabi-gcc.exe", "arm-none-eabi-gcc")
    readelf = _first(root, "arm-none-eabi-readelf.exe", "arm-none-eabi-readelf")
    strip = _first(root, "arm-none-eabi-strip.exe", "arm-none-eabi-strip")
    if not gcc or not readelf:
        return None
    return Toolchain(
        profile_id="gcc",
        display_name="ARM GCC (MRE)",
        root=Path(root).resolve(),
        compiler=gcc,
        linker=gcc,
        inspector=readelf,
        stripper=strip,
        entry_symbol="gcc_entry",
        compiler_family="gcc",
        compile_flags=(
            "-c", "-fpic", "-march=armv5te", "-mfloat-abi=soft",
            "-mlittle-endian", "-Os", "-fvisibility=hidden",
            "-fdata-sections", "-ffunction-sections", "-fno-strict-aliasing",
            "-std=gnu99",
            "-D_NOUNIX_", "-DMRE", "-DGCC", "-D__MRE_COMPILER_GCC__",
            "-DLUAS30_ENGINE", "-DLUAS30_NATIVE_SDK",
        ),
        link_flags=(
            "-nostartfiles", "-fpic", "-fpcc-struct-return", "-pie",
            "-Wl,--gc-sections", "-Wl,--strip-debug",
        ),
        output_style="gcc",
        evidence="LuaS30 MRE GCC profile",
    )


def _rvds(root: Path) -> Toolchain | None:
    armcc = _first(root, "armcc.exe", "armcc")
    armlink = _first(root, "armlink.exe", "armlink")
    fromelf = _first(root, "fromelf.exe", "fromelf")
    if not armcc or not armlink:
        return None
    return Toolchain(
        profile_id="rvds",
        display_name="RVDS / RVCT",
        root=Path(root).resolve(),
        compiler=armcc,
        linker=armlink,
        inspector=fromelf,
        stripper=None,
        entry_symbol="rvct_entry",
        compiler_family="armcc",
        compile_flags=(
            "-c", "-O2", "-g", "--split_sections", "--apcs=/fpic",
            "--cpu", "ARM7EJ-S", "--littleend",
            "-D_NOUNIX_", "-DMRE", "-D__MRE_COMPILER_RVCT__",
            "-DLUAS30_ENGINE", "-DLUAS30_NATIVE_SDK",
        ),
        link_flags=(
            "--fpic", "--sysv", "--remove",
        ),
        output_style="rvds",
        evidence="MRE SDK/RVCT ARM7EJ-S + fpic + rvct_entry convention",
    )


def _ads12(root: Path) -> Toolchain | None:
    # ADS 1.2 commonly has both tcc.exe (Thumb C) and armcc.exe. MRELauncher
    # exposed a "Thumb Command", so prefer tcc when it exists.
    tcc = _first(root, "tcc.exe", "tcc")
    armcc = _first(root, "armcc.exe", "armcc")
    compiler = tcc or armcc
    armlink = _first(root, "armlink.exe", "armlink")
    fromelf = _first(root, "fromelf.exe", "fromelf")
    if not compiler or not armlink:
        return None
    return Toolchain(
        profile_id="ads12",
        display_name="ARM ADS 1.2",
        root=Path(root).resolve(),
        compiler=compiler,
        linker=armlink,
        inspector=fromelf,
        stripper=None,
        entry_symbol="ads_entry",
        compiler_family="ads",
        compile_flags=(
            "-c", "-O2", "-g", "-apcs", "/fpic", "-cpu", "ARM7EJ-S",
            "-D_NOUNIX_", "-DMRE", "-D__MRE_COMPILER_ADS__",
            "-DLUAS30_ENGINE", "-DLUAS30_NATIVE_SDK",
        ),
        # ADS 1.2 armlink uses the older single-dash syntax. -reloc keeps
        # relocation information for loader-oriented images; entry/first are
        # appended by build.py so --entry-symbol can override the LuaS30 name.
        link_flags=("-elf", "-reloc", "-remove"),
        output_style="ads",
        evidence="ADS 1.2 tcc/armcc/armlink compatibility profile",
    )


def detect_toolchain(root: Path, requested: str = "auto") -> Toolchain:
    root = Path(root).expanduser().resolve()
    requested = str(requested or "auto").lower()
    if requested not in PROFILE_IDS:
        raise ValueError(f"Unknown compiler profile: {requested}")

    if requested == "gcc":
        found = _gcc(root)
        if not found:
            raise FileNotFoundError("ARM GCC profile selected but arm-none-eabi-gcc/readelf were not found.")
        return found
    if requested == "rvds":
        found = _rvds(root)
        if not found:
            raise FileNotFoundError("RVDS profile selected but armcc/armlink were not found.")
        return found
    if requested == "ads12":
        found = _ads12(root)
        if not found:
            raise FileNotFoundError("ADS1.2 profile selected but tcc/armcc + armlink were not found.")
        return found

    # Auto: GCC first for LuaS30's bundled toolchain. If ARM proprietary tools
    # are supplied, tcc is a strong ADS 1.2 discriminator; otherwise armcc+
    # armlink is treated as RVDS/RVCT.
    found = _gcc(root)
    if found:
        return found
    if _first(root, "tcc.exe", "tcc"):
        found = _ads12(root)
        if found:
            return found
    found = _rvds(root)
    if found:
        return found
    found = _ads12(root)
    if found:
        return found

    raise FileNotFoundError(
        "No supported MRE ARM toolchain found. Expected ARM GCC "
        "(arm-none-eabi-gcc/readelf), RVDS/RVCT (armcc/armlink), or "
        "ADS1.2 (tcc/armcc + armlink)."
    )


def configure_environment(toolchain: Toolchain) -> list[str]:
    root = toolchain.root
    candidates = [
        toolchain.compiler.parent,
        toolchain.linker.parent,
        toolchain.inspector.parent if toolchain.inspector else None,
        root / "bin",
        root / "Bin",
        root / "arm-none-eabi" / "bin",
        root / "libexec",
    ]
    existing = []
    seen = set()
    for item in candidates:
        if item and Path(item).is_dir():
            value = str(Path(item).resolve())
            low = value.lower()
            if low not in seen:
                existing.append(value)
                seen.add(low)

    old = os.environ.get("PATH", "")
    old_entries = {x.lower() for x in old.split(os.pathsep) if x}
    prepend = [x for x in existing if x.lower() not in old_entries]
    if prepend:
        os.environ["PATH"] = os.pathsep.join(prepend + ([old] if old else []))
    os.environ["LUAS30_TOOLCHAIN_ROOT"] = str(root)
    os.environ["LUAS30_COMPILER_PROFILE"] = toolchain.profile_id

    # ARM proprietary tools traditionally use ARMBIN/ARMLIB/ARMINC style
    # environment variables. Fill only missing values so licensed user setups
    # are not overwritten.
    if toolchain.compiler_family in {"armcc", "ads"}:
        os.environ.setdefault("ARMBIN", str(toolchain.compiler.parent))
        lib_candidates = [root / "lib", root / "Lib"]
        inc_candidates = [root / "include", root / "Include"]
        for p in lib_candidates:
            if p.is_dir():
                os.environ.setdefault("ARMLIB", str(p.resolve()))
                break
        for p in inc_candidates:
            if p.is_dir():
                os.environ.setdefault("ARMINC", str(p.resolve()))
                break
    return prepend


def version_text(executable: Path, family: str) -> str:
    attempts = (
        ["--version"],
        ["--vsn"],
        ["-vsn"],
        ["-help"],
    ) if family == "gcc" else (
        ["--vsn"],
        ["-vsn"],
        ["--version"],
        ["-help"],
    )
    for args in attempts:
        try:
            p = subprocess.run(
                [str(executable), *args],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=12,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        text = (p.stdout or "") + (p.stderr or "")
        if text.strip():
            return text.strip()
    return ""
