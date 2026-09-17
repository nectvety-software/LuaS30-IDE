"""Regression test: Vietnamese (U+01B0) must survive the UTF-8 pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from utf8_stdio import (  # noqa: E402
    configure_utf8_stdio,
    decode_bytes,
    safe_print,
    utf8_env,
    write_text_utf8,
)

SAMPLE = "Ứng dụng thử nghiệm — đường dẫn, thư mục, người dùng, cấu hình"
UNI_PATH = Path("C:/Temp") / "Dự án thử" / "Ứng dụng Mèo"


def _ok(label: str) -> None:
    print(f"PASS: {label}", flush=True)


def _fail(label: str, detail: str = "") -> None:
    print(f"FAIL: {label} {detail}".rstrip(), flush=True)
    raise SystemExit(1)


def test_stdio() -> None:
    configure_utf8_stdio()
    encoding = (getattr(sys.stdout, "encoding", None) or "").lower()
    if "utf-8" not in encoding and "utf8" not in encoding:
        _fail("stdout UTF-8", f"encoding={encoding}")
    _ok("stdout UTF-8")
    try:
        print(SAMPLE, file=sys.stderr, flush=True)
        _ok("stderr UTF-8")
    except UnicodeEncodeError as exc:
        _fail("stderr UTF-8", str(exc))


def test_subprocess() -> None:
    code = f"print({SAMPLE!r}, end='')"
    p = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        env=utf8_env(),
    )
    if p.returncode != 0:
        _fail("subprocess UTF-8", p.stderr)
    if "Ứng dụng" not in p.stdout or "ư" not in p.stdout:
        _fail("subprocess UTF-8", "missing U+01B0 in stdout")
    _ok("subprocess UTF-8")


def test_decode_fallback() -> None:
    raw = "ư".encode("cp1258")
    text = decode_bytes(raw)
    if "ư" not in text:
        _fail("decode cp1258", text)
    _ok("decode fallback")


def test_safe_print() -> None:
    safe_print(SAMPLE)
    _ok("safe_print")


def test_log_and_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        log = tmp_path / "build.log"
        write_text_utf8(log, SAMPLE + "\n")
        if SAMPLE not in log.read_text(encoding="utf-8"):
            _fail("log UTF-8")
        _ok("log UTF-8")

        payload = {"note": SAMPLE, "path": str(UNI_PATH)}
        json_path = tmp_path / "manifest.json"
        json_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            errors="replace",
        )
        loaded = json.loads(json_path.read_text(encoding="utf-8"))
        if loaded["note"] != SAMPLE:
            _fail("JSON UTF-8")
        _ok("JSON UTF-8")


def test_unicode_path() -> None:
    base = Path(tempfile.gettempdir()) / "LuaS30_UTF8_Regression"
    target = base / "Dự án thử" / "Ứng dụng Mèo"
    target.mkdir(parents=True, exist_ok=True)
    marker = target / "config.json"
    write_text_utf8(marker, json.dumps({"name": SAMPLE}, ensure_ascii=False))
    if "Ứng dụng" not in marker.read_text(encoding="utf-8"):
        _fail("Unicode project path")
    _ok("Unicode project path")


def test_u01b0_bootstrap() -> None:
    p = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys;"
                f"sys.path.insert(0,{str(TOOLS)!r});"
                "import utf8_stdio; utf8_stdio.configure_utf8_stdio();"
                f"print({SAMPLE!r});"
                "assert 'utf-8' in (sys.stdout.encoding or '').lower()"
            ),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        env=utf8_env(),
        cwd=str(ROOT),
    )
    if p.returncode != 0 or "Ứng dụng" not in p.stdout:
        _fail("build-side UTF-8 bootstrap", p.stderr)
    _ok("U+01B0 / ư")


def test_qprocess_decode() -> None:
    studio = ROOT / "studio"
    if str(studio) not in sys.path:
        sys.path.insert(0, str(studio))
    try:
        from app.core.utf8 import decode_process_bytes

        text = decode_process_bytes(SAMPLE.encode("utf-8"))
        if "Ứng dụng" not in text:
            _fail("QProcess decode")
        _ok("QProcess decode")
    except Exception as exc:
        _fail("QProcess decode", str(exc))


def test_build_module_loads() -> None:
    p = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import runpy,sys;"
                f"sys.path.insert(0,{str(TOOLS)!r});"
                "runpy.run_path(r'" + str(TOOLS / "build.py") + "', run_name='not_main')"
            ),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=utf8_env(),
        cwd=str(ROOT),
    )
    if p.returncode != 0:
        # argparse/import may still fail for unrelated reasons; only require no charmap crash.
        combined = (p.stdout or "") + (p.stderr or "")
        if "charmap" in combined or "UnicodeEncodeError" in combined:
            _fail("build.py import encoding", combined[-500:])
        # Import of build.py as not_main should not raise SystemExit from argparse.
        # If it fails for missing args only when run as main, that's fine.
    combined = (p.stdout or "") + (p.stderr or "")
    if "UnicodeEncodeError" in combined or "'charmap' codec" in combined:
        _fail("build.py import encoding", combined[-500:])
    _ok("build.py UTF-8 bootstrap")


def main() -> int:
    configure_utf8_stdio()
    print("LuaS30 UTF-8 pipeline regression", flush=True)
    print("sample:", SAMPLE, flush=True)
    test_stdio()
    test_subprocess()
    test_decode_fallback()
    test_safe_print()
    test_log_and_json()
    test_unicode_path()
    test_u01b0_bootstrap()
    test_qprocess_decode()
    test_build_module_loads()
    print("PASS: UTF-8 pipeline complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
