from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
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

# --- Tối ưu hoá bộ nhớ đệm ------------------------------------------------
# Vòng lặp agent gọi `build()` MỖI LƯỢT (8 lượt thường, 32 lượt ở Full Access)
# với cùng một câu hỏi và cùng một project. Nếu không đệm, mỗi lượt lại: đọc
# 160k ký tự tài liệu chỉ dẫn, quét cây thư mục, và chấm điểm + đọc 9k ký tự
# của hàng trăm tệp ứng viên. Ba tầng đệm dưới đây cắt đúng phần đó.
#
# NGUYÊN TẮC AN TOÀN: mọi khoá đệm đều chứa VÂN TAY NỘI DUNG
# `(đường dẫn, mtime_ns, size)` — sửa tệp là vân tay đổi, đệm tự vô hiệu. Không
# có chỗ nào phục vụ nội dung cũ mà không kiểm vân tay. `invalidate()` chỉ là
# chốt thêm cho trường hợp cùng size + cùng mtime_ns (cực hiếm).
FILE_CACHE_CHAR_CAP = 200_000
FILE_CACHE_MAX_ENTRIES = 400
STRUCTURE_FINGERPRINT_MAX_ENTRIES = 2000
PREFIX_CACHE_MAX_ENTRIES = 6
SOURCES_CACHE_MAX_ENTRIES = 12

# Hạ sẵn về chữ thường: trước đây mỗi tệp ứng viên lại dựng lại set này một lần
# (`{name.lower() for name in IGNORED_NAMES}` nằm trong vòng lặp) — với 1600 ứng
# viên là 1600 set dựng thừa mỗi lượt.
_IGNORED_DIRS_LOWER = frozenset(name.lower() for name in IGNORED_DIRS)
_IGNORED_NAMES_LOWER = frozenset(name.lower() for name in IGNORED_NAMES)


@dataclass
class ContextBundle:
    text: str
    tree_entries: int
    instruction_files: list[str]
    source_files: list[str]
    total_chars: int
    cache_hit: bool = False
    stable_chars: int = 0
    metrics: dict = field(default_factory=dict)

    @property
    def cache_rate(self) -> int:
        """% ngữ cảnh dựng lại từ đệm ở lượt này (0-100)."""
        if not self.total_chars:
            return 0
        return int(self.stable_chars * 100 / self.total_chars)


class CodebaseContextService:
    def __init__(self, engine_root: Path) -> None:
        self.engine_root = Path(engine_root).resolve()
        self.extension_service = ExtensionService(self.engine_root)
        self.skill_service = SkillService(self.engine_root)
        # Tầng 1: nội dung tệp, khoá theo vân tay (path, mtime_ns, size).
        self._file_cache: dict[tuple[str, int, int], tuple[str, int]] = {}
        # Tầng 2: tiền tố ổn định (cây + briefing + skills + tài liệu chỉ dẫn).
        self._prefix_cache: dict[tuple, tuple[str, int, tuple[str, ...]]] = {}
        # Tầng 3: danh sách tệp ứng viên, khoá theo vân tay CẤU TRÚC thư mục.
        self._index_cache: dict[str, tuple[str, tuple[Path, ...]]] = {}
        self._sources_cache: dict[tuple, tuple[tuple[str, str], ...]] = {}
        self._metrics = {
            "file_reads": 0, "file_hits": 0,
            "prefix_builds": 0, "prefix_hits": 0,
            "index_builds": 0, "index_hits": 0,
            "sources_builds": 0, "sources_hits": 0,
            "read_chars": 0, "reused_chars": 0,
        }

    # ------------------------------------------------------------------
    # Hạ tầng đệm
    # ------------------------------------------------------------------

    @staticmethod
    def _stat_key(path: Path) -> tuple[str, int, int] | None:
        try:
            info = os.stat(path)
        except OSError:
            return None
        return (str(path), int(info.st_mtime_ns), int(info.st_size))

    def _structure_fingerprint(
        self, root: Path, max_entries: int = STRUCTURE_FINGERPRINT_MAX_ENTRIES
    ) -> str:
        """Vân tay CẤU TRÚC: tên của mọi mục con. CỐ TÌNH không dùng mtime.

        Đã thử dùng mtime thư mục và nó hỏng thật: NTFS ghi metadata TRỄ, nên
        ngay sau khi tạo tệp, mtime của thư mục cha có thể vẫn là giá trị CŨ —
        hai lần gọi liên tiếp cho hai vân tay khác nhau, và tệp vừa tạo có thể
        không xuất hiện. Dùng mtime làm khoá đệm là mời sẵn một lỗi phục vụ dữ
        liệu cũ.

        Tên mục thì không có độ trễ đó: thêm/xoá/đổi tên thấy ngay, còn SỬA NỘI
        DUNG tệp thì không đổi vân tay — đúng thứ cần cho cây thư mục.
        """
        names: list[str] = []
        stack: list[tuple[Path, str]] = [(root, "")]
        while stack and len(names) < max_entries:
            directory, prefix = stack.pop()
            try:
                entries = list(os.scandir(directory))
            except OSError:
                continue
            for entry in entries:
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                except OSError:
                    continue
                lowered = entry.name.lower()
                if lowered in _IGNORED_NAMES_LOWER:
                    continue
                if is_dir and lowered in _IGNORED_DIRS_LOWER:
                    continue
                rel = prefix + entry.name + ("/" if is_dir else "")
                names.append(rel)
                if is_dir:
                    stack.append((Path(entry.path), rel))
        names.sort()
        digest = hashlib.sha1(str(root).encode("utf-8", "surrogateescape"))
        digest.update("\n".join(names).encode("utf-8", "surrogateescape"))
        return digest.hexdigest()

    def _cached_read(self, path: Path, limit: int = 12000) -> str:
        """Đọc tệp có đệm; cắt theo `limit` SAU khi lấy từ đệm.

        Cắt sau là điểm quan trọng: cùng một tệp được đọc với hạn mức khác nhau
        (tài liệu chỉ dẫn dùng hạn mức co lại theo ngân sách còn lại), nên không
        thể đệm theo (tệp, limit) — phải đệm nội dung gốc rồi cắt mỗi lần.
        """
        key = self._stat_key(path)
        if key is None:
            return ""
        entry = self._file_cache.get(key)
        if entry is None:
            raw = self._read_raw(path)
            total = len(raw)
            entry = (raw[:FILE_CACHE_CHAR_CAP], total)
            self._file_cache[key] = entry
            self._metrics["file_reads"] += 1
            self._metrics["read_chars"] += total
            while len(self._file_cache) > FILE_CACHE_MAX_ENTRIES:
                self._file_cache.pop(next(iter(self._file_cache)))
        else:
            self._metrics["file_hits"] += 1
            self._metrics["reused_chars"] += len(entry[0])
        text, total = entry
        if total <= limit:
            return text
        return self._truncate(text, limit, total)

    def _candidate_index(self, root: Path, structure_fingerprint: str | None = None) -> tuple[list[Path], str]:
        """(danh sách tệp ứng viên, vân tay nội dung của chúng).

        Danh sách chỉ dựng lại khi CẤU TRÚC thư mục đổi; vân tay nội dung thì
        luôn tính mới — `stat` 1600 tệp (~ms) rẻ hơn hẳn việc đọc + chấm điểm
        chúng (~chục ms), và đó chính là khoản được tiết kiệm ở `relevant_files`.
        """
        structure_fp = structure_fingerprint if structure_fingerprint is not None else self._structure_fingerprint(root)
        cached = self._index_cache.get(str(root))
        if cached is not None and cached[0] == structure_fp:
            paths = cached[1]
            self._metrics["index_hits"] += 1
        else:
            paths = tuple(self._candidate_files(root))
            self._index_cache[str(root)] = (structure_fp, paths)
            self._metrics["index_builds"] += 1
        digest = hashlib.sha1()
        for path in paths:
            key = self._stat_key(path)
            if key is None:
                continue
            digest.update(f"{key[0]}|{key[1]}|{key[2]}\n".encode("utf-8", "surrogateescape"))
        return list(paths), digest.hexdigest()

    def _instruction_stamp(self, project: Path | None) -> str:
        digest = hashlib.sha1()
        for path in self.instruction_paths(project):
            key = self._stat_key(path)
            digest.update((f"{key}\n" if key else f"{path}|missing\n").encode("utf-8", "surrogateescape"))
        return digest.hexdigest()

    def invalidate(self, project_root: Path | None = None) -> int:
        """Xoá đệm. Gọi sau khi AI ghi tệp để chắc chắn không phục vụ bản cũ."""
        dropped = (
            len(self._file_cache) + len(self._prefix_cache)
            + len(self._index_cache) + len(self._sources_cache)
        )
        self._file_cache.clear()
        self._prefix_cache.clear()
        self._index_cache.clear()
        self._sources_cache.clear()
        return dropped

    def metrics(self) -> dict:
        return dict(self._metrics)

    def reset_metrics(self) -> None:
        for key in self._metrics:
            self._metrics[key] = 0

    def cache_report(self) -> str:
        m = self._metrics
        total = m["file_reads"] + m["file_hits"]
        rate = int(m["file_hits"] * 100 / total) if total else 0
        return (
            f"đệm: đọc lại {m['file_hits']}/{total} tệp ({rate}%) · "
            f"tiền tố ổn định dùng lại {m['prefix_hits']} lần · "
            f"danh sách tệp dùng lại {m['index_hits']} lần · "
            f"chọn nguồn dùng lại {m['sources_hits']} lần · "
            f"tiết kiệm {m['reused_chars']} ký tự đọc"
        )

    @staticmethod
    def _safe_text_file(path: Path) -> bool:
        if path.name.lower() in _IGNORED_NAMES_LOWER:
            return False
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name not in INSTRUCTION_NAMES:
            return False
        if {part.lower() for part in path.parts} & _IGNORED_DIRS_LOWER:
            return False
        if any(token in path.name.lower() for token in ("secret", "credential", "private_key")):
            return False
        return True

    @staticmethod
    def _read_raw(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            try:
                return path.read_text(encoding="latin-1")
            except OSError:
                return ""
        except OSError:
            return ""

    @staticmethod
    def _truncate(value: str, limit: int, total: int | None = None) -> str:
        """Cắt và NÓI RÕ đã cắt bao nhiêu ký tự.

        `total` là độ dài THẬT của tệp (có thể lớn hơn `value` khi `value` đã bị
        cắt theo FILE_CACHE_CHAR_CAP) — nếu lấy `len(value)` thì thông báo sẽ nói
        sai số liệu, đúng kiểu "cắt im lặng" mà dự án đã từng dính.
        """
        real = len(value) if total is None else max(int(total), len(value))
        if real <= limit:
            return value
        return value[:limit] + f"\n...[truncated: {real - limit} of {real} chars omitted]..."

    @staticmethod
    def _read_text(path: Path, limit: int = 12000) -> str:
        value = CodebaseContextService._read_raw(path)
        return CodebaseContextService._truncate(value, limit)

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
        structure_fingerprint: str | None = None,
    ) -> list[tuple[str, str]]:
        if not project_root:
            return []
        root = Path(project_root).resolve()
        if not root.is_dir():
            return []

        paths, content_fp = self._candidate_index(root, structure_fingerprint)
        cache_key = (
            str(root),
            question,
            content_fp,
            str(active_path) if active_path else "",
            len(active_text or ""),
            hashlib.sha1((active_text or "").encode("utf-8", "surrogateescape")).hexdigest()[:16],
            int(max_files),
            int(max_total_chars),
        )
        cached = self._sources_cache.get(cache_key)
        if cached is not None:
            self._metrics["sources_hits"] += 1
            self._metrics["reused_chars"] += sum(len(text) for _, text in cached)
            return list(cached)

        self._metrics["sources_builds"] += 1
        result = self._score_sources(
            root,
            question,
            paths,
            active_path=active_path,
            active_text=active_text,
            max_files=max_files,
            max_total_chars=max_total_chars,
        )
        while len(self._sources_cache) >= SOURCES_CACHE_MAX_ENTRIES:
            self._sources_cache.pop(next(iter(self._sources_cache)))
        self._sources_cache[cache_key] = tuple(result)
        return result

    def _score_sources(
        self,
        root: Path,
        question: str,
        paths: list[Path],
        *,
        active_path: Path | None,
        active_text: str,
        max_files: int,
        max_total_chars: int,
    ) -> list[tuple[str, str]]:
        selected, budget = [], max_total_chars

        if active_path and active_text:
            try:
                rel = active_path.resolve().relative_to(root).as_posix()
            except Exception:
                rel = active_path.name
            content = active_text[:12000]
            selected.append((rel + " [active]", content))
            budget -= len(content)

        tokens = self._tokens(question)
        ranked = []
        active_resolved = active_path.resolve() if active_path else None
        for path in paths:
            try:
                if active_resolved and path.resolve() == active_resolved:
                    continue
            except OSError:
                pass
            rel = path.relative_to(root).as_posix()
            score = sum(8 for token in tokens if token in rel.lower())
            text = ""
            if tokens:
                text = self._cached_read(path, 9000)
                low = text.lower()
                score += sum(min(12, low.count(token)) for token in tokens)
            elif path.name in {"project.json", "main.lua", "conf.lua"}:
                score += 6
                text = self._cached_read(path, 9000)
            if score > 0:
                if not text:
                    text = self._cached_read(path, 9000)
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

    def _stable_prefix(
        self, project: Path | None, structure_fingerprint: str = ""
    ) -> tuple[str, tuple[str, ...], int, bool]:
        """Tiền tố dùng chung cho mọi lượt trong cùng một phiên làm việc.

        Gồm: cây thư mục + briefing extension + mục lục skill + tài liệu chỉ
        dẫn. KHÔNG phụ thuộc câu hỏi ⇒ dùng lại được nguyên văn giữa các lượt,
        miễn là không tệp nào đổi (vân tay tài liệu) và cấu trúc thư mục không
        đổi. Đây là phần đắt nhất: 160k ký tự tài liệu chỉ dẫn.
        """
        key = (
            str(self.engine_root),
            str(project) if project else "",
            self._instruction_stamp(project),
            structure_fingerprint,
        )
        cached = self._prefix_cache.get(key)
        if cached is not None:
            self._metrics["prefix_hits"] += 1
            self._metrics["reused_chars"] += len(cached[0])
            return cached[0], cached[2], cached[1], True

        self._metrics["prefix_builds"] += 1
        tree, tree_count = self.project_tree(project)
        parts = ["<codebase_context>", "<project_structure>", tree, "</project_structure>"]
        briefing = self.extension_service.agent_briefing()
        if briefing:
            parts.append(briefing)
        skills = self.skill_service.index_text(project)
        if skills:
            parts.append(skills)

        instruction_sections, instruction_files = [], []
        instruction_budget = INSTRUCTION_TOTAL_BUDGET
        for path in self.instruction_paths(project):
            if instruction_budget <= 0:
                break
            text = self._cached_read(path, min(INSTRUCTION_FILE_LIMIT, instruction_budget))
            if not text:
                continue
            try:
                label = ("project/" + path.relative_to(project).as_posix()) if project and path.is_relative_to(project) else ("engine/" + path.relative_to(self.engine_root).as_posix())
            except Exception:
                label = str(path)
            instruction_files.append(label)
            instruction_sections.append(f"<instruction_document source={label!r}>\n{text}\n</instruction_document>")
            instruction_budget -= len(text)
        if instruction_sections:
            parts += ["<instruction_documents>", *instruction_sections, "</instruction_documents>"]

        text = "\n".join(parts)
        entry = (text, tree_count, tuple(instruction_files))
        while len(self._prefix_cache) >= PREFIX_CACHE_MAX_ENTRIES:
            self._prefix_cache.pop(next(iter(self._prefix_cache)))
        self._prefix_cache[key] = entry
        return text, entry[2], tree_count, False

    def build(self, project_root: Path | None, question: str, *, active_path: Path | None = None, active_text: str = "") -> ContextBundle:
        project = Path(project_root).resolve() if project_root else None
        # Tính vân tay cấu trúc MỘT lần cho cả lượt: `_stable_prefix` và
        # `_candidate_index` cùng cần nó, mỗi bên tự tính thì đi bộ thư mục hai lần.
        structure_fp = self._structure_fingerprint(project) if project and project.is_dir() else ""

        prefix, instruction_files, tree_count, prefix_hit = self._stable_prefix(project, structure_fp)
        sources = self.relevant_files(
            project,
            question,
            active_path=active_path,
            active_text=active_text,
            structure_fingerprint=structure_fp,
        )

        parts = [prefix]
        if sources:
            parts += ["<relevant_sources>"] + [
                f"<source_file path={name!r}>\n{text}\n</source_file>" for name, text in sources
            ] + ["</relevant_sources>"]
        parts.append("</codebase_context>")
        combined = "\n".join(parts)
        return ContextBundle(
            text=combined,
            tree_entries=tree_count,
            instruction_files=list(instruction_files),
            source_files=[name for name, _ in sources],
            total_chars=len(combined),
            cache_hit=prefix_hit,
            stable_chars=len(prefix) if prefix_hit else 0,
            metrics=self.metrics(),
        )
