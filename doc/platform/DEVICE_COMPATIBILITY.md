# Device Compatibility

## Baseline

LuaS30 v1.6 dùng baseline ARMv5TE + soft-float cho VXP workflow hiện tại.

Profile chung:

```text
generic-vxp-qvga
```

Mục tiêu mặc định:

```text
240×320
15 FPS
1536 KB profile recommendation
```

Đây là baseline build policy, không phải cam kết mọi thiết bị VXP đều có cùng ABI.

## Capability model

Runtime phân biệt optional feature:

- files;
- audio;
- images;
- touch;
- logging;
- rename;
- removable storage.

Game nên kiểm tra:

```lua
engine.has_files
engine.has_audio
engine.has_images
```

và dùng fallback.

## Device probe

Trước khi port game lớn:

```text
templates/device_probe/
```

Probe nên được build/chạy trước để xác minh:

1. app khởi động;
2. framebuffer/text;
3. keypad;
4. timer;
5. screen dimensions;
6. optional capabilities.

## Nokia 225 Dual SIM

Có profile:

```text
nokia-225-dual-sim
```

Không nên suy ra compatibility chỉ từ tên model. Firmware revision và policy phân phối VXP
có thể khác.

## Port thiết bị mới

1. Clone `generic-vxp-qvga.json`.
2. Đặt screen/RAM/FPS conservative.
3. Build `device_probe`.
4. Ghi symbol/feature thiếu.
5. Thêm ABI alias trong `abi_resolver.c` nếu cần.
6. Không gọi firmware API trực tiếp ngoài resolver.
7. Test save/audio/image.
8. Test inactive/hide/resume.
9. Chạy endurance.
10. Chỉ sau đó cập nhật compatibility status.

## Compatibility status đề xuất

Documentation nên dùng một trong:

```text
UNTESTED
EMULATOR_ONLY
BOOTS_ON_HARDWARE
SMOKE_TESTED
ENDURANCE_TESTED
```

Không dùng "fully compatible" nếu chưa có test phù hợp.
