# LuaS30 Native SDK / MRE API v1.6

## Mục tiêu

LuaS30 sở hữu lớp SDK mà runtime sử dụng. Native code không compile dựa trên
vendor MRE headers và không link `percommon.a` / `peraudio.a`.

```text
Lua game
   ↓
engine.*
   ↓
LuaS30 Runtime
   ↓
LuaS30 Native SDK (ls30_*)
   ↓
ABI Resolver
   ↓
VXP-capable firmware
```

## Điều "độc lập" có nghĩa gì

LuaS30 tự định nghĩa:

- primitive types;
- event/key constants;
- RGB565 helpers;
- file/audio/image abstraction;
- device/capability model;
- public `ls30_*` API;
- runtime lifecycle;
- VXP packaging/build tooling.

LuaS30 **không thể bỏ firmware ABI**. Display, keypad, timer, resource loader,
filesystem và audio là dịch vụ của hệ điều hành thiết bị. Phần phụ thuộc bắt buộc
này được cô lập ở `sdk/luas30/src/abi_resolver.c`.

## Public headers

```text
sdk/luas30/include/ls30/
├── base.h
├── events.h
├── graphics.h
├── filesystem.h
├── audio.h
├── device.h
└── api.h
```

Native runtime bên ngoài resolver chỉ nên include các header này.

## Public API groups

### Platform

```c
int ls30_platform_bind(ls30_symbol_resolver resolver);
int ls30_platform_ready(void);
ls30_u32 ls30_capabilities(void);
```

### Memory/process

```c
void *ls30_alloc(int size);
void *ls30_realloc(void *ptr, int size);
void  ls30_free(void *ptr);
int   ls30_ticks(void);
void  ls30_exit(void);
```

### Events/timers

```c
void ls30_on_system(ls30_system_event_cb cb);
void ls30_on_key(ls30_key_event_cb cb);
void ls30_on_pen(ls30_pen_event_cb cb);
int  ls30_timer_start(unsigned ms, ls30_timer_cb cb);
void ls30_timer_stop(int timer_id);
```

### Graphics

API hỗ trợ layer framebuffer, fill rect, text, line, flush và image canvas.

### Files/audio

Các API optional được expose thông qua capability bits.

## Capability bits

```text
LS30_CAP_FILES
LS30_CAP_AUDIO
LS30_CAP_IMAGES
LS30_CAP_TOUCH
LS30_CAP_LOG
LS30_CAP_RENAME
LS30_CAP_REMOVABLE
```

Optional symbol không tồn tại không nên khiến runtime link fail; feature tương ứng
được disable.

## Required vs optional

Required baseline cần đủ để:

- allocate/free;
- register lifecycle/key callbacks;
- load resources;
- timer;
- query screen;
- create/access layer;
- clip/font/fill/text/flush.

Files, audio, image decode, touch, rename, removable storage và logging là optional.

## Device profile

```c
typedef struct ls30_device_profile {
    const char *family;
    int screen_width;
    int screen_height;
    int preferred_fps;
    int recommended_ram_kb;
    ls30_u32 capabilities;
} ls30_device_profile;
```

Lua:

```lua
local d = engine.device_info()
print(d.family)
print(d.width, d.height)
print(d.preferred_fps)
print(d.recommended_ram_kb)

local caps = engine.capabilities()
```

## Port firmware mới

Không sửa toàn runtime.

1. Build `templates/device_probe`.
2. Kiểm tra symbol baseline.
3. Nếu firmware dùng spelling khác, thêm alias tại `abi_resolver.c`.
4. Nếu service mới là optional, thêm capability.
5. Thêm `profiles/<device>.json`.
6. Test hardware.
7. Ghi lại kết quả vào compatibility documentation.

## Quy tắc

Firmware symbols không được gọi trực tiếp từ:

```text
engine/src/runtime_*.c
```

Chỉ `abi_resolver.c` biết tên ABI cụ thể.
