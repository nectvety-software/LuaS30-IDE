# Architecture

## Tổng quan

LuaS30 được chia thành 5 lớp độc lập:

```text
┌─────────────────────────────────────┐
│ LuaS30 Studio (PySide6)             │
│ Editor / Explorer / Assets / UI     │
│ Build / Emulator / Console          │
└──────────────────┬──────────────────┘
                   │ project files
                   ▼
┌─────────────────────────────────────┐
│ Build Tooling (Python)              │
│ resources / ARM compile / ELF       │
│ verify / VXP pack / bind / hash     │
└──────────────────┬──────────────────┘
                   │ native binary + resources
                   ▼
┌─────────────────────────────────────┐
│ LuaS30 Runtime                     │
│ runtime_entry.c / runtime_lua.c     │
│ runtime_bridge.c                    │
└──────────────────┬──────────────────┘
                   │ ls30_* API
                   ▼
┌─────────────────────────────────────┐
│ LuaS30 Native SDK                  │
│ sdk/luas30/include/ls30             │
│ sdk/luas30/src                      │
└──────────────────┬──────────────────┘
                   │ firmware ABI resolver
                   ▼
┌─────────────────────────────────────┐
│ VXP-capable firmware                │
│ display / input / timers / files    │
│ resources / optional audio/images   │
└─────────────────────────────────────┘
```

## Studio

`studio/` chỉ chạy trên PC. PySide6 không được đóng vào VXP.

Các vùng chính:

- `studio/app/editor/` — editor intelligence + Explorer.
- `studio/app/views/` — Build/Emulator/Assets/UI Designer.
- `studio/app/ui/` — main window, theme, About.
- `studio/app/core/` — paths/project session.

## Build tooling

`tools/build.py` chịu trách nhiệm:

1. đọc `project.json`;
2. chọn profile;
3. gom Lua/resources;
4. compile Native SDK + runtime + Lua VM bằng ARM GCC;
5. link ARM ELF;
6. verify ELF;
7. pack VXP;
8. optional bind/sign;
9. tạo SHA-256;
10. optional chạy emulator với chính VXP cuối.

## Runtime

`engine/src/runtime_entry.c`

- entry ARM/VXP;
- bind firmware resolver;
- cung cấp minimal C runtime hooks.

`engine/src/runtime_lua.c`

- tạo Lua 5.1 VM;
- load `conf.lua/.lub`;
- load `main.lua/.lub`;
- lifecycle;
- timer/update/draw;
- input callbacks;
- pause/resume/quit.

`engine/src/runtime_bridge.c`

- tạo global `engine`;
- alias `mre`;
- graphics/files/audio/system Lua API;
- `require()` resource loader;
- capability/device info.

## Native SDK

Public headers:

```text
sdk/luas30/include/ls30/
├── api.h
├── base.h
├── events.h
├── graphics.h
├── filesystem.h
├── audio.h
└── device.h
```

Firmware-specific resolution chỉ nằm tại:

```text
sdk/luas30/src/abi_resolver.c
```

Đây là ranh giới portability quan trọng nhất.

## Quy tắc dependency

Native build không được đưa trở lại:

```text
percommon.a
peraudio.a
vmsys.h
vmgraph.h
vmio.h
vmmm.h
```

Nếu cần firmware service mới:

1. thêm API trung lập vào `ls30_*`;
2. thêm capability nếu service là optional;
3. resolve symbol trong `abi_resolver.c`;
4. runtime chỉ gọi `ls30_*`, không gọi firmware symbol trực tiếp.

## Lua 5.1

Source Lua 5.1.5 được bundle và compile cùng runtime. Không giả định Lua 5.2+ syntax/API.

## Device profiles

Target-specific policy nằm trong:

```text
profiles/*.json
```

Không hard-code model điện thoại vào gameplay/runtime nếu profile có thể diễn tả nó.

## Emulator

Emulator là bước test desktop, không phải bằng chứng cuối cùng cho compatibility máy thật.
Exact VXP bytes được đối chiếu bằng SHA-256 trong build/run workflow.


## Specialized device engine model

LuaS30 uses one stable project API and may provide device-specific MRE/VXP adaptation
underneath it.

```text
engine.* Lua application API
        ↓
shared LuaS30 runtime
        ↓
device profile / adapter
        ↓
LuaS30 Native SDK
        ↓
firmware ABI resolver
        ↓
specific S30+/VXP firmware
```

This lets a Nokia/S30+ target receive a specialized profile without forcing game source
to call device firmware APIs directly.

"No dependency" for target applications means no extra application runtime frameworks
and no vendor MRE SDK build dependency. The firmware operating-system ABI remains an
unavoidable platform boundary.


## Single application artifact

LuaS30 1.8.1 does not fork an application VXP by phone model.

```text
single ProjectName.vxp
        ↓
shared engine.* API
        ↓
runtime capability detection
        ↓
ABI resolver aliases
        ↓
firmware
```

When a new firmware needs compatibility work, update the engine/resolver instead of
creating another application variant.
