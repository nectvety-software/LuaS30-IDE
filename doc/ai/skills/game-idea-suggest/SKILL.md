---
name: game-idea-suggest
description: Gợi ý trong hội thoại nên làm game gì / theo phong cách nào — dựa trên <prior_work> (danh mục dự án cũ của người dùng) + ràng buộc 240x320 MRE, rồi biến lựa chọn thành kế hoạch thật
---

# Gợi ý ý tưởng game — có căn cứ, không chung chung

Dùng skill này khi người dùng **đang cân nhắc làm gì**, ví dụ:

- "làm game gì bây giờ", "gợi ý ý tưởng đi", "nên làm cái gì"
- "làm game theo phong cách gì", "art style nào hợp"
- mở project trống / project mới rồi hỏi bắt đầu từ đâu
- khen/chê một hướng đi và muốn phương án khác

**Không** dùng khi người dùng đã nói rõ cần gì (sửa lỗi, thêm màn hình, build...).
Lúc đó cứ làm việc — đừng chen ý tưởng vào.

## 1. Bằng chứng nằm ở đâu

`<prior_work>` trong system prompt là danh mục các dự án LuaS30 **khác** của
người dùng, do IDE quét hộ từ `Documents\LuaS30 Projects`.

> ⚠️ Bạn **KHÔNG** đọc trực tiếp được thư mục đó: mọi đường dẫn của tool
> `read`/`grep`/`glob` đều bị khoá trong project đang mở. Đừng thử `read`
> `../mini-farm/main.lua` — nó sẽ bị từ chối. Dùng đúng hai nguồn dưới đây.

| Cần gì | Lấy ở đâu |
|---|---|
| Toàn bộ danh mục | `{"tool":"projects","args":{"op":"list"}}` |
| Chi tiết một dự án | `{"tool":"projects","args":{"op":"show","name":"BusJam"}}` |
| Chỉ gu tổng hợp | `{"tool":"projects","args":{"op":"styles"}}` |

Ở lượt bình thường `<prior_work>` chỉ có bản gọn (gu + câu chỉ đường). **Khi
người dùng hỏi nên làm gì thì PHẢI gọi `projects` op=list trước khi trả lời.**
Gợi ý mà chưa đọc danh mục là gợi ý bịa.

## 2. Đọc danh mục cho đúng

Danh mục đã tách sẵn ba thứ — đừng lẫn chúng:

- **genre** — thể loại, suy từ từ khoá trong README/main.lua (kèm dòng `genre
  "..." — từ khoá khớp: "..."` để bạn biết vì sao).
- **phong cách** — pop-art / notebook-doodle / comic-noir / pixel-art.
- **KỸ THUẬT CHUNG** — gần như mọi dự án đều vẽ procedural
  (`engine.rect/line/text`, không bitmap). Đây là **cách làm**, không phải
  phong cách. Đừng đề xuất "phong cách procedural" như thể là một lựa chọn mỹ thuật.

Vài dự án có tên trùng nhau vì chúng là **bản sao template chưa sửa** (ví dụ ba
dự án cùng tên "Doodle Quest"). Thấy vậy thì đừng tính chúng là ba lần chọn
phong cách — nói thẳng ra cũng được, người dùng biết chuyện đó.

Các con số trong skill này (bao nhiêu dự án, phong cách nào nhiều nhất) có thể
đã cũ. **Tin danh mục sống, không tin đoạn văn này.**

## 3. Trần ràng buộc — mọi ý tưởng phải lọt qua

Đây là máy Nokia S30+ / MediaTek MRE, không phải điện thoại cảm ứng:

| Hạng mục | Giá trị |
|---|---|
| Màn hình | 240×320, dọc |
| Nhịp | 10–15 FPS |
| Nhập liệu | **chỉ bàn phím cứng**: D-Pad, 2/4/6/8, OK/5, softkey trái/phải, `*`, `#`, `0` |
| Ngôn ngữ | Lua 5.1 (không `//`, không bitwise, không `goto`) |
| Heap | `project.json → ram_kb` (768–1024 KB) cho **cả** VM + code + dữ liệu |
| Đồ họa | `engine.*` procedural; bitmap lớn là bẫy bộ nhớ |

⇒ **Loại thẳng** những ý cần: con trỏ/chuột/chạm, kéo-thả, nhập chữ tự do nhiều,
xoay ảnh góc bất kỳ, atlas sprite lớn, particle dày, nhiều thực thể cùng lúc,
bảng dữ liệu dựng mỗi frame.

⇒ **Hợp gu máy này**: một tay cầm điều khiển, vòng lặp ngắn (5–30 giây), trạng
thái vẽ lại từ code, màn hình tĩnh + vài phần tử động, số màn hữu hạn.

## 4. Cách trình bày một gợi ý

1. **Nói quan sát trước.** Một câu, dựa trên danh mục thật:
   > "Trong 18 dự án, phong cách bạn quay lại nhiều nhất là notebook-doodle
   > (11 dự án), sau đó pop-art (5). Genre thì trải từ cardgame tới
   > first-person-shooter, nhưng chưa có dự án nào thuần quản lý theo lượt."

2. **Đưa 2–3 phương án CỤ THỂ**, mỗi phương án một khối ngắn:
   - **Thể loại + phong cách** (gọi tên phong cách có thật trong danh mục)
   - **Vòng lặp cốt lõi** trong MỘT câu — người chơi làm gì, lặp lại thế nào
   - **Điều khiển** bằng phím nào (chỉ phím có thật)
   - **Gần với dự án nào của bạn** — và nói rõ nó *khác* ở đâu
   - **Vì sao hợp máy này** — một câu, chỉ vào ràng buộc thật

   Ba phương án nên khác nhau về **độ mới**, không phải ba biến thể của một ý:
   một cái an toàn (nối tiếp thứ đã làm tốt), một cái lai (ghép hai hướng cũ),
   một cái mới (genre chưa đụng tới).

3. **Hỏi chọn cái nào**, rồi dừng. Đừng tự bắt tay vào code khi chưa được chọn.

### Ví dụ một phương án viết đúng

> **Bus Line Manager — notebook-doodle + quản lý theo lượt**
> Vòng lặp: mỗi lượt bạn xếp 3 chuyến xe vào 4 bến; khách lên đúng tuyến thì ăn
> điểm, sai tuyến thì trễ và mất mạng. Hết lượt mới biết lãi lỗ.
> Phím: 2/4/6/8 chọn bến, 5 xác nhận chuyến, LSK mở sổ.
> Gần với `BusJam` của bạn, nhưng BusJam là giải đố thời gian thực — bản này
> **theo lượt**, nên không cần 15 FPS ổn định và dễ chơi trên máy chậm.
> Hợp máy này vì chỉ vẽ một bàn 4 bến tĩnh + vài con số; không có gì động mỗi frame.

### Viết sai (đừng làm thế)

> "Bạn có thể làm platformer, puzzle, hoặc RPG. Platformer thì vui, puzzle thì
> dễ làm, RPG thì sâu."

Không có dự án nào được nhắc, không có phím, không có vòng lặp, không có ràng
buộc — đây là văn mẫu, không phải gợi ý.

## 5. Từ gợi ý thành việc thật

Khi người dùng đã chọn:

1. Ghi lại lựa chọn trước khi code, bằng tool `task`:
   `{"tool":"task","args":{"op":"objective","text":"Làm <tên game>: <thể loại>,
   <phong cách>; xong khi /run mở được menu và vào màn chơi"}}`
   rồi `op=plan` với 3–8 bước kiểm chứng được.
2. Nạp `s30plus-ui-design` nếu phải dựng màn hình/nút.
3. Nạp `keypad` **trước khi viết một dòng xử lý phím nào** — tên phím sai thì
   game chết lặng, không báo lỗi.
4. Giữ phong cách đã chọn nhất quán suốt dự án; đổi phong cách giữa đường thì
   nói rõ với người dùng.
5. Xong một mốc thì `/run` để chứng minh nó chạy, đừng chỉ mô tả.

## 6. Giới hạn phải nói thật

- Danh mục chỉ đọc được **metadata** (`project.json`, `README`, `conf.lua`,
  header `main.lua`) — bạn **không** thấy code bên trong dự án cũ. Đừng nói
  "tôi đã xem cách bạn cài đặt X trong BusJam" khi thực tế chỉ thấy mô tả.
- Danh mục rỗng (thư mục đổi chỗ, ổ đĩa khác) là chuyện có thể xảy ra. Lúc đó
  nói thẳng là chưa có dữ liệu và hỏi người dùng thích gì — **đừng bịa ra dự án**.
