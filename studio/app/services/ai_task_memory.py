"""Bộ nhớ CÔNG VIỆC ĐANG LÀM (working memory) cho AI Workbench.

Vì sao có file này
------------------
Một lượt hỏi/đáp thì không cần nhớ gì. Nhưng khi agent làm một việc dài — sửa 6 tệp,
chạy build, sửa tiếp, kiểm thử, sửa tiếp — có ba thứ chắc chắn làm nó mất mạch:

  1. **Trần ngữ cảnh.** `AIChatView._start_request` chỉ gửi lại vài tin nhắn gần
     nhất. Việc đã bàn ở đầu phiên biến mất KHÔNG một dấu vết.
  2. **Khởi động lại.** Đóng IDE rồi mở lại: phiên chat cũ vẫn còn, nhưng không có
     gì nói "đang dở bước 3".
  3. **Phiên chat mới.** Bấm /new là mất sạch ngữ cảnh.

Goal Mode (`ai_goal_service.py`) đã giải (2) và (3) — nhưng chỉ khi người dùng gõ
`/goal`, và nó chỉ giữ **danh sách bước**. File này giữ phần còn lại: đang làm gì,
đã QUYẾT ĐỊNH gì và vì sao, đã đụng tệp nào, việc kế tiếp là gì — và **luôn bật**,
không cần lệnh nào.

Đây không phải nhật ký
----------------------
Ghi mọi bước nhỏ vào đây là tự biến nó thành rác và làm loãng prompt. Chỉ ghi thứ
đáng nhớ: mục tiêu, bước, phát hiện/quyết định, tệp đã sửa, việc kế tiếp.

Trạng thái ở `<project>/.luas30/ai_task.json`, ghi kiểu nguyên tử (tmp +
`os.replace`) để không bao giờ để lại JSON cụt. JSON hỏng do sửa tay được coi là
"chưa có gì" nhưng **không** bị xoá — người dùng còn cứu được.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.services.ai_agent_protocol import TASK_OPS

TASK_STATUSES = ("idle", "working", "blocked", "done")
STEP_STATUSES = ("todo", "doing", "done", "failed")

MAX_OBJECTIVE = 400
MAX_STEP_TITLE = 200
MAX_STEP_COUNT = 16
MAX_FACTS = 24
MAX_FACT = 400
MAX_FILES = 40
MAX_NOTE = 240
MAX_NEXT = 400
MAX_BLOCKERS = 8
MAX_BLOCKER = 400
MAX_EVIDENCE = 6
MAX_EVIDENCE_ITEM = 300
# Trần lượt chỉ để JSON không phình vô hạn; vòng lặp thật đã bị chặn ở AIChatView.
MAX_TURNS = 100_000

STATE_RELPATH = Path(".luas30") / "ai_task.json"

STEP_MARKERS = {"todo": "[ ]", "doing": "[>]", "done": "[x]", "failed": "[!]"}


class TaskMemoryError(ValueError):
    """Thao tác bộ nhớ không hợp lệ (op lạ, thiếu tham số, vượt hạn mức...)."""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clip(text: str, limit: int) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    return value[: max(1, limit - 1)].rstrip() + "…"


def _as_int(value, default: int = 0) -> int:
    """Ép số chịu được JSON sửa tay (không bao giờ raise)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class TaskStep:
    index: int
    title: str
    status: str = "todo"

    def to_dict(self) -> dict:
        return {"index": self.index, "title": self.title, "status": self.status}


@dataclass
class TaskFile:
    path: str
    note: str = ""

    def to_dict(self) -> dict:
        return {"path": self.path, "note": self.note}


@dataclass
class TaskState:
    objective: str = ""
    status: str = "idle"
    steps: list[TaskStep] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)
    files: list[TaskFile] = field(default_factory=list)
    next_action: str = ""
    blockers: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    turns: int = 0
    created_at: str = ""
    updated_at: str = ""

    # -------------------------------------------------------------- truy vấn
    @property
    def active(self) -> bool:
        return self.status in {"working", "blocked"}

    @property
    def has_work(self) -> bool:
        """Có gì đáng nhớ không. Rỗng thì KHÔNG nhồi khối vào prompt."""
        return bool(
            self.objective or self.steps or self.facts or self.files
            or self.next_action or self.blockers
        )

    @property
    def should_continue(self) -> bool:
        """Còn việc tự làm được không — dùng cho vòng lặp tự tiếp tục."""
        return self.status == "working" and bool(self.next_action)

    @property
    def done_steps(self) -> int:
        return sum(1 for step in self.steps if step.status == "done")

    @property
    def current_step(self) -> TaskStep | None:
        for step in self.steps:
            if step.status == "doing":
                return step
        for step in self.steps:
            if step.status == "todo":
                return step
        return None

    def progress_text(self) -> str:
        if not self.steps:
            return "chưa có kế hoạch"
        return f"{self.done_steps}/{len(self.steps)} bước"

    def plan_text(self) -> str:
        if not self.steps:
            return "(chưa chia bước)"
        return "\n".join(
            f"{STEP_MARKERS.get(step.status, '[ ]')} {step.index}. {step.title}"
            for step in self.steps
        )

    def to_dict(self) -> dict:
        return {
            "schema": 1,
            "objective": self.objective,
            "status": self.status,
            "steps": [step.to_dict() for step in self.steps],
            "facts": list(self.facts),
            "files": [item.to_dict() for item in self.files],
            "next": self.next_action,
            "blockers": list(self.blockers),
            "evidence": list(self.evidence),
            "turns": self.turns,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def _state_from_dict(payload: dict) -> TaskState:
    """Đọc JSON chịu được dữ liệu bẩn; KHÔNG bao giờ raise."""
    status = str(payload.get("status") or "idle").strip().lower()
    if status not in TASK_STATUSES:
        status = "idle"

    steps: list[TaskStep] = []
    for raw in payload.get("steps") or []:
        if not isinstance(raw, dict):
            continue
        step_status = str(raw.get("status") or "todo").strip().lower()
        if step_status not in STEP_STATUSES:
            step_status = "todo"
        steps.append(
            TaskStep(
                index=_as_int(raw.get("index"), len(steps) + 1),
                title=_clip(raw.get("title"), MAX_STEP_TITLE),
                status=step_status,
            )
        )
        if len(steps) >= MAX_STEP_COUNT:
            break

    files: list[TaskFile] = []
    for raw in payload.get("files") or []:
        if isinstance(raw, dict):
            path = _clip(raw.get("path"), MAX_STEP_TITLE)
            note = _clip(raw.get("note"), MAX_NOTE)
        else:
            path, note = _clip(raw, MAX_STEP_TITLE), ""
        if path:
            files.append(TaskFile(path=path, note=note))
        if len(files) >= MAX_FILES:
            break

    def _text_list(key: str, limit: int, item_limit: int) -> list[str]:
        rows: list[str] = []
        for raw in payload.get(key) or []:
            text = _clip(raw, item_limit)
            if text:
                rows.append(text)
            if len(rows) >= limit:
                break
        return rows

    return TaskState(
        objective=_clip(payload.get("objective"), MAX_OBJECTIVE),
        status=status,
        steps=steps,
        facts=_text_list("facts", MAX_FACTS, MAX_FACT),
        files=files,
        next_action=_clip(payload.get("next"), MAX_NEXT),
        blockers=_text_list("blockers", MAX_BLOCKERS, MAX_BLOCKER),
        evidence=_text_list("evidence", MAX_EVIDENCE, MAX_EVIDENCE_ITEM),
        turns=max(0, min(MAX_TURNS, _as_int(payload.get("turns"), 0))),
        created_at=str(payload.get("created_at") or ""),
        updated_at=str(payload.get("updated_at") or ""),
    )


class TaskMemory:
    """Bộ nhớ công việc theo TỪNG project, sống qua khởi động lại và qua phiên chat.

    Không giữ trạng thái UI và không tự gọi model — chỉ đọc/ghi tệp JSON và sinh
    ra khối chỉ dẫn. Nhờ vậy test được bằng tệp thật trên thư mục tạm.
    """

    def __init__(self, project_root: Path | str | None = None) -> None:
        self._root: Path | None = None
        self.state = TaskState()
        if project_root:
            self.attach(project_root)

    # ------------------------------------------------------------- vòng đời
    @property
    def root(self) -> Path | None:
        return self._root

    @property
    def path(self) -> Path | None:
        return (self._root / STATE_RELPATH) if self._root else None

    def attach(self, project_root: Path | str | None) -> None:
        """Gắn vào một project và nạp bộ nhớ của project đó.

        Gọi với `None` (không có project nào mở) thì bộ nhớ rỗng và
        `prompt_block()` trả "" — agent chạy như trước, không có khối thừa.
        """
        if not project_root:
            self._root = None
            self.state = TaskState()
            return
        try:
            root = Path(project_root).expanduser().resolve()
        except OSError:
            root = Path(project_root)
        self._root = root
        self.state = self.load()

    def load(self) -> TaskState:
        path = self.path
        if path is None or not path.is_file():
            return TaskState()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            # JSON cụt/hỏng do sửa tay: coi như chưa có gì, nhưng KHÔNG xoá tệp —
            # người dùng còn mở ra cứu. Ghi đè lần sau sẽ thay nó bằng JSON hợp lệ.
            return TaskState()
        if not isinstance(payload, dict):
            return TaskState()
        return _state_from_dict(payload)

    def save(self) -> None:
        """Ghi nguyên tử: không bao giờ để lại JSON cụt giữa đường."""
        path = self.path
        if path is None:
            return
        self.state.updated_at = _now()
        if not self.state.created_at:
            self.state.created_at = self.state.updated_at
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".json", prefix="ai_task_", dir=str(path.parent),
            delete=False, encoding="utf-8",
        )
        try:
            with handle:
                json.dump(self.state.to_dict(), handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            os.replace(handle.name, path)
        except OSError:
            try:
                os.unlink(handle.name)
            except OSError:
                pass
            raise

    # ------------------------------------------------------------- thao tác
    def _touch(self, status: str | None = None) -> None:
        if status:
            self.state.status = status
        self.save()

    def set_objective(self, text: str) -> TaskState:
        self.state.objective = _clip(text, MAX_OBJECTIVE)
        if self.state.objective and self.state.status in {"idle", "done"}:
            self.state.status = "working"
        self._touch()
        return self.state

    def set_plan(self, steps) -> TaskState:
        titles: list[str] = []
        for raw in steps or []:
            title = _clip(raw, MAX_STEP_TITLE)
            if title:
                titles.append(title)
            if len(titles) >= MAX_STEP_COUNT:
                break
        if not titles:
            raise TaskMemoryError("plan cần args.steps là danh sách bước không rỗng.")
        self.state.steps = [
            TaskStep(index=i, title=title) for i, title in enumerate(titles, start=1)
        ]
        if self.state.status in {"idle", "done"}:
            self.state.status = "working"
        self._touch()
        return self.state

    def _resolve_step(self, ref) -> TaskStep:
        """Chọn bước theo số thứ tự (1-based) hoặc theo khúc tên."""
        if not self.state.steps:
            raise TaskMemoryError("chưa có kế hoạch — gọi plan trước.")
        text = str(ref or "").strip()
        if not text:
            step = self.state.current_step
            if step is None:
                raise TaskMemoryError("không còn bước nào đang mở.")
            return step
        number = _as_int(text, 0)
        if number:
            for step in self.state.steps:
                if step.index == number:
                    return step
            raise TaskMemoryError(f"không có bước {number}.")
        lowered = text.lower()
        for step in self.state.steps:
            if lowered in step.title.lower():
                return step
        raise TaskMemoryError(f"không khớp bước nào với {text!r}.")

    def mark_step(self, ref, status: str = "done") -> TaskStep:
        status = str(status or "done").strip().lower()
        if status not in STEP_STATUSES:
            raise TaskMemoryError(
                f"args.state phải là một trong {', '.join(STEP_STATUSES)}."
            )
        step = self._resolve_step(ref)
        step.status = status
        if status == "doing":
            self.state.status = "working"
        self._touch()
        return step

    def add_fact(self, text: str) -> TaskState:
        fact = _clip(text, MAX_FACT)
        if not fact:
            raise TaskMemoryError("fact cần args.text.")
        # Ghi lại y hệt thì bỏ qua — tránh phình danh sách vì model lặp.
        if fact not in self.state.facts:
            self.state.facts.append(fact)
            del self.state.facts[:-MAX_FACTS]
        self._touch()
        return self.state

    def note_file(self, path: str, note: str = "") -> TaskState:
        value = _clip(path, MAX_STEP_TITLE)
        if not value:
            raise TaskMemoryError("file cần args.path.")
        clean = _clip(note, MAX_NOTE)
        for item in self.state.files:
            if item.path == value:
                if clean:
                    item.note = clean
                break
        else:
            self.state.files.append(TaskFile(path=value, note=clean))
            del self.state.files[:-MAX_FILES]
        self._touch()
        return self.state

    def note_files(self, paths, note: str = "") -> TaskState:
        """Ghi nhiều tệp trong MỘT lần lưu.

        Vòng lặp thật gọi hàm này sau mỗi lần áp code; gọi `note_file` từng tệp sẽ
        ghi đĩa N lần cho cùng một thao tác.
        """
        changed = False
        for raw in paths or []:
            value = _clip(raw, MAX_STEP_TITLE)
            if not value:
                continue
            for item in self.state.files:
                if item.path == value:
                    break
            else:
                self.state.files.append(TaskFile(path=value, note=_clip(note, MAX_NOTE)))
                del self.state.files[:-MAX_FILES]
                changed = True
        if changed:
            self._touch()
        return self.state

    def set_next(self, text: str) -> TaskState:
        self.state.next_action = _clip(text, MAX_NEXT)
        if not self.state.next_action and self.state.status == "working":
            # Không còn việc kế tiếp mà vẫn "working" là trạng thái nói dối.
            self.state.status = "done" if self.state.steps else "idle"
        self._touch()
        return self.state

    def block(self, reason: str) -> TaskState:
        text = _clip(reason, MAX_BLOCKER)
        if not text:
            raise TaskMemoryError("blocked cần args.reason.")
        if text not in self.state.blockers:
            self.state.blockers.append(text)
            del self.state.blockers[:-MAX_BLOCKERS]
        self._touch("blocked")
        return self.state

    def unblock(self, note: str = "") -> TaskState:
        self.state.blockers.clear()
        if note:
            self.add_fact(f"Đã gỡ tắc: {_clip(note, MAX_NOTE)}")
        self._touch("working" if self.state.steps else "idle")
        return self.state

    def finish(self, verify: str = "") -> TaskState:
        proof = _clip(verify, MAX_EVIDENCE_ITEM)
        if proof and proof not in self.state.evidence:
            self.state.evidence.append(proof)
            del self.state.evidence[:-MAX_EVIDENCE]
        self.state.next_action = ""
        self.state.blockers.clear()
        for step in self.state.steps:
            if step.status in {"todo", "doing"}:
                step.status = "done"
        self._touch("done")
        return self.state

    def reset(self, reason: str = "") -> TaskState:
        created = self.state.created_at
        self.state = TaskState(created_at=created)
        if reason:
            self.state.facts.append(f"Bộ nhớ trước đã xoá: {_clip(reason, MAX_NOTE)}")
        self._touch()
        return self.state

    def note_turn(self, count: int = 1) -> None:
        self.state.turns = max(0, min(MAX_TURNS, self.state.turns + max(0, int(count))))
        self.save()

    def record_evidence(self, kind: str, text: str) -> None:
        """Ghi bằng chứng QUAN SÁT ĐƯỢC (không do model tự khai).

        Gọi từ vòng lặp thật khi tệp đã được áp hoặc lệnh đã chạy xong — nhờ vậy
        bộ nhớ vẫn có ích kể cả khi model quên gọi tool `task`.
        """
        label = _clip(kind, 40)
        body = _clip(text, MAX_EVIDENCE_ITEM)
        if not body:
            return
        row = f"{label}: {body}" if label else body
        if row in self.state.evidence:
            return
        self.state.evidence.append(row)
        del self.state.evidence[:-MAX_EVIDENCE]
        self.save()

    # ------------------------------------------------------------- tool `task`
    def handle_op(self, op: str, args: dict | None = None) -> str:
        """Một cửa cho tool `task`; trả về mô tả kết quả để đưa lại cho model.

        `op` được đối chiếu với `TASK_OPS` của `ai_agent_protocol` — nguồn duy nhất
        mà prompt cũng đọc, nên model gọi theo prompt thì handler không thể từ chối.
        """
        args = dict(args or {})
        name = str(op or "status").strip().lower()
        if name not in TASK_OPS:
            raise TaskMemoryError(
                f"op {name!r} không hợp lệ; dùng một trong: {', '.join(TASK_OPS)}."
            )
        if self._root is None:
            raise TaskMemoryError(
                "chưa mở project nào nên không có chỗ ghi bộ nhớ công việc."
            )

        if name == "status":
            return self.summary_text()
        if name == "objective":
            state = self.set_objective(args.get("text") or args.get("objective") or "")
            return f"Đã ghi mục tiêu:\n{state.objective}"
        if name == "plan":
            state = self.set_plan(args.get("steps") or [])
            return f"Đã ghi kế hoạch {state.progress_text()}:\n{state.plan_text()}"
        if name == "step":
            step = self.mark_step(args.get("step"), args.get("state") or "done")
            return f"Bước {step.index} = {step.status}: {step.title}"
        if name == "fact":
            self.add_fact(args.get("text") or args.get("fact") or "")
            return "Đã ghi vào ghi chú."
        if name == "file":
            self.note_file(args.get("path") or args.get("file") or "", args.get("note") or "")
            return "Đã ghi tệp đã đụng."
        if name == "next":
            state = self.set_next(args.get("text") or args.get("next") or "")
            return (
                f"Việc kế tiếp: {state.next_action}"
                if state.next_action
                else "Đã xoá việc kế tiếp (coi như không còn gì tự làm)."
            )
        if name == "blocked":
            state = self.block(args.get("reason") or args.get("text") or "")
            return f"Đã đánh dấu tắc:\n" + "\n".join(state.blockers)
        if name == "unblock":
            self.unblock(args.get("note") or "")
            return "Đã gỡ tắc, quay lại trạng thái working."
        if name == "done":
            self.finish(args.get("verify") or args.get("evidence") or "")
            return "Đã đánh dấu hoàn thành."
        self.reset(args.get("reason") or "")
        return "Đã xoá bộ nhớ công việc."

    # ------------------------------------------------------------- prompt/UI
    def prompt_block(self) -> str:
        """Khối nhồi vào system prompt. Rỗng khi chưa có gì đáng nhớ.

        Luôn được gọi ở MỌI lượt (khác `<goal_mode>` chỉ có khi bật /goal) — đó là
        điểm mấu chốt để agent biết mình đang dở việc gì ở lượt đầu của một phiên
        chat hoàn toàn mới.
        """
        state = self.state
        if self._root is None or not state.has_work:
            return ""
        lines = [
            "<task_memory>",
            "Bộ nhớ công việc của project này (tự động lưu, sống qua khởi động lại).",
        ]
        if state.objective:
            lines.append(f"MỤC TIÊU: {state.objective}")
        lines.append(
            f"TRẠNG THÁI: {state.status} · {state.progress_text()}"
            + (f" · cập nhật {state.updated_at}" if state.updated_at else "")
        )
        if state.steps:
            lines.append("KẾ HOẠCH:\n" + state.plan_text())
        if state.facts:
            lines.append("GHI CHÚ / QUYẾT ĐỊNH:\n" + "\n".join(f"- {f}" for f in state.facts))
        if state.files:
            lines.append(
                "TỆP ĐÃ ĐỤNG:\n"
                + "\n".join(
                    f"- {item.path}" + (f" — {item.note}" if item.note else "")
                    for item in state.files
                )
            )
        if state.next_action:
            lines.append(f"VIỆC KẾ TIẾP: {state.next_action}")
        if state.blockers:
            lines.append("ĐANG TẮC:\n" + "\n".join(f"- {b}" for b in state.blockers))
        if state.evidence:
            lines.append("BẰNG CHỨNG ĐÃ CÓ:\n" + "\n".join(f"- {e}" for e in state.evidence))
        lines.append(
            "Cập nhật bằng tool `task` khi có gì thay đổi đáng nhớ; đừng kể lại "
            "từng bước nhỏ."
        )
        lines.append("</task_memory>")
        return "\n".join(lines)

    def summary_text(self) -> str:
        if not self.state.has_work:
            return "Bộ nhớ công việc đang trống."
        return self.prompt_block().replace("<task_memory>", "").replace("</task_memory>", "").strip()

    def summary(self) -> dict:
        state = self.state
        current = state.current_step
        return {
            "active": state.active,
            "status": state.status,
            "objective": state.objective,
            "progress": state.progress_text(),
            "done_steps": state.done_steps,
            "total_steps": len(state.steps),
            "current_step": current.title if current else "",
            "next": state.next_action,
            "blockers": list(state.blockers),
            "turns": state.turns,
            "has_work": state.has_work,
            "should_continue": state.should_continue,
        }
