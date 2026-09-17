#!/usr/bin/env python3
"""validate_wiki.py — wiki song ngữ: cặp trang, chuyển ngữ, link và facts.

Chạy:

    py -3.12 -u tools/validate_wiki.py

Vì sao cần guard này: `wiki/` là bản sao song ngữ của tài liệu, nên nó hỏng theo
hai cách mà mắt thường không thấy:

1. **Lệch cặp trang** — sửa `vi/Building-VXP.md` rồi quên `en/Building-VXP.md`.
   Không có lỗi nào hiện ra, chỉ là một ngôn ngữ lặng lẽ cũ dần.
2. **Link chết** — đổi tên/thêm/xoá tài liệu trong `doc/` thì link trong wiki
   trỏ vào hư không. Repo **không nằm trong git** nên không có lịch sử để dò lại.

Guard này neo wiki vào source thật (`VERSION`, `doc/`, `tools/validate_*.py`) chứ
không kiểm tra văn phong. Đừng "sửa" bằng cách nới điều kiện — mỗi mục dưới đây
ứng với một cách wiki đã từng lệch khỏi thực tế.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"

# Danh sách token ký là MỘT nguồn duy nhất — mượn từ guard chống-ký thay vì chép
# lại. Chép lại chính là cách file này từng tự tố cáo mình: nó chứa đúng những
# token mà `validate_no_signing.py` cấm, nên guard kia quét ra và FAIL. Mượn lại
# còn có lợi: thêm token mới ở guard kia thì wiki được canh luôn.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_no_signing import FORBIDDEN_TOKENS  # noqa: E402

# 8 trang cốt lõi, phải có đủ ở CẢ hai ngôn ngữ.
PAGES = (
    "Home.md",
    "Getting-Started.md",
    "Studio-UI.md",
    "Building-VXP.md",
    "Project-Structure.md",
    "AI-Agent.md",
    "Troubleshooting.md",
    "FAQ.md",
)
LANGS = ("vi", "en")

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")

# Số lượng validator ghi cứng trong wiki. Chỉ chấp nhận dạng "hơn 40" / "more than
# 40" — số chính xác đổi mỗi lần thêm validator, nên nó luôn có ngày sai.
COUNT_RE = re.compile(r"(?<!hơn )(?<!more than )\d+\s+validators?\b")

# Ngưỡng "hơn 40 validator" mà wiki nói tới. Đây là điều kiện MỘT CHIỀU: wiki nói
# "hơn 40" nên chỉ cần > 40 là đúng. Cố ý không hard-code số chính xác — con số
# đó đổi mỗi lần thêm validator và sẽ biến wiki thành tài liệu nói dối.
VALIDATOR_MIN = 40

FAILS: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label} {detail}", flush=True)
    if not ok:
        FAILS.append(label)


def page(lang: str, name: str) -> Path:
    return WIKI / lang / name


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def resolve(page_path: Path, target: str) -> Path | None:
    """Đổi link markdown thành đường dẫn thật, hoặc None nếu không phải link nội bộ."""
    t = target.strip().strip("<>").split("#", 1)[0]
    if not t or t.startswith(SKIP_PREFIXES):
        return None
    return (page_path.parent / t).resolve()


def main() -> int:
    if not WIKI.is_dir():
        print("FAIL: không có thư mục wiki/", flush=True)
        return 1

    print("-- A. đủ 8 trang ở cả hai ngôn ngữ --", flush=True)
    for lang in LANGS:
        for name in PAGES:
            check(f"{lang}/{name} tồn tại", page(lang, name).is_file())

    print("-- B. vi/ và en/ có cùng tập tệp --", flush=True)
    vi = {p.name for p in (WIKI / "vi").iterdir() if p.is_file()}
    en = {p.name for p in (WIKI / "en").iterdir() if p.is_file()}
    check("tập tệp hai ngôn ngữ trùng nhau", vi == en,
          f"chỉ vi: {sorted(vi - en)}; chỉ en: {sorted(en - vi)}")

    print("-- C. mỗi trang có dòng chuyển ngữ --", flush=True)
    for name in PAGES:
        for lang, other in (("vi", "en"), ("en", "vi")):
            text = read(page(lang, name))
            want = f"../{other}/{name}"
            check(f"{lang}/{name} trỏ sang {want}", want in text)

    print("-- D. mọi link tương đối phải tồn tại --", flush=True)
    broken: list[str] = []
    checked = 0
    for md in sorted(WIKI.rglob("*.md")):
        for target in LINK_RE.findall(read(md)):
            dest = resolve(md, target)
            if dest is None:
                continue
            checked += 1
            if not dest.exists():
                broken.append(f"{md.relative_to(ROOT).as_posix()} -> {target}")
    check(f"{checked} link tương đối đều giải được", not broken, "; ".join(broken[:8]))

    print("-- E. link chéo ngôn ngữ phải đúng tên trang --", flush=True)
    # CHỈ xét link đi SANG ngôn ngữ kia. Link cùng ngôn ngữ đương nhiên trỏ tới
    # trang khác tên — đó là điều hướng bình thường, không phải lỗi.
    wrong: list[str] = []
    cross = 0
    for md in sorted(WIKI.rglob("*.md")):
        src_lang = md.parent.name
        if src_lang not in LANGS:
            continue
        for target in LINK_RE.findall(read(md)):
            dest = resolve(md, target)
            if dest is None or not dest.exists() or WIKI not in dest.parents:
                continue
            parts = dest.relative_to(WIKI).parts
            if len(parts) < 2 or parts[0] not in LANGS or parts[0] == src_lang:
                continue
            cross += 1
            # Cặp 1-1: sang ngôn ngữ kia phải giữ nguyên tên trang.
            if parts[1] != md.name:
                wrong.append(f"{md.relative_to(ROOT).as_posix()} -> {target}")
    check(f"{cross} link chéo ngôn ngữ giữ nguyên tên trang", not wrong,
          "; ".join(wrong[:8]))

    print("-- F. facts neo vào source thật --", flush=True)
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    for lang in LANGS:
        home = read(page(lang, "Home.md"))
        check(f"{lang}/Home.md nêu đúng VERSION {version}", version in home)
        # Tuyên bố không ký là thông tin quan trọng nhất của wiki.
        for name in ("Home.md", "Building-VXP.md", "FAQ.md"):
            text = read(page(lang, name)).lower()
            marker = "không ký" if lang == "vi" else "does not sign"
            check(f"{lang}/{name} nói rõ IDE không ký", marker in text)

    starter = read(page("vi", "Getting-Started.md"))
    for flag in ("--offline", "--online", "--deps-only", "--force-deps"):
        check(f"vi/Getting-Started.md có mode {flag}", flag in starter)
    check("vi/Getting-Started.md có ràng buộc PySide6",
          "PySide6>=6.7,<7" in starter)

    for lang in LANGS:
        text = read(page(lang, "Project-Structure.md"))
        check(f"{lang}/Project-Structure.md có thư mục project chuẩn",
              "Documents\\LuaS30IDE" in text)

    print("-- G. wiki không dạy ký VXP --", flush=True)
    # Wiki ĐƯỢC phép liệt kê những gì đã bị gỡ (đó chính là cách giải thích lý do),
    # nhưng không được trình bày chúng như lệnh để chạy. Nên: dòng nào nhắc token
    # ký mà đồng thời trông giống một lệnh thì bị bắt.
    bad: list[str] = []
    for md in sorted(WIKI.rglob("*.md")):
        for lineno, line in enumerate(read(md).splitlines(), 1):
            if not any(tok in line for tok in FORBIDDEN_TOKENS):
                continue
            if "python" in line or "build.py" in line:
                bad.append(f"{md.relative_to(ROOT).as_posix()}:{lineno}")
    check("không có dòng nào hướng dẫn chạy lệnh ký", not bad, "; ".join(bad[:8]))

    print("-- H. con số validator trong wiki còn đúng --", flush=True)
    actual = len(list((ROOT / "tools").glob("validate_*.py")))
    check(f"thực tế có hơn {VALIDATOR_MIN} validator", actual > VALIDATOR_MIN,
          f"({actual})")
    for lang in LANGS:
        text = read(page(lang, "Building-VXP.md"))
        claim = f"hơn {VALIDATOR_MIN}" if lang == "vi" else f"more than {VALIDATOR_MIN}"
        check(f"{lang}/Building-VXP.md nói '{claim}'", claim in text)

    print("-- I. wiki không ghi cứng số lượng validator --", flush=True)
    # Mục H chỉ canh MỘT trang. Con số cứng đã từng lọt vào hai trang khác (sơ đồ
    # cây thư mục trong Project-Structure.md), nên canh cả thư mục: mọi chỗ nhắc
    # số lượng validator phải dùng dạng "hơn 40" / "more than 40".
    hard: list[str] = []
    for md in sorted(WIKI.rglob("*.md")):
        for lineno, line in enumerate(read(md).splitlines(), 1):
            if COUNT_RE.search(line):
                hard.append(f"{md.relative_to(ROOT).as_posix()}:{lineno}")
    check("không nơi nào ghi số validator cứng", not hard, "; ".join(hard[:8]))

    print("\n== KẾT QUẢ ==", flush=True)
    print("FAIL:", FAILS or "không có", flush=True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
