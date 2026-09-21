from __future__ import annotations

import difflib
import json
import os
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
        created_backup = False
        if target.is_file():
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

        change_set.changes.remove(change)
        self.last_backup_dir = backup_dir if created_backup else self.last_backup_dir
        return target, (backup_dir if created_backup else None)

    def apply(self, change_set: PreparedChangeSet | None = None) -> tuple[list[Path], Path | None]:
        change_set = change_set or self.pending
        if not change_set:
            raise ValueError("There are no pending AI code changes.")

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup_dir = change_set.project_root / ".luas30" / "ai-backups" / stamp
        applied: list[Path] = []
        created_backup = False

        try:
            for change in change_set.changes:
                target = change.absolute_path
                target.parent.mkdir(parents=True, exist_ok=True)

                if target.is_file():
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
