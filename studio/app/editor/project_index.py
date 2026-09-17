from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


IGNORE_DIRS = {".git", ".svn", ".hg", "build", "release", ".venv", "venv", "__pycache__"}


@dataclass(slots=True)
class Symbol:
    name: str
    path: Path
    line: int
    column: int
    kind: str


class ProjectIndex:
    FUNCTION_RE = re.compile(r"^\s*(?:local\s+)?function\s+([A-Za-z_][A-Za-z0-9_\.:]*)")
    ASSIGNED_FUNCTION_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_\.:]*)\s*=\s*function\b")
    LOCAL_RE = re.compile(r"^\s*local\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|,|$)")

    def __init__(self) -> None:
        self.root: Path | None = None
        self.symbols: dict[str, list[Symbol]] = {}

    def set_root(self, root: str | Path | None) -> None:
        self.root = Path(root).resolve() if root else None
        self.rebuild()

    def rebuild(self) -> None:
        self.symbols.clear()
        if not self.root or not self.root.is_dir():
            return
        for path in self.root.rglob("*.lua"):
            if any(part in IGNORE_DIRS for part in path.relative_to(self.root).parts[:-1]):
                continue
            self.index_file(path)

    def index_file(self, path: str | Path) -> None:
        file_path = Path(path).resolve()
        # Remove stale symbols from this file first.
        for name in list(self.symbols):
            kept = [s for s in self.symbols[name] if s.path != file_path]
            if kept:
                self.symbols[name] = kept
            else:
                del self.symbols[name]
        if not file_path.is_file() or file_path.suffix.lower() != ".lua":
            return
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        for line_no, line in enumerate(text.splitlines(), 1):
            clean = line.split("--", 1)[0]
            match = self.FUNCTION_RE.match(clean)
            kind = "function"
            if not match:
                match = self.ASSIGNED_FUNCTION_RE.match(clean)
            if not match:
                match = self.LOCAL_RE.match(clean)
                kind = "local"
            if match:
                name = match.group(1)
                symbol = Symbol(name, file_path, line_no, max(1, match.start(1) + 1), kind)
                self.symbols.setdefault(name, []).append(symbol)

    def find_definition(self, query: str, current_file: Path | None = None) -> Symbol | None:
        query = query.strip()
        if not query:
            return None
        candidates = list(self.symbols.get(query, []))
        # `object:method` and `object.method` are interchangeable for navigation.
        alt = query.replace(":", ".") if ":" in query else query.replace(".", ":")
        if alt != query:
            candidates.extend(self.symbols.get(alt, []))
        if not candidates and "." in query:
            candidates.extend(self.symbols.get(query.split(".")[-1], []))
        if current_file:
            current = current_file.resolve()
            for symbol in candidates:
                if symbol.path == current:
                    return symbol
        return candidates[0] if candidates else None

    def names(self) -> list[str]:
        return sorted(self.symbols)
