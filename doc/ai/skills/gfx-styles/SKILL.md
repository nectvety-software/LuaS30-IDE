---
name: gfx-styles
description: Style do hoa game LuaS30 (8-bit, 2D, 2.5D isometric, 3D gia lap raycaster/Mode7): ky thuat ve tren RGB565 240x320, ngan sach perf 15fps, palette, parallax, billboard, lay asset tu VPEPixel va nhac tu sfx skill
---

# Style đồ họa cho LuaS30 (240x320 · RGB565 · 1 MB · 15 FPS)

Dùng skill này khi chọn/chuyển style hình cho game. Máy thật không có GPU:
mọi hiệu ứng đều là thủ thuật vẽ khôn ngoan + ngân sách chặt. Asset lấy từ
skill `vpe-assets` (thư viện mẫu `.vpe`/`.vpea` của VPEPixel), nhạc/SFX từ
skill `sfx`, input từ skill
`keypad`, vòng game từ skill `gameplay`.

## 0. Luật chung mọi style

- Vẽ bằng `rect/text/image_region`, chốt `flush()` 1 lần/frame.
- Cache mọi `engine.color()` dùng lại; không convert màu trong loop.
- Nền xa vẽ trước, gần vẽ sau; chỉ vẽ vật trong camera.
- Text 8px cho HUD, dự phòng khi thiếu ảnh (game không được đen nếu atlas lỗi).

## 1. 8-bit (pixel art + chiptune)

- Atlas pixel 1x, bảng màu gọn ~16 màu, font bitmap 8px, dither thủ công cho
  gradient (chấm xen kẽ, không blur).
- Sprite nhỏ (8x8–32x32), tile 16x16, colorkey `0xF81F` (magenta) cho nền
  trong suốt PNG.
- Nhạc: xem skill `sfx` — ưu tiên square/noise ngắn, loop đơn giản.

## 2. 2D (sprite + tilemap + parallax)

- Tilemap mảng 1 chiều, tile 16x16, atlas chung như skill `gameplay` §pool.
- Parallax tối đa 2 lớp xa (cuộn `x*0.3`, `x*0.6`) + 1 lớp chơi; lớp xa vẽ
  bằng `rect` dải màu thay vì ảnh khi RAM căng.
- Hiệu ứng: chớp trắng khi trúng đòn (vẽ đè `rect` 3 frame), rung màn hình
  ±2px, hạt từ pool (tối đa 20).

## 3. 2.5D (nghiêng/isometric trên nền 2D)

- Góc nghiêng cố định: world `(x, y, h)` → màn hình `(sx = x - y, sy =
  (x + y) / 2 - h)`. Số nguyên hết (tránh float mỗi tile).
- Isometric tile 2:1 (32x16); sắp xếp vẽ theo `y` tăng dần (vật dưới đè vật
  trên); bóng đổ = ellipse `rect` dẹt dưới chân.
- Độ cao `h` chỉ đổi `sy` (nhảy), không scale sprite trừ object bay quan
  trọng (scale bậc thang 1x/2x bằng `image_region` khung khác nhau).

## 4. 3D giả lập (raycaster / đường đua Mode7)

Máy không gánh 3D thật — chỉ 2 kỹ thuật này, ở độ phân giải thấp rồi phóng:

- **Raycaster** (mê cung/FPS): buffer logic 60x80 tia, mỗi cột 1 `rect`
  dọc cao tỉ lệ nghịch khoảng cách, 2-3 sắc độ tường theo hướng; sprite
  (quái/vật phẩm) billboard bằng `image_region` scale theo khoảng cách,
  vẽ từ xa tới gần. Tường 60 cột × fill dọc = đủ 15 FPS.
- **Đường đua Mode7** (xe): đường gồm đoạn cong, mỗi hàng scanline nội suy
  độ rộng + offset theo phối cảnh, lề cỏ 2 màu xen kẽ, xe người chơi là
  sprite cố định cuối màn + nghiêng khi cua. Vật ven đường billboard thưa.
- Cấm: loop pixel Lua full 240x320 mỗi frame (chết FPS), texture mapping
  thật, float dày đặc — tiền tính bảng `sin/cos/dist` một lần lúc load.

## 5. Chọn style theo game

```text
puzzle/menu/casual -> 8-bit hoặc 2D phẳng
platformer/runner/shooter -> 2D + parallax
RPG/tactics -> 2.5D isometric
mê cung/FPS/đua xe -> 3D giả lập (raycaster/Mode7)
máy yếu không rõ -> 2D (luôn chạy được)
```

Đổi style giữa chừng = vẽ lại asset theo atlas mới, không trộn 2 pipeline
vẽ trong một game.

## Definition of done

- Đúng style đã chọn ở mọi màn hình (splash/menu/play/over đồng bộ).
- 15 FPS ổn định trên profile RAM thiết bị; không OOM sau 5 phút.
- Asset từ `vpe-assets`, nhạc từ `sfx`, build VXP PASS + nhìn thật trên emulator.
