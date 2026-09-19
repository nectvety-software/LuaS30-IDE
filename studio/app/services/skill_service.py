"""skill_service.py — hệ thống SKILLS cho agent Lua S30+ MRE VXP.

Một skill là một tệp hướng dẫn có frontmatter, KHÁM PHÁ ĐƯỢC và NẠP THEO
YÊU CẦU (kiểu Cline/Claude skills) — khác với các tệp luật thường trực
SKILLS.md/SKILL.md/PROMPT.md luôn được nhét vào mọi system prompt:

    skills/<tên-skill>/SKILL.md      (thư mục — khuyến nghị)
    skills/<tên-skill>.md            (tệp đơn)

được quét từ:

    <project>/skills, <project>/.luas30/skills      nguồn "project"
    <engine>/doc/ai/skills, <engine>/skills         nguồn "engine"
    <extension>/skills                              nguồn "extension:<id>"

Frontmatter tối thiểu:

    ---
    name: problems-autofix
    description: Đọc bảng PROBLEMS, phân tích và tự sửa lỗi Lua trong dự án
    ---

Thiếu frontmatter thì lấy tên theo thư mục/mục `# ` đầu tiên và mô tả theo
đoạn văn đầu tiên của thân. Agent CHỈ thấy mục lục (name + description) trong
prompt; toàn văn nạp qua tool `skill` (op list|read) khi thật cần — nhờ vậy
luật dài không bị trả phí token ở mọi lượt hội thoại.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.services.extension_service import ExtensionService

SKILL_FILENAME = "SKILL.md"
PROJECT_SKILL_DIRS = ("skills", ".luas30/skills")
ENGINE_SKILL_DIRS = ("doc/ai/skills", "skills")
EXTENSION_SKILL_DIRS = ("skills",)
MAX_SKILL_CHARS = 48000


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    source: str          # project | engine | extension:<id>
    path: Path

    def index_line(self) -> str:
        return f"- {self.name} ({self.source}): {self.description}"


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Tách khối `--- ... ---` đầu tệp thành dict; trả (metadata, thân)."""
    value = str(text or "").lstrip("\ufeff").replace("\r\n", "\n")
    if not value.startswith("---"):
        return {}, value
    lines = value.split("\n")
    meta: dict[str, str] = {}
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            body = "\n".join(lines[index + 1:]).strip()
            return meta, body
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if match:
            meta[match.group(1).strip().lower()] = match.group(2).strip().strip("\"'")
    return {}, value  # khối mở không đóng — coi như không có frontmatter


def _fallback_description(body: str) -> str:
    for paragraph in re.split(r"\n\s*\n", str(body or "")):
        cleaned = " ".join(paragraph.split())
        cleaned = re.sub(r"^#+\s*", "", cleaned)
        cleaned = re.sub(r"[*_`>]", "", cleaned).strip()
        if cleaned and not cleaned.startswith(("|", "-")):
            return cleaned[:220]
    return "(no description)"


class SkillService:
    def __init__(self, engine_root: Path) -> None:
        self.engine_root = Path(engine_root).resolve()
        self.extension_service = ExtensionService(self.engine_root)

    # --------------------------------------------------------- khám phá
    def _scan_dir(self, base: Path, source: str) -> list[Skill]:
        found: list[Skill] = []
        if not base.is_dir():
            return found
        entries: list[Path] = []
        try:
            entries = sorted(base.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            return found
        for entry in entries:
            candidates: list[Path] = []
            if entry.is_dir():
                candidates.append(entry / SKILL_FILENAME)
            elif entry.suffix.lower() == ".md":
                candidates.append(entry)
            for file in candidates:
                if not file.is_file():
                    continue
                try:
                    text = file.read_text(encoding="utf-8-sig")
                except (OSError, UnicodeDecodeError):
                    continue
                meta, body = parse_front_matter(text)
                name = meta.get("name") or (
                    entry.stem if entry.is_file() else entry.name
                )
                description = meta.get("description") or _fallback_description(body)
                found.append(Skill(name=name.strip(), description=description,
                                   source=source, path=file))
        return found

    def discover(self, project_root: Path | None = None) -> list[Skill]:
        skills: list[Skill] = []
        if project_root:
            root = Path(project_root).resolve()
            for rel in PROJECT_SKILL_DIRS:
                skills.extend(self._scan_dir(root / rel, "project"))
        for rel in ENGINE_SKILL_DIRS:
            skills.extend(self._scan_dir(self.engine_root / rel, "engine"))
        for manifest in self.extension_service.discover():
            for rel in EXTENSION_SKILL_DIRS:
                skills.extend(self._scan_dir(
                    manifest.root / rel, f"extension:{manifest.id}"))
            # Tài liệu ở GỐC extension (SKILLS.md/SKILL.md/PROMPT.md) trước đây
            # bị nạp toàn văn vào mọi system prompt — giờ cũng là skill theo yêu
            # cầu, đặt tên theo extension để agent đọc được bằng tool `skill`.
            for doc in manifest.instruction_docs():
                try:
                    text = doc.read_text(encoding="utf-8-sig")
                except (OSError, UnicodeDecodeError):
                    continue
                meta, body = parse_front_matter(text)
                skills.append(Skill(
                    name=meta.get("name") or f"{manifest.id}:{doc.stem.lower()}",
                    description=meta.get("description")
                    or _fallback_description(body),
                    source=f"extension:{manifest.id}",
                    path=doc,
                ))
        # trùng tên: lượt khám phá TRƯỚC thắng (project > engine > extension)
        result, seen = [], set()
        for skill in skills:
            key = skill.name.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(skill)
        return result

    def by_name(self, name: str, project_root: Path | None = None) -> Skill | None:
        wanted = str(name or "").strip().lower()
        if not wanted:
            return None
        for skill in self.discover(project_root):
            if skill.name.lower() == wanted:
                return skill
        return None

    # --------------------------------------------------------- prompt
    def index_text(self, project_root: Path | None = None) -> str:
        """Mục lục skill cho system prompt — chỉ name + description."""
        skills = self.discover(project_root)
        if not skills:
            return ""
        lines = [skill.index_line() for skill in skills]
        return (
            "<agent_skills>\n"
            "Kỹ năng nạp theo yêu cầu — toàn văn KHÔNG nằm ở đây. Khi một skill "
            "khớp việc đang làm, nạp bằng tool "
            '{"tool":"skill","args":{"op":"read","name":"<tên>"}} rồi làm đúng '
            "quy trình của nó; op list để khám phá lại.\n"
            + "\n".join(lines) + "\n</agent_skills>"
        )

    # --------------------------------------------------------- tool
    def execute(self, project_root: Path | None, args: dict) -> str:
        """Handler tool `skill`: op list | read (args.name)."""
        op = str(args.get("op") or "list").strip().lower()
        skills = self.discover(project_root)
        if op == "list":
            if not skills:
                return ("SKILLS: chưa có skill nào. Đặt tệp SKILL.md có "
                        "frontmatter vào skills/<tên>/ của project, doc/ai/skills/ "
                        "của IDE, hoặc skills/ của extension đã cài.")
            return "SKILLS\n" + "\n".join(skill.index_line() for skill in skills)
        if op == "read":
            wanted = str(args.get("name") or "").strip().lower()
            if not wanted:
                raise ValueError("skill read cần args.name.")
            for skill in skills:
                if skill.name.lower() != wanted:
                    continue
                try:
                    text = skill.path.read_text(encoding="utf-8-sig")
                except (OSError, UnicodeDecodeError) as exc:
                    raise ValueError(f"Không đọc được skill '{skill.name}': {exc}") from exc
                if len(text) > MAX_SKILL_CHARS:
                    text = text[:MAX_SKILL_CHARS] + "\n...[skill truncated]..."
                return (f"SKILL {skill.name} (nguồn {skill.source})\n"
                        f"Đường dẫn: {skill.path}\n\n{text}")
            available = ", ".join(s.name for s in skills) or "(không có)"
            raise ValueError(f"Không tìm thấy skill '{wanted}'. Đang có: {available}")
        raise ValueError(f"Unsupported skill op: {op}")
