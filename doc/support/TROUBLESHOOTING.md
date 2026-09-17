# Troubleshooting

## `run.bat` không mở Studio

Kiểm tra:

```text
%APPDATA%\LuaS30IDE\logs\launcher.log
```

Sau đó chạy:

```bat
run.bat --deps-only
```

Nếu máy offline:

```bat
run.bat --offline
```

## PySide6 thiếu

Launcher chỉ cài/update khi version hiện tại không thỏa:

```text
PySide6>=6.7,<7
```

Nếu offline và package chưa có, cần cài trước khi dùng offline mode.

## ARM GCC không tìm thấy

Expected:

```text
toolchain\arm-gcc\bin\arm-none-eabi-gcc.exe
toolchain\arm-gcc\bin\arm-none-eabi-readelf.exe
```

## Build thất bại ở native SDK

Chạy:

```bat
python tools\validate_native_sdk.py
```

Nếu source có `percommon.a`, `peraudio.a` hoặc vendor MRE headers thì đó là regression.

## Project không mở

Project path mặc định:

```text
Documents\LuaS30IDE\<ProjectName>
```

Explorer root phải trỏ đúng thư mục có `project.json`.

## VXP emulator chạy nhưng máy thật không chạy

Emulator success không chứng minh firmware compatibility.

Thử:

1. build `templates/device_probe`;
2. giảm RAM/profile;
3. kiểm tra ELF report;
4. kiểm tra binding/sign policy;
5. kiểm tra firmware ABI alias;
6. thử build không audio/image optional;
7. kiểm tra lifecycle hide/inactive/resume.

## Audio không phát

Kiểm tra:

```lua
print(engine.has_audio)
```

Codec support phụ thuộc firmware. Luôn có fallback khi audio unavailable.

## Image không vẽ

Kiểm tra:

```lua
print(engine.has_images)
```

Đảm bảo resource thực sự được pack và path đúng case/tên.

## Save không hoạt động

Kiểm tra:

```lua
print(engine.has_files)
```

Không giả định writable storage tồn tại trên mọi firmware.
