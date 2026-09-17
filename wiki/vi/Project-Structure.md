# Cấu trúc project

> **Ngôn ngữ:** Tiếng Việt · [English](../en/Project-Structure.md)

Trang này mô tả hai thứ khác nhau: **cấu trúc repo IDE** (nơi engine nằm) và
**cấu trúc một project người dùng** (nơi game của bạn nằm).

## Repo IDE

```text
LuaS30-Engine/
├── VERSION
├── README.md
├── LICENSE
├── run.bat                 launcher
├── new_project.bat         tạo project
├── build.bat               build + emulator
├── build_only.bat          chỉ build
├── requirements-studio.txt
├── build/                  output build, runtime compat matrix
├── compat/                 fixture manifest firmware (MRE)
├── doc/                    toàn bộ tài liệu markdown
├── emulator/               VXP emulator
├── engine/
│   ├── src/                runtime_entry.c, runtime_lua.c, runtime_bridge.c
│   └── linker/             luas30.ld
├── profiles/               profile tương thích thiết bị (JSON)
├── sdk/luas30/
│   ├── include/ls30/       api.h base.h events.h graphics.h filesystem.h audio.h device.h compat.h
│   └── src/                abi_resolver.c  <- ranh giới portability
├── studio/                 LuaS30 Studio (PySide6, chỉ chạy trên PC)
├── templates/              basic/ và device_probe/
├── toolchain/arm-gcc/      ARM GCC đã bundle
├── tools/                  build tooling + validator
└── vendor/lua-5.1.5/       source Lua 5.1.5
```

`studio/` **chỉ chạy trên PC** — PySide6 không bao giờ được đóng vào VXP.

## Project người dùng

```text
Documents\LuaS30IDE\<ProjectName>\
├── project.json            metadata build
├── conf.lua                cấu hình runtime
├── main.lua                entry script
├── src/                    module Lua
├── assets/                 ảnh, âm thanh, resource
├── .luas30/                dữ liệu riêng của IDE
│   ├── ui_design.json
│   ├── mre_sdk.json
│   └── ai-backups/<timestamp>/
└── build/                  output build (sinh ra)
```

### `project.json`

Ví dụ từ `templates/basic/project.json`:

```json
{
  "name": "LuaS30 Demo",
  "vendor": "LuaS30",
  "appid": 262567,
  "ram_kb": 1024,
  "screen_width": 240,
  "screen_height": 320,
  "fps": 15,
  "runtime_target": "mre-s30plus",
  "single_vxp": true,
  "compat_profile": "auto",
  "mre_api": "Audio File ProMng",
  "app_version": "1.0.0",
  "mediatek_chipset": "MTK6260",
  "mediatek_chipset_label": "MTK6260  (Nokia 220, 225)",
  "resolution": "240x320",
  "resolution_label": "240x320  (QVGA - Chuẩn Nokia)"
}
```

| Trường | Ý nghĩa |
|---|---|
| `name` | tên ứng dụng hiển thị |
| `vendor` | nhà phát triển |
| `appid` | AppID số. **Mỗi project mới nhận AppID mới.** Nhân bản và Import cũng cấp AppID mới; Rename **giữ nguyên** AppID |
| `ram_kb` | heap RAM cấp cho runtime |
| `screen_width` / `screen_height` | độ phân giải (S30+ thường 240×320) |
| `fps` | FPS mục tiêu; `dt` của `engine.update(dt)` tính từ đây |
| `runtime_target` | backend runtime |
| `single_vxp` | luôn `true` — mô hình một VXP duy nhất |
| `compat_profile` | `auto` để build tự chọn theo cấu hình project |
| `mre_api` | nhóm API permission ghi vào manifest |
| `mediatek_chipset` | chipset đã chọn trong wizard |

Cấu hình **riêng của project** thuộc về file này, không hard-code trong Studio.

### `conf.lua`

```lua
config = {
    name = "LuaS30 Demo",
    screen_width = 240,
    screen_height = 320,
    fps = 15
}
return config
```

### `main.lua`

Entry script. Runtime gọi các callback trên global `engine`:

```lua
local E = engine
local bg = E.color(35, 83, 47)
local white = E.color(255, 255, 255)

function E.load()
    E.set_font(8)
end

function E.update(dt)
    -- logic theo dt
end

function E.draw()
    E.clear(bg)
    E.text(4, 4, "Hello", white)
end

function E.keypressed(k)
    if k == "0" then E.exit() end
end
```

Lifecycle đầy đủ: `load()`, `update(dt)`, `draw()`, `keypressed(key)`,
`keyreleased(key)`, `pause()`, `resume()`, `quit()`.

### `src/` và `require()`

LuaS30 có `require()` dựa trên resource:

```lua
local Player = require("src.player")
```

Runtime ưu tiên `src/player.lub`, sau đó fallback `src/player.lua`. Nhờ vậy
development mode pack raw Lua mà không cần host `luac`.

### `assets/`

Ảnh, âm thanh và resource. Đường dẫn trong Lua là **tương đối với project**:

```lua
engine.image(10, 10, "assets/image.png")
engine.audio_play("assets/sfx/select.mp3")
```

Với S30+ nên ưu tiên atlas, ảnh nhỏ, art thân thiện RGB565, audio ngắn/mono và
tái sử dụng asset.

### `.luas30/`

Thư mục dữ liệu riêng của IDE, **không** phải mã nguồn game:

| File | Nội dung |
|---|---|
| `ui_design.json` | nguồn sự thật của UI Designer (v2, đa màn hình). Sinh ra `ui_design.lua` |
| `mre_sdk.json` | cấu hình MediaTek MRE SDK do wizard ghi |
| `ai-backups/<timestamp>/` | bản sao file trước khi AI Agent ghi đè |

### `build/`

Được sinh ra, có thể xoá an toàn. Project Storage khi **nhân bản** sẽ không copy
dữ liệu `build`/`release`.

## Đường dẫn và override

```text
%APPDATA%\LuaS30IDE\        config, logs, cache, temp, backups, venv
Documents\LuaS30IDE\        project được quản lý
```

Biến môi trường override (portable/test):

```text
LUAS30_APPDATA
LUAS30_DOCUMENTS
LUAS30_PROJECTS
```

Studio resolve thư mục Documents thật của Windows, nên Documents bị redirect vẫn
hoạt động.

## Nguyên tắc dependency

Code phía target **chỉ** dùng API ổn định của LuaS30:

```text
engine.*     API chính
mre.*        alias tương thích
ls30_*       lớp Native SDK khi cần viết native extension
```

Không đưa vào phía target:

```text
third-party Lua package manager
dynamic native library
vendor MRE SDK header pack
percommon.a / peraudio.a
import firmware trực tiếp từ code ứng dụng
```

"Theo chuẩn engine-only" nghĩa là **không thêm dependency runtime cho ứng dụng và
không phụ thuộc build vào vendor MRE SDK** — không phải là điện thoại chạy được
mà không cần firmware của nó. Firmware vẫn là ranh giới hệ điều hành bắt buộc cho
display, keypad, timer, resource, file và audio.

Xem thêm [`doc/architecture/ARCHITECTURE.md`](../../doc/architecture/ARCHITECTURE.md)
và [`doc/configuration/USER_PATHS.md`](../../doc/configuration/USER_PATHS.md).
