# Quick Start

## 1. Yêu cầu desktop

Khuyến nghị Windows 10/11 và Python 3.10+.

Engine đã bundle ARM GCC và emulator workflow. Studio chỉ cần Python + PySide6.

## 2. Mở engine

```bat
run.bat
```

Launcher:

- tạo `%APPDATA%\LuaS30IDE\venv` nếu chưa có;
- kiểm tra version dependency;
- không gọi mạng nếu dependency đã phù hợp;
- validate Native SDK/runtime/Studio;
- kiểm tra ARM GCC;
- kiểm tra emulator;
- mở Studio.

Không có mạng:

```bat
run.bat --offline
```

## 3. Tạo project

```bat
new_project.bat HelloS30
```

Kết quả:

```text
Documents\LuaS30IDE\HelloS30\
```

Hoặc dùng **File → New Project**.

## 4. File chính

`project.json`:

```json
{
  "name": "HelloS30",
  "vendor": "LuaS30",
  "appid": 262567,
  "ram_kb": 1024,
  "screen_width": 240,
  "screen_height": 320,
  "fps": 15,
  "target_profile": "generic-vxp-qvga"
}
```

`conf.lua`:

```lua
config = {
    name = "HelloS30",
    screen_width = 240,
    screen_height = 320,
    fps = 15
}
return config
```

`main.lua`:

```lua
local E = engine
local white = E.color(255,255,255)
local bg = E.color(20,45,35)

function E.draw()
    E.clear(bg)
    E.text(8,8,"Hello S30+",white)
end

function E.keypressed(key)
    if key == "0" then
        E.exit()
    end
end
```

## 5. Build

```bat
build_only.bat "%USERPROFILE%\Documents\LuaS30IDE\HelloS30"
```

Hoặc build + emulator:

```bat
build.bat "%USERPROFILE%\Documents\LuaS30IDE\HelloS30"
```

## 6. Output

Build output nằm trong:

```text
HelloS30\build\
```

Thông thường gồm ARM ELF/AXF, ELF report, VXP, SHA-256 và metadata build tùy mode.

## 7. Test thiết bị chưa biết

Dùng template:

```text
templates\device_probe\
```

Build probe trước game lớn để kiểm tra:

- runtime khởi động;
- graphics;
- keypad;
- timer;
- capability file/audio/image;
- resolution.

## 8. Tiếp theo

- Lua API: `doc/reference/API.md`
- Build: `doc/build/BUILD_VXP.md`
- Device: `doc/platform/DEVICE_COMPATIBILITY.md`
