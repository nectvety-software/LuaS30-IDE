from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from runtime_compat_model import evaluate_firmware, load_contract, verify_expected

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = ROOT / "compat" / "runtime_abi_contract.json"
DEFAULT_FIRMWARE_DIR = ROOT / "compat" / "mre"
DEFAULT_OUT = ROOT / "build" / "runtime_compat_matrix"


def discover_manifests(directory: Path) -> list[Path]:
    return sorted(
        p for p in directory.glob("*.json")
        if p.name != "runtime_abi_contract.json"
    )


def compact_list(values: list[str]) -> str:
    return ", ".join(values) if values else "-"


def alias_text(row: dict) -> str:
    aliases = row["abi_aliases"]
    if not aliases:
        return "-"
    return "; ".join(
        f'{a["field"]}:{a["primary"]}->{a["selected"]}' for a in aliases
    )


def print_table(rows: list[dict]) -> None:
    headers = ["Firmware", "Evidence", "Native Caps", "ABI Aliases", "Fallbacks", "Level", "Result"]
    printable = []
    for row in rows:
        printable.append([
            row["id"],
            row["evidence"],
            compact_list(row["native_capabilities"]),
            alias_text(row),
            compact_list(row["fallbacks"]),
            row["compatibility_level"],
            row["final_result"],
        ])
    widths = [
        max(len(headers[i]), *(len(r[i]) for r in printable))
        for i in range(len(headers))
    ]
    def emit(items):
        print(" | ".join(str(items[i]).ljust(widths[i]) for i in range(len(headers))))
    emit(headers)
    print("-+-".join("-" * w for w in widths))
    for row in printable:
        emit(row)


def write_outputs(out_dir: Path, rows: list[dict], contract_path: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": 1,
        "engine_version": "1.8.3",
        "contract": str(contract_path.resolve()),
        "summary": {
            "total": len(rows),
            "pass": sum(1 for r in rows if r["final_result"] == "PASS"),
            "degraded": sum(1 for r in rows if r["final_result"] == "DEGRADED"),
            "fail": sum(1 for r in rows if r["final_result"] == "FAIL"),
        },
        "firmwares": rows,
    }
    (out_dir / "runtime_compat_matrix.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with (out_dir / "runtime_compat_matrix.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "id","label","firmware","evidence","export_count",
            "native_capabilities","effective_capabilities","abi_aliases",
            "fallbacks","missing_required","compatibility_level","final_result","notes",
        ])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "id": row["id"],
                "label": row["label"],
                "firmware": row["firmware"],
                "evidence": row["evidence"],
                "export_count": row["export_count"],
                "native_capabilities": compact_list(row["native_capabilities"]),
                "effective_capabilities": compact_list(row["effective_capabilities"]),
                "abi_aliases": alias_text(row),
                "fallbacks": compact_list(row["fallbacks"]),
                "missing_required": compact_list(row["missing_required"]),
                "compatibility_level": row["compatibility_level"],
                "final_result": row["final_result"],
                "notes": row["notes"],
            })

    lines = [
        "LuaS30 Runtime Compatibility Matrix 1.8.3",
        "=" * 46,
        "",
        f"Total: {len(rows)}",
        f"PASS: {sum(1 for r in rows if r['final_result']=='PASS')}",
        f"DEGRADED: {sum(1 for r in rows if r['final_result']=='DEGRADED')}",
        f"FAIL: {sum(1 for r in rows if r['final_result']=='FAIL')}",
        "",
    ]
    for row in rows:
        lines += [
            f'[{row["final_result"]}] {row["id"]} ({row["evidence"]})',
            f'  native capabilities : {compact_list(row["native_capabilities"])}',
            f'  effective capabilities: {compact_list(row["effective_capabilities"])}',
            f'  ABI aliases          : {alias_text(row)}',
            f'  fallbacks            : {compact_list(row["fallbacks"])}',
            f'  missing required     : {compact_list(row["missing_required"])}',
            f'  compatibility level  : {row["compatibility_level"]}',
            "",
        ]
    (out_dir / "runtime_compat_matrix.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate LuaS30 runtime compatibility against MRE firmware symbol manifests.")
    ap.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    ap.add_argument("--firmware-dir", type=Path, default=DEFAULT_FIRMWARE_DIR)
    ap.add_argument("--firmware", action="append", type=Path, default=[],
                    help="explicit firmware manifest; can be repeated")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--fail-on-incompatible", action="store_true",
                    help="return nonzero when any evaluated firmware is incompatible")
    ap.add_argument("--no-verify-expected", action="store_true",
                    help="do not assert fixture expected values")
    args = ap.parse_args()

    contract = load_contract(args.contract)
    paths = args.firmware or discover_manifests(args.firmware_dir)
    if not paths:
        print("No firmware manifests found.", file=sys.stderr)
        return 2

    rows = []
    expectation_failures = []
    for path in paths:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        row = evaluate_firmware(contract, manifest)
        row["manifest_path"] = str(path.resolve())
        rows.append(row)
        if not args.no_verify_expected:
            for error in verify_expected(row):
                expectation_failures.append(f'{row["id"]}: {error}')

    print_table(rows)
    if not args.no_write:
        write_outputs(args.out, rows, args.contract)
        print(f"\nReports: {args.out.resolve()}")

    if expectation_failures:
        print("\nExpectation failures:", file=sys.stderr)
        for error in expectation_failures:
            print(" -", error, file=sys.stderr)
        return 3

    if args.fail_on_incompatible and any(r["final_result"] == "FAIL" for r in rows):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
