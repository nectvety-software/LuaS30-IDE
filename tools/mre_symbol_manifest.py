from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Create an MRE firmware compatibility manifest from a newline-delimited exported-symbol list."
    )
    ap.add_argument("--id", required=True)
    ap.add_argument("--label")
    ap.add_argument("--firmware", required=True)
    ap.add_argument("--evidence", choices=("observed","fixture","imported"), default="observed")
    ap.add_argument("--symbols", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    symbols = []
    for raw in args.symbols.read_text(encoding="utf-8", errors="replace").splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        # Accept either a bare symbol or simple nm/readelf-style lines.
        token = value.split()[-1]
        if token not in symbols:
            symbols.append(token)

    payload = {
        "schema": 1,
        "id": args.id,
        "label": args.label or args.id,
        "firmware": args.firmware,
        "evidence": args.evidence,
        "exports": sorted(symbols),
        "notes": args.notes,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} with {len(symbols)} exported symbols.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
