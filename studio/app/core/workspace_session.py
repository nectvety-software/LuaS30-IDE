from __future__ import annotations

import json
from pathlib import Path

from app.core.paths import config_dir


class WorkspaceSessionStore:
    SCHEMA = 1

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or (config_dir() / "workspace_session.json"))

    def load(self) -> dict:
        if not self.path.is_file():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        if not isinstance(payload, dict) or payload.get("schema") != self.SCHEMA:
            return {}
        return payload

    def save(self, state: dict) -> None:
        payload = dict(state)
        payload["schema"] = self.SCHEMA
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(self.path)

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)
