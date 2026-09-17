"""UTF-8 process helpers for Studio QProcess / stdio on Windows."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping

from PySide6.QtCore import QProcessEnvironment


def configure_utf8_stdio() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def utf8_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(base) if base is not None else os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def utf8_qprocess_environment(extra: Mapping[str, str] | None = None) -> QProcessEnvironment:
    env = QProcessEnvironment.systemEnvironment()
    env.insert("PYTHONUTF8", "1")
    env.insert("PYTHONIOENCODING", "utf-8")
    if extra:
        for key, value in extra.items():
            if value is not None:
                env.insert(str(key), str(value))
    return env


def decode_process_bytes(data: bytes | bytearray | memoryview | None) -> str:
    if not data:
        return ""
    raw = bytes(data)
    for encoding in ("utf-8", "utf-8-sig", "cp1258", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")
