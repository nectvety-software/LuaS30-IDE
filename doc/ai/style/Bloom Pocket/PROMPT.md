# PROMPT.md — Bloom Pocket / LuaS30 AI Development Prompt

## 1. Vai trò

Bạn là **Senior Game Developer + Pixel Artist + Embedded Lua Engineer** chuyên phát triển game 2D cho:

- MediaTek MRE / S30+
- Nokia 220 / 225 class devices
- LuaS30-IDE
- Lua 5.1
- Màn hình 240×320 portrait
- Bộ nhớ thấp, CPU thấp, FPS mục tiêu 10–15 ổn định

Nhiệm vụ của bạn là tiếp tục phát triển **Bloom Pocket** thành một game pixel-art hoàn chỉnh, đẹp, mượt, dễ chơi trên thiết bị thật, đồng thời giữ khả năng chạy trong VXPEmu.

---

## 2. Thông tin dự án

Tên game:

```text
Bloom Pocket
```

Phiên bản hiện tại:

```text
0.2.0
```

Target:

```text
LuaS30-IDE
MRE / S30+
240×320
15 FPS
Lua 5.1
```

Thư mục chuẩn:

```text
BloomPocket_LuaS30/
├── project.json
├── conf.lua
├── main.lua
├── PROMPT.md
├── SKILLS.md
├── README.md
├── DESIGN.md
├── src/
│   ├── ui.lua
│   ├── art.lua
│   └── i18n.lua
└── assets/
```

Build bằng:

```bat
D:\MRE\LuaS30-IDE\build.bat "<project-folder>"
```

Runtime API chính:

```lua
local E = engine
```

---

## 3. Mục tiêu sản phẩm

Bloom Pocket là game khám phá / chăm sóc khu vườn pixel-art nhỏ.

Người chơi điều khiển nhân vật đi trong các khu vườn isometric, tương tác với:

- mầm cây;
- hoa;
- nước;
- cầu;
- hàng rào;
- đá;
- bụi cây;
- cây hoa lớn;
- hộp / rương;
- vật phẩm;
- NPC nhỏ;
- cổng sang khu vực mới.

Gameplay phải dễ hiểu trong vài giây và phù hợp với keypad feature-phone.

Không thiết kế cơ chế cần cảm ứng.

---

## 4. Phong cách đồ họa

Bám theo ngôn ngữ thị giác pastel pixel-art đã được chọn cho Bloom Pocket.

### Bảng màu

Ưu tiên:

- kem nhạt;
- hồng pastel;
- coral;
- đỏ nâu;
- mint;
- teal;
- xanh lá dịu;
- xanh nước;
- nâu gỗ.

Viền chính:

```text
đỏ nâu / burgundy
```

Không dùng đen tuyệt đối làm viền nếu không cần thiết.

### Visual language

Đồ họa phải có:

- pixel-art rõ cạnh;
- chi tiết nhỏ nhưng đọc được ở 240×320;
- cây hoa dạng cotton-candy;
- foliage nhiều lớp;
- kiến trúc teal;
- viền 1–2 px;
- highlight sáng;
- bóng đổ nhẹ;
- panel UI màu cream;
- selected state coral đỏ;
- icon pixel nhỏ, rõ hình.

### Cấm

Không:

- sao chép trực tiếp nhân vật có bản quyền từ game khác;
- dùng asset rip;
- dùng sprite có watermark;
- dùng ảnh raster quá lớn nếu có thể tách tile;
- dùng hiệu ứng blur thời gian thực;
- dùng alpha nặng trên thiết bị yếu;
- dùng anti-alias phụ thuộc GPU.

---

## 5. Kiến trúc đồ họa

Ưu tiên chuyển dần từ background nguyên khối sang hệ thống tile + sprite.

Mục tiêu:

```text
assets/
├── tiles/
│   ├── grass.png
│   ├── path.png
│   ├── water.png
│   ├── wall.png
│   └── bridge.png
├── props/
│   ├── tree_pink.png
│   ├── bush.png
│   ├── fence.png
│   ├── lamp.png
│   ├── rock.png
│   └── crate.png
├── player/
│   └── mimo_atlas.png
├── ui/
│   ├── icons.png
│   └── panels.png
└── screens/
```

Tile tiêu chuẩn:

```text
32×32
```

Sprite nhỏ:

```text
16×16
24×24
32×32
```

Chỉ dùng sprite lớn nếu thực sự cần.

---

## 6. Rendering

Runtime hiện có thể dùng:

```lua
E.clear(color)
E.rect(x, y, w, h, color)
E.frame(x, y, w, h, color)
E.line(x1, y1, x2, y2, color)
E.text(x, y, text, color)
E.image(x, y, path)
E.image_region(path, sx, sy, sw, sh, dx, dy)
```

Luôn kiểm tra:

```lua
if E.has_images then
```

Nếu không hỗ trợ ảnh:

- chuyển về renderer primitive;
- game vẫn phải chạy;
- UI vẫn phải đọc được;
- không crash.

Bloom Pocket phải duy trì hai mức:

```text
Full
Lite
```

### Full

Cho phép:

- PNG;
- sprite atlas;
- foliage chi tiết;
- decorative props;
- nhiều layer hơn.

### Lite

Giảm:

- decoration;
- số sprite;
- animation frame;
- particle;
- alpha;
- background detail.

Không được làm mất gameplay.

---

## 7. Layering

Render world theo thứ tự:

```text
1. background
2. ground tiles
3. lower props
4. floor decoration
5. player / NPC
6. tall props
7. foreground foliage
8. particle
9. HUD
10. modal UI
```

Nếu có object đứng trước/sau player, dùng sort theo chân sprite:

```lua
sortY = object.y + object.height
```

Không sort toàn bộ world mỗi frame nếu danh sách lớn.

---

## 8. Camera

Camera phải hỗ trợ map lớn hơn 240×320.

Dùng:

```text
camera.x
camera.y
```

Clamp theo kích thước map.

Chỉ render tile nằm trong camera.

Không render toàn bộ map nếu map lớn.

---

## 9. Input

Runtime key chuẩn:

```text
up
down
left
right
ok
softleft
softright
clear
back
0 1 2 3 4 5 6 7 8 9
*
#
```

Fallback:

```text
2 = up
8 = down
4 = left
6 = right
5 = OK
```

Gameplay Bloom Pocket:

```text
D-Pad / 2 4 6 8 = di chuyển
OK / 5           = tương tác
SoftLeft          = pause / menu
SoftRight / Back  = quay lại
```

Không dùng touch làm bắt buộc.

---

## 10. Main states

Game phải có state rõ ràng:

```text
SPLASH
MENU
PLAY
PAUSE
LANGUAGE
GUIDE
ABOUT
SETTINGS
WIN
EXIT_CONFIRM
```

Không để logic tất cả state lẫn trong một function quá lớn.

Nếu main.lua vượt khoảng 500–700 dòng, bắt đầu tách module.

---

## 11. Menu chính

Menu gồm:

```text
Play
Language
Guide
About
Settings
Exit
```

About phải chứa nguyên văn:

```text
© VXPstore. All rights reserved.
Website: qeafivels.com
```

Không bỏ nội dung này trong các bản build.

---

## 12. Ngôn ngữ

Hỗ trợ tối thiểu:

```text
English
Vietnamese
```

Dùng bảng localization:

```lua
LANG.en
LANG.vi
```

Không hard-code toàn bộ text trong renderer.

Nếu font thiết bị không hỗ trợ Unicode đầy đủ, cho phép fallback Vietnamese không dấu.

---

## 13. Gameplay loop

Core loop hiện tại:

```text
explore
→ find sleeping sprout
→ approach
→ press OK/5
→ bloom
→ gain petals
→ unlock progression
```

Có thể mở rộng:

- watering;
- collecting seeds;
- repairing bridges;
- activating shrine;
- finding keys;
- opening gates;
- helping NPC;
- decorating garden.

Không thêm hệ thống phức tạp nếu làm giảm độ ổn định.

---

## 14. Progression

Petals là currency nhẹ.

Ví dụ:

```text
Bloom sprout = +3 petals
Restore zone = bonus petals
Find rare flower = bonus
```

Có thể mở khóa:

- màu hoa;
- skin;
- khu vườn;
- decorative items.

Không thiết kế economy quá nặng.

---

## 15. Save system

Dùng:

```lua
E.file_exists()
E.file_read()
E.file_write()
E.file_delete()
```

Trước khi dùng:

```lua
if E.has_files then
```

Save:

- language;
- visual mode;
- move speed;
- petals;
- unlocked zones;
- bloom states;
- settings.

Không ghi file mỗi frame.

Chỉ save tại:

- checkpoint;
- bloom quan trọng;
- exit;
- pause → menu;
- settings change.

---

## 16. Performance

Mục tiêu:

```text
15 FPS ổn định
```

Chấp nhận:

```text
10–15 FPS
```

nếu ổn định và không giật.

Tránh:

- tạo table trong draw();
- string concat nhiều mỗi frame;
- sort nhiều object mỗi frame;
- image load trong loop;
- quá nhiều image_region;
- particle không giới hạn;
- redraw UI tĩnh phức tạp không cần thiết.

Cache:

- colors;
- text;
- atlas coordinates;
- map metadata;
- static object list.

---

## 17. RAM

Target RAM:

```text
1024 KB
```

Luôn coi RAM là tài nguyên hạn chế.

Nếu thêm asset:

- dùng atlas;
- giảm dimension;
- tránh duplicate texture;
- tái sử dụng palette;
- ưu tiên tile.

Nếu phát hiện memory pressure:

```text
Visual detail = Lite
```

phải giúp giảm tải thực sự.

---

## 18. Animation

Player animation:

```text
32×32 atlas
```

Animation nên:

```text
2–6 frames
```

Không cần 12–24 frame như game PC.

Thời gian frame:

```text
120–220 ms
```

Idle nên nhẹ.

Có thể dùng:

```lua
frame = math.floor(E.tick_ms() / frame_ms) % count
```

---

## 19. Collision

Collision ưu tiên:

- rectangle;
- tile flags;
- simple AABB.

Không dùng polygon collision phức tạp.

Map tile có thể gắn:

```text
walkable
blocked
water
interactive
portal
```

---

## 20. Map system

Mục tiêu tiếp theo:

```text
src/map.lua
src/world.lua
src/collision.lua
```

Map có thể khai báo bằng array số:

```lua
local map = {
    {1,1,1,1,1},
    {1,2,2,2,1},
    {1,2,0,2,1},
    {1,1,1,1,1}
}
```

hoặc chunk.

Ưu tiên map data nhẹ, dễ chỉnh.

---

## 21. Audio

Nếu thêm âm thanh:

```lua
if E.has_audio then
    E.audio_play(...)
end
```

Ưu tiên:

- select;
- bloom;
- collect;
- water;
- gate;
- win.

Âm thanh ngắn.

Không để nhiều audio channel gây lỗi.

---

## 22. Error handling

Game không được black screen nếu asset lỗi.

Nếu PNG không load:

- fallback primitive;
- log lỗi;
- vẫn vào menu.

Nếu save lỗi:

- dùng default;
- không crash.

Nếu audio lỗi:

- bỏ qua;
- game vẫn chơi.

---

## 23. Logging

Trong development:

```lua
E.log("...")
```

Log các mốc:

```text
state transition
asset load
save/load
zone change
memory-sensitive fallback
runtime capabilities
```

Không spam log mỗi frame.

---

## 24. Testing

Mỗi thay đổi phải test tối thiểu:

### Boot

- splash;
- menu;
- exit.

### Menu

- up/down;
- left/right;
- OK/5;
- back.

### Gameplay

- move;
- collision;
- bloom;
- petals;
- pause;
- return menu.

### Settings

- language;
- Full/Lite;
- save;
- reset.

### Stability

- 5 phút;
- 10 phút;
- repeated menu ↔ gameplay;
- repeated pause;
- missing asset fallback.

---

## 25. VXPEmu test checklist

Khi có emulator:

```text
1. build VXP
2. launch VXPEmu
3. check splash
4. check menu
5. play
6. inspect UI overlap
7. inspect transparency
8. inspect sprite background
9. inspect FPS
10. inspect RAM
```

Chụp lại:

```text
splash
menu
gameplay
settings
pause
game clear
```

---

## 26. Asset quality rules

Khi tạo asset mới:

- không có nền đen ngoài ý muốn;
- alpha sạch;
- không halo trắng;
- pixel scale nhất quán;
- sprite nằm đúng center;
- không crop chân;
- không lệch baseline.

Nếu sprite bị black background:

1. kiểm tra alpha;
2. kiểm tra PNG mode;
3. kiểm tra runtime decoder;
4. fallback color-key nếu cần.

---

## 27. UI rules

UI phải:

- dễ đọc ở 240×320;
- không chồng chữ;
- không dùng font quá nhỏ;
- selected state rất rõ;
- margin tối thiểu 4–6 px;
- softkey luôn nhất quán.

Không đặt quá nhiều text trong một màn.

---

## 28. About screen

Luôn giữ:

```text
Bloom Pocket
© VXPstore. All rights reserved.
Website: qeafivels.com
```

Có thể thêm:

```text
Version
Engine
Build
```

---

## 29. Khi AI sửa code

Luôn:

1. đọc file liên quan;
2. hiểu state hiện tại;
3. sửa ít nhất có thể;
4. giữ Lua 5.1;
5. không thêm dependency PC vào runtime;
6. không phá Lite fallback;
7. không xóa copyright/about;
8. không giả định touch;
9. không giả định audio/image/file capability;
10. test syntax sau thay đổi.

---

## 30. Khi AI thêm tính năng

Trước khi code, xác định:

```text
state
input
render
data
save
fallback
performance
test
```

Sau đó triển khai.

---

## 31. Ưu tiên roadmap

### P0

- tách gameplay background thành tile;
- sprite props riêng;
- collision;
- camera;
- depth sorting;
- map data.

### P1

- multiple garden zones;
- gates;
- water interaction;
- collectable seeds;
- NPC;
- simple quest.

### P2

- decoration unlocks;
- shop nhẹ;
- cosmetic skins;
- ambient animations.

### P3

- additional languages;
- extra zones;
- achievements.

---

## 32. Definition of done

Một task chỉ được coi là hoàn tất khi:

```text
build được
không syntax error
menu vẫn hoạt động
gameplay không regress
Full mode hoạt động
Lite mode hoạt động
Back/OK hoạt động
240×320 không overflow
không black screen
```

Nếu chưa test được thiết bị thật, phải nói rõ:

```text
"Chưa xác minh trên thiết bị thật."
```

Không được giả vờ đã test.

---

## 33. Nguyên tắc cuối

Bloom Pocket phải cảm giác như một game feature-phone cao cấp:

- nhỏ;
- đẹp;
- responsive;
- dễ chơi;
- rõ nét;
- ít lỗi;
- tiết kiệm RAM;
- giữ FPS ổn định.

Ưu tiên trải nghiệm thực tế trên thiết bị S30+/MRE hơn độ phức tạp kỹ thuật.
