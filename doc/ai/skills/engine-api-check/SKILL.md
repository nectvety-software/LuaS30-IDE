---
name: engine-api-check
description: Kiểm chứng hàm engine.* có thật cho Nokia S30+ MRE/VXP trước khi sửa code chạm API — chống bịa hàm love2d/mobile-Lua
---

# Kiểm chứng API engine trước khi sửa code

Dùng skill này TRƯỚC KHI viết hoặc sửa bất kỳ dòng nào gọi `engine.*`,
`gfx.*`, `ui.*` của runtime, hoặc thêm tài nguyên vào `conf.lua`.

## Quy trình

1. Tìm chỗ đăng ký hàm thật — mọi hàm `engine.*` nằm trong mảng
   `luaL_Reg funcs[]` do `luas30_bridge_open` nạp (tên global `engine`,
   alias cũ `mre`):
   - tool `grep`, args `{"pattern":"luaL_Reg|l_[a-z_]+,","scope":"engine","path":"engine/src","include":"**/*.c"}`
     để định vị — tệp chủ chốt là `engine/src/runtime_bridge.c`.
   - tool `read` với `scope:"engine"` đọc nguyên mảng funcs[]; mọi hàm KHÔNG
     xuất hiện trong mảng là hàm KHÔNG TỒN TẠI.
2. Xem wrapper Lua mỏng mà dự án thật sự gọi:
   `read {"path":"templates/basic/src/engine.lua","scope":"engine"}` —
   wrapper có thể đổi tên/bọc tham số; lấy tên theo wrapper làm chuẩn.
3. Đối chiếu ký hiệu nền khi nếu cần ABI:
   `read {"path":"sdk/luas30/abi/symbols.json","scope":"engine"}`.
4. Chỉ sau 3 bước trên mới phát `luas30-edit`. Trong lý do sửa, trích đúng
   dòng đăng ký đã thấy (tệp + số dòng).

## Ranh giới bắt buộc

- Màn hình logic 240×320; không có phép xoay bitmap tuỳ ý, chỉ 90/270 hoán
  rộng/cao (xem skill `s30plus-ui-design`).
- Không giả định API của love2d/Corona/Android (`graphics.*`, `display.newText`
  v.v.) — phải thấy hàm trong bảng đăng ký C hoặc wrapper engine.lua.
- Font: chỉ cỡ hệ thống mà `conf.lua`/engine khai báo; kiểm chứng bằng
  `grep {"pattern":"set_font|font","scope":"engine","path":"engine/src"}`.

## Chống chỉ định

- Đừng sửa code engine-facing chỉ dựa trên `<relevant_sources>` trong ngữ cảnh
  — ngữ cảnh có thể cắt bớt; đọc tệp thật bằng scope=engine.
- Đừng nhân bản một hàm "quen thuộc" (`graphics.drawLine`) rồi đổi tên engine;
  tên hàm phải lấy từ kết quả grep/read thật.
