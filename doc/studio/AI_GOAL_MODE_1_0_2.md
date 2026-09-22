# Goal Mode — Hệ thống Tác vụ tự chủ (ADE)

Mốc: **1.0.2** · Studio `1.0.2` · liên quan: `AI_WORKBENCH_V1_1_15_0.md`,
`AI_AGENT_SHELL_1_14_0.md`, `AI_DESIGN_TOOLS.md`

## Mục đích

Một lượt hỏi/đáp trả về một đoạn mã. **Goal Mode** nhận một *mục tiêu* rồi tự
đóng vòng lặp:

```
lập kế hoạch  →  chia nhỏ thành bước  →  sửa tệp nguồn
     →  tự chạy lệnh debug  →  kiểm thử  →  xác nhận từng bước
     →  bước kế tiếp, cho tới khi mục tiêu hoàn chỉnh
```

Người dùng điều khiển bằng ngôn ngữ tự nhiên qua cú pháp `/goal`, không phải
bằng cách ghép từng prompt nhỏ.

## Bốn trụ cột và chỗ cài đặt

| Trụ cột | Cài ở đâu | Kiểm bằng |
|---|---|---|
| Goal Mode (mục tiêu/bước/bằng chứng) | `app/services/ai_goal_service.py` + `AIChatView._run_goal_tool()` | `tools/validate_ai_goal_mode.py` |
| Phục hồi / quay lui trạng thái | `app/services/ai_change_service.py` (`restore_checkpoint`, `rewind_to`) + `MainWindow._rollback_ai_checkpoint()` | `tools/validate_ai_goal_rollback.py` |
| Tối ưu hoá bộ nhớ đệm | `app/services/codebase_context_service.py` | `tools/validate_ai_context_cache.py` |
| Quản lý quyền hạn chặt chẽ | `ACCESS_MODES` + `_edit_policy()` / `_shell_policy()` (đã có từ 1.15.0) | `tools/validate_ai_workbench.py` |

## 1. Goal Mode

### Lệnh

```
/goal <mô tả mục tiêu>   bắt đầu mục tiêu (phần còn lại là mô tả tự nhiên)
/goal status             trạng thái + kế hoạch
/goal plan               in lại kế hoạch
/goal resume             mở lại mục tiêu đang bị chặn
/goal abort              dừng mục tiêu, GIỮ NGUYÊN mã đã sửa
/goal finish             đóng mục tiêu là đã xong
/goal rollback [stamp]   quay lui (xem mục 2)
/goal help               trợ giúp
```

Từ đầu tiên không phải lệnh con ⇒ cả phần còn lại là mô tả mục tiêu.

### Trạng thái

Lưu ở `<project>/.luas30/ai_goal.json`, ghi kiểu nguyên tử (tmp + `os.replace`)
nên không bao giờ để lại JSON cụt. Mỗi project có mục tiêu riêng; đổi project là
nạp lại (`AIChatView._attach_goal()`). JSON hỏng ⇒ coi như không có mục tiêu và
**không xoá tệp** (người dùng còn cứu được).

Bước: `todo [ ]` · `doing [>]` · `done [x]` · `failed [!]`. Tối đa 12 bước.
Mục tiêu: `planning` → `active` → `done` / `blocked` / `aborted`.

### Giao thức tool `goal`

Agent điều khiển kế hoạch bằng tool, không phải bằng cách sửa tệp trạng thái:

```luas30-tool
{"tool":"goal","args":{"op":"plan","steps":["...","..."]},"reason":"chia bước"}
```

`op`: `plan` (args.steps) · `start` (args.step) · `done` (args.step, args.verify)
· `fail` (args.step, args.note) · `blocked` (args.reason) · `finish` · `status`.

`GOAL_OPS` trong `ai_agent_protocol.py` là **nguồn duy nhất** cho cả prompt lẫn
handler. `_GOAL_OP_ALIASES` trong `ai_chat_view.py` nhận thêm cách gọi lệch
(`step_done`, `completed`, `set_plan`…).

⚠️ Tên op từng lệch giữa ba nơi (`step_done` vs `done`) — model gọi đúng theo
prompt nhưng handler từ chối, và triệu chứng là **mục tiêu đứng im mà không có
lỗi nào**. Thêm op mới thì sửa cả ba: `GOAL_OPS`, `prompt_block()`, handler.

### Ngân sách lượt

Mục tiêu tự chủ nhưng **luôn có biên** — không bao giờ chạy vô hạn:

| Access mode | Ngân sách |
|---|---|
| Plan mode | 8 lượt (chỉ lập được kế hoạch) |
| Ask / Edit automatically | 40 lượt |
| Full access | 80 lượt (`MAX_TURN_BUDGET`) |

Hết ngân sách ⇒ **dừng vòng lặp và GIỮ NGUYÊN mã đang dở** (không tự quay lui —
tự ý xoá ở đây là phá công sức). Thông báo chỉ rõ `/goal resume` để làm tiếp.

### Bằng chứng

Mỗi bước chỉ được `op=done` khi có `args.verify` nêu **lệnh/kiểm tra đã thật sự
chạy**. Thiếu bằng chứng thì kết quả tool ghi rõ CẢNH BÁO nhưng vẫn ghi nhận —
không chặn cứng, vì đó là tín hiệu để người dùng đọc, không phải cửa khoá.

## 2. Phục hồi / quay lui trạng thái

Mỗi lần `AIChangeService.apply()` / `apply_one()` ghi tệp, nó tạo một **bản chụp**
ở `.luas30/ai-backups/<stamp>/` kèm `checkpoint.json`:

```json
{"stamp":"20260921-223000-123456","source":"ChatAI","created_at":"...",
 "summary":"2 file(s) · +10 -3",
 "files":[{"path":"src/main.lua","existed":true,
           "sha_before":"…","sha_after":"…"}]}
```

`existed: false` = tệp do AI **tạo mới** (không có bản sao lưu) — manifest chính
là thứ cho phép xoá nó khi quay lui. Thư mục cũ không có manifest vẫn liệt kê và
khôi phục được (chỉ chiều ghi đè).

### HAI kiểu quay lui — đừng lẫn

| Hàm | Nghĩa | Kết quả |
|---|---|---|
| `restore_checkpoint(s)` | hoàn tác các ghi **CỦA** `s` | trạng thái **TRƯỚC** `s` |
| `rewind_to(s)` | hoàn tác mọi ghi **SAU** `s` | trạng thái **TẠI** `s` |

Vì thư mục sao lưu giữ nội dung *trước khi ghi*, `restore_checkpoint(s)` lùi một
bước so với `rewind_to(s)`. Goal Mode cần `rewind_to` cho "quay về cuối bước N";
dùng nhầm `restore_checkpoint` sẽ lùi quá một bước — **lỗi im lặng rất khó thấy**.

`rewind_to` dừng ngay khi trạng thái khớp `sha_after` của bản chụp đích, nên
không hoàn tác thừa những bản chụp đã được xử lý trước đó.

### Chốt an toàn: không bao giờ nuốt công sức người dùng

Tệp lệch khỏi bản chụp đích chỉ bị bỏ qua khi nội dung **không do AI ghi**:

* người dùng sửa tay ⇒ **GIỮ NGUYÊN** và báo lại (`skipped`);
* chính AI ghi ở **bước sau** ⇒ được phép ghi đè (`_ai_written_hashes()`).

Không có phép phân biệt này thì quay lui nhiều bước **luôn** bị chặn — đúng tình
huống mà tính năng sinh ra để xử lý. `force=True` mới ghi đè được tệp sửa tay.

Đường dẫn trong manifest đi qua `_safe_target()`: không thoát project, không
chạm `.git`/`.env`/`release`… Stamp phải khớp `^[0-9]{8}-[0-9]{6}(-[0-9]{1,6})?$`.

### Quay lui tự động khi bị chặn

Agent gọi `op=blocked` ⇒ `AIChatView` phát `goal_rollback_requested` với
`mode="rewind"` và stamp của **bước đã xác nhận gần nhất** ⇒
`MainWindow._rollback_ai_checkpoint()` gọi `rewind_to`, nạp lại editor đang mở,
dựng lại cây thư mục và làm mới PROBLEMS. Không có bản chụp nào từ bước đã xác
nhận thì **không quay lui** và ghi rõ lý do.

Tắt được bằng `AIChatView.GOAL_AUTO_ROLLBACK = False`.

`prune_checkpoints(keep=20)` giữ 20 bản mới nhất — gọi khi cần dọn.

## 3. Tối ưu hoá bộ nhớ đệm

Vòng lặp agent gọi `build()` **mỗi lượt** (8 lượt thường, 32–80 lượt ở Goal
Mode/Full Access) với cùng câu hỏi và cùng project. Ba tầng đệm:

| Tầng | Khoá | Cắt được gì |
|---|---|---|
| Nội dung tệp | `(path, mtime_ns, size)` | đọc + giải mã lại 160k ký tự tài liệu chỉ dẫn |
| Tiền tố ổn định | engine + project + vân tay tài liệu + vân tay cấu trúc | dựng lại cây + briefing + skills + `<instruction_documents>` |
| Chọn nguồn | project + câu hỏi + vân tay nội dung + active file | chấm điểm + đọc 9k ký tự của hàng trăm tệp ứng viên |

Đo trên `templates/keypad-demo`: **32.8 ms → 4.7 ms (7×)**, 81% bundle dùng lại.

⚠️ **Vân tay cấu trúc dùng TÊN mục, KHÔNG dùng mtime thư mục.** NTFS ghi metadata
trễ: ngay sau khi tạo tệp, mtime thư mục cha có thể vẫn là giá trị cũ ⇒ hai lần
gọi liên tiếp cho hai vân tay khác nhau, và tệp vừa tạo có thể không xuất hiện.
Dùng mtime làm khoá đệm là mời sẵn một lỗi phục vụ dữ liệu cũ.

⚠️ `_cached_read` cắt theo hạn mức **sau** khi lấy từ đệm. Đệm theo `(tệp, limit)`
sẽ sai: tài liệu chỉ dẫn được đọc với hạn mức co lại theo ngân sách còn lại.

`invalidate()` gọi sau mỗi lần AI ghi tệp (`on_code_changes_applied`) — chốt thêm
cho trường hợp tệp mới trùng cả size lẫn `mtime_ns`.

`bundle.cache_hit` / `bundle.stable_chars` / `service.cache_report()` phơi số liệu
thật; `tools/validate_ai_context_cache.py` khẳng định **cả hai chiều**: lượt hai
không đọc lại tệp nào, VÀ sửa tài liệu / sửa mã / thêm tệp thì lượt sau **phải**
thấy nội dung mới.

## 4. Quản lý quyền hạn

Đã có từ 1.15.0, giữ nguyên bốn mức:

| Mức | Sửa tệp | Shell |
|---|---|---|
| Ask before changes | hỏi từng lần | hỏi từng lệnh |
| Edit automatically | tự áp | hỏi từng lệnh |
| Plan mode | **không** | **không** |
| Full access | tự áp | tự chạy (lệnh nguy hiểm vẫn hỏi) |

Goal Mode **không** nới quyền: nó chạy trong khuôn khổ access mode đang chọn, chỉ
đổi *số lượt* và *cách tự tiếp tục*.

## Kiểm chứng

```bash
py -3.12 tools/validate_ai_goal_mode.py        # 11 phép thử, widget THẬT offscreen
py -3.12 tools/validate_ai_goal_rollback.py    # 18 phép thử round-trip trên đĩa
py -3.12 tools/validate_ai_context_cache.py    # 9 phép thử đệm + chống cũ
QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
    py -3.12 -u tools/studio_theme_check.py --shots build/theme-shots
```

⚠️ `validate_ai_goal_mode.py` **bắt buộc chạy offline**: nó thay
`AIRequestThread` bằng `OfflineRequestThread`. Để nguyên thread thật thì
`_start_request` gọi provider thật của người dùng (config + API key trong
`%APPDATA%`), model trả về edit và vì mặc định là `edit_auto` nó **ghi luôn vào
dự án tạm** — hỏng cả tính xác định của bài kiểm lẫn dự án đang mở.

## Chưa làm

* Chưa chạy `tools/build.py` sinh VXP thật + VXPEmu cho một mục tiêu đầu-cuối.
* Chưa thử trên máy Nokia 225 thật.
* Chưa có UI xem/lọc danh sách bản chụp (`list_checkpoints` mới chỉ dùng nội bộ).
