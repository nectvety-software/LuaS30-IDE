from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.services.extension_service import ExtensionService
from app.services.skill_service import SkillService

IGNORED_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__",
    "build", "release", "dist", ".idea", ".vscode", ".cache", "cache",
}
IGNORED_NAMES = {
    ".env", ".env.local", ".env.production", "credentials.json", "secrets.json",
    "id_rsa", "id_ed25519",
}
TEXT_EXTENSIONS = {
    ".lua", ".py", ".c", ".h", ".cpp", ".hpp", ".cc", ".hh", ".md", ".txt",
    ".json", ".toml", ".ini", ".cfg", ".yaml", ".yml", ".xml", ".html", ".css",
    ".js", ".ts", ".tsx", ".jsx", ".bat", ".ps1",
}
INSTRUCTION_NAMES = ("SKILLS.md", "SKILL.md", "PROMPT.md")

# Tài liệu chỉ dẫn là LUẬT của agent, không phải mẫu source: cắt bớt ở đây không
# phải "tiết kiệm ngữ cảnh" mà là **giấu luật**. Từng bị đúng như vậy — PROMPT.md
# gộp thêm tài liệu Nokia 225 dài 51k ký tự, nhưng hạn mức 14k cắt mất phần cuối,
# nên agent không hề nhận được nội dung mới trong khi bản ghi vẫn báo "đã nạp".
# Vì thế hạn mức ở đây phải đủ cho cả bộ tài liệu, và khi buộc phải cắt thì thông
# báo phải nói rõ đã cắt BAO NHIÊU.
INSTRUCTION_FILE_LIMIT = 64000
INSTRUCTION_TOTAL_BUDGET = 160000

# Bản đồ "lõi Lua MRE" mà một dự án không tự thấy được — đưa thẳng vào mọi
# system prompt để agent biết chính xác chỗ phải đọc (read/grep/glob với
# scope="engine") thay vì bịa API của nền tảng di động khác.
ENGINE_CORE_ENTRIES = (
    ("templates/basic/src/engine.lua", "wrapper Lua mỏng quanh bảng global `engine` — API mà dự án thật sự gọi"),
    ("engine/src/runtime_bridge.c", "mảng `luaL_Reg funcs[]` + luas30_bridge_open — mọi hàm engine.* có thật đều đăng ký ở đây (tên global là `engine`, alias `mre`)"),
    ("templates/basic/main.lua", "điểm vào dự án chuẩn"),
    ("templates/basic/conf.lua", "cấu hình VXPEngine (màn hình 240x320, tài nguyên)"),
    ("templates/basic/project.json", "manifest build .vxp"),
    ("sdk/luas30/abi/symbols.json", "bảng ký hiệu MRE ABI mà runtime ánh xạ tới"),
    ("sdk/luas30/include/ls30/luas30_sdk.h", "API C của SDK"),
    ("engine/", "runtime C + linker biên dịch .vxp"),
    ("compat/devices", "hồ sơ thiết bị S30+ đã kiểm chứng"),
    ("doc/ai/SKILL.md", "luật agent chính thức"),
)


@dataclass
class ContextBundle:
    text: str
    tree_entries: int
    instruction_files: list[str]
    source_files: list[str]
    total_chars: int


class CodebaseContextService:
    def __init__(self, engine_root: Path) -> None:
        self.engine_root = Path(engine_root).resolve()
        self.extension_service = ExtensionService(self.engine_root)
        self.skill_service = SkillService(self.engine_root)

    @staticmethod
    def _safe_text_file(path: Path) -> bool:
        if path.name.lower() in {name.lower() for name in IGNORED_NAMES}:
            return False
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name not in INSTRUCTION_NAMES:
            return False
        lowered = {part.lower() for part in path.parts}
        if lowered & {name.lower() for name in IGNORED_DIRS}:
            return False
        if any(token in path.name.lower() for token in ("secret", "credential", "private_key")):
            return False
        return True

    @staticmethod
    def _read_text(path: Path, limit: int = 12000) -> str:
        try:
            value = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            try:
                value = path.read_text(encoding="latin-1")
            except OSError:
                return ""
        except OSError:
            return ""
        return value if len(value) <= limit else (
            value[:limit]
            + f"\n...[truncated: {len(value) - limit} of {len(value)} chars omitted]..."
        )

    def instruction_paths(self, project_root: Path | None) -> list[Path]:
        candidates: list[Path] = []
        if project_root:
            root = Path(project_root).resolve()
            for rel in (
                "SKILLS.md", "SKILL.md", "PROMPT.md",
                ".luas30/SKILLS.md", ".luas30/SKILL.md", ".luas30/PROMPT.md",
                "doc/ai/SKILLS.md", "doc/ai/SKILL.md", "doc/ai/PROMPT.md",
            ):
                candidates.append(root/rel)
        for rel in (
            "SKILLS.md", "SKILL.md", "PROMPT.md",
            "doc/ai/SKILLS.md", "doc/ai/SKILL.md", "doc/ai/PROMPT.md",
        ):
            candidates.append(self.engine_root/rel)
        # Tài liệu của extension KHÔNG nạp toàn văn ở đây nữa — mỗi lượt hội
        # thoại trả lại phí token cho chúng trong khi model hiếm khi dùng tới.
        # SkillService biến chúng thành skill nạp theo yêu cầu (tool `skill`),
        # còn <installed_extensions> vẫn liệt kê đầy đủ để agent biết đường gọi.

        result, seen = [], set()
        for path in candidates:
            try:
                resolved = path.resolve()
            except OSError:
                continue
            key = str(resolved).lower()
            if key in seen or not resolved.is_file():
                continue
            seen.add(key)
            result.append(resolved)
        return result

    def project_tree(self, project_root: Path | None, max_entries: int = 450) -> tuple[str, int]:
        if not project_root:
            return "(no project open)", 0
        root = Path(project_root).resolve()
        if not root.is_dir():
            return "(project root missing)", 0
        lines = [f"{root.name}/"]
        count = 0

        def walk(directory: Path, prefix: str = "") -> None:
            nonlocal count
            if count >= max_entries:
                return
            try:
                entries = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            except OSError:
                return
            entries = [x for x in entries if x.name not in IGNORED_NAMES and x.name not in IGNORED_DIRS]
            for index, item in enumerate(entries):
                if count >= max_entries:
                    break
                count += 1
                last = index == len(entries)-1
                lines.append(prefix + ("└─ " if last else "├─ ") + item.name + ("/" if item.is_dir() else ""))
                if item.is_dir():
                    walk(item, prefix + ("   " if last else "│  "))

        walk(root)
        if count >= max_entries:
            lines.append("... [tree truncated] ...")
        return "\n".join(lines), count

    @staticmethod
    def _tokens(question: str) -> set[str]:
        words = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", question.lower())
        stop = {"the","and","for","with","this","that","from","into","code","file","project","lua","please","what","when","where"}
        return {w for w in words if w not in stop}

    def _candidate_files(self, root: Path, max_files: int = 1600) -> list[Path]:
        result = []
        for path in root.rglob("*"):
            if len(result) >= max_files:
                break
            if path.is_file() and self._safe_text_file(path):
                try:
                    rel = path.relative_to(root)
                except ValueError:
                    continue
                if not any(part in IGNORED_DIRS for part in rel.parts):
                    result.append(path)
        return result

    def relevant_files(
        self,
        project_root: Path | None,
        question: str,
        *,
        active_path: Path | None = None,
        active_text: str = "",
        max_files: int = 8,
        max_total_chars: int = 50000,
    ) -> list[tuple[str, str]]:
        if not project_root:
            return []
        root = Path(project_root).resolve()
        if not root.is_dir():
            return []
        selected, budget = [], max_total_chars

        if active_path and active_text:
            try:
                rel = active_path.resolve().relative_to(root).as_posix()
            except Exception:
                rel = active_path.name
            content = active_text[:12000]
            selected.append((rel+" [active]", content))
            budget -= len(content)

        tokens = self._tokens(question)
        ranked = []
        active_resolved = active_path.resolve() if active_path else None
        for path in self._candidate_files(root):
            try:
                if active_resolved and path.resolve() == active_resolved:
                    continue
            except OSError:
                pass
            rel = path.relative_to(root).as_posix()
            score = sum(8 for token in tokens if token in rel.lower())
            text = ""
            if tokens:
                text = self._read_text(path, 9000)
                low = text.lower()
                score += sum(min(12, low.count(token)) for token in tokens)
            elif path.name in {"project.json","main.lua","conf.lua"}:
                score += 6
                text = self._read_text(path, 9000)
            if score > 0:
                if not text:
                    text = self._read_text(path, 9000)
                ranked.append((score, rel, text))

        ranked.sort(key=lambda item: (-item[0], item[1].lower()))
        for _, rel, text in ranked:
            if len(selected) >= max_files or budget <= 0:
                break
            value = text[:min(len(text), budget, 9000)]
            if value:
                selected.append((rel, value))
                budget -= len(value)
        return selected

    def engine_core_summary(self) -> str:
        """Bản đồ ngắn lõi MRE của IDE — đường dẫn THẬT, chỉ liệt kê khi tồn tại,
        kèm số dòng để agent biết độ lớn trước khi gọi tool `engine` đọc nội dung."""
        lines = []
        for rel, note in ENGINE_CORE_ENTRIES:
            target = self.engine_root / rel
            if target.is_file():
                try:
                    size = len(target.read_bytes().splitlines())
                except OSError:
                    size = 0
                lines.append(f"- {rel} ({size} dòng) — {note}")
            elif target.is_dir():
                try:
                    count = sum(1 for _ in target.iterdir())
                except OSError:
                    count = 0
                lines.append(f"- {rel} ({count} mục) — {note}")
        if not lines:
            return ""
        return (
            "<engine_core root=\"LuaS30 IDE installation — outside any project\">\n"
            'Đọc các tệp này bằng read/grep/glob với args.scope="engine" trước khi '
            "sửa code chạm API engine; tuyệt đối không bịa hàm của nền tảng khác.\n"
            + "\n".join(lines) + "\n</engine_core>"
        )

    def build(self, project_root: Path | None, question: str, *, active_path: Path | None = None, active_text: str = "") -> ContextBundle:
        project = Path(project_root).resolve() if project_root else None
        tree, tree_count = self.project_tree(project)

        instruction_sections, instruction_files = [], []
        instruction_budget = INSTRUCTION_TOTAL_BUDGET
        for path in self.instruction_paths(project):
            if instruction_budget <= 0:
                break
            text = self._read_text(path, min(INSTRUCTION_FILE_LIMIT, instruction_budget))
            if not text:
                continue
            try:
                label = ("project/" + path.relative_to(project).as_posix()) if project and path.is_relative_to(project) else ("engine/" + path.relative_to(self.engine_root).as_posix())
            except Exception:
                label = str(path)
            instruction_files.append(label)
            instruction_sections.append(f"<instruction_document source={label!r}>\n{text}\n</instruction_document>")
            instruction_budget -= len(text)

        sources = self.relevant_files(project, question, active_path=active_path, active_text=active_text)
        parts = ["<codebase_context>", "<project_structure>", tree, "</project_structure>"]
        briefing = self.extension_service.agent_briefing()
        if briefing:
            parts.append(briefing)
        core = self.engine_core_summary()
        if core:
            parts.append(core)
        skills = self.skill_service.index_text(project)
        if skills:
            parts.append(skills)
        if instruction_sections:
            parts += ["<instruction_documents>", *instruction_sections, "</instruction_documents>"]
        if sources:
            parts += ["<relevant_sources>"] + [
                f"<source_file path={name!r}>\n{text}\n</source_file>" for name,text in sources
            ] + ["</relevant_sources>"]
        parts.append("</codebase_context>")
        combined = "\n".join(parts)
        return ContextBundle(
            text=combined,
            tree_entries=tree_count,
            instruction_files=instruction_files,
            source_files=[name for name,_ in sources],
            total_chars=len(combined),
        )
