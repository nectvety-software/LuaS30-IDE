# Memory / production report

- Target resolution: 240x320
- Target frame rate: 15 FPS
- Target RAM: 1024 KB
- Production `main.lua`: ~28.9 KB source
- Indexed sprite atlas: ~1.1 KB, 128x128, low-color palette
- Enemy pool: 20 preallocated slots
- Box pool: 8 preallocated slots
- FX pool: 24 preallocated slots
- Audio queue: fixed ring buffer, 8 entries
- Incremental GC: one step about every 3 seconds
- Full GC: level load / explicit debug action only
- Background: procedural rectangles; no full-screen bitmap
- Atlas, tone, save and heap APIs are optional and have fallbacks

The host `texlua` runtime used for smoke testing is not representative of MTK6260 native heap usage, so its heap figure is intentionally not reported as device RAM.
