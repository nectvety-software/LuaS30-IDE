"""Goal Mode — hệ thống tác vụ tự chủ cho AI Workbench (ADE).

Khác với một lượt hỏi/đáp, một *goal* là mục tiêu sống qua nhiều lượt agent:

    lập kế hoạch  ->  chia nhỏ thành bước  ->  sửa tệp nguồn
    ->  tự chạy lệnh debug  ->  kiểm thử  ->  xác nhận bước xong
    ->  bước kế tiếp, cho tới khi mục tiêu hoàn chỉnh.

Module này chỉ giữ **trạng thái** (mục tiêu, các bước, bằng chứng, checkpoint) và
sinh ra phần chỉ dẫn để nhồi vào system prompt. Vòng lặp thật (gọi model, chạy
tool, áp edit) nằm ở `AIChatView`; việc khôi phục tệp nằm ở `AIChangeService`.

Trạng thái lưu ở `<project>/.luas30/ai_goal.json` nên sống qua lần khởi động lại,
và ghi kiểu nguyên tử (tmp + os.replace) để không bao giờ để lại JSON cụt.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

GOAL_STATUSES = ("planning", "active", "blocked", "done", "aborted")
STEP_STATUSES = ("todo", "doing", "done", "failed")

MAX_STEPS = 12
MAX_GOAL_TITLE = 240
MAX_STEP_TITLE = 200
MAX_EVIDENCE = 600

# Ngân sách lượt cho một goal: tự chủ nhưng LUÔN có biên. Đây là chốt an toàn
# tương tự `_max_full_access_turns` của Full Access — vòng lặp tự chạy không bao
# giờ được phép chạy vô hạn.
DEFAULT_TURN_BUDGET = 40
MAX_TURN_BUDGET = 80

STATE_RELPATH = Path(".luas30") / "ai_goal.json"

STEP_MARKERS = {"todo": "[ ]", "doing": "[>]", "done": "[x]", "failed": "[!]"}


class GoalError(ValueError):
    """Thao tác goal không hợp lệ (chưa có goal, sai chỉ số bước, quá hạn mức...)."""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clip(text: str, limit: int) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    return value[: max(1, limit - 1)].rstrip() + "…"


def _as_int(value, default: int = 0) -> int:
    """Ép số chịu được JSON do người dùng sửa tay (không bao giờ raise)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class GoalStep:
    index: int
    title: str
    status: str = "todo"
    verify: str = ""
    note: str = ""
    checkpoint: str = ""

    @property
    def marker(self) -> str:
        return STEP_MARKERS.get(self.status, "[?]")

    @property
    def line(self) -> str:
        text = f"{self.marker} {self.index}. {self.title}"
        if self.verify:
            text += f"  (bằng chứng: {self.verify})"
        if self.note:
            text += f"  (lỗi: {self.note})"
        return text

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "title": self.title,
            "status": self.status,
            "verify": self.verify,
            "note": self.note,
            "checkpoint": self.checkpoint,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "GoalStep":
        status = str(payload.get("status") or "todo")
        if status not in STEP_STATUSES:
            status = "todo"
        return cls(
            index=_as_int(payload.get("index"), 0),
            title=str(payload.get("title") or ""),
            status=status,
            verify=str(payload.get("verify") or ""),
            note=str(payload.get("note") or ""),
            checkpoint=str(payload.get("checkpoint") or ""),
        )


@dataclass
class Goal:
    title: str
    status: str = "planning"
    steps: list[GoalStep] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    turn_budget: int = DEFAULT_TURN_BUDGET
    turns_used: int = 0
    blocked_reason: str = ""
    checkpoints: list[str] = field(default_factory=list)

    # ------------------------------------------------------------ truy vấn
    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def done_steps(self) -> int:
        return sum(1 for step in self.steps if step.status == "done")

    @property
    def failed_steps(self) -> int:
        return sum(1 for step in self.steps if step.status == "failed")

    @property
    def finished(self) -> bool:
        return self.status in {"done", "aborted"}

    @property
    def active(self) -> bool:
        return self.status in {"planning", "active"}

    @property
    def turns_left(self) -> int:
        return max(0, int(self.turn_budget) - int(self.turns_used))

    @property
    def exhausted(self) -> bool:
        return self.turns_left <= 0

    def current_step(self) -> GoalStep | None:
        for step in self.steps:
            if step.status == "doing":
                return step
        for step in self.steps:
            if step.status == "todo":
                return step
        return None

    def step_at(self, index: int) -> GoalStep | None:
        for step in self.steps:
            if step.index == int(index):
                return step
        return None

    @property
    def progress_text(self) -> str:
        if not self.steps:
            return "chưa có kế hoạch"
        return f"{self.done_steps}/{self.total_steps} bước"

    def plan_text(self) -> str:
        if not self.steps:
            return "(chưa chia bước)"
        return "\n".join(step.line for step in self.steps)

    # ------------------------------------------------------------ (de)serialize
    def to_dict(self) -> dict:
        return {
            "schema": 1,
            "title": self.title,
            "status": self.status,
            "steps": [step.to_dict() for step in self.steps],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "turn_budget": self.turn_budget,
            "turns_used": self.turns_used,
            "blocked_reason": self.blocked_reason,
            "checkpoints": list(self.checkpoints),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "Goal":
        status = str(payload.get("status") or "planning")
        if status not in GOAL_STATUSES:
            status = "planning"
        budget = _as_int(payload.get("turn_budget"), DEFAULT_TURN_BUDGET)
        goal = cls(
            title=str(payload.get("title") or ""),
            status=status,
            steps=[GoalStep.from_dict(item) for item in payload.get("steps") or []
                   if isinstance(item, dict)],
            created_at=str(payload.get("created_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
            turn_budget=max(1, min(MAX_TURN_BUDGET, budget)),
            turns_used=max(0, _as_int(payload.get("turns_used"), 0)),
            blocked_reason=str(payload.get("blocked_reason") or ""),
            checkpoints=[str(item) for item in payload.get("checkpoints") or []],
        )
        return goal


class GoalService:
    """Vòng đời của một goal trong một project đang mở."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root: Path | None = None
        self.goal: Goal | None = None
        if project_root:
            self.attach(project_root)

    # ------------------------------------------------------------ trạng thái
    def attach(self, project_root: Path | None) -> None:
        """Đổi project: nạp goal của project đó (mỗi project có goal riêng)."""
        if project_root:
            self.project_root = Path(project_root).expanduser().resolve()
        else:
            self.project_root = None
        self.goal = None
        self.load()

    @property
    def state_path(self) -> Path | None:
        if not self.project_root:
            return None
        return self.project_root / STATE_RELPATH

    @property
    def active(self) -> bool:
        return bool(self.goal and self.goal.active)

    def load(self) -> Goal | None:
        path = self.state_path
        if not path or not path.is_file():
            self.goal = None
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            # JSON hỏng: coi như không có goal, KHÔNG xoá tệp (người dùng còn cứu).
            self.goal = None
            return None
        if not isinstance(payload, dict):
            self.goal = None
            return None
        self.goal = Goal.from_dict(payload)
        return self.goal

    def save(self) -> None:
        path = self.state_path
        if not path or not self.goal:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        self.goal.updated_at = _now()
        fd, temp_name = tempfile.mkstemp(
            prefix="ai_goal-", suffix=".tmp", dir=str(path.parent), text=True
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(self.goal.to_dict(), handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def clear(self) -> None:
        """Bỏ goal hiện tại (xoá tệp trạng thái)."""
        path = self.state_path
        self.goal = None
        if path and path.is_file():
            try:
                path.unlink()
            except OSError:
                pass

    # ------------------------------------------------------------ vòng đời
    def start(self, title: str, *, turn_budget: int | None = None) -> Goal:
        title = _clip(title, MAX_GOAL_TITLE)
        if not title:
            raise GoalError("Goal cần một mô tả mục tiêu bằng ngôn ngữ tự nhiên.")
        budget = int(turn_budget or DEFAULT_TURN_BUDGET)
        budget = max(4, min(MAX_TURN_BUDGET, budget))
        stamp = _now()
        self.goal = Goal(
            title=title,
            status="planning",
            created_at=stamp,
            updated_at=stamp,
            turn_budget=budget,
        )
        self.save()
        return self.goal

    def set_steps(self, titles) -> Goal:
        """Nạp kế hoạch do agent chia nhỏ. Bước cũ (nếu có) bị thay hoàn toàn."""
        goal = self._require()
        cleaned: list[GoalStep] = []
        for item in list(titles or []):
            text = _clip(item, MAX_STEP_TITLE)
            if not text:
                continue
            cleaned.append(GoalStep(index=len(cleaned) + 1, title=text))
            if len(cleaned) >= MAX_STEPS:
                break
        if not cleaned:
            raise GoalError("Kế hoạch rỗng: cần ít nhất một bước.")
        goal.steps = cleaned
        goal.status = "active"
        goal.blocked_reason = ""
        self.save()
        return goal

    def mark_step(
        self,
        index: int,
        status: str,
        *,
        verify: str = "",
        note: str = "",
        checkpoint: str = "",
    ) -> GoalStep:
        goal = self._require()
        if status not in STEP_STATUSES:
            raise GoalError(f"Trạng thái bước không hợp lệ: {status}")
        step = goal.step_at(index)
        if step is None:
            raise GoalError(f"Không có bước số {index}.")
        step.status = status
        if verify:
            step.verify = _clip(verify, MAX_EVIDENCE)
        if note:
            step.note = _clip(note, MAX_EVIDENCE)
        if checkpoint:
            step.checkpoint = checkpoint
            if checkpoint not in goal.checkpoints:
                goal.checkpoints.append(checkpoint)
        if goal.status == "planning":
            goal.status = "active"
        self.save()
        return step

    def start_step(self, index: int) -> GoalStep:
        goal = self._require()
        for step in goal.steps:
            if step.status == "doing" and step.index != int(index):
                step.status = "todo"
        return self.mark_step(index, "doing")

    def complete_step(self, index: int, verify: str = "", *, checkpoint: str = "") -> GoalStep:
        step = self.mark_step(index, "done", verify=verify, checkpoint=checkpoint)
        if self.goal and self.goal.steps and all(item.status == "done" for item in self.goal.steps):
            self.finish()
        return step

    def fail_step(self, index: int, note: str = "") -> GoalStep:
        return self.mark_step(index, "failed", note=note)

    def block(self, reason: str) -> Goal:
        goal = self._require()
        goal.status = "blocked"
        goal.blocked_reason = _clip(reason, MAX_EVIDENCE) or "không rõ nguyên nhân"
        self.save()
        return goal

    def finish(self) -> Goal:
        goal = self._require()
        goal.status = "done"
        goal.blocked_reason = ""
        self.save()
        return goal

    def abort(self) -> Goal:
        goal = self._require()
        goal.status = "aborted"
        self.save()
        return goal

    def resume(self) -> Goal:
        """Mở lại goal đang `blocked` để agent thử tiếp."""
        goal = self._require()
        if goal.status == "blocked":
            goal.status = "active"
            self.save()
        return goal

    # ------------------------------------------------------------ ngân sách lượt
    def note_turn(self) -> int:
        """Ghi nhận một lượt agent đã dùng cho goal này."""
        goal = self._require()
        goal.turns_used += 1
        self.save()
        return goal.turns_used

    def record_checkpoint(self, stamp: str) -> None:
        goal = self._require()
        stamp = str(stamp or "").strip()
        if stamp and stamp not in goal.checkpoints:
            goal.checkpoints.append(stamp)
            self.save()

    # ------------------------------------------------------------ prompt
    def prompt_block(self) -> str:
        """Khối chỉ dẫn nhồi vào system prompt khi goal đang chạy.

        Rỗng khi không có goal hoặc goal đã kết thúc — lúc đó agent làm việc
        như một lượt hỏi/đáp bình thường.

        Tên op ở đây PHẢI trùng `GOAL_OPS` trong `ai_agent_protocol.py` và trùng
        bộ xử lý trong `AIChatView._run_goal_tool()`. Từng có ba nơi ghi ba kiểu
        (`step_done` vs `done`) — model gọi đúng theo prompt nhưng handler từ chối,
        và triệu chứng là "mục tiêu không bao giờ tiến được" chứ không phải một
        lỗi rõ ràng.
        """
        goal = self.goal
        if not goal or not goal.active:
            return ""
        current = goal.current_step()
        if goal.status == "planning" or not goal.steps:
            phase = (
                "GIAI ĐOẠN 1 — LẬP KẾ HOẠCH. Chưa có kế hoạch. Hãy đọc code cần "
                "thiết rồi chia mục tiêu thành 3–8 bước cụ thể, kiểm chứng được, "
                'và gọi tool `goal` với op="plan" (args.steps). Không sửa tệp trong '
                "cùng lượt với op=plan."
            )
        elif current is None:
            phase = (
                'Không còn bước nào đang mở. Nếu mục tiêu đã đạt, gọi op="finish" '
                'kèm bằng chứng tổng kết; nếu chưa, gọi op="blocked" kèm lý do.'
            )
        else:
            phase = (
                f"BƯỚC ĐANG LÀM: {current.index}. {current.title}\n"
                "Quy trình khép kín BẮT BUỘC cho bước này: sửa tệp nguồn "
                "(luas30-edit) → tự chạy lệnh cần thiết (luas30-shell) → kiểm thử "
                "bằng tool `problems`/`run_app` → chỉ khi có BẰNG CHỨNG mới gọi "
                '`goal` op="done" (args.step, args.verify).\n'
                "Nếu bước hỏng: sửa và thử lại; sau 2 lần vẫn hỏng thì gọi "
                'op="fail" (args.step, args.note) rồi op="blocked" kèm lý do cụ thể.'
            )
        return (
            "<goal_mode>\n"
            f"MỤC TIÊU: {goal.title}\n"
            f"TRẠNG THÁI: {goal.status} · {goal.progress_text} · "
            f"còn {goal.turns_left}/{goal.turn_budget} lượt\n"
            f"{goal.plan_text()}\n\n"
            f"{phase}\n\n"
            "Giao thức tool `goal` (một khối mỗi lần):\n"
            "```luas30-tool\n"
            '{"tool":"goal","args":{"op":"plan","steps":["...","..."]},"reason":"Chia nhỏ mục tiêu"}\n'
            "```\n"
            'op khác: "start" (args.step), "done" (args.step, args.verify), '
            '"fail" (args.step, args.note), "blocked" (args.reason), "finish", "status".\n'
            "KHÔNG được báo xong khi chưa có bằng chứng thật (kết quả problems sạch, "
            "lệnh đã chạy, hoặc run_app đã chụp ảnh). Không tự bịa kết quả tool.\n"
            "</goal_mode>"
        )

    def turn_prompt(self) -> str:
        """Câu nhắc dùng để tự tiếp tục vòng lặp sau mỗi lượt."""
        goal = self.goal
        if not goal or not goal.active:
            return "Continue"
        current = goal.current_step()
        if goal.status == "planning" or not goal.steps:
            return "Chia mục tiêu thành các bước kiểm chứng được và gọi tool goal op=plan."
        if not current:
            return "Mọi bước đã xong — gọi tool goal op=finish kèm bằng chứng tổng kết."
        return (
            f"Tiếp tục bước {current.index}: {current.title}. "
            "Thực hiện rồi kiểm thử; chỉ gọi goal op=done khi có bằng chứng."
        )

    def summary(self) -> dict:
        goal = self.goal
        if not goal:
            return {"active": False, "status": "none", "progress": "", "title": ""}
        current = goal.current_step()
        return {
            "active": goal.active,
            "status": goal.status,
            "title": goal.title,
            "progress": goal.progress_text,
            "done_steps": goal.done_steps,
            "total_steps": goal.total_steps,
            "current_step": current.title if current else "",
            "current_index": current.index if current else 0,
            "turns_left": goal.turns_left,
            "blocked_reason": goal.blocked_reason,
            "checkpoints": list(goal.checkpoints),
        }

    # ------------------------------------------------------------ nội bộ
    def _require(self) -> Goal:
        if not self.goal:
            raise GoalError("Chưa có goal nào. Bắt đầu bằng /goal <mô tả mục tiêu>.")
        return self.goal
