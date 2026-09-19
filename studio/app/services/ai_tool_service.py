from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from app.services.ai_agent_protocol import ToolAction
from app.services.skill_service import SkillService


_SKIP_PARTS = {".git", ".luas30", "node_modules", "venv", ".venv", "__pycache__", "build", "release"}
_BLOCKED_NAMES = {".env", ".env.local", "credentials.json", "secrets.json", "id_rsa", "id_ed25519"}


class AIReadOnlyToolService:
    """Small, project-confined read/grep/glob toolset inspired by OpenCode."""

    def __init__(self, max_output: int = 18000, engine_root: Path | None = None) -> None:
        self.max_output = max(1000, int(max_output))
        self.engine_root = Path(engine_root).resolve() if engine_root else None
        self.skill_service = SkillService(engine_root) if engine_root else None

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
        """Chạy tool đọc CHUẨN trong project đang mở.

        Agent không còn vùng đọc nào ngoài project: không có `args.scope="engine"`
        để đọc mã nguồn của chính LuaS30 IDE. Nếu model vẫn phát ra scope đó, ta bỏ
        qua và phục vụ từ gốc project như mọi lời gọi read/grep/glob khác.
        """
        tool = str(action.tool or "").lower()
        args = dict(action.args or {})
        args.pop("scope", None)
        if tool == "skill":
            if not self.skill_service:
                raise ValueError("Skill tool is unavailable without an engine root.")
            return self.skill_service.execute(project_root, args)
        root = self._root(project_root)
        if tool == "read":
            return self._read(root, args)
        if tool == "glob":
            return self._glob(root, args)
        if tool == "grep":
            return self._grep(root, args)
        raise ValueError(f"Unsupported AI tool: {action.tool}")

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
