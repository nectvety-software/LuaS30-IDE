# SKILLS.md — Bloom Pocket / LuaS30 Agent Skills

## Tổng quan

File này định nghĩa các kỹ năng mà AI coding agent cần dùng khi làm việc với Bloom Pocket.

Mỗi kỹ năng gồm:

```text
Purpose
Inputs
Steps
Checks
Output
```

---

# Skill 01 — Inspect LuaS30 project

## Purpose

Đọc và hiểu cấu trúc dự án trước khi sửa.

## Inputs

```text
project.json
conf.lua
main.lua
src/
assets/
```

## Steps

1. Đọc `project.json`.
2. Xác nhận resolution.
3. Xác nhận FPS.
4. Xác nhận RAM.
5. Đọc `main.lua`.
6. Liệt kê states.
7. Đọc module trong `src/`.
8. Kiểm tra asset trong `assets/`.
9. Xác định Full/Lite renderer.

## Checks

```text
Lua 5.1 compatible
240×320
mre-s30plus
engine API
```

## Output

Tóm tắt:

```text
current architecture
current states
current controls
current renderer
risk areas
```

---

# Skill 02 — Build LuaS30 VXP

## Purpose

Build project bằng LuaS30-IDE.

## Command

```bat
D:\MRE\LuaS30-IDE\build.bat "<project>"
```

Hoặc:

```bat
D:\MRE\LuaS30-IDE\build_only.bat "<project>"
```

## Checks

Kiểm tra:

```text
Lua syntax
asset pack
ELF output
VXP output
build log
```

## Failure handling

Nếu build lỗi:

1. lấy dòng lỗi đầu tiên có ý nghĩa;
2. xác định file;
3. sửa root cause;
4. build lại;
5. không sửa hàng loạt khi chưa biết lỗi.

---

# Skill 03 — Lua 5.1 compatibility

## Purpose

Đảm bảo code chạy đúng runtime LuaS30.

## Rules

Không dùng:

```lua
goto
table.unpack
utf8
bit32
_ENV
```

nếu runtime chưa cung cấp.

Ưu tiên:

```lua
unpack
pairs
ipairs
string.sub
math.floor
```

Không dùng syntax Lua 5.2+.

---

# Skill 04 — LuaS30 graphics

## Purpose

Vẽ bằng API engine.

## APIs

```lua
E.clear()
E.rect()
E.frame()
E.line()
E.text()
E.image()
E.image_region()
```

## Rules

Cache color:

```lua
local RED = E.color(...)
```

Không gọi `E.color()` liên tục mỗi frame.

Kiểm tra:

```lua
E.has_images
```

trước khi phụ thuộc PNG.

---

# Skill 05 — Pixel-art integration

## Purpose

Tích hợp sprite/tile mới vào game.

## Steps

1. kiểm tra size;
2. kiểm tra alpha;
3. crop padding;
4. scale pixel-perfect;
5. thêm vào atlas nếu phù hợp;
6. map coordinates;
7. code `image_region`;
8. test Full;
9. test Lite fallback.

## Checks

Không có:

```text
black rectangle
white halo
wrong crop
wrong baseline
```

---

# Skill 06 — Build sprite atlas

## Purpose

Giảm file count và RAM overhead.

## Atlas rules

Khuyến nghị:

```text
16×16
24×24
32×32
```

Các frame cùng animation nên cùng cell size.

Ví dụ:

```text
mimo_atlas.png
192×32
6 frames × 32×32
```

Render:

```lua
E.image_region(
    "assets/mimo_atlas.png",
    frame * 32,
    0,
    32,
    32,
    x,
    y
)
```

---

# Skill 07 — Animation

## Purpose

Animation nhẹ.

## Pattern

```lua
local frame = math.floor(E.tick_ms() / 180) % frame_count
```

## Rules

Không tạo timer object riêng nếu không cần.

Không dùng animation > 8 frame cho sprite nhỏ nếu không có lý do.

---

# Skill 08 — Tilemap renderer

## Purpose

Render map lớn hiệu quả.

## Map representation

```lua
local map = {
    {1,1,1,1},
    {1,2,2,1},
    {1,2,3,1},
}
```

## Render

Chỉ vẽ tile trong viewport.

Pseudo:

```lua
local x0 = math.floor(camera.x / TILE)
local y0 = math.floor(camera.y / TILE)
local x1 = x0 + visible_cols
local y1 = y0 + visible_rows
```

Không vẽ tile ngoài camera.

---

# Skill 09 — Camera

## Purpose

Camera theo player.

## Pattern

```lua
camera.x = player.x - W / 2
camera.y = player.y - H / 2
```

Clamp:

```text
0 .. map_width - screen_width
0 .. map_height - screen_height
```

Có thể dùng easing nhẹ nhưng không cần float phức tạp.

---

# Skill 10 — Collision

## Purpose

Ngăn player xuyên vật thể.

## Preferred

```text
AABB
tile collision
```

Tile flags:

```lua
COLLISION[id] = true
```

Test X và Y riêng để giảm lỗi kẹt góc.

---

# Skill 11 — Depth sorting

## Purpose

Player đi sau/trước object hợp lý.

## Key

```lua
sortY = y + height
```

Nếu object ít:

```lua
table.sort(drawables, function(a,b)
    return a.sortY < b.sortY
end)
```

Nếu object nhiều:

- sort static once;
- chỉ merge dynamic object;
- không sort world lớn mỗi frame.

---

# Skill 12 — Player movement

## Purpose

Điều khiển keypad mượt.

## Input aliases

```text
up / 2
down / 8
left / 4
right / 6
ok / 5
```

## Rules

Dùng state held cho movement.

Action một lần phải dùng fresh press.

---

# Skill 13 — Menu navigation

## Purpose

Menu ổn định trên keypad.

## Expected

```text
Up/Down = select
OK/5 = confirm
SoftRight/Back = back
```

Selection luôn wrap hoặc clamp nhất quán.

Không tạo menu cần mouse.

---

# Skill 14 — State machine

## Purpose

Quản lý screen rõ ràng.

## Suggested modules

```text
src/states/menu.lua
src/states/play.lua
src/states/settings.lua
```

Nếu chưa tách module:

```lua
state = "menu"
```

vẫn phải giữ transition rõ.

Không gọi state change ở nhiều nơi không kiểm soát.

---

# Skill 15 — Localization

## Purpose

Thêm ngôn ngữ mà không duplicate renderer.

## Pattern

```lua
LANG.en = {}
LANG.vi = {}
```

Truy cập:

```lua
T().play
```

Không hard-code text gameplay nếu có localization key tương ứng.

---

# Skill 16 — Save system

## Purpose

Lưu progress an toàn.

## APIs

```lua
E.file_exists()
E.file_read()
E.file_write()
E.file_delete()
```

## Rules

Trước khi dùng:

```lua
if E.has_files then
```

Không save mỗi frame.

Có default nếu file lỗi.

---

# Skill 17 — Full/Lite graphics

## Purpose

Giữ game chạy trên thiết bị yếu.

## Full

```text
PNG assets
sprite animation
decorative props
more foliage
```

## Lite

```text
primitive art
fewer props
fewer effects
no decorative particles
```

Gameplay data phải giống nhau.

---

# Skill 18 — UI layout 240×320

## Purpose

Không chồng chữ.

## Safe layout

```text
top HUD: 0–30
content: 31–300
softkey: 302–319
```

## Minimums

```text
margin 4–6 px
button height 24–34 px
text spacing 12–16 px
```

Luôn test English và Vietnamese.

---

# Skill 19 — About screen compliance

## Required text

```text
© VXPstore. All rights reserved.
Website: qeafivels.com
```

Không thay đổi hoặc xóa nếu user không yêu cầu.

---

# Skill 20 — Audio

## Purpose

Thêm SFX an toàn.

## Guard

```lua
if E.has_audio then
    E.audio_play(...)
end
```

## Recommended sounds

```text
menu select
bloom
collect
water
gate open
win
```

Không để audio failure gây crash.

---

# Skill 21 — Performance profiling

## Purpose

Tìm bottleneck.

## Measure

```text
FPS
frame time
RAM
asset load
number of draw calls
```

## Suspects

```text
too many image_region
too many particles
sorting every frame
string concat every frame
large backgrounds
duplicate textures
```

Ưu tiên giảm draw call trước khi tăng FPS config.

---

# Skill 22 — RAM optimization

## Purpose

Giữ memory thấp.

## Methods

- atlas;
- tile reuse;
- smaller textures;
- no duplicate PNG;
- release unused references;
- Lite mode;
- avoid giant map table if unnecessary.

Không tăng `ram_kb` chỉ để che vấn đề nếu có thể tối ưu.

---

# Skill 23 — Missing asset fallback

## Purpose

Không black screen.

## Pattern

```lua
if E.has_images then
    -- detailed renderer
else
    -- primitive renderer
end
```

Nếu một asset cụ thể lỗi:

- log;
- dùng primitive placeholder;
- tiếp tục game.

---

# Skill 24 — Safe interaction system

## Purpose

Quản lý OK/5 interaction.

## Pattern

Mỗi object có:

```lua
type
x
y
radius
active
```

Tìm nearest interactable.

Không loop hàng trăm object nếu chỉ có vài object gần player.

Có thể spatial partition sau.

---

# Skill 25 — Bloom interaction

## Purpose

Core interaction.

## Logic

```text
find nearest sleeping sprout
distance check
mark grown
reward petals
save
play effect
check zone completion
```

Không cho bloom cùng object nhiều lần.

---

# Skill 26 — Quest system

## Purpose

Quest nhẹ.

## Recommended

```lua
quest = {
    id = "restore_garden",
    progress = 0,
    target = 6,
    complete = false
}
```

Không làm quest graph phức tạp trong giai đoạn đầu.

---

# Skill 27 — Multi-zone world

## Purpose

Mở rộng game.

## Zone example

```text
Garden Gate
Petal Courtyard
Water Terrace
Cloud Orchard
Moon Garden
```

Mỗi zone có:

```text
map
spawn
objects
music
exit portals
```

Chuyển zone phải cleanup asset/object tạm.

---

# Skill 28 — Portal / gate

## Purpose

Chuyển map.

## Trigger

```text
player enters portal rectangle
```

## Steps

1. save current zone;
2. set target zone;
3. load map;
4. set spawn;
5. reset camera;
6. fade optional.

---

# Skill 29 — NPC

## Purpose

NPC nhẹ.

## NPC fields

```lua
x
y
dir
sprite
dialog_id
state
```

AI đơn giản:

```text
idle
wander
talk
```

Không cần pathfinding phức tạp ban đầu.

---

# Skill 30 — Particle effects

## Purpose

Hiệu ứng bloom đẹp nhưng nhẹ.

## Limit

```text
8–20 particles
```

Mỗi particle:

```lua
x
y
vx
vy
life
```

Reuse table nếu có thể.

Lite mode có thể tắt.

---

# Skill 31 — Water animation

## Purpose

Tạo nước sống động.

Không dùng shader.

Dùng:

- 2–3 tile frame;
- alternate highlight;
- slow animation.

Frame interval:

```text
300–600 ms
```

---

# Skill 32 — Screen transition

## Purpose

Chuyển cảnh mềm.

Ưu tiên:

```text
simple fade
wipe
slide 4–8 frames
```

Lite mode có thể bỏ transition.

Không dùng full-screen alpha nhiều lớp kéo dài.

---

# Skill 33 — Emulator regression test

## Purpose

Không regress.

## Minimum matrix

```text
Splash
Menu
Play
Language
Guide
About
Settings
Pause
Win
Exit
```

Input:

```text
D-Pad
2/4/6/8
OK/5
SoftLeft
SoftRight
Back
```

---

# Skill 34 — 10-minute stability test

## Purpose

Bắt leak và crash.

## Scenario

```text
2 min menu transitions
5 min gameplay movement
1 min pause/resume
1 min settings
1 min gameplay return
```

Quan sát:

```text
FPS degradation
RAM increase
stutter
sprite corruption
black screen
```

---

# Skill 35 — Screenshot QA

## Purpose

Kiểm tra đồ họa.

Chụp:

```text
splash
menu
gameplay
language
settings
pause
win
```

Kiểm tra:

```text
text overlap
wrong crop
black background
alpha halo
misaligned button
off-screen UI
```

---

# Skill 36 — Refactor main.lua

## Purpose

Giữ code maintainable.

Refactor khi:

```text
main.lua > 500–700 lines
```

Suggested:

```text
src/game.lua
src/input.lua
src/save.lua
src/world.lua
src/map.lua
src/collision.lua
src/camera.lua
src/ui.lua
src/art.lua
src/i18n.lua
```

Không refactor toàn bộ cùng lúc nếu đang sửa bug nhỏ.

---

# Skill 37 — Build-safe changes

## Purpose

Giảm regression.

## Process

```text
read
change
syntax check
build
run
test
compare
```

Không sửa nhiều subsystem cùng lúc nếu không cần.

---

# Skill 38 — Asset naming

## Purpose

Giữ project sạch.

## Convention

```text
snake_case.png
```

Examples:

```text
tree_pink_large.png
bush_mint_01.png
bridge_wood.png
mimo_walk.png
```

Không dùng:

```text
final2_new_new.png
asset(1).png
image123.png
```

---

# Skill 39 — Versioning

## Purpose

Theo dõi build.

Format:

```text
MAJOR.MINOR.PATCH
```

Ví dụ:

```text
0.2.0
0.2.1
0.3.0
```

Patch:

```text
bugfix
```

Minor:

```text
new feature
```

Major:

```text
large gameplay/runtime change
```

Cập nhật đồng bộ:

```text
project.json
README
About
release package
```

---

# Skill 40 — Release packaging

## Purpose

Tạo package sạch.

Package nên chứa:

```text
project source
assets
README
PROMPT.md
SKILLS.md
build helper
```

Không nên chứa:

```text
temporary files
editor cache
logs
crash dumps
duplicate previews
```

Tên:

```text
BloomPocket_LuaS30_vX.Y.Z.zip
```

---

# Skill 41 — Report changes

## Purpose

Báo cáo chính xác sau khi làm.

Format:

```text
Changed:
- ...

Tested:
- ...

Not tested:
- ...

Artifacts:
- ...
```

Không tuyên bố đã chạy emulator/thiết bị nếu chưa chạy.

---

# Skill 42 — Next-task selection

Nếu không có task cụ thể, ưu tiên theo thứ tự:

```text
1. gameplay correctness
2. crash fix
3. graphics corruption
4. input bug
5. performance
6. map expansion
7. cosmetic polish
```

Không ưu tiên hiệu ứng đẹp hơn nếu game đang crash.
