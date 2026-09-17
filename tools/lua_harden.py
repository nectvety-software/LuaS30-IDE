from __future__ import annotations

import re
from pathlib import Path


_WORD = re.compile(r"[A-Za-z0-9_]")


def _long_bracket_start(text: str, pos: int):
    if pos >= len(text) or text[pos] != "[":
        return None
    i = pos + 1
    while i < len(text) and text[i] == "=":
        i += 1
    if i < len(text) and text[i] == "[":
        eq = i - pos - 1
        return i + 1, eq
    return None


def _long_bracket_end(text: str, pos: int, eq: int):
    marker = "]" + ("=" * eq) + "]"
    end = text.find(marker, pos)
    return len(text) if end < 0 else end + len(marker)


def _needs_space(prev: str, nxt: str) -> bool:
    if not prev or not nxt:
        return False
    if _WORD.match(prev) and _WORD.match(nxt):
        return True
    if (prev.isdigit() and nxt == ".") or (prev == "." and nxt.isdigit()):
        return True
    if prev + nxt in {"--", "..", "==", "~=", "<=", ">=", "::"}:
        return True
    return False


def minify_lua(text: str) -> str:
    """Conservative Lua 5.1 source minifier.

    Removes comments and unnecessary whitespace while preserving strings,
    long-bracket strings and token boundaries. This is source hardening, not
    cryptographic protection and not a substitute for Lua bytecode.
    """
    out: list[str] = []
    pending_space = False
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        # Short/long comments.
        if ch == "-" and i + 1 < n and text[i + 1] == "-":
            i += 2
            lb = _long_bracket_start(text, i)
            if lb:
                start, eq = lb
                i = _long_bracket_end(text, start, eq)
            else:
                while i < n and text[i] not in "\r\n":
                    i += 1
            pending_space = True
            continue

        # Quoted strings.
        if ch in ("'", '"'):
            if pending_space and out and _needs_space(out[-1][-1], ch):
                out.append(" ")
            pending_space = False
            quote = ch
            start = i
            i += 1
            escaped = False
            while i < n:
                c = text[i]
                i += 1
                if escaped:
                    escaped = False
                    continue
                if c == "\\":
                    escaped = True
                    continue
                if c == quote:
                    break
            out.append(text[start:i])
            continue

        # Long-bracket strings.
        lb = _long_bracket_start(text, i)
        if lb:
            if pending_space and out and _needs_space(out[-1][-1], ch):
                out.append(" ")
            pending_space = False
            start, eq = lb
            end = _long_bracket_end(text, start, eq)
            out.append(text[i:end])
            i = end
            continue

        if ch.isspace():
            pending_space = True
            i += 1
            continue

        if pending_space and out and _needs_space(out[-1][-1], ch):
            out.append(" ")
        pending_space = False
        out.append(ch)
        i += 1

    result = "".join(out).strip()
    if text.endswith(("\n", "\r")):
        result += "\n"
    return result


def minify_file(source: Path, target: Path) -> dict:
    source = Path(source)
    target = Path(target)
    raw = source.read_text(encoding="utf-8-sig")
    hardened = minify_lua(raw)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(hardened, encoding="utf-8", newline="\n")
    before = source.stat().st_size
    after = target.stat().st_size
    return {
        "source": str(source),
        "target": str(target),
        "before_bytes": before,
        "after_bytes": after,
        "saved_bytes": max(0, before - after),
    }


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("target", type=Path)
    args = ap.parse_args()
    print(json.dumps(minify_file(args.source, args.target), indent=2))
