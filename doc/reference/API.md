# LuaS30 IDE Lua API

Global table chính:

```lua
engine
```

Alias tương thích:

```lua
mre
```

## Lifecycle

```lua
function engine.load() end
function engine.update(dt) end
function engine.draw() end
function engine.keypressed(key) end
function engine.keyreleased(key) end
function engine.pause() end
function engine.resume() end
function engine.quit() end
```

`dt` được tính từ FPS cấu hình của runtime.

## Graphics

```lua
engine.color(r, g, b) -> rgb565

engine.clear(color)
engine.rect(x, y, w, h, color)
engine.frame(x, y, w, h, color)
engine.line(x1, y1, x2, y2, color)

engine.text(x, y, text, color)
engine.set_font(size)
engine.text_width(text)
engine.font_height()

engine.image(x, y, "assets/image.png")
engine.image_region(
    "assets/atlas.png",
    sx, sy, sw, sh,
    dx, dy
)

engine.flush()
```

`image()` và `image_region()` phụ thuộc `engine.has_images`.

## Input

Key names:

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

Ví dụ:

```lua
local keys = {}

function engine.keypressed(k)
    keys[k] = true
end

function engine.keyreleased(k)
    keys[k] = false
end
```

## Files

```lua
engine.file_exists("save.dat")
engine.file_write("save.dat", data)
engine.file_read("save.dat")
engine.file_delete("save.dat")
```

Kiểm tra trước:

```lua
if engine.has_files then
    -- use save system
end
```

## Audio

```lua
engine.audio_play("assets/sfx/select.mp3")
engine.audio_stop()
engine.audio_set_volume(0) -- 0..6
engine.audio_is_playing()
```

Kiểm tra:

```lua
if engine.has_audio then
    engine.audio_play("assets/sfx/select.mp3")
end
```

Firmware/codec support có thể khác theo thiết bị.

## System

```lua
engine.tick_ms()
engine.log("message")
engine.exit()

engine.W
engine.H
engine.version

engine.has_audio
engine.has_files
engine.has_images
```

## Device/capabilities

```lua
local caps = engine.capabilities()

local d = engine.device_info()
print(d.family)
print(d.width)
print(d.height)
print(d.preferred_fps)
print(d.recommended_ram_kb)
print(d.capabilities)
```

## Modules

LuaS30 có `require()` resource-based:

```lua
local Player = require("src.player")
```

Runtime ưu tiên:

```text
src/player.lub
```

sau đó fallback:

```text
src/player.lua
```

Điều này cho phép development mode pack raw Lua mà không cần host `luac`.

## Lua compatibility

Code target nên tương thích **Lua 5.1**.

Tránh dùng syntax/API chỉ có ở Lua 5.2/5.3/5.4 nếu chưa được implement riêng.

## Performance guidelines

Cho S30+ cấu hình thấp:

- tránh tạo table mỗi frame;
- cache colors;
- cache text/static data;
- dùng atlas;
- giới hạn image cache;
- chỉ render object trong camera;
- tránh animation/particle nặng;
- save dạng delta thay vì serialize world lớn;
- 10–15 FPS ổn định thường hữu ích hơn FPS cao nhưng giật.


## Runtime compatibility 1.8.2

```lua
local compat = engine.runtime_compat()

if not compat.compatible then
    -- The core runtime should not normally reach Lua in this state.
end

print(compat.level)               -- "full" / "degraded" / "incompatible"
print(compat.native_capabilities)
print(compat.capabilities)
print(compat.alias_count)
print(compat.fallback_mask)
print(compat.missing_required)

if compat.fallbacks.rename_copy_delete then
    print("rename is emulated by copy/delete")
end
```

Additional flags:

```lua
engine.has_touch
engine.has_rename
engine.has_removable
engine.has_log
engine.runtime_compatible
```

Use capability flags rather than assuming every MRE firmware exports every optional API.
