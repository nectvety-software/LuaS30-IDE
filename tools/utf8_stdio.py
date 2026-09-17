"""Windows-safe UTF-8 stdio / subprocess helpers for LuaS30 tools and Studio."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path


def configure_utf8_stdio() -> None:
    """Force UTF-8 stdout/stderr so Vietnamese text never hits locale charmap."""
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


def decode_bytes(data: bytes | bytearray | memoryview | None) -> str:
    if not data:
        return ""
    raw = bytes(data)
    for encoding in ("utf-8", "utf-8-sig", "cp1258", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def safe_print(*args: object, file=None, **kwargs) -> None:
    """print() that never raises on encode; used after a valid artifact exists."""
    stream = file if file is not None else sys.stdout
    try:
        print(*args, file=stream, **kwargs)
        return
    except UnicodeEncodeError:
        pass
    text = " ".join(str(a) for a in args)
    end = kwargs.get("end", "\n")
    if not isinstance(end, str):
        end = "\n"
    payload = (text + end).encode("utf-8", errors="replace")
    buffer = getattr(stream, "buffer", None)
    if buffer is not None:
        try:
            buffer.write(payload)
            buffer.flush()
            return
        except Exception:
            pass
    try:
        Path(os.devnull).write_bytes(b"")
    except Exception:
        pass


def write_text_utf8(path: Path | str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8", errors="replace")
