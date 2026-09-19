---
name: s30plus-ui-design
description: Thiết kế màn hình 240x320 Nokia S30+ qua tool ui_design/asset và dùng ui_design.lua trong game (hit-test, vẽ lại mỗi frame)
---

# UI 240×320 cho S30+ (tool ui_design + asset)

Dùng skill này khi tạo/sửa màn hình, nút, label, sprite cho dự án.

## Hợp đồng màn hình

- Khung vật lý 240×320; lưới 4px — toạ độ nên là bội số 4.
- Mọi thành phần PHẢI nằm trọn trong khung; tool tự kẹp (clamp) nhưng đừng
  lợi dụng — thiết kế ngoài rìa sẽ bị cắt khó thấy.
- `engine` chỉ vẽ hình chữ nhật trục-thẳng: xoay chỉ có ý nghĩa 90/270
  (hoán đổi rộng/cao); góc khác bị bỏ qua.

## Vận hành tool ui_design

1. Đọc hiện trạng trước khi ghi: `{"op":"screens"}` rồi `{"op":"get","screen":"main"}`.
2. Ghi thiết kế: `add_screen` / `add_item` (type + name + x,y,w,h + text) /
   `update_item` (args.name + args.fields) / `remove_item` / `rename_screen`.
3. ID thành phần là định danh Lua: `[A-Za-z_][A-Za-z0-9_]*`, duy nhất trong
   màn hình — nó thành khoá `name` trong scene và `ui.<id>` khi export.
4. SAU MỖI LẦN ghi: chạy `{"op":"export"}` để sinh `ui_design.lua`, và đừng
   tuyên bố đã lưu trước khi tool báo thành công.

## Vận hành tool asset

- `{"op":"make","kind":"button|panel|solid|gradient|checker|grid|frame|bar|label","name":...,"width":...,"height":...,"color":"#rrggbb",...}`
  sinh PNG thật vào `assets/...` của dự án — ảnh quá khổ sẽ bị thu về ≤240×320.
- Kiểm tra trước bằng `{"op":"list"}` để khỏi trùng tên.

## Dùng trong game (ui_design.lua)

```lua
local ui = require("ui_design")
function engine.draw() ui.draw("main") end
local item  = ui.get("main", "btn_start")   -- tra cứu theo ID
local top   = ui.hit("main", touch_x, touch_y)  -- thành phần trên cùng dưới chạm
```

- Màn hình khởi động luôn là `main`.
- Cảm ứng: xử lý qua `ui.hit`, đừng tự so sánh toạ độ thủ công.
