from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.core.paths import config_dir


class AICredentialStore:
    """Local credential store. On Windows, API keys are DPAPI-encrypted.

    Keys stay outside project folders. The file is written atomically.
    Plaintext keys from older installs are migrated to DPAPI on load.
    """

    SCHEMA = 1
    _ENC = "dpapi"

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or (config_dir() / "ai_credentials.json"))

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _protect(self, plain: str) -> tuple[str, str] | None:
        blob = self._crypt_protect(plain.encode("utf-8"))
        if blob is None:
            return None
        return base64.b64encode(blob).decode("ascii"), self._ENC

    def _unprotect(self, encoded: str) -> str:
        blob = base64.b64decode(encoded.encode("ascii"))
        raw = self._crypt_unprotect(blob)
        if raw is None:
            return ""
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def _crypt_protect(data: bytes) -> bytes | None:
        if os.name != "nt":
            return None
        try:
            import ctypes
            from ctypes import wintypes

            class DATA_BLOB(ctypes.Structure):
                _fields_ = [
                    ("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_byte)),
                ]

            buf = ctypes.create_string_buffer(data, len(data))
            blob_in = DATA_BLOB(
                len(data),
                ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)),
            )
            blob_out = DATA_BLOB()
            ok = ctypes.windll.crypt32.CryptProtectData(  # type: ignore[attr-defined]
                ctypes.byref(blob_in),
                None,
                None,
                None,
                None,
                0,
                ctypes.byref(blob_out),
            )
            if not ok:
                return None
            try:
                return ctypes.string_at(blob_out.pbData, blob_out.cbData)
            finally:
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)  # type: ignore[attr-defined]
        except Exception:
            return None

    @staticmethod
    def _crypt_unprotect(data: bytes) -> bytes | None:
        if os.name != "nt":
            return None
        try:
            import ctypes
            from ctypes import wintypes

            class DATA_BLOB(ctypes.Structure):
                _fields_ = [
                    ("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_byte)),
                ]

            buf = ctypes.create_string_buffer(data, len(data))
            blob_in = DATA_BLOB(
                len(data),
                ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)),
            )
            blob_out = DATA_BLOB()
            ok = ctypes.windll.crypt32.CryptUnprotectData(  # type: ignore[attr-defined]
                ctypes.byref(blob_in),
                None,
                None,
                None,
                None,
                0,
                ctypes.byref(blob_out),
            )
            if not ok:
                return None
            try:
                return ctypes.string_at(blob_out.pbData, blob_out.cbData)
            finally:
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)  # type: ignore[attr-defined]
        except Exception:
            return None

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
        enc = str(item.get("enc") or "plain")
        raw = str(item.get("api_key") or "")
        if not raw:
            return ""
        if enc == self._ENC:
            return self._unprotect(raw)
        # Legacy plaintext: re-save with DPAPI when possible.
        try:
            self.save_key(str(provider or ""), raw)
        except Exception:
            pass
        return raw

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
        stored = key
        enc = "plain"
        protected = self._protect(key)
        if protected is not None:
            stored, enc = protected
        payload = self._load()
        payload["providers"][name] = {
            "api_key": stored,
            "enc": enc,
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
