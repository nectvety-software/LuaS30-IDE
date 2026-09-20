# PROMPT.md — Chống lỗi "not enough memory" cho dự án LuaS30 / MRE

> Dùng như prompt hệ thống khi nhờ AI viết / sửa / tối ưu một dự án game LuaS30 (MediaTek MRE,
> Nokia S30+). Bản này đúc từ lần tối ưu game **Biển Mực (Chetaslua)** và các con số đo thật
> trên runtime của IDE (`tools/lua_preview.py`, Lua 5.1 + lupa).
>
> **Vị trí**: `D:\MRE\LuaS30-IDE\doc\ai\MEMORY_PROMPT.md` — bổ sung, **không** thay thế
> `doc/ai/PROMPT.md` và `doc/ai/SKILL.md` của IDE (hai file đó nói chung về quy trình, file này
> chỉ nói về bộ nhớ). Đọc kèm `MEMORY_SKILLS.md`. Cập nhật: 09/2026 theo số đo của dự án Chetaslua.

---

## 0. Điều kiện nền (phải đọc trước khi viết một dòng code)

| Hạng mục | Giá trị |
|---|---|
| Ngôn ngữ | Lua 5.1 (firmware là Lua 5.1.5 biên dịch sẵn trong app) |
| Heap Lua | `project.json → ram_kb` (thường 1024 KB). Đây là **tổng** cho Lua VM + code + dữ liệu |
| Màn hình | 240×320, nhịp 15 FPS |
| API bộ nhớ | **Không có.** Đã tìm trong `sdk/luas30/include`: không có hàm báo heap trống |
| Tín hiệu duy nhất | `collectgarbage("count")` — chính là con số firmware dùng để báo `not enough memory` |
| Khi lỗi xảy ra | Firmware **tắt app ngay**, không có cơ hội `pcall` |

Vì không có API bộ nhớ, mọi dự án **bắt buộc** có một mô-đun giám sát + tự hạ chất lượng
(`src/mem.lua` trong dự án mẫu).

---

## 1. Quy tắc bất biến (vi phạm = lỗi phải sửa, không thoả hiệp)

1. **Không tạo table trong hàm vẽ/`update`.** Một table literal tốn 112–256 byte rác; ở 15 FPS
   GC phải chạy liên tục. Dời mọi bảng điểm/hình dạng ra hằng số mô-đun.
2. **Không ghép chuỗi trong hàm vẽ.** Xem quy tắc 3 và mục SKILLS "đệm chuỗi".
3. **Mọi đệm phải (a) có trần, và (b) chịu được chuỗi DÀI.** Lua 5.1 chỉ *intern* chuỗi ≤ 40 ký
   tự; chuỗi dài ghép mỗi khung là đối tượng mới nên đệm kiểu `cache[s] = v` sẽ đầy rồi bị xoá
   liên tục → vừa tốn RAM vừa không có tác dụng. Dùng `memo_new/memo_get/memo_put` (mục SKILLS 3).
4. **Dữ liệu nặng phải sinh ngay khi dùng, không sinh sẵn lúc nạp**: bảng glyph, bảng bỏ dấu,
   bảng chữ HOA, gói ngôn ngữ không dấu…
5. **Nạp màn hình theo nhu cầu và trả lại bytecode khi máy chặt.** Bytecode là phần GC không dọn
   được (dự án mẫu: ~300 KB cho 14 file). Không có cách nào rẻ hơn để lấy lại vài chục KB.
6. **Không bật `--lua-protection bytecode`** với `luac` của máy tính: header Lua 5.1 ghi
   `sizeof(size_t)`, 64-bit trên PC (8) khác ARM 32-bit của máy (4) → firmware báo `bad bytecode`.
   Chỉ dùng bytecode nếu có `luac` 32-bit cùng `luaconf.h` với runtime.
7. **Mọi API tuỳ chọn phải được kiểm tra kiểu trước khi gọi** (`type(engine.xxx) == "function"`,
   hoặc `userdata`/`table` với firmware bọc lại). `pcall` chỉ dùng ở ranh giới API
   (file, âm thanh, ảnh), **không** nuốt lỗi logic game.
8. **Điểm an toàn để dọn rác**: đổi màn hình, đổi đợt sóng, chấm điểm cuối trận. **Không** dọn
   rác giữa lúc đang chơi (gây giật) và **không** xoá đệm vẽ chữ giữa trận (sẽ phải nan lại).
9. **Chuỗi đã ghép để hiển thị phải nhớ lại kèm khoá là số liệu VÀ ngôn ngữ.** Đổi số liệu hoặc
   đổi ngôn ngữ mà không ghép lại = hiện sai/hiện tiếng cũ (lỗi thật đã gặp ở màn Cài đặt).
10. **Không đóng gói file tạm.** `tools/build.py` bỏ qua `build/ release/ saves/ tests/ backups/
    .git/ .luas30` nhưng **KHÔNG** bỏ qua `.freebuff` → đừng để `.lua`/`.png` sinh ra trong
    `.freebuff`; cho tool ghi vào `build/`.

---

## 2. Ngân sách phải giữ (tham chiếu từ dự án mẫu, heap 1024 KB)

| Chỉ số | Ngưỡng |
|---|---|
| Heap sau khi nạp các mô-đun lõi + màn hình đầu | ≤ 250 KB |
| Heap khi đang chơi (đỉnh, có boss) | ≤ 430 KB và ≤ 45% heap máy |
| Rác mỗi khung ở trạng thái ổn định | ≤ 32 byte/khung (màn menu thường 0–2 B) |
| Phí "khởi động" khi vào một màn hình (nan glyph + nạp đệm) | ≤ 15 KB, chỉ trả một lần |
| 5 vòng menu → trận → boss → menu: bộ nhớ sau khi dọn rác | tăng < 12 KB (tốt nhất ≈ 0) |
| Số lệnh vẽ 1 khung | ≤ 1500 (đo bằng `Sim.canvas.draws`) |
| Trần cache | tổng ≤ 64 mục/cache; xoá sạch khi đầy |

---

## 3. Thang hạ chất lượng (bắt buộc có, không được crash)

`Mem.level` 0→4, ngưỡng tính theo **bội số của mốc nền đo trên chính máy đó** (mốc nền = heap
ngay sau khi nạp xong) và có **trần tuyệt đối 80% heap máy**:

| Mức | Kích hoạt | Hậu quả cho phép |
|---|---|---|
| 0 | quanh mốc nền | không đổi |
| 1 | > 1.30 × nền | bớt tô gạch/đổ bóng, tắt trang trí không cần |
| 2 | > 1.55 × nền, hoặc nền đã > 44% heap | bớt dòng kẻ vở/mưa/mây, hiệu ứng 14→8, **trả bytecode màn không dùng** |
| 3 | > 1.85 × nền | tắt mưa/mây/sét, vật thể 9→6, bỏ loại địch nặng, **tắt nhạc nền** |
| 4 | > 2.20 × nền hoặc > 80% heap | tối thiểu hoá trang trí |

Có trễ (hysteresis) khi nâng lại chất lượng. Người chơi phải **nhìn thấy được** mức tiết kiệm
(hiện ở màn Cài đặt) để còn báo lỗi kèm số liệu.

---

## 4. Quy trình bắt buộc (không được nhảy bước)

1. **Đo trước khi sửa**: rác/khung từng màn, heap sau khi nạp, đỉnh khi chơi, bytecode vs bảng dữ liệu.
2. Sửa **từng nhóm** nguyên nhân, sau mỗi nhóm chạy lại **toàn bộ** tool kiểm tra.
3. Đo lại và ghi số vào báo cáo; nếu số không giảm thì **hoàn tác** thay đổi đó.
4. Chạy test OOM 5 vòng + mô phỏng máy heap nhỏ (ép `Mem.budget = 512`) để chắc game tự hạ cấp.
5. Đóng gói VXP và chạy bản Lua **đã nén** trong gói.
6. Trả báo cáo bộ nhớ kèm danh sách thay đổi.

---

## 5. Tiêu chí nghiệm thu

- [ ] Không còn màn hình nào tạo > 32 byte rác/khung ở trạng thái ổn định.
- [ ] Heap sau 5 vòng menu→trận→boss→menu không tăng dần (không rò rỉ).
- [ ] Đỉnh bộ nhớ khi chơi ≤ 45% heap cấu hình.
- [ ] Máy heap nhỏ (512 KB) **tự hạ cấp** thay vì hết bộ nhớ.
- [ ] Không tạo table/chuỗi trong hàm vẽ; mọi đệm có trần và chống được chuỗi dài.
- [ ] Bytecode màn hình không dùng được trả lại khi máy chặt.
- [ ] Mọi API tuỳ chọn đều được kiểm tra kiểu; `pcall` chỉ ở ranh giới API.
- [ ] Cả 3 ngôn ngữ (kể cả bản không dấu) chạy trên mọi màn hình, không sót dấu, không sót chữ cũ.
- [ ] Gói VXP không chứa file tạm; bản Lua đã nén trong gói chạy đúng.
- [ ] Có báo cáo bộ nhớ kèm số đo trước/sau.

---

## 6. Bảng chống chỉ định (đã từng gây lỗi thật)

| Viết thế này | Hỏng thế nào | Viết thế này thay thế |
|---|---|---|
| `local pts = {...}` trong hàm vẽ | ~200 B rác/khung | hằng số mô-đun, hoặc một bảng nháp dùng lại |
| `cache[s] = v` với `s` ghép mỗi khung | đệm đầy → xoá liên tục → 237–265 B rác/khung | `memo_new/memo_get/memo_put` (vòng 8 mục so nội dung) |
| `require` tất cả màn hình ở `load()` | ~300 KB bytecode nằm mãi trong heap | nạp khi vào màn, trả khi máy chặt |
| Nan sẵn cả bộ glyph / cả gói ngôn ngữ | 64 KB + 32 KB ngay lúc nạp | sinh ngay khi dùng |
| Bảng nhẩm hiển thị không khoá theo ngôn ngữ | hiện tiếng Việt khi đang ở tiếng Anh | khoá = (số liệu, `S.cfg.lang`) |
| Dùng `luac` trên PC để tạo `.lub` | `bad bytecode` trên máy | giữ `.lua` + minify của IDE |
| Vòng lặp khung do Python điều khiển khi đo | sai số ~170 B/khung | chạy vòng lặp **trong Lua**, Python chỉ đọc kết quả |
| Kiểm tra hiệu năng/độ rò bằng mắt | bỏ sót rò rỉ | luôn có tool đo tự động + test OOM 5 vòng |

---

## 7. Bốn câu hỏi phải trả lời trong báo cáo cuối

1. Bộ nhớ đi đâu? (bytecode bao nhiêu KB, bảng dữ liệu bao nhiêu KB, theo từng file)
2. Rác mỗi khung từng màn là bao nhiêu, sau khi sửa còn bao nhiêu?
3. Nếu máy chỉ có 512 KB thì game làm gì? (mức nào bật, màn nào bị trả khỏi bộ nhớ, tính năng nào tắt)
4. Bằng chứng đóng gói: dung lượng VXP, SHA-256, số file trong gói, bản Lua đã nén chạy thế nào?

Chi tiết kỹ thuật và mã mẫu: **SKILLS.md** cùng thư mục.
