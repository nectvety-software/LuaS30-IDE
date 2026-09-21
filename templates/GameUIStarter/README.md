# Game UI Starter

Mẫu game nhẹ cho LuaS30 IDE / MediaTek MRE, ưu tiên màn hình 240×320 và thiết bị RAM thấp.

## Có sẵn

- Splash screen dạng đồ họa procedural, không cần asset ngoài.
- Main Menu: Play, How To Play, Settings, About, Exit.
- HUD trong game: HP, score và mục tiêu thu thập.
- Pause menu và Game Over / Mission Complete.
- Điều khiển keypad Nokia/S30+: 2/4/6/8, 5 và 0.
- Theme riêng trong `src/theme.lua`.
- UI component nhẹ trong `src/ui.lua`.
- Gameplay demo trong `src/game.lua`.
- Không dùng ảnh nền lớn nên phù hợp MRE/MTK6260 và dễ thay bằng asset của game thật.

## Cấu trúc

```text
GameUIStarter/
├── main.lua
├── conf.lua
├── project.json
├── src/
│   ├── game.lua
│   ├── theme.lua
│   └── ui.lua
└── .luas30/
    └── ui_design.json
```

## Điều khiển

| Phím | Chức năng |
| --- | --- |
| 2 / ↑ | Lên |
| 8 / ↓ | Xuống |
| 4 / ← | Trái |
| 6 / → | Phải |
| 5 / OK | Chọn |
| 0 / Back | Quay lại / Pause |

## Tùy biến nhanh

1. Đổi palette trong `src/theme.lua`.
2. Đổi tên game và menu trong `main.lua`.
3. Thay gameplay demo ở `src/game.lua`.
4. Giữ các hàm UI trong `src/ui.lua` để tái sử dụng cho nhiều màn hình.
5. Có thể thêm sprite/audio vào `assets/` sau mà không phải đổi kiến trúc state/menu.

Mẫu mặc định dùng đồ họa hình học để chạy ngay sau khi tạo project.
