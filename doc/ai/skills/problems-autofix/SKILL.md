---
name: problems-autofix
description: Đọc bảng PROBLEMS của IDE bằng tool "problems", phân tích nguyên nhân từng lỗi Lua, sửa thẳng vào dự án bằng luas30-edit (chế độ Edit automatically áp mã tự động), lặp lại đến khi bảng sạch lỗi rồi build xác nhận
---

# PROBLEMS → phân tích → tự sửa

Dùng skill này khi người dùng yêu cầu "sửa lỗi", "fix PROBLEMS", hoặc khi
bạn vừa áp dụng code và muốn tự kiểm chứng không còn chẩn đoán treo.

## Vòng lặp chuẩn (Cline-style, mỗi bước một lượt)

1. **Đọc lỗi**: `{"tool":"problems","args":{"op":"list"},"reason":"..."}`
   — kết quả là bảng PROBLEMS thật của IDE: severity, đường dẫn tương đối,
   dòng:cột, thông điệp, kèm snippet code quanh dòng lỗi.
2. **Nhóm theo tệp**: nhiều lỗi cùng một tệp thường chung nguyên nhân
   (thiếu `end`, khai báo sai, gọi hàm engine không tồn tại).
3. **Đọc ngữ cảnh**: dùng `read` cho cả tệp nếu snippet chưa đủ kết luận.
   Nghi ngờ API engine → grep `runtime_bridge.c` với `args.scope="engine"`
   (xem skill `engine-api-check`) trước khi đổi tên hàm.
4. **Sửa bằng `luas30-edit`**: mỗi lỗi một edit tối thiểu, đường dẫn tương
   đối dự án. Ở chế độ mặc định **Edit automatically**, IDE áp mã thẳng vào
   tệp (có backup trong `.luas30/ai-backups`) rồi tự tiếp tục lượt cho bạn —
   đừng chờ người dùng bấm Apply.
5. **Kiểm tra lại**: gọi `problems` (op `list` hoặc `count`) SAU khi sửa để
   xác nhận lỗi biến mất. Mã vừa áp có thể chưa được lint lại — nếu bảng
   vẫn liệt kê lỗi cũ ở đúng dòng đã sửa, dùng `read` đọc tệp để kiểm tra
   trạng thái thật thay vì tin bảng mù quáng.
6. **Kết thúc**: khi `count` về 0, chạy build thật theo skill
   `vxp-build-run` để có bằng chứng cuối cùng.

## Lưu ý về nguồn dữ liệu

- Bảng PROBLEMS do editor lint theo tệp đang mở — nó chỉ chứa tệp được
  phân tích GẦN NHẤT, tối đa 15 dòng hiển thị (`count` báo tổng thật).
- Người dùng yêu cầu quét CẢ DỰ ÁN mà bảng rỗng → đừng báo "không có lỗi";
  hãy `glob **/*.lua` rồi `read`/build từng tệp, hoặc mở tệp nghi ngờ.
- Severity: ERROR phải sửa; WARNING chỉ sửa khi liên quan yêu cầu hiện tại.

## Khi kẹt

- Sửa 2 lần mà lỗi y nguyên → DỪNG vòng lặp sửa mù: `read` toàn bộ hàm
  chứa lỗi, truy nguyên nhân gốc (thường ở dòng TRƯỚC dòng báo lỗi trong
  Lua — `end` thiếu, dấu `,` thừa), rồi sửa một lần dứt điểm.
- Lỗi sinh ra DO bản sửa trước → hoàn tác ý định đó (`luas30-edit` ngược)
  rồi chọn cách sửa khác; đừng chồng thêm bản sửa.
- Kết thúc: tóm tắt tắt — đã sửa tệp nào, còn warning nào để lại và vì sao.
