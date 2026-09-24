# LuaS30 Studio 1.0.3 — chi tiết

Tóm tắt đầy đủ theo từng đợt nằm trong `CHANGELOG.md` gốc (mục `[1.0.3]`).
Tệp này nhóm lại theo **hệ thống con** để đọc một mạch, và chỉ ra tài liệu sâu
của từng mảng.

1.0.3 là **bản đóng gói thứ hai**: nó gom toàn bộ công việc landed sau mốc
1.0.2 (2026-09-21 11:13) và phát hành lại dưới dạng **một file Setup EXE duy
nhất**. Không có thay đổi phá vỡ tương thích: project, `project.json`, `conf.lua`
và hợp đồng phím Lua giữ nguyên.

| | |
|---|---|
| File phát hành | `dist/LuaS30IDE-Setup-1.0.3.exe` (duy nhất 1 file) |
| Dung lượng | 511 171 480 byte (487,5 MB) |
| SHA-256 | `f404099bd77aee23786102bbc59db2f4794a6c0368ae88f20263c8b7f13e47af` |
| Nội dung | core IDE + toolchain ARM GCC + VXPEmu + Python embedded + wheels PySide6 offline |
| Cài đặt | per-user, `%LOCALAPPDATA%\Programs\LuaS30 IDE\`, không cần admin |

---

## 1. Goal Mode (`/goal`) — vòng lặp tự chủ

Mục tiêu bằng ngôn ngữ tự nhiên → agent tự chia bước → sửa tệp nguồn → tự chạy
lệnh debug → kiểm thử → xác nhận từng bước, cho tới khi xong.

- Trạng thái ở `<project>/.luas30/ai_goal.json`; điều khiển bằng tool `goal`
  (`plan`/`start`/`done`/`fail`/`blocked`/`finish`); dải tiến độ trong panel AI.
- Ngân sách lượt **có biên** (8/40/80 theo access mode). Hết ngân sách thì dừng
  và **giữ nguyên** mã đang dở — không tự xoá.
- Tên op của tool nằm ở **một nguồn** (`GOAL_OPS`, `ai_agent_protocol.py`) và
  service import lại đúng tuple đó, nên prompt và handler không thể lệch.

Tài liệu: [`doc/studio/AI_GOAL_MODE_1_0_2.md`](../../studio/AI_GOAL_MODE_1_0_2.md).

## 2. Phục hồi trạng thái (checkpoint / rewind)

- Mỗi lần áp code ghi `checkpoint.json` vào `.luas30/ai-backups/<stamp>/`, biết
  cả tệp AI **tạo mới** để xoá khi quay lui.
- **Hai kiểu quay lui tách bạch**, và lẫn lộn chúng là lỗi đã từng xảy ra:
  `restore_checkpoint(s)` = hoàn tác ghi **của** `s`; `rewind_to(s)` = hoàn tác
  mọi ghi **sau** `s`. "Về cuối bước N" phải dùng `rewind_to`.
- Bị chặn giữa đường thì tự quay lui về cuối bước đã xác nhận.
- Tệp **người dùng sửa tay** luôn được giữ nguyên và báo lại; chỉ tệp do chính
  AI ghi ở bước sau mới được ghi đè. Chốt này phân biệt **ai viết** qua
  `_ai_written_hashes`.

## 3. Tối ưu bộ nhớ đệm ngữ cảnh

Ba tầng (nội dung tệp / tiền tố ổn định / chọn nguồn). Đo trên
`templates/keypad-demo`: **32.8 ms → 4.7 ms (7×)**, 81% bundle dùng lại.

⚠️ Vân tay đệm dùng **TÊN mục**, không dùng mtime thư mục — NTFS ghi metadata
**trễ**, nên bản cũ phục vụ cây tệp cũ mà không báo lỗi.

## 4. Bộ nhớ công việc của AI Agent

`studio/app/services/ai_task_memory.py` — để agent **code dài hơn** và **nhớ
việc đang làm**. Bốn nguyên nhân làm nó mất mạch, cả bốn đều hỏng im lặng:
cửa sổ hội thoại cắt còn `_history[-16:]` mà không tóm tắt gì; đóng IDE mở lại
là mất ngữ cảnh; `/new` mù hoàn toàn; trần lượt 8/32 quá thấp cho việc nhiều tệp.

- Sổ `<project>/.luas30/ai_task.json` (ghi nguyên tử; JSON hỏng thì coi như rỗng
  nhưng **không xoá tệp**): mục tiêu, bước, ghi chú/quyết định, tệp đã đụng, việc
  kế tiếp, chỗ tắc, và **bằng chứng quan sát được** (tệp đã ghi, lệnh đã chạy kèm
  mã thoát) — ghi tự động, nên sổ vẫn có ích kể cả khi model quên gọi tool.
- Tool `task` (op `status/objective/plan/step/fact/file/next/blocked/unblock/done/reset`);
  `TASK_OPS` là một nguồn, service import lại.
- `<task_memory>` nhồi vào system prompt ở **mọi** lượt (khác `<goal_mode>` chỉ có
  khi bật `/goal`) ⇒ lượt đầu của phiên chat hoàn toàn mới vẫn biết đang dở việc gì.
- `<earlier_work>`: bản tóm tắt phần hội thoại đã ra khỏi cửa sổ — hàm **thuần**,
  không gọi model, không tốn lượt. Cửa sổ gửi nguyên văn 16 → **40** (Goal Mode 60).
- Trần lượt 8/32 → **24/120**. `_nudge_unfinished_work()` nhắc **đúng MỘT lần**
  khi model định dừng bằng văn xuôi trong lúc sổ còn `next`; **không** nhắc ở plan
  mode hoặc Goal Mode (hai vòng lặp giành nhau quyết định dừng).
- Lệnh `/task` (xem sổ) và `/task clear` (xoá sổ).

Tài liệu: [`doc/studio/AI_TASK_MEMORY_1_0_2.md`](../../studio/AI_TASK_MEMORY_1_0_2.md).

## 5. AI Agent gợi ý ý tưởng theo dự án anh em

`studio/app/services/prior_work_service.py`. Yêu cầu người dùng: agent phải
"biết gợi ý trong cuộc trò chuyện như làm game theo phong cách gì" và "xem qua
các project". Vấn đề thật: `project_scope_note` khoá agent trong project đang mở,
nên nó **không tự đọc được** `Documents\LuaS30 Projects\<dự án khác>`. Nên **IDE
quét hộ** rồi nhồi kết quả vào prompt.

- Quét `projects_root()`, rút genre / phong cách / target / số màn / mô-đun từ
  `project.json` + `README.md` + `conf.lua` + khối comment đầu `main.lua`.
  Mỗi dòng giữ lại `evidence` (câu trích + từ khoá khớp) để agent trích dẫn được
  và người đọc kiểm lại được — không phải model đoán.
- ⚠️ **Kỹ thuật tách khỏi phong cách**: gần như dự án nào cũng "procedural", nên
  để chung thì `procedural (14)` luôn đứng đầu bảng phong cách và **che mất tín
  hiệu thật**. Tách thành một dòng "KỸ THUẬT CHUNG" nêu một lần.
- Tool `projects` (`op=list|show|styles`), `PROJECT_OPS` là một nguồn dùng chung.
- `<prior_work>` + khối `SUGGESTIONS` chỉ dựng khi có project đang mở, và có
  **hai bản**: bản đầy đủ cho lượt bàn "làm gì / phong cách gì", bản gọn cho lượt
  sửa lỗi — nếu không thì mỗi lượt vá một dòng cũng phải mang thêm ~1.2k token
  danh mục không liên quan.
- Đệm theo **vân tay nội dung** `(đường dẫn, mtime_ns, size)`; sửa README là danh
  mục tự đổi. ⚠️ Không dùng mtime **thư mục** (NTFS ghi trễ).

Tài liệu: [`doc/studio/AI_IDEA_SUGGEST_1_0_2.md`](../../studio/AI_IDEA_SUGGEST_1_0_2.md)
+ skill [`doc/ai/skills/game-idea-suggest/`](../../ai/skills/game-idea-suggest/SKILL.md).

## 6. Chip tác vụ trên header — hai lỗi "hỏng im lặng"

Do người dùng báo: chip tác vụ (Run/Build) **kẹt vĩnh viễn và nút X thành nút
chết**. Hai nguyên nhân chồng nhau:

1. `LuaRunner._on_build_finished` `return` sớm khi `post_action == "vxpemu"` nên
   **không** phát `finished` → không ai gọi `task_progress.finish()` cho tác vụ Run.
2. Nút X chỉ phát `cancel_requested` → `build_service.cancel()`, mà lúc đó build
   đã xong nên **no-op**.

Nay X **luôn** đóng chip (huỷ trước, rồi ẩn); chip được chốt ở
`_on_vxpemu_stopped` khi phiên giả lập kết thúc; nhãn X đổi thành "Đóng thông báo
tác vụ" khi build đã xong.

Tiếp theo, theo yêu cầu người dùng: **tắt giả lập thì chip phải tắt theo**.
`_on_vxpemu_stopped(0)` nay gọi `dismiss()` thay vì `finish()` — trước đó chip nán
lại **5 giây** với dòng "Đã dừng giả lập", che vùng làm việc. Mã thoát **khác 0**
vẫn hiện (`finish(False, "Giả lập lỗi")`) vì ẩn đi là giấu mất sự cố. Ba đường tắt
giả lập (bấm Dừng, đóng cửa sổ VXPEmu, VXPEmu tự thoát/crash — watcher PID) đều dồn
về một mối.

## 7. Vỏ máy giả lập — mockup "classic dark" + rail icon

`studio/app/widgets/vxp_emu_window.py` viết lại theo mockup người dùng gửi.

- Thân gradient dựng đứng `#2a3343 → #161d28`, bo góc 18, viền `#435069`.
- Hàng trạng thái trong thân vỏ: thanh xanh chỉ **đã nhúng được cửa sổ VXPEmu**,
  dòng dưới là `240×320 · 15 FPS`.
- Màn hình chờ có nội dung **thật**: tên tệp `.vxp` + nhãn trạng thái, đồng hồ và
  ngày thật (cập nhật 20s), `NOKIA 225 DUAL SIM`, dải phím mềm `Menu`/`Chọn`.
- Bàn phím 21 phím hai dòng: số lớn + chữ cái nhỏ (`2`/`abc`), nền `#34445d`,
  viền `#506685`, bo 10, phím OK cao hơn hàng của nó.
- ⚠️ **Chỗ mockup bịa thì thay bằng dữ liệu thật**: app không có nguồn cho
  `4G VoLTE` / `WiFi · 1.0Gbps` / `56 FPS` (đã kiểm: không chỗ nào đo FPS), nên
  chỗ đó hiện tệp đang nạp + PID + **FPS mục tiêu** của `conf.lua`, không bịa số đo.
- ⚠️ `⇧` (U+21E7) **không có trong `segoeui.ttf`** ⇒ vẽ ra ô vuông, im lặng. Đổi
  thành `Aa`. `back`/`clear` dùng **chữ** thay glyph (glyph `back` là mũi tên trái,
  đứng cạnh `left` cũng mũi tên trái thì không phân biệt được). `#` được **làm mờ**
  để thấy ngay nó không gửi được vào VXPEmu.

**Rê chuột lên phím thì hiện TÊN PHÍM** — nhưng không dùng tooltip: tooltip là cửa
sổ của hệ điều hành, trễ ~700ms, có thể bị che, và **không kiểm chứng được
offscreen**. Tên phím được vẽ vào dòng dưới của hàng trạng thái (tên Lua của hợp
đồng phím, thêm chữ nhỏ nếu có: `2 · abc`), lấy từ `PhoneKeypad.MRE_KEY_NAMES` —
cùng nguồn với tooltip nên không thể lệch. Phím đang trỏ sáng lên để biết tên đó
ứng với phím nào.

**Hai chip `MENU`/`Shot` → rail icon bên phải** (theo yêu cầu "chuyển sang phải
như máy ảo LDPlayer 14 chỉ icon khi rê chuột và sẽ hiện title lên"): `ToolRail`
dọc bên phải thân máy, **chỉ icon**, tên công cụ hiện trong **bong bóng** khi rê
chuột. Đủ 7 việc cũ (chạy/dừng, nạp `.vxp`, chụp màn hình, mở thư mục ảnh, quay
video, xoay, toàn màn hình); `RAIL_ITEMS` ↔ `_tool_handlers()` là **một hợp đồng**,
validator canh cả hai chiều.

- **Bỏ hẳn `QMenu`**: `QMenu.exec()` mở vòng lặp sự kiện **lồng nhau** ⇒ validator
  offscreen bấm vào sẽ treo vô hạn, im lặng.
- **Bong bóng là widget tự vẽ (`RailTip`)**, mang `WA_TransparentForMouseEvents` và
  là widget **lá** vì nó vẽ đè lên mép phải thân máy — chỗ có bàn phím cần bấm.
- Icon đổi theo trạng thái thật qua `_sync_rail()` (`play`↔`stop`, `circle`↔`stop`,
  `expand`↔`collapse`, viền `ACCENT` khi công cụ đang bật). Bỏ sót một chỗ gọi là
  rail **nói dối** (vẫn vẽ "play" khi giả lập đang chạy).
- ⚠️ **Một lỗi THẬT, im lặng tuyệt đối**: `ToolRail._on_hover` phát tâm Y của nút
  theo hệ toạ độ **rail**, còn `PhoneStage` đặt bong bóng theo hệ toạ độ **stage**
  ⇒ bong bóng hiện **cao hơn nút ~175 px** mà không có lỗi, không cảnh báo.

Tài liệu: [`doc/studio/EMULATOR_SHELL_FRAME_1_0_2.md`](../../studio/EMULATOR_SHELL_FRAME_1_0_2.md)
— gồm đầy đủ bẫy của chính validator/harness: `grab()` tô vùng trống `#efefef`,
`QMenu.exec()` treo nền offscreen, trộn hai hệ toạ độ ra chiều cao âm, tooltip
không đo được offscreen, thứ tự `Enter`/`Leave` giữa hai widget kề **không được Qt
bảo đảm**, mẫu phá tệp CRLF để lại `\r` gây `IndentationError`.

## 8. Bàn phím MRE trong VXPEmu

Trước đây mỗi nút phát `clicked` → down+up tức thời, nên app **không bao giờ** thấy
trạng thái ĐANG GIỮ — bảng `held` trong `keypad.lua` vô nghĩa và
`engine.keypressed`/`keyreleased` không thành cặp.

- Nay `PhoneKey` phát `key_pressed`/`key_released` riêng; `send_key_down`/`send_key_up`
  ghép cặp (`WM_KEYDOWN`/`WM_KEYUP`); nhả phím khi thả ngoài nút / mất focus / dừng
  giả lập / đóng cửa sổ.
- Bổ sung 2 phím còn thiếu của hợp đồng §0 (`back`, `clear`) — đủ **21/21** nút.
  Bàn phím thật của máy đi cùng bảng phím với VXPEmu
  (`_QT_TO_MRE` ↔ `KeyboardMapping::loadDefaults`), auto-repeat bị bỏ qua đúng như
  VXPEmu.
- ⚠️ **`#` không gửi được vào VXPEmu** — chốt bằng **đo**, không phải suy đoán. Qt
  chỉ ra `Qt::Key_NumberSign` khi Shift **thật** đang giữ; gửi `VK_SHIFT` thay thế
  còn tệ hơn vì `Qt::Key_Shift` nằm trong bảng phím của VXPEmu nên thành một cú
  `softright` giả. Đã thử 5 cách; chỉ `AttachThreadInput` + `SendInput` Shift thật
  chạy được, nhưng **~1/7 lần app nhận `3`** — tức **sai phím mà im lặng** — nên bỏ
  hẳn và chặn tường minh bằng `native_window.MRE_KEYS_NOT_INJECTABLE`. Muốn sửa thì
  phải cho VXPEmu một đường bơm thẳng mã MRE (`dispatchKeyPress`).
- Ghi nhận khi làm E2E: **`print()` của Lua không hiện ở đâu** khi chạy VXPEmu —
  runtime gọi `ls30_log_info` → `_vm_log_info`, mà VXPEmu chỉ export `vm_app_log`,
  nên lời gọi là no-op im lặng. Muốn quan sát phải **vẽ lên framebuffer**. Cũng phát
  hiện VXPEmu vẽ framebuffer 240×320 vào cửa sổ với **scale ≈ 1.25** kèm lệch, nên
  toạ độ pixel không dùng trực tiếp được.

Tài liệu: [`doc/ai/Keypad.md`](../../ai/Keypad.md) §6 "Bấm phím trong emulator".

## 9. Template dự án thứ 7 — Pop Art City 3D

`popart-city-3d` → `templates/PopArtCity3D/` (appid 586534798). Thành phố giả 3D
kiểu GTA phong cách pop-art: raycasting DDA, lái xe giao hàng, radar bắc-up, mức
truy nã, HP. Đăng ký ở cả `PROJECT_TEMPLATE_OPTIONS` (`mediatek_mre_dialog.py`) và
`PROJECT_TEMPLATES` (`project_session.py`).

**"3D" ở đây là pseudo-3D, không phải 3D thật** — và README của template nói thẳng
như vậy. MRE 240×320 không có GPU, không có alpha, không có `pixel`/`vline`/`hline`;
nên renderer vẽ 60 cột × 4 px và **trộn trước** sương mù thành 4 sắc độ rồi chọn
theo khoảng cách. Chính ràng buộc đó tạo ra nét pop-art.

**Bốn lỗi THẬT chỉ chạy thật mới thấy** (đều im lặng qua kiểm tra tĩnh và harness Lua):

1. `main.lua` gọi `P.C.gold` trong khi `gold` chỉ có trong `HUD.C` ⇒ `E.text` nhận
   `nil` ở tham số #4 ⇒ `luaL_checknumber(L,4)` ⇒ `bad argument #4` ⇒ **chết cả màn
   hình hướng dẫn**;
2. 9 dòng chữ tràn ra ngoài framebuffer 240 px (đo được: chân trang tiêu đề vẽ từ
   x = 0 tới 239.2 và vẫn bị cắt hai đầu);
3. nhãn "HP"/"SPD" của HUD đè lên chính thanh của nó;
4. `PrintWindow` thỉnh thoảng trả về **bề mặt cũ** (thanh tiêu đề Qt + ruột đen)
   thay vì framebuffer.

Màu không hiện ra như khai báo: runtime nén qua `LS30_RGB565` (macro **không chuẩn**,
bit 1..0 của kênh G bị bỏ) rồi VXPEmu giải nén bằng phép dịch — E2E chép nguyên công
thức và đọc bảng màu thẳng từ `src/*.lua` thay vì chép tay giá trị hex.

Tài liệu: [`doc/studio/POPART_CITY_3D_1_0_2.md`](../../studio/POPART_CITY_3D_1_0_2.md).

## 10. Hạ tầng build / đóng gói

Ba lỗi im lặng của chính pipeline, đã vá trong bản này:

1. **Hook `[safe-delete]` của host giết build.** `dist/frozen/LuaS30IDE/` là **3022
   tệp**, vượt ngân sách xoá theo lượt (50 mục) ⇒ guard `exit 2` → shim đổi thành
   `SystemExit(1)` ⇒ script **chết với `exit 1` mà không in gì**, trông y như
   "PyInstaller hỏng". Nay scratch PyInstaller nằm trong temp của OS, và bản frozen
   cũ được **đổi tên** `.old-*` (metadata) thay vì xoá.
   ⚠️ `ignore_errors=True` **không** nuốt `SystemExit` — đừng coi nó là lưới an toàn.
2. **`VERSION` bị thư mục frozen ghi đè.** `stage_frozen()` trộn frozen vào GỐC stage
   **sau** khi stage `VERSION`, mà frozen mang `VERSION` cũ của chính nó ⇒ bản cài
   báo số cũ dù build vẫn xanh. Nay `build_frozen.py` chép `VERSION` vào thư mục frozen.
3. **4 lượt tải 404 lãng phí mỗi lần build.** Danh sách ứng viên Python embed lấy từ
   FTP xếp **mới nhất trước**, bản cache 3.12.10 nằm cuối ⇒ luôn thử 4 URL không tồn
   tại trước khi rơi về cache. Nay quét cache trước, sắp theo **số** (`_ver_key`).

Tài liệu: [`packaging/README.md`](../../../packaging/README.md).

## 11. Tài liệu mới trong bản này

- [`doc/studio/AI_GOAL_MODE_1_0_2.md`](../../studio/AI_GOAL_MODE_1_0_2.md)
- [`doc/studio/AI_TASK_MEMORY_1_0_2.md`](../../studio/AI_TASK_MEMORY_1_0_2.md)
- [`doc/studio/AI_IDEA_SUGGEST_1_0_2.md`](../../studio/AI_IDEA_SUGGEST_1_0_2.md)
- [`doc/studio/EMULATOR_SHELL_FRAME_1_0_2.md`](../../studio/EMULATOR_SHELL_FRAME_1_0_2.md)
- [`doc/studio/POPART_CITY_3D_1_0_2.md`](../../studio/POPART_CITY_3D_1_0_2.md)
- [`doc/ai/Keypad.md`](../../ai/Keypad.md) §6 (bấm phím trong emulator)
- [`doc/ai/skills/game-idea-suggest/SKILL.md`](../../ai/skills/game-idea-suggest/SKILL.md)
- [`doc/ai/CACHE_PROMPT.md`](../../ai/CACHE_PROMPT.md) + [`doc/ai/CACHE_SKILL.md`](../../ai/CACHE_SKILL.md)

Kiểm chứng của bản này: [`VALIDATION_STUDIO_1_0_3.md`](../validation/VALIDATION_STUDIO_1_0_3.md).
