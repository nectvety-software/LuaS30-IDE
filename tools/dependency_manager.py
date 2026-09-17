from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

try:
    from pip._vendor.packaging.requirements import Requirement
    from pip._vendor.packaging.version import Version
except Exception as exc:  # pragma: no cover - pip is bootstrapped before this script
    print(f"[ERROR] pip packaging helpers unavailable: {exc}", file=sys.stderr)
    raise SystemExit(31)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def log_line(path: Path | None, text: str) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def parse_requirements(path: Path) -> list[Requirement]:
    result: list[Requirement] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-r ", "--requirement ", "--extra-index-url", "--index-url")):
            raise ValueError(f"Unsupported requirement directive in smart launcher: {line}")
        result.append(Requirement(line))
    return result


def installed_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def requirement_state(req: Requirement) -> dict:
    current = installed_version(req.name)
    ok = False
    if current is not None:
        try:
            ok = req.specifier.contains(Version(current), prereleases=True)
        except Exception:
            ok = False
    return {
        "name": req.name,
        "requirement": str(req),
        "installed": current,
        "satisfied": ok,
    }


def all_states(reqs: Iterable[Requirement]) -> list[dict]:
    return [requirement_state(r) for r in reqs]


def internet_available(timeout: float = 2.5) -> bool:
    # Only called when a dependency actually needs changing. This avoids a
    # network touch on normal starts when the environment is already valid.
    targets = (("pypi.org", 443), ("files.pythonhosted.org", 443))
    for host, port in targets:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            pass
    return False


def run_pip(python: Path, args: list[str], launcher_log: Path | None) -> int:
    cmd = [str(python), "-m", "pip", "--disable-pip-version-check", *args]
    log_line(launcher_log, "[deps] RUN " + " ".join(cmd))
    p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, errors="replace")
    if p.stdout:
        for line in p.stdout.splitlines():
            log_line(launcher_log, "[pip] " + line)
    return p.returncode


def print_state(states: list[dict]) -> None:
    for s in states:
        current = s["installed"] or "not installed"
        marker = "OK" if s["satisfied"] else "NEEDS UPDATE"
        print(f"       {s['name']}: {current} -> {s['requirement']} [{marker}]")


def change_reason(before: str | None, after: str | None) -> str:
    if before is None and after:
        return "installed"
    if before and after and before != after:
        return "updated"
    return "unchanged"


def main() -> int:
    ap = argparse.ArgumentParser(description="LuaS30 smart dependency checker/updater")
    ap.add_argument("--requirements", type=Path, required=True)
    ap.add_argument("--python", type=Path, default=Path(sys.executable))
    ap.add_argument("--mode", choices=("auto", "online", "offline"), default="auto")
    ap.add_argument("--changes-log", type=Path)
    ap.add_argument("--launcher-log", type=Path)
    ap.add_argument("--state-json", type=Path)
    ap.add_argument("--force", action="store_true", help="reinstall/upgrade requirements even when satisfied")
    ap.add_argument(
        "--find-links",
        action="append",
        default=[],
        metavar="DIR",
        help="Local directory with .whl files for offline install. "
        "Can be repeated. Bundled single-file installers ship vendor/wheels.",
    )
    args = ap.parse_args()

    req_path = args.requirements.resolve()
    python = args.python.resolve()
    if not req_path.is_file():
        print(f"[ERROR] requirements file missing: {req_path}")
        return 32

    reqs = parse_requirements(req_path)
    before = all_states(reqs)
    print_state(before)

    unsatisfied = [s for s in before if not s["satisfied"]]
    update_required = bool(unsatisfied) or args.force

    effective_mode = args.mode
    online = None
    did_network_probe = False
    if not update_required:
        print("       Dependencies already satisfy requirements. No network check, no pip install.")
    else:
        if args.mode == "offline":
            online = False
        elif args.mode == "online":
            online = True
        else:
            did_network_probe = True
            online = internet_available()
            effective_mode = "online" if online else "offline"

        if not online:
            # Offline: install only from bundled local wheels when available.
            targets = [s["requirement"] for s in before if (args.force or not s["satisfied"])]
            link_dirs = [Path(d) for d in (args.find_links or [])]
            link_dirs = [d for d in link_dirs if d.is_dir() and any(d.glob("*.whl"))]
            if link_dirs:
                pip_args: list[str] = ["install", "--upgrade", "--no-index"]
                for d in link_dirs:
                    pip_args += ["--find-links", str(d)]
                pip_args += targets
                print("       Installing from bundled offline wheels: " + ", ".join(str(d) for d in link_dirs))
                rc = run_pip(python, pip_args, args.launcher_log)
                if rc != 0:
                    print("       [WARN] offline wheels install failed. Re-checking installed environment.")
                    log_line(args.changes_log, f"{now_iso()} UPDATE_FAILED mode={effective_mode} targets={targets} wheels={[str(d) for d in link_dirs]}")
            else:
                print("       Offline mode active. Skipping package download/update.")
        else:
            targets = [s["requirement"] for s in before if (args.force or not s["satisfied"])]
            if targets:
                print("       Updating only required packages: " + ", ".join(targets))
                pip_args = ["install", "--upgrade"]
                for d in (args.find_links or []):
                    if Path(d).is_dir() and any(Path(d).glob("*.whl")):
                        pip_args += ["--find-links", str(Path(d))]
                pip_args += targets
                rc = run_pip(python, pip_args, args.launcher_log)
                if rc != 0:
                    print("       [WARN] pip update failed. Re-checking installed environment.")
                    log_line(args.changes_log, f"{now_iso()} UPDATE_FAILED mode={effective_mode} targets={targets}")

    after = all_states(reqs)
    changed = []
    for b, a in zip(before, after):
        if b["installed"] != a["installed"]:
            reason = change_reason(b["installed"], a["installed"])
            changed.append({
                "name": a["name"],
                "before": b["installed"],
                "after": a["installed"],
                "reason": reason,
            })
            log_line(
                args.changes_log,
                f"{now_iso()} {reason.upper()} {a['name']} {b['installed'] or '-'} -> {a['installed'] or '-'} requirement={a['requirement']}",
            )

    if not changed and update_required:
        log_line(args.changes_log, f"{now_iso()} NO_CHANGE mode={effective_mode} requirements={req_path.name}")

    ready = all(s["satisfied"] for s in after)
    state = {
        "checked_at": now_iso(),
        "requested_mode": args.mode,
        "effective_mode": effective_mode,
        "network_checked": did_network_probe,
        "network_available": online,
        "update_required": update_required,
        "changed": changed,
        "ready": ready,
        "requirements_file": str(req_path),
        "packages": after,
    }
    if args.state_json:
        args.state_json.parent.mkdir(parents=True, exist_ok=True)
        args.state_json.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    print("       Dependency mode:", effective_mode.upper())
    if changed:
        for c in changed:
            print(f"       Changed: {c['name']} {c['before'] or '-'} -> {c['after'] or '-'}")
    else:
        print("       No dependency changes.")

    if ready:
        return 0

    print("       [ERROR] Required Python libraries are not available in compatible versions.")
    if effective_mode == "offline":
        print("       Connect to the Internet once, or run again without --offline after network access is restored.")
        return 20
    return 21


if __name__ == "__main__":
    raise SystemExit(main())
