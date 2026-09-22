"""Đệm ngữ cảnh: phải NHANH hơn, nhưng tuyệt đối không được CŨ.

Một bộ đệm phục vụ nội dung cũ còn tệ hơn không có đệm: agent sẽ sửa dựa trên
mã đã đổi. Vì vậy phép thử ở đây gồm cả hai chiều:

  * DƯƠNG: build lần hai không đọc lại tệp nào (`file_reads == 0`), chữ y hệt.
  * ÂM: sửa tài liệu / sửa mã nguồn / thêm tệp  ->  lần build sau BẮT BUỘC thấy
    nội dung mới. Không có nhánh nào được phục vụ bản cũ.
"""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "studio"))

from app.services.codebase_context_service import CodebaseContextService

PASS = []


def ok(message):
    PASS.append(message)
    print("PASS:", message)


def make_project(td: Path, prompt: str = "PROMPT goc cua du an\n") -> Path:
    root = td
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "PROMPT.md").write_text(prompt, encoding="utf-8")
    (root / "src" / "main.lua").write_text(
        "function player_move() return 1 end\n", encoding="utf-8"
    )
    return root


# ---------------------------------------------------------------------------
# 1: lần build thứ hai không đọc lại đĩa, và chữ KHÔNG đổi
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = make_project(Path(td))
    service = CodebaseContextService(ROOT)

    cold = service.build(root, "player move")
    assert cold.cache_hit is False, "lần đầu chưa có gì để trúng đệm"
    assert cold.stable_chars == 0

    service.reset_metrics()
    warm = service.build(root, "player move")
    metrics = service.metrics()

    assert warm.cache_hit is True, "lần hai phải trúng đệm tiền tố"
    assert warm.text == cold.text, "đệm làm ĐỔI ngữ cảnh -> hỏng ngữ nghĩa"
    assert metrics["file_reads"] == 0, f"còn đọc lại đĩa: {metrics}"
    assert metrics["prefix_hits"] == 1, metrics
    assert metrics["sources_hits"] == 1, metrics
    assert metrics["index_hits"] == 1, metrics
    assert metrics["reused_chars"] > 1000, metrics
    assert warm.stable_chars > 1000
    ok(f"lượt hai dùng lại đệm, không đọc lại tệp nào (tiết kiệm {metrics['reused_chars']} ký tự)")

    report = service.cache_report()
    assert "đệm:" in report and "tiết kiệm" in report, report
    ok("cache_report() đọc được sau khi reset số liệu: " + report)

    # Báo cáo phải nêu được CẢ lượt đọc lẫn lượt trúng (đo trên một service mới,
    # KHÔNG reset số liệu) — nếu không thì nó chỉ là chuỗi trang trí.
    fresh = CodebaseContextService(ROOT)
    fresh.build(root, "player move")
    fresh.build(root, "player move")
    mixed = fresh.cache_report()
    assert "0/0" not in mixed, mixed
    assert "(0%)" not in mixed and "(100%)" not in mixed, mixed
    ok("số liệu đệm cộng dồn đúng qua nhiều lượt: " + mixed)

# ---------------------------------------------------------------------------
# 2: sửa tài liệu chỉ dẫn -> tiền tố phải dựng lại, thấy nội dung mới
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = make_project(Path(td))
    service = CodebaseContextService(ROOT)
    assert "PROMPT goc cua du an" in service.build(root, "player move").text

    (root / "PROMPT.md").write_text("PROMPT MOI-CUA-DU-AN\n", encoding="utf-8")
    after = service.build(root, "player move")
    assert "MOI-CUA-DU-AN" in after.text, "tài liệu mới không tới được model"
    assert "PROMPT goc cua du an" not in after.text, "phục vụ tài liệu CŨ"
    assert after.cache_hit is False
    ok("sửa tài liệu chỉ dẫn -> đệm tiền tố tự vô hiệu, nội dung mới tới model")

# ---------------------------------------------------------------------------
# 3: sửa mã nguồn -> nội dung nguồn phải mới
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = make_project(Path(td))
    service = CodebaseContextService(ROOT)
    assert "return 1 end" in service.build(root, "player move").text

    (root / "src" / "main.lua").write_text(
        "function player_move() return 999 end\n", encoding="utf-8"
    )
    after = service.build(root, "player move")
    assert "return 999" in after.text, "nguồn mới không tới được model"
    assert "return 1 end" not in after.text, "phục vụ mã CŨ"
    ok("sửa mã nguồn -> nội dung nguồn trong ngữ cảnh được cập nhật")

# ---------------------------------------------------------------------------
# 4: thêm tệp -> cây thư mục phải đổi (vân tay CẤU TRÚC, không phải vân tay tệp)
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = make_project(Path(td))
    service = CodebaseContextService(ROOT)
    assert "new_thing.lua" not in service.build(root, "player move").text

    (root / "src" / "new_thing.lua").write_text("-- MOI\n", encoding="utf-8")
    after = service.build(root, "player move")
    assert "new_thing.lua" in after.text, "cây thư mục phục vụ bản CŨ"
    ok("thêm tệp mới -> cây thư mục trong ngữ cảnh được dựng lại")

# ---------------------------------------------------------------------------
# 5: cùng một tệp, hai hạn mức khác nhau -> KHÔNG được đệm theo (tệp, hạn mức)
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = make_project(Path(td))
    service = CodebaseContextService(ROOT)
    big = root / "big.md"
    big.write_text("y" * 5000, encoding="utf-8")

    small = service._cached_read(big, 100)
    full = service._cached_read(big, 5000)
    again = service._cached_read(big, 100)

    assert "truncated" in small and "4900" in small and "5000" in small, small[-80:]
    assert full == "y" * 5000, "hạn mức lớn trả về bản đã cắt"
    assert again == small
    assert service.metrics()["file_reads"] == 1, service.metrics()
    ok("cắt theo hạn mức tính lại sau khi lấy từ đệm (không đệm theo hạn mức)")

# ---------------------------------------------------------------------------
# 6: hai project khác nhau không rò rỉ ngữ cảnh sang nhau
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td_a, tempfile.TemporaryDirectory() as td_b:
    root_a = make_project(Path(td_a), "PROMPT CUA-A\n")
    root_b = make_project(Path(td_b), "PROMPT CUA-B\n")
    service = CodebaseContextService(ROOT)
    text_a = service.build(root_a, "player move").text
    text_b = service.build(root_b, "player move").text
    assert "CUA-A" in text_a and "CUA-B" not in text_a
    assert "CUA-B" in text_b and "CUA-A" not in text_b
    text_a2 = service.build(root_a, "player move").text
    assert text_a2 == text_a
    ok("khoá đệm gồm project root -> hai project không lẫn ngữ cảnh")

# ---------------------------------------------------------------------------
# 7: invalidate() xoá sạch
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = make_project(Path(td))
    service = CodebaseContextService(ROOT)
    service.build(root, "player move")
    assert service.build(root, "player move").cache_hit is True

    dropped = service.invalidate()
    assert dropped > 0, dropped
    assert service.build(root, "player move").cache_hit is False
    assert service.metrics()["file_reads"] > 0
    ok(f"invalidate() xoá {dropped} mục đệm, lượt sau dựng lại từ đĩa")

print()
print(f"PASS: {len(PASS)} kiểm tra đệm ngữ cảnh")
