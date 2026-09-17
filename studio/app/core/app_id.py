from __future__ import annotations

import json
import secrets
from pathlib import Path


APP_ID_MIN = 100_000
APP_ID_MAX = 2_147_483_647


def collect_app_ids(projects_root: Path, *, exclude: Path | None = None) -> set[int]:
    root = Path(projects_root).expanduser().resolve()
    excluded = Path(exclude).resolve() if exclude else None
    values: set[int] = set()
    if not root.is_dir():
        return values

    for descriptor in root.rglob("project.json"):
        try:
            project_root = descriptor.parent.resolve()
            if excluded and project_root == excluded:
                continue
            payload = json.loads(descriptor.read_text(encoding="utf-8-sig"))
            value = int(payload.get("appid"))
            if value > 0:
                values.add(value)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    return values


def generate_unique_app_id(projects_root: Path, *, exclude: Path | None = None) -> int:
    """Return a positive 31-bit AppID not used by another managed project."""
    used = collect_app_ids(projects_root, exclude=exclude)
    span = APP_ID_MAX - APP_ID_MIN + 1

    for _ in range(1024):
        candidate = APP_ID_MIN + secrets.randbelow(span)
        if candidate not in used:
            return candidate

    # Collision-safe deterministic fallback. This is practically unreachable
    # with the random range, but keeps the uniqueness contract explicit.
    candidate = APP_ID_MIN
    while candidate in used and candidate <= APP_ID_MAX:
        candidate += 1
    if candidate > APP_ID_MAX:
        raise RuntimeError("No free LuaS30 AppID remains in the configured range.")
    return candidate


def rewrite_project_identity(
    descriptor: Path,
    *,
    projects_root: Path,
    name: str | None = None,
    assign_new_app_id: bool = True,
) -> int | None:
    descriptor = Path(descriptor)
    payload = {}
    if descriptor.is_file():
        try:
            payload = json.loads(descriptor.read_text(encoding="utf-8-sig"))
        except Exception:
            payload = {}

    if name is not None:
        payload["name"] = name

    new_app_id = None
    if assign_new_app_id:
        new_app_id = generate_unique_app_id(
            projects_root,
            exclude=descriptor.parent if descriptor.parent.exists() else None,
        )
        payload["appid"] = new_app_id

    descriptor.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return new_app_id
