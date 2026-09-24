# Bộ nhớ công việc của AI Agent — `ai_task_memory.py` (1.0.2)

Tài liệu này giải thích **vì sao** có bộ nhớ công việc, **cái gì** được lưu, và
**những chỗ hỏng im lặng** phải tránh khi sửa. Đọc trước khi đụng vào
`studio/app/services/ai_task_memory.py`, `AIChatView` hoặc tool `task`.

## 1. Vấn đề: agent không code dài được

Một lượt hỏi/đáp thì không cần nhớ gì. Nhưng khi agent làm một việc dài — sửa 6 tệp,
build, sửa tiếp, kiểm thử, sửa tiếp — có bốn thứ làm nó mất mạch, và **cả bốn đều
hỏng im lặng** (không exception, không log, chỉ thấy agent làm sai):

| # | Nguyên nhân | Triệu chứng người dùng thấy |
|---|---|---|
| 1 | `_start_request` chỉ gửi `self._history[-16:]` | Đầu phiên biến mất; agent hỏi lại đúng thứ vừa thống nhất xong |
| 2 | Không có bộ nhớ nào | Đóng IDE mở lại là mất sạch ngữ cảnh, làm lại từ đầu |
| 3 | `/new` xoá hội thoại | Phiên mới hoàn toàn mù về việc đang dở |
| 4 | Trần lượt 8/32 quá thấp | Việc nhiều tệp bị dừng giữa chừng, người dùng phải gõ "làm tiếp đi" |

Goal Mode (`ai_goal_service.py`) đã giải (2) và (3) — nhưng **chỉ khi người dùng gõ
`/goal`**, và nó chỉ giữ **danh sách bước**. Bộ nhớ công việc giữ phần còn lại, và
**luôn bật**.

## 2. Lưu cái gì

`<project>/.luas30/ai_task.json`:

```json
{
  "schema": 1,
  "objective": "Thêm màn hình shop; xong khi /run hiện ra và problems sạch",
  "status": "working",
  "steps": [{"index": 1, "title": "Đọc template", "status": "done"}],
  "facts": ["Dùng rect() chứ không phải drawImage()"],
  "files": [{"path": "src/shop.lua", "note": "màn hình mới"}],
  "next": "Viết src/shop.lua rồi chạy luac -p",
  "blockers": [],
  "evidence": ["Lệnh đã chạy: luac -p src/shop.lua → exit 0"],
  "turns": 7,
  "created_at": "…", "updated_at": "…"
}
```

- `status`: `idle | working | blocked | done`
- `steps[].status`: `todo | doing | done | failed`
- `evidence` gồm **bằng chứng quan sát được**, không phải model tự khai: tệp đã ghi
  (`on_code_changes_applied`) và lệnh đã chạy kèm mã thoát (`on_shell_command_finished`).

**Đây không phải nhật ký.** Ghi mọi bước nhỏ vào đây là tự biến nó thành rác và làm
loãng prompt. Chỉ ghi thứ đáng nhớ.

## 3. Tool `task` — và vì sao `TASK_OPS` phải là MỘT nguồn

`TASK_OPS` nằm ở `ai_agent_protocol.py` (cạnh `GOAL_OPS`), và `ai_task_memory.py`
**import lại đúng tuple đó** cho handler. Prompt quảng bá từ cùng tuple ấy.

> ⚠️ Đây là bài học trả giá thật của Goal Mode: từng có **ba nơi ghi ba kiểu**
> (`step_done` vs `done`). Model gọi đúng theo prompt, handler từ chối, và triệu
> chứng là *"mục tiêu không bao giờ tiến được"* — không phải một lỗi rõ ràng.
> `TASK_OPS` chặn hẳn bằng import nên hai bên không thể lệch.

Ops: `status` · `objective` · `plan` · `step` · `fact` · `file` · `next` ·
`blocked` · `unblock` · `done` · `reset`.

Thêm op mới thì thêm **một chỗ** (`TASK_OPS`) rồi xử lý trong `handle_op`; quên
nhánh xử lý thì `validate_ai_task_memory.py` đỏ ngay (nó gọi thử **mọi** op).

> ⚠️ Tool `task` phải nằm trong `TOOL_NAMES`. Parser lọc theo danh sách đó: thiếu
> tên ⇒ khối tool bị bỏ **im lặng** (0 action, không lỗi).

## 4. Nhồi vào prompt thế nào

`AIChatView._system_prompt` ghép, theo thứ tự: chỉ dẫn gốc → `agent_protocol_prompt(...)`
→ `<goal_mode>` (chỉ khi bật `/goal`) → **`<task_memory>` (LUÔN, khi có project)** →
`<earlier_work>` → bundle codebase.

- `<task_memory>` rỗng khi chưa có gì đáng nhớ ⇒ không có khối thừa.
- Không có project nào mở ⇒ `task_memory=False`, prompt y như trước.

### `<earlier_work>` — bản tóm tắt phần hội thoại đã ra khỏi cửa sổ

`_earlier_work_digest()` là hàm **THUẦN**: không gọi model, không tốn lượt. Nó lấy
câu hỏi người dùng, câu trả lời và các hành động đã chạy ở phần cũ, nén thành một
dòng mỗi lượt (trần `DIGEST_MAX_ROWS=60` dòng / `DIGEST_MAX_CHARS=4000` ký tự).

Cửa sổ gửi nguyên văn: `REPLAY_WINDOW = 40` (Goal Mode: 60).

> ⚠️ **Đừng "tối ưu" bằng cách cắt cửa sổ nhỏ lại.** Con số 16 cũ là đúng cái đã
> làm đầu phiên biến mất im lặng. Nếu cần giảm prompt thì giảm `DIGEST_MAX_CHARS`,
> đừng bỏ bản tóm tắt — bỏ nó là quay lại lỗi cũ mà không có gì báo.

## 5. Code dài hơn: trần lượt + nhắc một lần

- Trần lượt: `_max_agent_turns = 24`, `_max_full_access_turns = 120`. **Luôn có
  biên** — vòng lặp tự chạy không bao giờ vô hạn, hết trần thì dừng và **giữ
  nguyên** code đang dở.
- `_nudge_unfinished_work()`: model định kết thúc lượt bằng văn xuôi trong khi
  chính sổ của nó ghi còn `next` ⇒ nhắc **đúng MỘT lần** cho mỗi lượt người dùng.
  Nhắc xong mà vẫn dừng thì tôn trọng quyết định đó.

  Không nhắc khi: đang `plan` mode, Goal Mode đang chạy (nó có vòng lặp riêng —
  chồng thêm là mở đường cho hai vòng lặp giành nhau quyết định dừng), hoặc sổ
  không có `next`.

> ⚠️ Hai guard cũ `validate_ai_agent_shell.py` / `validate_ai_full_access_stop.py`
> từng **ghim cứng** `= 8` và `= 32`. Đã đổi thành canh **bất biến** (có biên, Full
> Access rộng hơn nhưng vẫn có biên) — ghim số thì mỗi lần chỉnh ngân sách là đỏ
> oan, và người ta sẽ "sửa" guard bằng cách đổi số.

## 6. Bất biến — đừng phá

1. **Ghi nguyên tử** (`tempfile` + `os.replace`). Không bao giờ để lại JSON cụt.
2. **JSON hỏng thì coi như rỗng nhưng KHÔNG xoá tệp** — người dùng còn mở ra cứu.
3. **Tách theo project**: `attach(root)` nạp đúng sổ của project đó. Quên bước này
   trong `set_project_root` ⇒ agent tưởng đang dở việc của project khác.
4. **`next` rỗng khi vẫn `working` là trạng thái nói dối** ⇒ `set_next` tự hạ
   trạng thái. Nếu không, vòng lặp tự tiếp tục sẽ đuổi theo một việc không tồn tại.
5. **Mọi danh sách đều có trần** (`MAX_FACTS`, `MAX_FILES`, `MAX_STEP_COUNT`, …) và
   luôn cắt ở **đầu cũ** để giữ mới nhất.
6. **Không có project ⇒ no-op**, không raise (agent vẫn chạy được khi chưa mở dự án).

## 7. Kiểm chứng

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
  py -3.12 -u tools/validate_ai_task_memory.py
```

Bài kiểm soi bốn tầng: hợp đồng tĩnh (tool trong `TOOL_NAMES`, `TASK_OPS` khớp
handler, prompt nhắc đủ op) → dịch vụ thật trên thư mục tạm (ghi/đọc/xoá, bền qua
khởi động lại, JSON nguyên tử, chịu JSON hỏng, tách project, trần) → prompt →
**thân hàm thật** của `AIChatView._earlier_work_digest` và
`_nudge_unfinished_work` gọi trên stub.

Đã **kiểm chứng ngược 8/8**: phá từng hành vi (rút `task` khỏi `TOOL_NAMES`, cắt
cửa sổ về 16, hạ trần về 8, ngắt hai hàm khỏi chỗ gọi, `should_continue` luôn
`True`, xoá tệp JSON hỏng) ⇒ bài kiểm exit 1 và kêu **đúng dòng**; khôi phục ⇒ xanh.
Harness: `build/_rp_task_memory.py`.

> ⚠️ Chứng minh ngược phải **y nguyên bản gốc**. Lần trước, một lần revert "gần
> giống" còn sót lại `dismiss()` nên chỉ 2/3 guard đỏ — guard thứ ba chưa bao giờ
> được chứng minh là có thật.

## 8. Ghi chú về ZCode

Người dùng yêu cầu "như ZCode". Đã tra repo công khai `zai-org/ZCode`: **không có
tài liệu nào mô tả tính năng runtime của agent**. `README.md` chỉ nói setup/dev;
`DESIGN.md` là design system UI (chỉ nhắc "long sessions" như *mục tiêu thiết kế*);
`AGENTS.md` là hướng dẫn dev cho repo; `apps/zcode-cli/tools/prompt-trajectory` là
tool debug ghi lại prompt. Vì vậy không thể liệt kê "ZCode có gì" từ bằng chứng —
phần triển khai ở đây bám vào đúng hai yêu cầu nêu rõ: **code dài hơn** và **nhớ
việc đang làm**.
