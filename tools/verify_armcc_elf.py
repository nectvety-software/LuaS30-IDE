from __future__ import annotations

import argparse
import struct
import subprocess
from pathlib import Path

from vxp_pack import iter_elf32_symbols


def verify(elf: Path, entry_symbol: str, inspector: Path | None = None):
    data = elf.read_bytes()
    checks = {
        "ELF magic": data[:4] == b"\x7fELF",
        "ELF32": len(data) > 20 and data[4] == 1,
        "little-endian": len(data) > 20 and data[5] == 1,
        "ARM machine": len(data) > 20 and struct.unpack_from("<H", data, 18)[0] == 40,
    }
    symbols = list(iter_elf32_symbols(data))
    names = {item["name"] for item in symbols}
    checks[f"entry {entry_symbol}"] = entry_symbol in names

    undefined_vm = [
        item["name"] for item in symbols
        if item["shndx"] == 0 and item["name"].startswith("vm_")
    ]
    checks["no static vm_* undefined imports"] = not undefined_vm

    inspector_text = ""
    if inspector and inspector.is_file():
        for args in (["--text", "-c", str(elf)], ["-text", "-c", str(elf)], ["-a", str(elf)]):
            try:
                p = subprocess.run(
                    [str(inspector), *args],
                    capture_output=True, text=True, errors="replace", timeout=20,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            inspector_text = ((p.stdout or "") + (p.stderr or "")).strip()
            if inspector_text:
                break

    lines = ["# LuaS30 ARMCC/ADS ELF report", ""]
    lines.extend(f"{name}: {'PASS' if value else 'FAIL'}" for name, value in checks.items())
    lines += [
        "",
        f"Entry convention: `{entry_symbol}`",
        f"Undefined vm_* symbols: {', '.join(undefined_vm) if undefined_vm else 'none'}",
    ]
    if inspector_text:
        lines += ["", "## fromelf output", "```text", inspector_text[:16000], "```"]
    return all(checks.values()), "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("elf", type=Path)
    ap.add_argument("entry")
    ap.add_argument("report", type=Path)
    ap.add_argument("--inspector", type=Path)
    args = ap.parse_args()
    ok, text = verify(args.elf, args.entry, args.inspector)
    args.report.write_text(text, encoding="utf-8")
    print("\n".join(text.splitlines()[:10]))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
