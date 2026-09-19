from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from app.services.ai_agent_protocol import ToolAction


_SKIP_PARTS = {".git", ".luas30", "node_modules", "venv", ".venv", "__pycache__", "build", "release"}
_BLOCKED_NAMES = {".env", ".env.local", "credentials.json", "secrets.json", "id_rsa", "id_ed25519"}

# Vùng đọc được của công cụ "engine": lõi MRE của chính IDE, nằm ngoài mọi dự án.
ENGINE_ALLOWED_PREFIXES = (
    "templates", "sdk", "engine", "compat", "doc/ai", "extensions",
)
ENGINE_READABLE_SUFFIXES = {
    ".lua", ".c", ".h", ".cpp", ".hpp", ".py", ".md", ".json", ".txt",
    ".toml", ".ini", ".cfg", ".yaml", ".yml", ".xml", ".qss",
}


class AIReadOnlyToolService:
    """Small, project-confined read/grep/glob toolset inspired by OpenCode."""

    def __init__(self, max_output: int = 18000, engine_root: Path | None = None) -> None:
        self.max_output = max(1000, int(max_output))
        self.engine_root = Path(engine_root).resolve() if engine_root else None

    @staticmethod
    def _root(project_root: Path | None) -> Path:
        if not project_root:
            raise ValueError("Open a project before using codebase tools.")
        root = Path(project_root).expanduser().resolve()
        if not root.is_dir():
            raise ValueError("The active project directory is unavailable.")
        return root

    @staticmethod
    def _safe_file(root: Path, relative: str) -> Path:
        raw = str(relative or "").strip().replace("\\", "/")
        while raw.startswith("./"):
            raw = raw[2:]
        if not raw or raw.startswith("/") or ".." in Path(raw).parts:
            raise ValueError("Tool path must be project-relative.")
        target = (root / raw).resolve()
        try:
            rel = target.relative_to(root)
        except ValueError as exc:
            raise ValueError("Tool path escaped the project root.") from exc
        lowered_name = target.name.lower()
        if lowered_name in _BLOCKED_NAMES or any(token in lowered_name for token in ("secret", "credential", "private_key")):
            raise ValueError("The requested path is protected or sensitive.")
        if any(part.lower() in _SKIP_PARTS for part in rel.parts):
            raise ValueError("The requested path is protected or generated.")
        return target

    @staticmethod
    def _allowed(path: Path, root: Path) -> bool:
        try:
            rel = path.relative_to(root)
        except ValueError:
            return False
        lowered_name = path.name.lower()
        if lowered_name in _BLOCKED_NAMES or any(token in lowered_name for token in ("secret", "credential", "private_key")):
            return False
        return not any(part.lower() in _SKIP_PARTS for part in rel.parts)

    @staticmethod
    def _matches(rel: str, pattern: str) -> bool:
        pattern = str(pattern or "**/*").replace("\\", "/")
        if pattern in {"*", "**", "**/*"}:
            return True
        variants = [pattern]
        if pattern.startswith("**/"):
            variants.append(pattern[3:])
        return any(fnmatch.fnmatch(rel, item) or Path(rel).match(item) for item in variants)

    def _limit(self, text: str) -> str:
        value = str(text or "")
        if len(value) <= self.max_output:
            return value
        half = self.max_output // 2
        return value[:half] + "\n...[tool output truncated]...\n" + value[-half:]

    def execute(self, project_root: Path | None, action: ToolAction) -> str:
        tool = str(action.tool or "").lower()
        args = dict(action.args or {})
        if tool == "engine":
            return self._engine(args)
        root = self._root(project_root)
        if tool == "read":
            return self._read(root, args)
        if tool == "glob":
            return self._glob(root, args)
        if tool == "grep":
            return self._grep(root, args)
        raise ValueError(f"Unsupported AI tool: {action.tool}")

    # ------------------------------------------------------------ engine tool
    def _engine_root(self) -> Path:
        if not self.engine_root or not self.engine_root.is_dir():
            raise ValueError("Engine root is unavailable for the engine tool.")
        return self.engine_root

    def _engine_path(self, raw: str) -> Path:
        root = self._engine_root()
        rel = self._safe_file(root, str(raw or ""))
        parts = rel.relative_to(root).parts
        prefix = "/".join(parts[:2]) if parts and parts[0] == "doc" else (parts[0] if parts else "")
        if prefix not in ENGINE_ALLOWED_PREFIXES:
            raise ValueError(
                "engine tool chỉ đọc được: " + ", ".join(ENGINE_ALLOWED_PREFIXES)
            )
        return rel

    def _engine(self, args: dict) -> str:
        op = str(args.get("op") or "read").strip().lower()
        root = self._engine_root()
        if op == "read":
            target = self._engine_path(str(args.get("path") or ""))
            if not target.is_file():
                raise ValueError(f"File not found: {target}")
            if target.suffix.lower() not in ENGINE_READABLE_SUFFIXES:
                raise ValueError("engine read only supports text source/doc files.")
            return self._read(root, args)
        if op == "list":
            scope = self._engine_path(str(args.get("path") or "")) if args.get("path") else root
            if not scope.is_dir():
                raise ValueError(f"Not an engine directory: {args.get('path')}")
            entries = sorted(
                (p for p in scope.iterdir() if self._allowed(p, root)),
                key=lambda p: (p.is_file(), p.name.lower()),
            )[:400]
            lines = [
                f"{p.relative_to(root).as_posix()}{'/' if p.is_dir() else ''}" for p in entries
            ]
            return self._limit(f"LIST {scope.relative_to(root).as_posix() or '.'}\n" + ("\n".join(lines) or "(empty)"))
        if op == "glob":
            pattern = str(args.get("pattern") or "**/*").replace("\\", "/")
            matches: list[str] = []
            for base in self._engine_scopes():
                for path in base.rglob("*"):
                    if len(matches) >= 300:
                        break
                    if not path.is_file() or not self._allowed(path, root):
                        continue
                    rel = path.relative_to(root).as_posix()
                    if self._matches(rel, pattern) or self._matches(rel, f"**/{pattern}"):
                        matches.append(rel)
            matches.sort()
            return self._limit("GLOB " + pattern + "\n" + ("\n".join(matches) or "(no matches)"))
        if op == "grep":
            pattern = str(args.get("pattern") or "")
            if not pattern:
                raise ValueError("grep pattern is empty.")
            scope = str(args.get("path") or "").strip().strip("/")
            include = str(args.get("include") or "**/*")
            if scope:
                scope_dir = self._engine_path(scope)
                if not scope_dir.is_dir():
                    raise ValueError(f"Not an engine directory: {scope}")
                walk_roots = [scope_dir]
            else:
                walk_roots = self._engine_scopes()
            lines: list[str] = []
            for base in walk_roots:
                prefix = base.relative_to(root).as_posix()
                result = self._grep(base, {
                    "pattern": pattern,
                    "include": include,
                    "case_sensitive": args.get("case_sensitive"),
                })
                body = result.split("\n", 1)[1] if "\n" in result else ""
                for line in body.splitlines():
                    if line.startswith("(no matches)") or line.startswith("..."):
                        continue
                    lines.append(f"{prefix}/{line}" if not line.startswith(prefix) else line)
                    if len(lines) >= 200:
                        break
                if len(lines) >= 200:
                    break
            return self._limit("GREP " + pattern + " (engine)\n" + ("\n".join(lines) or "(no matches)"))
        raise ValueError(f"Unsupported engine op: {op}")

    def _engine_scopes(self) -> list[Path]:
        root = self._engine_root()
        return [
            root / prefix for prefix in ENGINE_ALLOWED_PREFIXES
            if (root / prefix).is_dir()
        ]

    def _read(self, root: Path, args: dict) -> str:
        path = self._safe_file(root, str(args.get("path") or ""))
        if not path.is_file():
            raise ValueError(f"File not found: {path.relative_to(root).as_posix()}")
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except UnicodeDecodeError as exc:
            raise ValueError("read only supports text source files.") from exc
        start = max(1, int(args.get("start_line") or 1))
        end = int(args.get("end_line") or min(len(lines), start + 299))
        end = max(start, min(len(lines), end))
        selected = [f"{idx:>5}: {lines[idx-1]}" for idx in range(start, end + 1)]
        header = f"READ {path.relative_to(root).as_posix()} lines {start}-{end}/{len(lines)}\n"
        return self._limit(header + "\n".join(selected))

    def _glob(self, root: Path, args: dict) -> str:
        pattern = str(args.get("pattern") or "**/*").replace("\\", "/")
        matches: list[str] = []
        for path in root.rglob("*"):
            if len(matches) >= 300:
                break
            if not path.is_file() or not self._allowed(path, root):
                continue
            rel = path.relative_to(root).as_posix()
            if self._matches(rel, pattern):
                matches.append(rel)
        matches.sort()
        return self._limit("GLOB " + pattern + "\n" + ("\n".join(matches) if matches else "(no matches)"))

    def _grep(self, root: Path, args: dict) -> str:
        pattern = str(args.get("pattern") or "")
        if not pattern:
            raise ValueError("grep pattern is empty.")
        include = str(args.get("include") or "**/*")
        try:
            regex = re.compile(pattern, re.IGNORECASE if not bool(args.get("case_sensitive")) else 0)
        except re.error as exc:
            raise ValueError(f"Invalid grep regex: {exc}") from exc
        hits: list[str] = []
        for path in root.rglob("*"):
            if len(hits) >= 200:
                break
            if not path.is_file() or not self._allowed(path, root):
                continue
            rel = path.relative_to(root).as_posix()
            if not self._matches(rel, include):
                continue
            try:
                text = path.read_text(encoding="utf-8-sig")
            except (UnicodeDecodeError, OSError):
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    hits.append(f"{rel}:{line_no}: {line[:500]}")
                    if len(hits) >= 200:
                        break
        return self._limit("GREP " + pattern + "\n" + ("\n".join(hits) if hits else "(no matches)"))
