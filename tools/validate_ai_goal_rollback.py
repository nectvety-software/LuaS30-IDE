"""Quay lui (rollback) thật cho thay đổi do AI ghi.

Kiểm bằng cách CHẠY THẬT `AIChangeService`: prepare -> apply -> restore, rồi
so nội dung tệp trên đĩa. Không kiểm bằng cách đọc chuỗi trong mã nguồn.

Bốn tình huống bắt buộc phải đúng:
  1. Tệp bị GHI ĐÈ  -> khôi phục nguyên nội dung cũ.
  2. Tệp do AI TẠO  -> bị xoá khi quay lui (bản chụp cũ chỉ sao lưu tệp đã có,
     nên đây chính là lỗ hổng mà manifest `checkpoint.json` bịt lại).
  3. Tệp bị SỬA TAY sau khi AI ghi -> KHÔNG được ghi đè/xoá (trừ khi force).
  4. Thư mục sao lưu CŨ (không có manifest) vẫn phải liệt kê + khôi phục được.
"""

from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "studio"))

from app.services.ai_agent_protocol import CodeEditAction
from app.services.ai_change_service import (
    AIChangeService,
    CHECKPOINT_MANIFEST,
)

PASS = []


def ok(message):
    PASS.append(message)
    print("PASS:", message)


def expect_error(fn, label):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError(f"{label}: lẽ ra phải báo lỗi ValueError")


# ---------------------------------------------------------------------------
# 1 + 2: apply() ghi manifest, restore() trả tệp cũ về và xoá tệp mới
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "src").mkdir()
    old_file = root / "src" / "main.lua"
    old_file.write_text('local mode = "old"\n', encoding="utf-8")

    service = AIChangeService()
    change_set = service.prepare(
        root,
        [
            CodeEditAction(path="src/main.lua", find='"old"', replace='"new"', reason="doi mode"),
            CodeEditAction(path="src/extra.lua", content="return 1\n", reason="tao moi"),
        ],
    )
    assert change_set.changed_files == 2
    applied, backup = service.apply(change_set)
    assert len(applied) == 2
    assert backup is not None
    assert backup.name and backup.parent.name == "ai-backups"
    assert (backup / CHECKPOINT_MANIFEST).is_file(), "thiếu checkpoint.json"
    assert '"new"' in old_file.read_text(encoding="utf-8")
    assert (root / "src" / "extra.lua").is_file()
    ok("apply() ghi checkpoint.json cho cả tệp ghi đè lẫn tệp tạo mới")

    items = AIChangeService.list_checkpoints(root)
    assert len(items) == 1, items
    assert items[0]["stamp"] == backup.name
    assert items[0]["file_count"] == 2
    assert items[0]["legacy"] is False
    by_path = {item["path"]: item for item in items[0]["files"]}
    assert by_path["src/main.lua"]["existed"] is True
    assert by_path["src/extra.lua"]["existed"] is False
    ok("list_checkpoints() phân biệt đúng tệp cũ và tệp AI tạo mới")

    report = AIChangeService.restore_checkpoint(root, backup.name)
    assert report["restored"] == ["src/main.lua"], report
    assert report["removed"] == ["src/extra.lua"], report
    assert report["skipped"] == [], report
    assert old_file.read_text(encoding="utf-8") == 'local mode = "old"\n'
    assert not (root / "src" / "extra.lua").exists(), "tệp AI tạo phải bị xoá"
    ok("restore_checkpoint() trả nội dung cũ về và xoá tệp do AI tạo")

    # Quay lui lần hai phải là no-op, không được nổ.
    again = AIChangeService.restore_checkpoint(root, backup.name)
    assert again["restored"] == [] and again["removed"] == [], again
    ok("quay lui lần hai là no-op (idempotent)")

# ---------------------------------------------------------------------------
# 3: chốt an toàn — tệp bị sửa tay thì KHÔNG ghi đè, trừ khi force
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    target = root / "main.lua"
    target.write_text("v1\n", encoding="utf-8")

    service = AIChangeService()
    change_set = service.prepare(
        root, [CodeEditAction(path="main.lua", content="v2\n", reason="ai")]
    )
    _, backup = service.apply(change_set)
    assert target.read_text(encoding="utf-8") == "v2\n"

    target.write_text("v3-nguoi-dung-tu-sua\n", encoding="utf-8")
    report = AIChangeService.restore_checkpoint(root, backup.name)
    assert report["restored"] == [], report
    assert report["skipped"] and "sửa" in report["skipped"][0]["reason"], report
    assert target.read_text(encoding="utf-8") == "v3-nguoi-dung-tu-sua\n"
    ok("tệp bị sửa tay sau khi AI ghi thì KHÔNG bị quay lui tự động")

    forced = AIChangeService.restore_checkpoint(root, backup.name, force=True)
    assert forced["restored"] == ["main.lua"], forced
    assert target.read_text(encoding="utf-8") == "v1\n"
    ok("force=True mới ghi đè được tệp đã bị sửa tay")

# ---------------------------------------------------------------------------
# 3b: HAI kiểu quay lui khác nhau, và lẫn lộn chúng là lùi quá một bước:
#       * restore_checkpoint(s) = hoàn tác các ghi CỦA s  -> trạng thái TRƯỚC s
#       * rewind_to(s)          = hoàn tác mọi ghi SAU s  -> trạng thái TẠI s
#     Không phân biệt được thì "quay về cuối bước N" sẽ lùi về TRƯỚC bước N.
# ---------------------------------------------------------------------------
def two_step_project():
    """Dựng dự án 2 bước: goc -> buoc1 (bản chụp tốt) -> buoc2-hong."""
    holder = tempfile.TemporaryDirectory()
    root = Path(holder.name)
    target = root / "main.lua"
    target.write_text("goc\n", encoding="utf-8")
    service = AIChangeService()
    first = service.prepare(
        root, [CodeEditAction(path="main.lua", content="buoc1\n", reason="b1")]
    )
    _, good = service.apply(first)
    second = service.prepare(
        root, [CodeEditAction(path="main.lua", content="buoc2-hong\n", reason="b2")]
    )
    _, bad = service.apply(second)
    assert target.read_text(encoding="utf-8") == "buoc2-hong\n"
    assert good.name != bad.name
    return holder, root, target, good, bad


# 3b-1: hoàn tác bản chụp -> TRƯỚC bản chụp đó
holder, root, target, good, bad = two_step_project()
with holder:
    report = AIChangeService.restore_checkpoint(root, good.name)
    assert report["restored"] == ["main.lua"], report
    assert target.read_text(encoding="utf-8") == "goc\n", \
        "restore_checkpoint hoàn tác ghi của chính nó -> trạng thái TRƯỚC bản chụp"
    ok("restore_checkpoint(s) hoàn tác ghi của s (trạng thái TRƯỚC s)")

# 3b-2: quay về TẠI bản chụp -> hoàn tác mọi ghi sau nó
holder, root, target, good, bad = two_step_project()
with holder:
    report = AIChangeService.rewind_to(root, good.name)
    assert report["mode"] == "rewind" and report["undone"] == [bad.name], report
    assert report["restored"] == ["main.lua"], report
    assert target.read_text(encoding="utf-8") == "buoc1\n", \
        "rewind_to phải về đúng trạng thái TẠI bản chụp, không lùi quá một bước"
    ok("rewind_to(s) hoàn tác mọi ghi sau s (trạng thái TẠI s)")

    # Nội dung do NGƯỜI dùng sửa tay vẫn phải được giữ khi quay lui.
    target.write_text("nguoi-dung-viet-tay\n", encoding="utf-8")
    report = AIChangeService.rewind_to(root, good.name)
    assert report["restored"] == [], report
    assert report["skipped"], report
    assert target.read_text(encoding="utf-8") == "nguoi-dung-viet-tay\n"
    ok("vẫn giữ nguyên tệp người dùng sửa tay (không ghi đè khi quay lui)")

# 3b-3: chuỗi 3 bước -> quay về giữa chuỗi phải hoàn tác đúng 2 bản chụp cuối
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    target = root / "main.lua"
    target.write_text("goc\n", encoding="utf-8")
    service = AIChangeService()
    chain = []
    for text in ("a\n", "b\n", "c\n"):
        cs = service.prepare(
            root, [CodeEditAction(path="main.lua", content=text, reason="x")]
        )
        _, bk = service.apply(cs)
        chain.append(bk.name)
    assert target.read_text(encoding="utf-8") == "c\n"
    report = AIChangeService.rewind_to(root, chain[0])
    assert report["undone"] == [chain[2], chain[1]], report
    assert target.read_text(encoding="utf-8") == "a\n", report
    ok("rewind_to giữa chuỗi 3 bước hoàn tác đúng 2 bản chụp cuối")

    expect_error(
        lambda: AIChangeService.rewind_to(root, "khong-ton-tai"), "rewind stamp lạ"
    )
    ok("rewind_to từ chối stamp không tồn tại")

# ---------------------------------------------------------------------------
# 4: thư mục sao lưu CŨ (không manifest) vẫn dùng được
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    target = root / "main.lua"
    target.write_text("moi\n", encoding="utf-8")

    legacy = root / ".luas30" / "ai-backups" / "20200101-000000-000000"
    (legacy / "main.lua").parent.mkdir(parents=True)
    (legacy / "main.lua").write_text("cu\n", encoding="utf-8")

    items = AIChangeService.list_checkpoints(root)
    assert len(items) == 1 and items[0]["legacy"] is True, items
    assert items[0]["file_count"] == 1
    report = AIChangeService.restore_checkpoint(root, items[0]["stamp"])
    assert report["legacy"] is True
    assert report["restored"] == ["main.lua"], report
    assert target.read_text(encoding="utf-8") == "cu\n"
    ok("bản chụp cũ không có checkpoint.json vẫn liệt kê + khôi phục được")

# ---------------------------------------------------------------------------
# 5: an toàn đường dẫn + stamp
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "ok.lua").write_text("x\n", encoding="utf-8")
    evil = root / ".luas30" / "ai-backups" / "20200101-000000-000001"
    evil.mkdir(parents=True)
    (evil / CHECKPOINT_MANIFEST).write_text(
        json.dumps({
            "stamp": evil.name,
            "files": [
                {"path": "../../thoat-ra-ngoai.lua", "existed": True},
                {"path": ".git/config", "existed": True},
                {"path": ".env", "existed": True},
                {"path": "ok.lua", "existed": True},
            ],
        }),
        encoding="utf-8",
    )
    (evil / "ok.lua").write_text("khoi-phuc\n", encoding="utf-8")

    report = AIChangeService.restore_checkpoint(root, evil.name)
    assert report["restored"] == ["ok.lua"], report
    assert len(report["skipped"]) == 3, report
    assert not (root.parent / "thoat-ra-ngoai.lua").exists()
    ok("manifest độc hại không thoát được project / không chạm .git, .env")

    expect_error(
        lambda: AIChangeService.restore_checkpoint(root, "../../etc"),
        "stamp traversal",
    )
    expect_error(
        lambda: AIChangeService.restore_checkpoint(root, "khong-ton-tai"),
        "stamp không tồn tại",
    )
    ok("stamp có dấu phân cách đường dẫn bị từ chối")

# ---------------------------------------------------------------------------
# 6: apply_one cũng tạo checkpoint (để Accept từng tệp vẫn quay lui được)
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    service = AIChangeService()
    change_set = service.prepare(
        root,
        [
            CodeEditAction(path="a.lua", content="A\n", reason="tao a"),
            CodeEditAction(path="b.lua", content="B\n", reason="tao b"),
        ],
    )
    target, backup = service.apply_one(change_set, 0)
    assert target == (root / "a.lua").resolve()
    assert backup is not None and (backup / CHECKPOINT_MANIFEST).is_file()
    assert (root / "a.lua").is_file() and not (root / "b.lua").exists()

    report = AIChangeService.restore_checkpoint(root, backup.name)
    assert report["removed"] == ["a.lua"], report
    assert not (root / "a.lua").exists()
    ok("apply_one() tạo bản chụp riêng và quay lui được tệp vừa Accept")

# ---------------------------------------------------------------------------
# 7: prune_checkpoints giữ đúng số bản mới nhất
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    service = AIChangeService()
    stamps = []
    for index in range(4):
        change_set = service.prepare(
            root, [CodeEditAction(path="f.lua", content=f"v{index}\n", reason="v")]
        )
        _, backup = service.apply(change_set)
        stamps.append(backup.name)
    assert len(AIChangeService.list_checkpoints(root)) == 4

    deleted = AIChangeService.prune_checkpoints(root, keep=2)
    assert len(deleted) == 2, deleted
    kept = [item["stamp"] for item in AIChangeService.list_checkpoints(root)]
    assert kept == sorted(stamps, reverse=True)[:2], (kept, stamps)
    ok("prune_checkpoints(keep=2) chỉ xoá bản cũ, giữ 2 bản mới nhất")

    latest = AIChangeService.restore_latest(root)
    assert latest["stamp"] == kept[0]
    ok("restore_latest() chọn đúng bản chụp mới nhất")

# ---------------------------------------------------------------------------
# 8: thư mục rác trong ai-backups không làm vỡ danh sách
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    backup_root = root / ".luas30" / "ai-backups"
    (backup_root / "..").mkdir(parents=True, exist_ok=True)
    (backup_root / "khong-phai-stamp" / "!").mkdir(parents=True, exist_ok=True)
    (backup_root / "loose.txt").write_text("rac", encoding="utf-8")
    assert AIChangeService.list_checkpoints(root) == []
    ok("mục lạ trong ai-backups bị bỏ qua, không raise")

print()
print(f"PASS: {len(PASS)} kiểm tra quay lui")
