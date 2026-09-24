# Changelog — LuaS30 IDE

Mọi thay đổi đáng chú ý của IDE, engine và Studio. Dạng tóm tắt
(Keep a Changelog); chi tiết đầy đủ của từng bản nằm trong
[`doc/release/changelog/`](doc/release/changelog/) và
kết quả kiểm tra tương ứng trong [`doc/release/validation/`](doc/release/validation/).

Phiên bản phát hành Studio là `VERSION` (hiện là **1.0.3**); các mốc
1.x bên dưới là dòng tính năng của engine/workbench được giữ nguyên
theo tên tệp tài liệu gốc.

## [1.0.2] — 2026-09-21 · Modal chrome + template dự án

- Toàn bộ hộp thoại modal của Studio chuyển sang **custom Title Bar
  frameless** (họ `CustomDialog`: Notice/Confirm/TextInput/IntInput/
  ColorPicker/FilePicker/RunSession/About/Setup), bo góc **12px** đồng bộ
  thẻ `Cấu hình MediaTek MRE SDK`, viền `#3A3A56` — trừ cửa sổ giả lập giữ
  chrome hệ thống. Riêng dòng "Mở dự án" dùng hộp chọn **thư mục Windows
  gốc (native)** theo yêu cầu người dùng. Chuẩn + danh sách ngoại lệ:
  [`doc/studio/MODAL_TITLEBAR_1_0_1.md`](doc/studio/MODAL_TITLEBAR_1_0_1.md).
- Sửa lỗi THẬT tìm ra khi drive modal: xác nhận Delete trong cây dự án in
  chuỗi `?\n\n` nguyên văn (escape đôi trong f-string `project_tree.py`).
- `validate_about_credits.py` soi theme **merged** `APP_STYLE +
  dark_theme.qss` đúng như app nạp — không còn render môi trường giả.
- Merge các PR trên GitHub (`qeafivels`): selector **chọn template khi tạo
  dự án**, template game đồ họa **DoodleQuest**, và luồng làm mới AI
  assistant trong editor (tab nền + badge "AI Modified/Created" —
  `validate_ai_assistant_ui_refresh.py`).
- Template **Keypad Demo** (`templates/keypad-demo`) + mục chọn thứ 5 trong
  `Cấu hình MediaTek MRE SDK`. `src/keypad.lua` là hợp đồng phím dùng lại được:
  bảng trạng thái `pressed`/`released`, alias số `2/8/4/6/5`, `softleft` = menu /
  `softright` = back, `drawPad()` vẽ bàn phím vật lý bằng `rect`/`text`;
  `main.lua` minh hoạ 3 màn menu / kiểm tra phím / nhập số theo
  `doc/ai/Keypad.md`. `templates/basic/main.lua` cũng được nâng lên mẫu wrapper
  chuẩn của tài liệu (`input_up/down/left/right/ok`, alias số, `pause`/`resume`
  gỡ trạng thái phím).
- Sửa lỗi THẬT do harness bắt được: `K.press()` trả **thiếu cờ `fresh`**, nên
  mọi nhánh chặn hành động lặp (`ok`, softkey, `clear`, `#`, `*`) không bao giờ
  chạy — runtime gửi lại `keypressed` cho phím đang giữ (sự kiện repeat) gây
  mở/nhập lặp. Validator tĩnh không thấy được lỗi này.
- Guard mới: `validate_mre_project_wizard.py` khẳng định dialog ↔
  `PROJECT_TEMPLATES` ↔ thư mục `templates/` khớp nhau (thêm template mà quên
  một chỗ trước đây hỏng im lặng); `validate_keypad_skill.py` soi **code** Lua
  template (bỏ comment trước khi tìm `KEY_*`/tên phím HOA).
- Kiểm chứng thật bằng Lua 5.1 build từ `vendor/lua-5.1.5`:
  `tools/keypad_template_check.lua` (37 assert) + `tools/basic_template_check.lua`
  (10 assert), chạy qua `tools/validate_project_templates_e2e.py` trên **dự án
  vừa tạo từ template**.
- Tài liệu chi tiết: [`doc/release/changelog/CHANGELOG_STUDIO_1_0_1.md`](doc/release/changelog/CHANGELOG_STUDIO_1_0_1.md),
  [`doc/release/validation/VALIDATION_STUDIO_1_0_1.md`](doc/release/validation/VALIDATION_STUDIO_1_0_1.md).
- NUMBERING: đợt modal + PR này vào thẳng bản 1.0.1 đã phát hành (commit
  `7c06961`/`d53ddd4`), bản 1.0.2 là **bản đóng gói đầu tiên** chứa chúng.
  Bản 1.0.2 đóng gói lúc **2026-09-21 11:13** (`dist/LuaS30IDE-Setup-1.0.2.exe`).

## [1.0.3] — 2026-09-24 · Bản đóng gói thứ hai

Đóng gói lại **toàn bộ** công việc landed sau mốc 1.0.2 (2026-09-21 11:13) —
mọi mục từ đây xuống hết mục "Vỏ giả lập: hai chip → rail icon bên phải" đều
nằm trong bản này.

**Kết quả đóng gói**: `dist/LuaS30IDE-Setup-1.0.3.exe` — **duy nhất 1 file**,
511 171 480 byte (**487,5 MB**), SHA-256
`f404099bd77aee23786102bbc59db2f4794a6c0368ae88f20263c8b7f13e47af`.
Chứng minh bằng chạy thật (cài im lặng vào temp, cấu hình cô lập): cài →
**4649 tệp**, `VERSION` trên đĩa = `1.0.3`; chạy `LuaS30IDE.exe --version` →
`LuaS30 IDE 1.0.3`; gỡ → **thư mục biến mất hoàn toàn**, registry sạch (kiểm
bằng `winreg`). Kiểm chứng nội dung: suite đầy đủ **70 ok / 0 SKIP / 0 FAIL**
khi chạy **không tương tác**; `validate_emulator_shell_frame.py` **710 phép
kiểm**; phản chứng `build/_rp_emulator_shell_frame.py` **36/36**.

Chi tiết đầy đủ theo hệ thống con:
[`doc/release/changelog/CHANGELOG_STUDIO_1_0_3.md`](doc/release/changelog/CHANGELOG_STUDIO_1_0_3.md).
Kết quả kiểm chứng (kể cả các phép đo **không** dùng được làm bằng chứng):
[`doc/release/validation/VALIDATION_STUDIO_1_0_3.md`](doc/release/validation/VALIDATION_STUDIO_1_0_3.md).

Chi tiết từng thay đổi:
- **Goal Mode** (`/goal`) — hệ thống tác vụ tự chủ cho AI Workbench: mục tiêu
  bằng ngôn ngữ tự nhiên → agent tự chia bước → sửa tệp nguồn → tự chạy lệnh
  debug → kiểm thử → xác nhận từng bước, cho tới khi xong. Trạng thái ở
  `<project>/.luas30/ai_goal.json`, điều khiển bằng tool `goal`
  (`plan`/`start`/`done`/`fail`/`blocked`/`finish`), dải tiến độ trong panel AI.
  Ngân sách lượt có biên (8/40/80 theo access mode) — hết ngân sách thì dừng và
  **giữ nguyên** mã đang dở, không tự xoá.
- **Phục hồi trạng thái**: mỗi lần áp code ghi `checkpoint.json` vào
  `.luas30/ai-backups/<stamp>/` (biết cả tệp AI **tạo mới** để xoá khi quay lui).
  Hai kiểu quay lui tách bạch: `restore_checkpoint(s)` = hoàn tác ghi của `s`,
  `rewind_to(s)` = hoàn tác mọi ghi **sau** `s`. Bị chặn giữa đường thì tự quay
  lui về cuối bước đã xác nhận. Tệp **người dùng sửa tay** luôn được giữ nguyên
  và báo lại; tệp do chính AI ghi ở bước sau mới được ghi đè.
- **Tối ưu bộ nhớ đệm ngữ cảnh**: 3 tầng (nội dung tệp / tiền tố ổn định / chọn
  nguồn), đo trên `templates/keypad-demo`: **32.8 ms → 4.7 ms (7×)**, 81% bundle
  dùng lại. Vân tay cấu trúc dùng **tên mục** chứ không dùng mtime thư mục.
- Sửa 3 lỗi THẬT mà harness bắt được, đều thuộc loại "hỏng im lặng": (1) tên op
  của tool `goal` lệch giữa prompt và handler ⇒ mục tiêu đứng im không báo lỗi;
  (2) `restore_checkpoint` dùng nhầm cho "quay về cuối bước N" ⇒ **lùi quá một
  bước**; (3) `goal.turn_prompt()` gọi trên `Goal` trong khi hàm nằm ở
  `GoalService`. Ngoài ra chốt an toàn "đừng ghi đè tệp sửa tay" từng chặn luôn
  cả quay lui nhiều bước — nay phân biệt được hai nguyên nhân lệch.
- Guard mới: `validate_ai_goal_mode.py` (11 phép thử, dựng **widget thật**
  offscreen), `validate_ai_goal_rollback.py` (18 phép thử round-trip trên đĩa),
  `validate_ai_context_cache.py` (9 phép thử, khẳng định **cả** chiều "không đọc
  lại" **và** chiều "không được phục vụ nội dung cũ"); `studio_theme_check.py`
  thêm mục E soi render dải mục tiêu (rò theme sáng, cắt chữ, khoá nút).
- Tài liệu: [`doc/studio/AI_GOAL_MODE_1_0_2.md`](doc/studio/AI_GOAL_MODE_1_0_2.md).
- Sửa lỗi THẬT do người dùng báo: chip tác vụ nổi trên header (Run/Build)
  **kẹt vĩnh viễn và nút X thành nút chết**. Hai nguyên nhân chồng nhau, đều
  hỏng im lặng: (1) `LuaRunner._on_build_finished` `return` sớm khi
  `post_action == "vxpemu"` nên **không** phát `finished` → không ai gọi
  `task_progress.finish()` cho tác vụ Run; (2) nút X chỉ phát
  `cancel_requested` → `build_service.cancel()`, mà lúc đó build đã xong nên
  no-op. Nay X **luôn** đóng chip (huỷ trước, rồi ẩn), chip được chốt ở
  `_on_vxpemu_stopped` khi phiên giả lập kết thúc, và đổi nhãn X sang
  "Đóng thông báo tác vụ" khi build đã xong. Guard mới:
  `validate_task_chip_dismiss.py` (hợp đồng tĩnh + **widget thật** offscreen +
  gọi thẳng `VxpMainWindow._on_vxpemu_stopped` trên stub) — đã kiểm chứng
  ngược: bản cũ FAIL đúng dòng "bấm X mà chip không đóng".
- Sửa tiếp theo yêu cầu người dùng: **tắt giả lập thì chip tác vụ phải tắt
  theo**. `_on_vxpemu_stopped(0)` nay gọi `task_progress.dismiss()` thay vì
  `finish()` — trước đó chip nán lại **5 giây** với dòng "Đã dừng giả lập",
  che vùng làm việc sau khi phiên giả lập đã kết thúc. Mã thoát **khác 0** vẫn
  hiện (`finish(False, "Giả lập lỗi")`) vì ẩn đi là giấu mất sự cố, và khi
  build còn chạy thì chip vẫn giữ nguyên tiến độ build. Ba đường tắt giả lập
  (bấm Dừng, đóng cửa sổ VXPEmu, VXPEmu tự thoát/crash — watcher PID) đều dồn
  về `_on_vxpemu_stopped(0)` nên chỉ cần một mối. `validate_task_chip_dismiss.py`
  thêm 6 assert cho nhánh này — kiểm chứng ngược: bản cũ FAIL đúng 3 dòng, gồm
  "tắt giả lập mà chip vẫn nằm trên header".
- **Bộ nhớ công việc của AI Agent** (`studio/app/services/ai_task_memory.py`, mới) —
  để agent **code dài hơn** và **nhớ việc đang làm**. Bốn nguyên nhân làm nó mất
  mạch, cả bốn đều **hỏng im lặng**: (1) `_start_request` chỉ gửi
  `self._history[-16:]` và **không tóm tắt gì** ⇒ đầu phiên biến mất, agent hỏi lại
  thứ vừa thống nhất; (2) đóng IDE mở lại là mất ngữ cảnh; (3) `/new` là mù hoàn
  toàn; (4) trần lượt 8/32 quá thấp cho việc nhiều tệp. Goal Mode chỉ giải (2)(3)
  **khi gõ `/goal`** và chỉ giữ danh sách bước.
  - Trạng thái ở `<project>/.luas30/ai_task.json` (ghi nguyên tử; JSON hỏng thì coi
    như rỗng nhưng **không xoá**): mục tiêu, bước, ghi chú/quyết định, tệp đã đụng,
    việc kế tiếp, chỗ tắc, và **bằng chứng quan sát được** (tệp đã ghi, lệnh đã chạy
    kèm mã thoát) — ghi tự động từ `on_code_changes_applied`/`on_shell_command_finished`
    nên sổ vẫn có ích kể cả khi model quên gọi tool.
  - Tool `task` (op: `status/objective/plan/step/fact/file/next/blocked/unblock/done/reset`).
    `TASK_OPS` nằm ở `ai_agent_protocol.py` và service **import lại đúng tuple đó**,
    nên prompt và handler không thể lệch — đúng bẫy `step_done` vs `done` đã từng làm
    Goal Mode đứng im. Tool phải nằm trong `TOOL_NAMES`, thiếu là khối tool bị bỏ im lặng.
  - `<task_memory>` nhồi vào system prompt ở **MỌI** lượt (khác `<goal_mode>` chỉ có
    khi bật `/goal`), nên lượt đầu của một phiên chat hoàn toàn mới vẫn biết đang dở việc gì.
  - `<earlier_work>`: bản tóm tắt phần hội thoại đã ra khỏi cửa sổ — hàm **thuần**,
    không gọi model, không tốn lượt (60 dòng / 4000 ký tự). Cửa sổ gửi nguyên văn
    16 → **40** (Goal Mode 60). Đừng cắt nhỏ lại: con số 16 chính là thứ đã làm đầu
    phiên biến mất.
  - Trần lượt 8/32 → **24/120** (luôn có biên; hết trần thì dừng và **giữ nguyên**
    code đang dở). Thêm `_nudge_unfinished_work()`: model định dừng bằng văn xuôi
    trong khi sổ của nó ghi còn `next` ⇒ nhắc **đúng MỘT lần**, không phải vòng lặp;
    không nhắc khi plan mode hoặc Goal Mode đang chạy.
  - Lệnh `/task` (xem sổ) và `/task clear` (xoá sổ).
  - Guard mới `tools/validate_ai_task_memory.py` — soi bốn tầng, gồm gọi **thân hàm
    thật** `_earlier_work_digest`/`_nudge_unfinished_work` trên stub. Đã **kiểm chứng
    ngược 8/8** (`build/_rp_task_memory.py`): phá từng hành vi ⇒ exit 1 và kêu đúng dòng.
  - `validate_ai_agent_shell.py` + `validate_ai_full_access_stop.py` thôi **ghim cứng**
    `= 8`/`= 32`, chuyển sang canh **bất biến** (có biên; Full Access rộng hơn nhưng
    vẫn có biên) — ghim số thì mỗi lần chỉnh ngân sách là đỏ oan.
  - Tài liệu: [`doc/studio/AI_TASK_MEMORY_1_0_2.md`](doc/studio/AI_TASK_MEMORY_1_0_2.md).
    Ghi chú trung thực: repo công khai `zai-org/ZCode` **không có** tài liệu nào mô tả
    tính năng runtime của agent (README chỉ nói setup; `DESIGN.md` là design system UI;
    `AGENTS.md` là hướng dẫn dev; `prompt-trajectory` là tool debug), nên không thể
    liệt kê "ZCode có gì" từ bằng chứng.
- **AI Agent gợi ý ý tưởng dựa trên dự án cũ của người dùng**
  (`studio/app/services/prior_work_service.py`, mới; skill
  [`doc/ai/skills/game-idea-suggest/`](doc/ai/skills/game-idea-suggest/SKILL.md)).
  Người dùng yêu cầu agent "biết gợi ý trong cuộc trò chuyện như làm game theo
  phong cách gì" và "xem qua các project". Vấn đề thật: `project_scope_note` khoá
  agent trong project đang mở, nên nó **không tự đọc được** `Documents\LuaS30
  Projects\<dự án khác>` — để mặc định thì prompt bảo "xem qua các project" mà
  không có đường nào để xem. Nên **IDE quét hộ** rồi nhồi kết quả vào prompt:
  - Quét `projects_root()`, rút genre / phong cách / target / số màn / mô-đun từ
    `project.json` + `README.md` + `conf.lua` + khối comment đầu `main.lua`.
    Genre và phong cách được **chấm điểm bằng từ khoá trên chính README người
    dùng viết**, và mỗi dòng giữ lại `evidence` (câu trích + từ khoá khớp) để
    agent trích dẫn được và người đọc kiểm lại được — không phải model đoán.
  - ⚠️ **Kỹ thuật tách khỏi phong cách**: gần như dự án nào cũng "procedural", nên
    để chung thì `procedural (14)` luôn đứng đầu bảng phong cách và che mất tín
    hiệu thật. Tách ra thành một dòng "KỸ THUẬT CHUNG" nêu MỘT lần; bảng phong cách
    còn lại mới có nghĩa: notebook-doodle (11), pop-art (4), pixel-art (3).
  - Tool mới `projects` (`PROJECT_OPS` = một nguồn dùng chung với prompt, service
    **import lại** đúng tuple của protocol nên hai bên không thể lệch):
    `op=list|show|styles`.
  - `<prior_work>` + khối `SUGGESTIONS` nhồi vào system prompt, nhưng **chỉ dựng
    khi có project đang mở** và **có hai bản**: bản đầy đủ (danh mục từng dự án)
    cho lượt đang bàn "làm gì / phong cách gì" hoặc project còn trống, bản gọn
    (chỉ gu tổng hợp + câu chỉ đường tới tool) cho lượt sửa lỗi — nếu không thì
    mỗi lượt vá một dòng cũng phải mang thêm ~1.2k token danh mục không liên quan.
    Đoán nhầm thành bản gọn vẫn an toàn: agent gọi được `projects` op=list.
  - Đệm theo **vân tay nội dung** `(đường dẫn, mtime_ns, size)`: sửa README là danh
    mục tự đổi. ⚠️ Không dùng mtime THƯ MỤC (NTFS ghi metadata trễ ⇒ phục vụ cây cũ).
  - Guard mới `tools/validate_prior_work_suggest.py` — bốn tầng, gồm **gọi thật**
    `AIChatView._run_tool` với một lời gọi `projects` để chứng minh kết quả về tới
    hội thoại. Đã **kiểm chứng ngược 14/14** (`build/_rp_prior_work.py`).
  - Tài liệu: [`doc/studio/AI_IDEA_SUGGEST_1_0_2.md`](doc/studio/AI_IDEA_SUGGEST_1_0_2.md).
- **UI lại vỏ máy giả lập theo mockup "classic dark"** (`studio/app/widgets/
  vxp_emu_window.py` viết lại). Người dùng gửi ảnh thiết kế; thân máy cũ (thanh
  tiêu đề + thanh công cụ 7 nút + gradient chéo + bàn phím một dòng chữ) được
  thay bằng:
  - Thân gradient **dựng đứng** `#2a3343 → #161d28`, bo góc 18, viền `#435069`.
  - Hai **chip nổi** `MENU` / `Shot` chờm lên đỉnh vỏ (`PhoneStage` mới — chip nằm
    ngoài khung `PhoneBody` nên không thể là con của nó). `MENU` mở `QMenu` chứa
    đủ 7 việc của thanh công cụ cũ: chạy/dừng, nạp `.vxp`, chụp màn hình, mở thư
    mục ảnh, quay video, xoay, toàn màn hình.
  - **Hàng trạng thái** trong thân vỏ trên màn hình: thanh xanh chỉ **đã nhúng
    được cửa sổ VXPEmu** (xám khi chưa), dòng dưới là `240×320 · 15 FPS`.
  - **Màn hình chờ** có nội dung thật: tên tệp `.vxp` + nhãn trạng thái, đồng hồ
    và ngày **thật** (cập nhật 20s), `NOKIA 225 DUAL SIM`, dòng trạng thái, dải
    phím mềm `Menu`/`Chọn`.
  - **Bàn phím 21 phím hai dòng**: số lớn + chữ cái nhỏ (`2`/`abc`), nền
    `#34445d`, viền `#506685`, bo 10, phím OK cao hơn hàng của nó.
  - ⚠️ **Chỗ mockup bịa thì thay bằng dữ liệu thật**: app KHÔNG có nguồn cho
    `4G VoLTE` / `WiFi · 1.0Gbps` / `56 FPS` (đã kiểm: không chỗ nào đo FPS), nên
    chỗ đó hiện tệp đang nạp + PID + **FPS mục tiêu** của `conf.lua`, không bịa số
    đo. Bảng đối chiếu đầy đủ ở tài liệu dưới.
  - ⚠️ `⇧` (U+21E7) **không có trong `segoeui.ttf`** — chỉ Segoe UI Symbol mới có
    — nên vẽ bằng Segoe UI là ra ô vuông, im lặng. Đổi thành `Aa`; validator đọc
    thẳng cmap của font để canh.
  - `back`/`clear` dùng **chữ** chứ không dùng glyph: glyph `back` là mũi tên
    trái, đứng cạnh `left` (cũng mũi tên trái) thì không phân biệt được nút nào.
    `#` được **làm mờ** để thấy ngay nó không gửi được vào VXPEmu.
  - Guard mới `tools/validate_emulator_shell_frame.py`: **546 phép kiểm**, render
    thật vỏ máy ngoài màn hình rồi soi điểm ảnh (gradient, góc bo, chip chờm,
    hàng trạng thái, mỗi phím số có HAI dòng chữ), kiểm cả cmap font và năm hành
    vi. Đã **kiểm chứng ngược 24/24** (`build/_rp_emulator_shell_frame.py`).
  - Tài liệu: [`doc/studio/EMULATOR_SHELL_FRAME_1_0_2.md`](doc/studio/EMULATOR_SHELL_FRAME_1_0_2.md)
    (gồm 16 bẫy của chính validator/harness: `grab()` tô vùng trống `#efefef`, gốc
    toạ độ là `PhoneStage`, `QMenu.exec()` treo nền offscreen, so cả ảnh thay vì
    dải đồng hồ, gradient chéo không phân biệt được ở orientation dọc, hộp chữ hai
    dòng chồng nhau, trộn hai hệ toạ độ ra chiều cao âm, mẫu phá tệp CRLF để lại
    `\r` gây `IndentationError`).
- **Rê chuột lên phím thì hiện TÊN PHÍM ngay trên vỏ máy giả lập**
  (`studio/app/widgets/vxp_emu_window.py`). Yêu cầu người dùng: "khi dê chuột sẽ
  hiện tên của các nút bấm". `setToolTip()` vốn đã có đủ cho 21 phím + 2 chip,
  nhưng tooltip là **cửa sổ của hệ điều hành**: trễ ~700ms, có thể bị cửa sổ khác
  che, và **không kiểm chứng được offscreen**. Nên tên phím được vẽ vào chỗ luôn
  nhìn thấy:
  - Dòng dưới của **hàng trạng thái** đổi từ `240×320 · 15 FPS` (màu nhấn xanh)
    sang tên phím (chữ sáng) khi rê chuột, tự trả lại khi chuột ra. Vị trí này
    nằm TRONG vỏ máy và không bị cửa sổ VXPEmu che khi game đang chạy.
  - Tên hiện ra là **tên Lua** của hợp đồng phím (`up`, `softleft`, `ok`…), thêm
    chữ nhỏ nếu phím có: `2 · abc`, `* · +`, `# · Aa`. Lấy từ
    `PhoneKeypad.MRE_KEY_NAMES` — cùng nguồn với tooltip nên không thể lệch.
  - Phím đang trỏ **sáng lên** (`KEY_FILL_HOVER = "#3f5580"`, màu SUY RA vì mockup
    không có trạng thái hover) để biết tên đó ứng với phím nào.
  - ⚠️ **Thứ tự `Enter`/`Leave` giữa hai nút kề KHÔNG được Qt bảo đảm.** Xử lý
    theo cặp ("Enter thì bật, Leave thì tắt") làm tên phím tắt ngay sau khi vừa
    bật — nhưng chỉ ở MỘT trong hai thứ tự nên rất khó thấy. Đúng: nhớ nút MỚI
    NHẤT được Enter, chỉ xoá khi chính nút đang nhớ phát Leave.
  - ⚠️ **`hideEvent` phải dọn hover**: nút bị ẩn lúc đang rê chuột thì `leaveEvent`
    không tới nữa và tên phím **kẹt vĩnh viễn** trên hàng trạng thái.
  - ⚠️ Câu gợi ý ở chân cửa sổ **quyết định bề ngang cửa sổ** (`_fit_shell` lấy
    `sizeHint()`, QLabel không tự co): thêm ~34 ký tự làm cửa sổ phình 632 → 829px.
    Muốn thêm chữ thì phải bỏ chữ khác.
  - ⚠️ Đừng lấy "tooltip có hiện không" làm phép kiểm: `QTest.mouseMove()` rồi đọc
    `QToolTip.isVisible()` **luôn** ra "không hiện", kể cả với `QPushButton` thường
    (đã chạy đối chứng để biết phép đo vô hiệu, không phải app lỗi); chụp màn hình
    thật với chuột thật cũng không kết luận được vì cửa sổ khác che mất.
  - Guard: `validate_emulator_shell_frame.py` §F (+125 phép kiểm, tổng **546**),
    phản chứng thêm **8 ca** (tổng **24/24**).
- **Cơ chế giả lập keypad viết lại** (`vxp_emu_window.py` + `native_window.py`):
  trước đây mỗi nút phát `clicked` → down+up tức thời, nên app **không bao giờ**
  thấy trạng thái ĐANG GIỮ — bảng `held` trong `keypad.lua` vô nghĩa và
  `engine.keypressed`/`keyreleased` không thành cặp. Nay `PhoneKey` phát
  `key_pressed`/`key_released` riêng, `send_key_down`/`send_key_up` ghép cặp
  (`WM_KEYDOWN`/`WM_KEYUP`), nhả phím khi thả ngoài nút / mất focus / dừng giả
  lập / đóng cửa sổ. Bổ sung 2 phím còn thiếu của hợp đồng §0 (`back`, `clear`)
  — đủ 21/21 nút, bố cục 3×7. Bàn phím thật của máy đi cùng bảng phím với
  VXPEmu (`_QT_TO_MRE` ↔ `KeyboardMapping::loadDefaults`), auto-repeat bị bỏ
  qua đúng như VXPEmu.
- ⚠️ **`#` không gửi được vào VXPEmu** — chốt bằng đo, không phải suy đoán.
  Qt chỉ ra `Qt::Key_NumberSign` khi `GetKeyboardState()` thấy Shift thật đang
  giữ; gửi `VK_SHIFT` thay thế còn tệ hơn vì `Qt::Key_Shift` nằm trong bảng
  phím của VXPEmu nên thành một cú `softright` giả. Đã thử 5 cách (Shift giả
  qua `PostMessageW`, `AttachThreadInput`+`SetKeyboardState`, `VK_PACKET`,
  `WM_CHAR`, quét 35 virtual-key OEM/numpad) — chỉ `AttachThreadInput` +
  `SendInput` Shift thật chạy được, nhưng ~1/7 lần app nhận `3`, tức **sai phím
  mà im lặng**, nên bỏ hẳn và chặn tường minh bằng
  `native_window.MRE_KEYS_NOT_INJECTABLE`. Nút `#` vẫn có trên vỏ máy, tooltip
  nói rõ chỉ chạy trên máy thật. Muốn sửa thì phải cho VXPEmu một đường bơm
  thẳng mã MRE (`dispatchKeyPress`).
- Guard mới: `validate_keypad_emulation.py` (đối chiếu 3 bảng phím với **nguồn
  VXPEmu** + widget offscreen: giữ/nhả, nhả ngoài nút, mất focus, dừng giả lập)
  và `validate_keypad_emulation_e2e.py` — **E2E thật**: build dự án dò bằng
  toolchain ARM + MRE SDK, mở `VXPEmu.exe`, nhúng vào shell 240×320 như Studio,
  bơm phím rồi **đọc framebuffer** để khẳng định Lua nhận đúng tên phím
  (`giữ up` → `held={up}`, `giữ down+left` → `held={down,left}`, nhả hết → rỗng).
  Tự SKIP khi thiếu VXPEmu/toolchain/SDK.
- Ghi nhận khi làm E2E: `print()` của Lua **không hiện ở đâu** khi chạy VXPEmu —
  runtime gọi `ls30_log_info` → `_vm_log_info`, mà VXPEmu chỉ export
  `vm_app_log`, nên lời gọi là no-op im lặng. Muốn quan sát phải vẽ lên màn hình.
  Cũng phát hiện VXPEmu vẽ framebuffer 240×320 vào cửa sổ với scale ≈ 1.25 kèm
  lệch, nên toạ độ pixel không dùng trực tiếp được — validator tự giải phép biến
  đổi từ 3 điểm chốt.
- Tài liệu: `doc/ai/Keypad.md` thêm §6 "Bấm phím trong emulator" (3 bảng phím,
  hợp đồng giữ phím, giới hạn `#`, cách kiểm chứng) và bổ sung checklist §4.

### 2026-09-23 · Template **Pop Art City 3D** (pseudo-3D raycasting)

- Template dự án thứ 7 trong `Cấu hình MediaTek MRE SDK`: `popart-city-3d` →
  `templates/PopArtCity3D/` (appid 586534798). Thành phố giả 3D kiểu GTA phong
  cách pop-art: raycasting DDA, lái xe giao hàng, radar bắc-up, mức truy nã, HP.
  Đăng ký ở cả `PROJECT_TEMPLATE_OPTIONS` (`mediatek_mre_dialog.py`) và
  `PROJECT_TEMPLATES` (`project_session.py`).
- **"3D" ở đây là pseudo-3D, không phải 3D thật** — và README của template nói
  thẳng như vậy. MRE 240×320 không có GPU, không có alpha, không có `pixel`/
  `vline`/`hline`; nên renderer vẽ 60 cột × 4 px và **trộn trước** sương mù
  thành 4 sắc độ rồi chọn theo khoảng cách. Chính ràng buộc đó tạo ra nét pop-art.
- **Bốn lỗi THẬT chỉ chạy thật mới thấy** (đều im lặng qua kiểm tra tĩnh và
  harness Lua) — chi tiết ở
  [`doc/studio/POPART_CITY_3D_1_0_2.md`](doc/studio/POPART_CITY_3D_1_0_2.md):
  1. `main.lua` gọi `P.C.gold` trong khi `gold` chỉ có trong `HUD.C` ⇒ `E.text`
     nhận `nil` ở tham số #4 ⇒ runtime `luaL_checknumber(L,4)` ⇒
     `bad argument #4` ⇒ **chết cả màn hình hướng dẫn**;
  2. 9 dòng chữ tràn ra ngoài framebuffer 240 px (đo được: chân trang tiêu đề vẽ
     từ x = 0 tới 239.2 và vẫn bị cắt hai đầu);
  3. nhãn "HP"/"SPD" của HUD đè lên chính thanh của nó;
  4. `PrintWindow` thỉnh thoảng trả về **bề mặt cũ** (thanh tiêu đề Qt + ruột đen)
     thay vì framebuffer — validator phải chụp lại cho tới khi khung hình trông
     như framebuffer thật.
- Guard mới, và đều đã reverse-proof (phá đúng một thứ, guard đỏ **vì đúng lý do**):
  `tools/popart_city_check.lua` (**62 kiểm tra**, 16/16 ca phá), stub `engine`
  nay mô phỏng đúng `luaL_checknumber` + `select("#", ...)` của
  `runtime_bridge.c`, gom màu trên **mọi** màn hình và kiểm tra **chữ có nằm
  trong màn hình** theo bề rộng font **đo được** (7.2 px/ký tự ở `set_font(8)`);
  `validate_popart_city_template.py` đối chiếu **tên** trong bảng màu với nơi
  định nghĩa (`P.C.*` ↔ `popart.lua`, `HUD.C.*` ↔ `hud.lua`).
- **E2E thật trên VXPEmu**: `tools/validate_popart_city_e2e.py` build template
  bằng toolchain ARM, mở `VXPEmu.exe --autostart --testapi --screen-only`, nhúng
  cửa sổ rồi **đọc pixel framebuffer** (vì `print()` của Lua không tới được log
  của VXPEmu). 26 kiểm tra: 6/6 dải trời, 12/24 sắc độ tường, 13 độ cao vỉa hè
  khác nhau, giữ `up` đổi 42.5% khung hình, đâm tường mất HP thật (576 → 512 px
  ruột thanh), bảng tạm dừng phủ 34.9%, và phân loại màn hình **đọc từ pixel**
  chứ không suy từ thứ tự bấm phím. Reverse-proof: 23/23.
- Màu không hiện ra như khai báo: runtime nén qua `LS30_RGB565` (macro **không
  chuẩn**, bit 1..0 của kênh G bị bỏ) rồi VXPEmu giải nén bằng phép dịch. E2E
  chép nguyên công thức, tự kiểm tra mô hình bằng màu đã đo, và đọc bảng màu
  thẳng từ `src/*.lua` thay vì chép tay giá trị hex.
- Ngân sách khung hình **đo bằng harness**: tiêu đề 337 rect / 146 489 px; đang
  chơi **187 rect / 134 951 px**.
- Build thật: `ELF32/ARM/EABI5/gcc_entry/no_vm_undefined` PASS, VXP đơn generic
  **chưa ký** (IDE không ký — xem 1.0.1).
- **Sửa một lỗi im lặng của chính E2E**: dự án ném để build từ `build/_popart_e2e`
  chuyển sang **temp của OS**, ảnh chụp sang `build/_popart_e2e_shots/`. Hook
  `[safe-delete]` của host chặn `shutil.rmtree` khi vượt **ngân sách xoá theo
  lượt** (`CODEBUDDY_SAFE_DELETE_BULK_THRESHOLD`, 50 mục) và thoát bằng
  `SystemExit(1)`: script chết với `exit 1` mà không in gì, trông y như "E2E hỏng
  vì lý do khác" — và chỉ lộ ra sau ~10 lần chạy khi thư mục đã tích đủ tệp.
  Đo được (`build/_probe_bulk_guard.py`): `build/` + 200 tệp ⇒ `exit 2`; cùng lượt
  30 rồi 30 tệp ⇒ `exit 0` rồi `exit 2` (đúng là cộng dồn); **TEMP** + 200 tệp ⇒
  xoá thật, không hỏi guard. Hàm `reset_scratch()` còn **từ chối** xoá nếu dự án
  ném không nằm trong temp, để lỗi lộ ra ngay nếu ai đó đổi lại.
  ⚠️ Áp dụng cho **mọi** validator của repo: đừng `rmtree` thư mục lớn trong `build/`.
- **Cùng lỗi đó ở `tools/validate_keypad_emulation_e2e.py`** — đã sửa. Nó build dự án
  dò vào `build/_kp_keypad_probe`, mà `tools/build.py:465` dọn bằng
  `shutil.rmtree(build, ignore_errors=True)`; ⚠️ `ignore_errors=True` **không** nuốt được
  `SystemExit` (chỉ bắt `OSError`) nên guard chặn là **cả script chết**. Thư mục
  `build/_kp_keypad_probe/build/` một mình đã **62 tệp > 50** ⇒ chạy lẻ (host duyệt
  tool-call) thì xanh, chạy **cả suite trong một lượt không tương tác** thì ĐỎ với
  `build dự án dò thất bại (exit 1)`. `PROBE_DIR` nay ở temp, ảnh chụp ở
  `build/_kp_keypad_probe_shots/`.
  ⇒ **Suite 70/70 xanh chỉ đáng tin khi chạy không tương tác.**

### 2026-09-23 · Vỏ giả lập: hai chip → **rail icon bên phải** + bong bóng tên

- Theo yêu cầu người dùng *"các menu của giả lập VXPEmu chuyển sang phải như máy ảo
  LDPlayer 14 chỉ icon khi dê chuột và sẽ hiện title lên"*: hai chip `MENU`/`Shot`
  chờm trên đỉnh vỏ được thay bằng `ToolRail` dọc **bên phải** thân máy, **chỉ
  icon**, tên công cụ hiện trong **bong bóng** khi rê chuột. Đủ 7 việc cũ
  (chạy/dừng, nạp `.vxp`, chụp màn hình, mở thư mục ảnh, quay video, xoay, toàn
  màn hình) — `RAIL_ITEMS` ↔ `_tool_handlers()` là **một hợp đồng**, validator canh
  cả hai chiều (thiếu khoá, thừa khoá).
- **Bỏ hẳn `QMenu`.** `QMenu.exec()` mở vòng lặp sự kiện **LỒNG NHAU**: validator
  offscreen bấm vào sẽ treo vô hạn, im lặng. Đổi lại `_choose_vxp` mở `QFileDialog`
  và `open_capture_folder` mở trình duyệt tệp của OS — cũng là modal, nên phần kiểm
  hành vi của rail vẫn phải chạy trên một `PhoneStage` **riêng**.
- **Bong bóng là widget tự vẽ (`RailTip`), KHÔNG dùng `QToolTip`.** Tooltip không
  kiểm chứng được offscreen (đã chạy đối chứng với `QPushButton` thường): xây tính
  năng dựa vào thứ không đo được thì không guard nào bảo vệ nó. `RailTip` mang
  `WA_TransparentForMouseEvents` và phải là widget **LÁ** vì nó vẽ đè lên mép phải
  thân máy — chỗ có bàn phím cần bấm. Kiểm bằng **cả hai** cách: `testAttribute()`
  và `stage.childAt(tâm_bong_bóng)` (đo được: `childAt` trả `ScreenHost`, không
  phải `RailTip`).
- **Icon đổi theo trạng thái thật** qua `_sync_rail()`: `play`↔`stop`,
  `circle`↔`stop`, `expand`↔`collapse`, kèm viền `ACCENT` khi công cụ đang bật. Bỏ
  sót một chỗ gọi là rail **nói dối** (vẫn vẽ "play" khi giả lập đang chạy) — guard
  khẳng định lời gọi có mặt trong cả **năm** hàm đổi trạng thái.
- **Một lỗi THẬT, im lặng tuyệt đối**: `ToolRail._on_hover` phát tâm Y của nút
  theo hệ toạ độ **rail**, còn `PhoneStage` đặt bong bóng theo hệ toạ độ **stage**
  ⇒ bong bóng hiện **cao hơn nút ~175 px** mà không có lỗi, không cảnh báo. Sửa bằng
  `self.y() + button.y() + …`; guard so tâm bong bóng với tâm nút **quy về stage**.
- Kiểm chứng: `validate_emulator_shell_frame.py` **546 → 710 phép kiểm**, thêm mục
  **G** (bong bóng: hiện/ẩn, đúng tên, đúng bề rộng chữ theo `QFontMetrics`, đúng
  vị trí, có mực vẽ, không chặn chuột, thứ tự Enter/Leave ở **cả hai** chiều, ẩn
  rail thì bong bóng phải tắt, viền accent đếm **cả ô** chứ không dò một điểm) và
  guard khoảng cách màu (hover/nền ≥ 40, glyph/nền ≥ 60, chữ bong bóng/nền ≥ 120).
  `build/_rp_emulator_shell_frame.py` **24 → 36 ca**, tất cả đỏ **vì đúng lý do** và
  xanh lại sau khôi phục: **36/36**.
- ⚠️ **Bẫy mới của chính harness phản chứng**: `_replace()` thay lần khớp **ĐẦU
  TIÊN**, mà `PhoneKey.enterEvent` và `PhoneRailButton.enterEvent` có thân **y hệt
  nhau** (`self.hover_changed.emit(self, True)`) và `PhoneKey` khai trước ⇒ ca "rail
  thôi báo hover" dùng mẫu ngắn sẽ phá **bàn phím**, validator vẫn đỏ nhưng đỏ ở
  §F — trông vẫn như đạt nếu chỉ liếc kết quả. Phải neo vào dòng comment chỉ rail
  mới có. Tương tự: ca "`_sync_rail` bị bỏ sót" **không** được phá bằng cách đổi tên
  hàm (⇒ `AttributeError` khi dựng `window`, harness xếp vào "đỏ vì vỡ cú pháp"),
  mà phải xoá **đúng một lời gọi**.
- Tài liệu: [`doc/studio/EMULATOR_SHELL_FRAME_1_0_2.md`](doc/studio/EMULATOR_SHELL_FRAME_1_0_2.md)
  (§"Rail icon bên phải thay hai chip" + 5 bẫy mới); QSS `theme.py` đổi
  `#PhoneChip` → `#PhoneRailButton`.

## [1.0.1] — 2026-09-19 · Studio chrome VXPEngine

- Port giao diện VXPEngine 1:1 vào `studio/app/vxpui/`: cửa sổ frameless
  với `CustomTitleBar` (menu bar nhúng), họ `CustomDialog`,
  `WindowStateController`, edge-resize thủ công — lõi Lua giữ nguyên.
- Icon không còn phụ thuộc QtAwesome lúc chạy packaged: fallback glyph
  Segoe MDL2 / Fluent (`app/ui/icons.py` + `app/vxpui/icons.py`).
- Panel THIẾT BỊ · VXPEMU chuyển thành hộp thoại application-modal mở từ
  menu "Công cụ" (Ctrl+Alt+D); đóng = ẩn để EmulatorView không bị phá huỷ.
- `AssetsStudioWindow`: cửa sổ top-level riêng kiểu Photoshop
  (Ctrl+Alt+U) gộp Assets + UI Designer, có title bar/menu/geometry riêng.
- Hộp thoại modal "TÀI NGUYÊN · ASSETS" (Ctrl+Alt+R): chọn ảnh chèn thẳng
  vào canvas hoặc import tệp — palette THÀNH PHẦN đồng bộ ngay để kéo-thả.
- CHAT AI là cột phải của workspace theo đúng mô hình panel Chat của
  VS Code (Ctrl+Alt+I), không còn nằm trong hộp thoại thiết bị.
- `AIChatView` dựng lại theo ảnh mẫu: header "AI Trợ lý", tab đoạn
  Chat/Context/Tools, welcome card + lưới 6 nút hành động nhanh, thẻ
  "Ngữ cảnh" và composer bo góc với pill model + nút gửi cyan.
- Vùng soạn thảo đồng bộ ảnh mẫu: thêm `ActivityBar` 46px bên trái
  (Explorer · Search · Console · Chat AI · Cài đặt), header Explorer
  động "EXPLORER - <TÊN DỰ ÁN>", tab mã có icon theo loại tệp + vạch
  accent cyan trên tab đang mở, status bar thêm badge `UTF-8` và
  `Spaces: 4`.
- Chuẩn tiện ích mở rộng mới: mọi thư mục `extensions/<id>/` có
  `extension.json` được `ExtensionService` tự phát hiện, hiện động trong
  menu "Công cụ → Tiện ích mở rộng", mở thành tab công cụ
  `extension:<id>` (lưu/restore qua workspace session).
- Trang "Cửa hàng tiện ích mở rộng" (`ExtensionMarketView`) dạng card nền
  tối theo ảnh mẫu: ô icon bo góc, tên, mô tả hai dòng, hàng
  "from · version · added"; luồng cài kiểu VS Code — nút "Cài đặt" →
  "Mở"+"Gỡ cài đặt", state lưu `config/extensions_installed.json`, và
  icon tiện ích đã cài xuất hiện trên activity bar trái như VS Code.
- `ExtensionHostView`: host QWebEngineView + cầu nối QWebChannel
  `window.luaS30` (extension/project/notify/writeFiles); ghi tệp bị giới
  hạn trong thư mục dự án, chặn `..`, tên tuyệt đối, tệp bí mật; trang
  nhận sự kiện `luas30-bridge-ready`.
- `sprite-sheet.html` → extension chuẩn đầu tiên
  `extensions/sprite-sheet/` (manifest + `ui/index.html` + `SKILLS.md`),
  bổ sung nút "Ghi vào dự án (PNG + atlas.json)" xuất thẳng sprite vào
  `assets/sprites/` của dự án đang mở.
- ChatAI chuyên Lua S30+ MRE VXP: thêm công cụ đọc-lõi (read/list/glob/grep
  trong templates·sdk·engine·compat·doc/ai·extensions),
  ngữ cảnh nhúng `<installed_extensions>` + `<engine_core>` (ranh giới
  Lua→C thật: `engine.lua` wrapper mỏng quanh bảng `engine` đăng ký trong
  `engine/src/runtime_bridge.c`), SKILLS.md của extension được nạp làm luật
  agent, system prompt yêu cầu kiểm chứng API bằng đường đọc lõi thay vì
  giả định hàm mobile-Lua/love2d.
- Tầng AI Agent dọn trùng lặp + nâng theo hướng Cline, chuyên Lua MRE S30+:
  tool `engine` riêng bị gộp vào read/grep/glob bằng `args.scope="engine"`
  (lời gọi kiểu cũ vẫn được parser tự dịch); SKILLS.md của extension không còn
  nạp toàn văn vào mọi system prompt; một lượt trả lời được phép phát NHIỀU
  khối `luas30-tool` và tất cả chạy lần lượt (trước chỉ chạy tool đầu tiên);
  bản đồ lõi sửa chỗ đăng ký hàm engine về đúng `engine/src/runtime_bridge.c`
  (mảng `luaL_Reg funcs[]` của `luas30_bridge_open`).
- Hệ thống SKILLS mới (`skill_service.py`): skill là tệp `SKILL.md` có
  frontmatter `name`/`description` quét từ `skills/` của project,
  `doc/ai/skills/` của IDE và `skills/` của extension; prompt chỉ mang MỤC LỤC
  `<agent_skills>`, toàn văn nạp theo yêu cầu qua tool `skill`
  (op list|read) — kèm 3 skill trụ cột `vxp-build-run`,
  `s30plus-ui-design`, `problems-autofix` và lệnh `/skills` trong ô chat. Validator mới
  `tools/validate_ai_skills.py`.
- Tool `problems` + mặc định "Edit automatically" (Cline Act):
  `{"tool":"problems","args":{"op":"list"|"count"}}` đọc trực tiếp bảng
  PROBLEMS của IDE (severity, đường dẫn tương đối, dòng:cột, message + snippet
  code) qua provider nối từ `MainWindow._ai_problems_snapshot` sang
  `AIChatView.set_problems_provider`; access mode mặc định nay là
  `edit_auto` — code agent sinh ra tự áp thẳng vào dự án (backup
  `.luas30/ai-backups`), vòng lặp tự tiếp tục sau khi áp, skill
  `problems-autofix` mô tả quy trình full vòng đời sửa lỗi.
- Mỗi đợt áp code của AI in một card tổng hợp kiểu Cline/Cursor ngay trong
  transcript Chat: "Đã sửa N tệp" + tổng `+X −Y` xanh/đỏ, nút **Review** mở lại
  tab AI Changes (kể cả sau khi đã áp — giữ `_ai_last_applied` + `mark_applied`),
  danh sách từng tệp kèm số dòng thêm/bớt, gọn 3 dòng đầu với link
  "Hiển thị thêm N tệp"/"Thu gọn danh sách" (`x-luas30://` anchor trên
  `QTextBrowser`, không lọt vào payload gửi provider). Validator mới
  `tools/validate_ai_change_card.py`.

- Sửa lỗi hiển thị bàn phím vỏ Nokia 225 (`vxp_emu_window.py`): nhãn phím mềm
  không còn bị cắt ("Phím mềm" đầy đủ + tooltip trái/phải, font 8pt, quy tắc
  QSS mới `QPushButton#PhoneKey` bỏ padding rộng thừa), phím điều hướng
  trái/phải có icon chevron (`arrow_left`/`arrow_right` E76B/E76C trong
  `icons.py`) thay vì ô đen rỗng, cột phím rộng 80px (bàn phím 252×186), và
  màn chờ hết cảnh chữ "NOKIA" đè lên "225 DUAL SIM".
- Sửa Chat AI "đứng" khi model không theo protocol: `parse_agent_response`
  nay dịch được tool-call XML gốc kiểu Gemini/Ling (`<tool_call=read>` hoặc
  thẻ trần + cặp `arg_key/arg_value`) — alias tên tool, suy đoán tool từ args
  khi thiếu tên, `engine` cũ hạ cấp thành read/grep/glob TRONG project (mọi
  `scope` bị bỏ), và `write_file`/`edit_file`
  thành `CodeEditAction` nên mã vẫn tự áp thẳng vào dự án như Cline; khối XML
  bị gỡ khỏi chữ hiển thị, value mã nguồn giữ nguyên newline, fenced JSON
  được ưu tiên khi trùng lặp. Validator mới
  `tools/validate_ai_tool_call_xml.py` (12 check).
- E2E tự động cho vòng lặp Chat AI (`tools/e2e_chat_ai_agent.py`, headless,
  không cần API key): 8 lượt model kịch bản xen lẫn fenced JSON + XML được
  phát qua đúng `AIChatView` thật trên dự án tạm — agent phải dựng màn hình
  đủ nút nhấn/label/photo/textbox/card trong `.luas30/ui_design.json`, sinh
  PNG thật, TỰ ÁP 2 đợt sửa `main.lua` (hiện 2 card "Đã sửa N tệp"), đọc
  PROBLEMS và dừng đúng lượt; 14 check, kèm chẩn đoán từng lượt nếu agent
  không tương tác được với dự án.
- `tools/drive_ide_as_user.py` — mô phỏng NGƯỜI DÙNG THẬT trong `VxpMainWindow`
  (appdata/projects tạm, chặn modal SetupDialog): tạo dự án mẫu `DemoApp` qua
  đúng `session.create_project` + `_switch_project`, gõ yêu cầu vào composer
  rồi `send()` thật; chỉ stub lớp mạng bằng kịch bản 8 lượt fenced+XML, còn
  toàn bộ pipeline thật chạy (auto-apply, backup, reload editor, tab AI
  Changes, PROBLEMS) — 14 check + ảnh `build/shots_user_ide/ide_as_user.png`.
- Sửa lỗi THẬT tìm ra nhờ mô phỏng: `AIDiffView` crash
  (`QPlainTextEdit.ExtraSelection` không tồn tại trong PySide6) khi highlight
  dòng thay đổi — chuyển sang `QTextEdit.ExtraSelection`; driver có check hồi
  quy riêng cho lỗi này.
- Sửa Chat AI không tự áp mã (xem [1.0.1] ở trên): đóng gói lại thành công
  `dist/LuaS30IDE-Setup-1.0.1.exe` (duy nhất 1 file, 483 MB, Inno Setup wizard
  + `/SILENT`, SHA-256 kèm theo) — cài đặt im lặng kiểm chứng OK, bản cài mở
  `LuaS30IDE.exe` thật (cửa sổ "LuaS30 IDE", dialog thiết lập lần đầu chạy
  đúng). `build_frozen.py` nay copy `VERSION` vào thư mục frozen: thiếu nó,
  bản đóng băng báo "unknown" và làm nhiễm `setup_state.json`, khiến bản cài
  thật bị hỏi lại thiết lập lần đầu.
- Sửa lỗi giao diện bản đóng gói (nền desktop xuyên qua sidebar trong suốt +
  "Phiên bản unknown"): `LuaS30IDE.spec` có `datas=[]` nên `dark_theme.qss`
  không được bundle — `main._stylesheet()` thiếu tệp này, cửa sổ frameless bật
  `WA_TranslucentBackground` và lộ nền màn hình. Spec nay chèn
  `app/vxpui/resources/dark_theme.qss` vào `datas`, `build_frozen.py` copy
  `VERSION` cạnh exe, và `verify_release.py` thêm chốt chặn bắt buộc tệp qss
  phải có trong stage. Kiểm chứng trên desktop thật: sidebar tối vẽ đúng.
- Sửa UI Designer không hiển thị ảnh do AI tạo (chỉ Panel thủ công hiện, ảnh
  thành placeholder núi, mở lại dự án vẫn hỏng): `DesignerItem.from_dict` chỉ
  tra ảnh trong registry RAM, mà công cụ AI ghi asset + thiết kế thẳng ra đĩa
  rồi — không đăng ký gì. Nay `from_dict` nhận `base_dir` (gốc project) và tự
  `load_image` từ đĩa khi `src` trỏ tới tệp có thật nhưng chưa có trong registry
  (đồng thời đăng ký để palette dùng chung). `set_project` khi cùng project cũng
  `reload_current_screen()` (bỏ qua nếu canvas còn thay đổi chưa lưu), và
  `_apply_ai_changes` gọi designer refresh khi AI vừa ghi `ui_design.json` hoặc
  `assets/`. Thêm 3 check hồi quy vào `ui_designer_check.py`.
- Sửa nút "Dừng" không dừng được khi build/run (hộp thoại kẹt "Đang chạy",
  máy vẫn lag vì compile âm ỉ): `QProcess.kill()` trên Windows chỉ giết tiến
  trình python cha, còn `arm-none-eabi-gcc`/`verify_elf.py`/`VXPEmu.exe` là con
  cháu vẫn giữ tay cầm stdout mở → Qt không phát `finished()`. Thêm
  `kill_process_tree()` (`taskkill /F /T /PID`, POSIX dùng `killpg`) mà
  `BuildService.cancel()` và `EmulatorService.stop()` gọi trước khi `kill()`;
  `stop()` của giả lập thôi `taskkill /IM VXPEmu.exe` toàn cục (tắt nhầm cả
  instance không liên quan) để chuyển sang diệt đúng cây theo PID.
  `LuaRunner.stopped_by_user` phân biệt "Đã dừng" với "thất bại" khi báo kết quả.
- Tối ưu IDE hết giật khi run giả lập: `VxpMainWindow` gom output console vào
  bộ đệm và chỉ repaint console + build log + hộp thoại Run mỗi ~60ms
  (`_flush_console`, thay vì vẽ lại cho TỪNG chunk hàng trăm dòng compile); hộp
  thoại Run giới hạn `setMaximumBlockCount(2000)` để log dài không phình.
- Chat AI hiện "hiệu ứng suy luận" của agent theo ảnh mẫu: mỗi lượt chạy tool
  chèn khối thu gọn `▸ Đã chạy N công cụ` vào transcript (bấm mở ra xem tên tool
  + lý do, giữ nguyên khi chuyển phiên qua `_render_history`), kèm dòng trạng
  thái có icon braille quay `⠿ Đang suy nghĩ… · Bước i` hiện/ẩn theo vòng đời
  agent (`_set_agent_active` bật/tắt `QTimer`, `_set_think_phase` đổi câu theo
  đọc ngữ cảnh · chạy công cụ · soạn code).
- AI Agents luôn trả lời bằng tiếng Việt: `_system_prompt` thêm chỉ dẫn BẮT BUỘC
  dịch `visible_text`, `reasoning_summary` và `reason` của tool sang tiếng Việt,
  đồng thời giữ nguyên mã nguồn, tên hàm/biến, đường dẫn và lệnh shell.
- README: mục "Ghi công" là bảng liệt kê thư viện + nguồn (Python/PSF,
  PySide6·Qt LGPLv3, Lua 5.1.5 MIT-style, GNU Arm Toolchain GPLv3+GCC-exception,
  Unicorn GPLv2, Inno Setup, WiX MS-RL, font Segoe) và KHÔNG tuyên bố bản quyền
  bao trùm. Đã bỏ hẳn câu dẫn "LuaS30 IDE được dựng trên nền rất nhiều dự án…"
  và dòng thông báo `© Qeafivels All rights reserved. · https://qeafivels.com/`
  khỏi README; bản quyền/website giờ chỉ còn ở `LICENSE`, hộp thoại About và
  `doc/legal/THIRD_PARTY_NOTICES.md`. `validate_about_credits.py` cập nhật tương
  ứng: README chỉ cần trỏ `](LICENSE)` và được CHỐT là không chứa lại chuỗi bản
  quyền/website. (Đồng thời dọn nốt khối conflict `<<<<<<< HEAD`/`>>>>>>>` bị commit
  sót từ lần merge `39056b4` — giữ nội dung "Ghi công" phía HEAD.)
- UI Designer nâng cấp chỉnh sửa theo chuẩn Canva: hoàn tác/đi lại theo từng
  bước (`Ctrl+Z`/`Ctrl+Shift+Z`, tối đa 60 trạng thái, chọn lại đúng các thành
  phần cũ), chọn nhiều bằng khung cao-su/`Shift`+click/`Ctrl+A`, resize 8 tay
  nắm (4 góc + 4 cạnh, kẹp trong màn hình, tối thiểu 4px), tinh chỉnh bằng mũi
  tên (1px, `Shift`=10px), sao chép/dán `Ctrl+C`/`Ctrl+V` tự cấp ID duy nhất,
  căn trái/giữa/phải · trên/giữa/dưới + phân bố đều qua menu chuột phải,
  khoá lớp (bỏ kéo/resize/nudge/Xoá, viền chấm, lưu khoá `lock` trong
  `ui_design.json`), sửa chữ tại chỗ bằng kích đúp, pan bằng `Space`+kéo hoặc
  chuột giữa, zoom tới 4× với `Ctrl+0/+/−`, và nhãn `x, y  w×h` trực tiếp khi
  kéo/resize.
- Sửa resolve màu icon, pipeline build UTF-8 và khôi phục đường dẫn
  toolchain (commits 71e0c25, 0cf75b9).
- KHOANH VÙNG AI Agent vào ĐÚNG project đang mở: agent không còn đọc/sửa được
  mã nguồn cài đặt của chính LuaS30 IDE. Đã xoá hẳn tool `engine` và cửa hậu
  `args.scope="engine"` (cùng `ENGINE_ALLOWED_PREFIXES`, `<engine_core>` trong
  context, skill `engine-api-check`); `AIReadOnlyToolService` bỏ mọi `scope`,
  mọi đường dẫn read/grep/glob chỉ resolve theo gốc project và chặn thoát ra
  ngoài; prompt đổi sang "Project scope (STRICT)". Lời gọi `engine` kiểu cũ
  được parser hạ cấp thành read/grep/glob project-scoped. Validator:
  `tools/validate_ai_skills.py` (mục 3–5).
- Sửa AI Agent không thêm được code vào project: trước đây MỘT thao tác `find`
  không khớp làm hỏng cả đợt `prepare()`. Nay `AIChangeService` có
  `EditMatchError` + `_flexible_span` (khớp dòng dung cảm thụt lề/khoảng trắng,
  chỉ khi khớp duy nhất) và bỏ qua mềm từng edit lỗi (vẫn raise với lỗi đường
  dẫn/an toàn), ghi "N edit(s) skipped" vào summary — tệp mới vẫn được tạo.
- Phát hiện lỗi + mở file cần sửa kiểu Antigravity: sau mỗi đợt áp code,
  `MainWindow` gọi `ai_chat.report_errors_after_change()`; `AIChatView` nối
  provider dòng PROBLEMS cấu trúc (`set_problems_rows_provider`) +
  `set_open_location_provider`, dựng thẻ "⚠ N lỗi cần sửa" với mỗi mục là neo
  `x-luas30://openfile/<id>:<idx>` bấm để mở đúng tệp:dòng:cột qua
  `open_location`, và tự mở lỗi đầu tiên. Kiểm chứng live: thẻ render, chỉ
  severity error được ưu tiên, click neo mở đúng tệp. Validator:
  `tools/validate_ai_skills.py` (mục 7).
- Sửa composer Chat AI: dòng `self.prompt.clear()` trước đây kẹt trên cùng dòng
  `return` nên chỉ chạy ở nhánh câu-trống — nay tách dòng riêng để XOÁ HẾT text
  ngay khi bấm Gửi. Đồng thời siết TRẠNG THÁI NÚT send: khi Agent đang chạy, nút
  luôn giữ là nút làm việc (glyph stop + `running`), chỉ hoàn nguyên về send khi
  lượt xong thật (`_response_ready` không còn đặt "Ready" giữa vòng lặp tool) HOẶC
  có LỖI; mỗi lỗi (kết nối/thực hiện, hoặc áp mã vào project thất bại) nay in
  DÒNG LỖI đỏ qua `_append_error_line()` rồi `_set_agent_active(False)` — hết
  cảnh nút kẹt "đang làm việc" mãi. Kiểm chứng live + `drive_ide_as_user.py`,
  `validate_ai_agent_shell.py` đều xanh.
- Chạy thử game/app một phát, cả cho người dùng LẪN AI Agent: thêm tool
  `run_app` (build project → launch VXPEmu `--screen-only` chạy ngầm → chờ khung
  hình ổn định → `VxpEmuWindow.capture_to_file` chụp ảnh khói vào
  `<project>/build/smoke/run-*.png` → tự đóng giả lập). Người dùng gõ `/run`
  (alias `/test`, `/chạy`) hoặc bấm quick-action "Chạy thử game/app"; agent phát
  `{"tool":"run_app","args":{"op":"run"|"stop"}}`. Chuỗi này BẤT ĐỒNG BỘ:
  `request_run_app` giữ nút ở trạng thái làm việc tới khi `MainWindow._report_ai_run`
  gọi lại `on_run_app_finished`; lỗi build/giả lập in dòng LỖI đỏ + hoàn nguyên nút
  (không tự loop model khi fail), Plan mode từ chối chạy. Tài liệu:
  `doc/ai/skills/vxp-build-run/SKILL.md`, `doc/studio/STUDIO_GUIDE.md`. Validator:
  `tools/validate_ai_run_app.py`.
- `run.bat`: bỏ hard-code số phiên bản — banner + log giờ ĐỌC TRỰC TIẾP từ file
  `VERSION` gốc repo (`set /p APP_VERSION`) nên luôn khớp, không phải sửa tay mỗi
  lần bump version.
- Tài liệu nêu rõ nguyên tắc kiểu Codex: "codebase" mà AI đọc VÀ ghi là **project
  mà người dùng tạo/mở** (`Documents\LuaS30 Projects\<name>`), KHÔNG bao giờ là thư
  mục cài đặt LuaS30-IDE (IDE chỉ là trình soạn thảo + biên dịch MRE + launcher
  VXPEmu). Ghi được cưỡng chế bởi `AIChangeService._safe_target` (chối đường dẫn
  tuyệt đối, ổ đĩa, `..`/symlink thoát khỏi gốc, tên được bảo vệ); tệp mới tạo dưới
  gốc project, tệp cũ backup ở `<project>/.luas30/ai-backups/`. Viết ở
  `doc/studio/STUDIO_GUIDE.md`.
- **Ép code fenced trong chat thành tệp dự án** (Codex-style): khi model bỏ qua
  protocol `luas30-edit` và chỉ dán nguồn trong khối Markdown thường, nếu info-string
  CỦA KHỐI khai báo tệp (` ```lua path=src/menu.lua ````, `file=`, hoặc bare
  ` ```src/conf.lua ``) thì `_recover_fenced_files` (`ai_agent_protocol.py`) biến nó
  thành `CodeEditAction` ghi CẢ TỆP MỚI vào project đang mở, và xoá khối code đó khỏi
  văn bản chat. Đây chỉ là fallback: khối `luas30-edit`/XML thắng, fence chỉ ghi ngôn
  ngữ không đường dẫn vẫn rơi về phục hồi theo tệp đang mở, snippet ngắn không đường
  dẫn KHÔNG tạo tệp (tránh nhận nhầm). `_extract_fenced_path` chặn trước tuyệt đối/ổ
  đĩa/`..`, `_safe_target` giam lại lần nữa khi ghi. Prompt bảo model đặt đường dẫn
  tương đối-project trong fence. Validator: `tools/validate_ai_fenced_files.py`.
- **Thẻ lỗi PROBLEM cập nhật realtime trong Chat AI** (thay snapshot tĩnh): trước đây
  mỗi lần áp code lại chèn MỘT thẻ "N lỗi cần sửa" đứng im, sửa xong trạng thái không
  đổi. Nay `AIChatView` giữ MỘT **thẻ sống** (`_live_problem_card`) và khớp lỗi theo
  **chữ ký** (`_problem_row_sig` = severity + đường dẫn tương đối + thông điệp, KHÔNG
  dùng số dòng vì nó nhảy khi sửa). Lỗi biến mất -> `✓ Đã sửa` (xanh, gạch ngang); lỗi
  mới -> thêm vào; header đếm lại `⚠ còn N lỗi · ✓ M đã sửa`; sạch hết -> `✓ Đã sửa hết`.
  `refresh_problem_card()` chạy cả khi áp code (`report_errors_after_change`) LẪN khi
  editor phát `diagnostics_changed`: `MainWindow._diagnostics_changed` mồi
  `_ai_problem_timer` (throttle 400ms) -> `_refresh_ai_problem_card`, nên thẻ bám theo
  cả lỗi người dùng tự sửa, không chỉ lỗi AI sửa. Tool `problems` cũng ghi vào thẻ sống.
  Phiên mới hoàn nguyên thẻ. Validator: `tools/validate_ai_problem_card_live.py`.
- **Bong bóng tin nhắn Chat AI theo kiểu Codex/DuckChat**: `_append_message` trước
  đây chỉ in nhãn trần `<b>You</b>` / `<b>AI` bám sát mép trái dock. Nay mỗi lượt
  là một **thẻ** đúng chất Codex: lời người dùng = bong bóng nền `BG_RAISED` viền
  mảnh **canh phải**, lời trợ lý = khối nội dung **canh trái** có viền trái accent
  mảnh, và phía trên là **header dòng nhỏ** — "BẠN" hoặc `◆ <tên model>` (màu
  accent) để biết model nào đang trả lời. Cột nội dung có khoảng thở
  (`document().setDocumentMargin(12)`) thay vì chữ kẹt mép. Thuần PySide6 (dựng
  HTML trong `QTextBrowser`), không đổi hành vi vòng lặp agent.
- **Sửa AI "không thấy sửa gì": nhận tool-call có THÂN LÀ JSON**: model kiểu
  Ling/Gemini hay bỏ qua fenced `luas30-edit` và phát thẻ
  `tool_call` tên dính thẳng sau tag, thân là JSON (không phải cặp
  `arg_key`), thường quên đóng thẻ — đúng như ảnh: tool-call tên
  `luas30-edit` mang mảng JSON `{path,find,replace}`. Ca `EDIT_RE` (cần fence)
  lẫn `XML_TOOL_RE` (cần `>` + `arg_key` + đóng thẻ) đều bỏ lọt, nên lỗi sửa
  của model không bao giờ được áp. Hàm mới `_recover_json_tool_calls` dùng
  `json.JSONDecoder().raw_decode` (chịu thân nhiều dòng + thẻ không đóng) dịch
  nó thành `CodeEditAction`/`ToolAction` và xoá khỏi văn bản chat. Chỉ nhận khi
  thân mở bằng `[` hoặc `{`; prose nhắc `tool_call` không payload vẫn bỏ qua.
  Chính sách plan/disabled vẫn do view `_edit_policy()` giữ (giống fenced block).
  Validator: `tools/validate_ai_json_toolcall.py`.
- **Khu vực AI Trợ lý khoác giao diện DuckChat (QSS thuần Python)**: thêm nhóm
  token `CHAT_*` vào `palette.py` — nền gần đen (`#0d0d0d`→`#242424`), accent cam
  `#ff6700`, viền `#262626` — rồi trỏ toàn bộ selector `AIChat*`/`AIWelcome*`/
  `AIQuick*`/`AIContext*`/`AIThinking*`/`AIActivity*`/`AIShell*`/`AIAccess*`/
  `AIChanges*`/`AIProvider*`/`AISessionsMenu` trong `theme.py` về `@CHAT_*`
  (bo góc vẫn chỉ 6/8/12, nút gửi pill, badge model font mono); `ai_chat_view.py`
  đổi HTML bong bóng/thẻ/card sang `palette.CHAT_*`, giữ màu trạng thái ngữ nghĩa
  (xanh/đỏ/hổ phách) cho diff·PROBLEM·shell. Chỉ đổi CHROME — cơ chế full access
  (`_edit_policy`/`_shell_policy`/`ACCESS_MODES`/vòng lặp agent) và palette VS
  Code toàn cục giữ nguyên. `studio_theme_check.py` PASS, 19 validator
  `validate_ai_*` PASS.
- **Nâng khu vực AI Trợ lý sát bản DuckChat thật (thẻ tin nhắn + khối code)**: mỗi
  lượt chuyện giờ là một **thẻ bo viền** có **avatar tròn** (người dùng nền
  `CHAT_RAISED` chữ "B" canh phải; trợ lý nền `CHAT_ACCENT_DEEP` dấu ◆ canh trái)
  kèm **tên** "Bạn"/"AI Trợ lý", thay cho khối bong bóng cũ chỉ in nhãn trần.
  `_render_markdown` tách văn bản thường khỏi **fenced code block**: khối code
  render dạng **bảng có cột số dòng** (số mờ canh phải, code thụt đầu dòng bằng
  `&nbsp;`), **tô màu cú pháp Lua** (comment/chuỗi/số/từ khoá qua `_LUA_TOKEN_RE`
  + palette `SYN_*`), và **nút "Sao chép"** neo `x-luas30://copy/<id>` — bấm là
  nội dung vào clipboard (`_copy_blocks` đăng ký khi render, `QApplication.clipboard`).
  Tab "Chat" đang chọn đổi sang **viền cam** (`#AIChatTab:checked` nền trong);
  composer chia **hai hàng**: hàng icon đính kèm/@/{ } + gợi ý "Shift + Enter để
  xuống dòng", hàng pill truy cập/model + **nút "Gửi"** thành pill chữ cam (giữ
  nguyên `objectName=AIChatSendIcon` và dòng `apply_icon(... "stop", 13)` mà
  validator `validate_ai_full_access_stop.py` ghim); **status bar đáy** mới
  "● Ready" trái + tagline "Hỗ trợ lập trình tốt hơn mỗi ngày ♥" phải. Thuần
  PySide6/HTML trong `QTextBrowser` (góc bo của thẻ là giới hạn của QTextBrowser,
  chấp nhận vuông); không đụng vòng lặp agent, `_edit_policy`/`_shell_policy` hay
  palette VS Code toàn cục. `studio_theme_check.py` PASS, 19 `validate_ai_*` PASS.
- **AI Trợ lý theo chuẩn "Modern Dark IDE / AI Coding Assistant"**: bảng `CHAT_*`
  được viết lại đúng spec prompt — nền `#0d1014`, panel `#11151a`, thẻ `#151a21`,
  ô nhập `#131820`, accent `#ff6a00/#ff7a1a/#e95f00`, cùng 20 token mới (trạng
  thái dừng `CHAT_STOP`, nút gửi bị tắt, timestamp, avatar người dùng, thanh cuộn,
  khối code `CHAT_CODE_*` và 6 màu cú pháp `CHAT_SYN_*`). `theme.py`: header
  50px, tab Chat hoạt động nền `#1c1815` viền cam, **thanh cuộn mảnh 6px**
  (thumb `#343c47`), composer bo 10px viền focus cam, pill Full Access **viền cam
  thay vì tô cam**, nút Gửi/Gửi-Dừng có `:pressed` + `:disabled`; `studio_theme_check.py`
  nới tập hợp bán kính cho phép thành 6/8/10/12. Logic tách vào module mới
  `ai_chat_render.py` (`TranscriptHtmlRenderer`: avatar, đầu thẻ kèm **timestamp
  góc phải**, markdown, tô sáng Lua cả lời gọi hàm, khối code có số dòng + "Sao
  chép"), `ai_chat_view.py` thêm **composer tự lớn 86→180px**, **cuộn thông minh**
  (không nhảy xuống nếu người dùng đang đọc lên — hiện nút "↓ Tin nhắn mới"),
  **Esc = dừng agent**, nút Gửi tự tắt khi trống, nhãn/model co giãn responsive
  360/420/480/600 (rút còn icon dưới 430px, tên model có ellipsis). Toàn bộ hợp
  đồng cũ giữ nguyên: `ACCESS_MODES`/chính sách sửa-vỏ, `worker.abort()`, neo
  `x-luas30://{copy,step,review,more,openfile}`, các dòng apply_icon bị validator
  ghim. `studio_theme_check.py` PASS, 19 `validate_ai_*` PASS, render offscreen
  360/420/480/600 không rò theme sáng.
- **Siết đúng thông số spec của prompt "Cursor agent"** (đợt 2, chỉ số đo — không
  đổi kiến trúc): tab Chat cao **42px** chữ 13px (spec 42–46); tiêu đề "AI Trợ lý"
  **18px** (spec typography 18–20); icon header **18px** (spec 18–20); pill model
  cao **42px** (spec 42–44); nút Gửi cao **44px** (spec 44–46); composer đệm trong
  **14px** (spec padding 14, đồng bộ hằng số tự lớn 86→180 sang `pad=32`); đầu
  khối code đệm 10px → cao ~35px (spec 34–38); font code đổi sang chuỗi
  **"JetBrains Mono" → "Cascadia Code" → Consolas** (thay vì Consolas trần) và
  transcript khai báo **"Inter" → "Segoe UI"** theo đúng thứ tự ưu tiên typography
  spec. Kiểm lại bằng `studio_theme_check.py` PASS + 19 `validate_ai_*` PASS +
  render offscreen 360/420/480/600: footer không tràn, send/model không overlap.
- **Tệp AI sửa/tạo tự mở thành tab editor kiểu VS Code**: `main_window.py` thêm
  `_open_ai_touched_tabs(change_set)` — sau `_apply_ai_changes` (cả luồng review
  bấm "Áp" lẫn auto-apply của Edit automatically/Full access qua
  `QTimer.singleShot(0, ...)`) và `_accept_ai_change_file` (accept từng file),
  mọi tệp trong change set được `tabs.open_file` mở tab (tệp đã mở thì nạp lại,
  không sinh tab trùng), nội dung đúng bản after, không dirty, tab cuối mở được
  chọn và focus. Tệp không tồn tại/bị loại bị bỏ qua êm. Smoke offscreen thật
  (dựng VxpMainWindow + dự án tạm + AIChangeService.apply): 7/7 PASS; 19
  `validate_ai_*` PASS.
- **Đồng bộ bảng màu AI Trợ lý theo UAGet Desktop**: toàn bộ token `CHAT_*`
  trong `palette.py` đổi sang đúng scheme indigo-navy + cam của
  `D:\UAGet\uaget\src\uaget\desktop\styles\dark.qss` — nền chat `#19192e`,
  header `#18182d`, card `#202039`, viền `#303049`/`#24243d`, accent
  `#ff8a00` (hover `#ff9a22`, nhấn `#e87a00`), tab đang chọn `#1c2a3b`, nút
  Dừng `#e85d75`, timestamp `#b99069`, send disabled `#4b566a`, code block
  `#10111a` + 6 màu cú pháp theo highlighter `chat_area.py` (`#ef8fcb`,
  `#6bdc91`, `#d7a6ff`, `#ffad4a`, `#777d86`, `#d3d7e3`). Chỉ đổi giá trị
  token — `theme.py`/view không sửa, chrome toàn cục và 3 lớp kích thước
  (42/18/44px) giữ nguyên. Verify: `studio_theme_check` FULL PASS (0 khối
  sáng), 19 `validate_ai_*` PASS, render offscreen 360/480px khớp ảnh tham
  chiếu.
- **Đồng bộ màu UAGet cho TOÀN BỘ IDE + đổi tên "AI Trợ lý" → "AI Agent"**:
  palette toàn cục trong `palette.py` chuyển từ VS Code Dark Modern sang đúng
  scheme UAGet (nền `#111122`/`#19192e`/`#1c1c33`, viền `#24243d`–`#303049`,
  accent cam `#ff8a00` với chữ tối `#1a1a2c`, selection `#1c2a3b`, status bar
  `#151527`); 41 màu chrome cấu trúc trong `app/vxpui/*.py` +
  `resources/dark_theme.qss` được map hàng loạt sang UAGet (giữ nguyên màu cú
  pháp Material Ocean của editor và swatch thẻ dự án `home_page.py`). Chuỗi
  hiển thị "AI Trợ lý"/"LuaS30 AI Assistant" đổi thành "AI Agent"
  (`ai_chat_view.py`, `ai_chat_render.py`, `STUDIO_GUIDE.md`). Verify:
  `studio_theme_check` FULL PASS (WCAG 14/14 với bảng màu mới, 0 khối sáng,
  ảnh render toàn IDE + Project Hub), **57/57 validators** PASS, quét CJK sạch.
- **Thanh cuộn thủ công hiện rõ trong AI Agent**: scrollbar của transcript
  (`QTextEdit#AIChatTranscript`) từ 6px track trong suốt → 10px có nền
  `@CHAT_PANEL` + viền `@CHAT_BORDER_WEAK` (cả trục đứng lẫn ngang), thumb
  `min-height/width` 36→48px dễ bấm-kéo; policy vẫn AsNeeded nên chỉ chiếm
  chỗ khi nội dung tràn. Render offscreen 14 tin dài: scrollbar hiện, kéo được
  (max=1805); pill "↓ Tin nhắn mới" + smart-scroll không đổi hành vi. 19
  `validate_ai_*` + theme check FULL PASS.
- **Bố cục chuyên nghiệp cho menu chọn chế độ truy cập (AI Agent)**:
  `AccessModeOption` nâng hàng 62→64px, icon đặt trong chip bo góc 30×30 căn
  giữa dọc (thay vì lề trên), tiêu đề 13px/600, mô tả 11px tự xuống dòng
  (hết chữ nhỏ mờ 10px), dấu ✓ căn giữa phải; thêm header in hoa "CHẾ ĐỘ
  TRUY CẬP" đầu popup, hàng đang chọn có nền + viền accent nhạt, pill chế độ
  cao 40→42px đồng bộ tab. Render offscreen đã soi ảnh; theme check + 19
  `validate_ai_*` PASS.
- Menu sidebar trang chủ (Trang chủ / Dự án / Tài liệu) căn TRÁI và có tính
  năng thật: QSS mới cho `#SidebarButton`/`#SidebarUtility`/`#SidebarSection`
  (nền trong, padding 10×12, hover đậm, hàng đang chọn nền `#1C2A3B` + vạch
  accent cam trái 3px). "Trang chủ" giờ hiển thị 4 dự án gần nhất với tiêu đề
  "Dự án gần đây" + nút "Xem tất cả →"; "Dự án" mở toàn bộ lưới "Tất cả dự
  án"; "Tài liệu" mở `doc/INDEX.md`. Verify: studio_theme check PASS,
  57/57 validators PASS, render offscreen 2 chế độ đã soi.
- Mọi hộp thoại modal bỏ thanh tiêu đề mặc định của hệ điều hành, dùng custom
  Title Bar theo chuẩn hộp thoại "Cấu hình MediaTek MRE SDK" (ngoại trừ cửa sổ
  giả lập): ~30 chỗ `QMessageBox`/`QInputDialog`/`QColorDialog`/`QFileDialog`
  chuyển sang `NoticeDialog`/`ConfirmDialog`/`TextInputDialog`/`ColorPickerDialog`/
  `FilePickerDialog`; `AboutDialog` + `SetupDialog` dựng lại trên nền
  `CustomDialog`; `FilePickerDialog` thêm chế độ lưu tệp (ghi đè có xác nhận).
  Verify: 57/57 validators + studio_theme check PASS, render offscreen 9 hộp
  thoại đã soi từng ảnh, quét CJK sạch.


## 1.15.0 — AI Workbench v1

- Added AI access selector under the ChatAI prompt.
- Added Ask before changes, Edit automatically, Plan mode and Full access modes.
- Kept sensitive/dangerous shell commands confirmation-gated in Full access.
- Replaced inline provider drawer with a custom AI Provider Settings dialog.
- Added Test Connection, Apply and Save & Close provider actions.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_15_0.md) (+11 mục khác)

## 1.15.0 · Agent Editor Fix — AI Agent Editor Apply Fix

- AI providers that ignore the `luas30-edit` protocol and return a normal fenced source block can now be recovered into an edit proposal for the active project file.
- Generated source no longer has to remain only in the Chat transcript when the request clearly asks to create, fix, update, refactor, or otherwise modify code.
- `Ask before changes` keeps the recovered edit pending for review/apply.
- `Edit automatically` and `Full access` continue through the existing automatic apply pipeline, writing the project file and refreshing any open editor buffer.
- Explanation/review prompts are excluded from fallback recovery to avoid accidental file replacement.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_15_0_AGENT_EDITOR_FIX.md) (+3 mục khác)

## 1.14.0 — AI Agent Activity + Shell

- Added collapsible AI Activity / Reasoning Summary panel.
- Added explicit policy against raw/private chain-of-thought display.
- Added `luas30-summary` response protocol.
- Added `luas30-shell` JSON action protocol.
- Added Shell access modes: Disabled, Ask, Auto Safe.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_14_0.md) (+8 mục khác)

## 1.13.0 — MediaTek MRE Project Wizard

- Replaced the old one-line New Project name prompt with a custom MediaTek MRE SDK modal.
- Added APPNAME, APPVER and VENDOR fields.
- Added screen-resolution preset selection.
- Added MTK6260, MTK6261, MTK6250 and MTK6225 presets.
- Added Heap RAM presets with chipset-specific recommended defaults.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_13_0.md) (+7 mục khác)

## 1.12.0 — Series 30+ High Compatibility

- Added S30+ compatibility profiles: auto, standalone, s30plus-native, nokia225-rm1011.
- Added native MRE SDK layout detection.
- Added ARM GCC high-compatibility MRE compile defines.
- Added native linking against local MRE SDK per*.a libraries and SDK scat.ld.
- Added explicit `vm_main()` application entry.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_12_0.md) (+8 mục khác)

## 1.11.0 — AI Workbench

- Added tab right-click Close / Close Others / Close All Tabs.
- Close All Tabs reaches every editor group.
- Rebuilt workbench as Explorer | center editor | ChatAI.
- Compact Bottom Panel is now center-only.
- Added ChatAI secondary sidebar and Ctrl+Alt+I.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_11_0.md) (+5 mục khác)

## 1.10.3 — Colored Panel / HEX / Unique AppID

- Added semantic colors to Console and Build log output.
- Added colored direct-terminal prompt/output.
- Added HEX tab to Compact Bottom Panel.
- Added 64 KiB paged VXP hex viewer with offset/hex/ASCII columns.
- Run/Emulator automatically loads and selects the exact manifest VXP in HEX.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_10_3.md) (+5 mục khác)

## 1.10.2 — Direct Integrated Terminal

- Removed the separate terminal command QLineEdit.
- Added `TerminalSurface`, a direct-edit QPlainTextEdit.
- Commands are typed directly after the cwd prompt.
- Protected terminal history from normal edits.
- Added Up/Down command history in the terminal surface.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_10_2.md) (+6 mục khác)

## 1.10.1 — Compact Bottom Panel

- Bottom Console/Build/Problems/Terminal panel is hidden on every startup.
- Terminal toggle opens/focuses the panel and hides it when invoked again.
- Added top-right Close Panel button.
- Hiding Terminal does not kill its QProcess shell.
- Added compact 145 px default reveal height and 72 px minimum.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_10_1.md) (+4 mục khác)

## 1.10.0 — Multi-Toolchain MRE Profiles

- Added `tools/toolchain_profiles.py`.
- Added ARM GCC, RVDS/RVCT and ARM ADS1.2 compiler profiles.
- Added `--compiler-profile auto|gcc|rvds|ads12`.
- Added `--entry-symbol` override.
- Added nested toolchain detection for gcc/readelf, armcc/armlink/fromelf and tcc.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_10_0.md) (+9 mục khác)

## 1.9.8 — Startup Screen Setting

- Added Settings -> Startup screen.
- Added Welcome startup mode.
- Added Project Hub startup mode.
- Added Empty Editor startup mode.
- Empty Editor restores project/layout but restores no file, untitled or tool tabs.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_8.md) (+4 mục khác)

## 1.9.7 — MRE GCC Build Fix

- Fixed literal `\n` being written into generated GCC probe C source.
- Fixed the same probe-source bug in `toolchain_doctor.py`.
- Added shared MRE GCC compile/link flag definitions.
- Added `MRE`, `GCC` and `__MRE_COMPILER_GCC__` compile defines.
- Preflight now verifies GCC driver, cc1, assembler and the MRE-style linker path.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_7.md) (+3 mục khác)

## 1.9.6 — Clean Startup Tabs

- Startup/restart no longer reopens source file tabs.
- Startup/restart no longer recreates untitled editor tabs.
- Removed automatic `main.lua` fallback during workspace restore.
- Session save filters file/untitled tabs from startup state.
- Older session files containing document tabs are accepted, but those entries are skipped.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_6.md) (+2 mục khác)

## 1.9.5 — Explorer / Activity Bar Toggles

- Added Workbench Bar Explorer button.
- Added Workbench Bar Activity Bar button.
- `Ctrl+B` toggles Explorer / Primary Side Bar.
- `Ctrl+Alt+A` toggles Activity Bar.
- Both actions are in View and Command Palette.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_5.md) (+2 mục khác)

## 1.9.4 — Project Hub Clean Layout

- Welcome and Project Storage now use a clean full-width central layout.
- Activity Bar is hidden on Project Hub pages.
- Explorer/Search sidebar is hidden on Project Hub pages.
- Find/Replace bar is hidden on Project Hub pages.
- Console/Build/Problems/Terminal bottom panel is hidden on Project Hub pages.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_4.md) (+3 mục khác)

## 1.9.3 — Integrated Terminal / Console

- Added real integrated Terminal based on QProcess.
- Added Console and Terminal toggle actions in View.
- Added top-level Terminal menu with New/Kill/Clear actions.
- Added Ctrl+J panel toggle, Ctrl+Shift+Y Console toggle, Ctrl+` Terminal toggle and
- Bottom panel is hidden by default in a new workspace.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_3.md) (+3 mục khác)

## 1.9.2 — Welcome / Project Hub

- Added VS Code-like `Welcome` startup tab.
- Welcome opens at tab index 0 of editor group 0.
- Added New Project, Open Folder, Import into Storage and Manage Storage start actions.
- Added Recent project list backed by managed Project Storage.
- Added Project Storage count/size/build summary and current-workspace card.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_2.md) (+5 mục khác)

## 1.9.1 — Workspace Session Restore

- Added automatic VS Code-like workspace session persistence.
- Added real multi-group editor workspace with horizontal editor groups.
- Added View → Split Editor Right and Close Editor Group.
- Restores current project, open source/tool/untitled tabs, tab order, active tab and active group.
- Restores editor-group splitter sizes.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_1.md) (+5 mục khác)

## 1.9.0 — Tabbed Workspace + Project Storage

- Removed whole-workspace switching for Assets, Designer, Emulator and Settings.
- Source files and persistent tools now share one closable/movable editor tab strip.
- Added keyed tool tabs so opening a feature focuses the existing instance.
- Added Toolchain Doctor as a real tab backed by `toolchain_doctor.py`.
- Project Doctor and Runtime Compatibility Matrix now open result tabs.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_0.md) (+11 mục khác)

## 1.8.4 — Portable ARM GCC Compile Fix

- Fixed portable ARM GCC child backend/DLL lookup on Windows.
- Build process now prepends bundled `arm-gcc/bin` and `arm-none-eabi/bin` to its local PATH.
- Added automatic GCC driver/cc1/assembler compile preflight.
- Added `tools/toolchain_doctor.py`.
- Build failures now include compiler stderr in the raised error message.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_4.md) (+2 mục khác)

## 1.8.3 — Runtime Compatibility Matrix

- Added `compat/runtime_abi_contract.json`.
- Added per-firmware MRE symbol manifests under `compat/mre/`.
- Added host-side runtime compatibility evaluator.
- Matrix rows report native/effective capabilities, selected ABI aliases, activated
- Added JSON, CSV and text matrix reports.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_3.md) (+4 mục khác)

## 1.8.2 — Runtime Compatibility Layer

- Added `ls30_compat_report` and compatibility levels: full/degraded/incompatible.
- Added native-vs-effective capability detection.
- Added conservative same-signature ABI alias resolution and alias hit reporting.
- Added safe fallbacks for graphics helpers, text metrics, resource init, file commit,
- Added software line/fill fallbacks so firmware only needs one basic primitive.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_2.md) (+3 mục khác)

## 1.8.1 — Single VXP

- Removed normal per-device VXP build selection.
- Removed `build_matrix.py`.
- Removed `--profile`, `--imsi` and device-bound application artifact mode from the normal builder.
- Canonical final artifact is always `build/<ProjectName>.vxp`.
- Templates no longer contain `target_profile`.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_1.md) (+5 mục khác)

## 1.8.0 — Release Security

- Added explicit signing modes: dev, device-bound, cert100.
- Added profile-level direct-run signing policy.
- `--release` refuses signing modes that the selected profile does not declare trusted.
- Added VXP structure/trailer inspection and release manifests.
- Added multi-target `build_matrix.py` for separate device-specific artifacts.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_0.md) (+7 mục khác)

## 1.7.1 — AI Agent Project Protocol

- Added a mandatory two-file preflight: `doc/ai/SKILL.md`, then `doc/ai/PROMPT.md`.
- Added `doc/ai/README.md` as the AI-agent entry point.
- Agents must inspect the selected target profile and current project template before
- Agents must select `GENERIC_VXP`, `KNOWN_DEVICE_PROFILE` or `NEW_DEVICE_PORT`.
- Target application code is engine-only and should not add external runtime frameworks.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_7_1.md) (+5 mục khác)

## 1.7.0 — Compact Workbench

- Removed duplicate Dashboard, Projects, Build and standalone Console pages.
- Activity Bar now contains only Explorer, Search, Assets, UI Designer, Emulator and Settings.
- Top workbench bar now contains project context + Command Palette only.
- Reduced menu set to File / Edit / View / Run / Tools / About.
- Integrated Output / Build / Problems remains the only log/panel surface.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_7_0.md) (+7 mục khác)

## 1.6.3 — Documentation Layout

- Consolidated all Markdown documentation under `doc/`.
- Kept only root `README.md` outside the documentation tree.
- Replaced the former `docs/` directory with categorized `doc/` subfolders.
- Moved `SKILL.md` and `PROMPT.md` to `doc/ai/`.
- Moved third-party notices to `doc/legal/`.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_6_3.md) (+4 mục khác)

## 1.6.2 — Font Icon UI

- Removed emoji/pictogram-style control text from the Studio.
- Added `studio/app/ui/icons.py`.
- Uses Windows system font icons: Segoe Fluent Icons / Segoe MDL2 Assets.
- No font files are bundled.
- Activity Bar, menus, top command bar, Explorer toolbar, Find/Replace and major

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_6_2.md) (+3 mục khác)

## 1.6.1 — Documentation & Agent Guide

- Rewrote root README around the current v1.6 Native SDK architecture.
- Added `doc/INDEX.md`.
- Added Quick Start, Architecture, Build VXP, Studio Guide, Device Compatibility,
- Expanded Native SDK documentation.
- Updated Lua API reference with `capabilities()` and `device_info()`.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_6_1.md) (+5 mục khác)

## 1.6

- Rebuilt the Explorer as a VS Code-style directory tree.
- Added quick New File/New Folder/Refresh/Collapse controls.
- Added relative path copy, reveal, generated-folder toggle, rename and delete.
- Added `sdk/luas30/` as a project-owned SDK.
- Replaced CoreMRE-facing runtime calls with stable `ls30_*` API calls.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_6.md) (+8 mục khác)

## 1.5 — VS Code-style workspace

- Replaced the wide dashboard/sidebar chrome with a compact VS Code-style workspace.
- Added a top application menu: File, Edit, Selection, View, Go, Run, Terminal, Help, About.
- Added a narrow activity bar for Explorer, Search, Projects, Build, Emulator, Assets, UI Designer, Console and Settings.
- Converted the editor project/search pane to an Explorer-style primary sidebar with hidden internal tabs.
- Reduced oversized headings, rounded dashboard cards and decorative chrome across Studio views.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_5.md) (+5 mục khác)

## 1.4.2

- Added requirement-aware dependency manager.
- `run.bat` no longer downloads/upgrades Python packages on every launch.
- Added automatic offline fallback and explicit `--offline` mode.
- Added `--online`, `--deps-only`, and `--force-deps` launcher modes.
- Added persistent dependency change log and JSON environment state.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_4_2.md) (+3 mục khác)

## Studio 1.3

- Added Lua 5.1 + LuaS30 `engine.*` autocomplete.
- Added current/project symbol completion.
- Added Find/Replace with match highlighting and wrap-around navigation.
- Added low-overhead source minimap.
- Added dependency-free inline Lua structural diagnostics.

→ [Chi tiết](doc/release/changelog/CHANGELOG_STUDIO_1_3.md) (+6 mục khác)
