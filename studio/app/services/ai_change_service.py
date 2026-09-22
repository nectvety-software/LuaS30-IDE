from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.services.ai_agent_protocol import CodeEditAction


BLOCKED_PARTS = {
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__",
    "release", ".idea", ".vscode",
}
BLOCKED_NAMES = {
    ".env", ".env.local", ".env.production", "credentials.json", "secrets.json",
    "id_rsa", "id_ed25519",
}

# Mỗi lần `apply()` / `apply_one()` ghi một "bản chụp" (checkpoint) vào
# `.luas30/ai-backups/<stamp>/`. Manifest này ghi LẠI chính xác tệp nào đã bị
# ghi đè và tệp nào do AI TẠO MỚI (không có bản sao lưu) — nhờ vậy mới quay lui
# được cả hai chiều: trả nội dung cũ về, và xoá tệp vừa sinh ra.
CHECKPOINT_MANIFEST = "checkpoint.json"
CHECKPOINT_KEEP = 20
# Stamp = "%Y%m%d-%H%M%S-%f" (vd 20260921-223000-123456). Chấp nhận cả bản chỉ
# có tới giây cho tương thích, nhưng TUYỆT ĐỐI không nhận dấu phân cách đường dẫn,
# "..", hay tên thư mục không phải stamp (để `list_checkpoints` không nhặt rác).
_STAMP_PATTERN = re.compile(r"^[0-9]{8}-[0-9]{6}(?:-[0-9]{1,6})?$")


def _sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", "surrogateescape")).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        data = Path(path).read_bytes()
    except OSError:
        return ""
    return hashlib.sha256(data).hexdigest()


class EditMatchError(ValueError):
    """Nội dung `find` của một edit không khớp tệp — KHÁC với lỗi bảo mật đường dẫn.

    Tách thành type riêng để `prepare()` bỏ qua ĐÚNG edit khớp hỏng mà vẫn áp các
    edit còn lại (đặc biệt là tệp MỚI tạo bằng `content`). Trước đây một `find`
    lệch whitespace thôi cũng làm hỏng CẢ lô, nên "thêm code vào project" thất
    bại toàn bộ dù ý định tạo tệp mới là hợp lệ.
    """


@dataclass
class PreparedChange:
    relative_path: str
    absolute_path: Path
    before: str
    after: str
    reason: str = ""
    existed: bool = True
    added_lines: int = 0
    removed_lines: int = 0

    @property
    def changed(self) -> bool:
        return self.before != self.after

    def unified_diff(self) -> str:
        before_lines = self.before.splitlines(keepends=True)
        after_lines = self.after.splitlines(keepends=True)
        return "".join(
            difflib.unified_diff(
                before_lines,
                after_lines,
                fromfile=f"a/{self.relative_path}",
                tofile=f"b/{self.relative_path}",
                lineterm="\n",
            )
        )


@dataclass
class PreparedChangeSet:
    project_root: Path
    changes: list[PreparedChange] = field(default_factory=list)
    source: str = "ChatAI"
    skipped: list[str] = field(default_factory=list)

    @property
    def changed_files(self) -> int:
        return sum(1 for item in self.changes if item.changed)

    @property
    def added_lines(self) -> int:
        return sum(item.added_lines for item in self.changes)

    @property
    def removed_lines(self) -> int:
        return sum(item.removed_lines for item in self.changes)

    def summary(self) -> str:
        text = (
            f"{self.changed_files} file(s) · +{self.added_lines} "
            f"-{self.removed_lines}"
        )
        if self.skipped:
            text += f" · {len(self.skipped)} edit(s) skipped"
        return text


def _line_stats(before: str, after: str) -> tuple[int, int]:
    added = 0
    removed = 0
    matcher = difflib.SequenceMatcher(
        a=before.splitlines(),
        b=after.splitlines(),
        autojunk=False,
    )
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in {"replace", "delete"}:
            removed += i2 - i1
        if tag in {"replace", "insert"}:
            added += j2 - j1
    return added, removed


class AIChangeService:
    """Prepare, review and atomically apply model-proposed project edits.

    The service intentionally refuses paths outside the active project and common
    credential/VCS/generated locations. It accepts full-file writes or exact
    search/replace edits from the model protocol.
    """

    def __init__(self) -> None:
        self.pending: PreparedChangeSet | None = None
        self.last_backup_dir: Path | None = None

    @staticmethod
    def _safe_target(project_root: Path, relative: str) -> tuple[str, Path]:
        raw = str(relative or "").strip().replace("\\", "/")
        while raw.startswith("./"):
            raw = raw[2:]
        if not raw:
            raise ValueError("AI edit path is empty.")
        if raw.startswith("/") or raw.startswith("\\") or (len(raw) >= 3 and raw[1] == ":" and raw[2] == "/"):
            raise ValueError(f"Absolute AI edit path is not allowed: {relative}")

        rel_path = Path(raw)
        if rel_path.name.lower() in {name.lower() for name in BLOCKED_NAMES}:
            raise ValueError(f"AI edit target is protected: {raw}")
        lowered = {part.lower() for part in rel_path.parts}
        if lowered & {name.lower() for name in BLOCKED_PARTS}:
            raise ValueError(f"AI edit target is outside editable source areas: {raw}")
        if any(token in rel_path.name.lower() for token in ("secret", "credential", "private_key")):
            raise ValueError(f"AI edit target looks sensitive: {raw}")

        root = project_root.expanduser().resolve()
        target = (root / rel_path).resolve()
        try:
            normalized = target.relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError(f"AI edit escaped the project root: {relative}") from exc
        return normalized, target

    @staticmethod
    def _read_text(path: Path) -> str:
        if not path.is_file():
            return ""
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            try:
                return path.read_text(encoding="latin-1")
            except OSError as exc:
                raise ValueError(f"Cannot read AI edit target: {path}") from exc
        except OSError as exc:
            raise ValueError(f"Cannot read AI edit target: {path}") from exc

    @staticmethod
    def _flexible_span(before: str, find: str) -> tuple[int, int] | None:
        """Tìm khối `find` trong `before` bỏ qua thụt lề/khoảng trắng từng dòng.

        Model hay copy lại một đoạn rồi dán vào `find` nhưng lệch chỗ đầu dòng
        (tab vs space, thụt lề tự động) khiến so khớp nguyên văn thất bại. So
        từng dòng sau `.strip()` cho phép "thêm code" áp được dù indent khác.
        Chỉ nhận khi khớp ĐÚNG MỘT vị trí để không thay nhầm chỗ.
        """
        find_lines = find.rstrip("\n").splitlines()
        if not find_lines:
            return None
        target = [ln.strip() for ln in find_lines]
        blines = before.splitlines(keepends=True)
        if len(blines) < len(target):
            return None
        matches: list[tuple[int, int]] = []
        for start in range(len(blines) - len(target) + 1):
            window = blines[start:start + len(target)]
            if all(w.strip() == t for w, t in zip(window, target)):
                offset = sum(len(blines[i]) for i in range(start))
                # Kết thúc ở HẾT nội dung dòng cuối, KHÔNG ăn ký tự xuống dòng của
                # nó — nếu không, thay thế sẽ dán liền dòng kế tiếp (vd "end").
                last = window[-1]
                content_len = len(last) - (len(last) - len(last.rstrip("\r\n")))
                span_end = offset + sum(len(w) for w in window[:-1]) + content_len
                matches.append((offset, span_end))
        if len(matches) == 1:
            return matches[0]
        return None

    def _apply_action(self, before: str, action: CodeEditAction) -> str:
        if action.content is not None:
            return action.content.replace("\r\n", "\n").replace("\r", "\n")

        old = action.find
        new = action.replace
        if old is None:
            raise EditMatchError(f"Edit for {action.path} has neither content nor find/replace.")
        count = before.count(old)
        if count == 1 or (count > 1 and action.replace_all):
            return before.replace(old, new or "", -1 if action.replace_all else 1)
        if count > 1:
            raise EditMatchError(
                f"Search text appears {count} times in {action.path}; "
                "the AI must provide a more specific match or replace_all=true."
            )
        span = self._flexible_span(before, old)
        if span is not None:
            start, end = span
            return before[:start] + (new or "") + before[end:]
        raise EditMatchError(f"Search text was not found in {action.path}.")

    def prepare(
        self,
        project_root: Path,
        actions: list[CodeEditAction] | tuple[CodeEditAction, ...],
        *,
        text_overrides: dict[Path, str] | None = None,
        source: str = "ChatAI",
    ) -> PreparedChangeSet:
        root = Path(project_root).expanduser().resolve()
        if not root.is_dir():
            raise ValueError("An open project is required before AI code changes can be prepared.")

        overrides: dict[Path, str] = {}
        for path, text in (text_overrides or {}).items():
            try:
                overrides[Path(path).resolve()] = str(text)
            except OSError:
                continue

        by_path: dict[Path, PreparedChange] = {}
        order: list[Path] = []
        skipped: list[str] = []
        for action in actions:
            # Lỗi ĐƯỜNG DẪN (ngoài project, tệp bảo mật) vẫn fatal: không bao giờ
            # viết ra ngoài project. Chỉ lỗi KHỚP NỘI DUNG mới được bỏ qua lẻ tẻ.
            relative, target = self._safe_target(root, action.path)
            if target not in by_path:
                before = overrides.get(target, self._read_text(target))
                by_path[target] = PreparedChange(
                    relative_path=relative,
                    absolute_path=target,
                    before=before,
                    after=before,
                    reason=action.reason,
                    existed=target.is_file(),
                )
                order.append(target)

            item = by_path[target]
            try:
                item.after = self._apply_action(item.after, action)
            except EditMatchError as exc:
                skipped.append(str(exc))
                continue
            if action.reason:
                item.reason = action.reason

        changes = []
        for target in order:
            item = by_path[target]
            item.added_lines, item.removed_lines = _line_stats(item.before, item.after)
            if item.changed:
                changes.append(item)

        if not changes:
            detail = "; ".join(dict.fromkeys(skipped))
            raise ValueError(
                "The AI edit proposal produced no code changes."
                + (f" Không áp được: {detail}" if detail else "")
            )

        self.pending = PreparedChangeSet(root, changes, source=source, skipped=skipped)
        return self.pending

    def reject(self) -> None:
        self.pending = None

    def discard(self, change_set: PreparedChangeSet, index: int) -> PreparedChange:
        """Bo mot file khoi set cho duyet (Reject tung file kieu Codex)."""
        try:
            return change_set.changes.pop(int(index))
        except (IndexError, ValueError, TypeError) as exc:
            raise ValueError("No such pending AI change.") from exc

    def apply_one(
        self, change_set: PreparedChangeSet, index: int
    ) -> tuple[Path, Path | None]:
        """Ghi mot file duy nhat (Accept tung file kieu Codex).

        Backup rieng theo stamp giong apply() de van khoi phuc duoc.
        """
        try:
            change = change_set.changes[int(index)]
        except (IndexError, ValueError, TypeError) as exc:
            raise ValueError("No such pending AI change.") from exc

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup_dir = change_set.project_root / ".luas30" / "ai-backups" / stamp
        target = change.absolute_path
        target.parent.mkdir(parents=True, exist_ok=True)
        existed = target.is_file()
        if existed:
            backup = backup_dir / change.relative_path
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)

        fd, temp_name = tempfile.mkstemp(
            prefix=target.name + ".ai-",
            suffix=".tmp",
            dir=str(target.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(change.after)
            os.replace(temp_name, target)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

        # Luon ghi manifest — kể cả khi không có bản sao lưu (tệp MỚI) — để
        # `restore_checkpoint()` biết phải XOÁ tệp nào khi quay lui.
        self._write_checkpoint(
            backup_dir,
            change_set,
            [{
                "path": change.relative_path,
                "existed": existed,
                "sha_before": _sha256_text(change.before) if existed else "",
                "sha_after": _sha256_text(change.after),
            }],
        )

        change_set.changes.remove(change)
        self.last_backup_dir = backup_dir
        return target, backup_dir

    def apply(self, change_set: PreparedChangeSet | None = None) -> tuple[list[Path], Path | None]:
        change_set = change_set or self.pending
        if not change_set:
            raise ValueError("There are no pending AI code changes.")

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup_dir = change_set.project_root / ".luas30" / "ai-backups" / stamp
        applied: list[Path] = []
        records: list[dict] = []
        created_backup = False

        try:
            for change in change_set.changes:
                target = change.absolute_path
                target.parent.mkdir(parents=True, exist_ok=True)
                existed = target.is_file()

                if existed:
                    backup = backup_dir / change.relative_path
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, backup)
                    created_backup = True

                fd, temp_name = tempfile.mkstemp(
                    prefix=target.name + ".ai-",
                    suffix=".tmp",
                    dir=str(target.parent),
                    text=True,
                )
                try:
                    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(change.after)
                    os.replace(temp_name, target)
                finally:
                    if os.path.exists(temp_name):
                        os.unlink(temp_name)
                records.append({
                    "path": change.relative_path,
                    "existed": existed,
                    "sha_before": _sha256_text(change.before) if existed else "",
                    "sha_after": _sha256_text(change.after),
                })
                applied.append(target)
        except Exception:
            # Roll back only files we already touched and for which a backup exists.
            for target in reversed(applied):
                try:
                    relative = target.relative_to(change_set.project_root)
                    backup = backup_dir / relative
                    if backup.is_file():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(backup, target)
                    elif target.is_file():
                        target.unlink()
                except OSError:
                    pass
            raise

        if records:
            self._write_checkpoint(backup_dir, change_set, records)
            created_backup = True

        self.last_backup_dir = backup_dir if created_backup else None
        self.pending = None
        return applied, self.last_backup_dir

    @staticmethod
    def manifest(change_set: PreparedChangeSet) -> dict:
        return {
            "source": change_set.source,
            "summary": change_set.summary(),
            "files": [
                {
                    "path": item.relative_path,
                    "reason": item.reason,
                    "added_lines": item.added_lines,
                    "removed_lines": item.removed_lines,
                    "existed": item.existed,
                }
                for item in change_set.changes
            ],
        }

    # ------------------------------------------------------------------
    # Checkpoint / rollback
    # ------------------------------------------------------------------

    @staticmethod
    def checkpoints_root(project_root: Path) -> Path:
        return Path(project_root).expanduser().resolve() / ".luas30" / "ai-backups"

    @staticmethod
    def _valid_stamp(stamp: str) -> bool:
        raw = str(stamp or "").strip()
        if not raw or ".." in raw:
            return False
        return bool(_STAMP_PATTERN.match(raw))

    @classmethod
    def _write_checkpoint(
        cls,
        backup_dir: Path,
        change_set: PreparedChangeSet | None,
        files: list[dict],
        *,
        source: str | None = None,
        extra: dict | None = None,
    ) -> Path:
        """Ghi manifest mô tả bản chụp. Ghi kiểu nguyên tử (tmp + replace)."""
        backup_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "stamp": backup_dir.name,
            "source": source or (change_set.source if change_set else "ChatAI"),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "summary": change_set.summary() if change_set else "",
            "files": list(files),
        }
        if extra:
            payload.update(extra)
        path = backup_dir / CHECKPOINT_MANIFEST
        temp = backup_dir / (CHECKPOINT_MANIFEST + ".tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temp, path)
        return path

    @classmethod
    def _read_checkpoint(cls, backup_dir: Path) -> dict:
        """Đọc manifest; thư mục CŨ không có manifest vẫn phải dùng được.

        Bản cũ chỉ có các tệp sao lưu trần ⇒ suy ra danh sách tệp bằng cách đi
        trong thư mục và coi tất cả là "đã tồn tại" (đúng bản chất: chỉ tệp đã
        tồn tại mới có bản sao lưu).
        """
        manifest_path = backup_dir / CHECKPOINT_MANIFEST
        if manifest_path.is_file():
            try:
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                payload = None
            if isinstance(payload, dict) and isinstance(payload.get("files"), list):
                files = [
                    item for item in payload["files"]
                    if isinstance(item, dict) and str(item.get("path") or "").strip()
                ]
                return {
                    "stamp": str(payload.get("stamp") or backup_dir.name),
                    "created_at": str(payload.get("created_at") or ""),
                    "source": str(payload.get("source") or "ChatAI"),
                    "summary": str(payload.get("summary") or ""),
                    "restored_at": str(payload.get("restored_at") or ""),
                    "legacy": False,
                    "backup_dir": str(backup_dir),
                    "files": files,
                }

        files = []
        for item in sorted(backup_dir.rglob("*")):
            if not item.is_file() or item.name == CHECKPOINT_MANIFEST:
                continue
            try:
                relative = item.relative_to(backup_dir).as_posix()
            except ValueError:
                continue
            files.append({
                "path": relative,
                "existed": True,
                "sha_before": "",
                "sha_after": "",
            })
        return {
            "stamp": backup_dir.name,
            "created_at": datetime.fromtimestamp(
                backup_dir.stat().st_mtime
            ).isoformat(timespec="seconds"),
            "source": "legacy",
            "summary": "",
            "restored_at": "",
            "legacy": True,
            "backup_dir": str(backup_dir),
            "files": files,
        }

    @classmethod
    def list_checkpoints(cls, project_root: Path) -> list[dict]:
        """Liệt kê bản chụp, MỚI NHẤT TRƯỚC. Không bao giờ raise."""
        root = cls.checkpoints_root(project_root)
        if not root.is_dir():
            return []
        found: list[dict] = []
        try:
            entries = list(root.iterdir())
        except OSError:
            return []
        for entry in entries:
            if not entry.is_dir() or not cls._valid_stamp(entry.name):
                continue
            try:
                info = cls._read_checkpoint(entry)
            except OSError:
                continue
            info["file_count"] = len(info.get("files") or [])
            found.append(info)
        found.sort(key=lambda item: item.get("stamp", ""), reverse=True)
        return found

    @classmethod
    def _ai_written_hashes(
        cls, project_root: Path, *, after_stamp: str = ""
    ) -> set[tuple[str, str]]:
        """Các cặp (đường dẫn, sha) mà CHÍNH AI đã ghi, ở mọi bản chụp MỚI HƠN.

        Cần phép phân biệt này vì "tệp lệch khỏi bản chụp đích" có hai nguyên
        nhân rất khác nhau:

          * người dùng sửa tay  -> phải GIỮ NGUYÊN, không được ghi đè;
          * chính AI ghi ở BƯỚC SAU -> phải được phép ghi đè khi quay lui về bước
            trước, nếu không thì quay lui nhiều bước LUÔN bị chặn — đúng tình
            huống mà tính năng này sinh ra để xử lý.

        Stamp có độ rộng cố định nên so sánh chuỗi chính là so sánh thời gian.
        """
        written: set[tuple[str, str]] = set()
        for info in cls.list_checkpoints(project_root):
            if after_stamp and str(info.get("stamp") or "") <= after_stamp:
                continue
            for record in info.get("files") or []:
                path = str(record.get("path") or "")
                sha = str(record.get("sha_after") or "")
                if path and sha:
                    written.add((path, sha))
        return written

    @classmethod
    def restore_checkpoint(
        cls,
        project_root: Path,
        stamp: str,
        *,
        force: bool = False,
    ) -> dict:
        """Quay lui về trạng thái trước bản chụp `stamp`.

        - Tệp đã tồn tại trước đó ⇒ chép bản sao lưu trở lại.
        - Tệp do AI TẠO MỚI ⇒ xoá đi.
        - Tệp lệch khỏi bản chụp đích ⇒ chỉ bỏ qua khi nội dung KHÔNG do AI ghi,
          tức là người dùng đã sửa tay (`force=True` để ghi đè). Nội dung do AI
          ghi ở bước sau thì được phép ghi đè — xem `_ai_written_hashes()`.
        """
        root = Path(project_root).expanduser().resolve()
        if not cls._valid_stamp(stamp):
            raise ValueError(f"Bản chụp không hợp lệ: {stamp}")
        backup_dir = cls.checkpoints_root(root) / str(stamp)
        if not backup_dir.is_dir():
            raise ValueError(f"Không tìm thấy bản chụp {stamp}.")

        info = cls._read_checkpoint(backup_dir)
        ai_written = cls._ai_written_hashes(root, after_stamp=str(stamp))
        restored: list[str] = []
        removed: list[str] = []
        skipped: list[dict] = []

        for record in info.get("files") or []:
            raw = str(record.get("path") or "")
            try:
                relative, target = cls._safe_target(root, raw)
            except ValueError as exc:
                skipped.append({"path": raw, "reason": str(exc)})
                continue

            existed = bool(record.get("existed", True))
            expected = str(record.get("sha_after") or "")
            current = _sha256_file(target) if target.is_file() else ""
            # Lệch bản chụp đích nhưng do AI ghi ở bước sau => vẫn được quay lui.
            drifted_by_hand = (
                bool(expected) and bool(current)
                and current != expected
                and (relative, current) not in ai_written
            )

            if not existed:
                if not target.is_file():
                    continue
                if drifted_by_hand and not force:
                    skipped.append({
                        "path": relative,
                        "reason": "tệp mới đã bị sửa tay sau khi AI tạo; không xoá",
                    })
                    continue
                try:
                    target.unlink()
                except OSError as exc:
                    skipped.append({"path": relative, "reason": f"không xoá được: {exc}"})
                    continue
                removed.append(relative)
                continue

            backup = backup_dir / relative
            if not backup.is_file():
                skipped.append({"path": relative, "reason": "thiếu tệp sao lưu"})
                continue
            if drifted_by_hand and not force:
                skipped.append({
                    "path": relative,
                    "reason": "tệp đã bị sửa tay sau khi AI ghi; dùng force để ghi đè",
                })
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, target)
            except OSError as exc:
                skipped.append({"path": relative, "reason": f"không ghi được: {exc}"})
                continue
            restored.append(relative)

        if restored or removed:
            try:
                cls._write_checkpoint(
                    backup_dir,
                    None,
                    info.get("files") or [],
                    source=info.get("source") or "ChatAI",
                    extra={
                        "summary": info.get("summary") or "",
                        "created_at": info.get("created_at") or "",
                        "restored_at": datetime.now().isoformat(timespec="seconds"),
                    },
                )
            except OSError:
                pass

        return {
            "stamp": str(stamp),
            "restored": restored,
            "removed": removed,
            "skipped": skipped,
            "legacy": bool(info.get("legacy")),
        }

    @classmethod
    def restore_latest(cls, project_root: Path, *, force: bool = False) -> dict:
        items = cls.list_checkpoints(project_root)
        if not items:
            raise ValueError("Chưa có bản chụp nào để quay lui.")
        return cls.restore_checkpoint(project_root, items[0]["stamp"], force=force)

    @staticmethod
    def _matches_state(project_root: Path, expected: dict[str, str]) -> bool:
        """Dự án đang đúng trạng thái `expected` (đường dẫn -> sha nội dung) chưa?"""
        for raw, sha in expected.items():
            if not sha:
                continue
            try:
                _relative, target = AIChangeService._safe_target(project_root, raw)
            except ValueError:
                return False
            if _sha256_file(target) != sha:
                return False
        return True

    @classmethod
    def rewind_to(cls, project_root: Path, stamp: str, *, force: bool = False) -> dict:
        """Đưa dự án về ĐÚNG trạng thái tại thời điểm `stamp` được tạo.

        KHÁC `restore_checkpoint(stamp)`: hàm đó hoàn tác các ghi CỦA CHÍNH `stamp`
        (thư mục sao lưu giữ nội dung TRƯỚC khi ghi), nên nó trả về trạng thái
        *trước* bản chụp. Hàm này hoàn tác MỌI bản chụp MỚI HƠN, lần lượt từ mới
        nhất về cũ nhất — kết quả là trạng thái *tại* `stamp`.

        Đây mới là thứ Goal Mode cần cho "quay về cuối bước N": bước N được xác
        nhận ở bản chụp `stamp`, mọi ghi sau đó (của bước N+1 đang hỏng) bị hoàn
        tác. Dùng `restore_checkpoint` ở đây sẽ trả về trạng thái *trước* bước N —
        lùi quá một bước, đúng kiểu lỗi im lặng rất khó thấy.
        """
        root = Path(project_root).expanduser().resolve()
        if not cls._valid_stamp(stamp):
            raise ValueError(f"Bản chụp không hợp lệ: {stamp}")
        target = cls.checkpoints_root(root) / str(stamp)
        if not target.is_dir():
            raise ValueError(f"Không tìm thấy bản chụp {stamp}.")
        info_target = cls._read_checkpoint(target)

        undone: list[str] = []
        restored: list[str] = []
        removed: list[str] = []
        skipped: list[dict] = []
        # Trạng thái ĐÍCH: `sha_after` của chính bản chụp `stamp` là nội dung tệp
        # ngay sau khi nó được tạo. Dừng ngay khi đạt được — nếu hoàn tác mù quáng
        # hết mọi bản chụp mới hơn thì một lần quay lui đã chạy trước đó (hoặc một
        # bản chụp chẳng liên quan) sẽ bị hoàn tác lại và đẩy dự án lùi quá đích.
        target_shas = {
            str(record.get("path") or ""): str(record.get("sha_after") or "")
            for record in (info_target.get("files") or [])
            if record.get("sha_after")
        }
        if target_shas and cls._matches_state(root, target_shas):
            return {
                "stamp": str(stamp), "mode": "rewind", "undone": [],
                "restored": [], "removed": [], "skipped": [], "legacy": False,
            }
        # `list_checkpoints` trả MỚI NHẤT TRƯỚC: hoàn tác theo đúng thứ tự đó.
        for info in cls.list_checkpoints(root):
            if str(info.get("stamp") or "") <= str(stamp):
                continue
            try:
                report = cls.restore_checkpoint(root, info["stamp"], force=force)
            except ValueError:
                continue
            undone.append(str(info.get("stamp")))
            restored += list(report.get("restored") or [])
            removed += list(report.get("removed") or [])
            skipped += list(report.get("skipped") or [])
            if target_shas and cls._matches_state(root, target_shas):
                break
        return {
            "stamp": str(stamp),
            "mode": "rewind",
            "undone": undone,
            "restored": restored,
            "removed": removed,
            "skipped": skipped,
            "legacy": False,
        }

    @classmethod
    def prune_checkpoints(cls, project_root: Path, keep: int = CHECKPOINT_KEEP) -> list[str]:
        """Xoá bản chụp cũ, giữ `keep` bản mới nhất. Trả về stamp đã xoá."""
        try:
            keep = max(1, int(keep))
        except (TypeError, ValueError):
            keep = CHECKPOINT_KEEP
        items = cls.list_checkpoints(project_root)
        doomed = items[keep:]
        deleted: list[str] = []
        for info in doomed:
            directory = Path(info.get("backup_dir") or "")
            if not directory.is_dir():
                continue
            try:
                shutil.rmtree(directory)
            except OSError:
                continue
            deleted.append(info.get("stamp", ""))
        return deleted
