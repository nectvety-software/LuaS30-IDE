# Bắt đầu

> **Ngôn ngữ:** Tiếng Việt · [English](../en/Getting-Started.md)

## 1. Yêu cầu

| Thành phần | Yêu cầu |
|---|---|
| Hệ điều hành | Windows 10/11 |
| Python | 3.10 trở lên |
| PySide6 | `PySide6>=6.7,<7` — launcher tự cài vào venv riêng |
| ARM GCC | đã bundle sẵn trong `toolchain/arm-gcc/` |
| Emulator | đã bundle sẵn trong `emulator/` |

Bạn **không** cần cài ARM toolchain hay emulator thủ công, và **không** cần cài
PySide6 toàn cục — launcher tạo một virtual environment riêng.

## 2. Mở Studio

```bat
run.bat
```

Các chế độ của launcher:

```bat
run.bat --offline      dùng cache, không gọi mạng
run.bat --online       cho phép kiểm tra/cập nhật dependency
run.bat --deps-only    chỉ cài dependency rồi thoát
run.bat --force-deps   cài lại dependency bất kể version
```

Trước khi mở Studio, launcher sẽ:

1. tạo `%APPDATA%\LuaS30IDE\venv` nếu chưa có;
2. kiểm tra version dependency (chỉ cài khi không thỏa);
3. không gọi mạng nếu dependency đã phù hợp;
4. validate Native SDK / runtime / Studio;
5. kiểm tra ARM GCC và emulator;
6. mở Studio.

### Thư mục dữ liệu người dùng

```text
%APPDATA%\LuaS30IDE\
├── config\      studio.ini, workspace_session.json, ai_*.json
├── logs\        launcher.log, environment.json
├── cache\
├── temp\
├── backups\
└── venv\        Python virtual environment
```

Engine cài đặt tách khỏi dữ liệu người dùng, nên thư mục engine gần như chỉ đọc
trong lúc dùng bình thường. Có thể override bằng biến môi trường
`LUAS30_APPDATA`, `LUAS30_DOCUMENTS`, `LUAS30_PROJECTS` (dùng cho môi trường
portable hoặc test).

## 3. Tạo project

```bat
new_project.bat HelloS30
```

Hoặc trong Studio: **File → New Project**.

Trong Studio, **New Project** mở hộp thoại **Cấu hình MediaTek MRE SDK** trước,
để chọn metadata đóng gói:

```text
APPNAME / APPVER / VENDOR
Resolution
MediaTek chipset
Heap RAM
```

Preset chipset có sẵn:

| Preset | Thiết bị tiêu biểu |
|---|---|
| `MTK6260` | Nokia 220, Nokia 225 |
| `MTK6261` | Nokia 3310 3G, Nokia 216 |
| `MTK6250` | Q-Mobile, K-Touch |
| `MTK6225` | Legacy MRE 2.0 |

Chọn `MTK6260` sẽ ghi profile tương thích `nokia225-rm1011`. Mọi project mới đều
nhận **AppID mới**; hộp thoại ghi cấu hình vào cả `project.json` và
`.luas30/mre_sdk.json`.

Project được tạo tại:

```text
Documents\LuaS30IDE\<ProjectName>\
```

Studio tự resolve thư mục Documents thật của Windows, nên Documents bị redirect
vẫn hoạt động.

## 4. Các file chính

```text
HelloS30/
├── project.json     metadata build (name, appid, RAM, độ phân giải, FPS, profile)
├── conf.lua         cấu hình runtime
├── main.lua         entry script
├── src/             module Lua dùng require()
└── assets/          ảnh, âm thanh, resource
```

`main.lua` tối thiểu:

```lua
local E = engine
local white = E.color(255, 255, 255)
local bg = E.color(20, 45, 35)

function E.draw()
    E.clear(bg)
    E.text(8, 8, "Hello S30+", white)
end

function E.keypressed(key)
    if key == "0" then E.exit() end
end
```

Chi tiết đầy đủ ở [Cấu trúc project](Project-Structure.md) và
[`doc/reference/API.md`](../../doc/reference/API.md).

## 5. Build

Chỉ build:

```bat
build_only.bat "%USERPROFILE%\Documents\LuaS30IDE\HelloS30"
```

Build rồi chạy emulator:

```bat
build.bat "%USERPROFILE%\Documents\LuaS30IDE\HelloS30"
```

Build có toolchain và IMSI chỉ định:

```bat
build.bat PROJECT_DIR TOOLCHAIN_DIR IMSI
```

Hoặc gọi CLI trực tiếp:

```bat
python tools\build.py ^
  --project "Documents\LuaS30IDE\HelloS30" ^
  --toolchain toolchain\arm-gcc ^
  --no-run
```

## 6. Output

```text
HelloS30\build\
├── HelloS30.axf
├── HelloS30.elf-report.txt
├── HelloS30.dev.vxp
├── HelloS30.vxp            <- artifact chính
├── *.sha256
└── sync_manifest.json
```

> **VXP xuất ra chưa ký.** IDE không ký. Firmware retail siết certificate trust
> sẽ từ chối mở file này. Xem [Build VXP](Building-VXP.md).

## 7. Thiết bị chưa biết

Trước khi build một game lớn cho thiết bị lạ, build template probe:

```text
templates\device_probe\
```

Probe kiểm tra runtime khởi động, graphics, keypad, timer, capability
file/audio/image và độ phân giải — giúp tách lỗi "engine chưa chạy được trên
firmware này" khỏi lỗi trong logic game.

## 8. Tiếp theo

- [Giao diện Studio](Studio-UI.md)
- [Build VXP](Building-VXP.md)
- [`doc/reference/API.md`](../../doc/reference/API.md) — toàn bộ API Lua
- [`doc/platform/DEVICE_COMPATIBILITY.md`](../../doc/platform/DEVICE_COMPATIBILITY.md)
- [`doc/getting-started/QUICKSTART.md`](../../doc/getting-started/QUICKSTART.md)
