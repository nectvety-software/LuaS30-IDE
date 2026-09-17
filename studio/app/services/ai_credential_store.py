from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.core.paths import config_dir


class AICredentialStore:
    """Local JSON credential store requested by the user.

    Keys are kept outside project folders so they are not accidentally committed.
    The file is written atomically and chmod(0600) is attempted on platforms that
    support POSIX permissions. This is still a local plaintext JSON file, so the
    provider dialog labels that fact explicitly.
    """

    SCHEMA = 1

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or (config_dir() / "ai_credentials.json"))

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load(self) -> dict:
        if not self.path.is_file():
            return {"schema": self.SCHEMA, "providers": {}}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {"schema": self.SCHEMA, "providers": {}}
        if not isinstance(payload, dict):
            return {"schema": self.SCHEMA, "providers": {}}
        providers = payload.get("providers")
        if not isinstance(providers, dict):
            providers = {}
        return {"schema": self.SCHEMA, "providers": providers}

    def _save(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def load_key(self, provider: str) -> str:
        item = self._load()["providers"].get(str(provider or ""), {})
        if not isinstance(item, dict):
            return ""
        return str(item.get("api_key") or "")

    def has_key(self, provider: str) -> bool:
        return bool(self.load_key(provider))

    def save_key(self, provider: str, api_key: str) -> None:
        name = str(provider or "").strip()
        key = str(api_key or "").strip()
        if not name:
            raise ValueError("Provider name is empty.")
        if not key:
            self.delete_key(name)
            return
        payload = self._load()
        payload["providers"][name] = {
            "api_key": key,
            "updated_at": self._now(),
        }
        self._save(payload)

    def delete_key(self, provider: str) -> None:
        name = str(provider or "").strip()
        payload = self._load()
        if name in payload["providers"]:
            del payload["providers"][name]
            self._save(payload)

    def providers(self) -> list[str]:
        return sorted(
            name for name, value in self._load()["providers"].items()
            if isinstance(value, dict) and value.get("api_key")
        )
