#!/usr/bin/env python3
"""validate_no_signing.py — IDE KHÔNG ký VXP: chặn code ký quay lại repo.

Chạy:

    py -3.12 -u tools/validate_no_signing.py

Vì sao cần guard này: repo **không nằm trong git**, nên một lần xoá là không khôi
phục được — và ngược lại, một lần thêm lại cũng không ai thấy. Quyết định "IDE
không ký" (2026-09-17) phải được mã hoá thành kiểm tra tự động, nếu không nó chỉ
là một câu trong tài liệu.

Phạm vi quét: CODE (`.py`, `.bat`, `.json`), không quét `.md` — tài liệu được
PHÉP nhắc tên những gì đã bị gỡ, vì đó chính là cách giải thích lý do. Ví dụ
`doc/build/RELEASE_AND_HARDENING.md` liệt kê đúng các tệp đã xoá.

Lưu ý về chính guard này: nó chứa danh sách token cấm, nên **phải tự loại mình**
khỏi vòng quét (`SELF`). Đừng "sửa" bằng cách đổi chữ trong danh sách token —
làm vậy là vô hiệu hoá tripwire.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()

# Tệp của lõi ký: phải VẮNG MẶT.
GONE_FILES = (
    "tools/vxp_sign_core.py",
    "tools/vxp_sign_pure.py",
    "doc/build/VXP_SIGNER.md",
    "doc/build/SIGNING_AND_RELEASE.md",
    "tools/validate_vxp_signer.py",
    "tools/vxp_signer_gui.py",
    "sign.bat",
)

# Token nhận diện code ký. KHÔNG gồm `cert100` trơn: `tools/vxp_inspect.py` dùng
# nó như nhãn chế độ khi ĐỌC file (để báo "file này chưa ký"), đó là kiểm tra chứ
# không phải ký. Các token dưới đây đều là API/tham số của việc KÝ.
FORBIDDEN_TOKENS = (
    "vxp_sign_core",
    "vxp_sign_pure",
    "--cert100-key",
    "sign_cert100",
    "rsa_md5_sign",
    "triple_md5",
    "sign_vxp",
    "verify_vxp",
    "signature_nonzero = True",
)

SCAN_SUFFIXES = (".py", ".bat", ".json")
SKIP_DIRS = {
    ".git", ".workbuddy-ai", "__pycache__", "build", "release", "dist",
    ".luas30-tmp", "vendor", "toolchain", "emulator", "doc",
}

# `tools/vxp_inspect.py` là máy DÒ chữ ký (read-only). Nó được phép nói về chữ ký
# để báo cáo một file là chưa ký; nhưng vẫn không được chứa API ký.
DETECTOR_OK = {"tools/vxp_inspect.py"}

FAILS: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label} {detail}", flush=True)
    if not ok:
        FAILS.append(label)


def iter_code_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SCAN_SUFFIXES:
            continue
        if path.resolve() == SELF:
            continue
        parts = {p.lower() for p in path.parts}
        if parts & {d.lower() for d in SKIP_DIRS}:
            continue
        yield path


def main() -> int:
    print("-- A. lõi ký phải vắng mặt --", flush=True)
    for rel in GONE_FILES:
        check(f"không còn {rel}", not (ROOT / rel).exists())

    print("-- B. code không còn API ký --", flush=True)
    hits: list[str] = []
    for path in iter_code_files():
        rel = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for token in FORBIDDEN_TOKENS:
            if token in text:
                hits.append(f"{rel}: {token}")
    check("không file code nào chứa API ký", not hits, "; ".join(hits[:6]))

    print("-- C. build.py không nhận khóa ký --", flush=True)
    build = (ROOT / "tools" / "build.py").read_text(encoding="utf-8")
    check("build.py không có --cert100-key", "--cert100-key" not in build)
    check("build.py không import lõi ký",
          "vxp_sign_core" not in build and "vxp_sign_pure" not in build)
    check("build.py vẫn ghi manifest 'signing' rõ ràng",
          '"signing":"none (IDE does not sign VXP)"' in build)
    check("build.py vẫn có bước kiểm VXP (vxp_inspect)",
          "from vxp_inspect import inspect_file" in build)

    print("-- D. không có khoá/chứng chỉ trong repo --", flush=True)
    keys = [
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file()
        and p.suffix.lower() in (".pem", ".key", ".p12", ".pfx")
        and not ({q.lower() for q in p.parts} & {"vendor", "toolchain", ".workbuddy-ai", "build"})
    ]
    check("không có file khoá/chứng chỉ", not keys, str(keys[:5]))

    print("-- E. Studio không có nút ký --", flush=True)
    studio = (ROOT / "studio" / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    check("main_window.py không còn sign_build_action",
          "sign_build_action" not in studio and "sign_build_button" not in studio)

    print("\n== KẾT QUẢ ==", flush=True)
    print("FAIL:", FAILS or "không có", flush=True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
