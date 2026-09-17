"""
asset_import.py — Nhập tài nguyên ngoài (ảnh, âm thanh) vào ĐÚNG thư mục Assets
của project, để engine nạp được bằng đường dẫn chuẩn.

Đích đến cố định theo loại tài nguyên — không đoán bừa, người dùng chọn trong
hộp thoại và hộp thoại gợi ý sẵn theo tên tệp. Cây thư mục theo đúng quy ước
của LuaS30 IDE (xem `doc/reference/API.md`: `engine.image(x, y,
"assets/…")`, `engine.audio_play("assets/sfx/…")`):

    Ảnh chung            assets
    Ảnh giao diện        assets/ui
    Sprite nhân vật      assets/sprites
    Ảnh nền game         assets/background
    Ô gạch bản đồ        assets/tiles
    Ảnh bản đồ           assets/maps
    Hiệu ứng âm thanh    assets/sfx
    Nhạc nền             assets/music

Khác bản lua-engine ở chỗ `assets/audio/{music,sfx}` được rút thành
`assets/{music,sfx}` cho khớp đường dẫn trong tài liệu API của LuaS30, và có
thêm đích `assets` (phẳng) — tab ASSETS của Studio cũng quét phẳng thư mục này.
"""
from __future__ import annotations

import shutil
from pathlib import Path

# ---------------------------------------------------------------- loại tệp
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ico", ".tga"}
AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".m4a", ".flac", ".aac", ".wma", ".mid", ".midi"}

KIND_IMAGE = "image"
KIND_AUDIO = "audio"

# (key, nhãn hiển thị, thư mục tương đối trong project)
IMAGE_TARGETS = [
    ("assets", "Ảnh chung (assets/)", "assets"),
    ("ui", "Ảnh giao diện (UI)", "assets/ui"),
    ("sprites", "Sprite nhân vật / vật thể", "assets/sprites"),
    ("background", "Ảnh nền game (240×320)", "assets/background"),
    ("tiles", "Ô gạch bản đồ (tile)", "assets/tiles"),
    ("maps", "Ảnh bản đồ (map)", "assets/maps"),
]

AUDIO_TARGETS = [
    ("sfx", "Hiệu ứng âm thanh (sfx)", "assets/sfx"),
    ("music", "Nhạc nền (music)", "assets/music"),
]

TARGETS = {KIND_IMAGE: IMAGE_TARGETS, KIND_AUDIO: AUDIO_TARGETS}
TARGET_DIRS = {key: rel for key, _label, rel in IMAGE_TARGETS + AUDIO_TARGETS}
TARGET_LABELS = {key: label for key, label, _rel in IMAGE_TARGETS + AUDIO_TARGETS}
TARGET_KINDS = {key: kind for kind, items in TARGETS.items() for key, _l, _r in items}

# tài nguyên âm thanh đã nhập trong phiên — palette UI Designer liệt kê để tham chiếu
AUDIO_REGISTRY: dict[str, dict] = {}


def classify(path) -> str:
    """'image' / 'audio' / '' theo phần mở rộng."""
    suffix = Path(path).suffix.lower()
    if suffix in IMAGE_EXTS:
        return KIND_IMAGE
    if suffix in AUDIO_EXTS:
        return KIND_AUDIO
    return ""


def file_filter(kind: str) -> str:
    """Chuỗi filter cho QFileDialog."""
    if kind == KIND_AUDIO:
        exts = " ".join(f"*{e}" for e in sorted(AUDIO_EXTS))
        return f"Tệp âm thanh ({exts})"
    exts = " ".join(f"*{e}" for e in sorted(IMAGE_EXTS))
    return f"Ảnh ({exts})"


def guess_target(path) -> str:
    """Gợi ý đích đến theo tên tệp. Người dùng vẫn sửa lại được trong hộp thoại."""
    name = Path(path).name.lower()
    if classify(path) == KIND_AUDIO:
        if any(h in name for h in ("music", "bgm", "song", "theme", "loop", "nhac")):
            return "music"
        return "sfx"

    if any(h in name for h in ("background", "backdrop", "bg_", "_bg", "bg-", "nen", "nền")):
        return "background"
    if any(h in name for h in ("tile", "gach", "gạch")):
        return "tiles"
    if "map" in name:
        return "maps"
    if any(h in name for h in ("ui_", "_ui", "button", "icon", "hud", "menu", "btn")):
        return "ui"
    return "assets"


def unique_destination(dest_dir: Path, filename: str) -> Path:
    """Tránh ghi đè: thêm hậu tố _1, _2… nếu tên đã tồn tại."""
    target = dest_dir / filename
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    index = 1
    while True:
        candidate = dest_dir / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def import_files(project_root, files, target_key: str, rename: str = "") -> list[dict]:
    """Copy `files` vào thư mục của `target_key` trong project.

    Trả về danh sách {"source", "dest", "rel", "size"} cho từng tệp đã copy.
    `rename` chỉ áp cho 1 tệp; nhiều tệp thì dùng làm tiền tố (ten_1, ten_2…).
    """
    project_root = Path(project_root)
    rel_dir = TARGET_DIRS.get(target_key, "assets")
    dest_dir = project_root / rel_dir
    dest_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for index, src in enumerate(files):
        src = Path(src)
        if not src.is_file():
            continue
        if rename:
            stem = Path(rename).stem
            name = f"{stem}{src.suffix}" if len(files) == 1 else f"{stem}_{index + 1}{src.suffix}"
        else:
            name = src.name
        dest = unique_destination(dest_dir, name)
        shutil.copy2(src, dest)
        results.append({
            "source": src,
            "dest": dest,
            "rel": f"{rel_dir}/{dest.name}",
            "size": dest.stat().st_size,
        })
    return results


def human_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.2f} MB"


# ---------------------------------------------------------------- quét tài nguyên có sẵn
# Quét phẳng cả cây `assets/` (rglob) — khớp cách tab ASSETS của Studio liệt kê.
SCAN_IMAGE_DIRS = ["assets"]
SCAN_AUDIO_DIRS = ["assets"]


def _scan(root: Path, rel_dirs, exts) -> list[dict]:
    found = []
    for rel in rel_dirs:
        directory = root / rel
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix.lower() in exts:
                found.append({
                    "path": path,
                    "rel": path.relative_to(root).as_posix(),
                    "size": path.stat().st_size,
                })
    return found


def scan_project_images(project_root) -> list[dict]:
    """Mọi ảnh đã có trong các thư mục tài nguyên của project."""
    root = Path(project_root)
    return _scan(root, SCAN_IMAGE_DIRS, IMAGE_EXTS) if root.is_dir() else []


def scan_project_audio(project_root) -> list[dict]:
    """Mọi tệp âm thanh đã có trong assets/audio của project."""
    root = Path(project_root)
    return _scan(root, SCAN_AUDIO_DIRS, AUDIO_EXTS) if root.is_dir() else []



# ---------------------------------------------------------------- âm thanh
def audio_token(key: str) -> str:
    return f"audio:{key}"


def is_audio_token(token: str) -> bool:
    return isinstance(token, str) and token.startswith("audio:")


def audio_key(token: str) -> str:
    return token[len("audio:"):] if is_audio_token(token) else ""


def register_audio(key: str, title: str, src: str, size: int = 0) -> dict:
    entry = {"key": key, "title": title, "src": src, "size": size}
    AUDIO_REGISTRY[key] = entry
    return entry


def audio_entry(key: str) -> dict | None:
    return AUDIO_REGISTRY.get(key)


def clear_audio():
    AUDIO_REGISTRY.clear()
