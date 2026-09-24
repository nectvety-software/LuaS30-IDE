# AI Agent gợi ý ý tưởng — `1.0.2`

Trạng thái: đã làm, đã kiểm chứng ngược 14/14. Ngày: 2026-09-23.

Người dùng yêu cầu:

> thêm skills và prompt để AI Agent biết gợi ý trong cuộc trò chuyện như làm game
> theo phong cách gì hay xem qua các project `Documents\LuaS30 Projects` để biết thêm

## 1. Vấn đề thật không nằm ở prompt

Viết một đoạn prompt bảo "hãy gợi ý phong cách" thì dễ. Cái khó là **không có đường
nào để agent xem qua các dự án cũ**.

`agent_protocol_prompt()` phát `project_scope_note`:

> Project scope (STRICT): every read/grep/glob path is relative to the OPEN project
> root and stays inside it. You cannot — and must not try to — read or edit the
> LuaS30 IDE's own installation/source tree (no scope=engine, no outside paths, no '..').

Nghĩa là `read ../mini-farm/README.md` **bị từ chối**. Nếu cứ viết prompt bảo agent
đi xem các dự án khác thì tính năng im lặng không chạy: model không có dữ liệu, nó
sẽ gợi ý chung chung, và không ai thấy có gì sai.

**Cách giải:** IDE quét hộ. `projects_root()` (`studio/app/core/paths.py`) chính là
`Documents\LuaS30 Projects` — đúng thư mục người dùng nói tới, và nó nằm ngoài
project nên chỉ lớp IDE (host) mới đọc được. IDE nén kết quả thành một danh mục
ngắn rồi nhồi vào system prompt.

## 2. Quét cái gì, và vì sao đáng tin

`PriorWorkService` đọc tối đa 5 tệp mỗi dự án:

| Tệp | Lấy được gì |
|---|---|
| `project.json` | `display_name`/`title`/`name`, `app_version`, `appid`, `ram_kb`, `screen_width/height`, `fps` |
| `README.md` | mục `## Style` / `## Gameplay` / `## Screens` / `## Target`, số màn, từ khoá |
| `CHANGELOG.md` | từ khoá (dự án cũ hay ghi rõ thể loại ở đây) |
| `conf.lua` | `width`/`height`/`fps`/`title` — **dự phòng** khi `project.json` không khai báo |
| `main.lua` | khối comment đầu tệp (mô tả do tác giả viết) + từ khoá |

Ba tệp sau không phải cho đủ bộ — mỗi cái vá một lỗ đã gặp thật khi quét 18 dự án:

- **`conf.lua`**: `DoodleNotebookHero/project.json` chỉ có `name`/`title`/`profile`,
  không có `screen_width`/`fps`/`ram_kb`, và README **không nhắc "240x320" lần nào**.
  Thiếu đường này thì dự án hiện ra với ô thông số trống.
- **`main.lua`**: `Fumble Run` **không có README**. Toàn bộ thông tin nằm ở comment
  đầu tệp:
  ```lua
  -- Shift Bound: Kinetic Escape - prototype
  -- May chay: Nokia 240x320, 15fps, 1MB RAM.
  -- Theme: Notebook Doodle Art (but bi xanh/do + chi)
  ```
  Không đọc `main.lua` thì nó rơi vào genre `khác` một cách vô cớ. (Đổi lại phải
  xử lý `1MB RAM` → `1024 KB`, và bỏ token tên tệp ở đầu dòng vì có dự án mở đầu
  bằng `-- main.lua -- BIỂN MỰC …`.)

### Genre và phong cách: chấm điểm, không đoán

`GENRE_RULES` / `STYLE_RULES` là bảng `(nhãn, (từ khoá…))`. Điểm = số từ khoá khớp
trong toàn bộ bằng chứng đã hạ chữ thường; điểm cao nhất thắng, hoà thì theo thứ tự
bảng (cụ thể trước, chung sau). Mỗi dự án giữ lại `evidence` — câu trích nguyên văn
cộng từ khoá đã khớp:

```
genre "farming-sim" — từ khoá khớp: "crop"
```

Nhờ vậy agent trích dẫn được, và người đọc kiểm lại được vì sao dự án bị xếp vào
một thể loại. **Không có bước nào để model đoán.**

### ⚠️ Kỹ thuật KHÔNG phải phong cách

Bản đầu để `procedural` chung bảng với phong cách. Kết quả: gần như dự án nào cũng
"procedural", nên bảng xếp hạng phong cách thành

```
procedural-flat (14), notebook-doodle (9), pop-art (4) …
```

— dòng đầu là thứ **mọi** dự án đều có, tức nó che mất đúng cái tín hiệu cần thấy.
Nay kỹ thuật nằm ở `TECHNIQUE_RULES` riêng, và khối prompt nêu **một lần**:

```
KỸ THUẬT CHUNG: 14/18 dự án vẽ procedural (engine.rect/line/text, không bitmap
runtime) — đây là cách làm quen thuộc của người dùng, không phải một phong cách riêng.
```

Bảng phong cách còn lại mới nói lên điều gì đó: `notebook-doodle (11)`,
`pop-art (4)`, `pixel-art (3)`, `comic-noir (1)`.

### Loại trừ

- Thư mục không có `project.json`/`main.lua`/`conf.lua` → không phải dự án (ví dụ
  `hello/` chỉ có `build/`).
- **Project đang mở bị loại** khỏi danh mục — nó đã nằm đầy đủ trong context bundle,
  nhắc lại chỉ tốn token.
- Thư mục rác: `.git`, `build`, `release`, `cache`, `backups`, `.luas30`, …

## 3. Đưa tới model

### Tool `projects`

`PROJECT_OPS = ("list", "show", "styles")` khai ở `ai_agent_protocol.py` —
**nguồn duy nhất** — và `prior_work_service.py` **import lại đúng tuple đó** cho
handler. Đây là cách chặn cứng lệch pha prompt/handler, giống `TASK_OPS`; khác
`GOAL_OPS` chỉ được validator canh. Tên `"projects"` phải nằm trong `TOOL_NAMES`:
parser lọc theo danh sách đó, quên là khối tool bị bỏ **im lặng** (0 action, không lỗi).

`op` thiếu hoặc rỗng thì **cố ý mặc định về `list`** (giống tool `skill`): đó là op
chỉ-đọc an toàn, và model quên `args.op` là lỗi phổ biến nhất — biến nó thành thông
báo lỗi chỉ tốn thêm một lượt. Nhưng op **lạ** thì ném `ValueError`, vì âm thầm coi
là `list` sẽ giấu mất lệch pha prompt/handler.

### Hai bản prompt, và một bất biến

`<prior_work>` chỉ dựng khi **có project đang mở**, và khớp với `prior_work=` truyền
cho `agent_protocol_prompt()`. Bất biến:

> có `<prior_work>` ⟺ có khối `SUGGESTIONS`

Lệch nhau là trạng thái nửa vời — hoặc có danh mục mà không được bảo dùng nó, hoặc
được bảo "hãy gợi ý" mà không có gì để gợi ý. Validator canh đúng bất biến này.

Hai bản:

| Lượt | Nhận gì | Cỡ |
|---|---|---|
| Đang bàn "làm gì / phong cách gì", hoặc project còn trống (chưa có `main.lua`) | danh mục ĐẦY ĐỦ, từng dòng một dự án | ~4.8k ký tự |
| Lượt làm việc bình thường (sửa lỗi, thêm nút…) | bản GỌN: gu tổng hợp + câu chỉ đường tới tool | ~0.6k ký tự |

Lý do tách: system prompt dựng ở **mọi** lượt, kể cả lượt vá một dòng. Mang 4.8k
ký tự danh mục vào lượt đó là lãng phí thuần. Và **đoán nhầm thành bản gọn vẫn an
toàn** — bản gọn nói rõ phải gọi `projects` op=list trước khi gợi ý, nên mất token
chứ không mất khả năng.

`_question_wants_ideas()` nhận diện bằng từ khoá (`gợi ý`, `phong cách`, `nên làm`,
`idea`, `what should i`, `genre`, …) cộng tín hiệu mạnh: **project chưa có `main.lua`**
= đang dựng cái mới.

### Đệm theo vân tay nội dung

`catalog()` chạy mỗi lượt. Đệm 2 tầng (`_file_cache` theo `(path, mtime_ns, size)`,
`_catalog_cache` theo vân tay cấu trúc) — cùng nguyên tắc với
`codebase_context_service.py`.

⚠️ Vân tay dựng từ **tên mục + (mtime, size) của từng tệp bằng chứng**, KHÔNG dùng
mtime của **thư mục**: NTFS ghi metadata thư mục trễ, nên thêm dự án mới có thể
không đổi vân tay và danh mục phục vụ bản cũ. (Đã mắc đúng bẫy này ở
`codebase_context_service`.)

⚠️ Hệ quả cho việc kiểm thử: đệm là thuộc tính **của từng instance**. Một
`PriorWorkService()` mới toanh có đệm rỗng nên luôn đọc lại từ đĩa — nó sẽ **xanh
kể cả khi vân tay bị phá hoàn toàn**. Validator phải dùng lại đúng instance đó. Đã
mắc: bản đầu tạo instance mới và guard "đệm tự vô hiệu" không hề canh gì cả.

## 4. Skill `game-idea-suggest`

`doc/ai/skills/game-idea-suggest/SKILL.md`, khám phá bởi `SkillService` (chỉ
name+description vào `<agent_skills>`; toàn văn nạp qua tool `skill` khi cần).

Dạy: lấy bằng chứng ở đâu · đọc danh mục cho đúng (đừng lẫn kỹ thuật với phong
cách; đừng tính bản sao template là ba lần chọn phong cách) · trần ràng buộc
240×320 / 15 FPS / chỉ phím cứng / Lua 5.1 / heap nhỏ · cách viết một gợi ý
(2–3 phương án, mỗi cái nêu vòng lặp cốt lõi bằng một câu + phím + dự án gần nhất
của người dùng + vì sao hợp máy này) · và **giới hạn phải nói thật**: chỉ đọc được
metadata, không thấy code bên trong dự án cũ.

## 5. Kiểm chứng

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
    py -3.12 -u tools/validate_prior_work_suggest.py

py -3.12 -u build/_rp_prior_work.py     # chứng minh ngược 14/14
```

`validate_prior_work_suggest.py` soi bốn tầng: hợp đồng tĩnh (TOOL_NAMES,
`PROJECT_OPS` một nguồn, skill khám phá được) → dịch vụ thật trên thư mục tạm
(`LUAS30_PROJECTS` chuyển hướng, nên không phụ thuộc `Documents` của máy chấm) →
**widget thật** đọc system prompt thật → **vòng lặp thật** gọi `AIChatView._run_tool`
và bắt buộc kết quả về tới hội thoại.

### Ba bài học khi viết chứng minh ngược

1. **Sao lưu theo TỆP, không theo từng lần vá.** Một ca vá hai chỗ trong cùng một
   tệp; lưu cả hai bản thì lúc khôi phục, bản thứ hai (đã vá dở) ghi đè bản gốc và
   tệp ở lại trạng thái vá một nửa. Đã mắc — và nó làm hỏng luôn các ca sau.
2. **Phá hành vi, đừng phá cú pháp.** Xoá cả hai dòng của `lines.append("…" "…")`
   để lại `lines.append()` rỗng → `TypeError`. Validator đỏ vì chương trình nổ,
   **không phải** vì guard bắt được — chứng minh giả. Phải thay nội dung, giữ cú pháp.
3. **Bắt đúng LOẠI lỗi là chưa đủ.** Xoá phép kiểm tra op thì lời gọi rơi xuống
   nhánh `show` và vẫn ném `ValueError` (thiếu `args.name`) — guard kiểu
   `except ValueError: pass` vẫn xanh **vì lý do sai**. Phải khẳng định thông báo
   lỗi nói về op, không phải về tên.

## 6. Bất biến cần giữ

1. `"projects"` ∈ `TOOL_NAMES`; `PROJECT_OPS` là một nguồn, service import lại.
2. Có `<prior_work>` ⟺ có khối `SUGGESTIONS`.
3. Danh mục loại project đang mở và thư mục không phải dự án.
4. Vân tay đệm dùng tên mục + (mtime, size) từng tệp, **không** mtime thư mục.
5. Kỹ thuật `procedural` không nằm trong bảng phong cách.
6. Bản gọn chỉ ở lượt làm việc; lượt hỏi ý tưởng và project trống nhận bản đầy đủ.
7. Thư mục không tồn tại ⇒ `catalog()` trả rỗng và `prompt_block()` trả rỗng,
   **không** ném lỗi.
8. Agent **không** đọc trực tiếp được thư mục dự án — mọi lời gọi đi qua IDE.

## 7. Việc còn lại (không chặn)

- Danh mục chỉ đọc metadata. Nếu muốn agent học cả *cách cài đặt* (ví dụ cấu trúc
  `src/game.lua` của `BusJam`), phải mở thêm một đường đọc chỉ-đọc có kiểm soát —
  hiện chưa làm, và skill nói thẳng với agent là nó không thấy code.
- `Chetaslua` bị xếp `device-utility` vì tài liệu của nó nói nhiều về quét bộ nhớ,
  trong khi thực tế là game vẽ tay hai người. Bảng từ khoá đúng nhưng bằng chứng
  không đại diện; `evidence` có ghi từ khoá khớp nên agent tự đánh giá được. Chấp
  nhận — sửa bằng cách thêm từ khoá sẽ là vá theo một dự án.
