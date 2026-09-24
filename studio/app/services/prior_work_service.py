"""Danh mục các dự án LuaS30 NGƯỜI DÙNG ĐÃ LÀM — bằng chứng để agent gợi ý.

Vì sao lớp IDE phải làm việc này
--------------------------------
`agent_protocol_prompt` khoá agent trong project đang mở (`project_scope_note`:
"every read/grep/glob path is relative to the OPEN project root and stays inside
it"). Nghĩa là agent **không** `read`/`glob` được sang
`Documents\\LuaS30 Projects\\<dự án khác>` — dù đó chính là nơi chứa bằng chứng
đáng tin nhất về gu làm game của người dùng.

Nên IDE quét hộ: đọc `project.json` + `README.md` + `conf.lua` + `src/` của từng
dự án anh em, rút ra genre / phong cách / thông số target / số màn / mô-đun, nén
thành một danh mục ngắn, và nhét vào system prompt dưới dạng `<prior_work>`.
Agent đọc danh mục rồi gợi ý — gợi ý **có căn cứ vào việc người dùng ĐÃ làm**,
không phải phỏng đoán chung chung kiểu "bạn có thể làm platformer".

Không phải suy diễn
-------------------
Genre/phong cách ở đây không do model đoán: chúng được chấm điểm bằng từ khoá
trên chính README của người dùng (các README này có hẳn mục `## Style` và
`## Gameplay`). Mỗi dòng danh mục giữ lại `evidence` — câu trích nguyên văn đã
dùng để chấm — để agent trích dẫn được và để người đọc kiểm lại được.

Đệm theo VÂN TAY NỘI DUNG
-------------------------
`build()` chạy ở MỌI lượt. Không đệm thì mỗi lượt lại mở ~4 tệp × N dự án.
Khoá đệm là `(đường dẫn, mtime_ns, size)` — sửa tệp là vân tay đổi, đệm tự vô
hiệu. Cùng nguyên tắc với `codebase_context_service.py`.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.core import paths
from app.services.ai_agent_protocol import PROJECT_OPS

# Tệp bằng chứng, theo thứ tự ưu tiên đọc. Chỉ đọc tệp CÓ THẬT.
# `main.lua` nằm trong danh sách vì nhiều dự án KHÔNG có README nhưng lại ghi rõ
# mục đích ngay ở khối comment đầu tệp (ví dụ `Fumble Run`: "Shift Bound: Kinetic
# Escape", "240x320, 15fps, 1MB RAM", "Theme: Notebook Doodle Art"). Bỏ nó đi thì
# những dự án đó rơi vào genre "khác" một cách vô cớ.
EVIDENCE_FILES = ("project.json", "README.md", "CHANGELOG.md", "conf.lua", "main.lua")
README_CHAR_LIMIT = 24000
CONFIG_CHAR_LIMIT = 4000
MAIN_LUA_CHAR_LIMIT = 8000   # chỉ để chấm điểm + lấy header; không hiển thị toàn văn

MAX_PROJECTS = 80          # trần cứng số dự án đưa vào danh mục
MAX_CATALOG_CHARS = 6000   # trần khối <prior_work> — vượt là tự cắt, có ghi rõ
MAX_EVIDENCE = 3           # số câu trích giữ lại mỗi dự án
MAX_EVIDENCE_ITEM = 200
MAX_MODULES = 12
MAX_SCREENS = 10

# Thư mục không bao giờ là dự án (rác build, VCS, cache...).
SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", "node_modules", "build", "release",
    "dist", ".venv", "venv", ".luas30", ".idea", ".vscode", "cache", "backups",
}

# Dấu hiệu "đây là một dự án" — thiếu cả ba thì bỏ qua (ví dụ `hello/` chỉ có build/).
PROJECT_MARKERS = ("project.json", "main.lua", "conf.lua")

# --- Chấm điểm genre ------------------------------------------------------
# Cộng điểm theo số từ khoá khớp trong toàn bộ bằng chứng; genre điểm cao nhất
# thắng, hoà thì lấy theo thứ tự bảng (cụ thể trước, chung sau). Từ khoá để ở
# dạng chữ thường, so trên văn bản đã hạ chữ thường.
GENRE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cardgame", (
        "card game", "cards", "poker", "tien len", "tiến lên", "shedding",
        "trick", "deck", "hand", "bài", "đánh bài", "tứ quý",
    )),
    ("farming-sim", (
        "farming", "farm sim", "crop", "seed", "harvest", "watering",
        "season", "quest", "nông trại", "trồng", "thu hoạch",
    )),
    ("first-person-shooter", (
        "first-person", "raycast", "ink ops", "rifle", "ammo", "reload",
        "splatter", "bắn", "shooter",
    )),
    ("dungeon-crawler", (
        "dungeon", "catacomb", "relic", "top-down", "maze", "sword",
        "guard", "acid", "hầm ngục",
    )),
    ("traffic-puzzle", (
        "puzzle", "match-3", "match3", "unblock", "solvable", "combo",
        "jam", "giải đố",
    )),
    ("platformer", (
        "platform", "jump", "dash", "slash", "wave", "chạy nhảy",
    )),
    ("base-builder", (
        "resource-management", "resource management", "gather", "supply",
        "upgrade", "survival", "base", "factory", "quản lý",
    )),
    ("pixel-editor", (
        "pixel editor", "paint", "brush", "palette", "canvas", "eraser",
        "eyedropper", "gif89a", "rgb565",
    )),
    ("device-utility", (
        "chat", "capture", "probe", "scan", "file", "notepad", "memory",
        "device_info", "soạn thảo", "quét bộ nhớ",
    )),
    ("template", (
        "template", "starter", "how to play", "included screens", "khung sườn",
    )),
)

# --- Chấm điểm phong cách MỸ THUẬT ----------------------------------------
# Cố ý KHÔNG có mục "procedural": đó là KỸ THUẬT, không phải phong cách, và gần
# như mọi dự án đều dùng. Trộn nó vào đây làm bảng xếp hạng phong cách vô nghĩa —
# "procedural (14)" luôn đứng đầu và che mất tín hiệu thật (notebook-doodle (9),
# pop-art (4)). Kỹ thuật được nêu MỘT LẦN ở đầu khối thay vì lặp 18 lần.
STYLE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pop-art", (
        "pop art", "pop-art", "halftone", "ben-day", "benday", "starburst",
        "magenta", "comic outline", "pow",
    )),
    ("notebook-doodle", (
        "notebook", "doodle", "ballpoint", "bút bi", "pencil", "bút chì",
        "graph paper", "hand-drawn", "hand drawn", "paper", "vở",
    )),
    ("comic-noir", (
        "comic-noir", "noir", "silhouette", "gothic", "parchment",
    )),
    ("pixel-art", (
        "pixel art", "pixel-art", "pixel",
    )),
)

# Kỹ thuật dùng chung — tách khỏi phong cách để không làm loãng bảng xếp hạng.
TECHNIQUE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("procedural-no-bitmap", (
        "procedural", "primitives", "engine.rect", "no bitmap", "no png",
        "không bitmap", "không dùng png", "rect", "khong can asset",
    )),
)

GENRE_FALLBACK = "khác"

# Mục README dùng để trích bằng chứng style / nội dung.
STYLE_HEADINGS = ("style", "visual style", "visual", "phong cách")
GAMEPLAY_HEADINGS = ("gameplay", "core loop", "how to play", "nội dung", "lối chơi")
SCREEN_HEADINGS = ("screens", "included screens", "màn hình")
TARGET_HEADINGS = ("target", "targets")


def _read_text(path: Path, limit: int) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")[:limit]
    except OSError:
        return ""


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _split_sections(text: str) -> dict[str, str]:
    """Tách `## Tiêu đề` → thân. Dùng cho README để lấy đúng mục Style/Gameplay."""
    sections: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []
    for raw in str(text or "").replace("\r\n", "\n").split("\n"):
        match = re.match(r"^#{1,3}\s+(.*)$", raw)
        if match:
            if current is not None:
                sections[current] = "\n".join(buffer).strip()
            current = match.group(1).strip().lower()
            buffer = []
            continue
        if current is not None:
            buffer.append(raw)
    if current is not None:
        sections[current] = "\n".join(buffer).strip()
    return sections


def _first_heading(text: str) -> str:
    for raw in str(text or "").replace("\r\n", "\n").split("\n"):
        match = re.match(r"^#\s+(.*)$", raw)
        if match:
            return match.group(1).strip()
    return ""


def _first_sentence(text: str, limit: int = MAX_EVIDENCE_ITEM) -> str:
    """Câu đầu tiên đủ nghĩa, đã gộp khoảng trắng — để trích làm bằng chứng."""
    flat = " ".join(str(text or "").split())
    flat = re.sub(r"^[-*+]\s+", "", flat)
    if not flat:
        return ""
    for stop in (". ", "。", "! "):
        head = flat.split(stop, 1)[0]
        if 12 <= len(head) < len(flat):
            flat = head + "."
            break
    return flat[:limit].strip()


def _section_text(sections: dict[str, str], headings: tuple[str, ...]) -> str:
    for name in headings:
        for key, body in sections.items():
            if key == name or key.startswith(name):
                if body:
                    return body
    return ""


def _parse_conf_lua(text: str) -> dict[str, str]:
    """Rút `width`/`height`/`fps`/`title` từ `conf.lua` (cú pháp `key = value`).

    Cần thiết vì có dự án chỉ khai báo target trong `conf.lua`, không trong
    `project.json` (ví dụ `DoodleNotebookHero`), và README thì không nhắc
    "240x320" lần nào — thiếu đường này thì dự án hiện ra không có thông số nào.
    """
    found: dict[str, str] = {}
    for key in ("width", "height", "fps", "title"):
        match = re.search(
            rf"^\s*{key}\s*=\s*(\"[^\"]*\"|'[^']*'|-?\d+)",
            text, re.MULTILINE,
        )
        if not match:
            continue
        found[key] = match.group(1).strip().strip("\"'")
    return found


def _lua_header_comment(text: str, limit: int = 4) -> list[str]:
    """Các dòng comment ở ĐẦU `main.lua` — thường là mô tả dự án do tác giả viết.

    Chỉ lấy khối `--` liền mạch từ dòng đầu; dừng ngay khi gặp dòng không phải
    comment. Nhờ vậy không nhặt bừa comment rải rác trong thân code.
    """
    lines: list[str] = []
    for raw in str(text or "").replace("\r\n", "\n").split("\n"):
        stripped = raw.strip()
        if not stripped:
            if lines:
                break
            continue
        if not stripped.startswith("--"):
            break
        body = stripped.lstrip("-").strip()
        if not body:
            continue
        # Bỏ token tên tệp ở đầu dòng — một số dự án mở đầu bằng
        # `-- main.lua -- BIỂN MỰC (Ink Seas) ...`, và "main.lua" chỉ là rác.
        body = re.sub(r"^\S+\.lua\b\s*[-—:]*\s*", "", body).strip()
        if not body:
            continue
        lines.append(body[:MAX_EVIDENCE_ITEM])
        if len(lines) >= limit:
            break
    return lines


def _clean_title(value: str) -> str:
    """Bỏ đuôi trang trí trong tiêu đề README: 'MemScan Notebook — LuaS30-IDE'."""
    text = " ".join(str(value or "").split())
    for sep in (" — ", " – ", " - ", " · ", " | "):
        if sep in text:
            head = text.split(sep, 1)[0].strip()
            if len(head) >= 4:
                text = head
                break
    return text.strip(" :#")[:80]


def _score(text: str, rules: tuple[tuple[str, tuple[str, ...]], ...]) -> list[tuple[str, int, str]]:
    """Trả [(nhãn, điểm, từ khoá khớp), ...] đã sắp giảm dần theo điểm."""
    scored: list[tuple[str, int, str]] = []
    for label, keywords in rules:
        hits = [kw for kw in keywords if kw in text]
        if hits:
            scored.append((label, len(hits), hits[0]))
    scored.sort(key=lambda item: -item[1])
    return scored


def _clean_list(items: list[str], limit: int) -> tuple[str, ...]:
    seen: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if value and value not in seen:
            seen.append(value)
        if len(seen) >= limit:
            break
    return tuple(seen)


@dataclass
class PriorProject:
    """Một dự án anh em, đã rút gọn thành thứ đáng đưa vào prompt."""

    folder: str
    title: str
    genre: str
    styles: tuple[str, ...]
    version: str
    screen: str
    fps: str
    ram_kb: str
    appid: str
    modules: tuple[str, ...] = ()
    screens: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    level_count: str = ""
    has_sfx: bool = False
    procedural: bool = False
    modified: str = ""
    path: Path | None = None

    def spec(self) -> str:
        """Chuỗi thông số target, chỉ gồm phần thật sự có dữ liệu."""
        parts = [p for p in (self.screen, self.fps, self.ram_kb) if p]
        return " · ".join(parts)

    def line(self) -> str:
        """Một dòng cho `<prior_work>` — càng ít token càng tốt, nhưng phải đủ ý."""
        bits: list[str] = [f"- {self.folder}"]
        if self.title and self.title.lower() != self.folder.lower():
            bits.append(f'"{self.title}"')
        bits.append(self.genre)
        if self.styles:
            bits.append("/".join(self.styles[:2]))
        spec = self.spec()
        if spec:
            bits.append(spec)
        if self.level_count:
            bits.append(self.level_count)
        if self.has_sfx:
            bits.append("sfx")
        if self.modules:
            bits.append(f"{len(self.modules)} mô-đun src/")
        head = " · ".join(bits)
        if self.evidence:
            head += f"\n    style: {self.evidence[0]}"
        return head

    def detail(self) -> str:
        """Toàn văn rút gọn cho tool `projects` op=show."""
        lines = [
            f"PROJECT {self.folder}",
            f"Tên: {self.title or self.folder}",
            f"Genre (suy từ README): {self.genre}",
            f"Phong cách: {', '.join(self.styles) or '(không rõ)'}",
        ]
        if self.version:
            lines.append(f"Phiên bản: {self.version}")
        if self.appid:
            lines.append(f"AppID: {self.appid}")
        spec = self.spec()
        if spec:
            lines.append(f"Target: {spec}")
        if self.level_count:
            lines.append(f"Nội dung: {self.level_count}")
        if self.screens:
            lines.append("Màn hình: " + ", ".join(self.screens))
        if self.modules:
            lines.append("Mô-đun src/: " + ", ".join(self.modules))
        if self.has_sfx:
            lines.append("Có assets/sfx (âm thanh thật).")
        if self.procedural:
            lines.append("Đồ họa procedural (rect/line/text, không bitmap runtime).")
        if self.modified:
            lines.append(f"Sửa lần cuối: {self.modified}")
        if self.evidence:
            lines.append("Trích bằng chứng:")
            lines.extend(f"  - {item}" for item in self.evidence)
        if self.path:
            lines.append(f"Đường dẫn: {self.path}")
        lines.append(
            "LƯU Ý: agent chỉ đọc được project ĐANG MỞ. Đây là dữ liệu tham khảo "
            "do IDE quét hộ, KHÔNG mở trực tiếp được."
        )
        return "\n".join(lines)


class PriorWorkService:
    """Quét `projects_root()` và nén thành danh mục + khối prompt."""

    def __init__(self, root: Path | None = None) -> None:
        self._root_override = Path(root) if root else None
        self._file_cache: dict[tuple[str, int, int], str] = {}
        self._catalog_cache: dict[str, tuple[tuple, tuple[PriorProject, ...]]] = {}

    # ------------------------------------------------------------ cấu hình
    def root(self) -> Path:
        return self._root_override if self._root_override else paths.projects_root()

    # ------------------------------------------------------------ đọc tệp
    def _cached_read(self, path: Path, limit: int) -> str:
        try:
            stat = path.stat()
        except OSError:
            return ""
        key = (str(path), stat.st_mtime_ns, stat.st_size)
        cached = self._file_cache.get(key)
        if cached is not None:
            return cached[:limit]
        text = _read_text(path, limit)
        self._file_cache[key] = text
        if len(self._file_cache) > 600:
            for stale in list(self._file_cache)[:200]:
                self._file_cache.pop(stale, None)
        return text[:limit]

    def _fingerprint(self, entries: list[Path]) -> tuple:
        """Vân tay cấu trúc: TÊN mục + (mtime, size) từng tệp bằng chứng.

        Không dùng mtime của THƯ MỤC: NTFS ghi metadata thư mục trễ, nên thêm dự
        án mới có thể không đổi vân tay và danh mục phục vụ bản cũ (đã mắc ở
        `codebase_context_service`). Liệt kê tên mục thì không có độ trễ đó.
        """
        marks: list[tuple] = []
        for entry in entries:
            marks.append(("dir", entry.name))
            for name in EVIDENCE_FILES:
                file = entry / name
                try:
                    stat = file.stat()
                except OSError:
                    continue
                marks.append((name, stat.st_mtime_ns, stat.st_size))
        return tuple(marks)

    # ------------------------------------------------------------ quét
    def _project_dirs(self) -> list[Path]:
        base = self.root()
        if not base.is_dir():
            return []
        try:
            entries = sorted(base.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            return []
        found: list[Path] = []
        for entry in entries:
            try:
                if not entry.is_dir():
                    continue
            except OSError:
                continue
            if entry.name.startswith(".") or entry.name.lower() in SKIP_DIRS:
                continue
            if any((entry / marker).is_file() for marker in PROJECT_MARKERS):
                found.append(entry)
        return found

    def _build_one(self, entry: Path) -> PriorProject | None:
        meta = _read_json(entry / "project.json")
        readme = self._cached_read(entry / "README.md", README_CHAR_LIMIT)
        changelog = self._cached_read(entry / "CHANGELOG.md", 6000)
        conf = self._cached_read(entry / "conf.lua", CONFIG_CHAR_LIMIT)
        main_lua = self._cached_read(entry / "main.lua", MAIN_LUA_CHAR_LIMIT)
        conf_values = _parse_conf_lua(conf)
        header = _lua_header_comment(main_lua)
        sections = _split_sections(readme)

        # Thứ tự ưu tiên tiêu đề: `display_name`/`title` (người viết đặt) → tiêu đề
        # `# ` của README (cũng do người viết) → `name` (thường chỉ là tên thư mục do
        # wizard sinh, ví dụ project.json của `cardgames` ghi name = "cardgames"
        # trong khi README mở đầu bằng "Tien Len Mien Nam").
        title = _clean_title(str(
            meta.get("display_name") or meta.get("title") or ""
        ))
        if not title:
            title = _clean_title(_first_heading(readme))
        if not title:
            title = _clean_title(str(meta.get("name") or conf_values.get("title") or ""))
        if not title:
            title = entry.name

        version = str(meta.get("app_version") or meta.get("version") or "").strip()
        appid = str(meta.get("appid") or "").strip()

        width = meta.get("screen_width") or conf_values.get("width")
        height = meta.get("screen_height") or conf_values.get("height")
        if width and height:
            screen = f"{width}x{height}"
        else:
            resolution = str(meta.get("resolution") or "").strip()
            match = re.search(r"(\d{2,4})\s*[x×]\s*(\d{2,4})", resolution or readme + main_lua)
            screen = f"{match.group(1)}x{match.group(2)}" if match else ""

        fps_value = meta.get("fps") or meta.get("target_fps") or conf_values.get("fps")
        fps = f"{fps_value} FPS" if fps_value else ""
        if not fps:
            match = re.search(r"(\d{1,3})\s*FPS", readme + main_lua, re.I)
            fps = f"{match.group(1)} FPS" if match else ""

        ram = meta.get("ram_kb") or meta.get("target_ram_kb")
        ram_kb = f"{ram} KB" if ram else ""
        if not ram_kb:
            match = re.search(r"(\d{3,5})\s*KB", readme + main_lua, re.I)
            ram_kb = f"{match.group(1)} KB" if match else ""
        if not ram_kb:
            # "1MB RAM" trong comment main.lua của Fumble Run.
            match = re.search(r"(\d+)\s*MB\s*RAM", readme + main_lua, re.I)
            ram_kb = f"{int(match.group(1)) * 1024} KB" if match else ""

        modules: list[str] = []
        src = entry / "src"
        if src.is_dir():
            try:
                modules = sorted(p.stem for p in src.glob("*.lua") if p.is_file())
            except OSError:
                modules = []

        # Văn bản để chấm điểm: README + changelog + conf + main.lua + tên + mô-đun.
        haystack = "\n".join((
            readme, changelog, conf, main_lua, title, entry.name, " ".join(modules),
        )).lower()

        genre_hits = _score(haystack, GENRE_RULES)
        genre = genre_hits[0][0] if genre_hits else GENRE_FALLBACK
        style_hits = _score(haystack, STYLE_RULES)
        styles = tuple(label for label, _count, _kw in style_hits[:3])
        procedural = bool(_score(haystack, TECHNIQUE_RULES))

        # Bằng chứng: câu trích từ mục Style/Gameplay của README, rồi tới khối
        # comment đầu `main.lua` (mô tả do tác giả viết), rồi lý do chấm genre.
        evidence: list[str] = []
        for body in (
            _section_text(sections, STYLE_HEADINGS),
            _section_text(sections, GAMEPLAY_HEADINGS),
        ):
            sentence = _first_sentence(body)
            if sentence:
                evidence.append(sentence)
        if not evidence and header:
            evidence.append(header[0])
        if genre_hits:
            label, _count, keyword = genre_hits[0]
            evidence.append(f'genre "{label}" — từ khoá khớp: "{keyword}"')

        screens: list[str] = []
        screen_body = _section_text(sections, SCREEN_HEADINGS)
        if screen_body:
            screens = [
                re.sub(r"^[-*+]\s*", "", " ".join(line.split()))[:60]
                for line in screen_body.split("\n")
                if line.strip()
            ]

        level_count = ""
        match = re.search(r"\*\*(\d+)\s+(?:levels|màn|stages|màn chơi)\*\*", readme)
        if not match:
            match = re.search(r"(\d+)\s+(?:levels|màn|stages|màn chơi)\b", readme, re.I)
        if match:
            level_count = f"{match.group(1)} màn"

        has_sfx = (entry / "assets" / "sfx").is_dir()
        try:
            modified = datetime.fromtimestamp(entry.stat().st_mtime).strftime("%Y-%m-%d")
        except OSError:
            modified = ""

        return PriorProject(
            folder=entry.name,
            title=title,
            genre=genre,
            styles=styles,
            version=version,
            screen=screen,
            fps=fps,
            ram_kb=ram_kb,
            appid=appid,
            modules=_clean_list(modules, MAX_MODULES),
            screens=_clean_list(screens, MAX_SCREENS),
            evidence=_clean_list(evidence, MAX_EVIDENCE),
            level_count=level_count,
            has_sfx=has_sfx,
            procedural=procedural,
            modified=modified,
            path=entry,
        )

    def catalog(self, current: Path | None = None) -> list[PriorProject]:
        """Danh mục đã sắp xếp (mới nhất trước), bỏ qua project đang mở."""
        entries = self._project_dirs()
        fingerprint = self._fingerprint(entries)
        key = str(self.root())
        cached = self._catalog_cache.get(key)
        if cached is not None and cached[0] == fingerprint:
            projects = list(cached[1])
        else:
            projects = []
            for entry in entries:
                if len(projects) >= MAX_PROJECTS:
                    break
                built = self._build_one(entry)
                if built is not None:
                    projects.append(built)
            self._catalog_cache[key] = (fingerprint, tuple(projects))
        current_name = ""
        if current:
            try:
                current_name = Path(current).resolve().name.lower()
            except OSError:
                current_name = Path(current).name.lower()
        if current_name:
            projects = [p for p in projects if p.folder.lower() != current_name]
        projects.sort(key=lambda p: p.modified, reverse=True)
        return projects

    # ------------------------------------------------------------ tổng hợp
    def style_profile(self, current: Path | None = None) -> list[tuple[str, int]]:
        """[(phong cách, số dự án)] giảm dần — 'gu' thật của người dùng."""
        counter: Counter[str] = Counter()
        for project in self.catalog(current):
            for style in project.styles[:2]:
                counter[style] += 1
        return counter.most_common()

    def genre_profile(self, current: Path | None = None) -> list[tuple[str, int]]:
        counter: Counter[str] = Counter()
        for project in self.catalog(current):
            counter[project.genre] += 1
        return counter.most_common()

    # ------------------------------------------------------------ prompt
    def prompt_block(self, current: Path | None = None, full: bool = True) -> str:
        """Khối `<prior_work>` cho system prompt. Rỗng khi không có gì để nói.

        `full=False` phát bản GỌN: chỉ tổng hợp gu + câu chỉ đường tới tool
        `projects`. Vẫn đủ để agent biết danh mục tồn tại và tự lấy khi cần, nhưng
        không tốn ~1.2k token ở mỗi lượt sửa lỗi — lượt đó không liên quan gì tới
        việc chọn làm game gì.
        """
        projects = self.catalog(current)
        if not projects:
            return ""
        styles = self.style_profile(current)
        genres = self.genre_profile(current)
        lines = [
            "<prior_work>",
            f"{len(projects)} dự án LuaS30 khác người dùng đã tự làm, trong "
            f"{self.root()}. Agent KHÔNG đọc trực tiếp được (bị khoá trong project "
            "đang mở) — IDE quét hộ.",
        ]
        if styles:
            lines.append(
                "PHONG CÁCH LẶP LẠI: "
                + ", ".join(f"{name} ({count} dự án)" for name, count in styles[:5])
            )
        if genres:
            lines.append(
                "GENRE ĐÃ LÀM: "
                + ", ".join(f"{name} ({count})" for name, count in genres[:6])
            )
        if not full:
            lines.append(
                "Danh mục đầy đủ bị lược ở lượt này để tiết kiệm ngữ cảnh. Khi người "
                "dùng hỏi nên làm gì / theo phong cách nào, lấy ngay bằng "
                '{"tool":"projects","args":{"op":"list"}} (hoặc op=show + args.name '
                "để xem chi tiết một dự án). Đừng gợi ý mà không đọc danh mục trước."
            )
            lines.append("</prior_work>")
            return "\n".join(lines)
        lines.append(
            "Dùng làm bằng chứng về gu và mức độ thành thạo, rồi gợi ý cụ thể; chi "
            "tiết một dự án thì gọi tool "
            '{"tool":"projects","args":{"op":"show","name":"<thư mục>"}}.'
        )
        lines.append("")
        lines.extend(project.line() for project in projects)
        procedural = sum(1 for project in projects if project.procedural)
        if procedural:
            lines.append("")
            lines.append(
                f"KỸ THUẬT CHUNG: {procedural}/{len(projects)} dự án vẽ procedural "
                "(engine.rect/line/text, không bitmap runtime) — đây là cách làm quen "
                "thuộc của người dùng, không phải một phong cách riêng."
            )
        lines.append(
            "Đây là dữ liệu QUÁ KHỨ để tham khảo, KHÔNG phải yêu cầu mới. Không "
            "được bịa ra dự án không có trong danh sách này."
        )
        lines.append("</prior_work>")
        block = "\n".join(lines)
        if len(block) > MAX_CATALOG_CHARS:
            block = (
                block[:MAX_CATALOG_CHARS]
                + f"\n...[danh mục đã bị cắt, còn {len(projects)} dự án — "
                  "gọi tool `projects` op=list để xem phần còn lại]..."
                  "\n</prior_work>"
            )
        return block

    # ------------------------------------------------------------ tool
    def execute(self, current: Path | None, args: dict) -> str:
        """Handler tool `projects`: op list | show | styles."""
        op = str(args.get("op") or "list").strip().lower()
        if op not in PROJECT_OPS:
            raise ValueError(
                f"projects op không hỗ trợ: {op}. Hợp lệ: {', '.join(PROJECT_OPS)}"
            )
        projects = self.catalog(current)
        if op == "styles":
            if not projects:
                return "PRIOR WORK: chưa có dự án nào khác trong " + str(self.root())
            styles = self.style_profile(current)
            genres = self.genre_profile(current)
            lines = [
                f"GU LÀM GAME — {len(projects)} dự án trong {self.root()}",
                "Phong cách (số dự án): "
                + ", ".join(f"{n} ({c})" for n, c in styles),
                "Genre (số dự án): "
                + ", ".join(f"{n} ({c})" for n, c in genres),
                "Thông số chung: "
                + ", ".join(sorted({
                    p.spec() for p in projects if p.spec()
                })[:4]),
            ]
            return "\n".join(lines)
        if op == "list":
            if not projects:
                return (
                    "PRIOR WORK: chưa có dự án nào khác trong "
                    + str(self.root())
                    + " (hoặc thư mục chưa tồn tại)."
                )
            return (
                f"PRIOR WORK — {len(projects)} dự án trong {self.root()}\n"
                + "\n".join(project.line() for project in projects)
            )
        # op == "show"
        wanted = str(args.get("name") or "").strip().lower()
        if not wanted:
            raise ValueError("projects op=show cần args.name (tên thư mục dự án).")
        for project in projects:
            if project.folder.lower() == wanted or project.title.lower() == wanted:
                return project.detail()
        available = ", ".join(p.folder for p in projects) or "(không có)"
        raise ValueError(f"Không tìm thấy dự án '{wanted}'. Đang có: {available}")

    def summary_text(self, current: Path | None = None) -> str:
        """Một dòng cho activity feed. RỖNG khi không có gì — để chỗ gọi tự bỏ qua.

        Không trả câu "chưa có dự án nào": một dòng như thế nằm lẫn trong feed trông
        y hệt một dòng thật, và người dùng không phân biệt được "quét ra 0 dự án"
        với "tính năng không chạy".
        """
        projects = self.catalog(current)
        if not projects:
            return ""
        styles = self.style_profile(current)
        return (
            f"{len(projects)} dự án anh em · phong cách nổi bật: "
            + ", ".join(name for name, _count in styles[:3])
        )
