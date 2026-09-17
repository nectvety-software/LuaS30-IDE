# Xử lý lỗi

> **Ngôn ngữ:** Tiếng Việt · [English](../en/Troubleshooting.md)

## `run.bat` không mở Studio

Xem log:

```text
%APPDATA%\LuaS30IDE\logs\launcher.log
```

Rồi chạy lại chỉ phần dependency:

```bat
run.bat --deps-only
```

Nếu máy đang offline:

```bat
run.bat --offline
```

## Thiếu PySide6

Launcher chỉ cài/cập nhật khi version hiện tại không thỏa:

```text
PySide6>=6.7,<7
```

Nếu offline mà package chưa có trong cache, phải cài trước rồi mới dùng được chế
độ offline. Có thể ép cài lại:

```bat
run.bat --force-deps
```

## Không tìm thấy ARM GCC

Các file cần có:

```text
toolchain\arm-gcc\bin\arm-none-eabi-gcc.exe
toolchain\arm-gcc\bin\arm-none-eabi-readelf.exe
```

Chẩn đoán:

```bat
python tools\toolchain_doctor.py --toolchain toolchain\arm-gcc
```

`toolchain_doctor` kiểm tra cả **linker**, không chỉ GCC/cc1/assembler. Nếu
preflight fail, thường là do backend `cc1.exe` không nạp được DLL runtime — build
tool tự prepend thư mục toolchain vào `PATH` của tiến trình con để tránh phải cài
MSYS2 toàn cục hoặc sửa `PATH` thủ công.

## Build thất bại ở native SDK

```bat
python tools\validate_native_sdk.py
```

Nếu source có `percommon.a`, `peraudio.a` hoặc vendor MRE header thì đó là
**regression** — Native SDK không được phép phụ thuộc vendor.

## Project không mở

Đường dẫn mặc định:

```text
Documents\LuaS30IDE\<ProjectName>
```

Explorer root phải trỏ đúng thư mục **có** `project.json`. Nếu mở nhầm thư mục
cha, Explorer sẽ không thấy cấu trúc project.

## Emulator chạy nhưng máy thật không chạy

Emulator pass **không** chứng minh firmware compatibility. Thử lần lượt:

1. build `templates/device_probe` để tách lỗi engine khỏi lỗi game;
2. giảm RAM/profile;
3. đọc `build\<Project>.elf-report.txt`;
4. kiểm tra binding/sign policy;
5. kiểm tra firmware ABI alias;
6. thử build **không** dùng audio/image optional;
7. kiểm tra lifecycle hide / inactive / resume.

## Máy retail từ chối mở VXP

**Đây là hành vi đúng, không phải lỗi.**

LuaS30 IDE **không ký** VXP. File xuất ra luôn chưa ký:

```text
cert-id            1
khối chữ ký        64 byte, toàn số 0
```

Firmware retail có siết certificate trust sẽ từ chối mở. Repo này không chứa code
ký và không chứa khóa, nên **không có cách nào** bật ký từ trong IDE. Nếu cần ký,
phải làm ngoài repo bằng công cụ do người vận hành kiểm soát.

Chi tiết: [Build VXP](Building-VXP.md).

## Audio không phát

```lua
print(engine.has_audio)
```

Codec support phụ thuộc firmware. Luôn có fallback khi audio không khả dụng.

## Image không vẽ

```lua
print(engine.has_images)
```

Kiểm tra resource có thật sự được pack và đường dẫn đúng **case**/tên.

## Save không hoạt động

```lua
print(engine.has_files)
```

Không giả định writable storage tồn tại trên mọi firmware.

## Thư mục dữ liệu vẫn tên `LuaS30Engine`

Tên sản phẩm là **LuaS30 IDE** và thư mục dữ liệu đích là `LuaS30IDE`; hệ thống
tự đổi tên từ `LuaS30Engine` lúc khởi động.

Nếu vẫn thấy tên cũ, nguyên nhân thường là **một tiến trình đang giữ thư mục**
(ví dụ emulator hoặc `python.exe` đang chạy). Windows không cho `os.rename` thư
mục đang bị giữ, và code **cố ý** quay về tên cũ thay vì làm hỏng dữ liệu.

Cách xử lý: đóng hết tiến trình liên quan rồi chạy lại. **Đừng** "sửa" bằng cách
copy rồi xoá — cách đó có thể mất cấu hình.

## Dải trắng ở giao diện

Một vùng vẫn sáng trong theme tối gần như luôn là **widget chưa được style**,
không chỉ subcontrol của nó. Ví dụ điển hình: chỉ khai báo `QHeaderView::section`
mà không khai báo nền cho chính `QHeaderView` — vùng sau section cuối rơi về
palette mặc định sáng.

Kiểm tra:

```text
QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
  py -3.12 -u tools/studio_theme_check.py
```

Rà thêm `QTabBar`, `QTableView`, `QTreeView`, `QListWidget`, `QScrollArea` — nếu
chỉ thấy `::subcontrol` mà không có rule cho chính widget thì gần như chắc chắn
còn sót một vùng nền.

## AI Agent "không thấy" phần cuối tài liệu

Tài liệu hướng dẫn bị cắt theo giới hạn ký tự khi nạp vào context. Nội dung nằm
quá giới hạn sẽ **âm thầm** không tới được model.

Giới hạn hiện tại: 64.000 ký tự mỗi file, 160.000 ký tự tổng; thông báo cắt ghi
rõ số ký tự bị bỏ.

```bat
python tools\validate_ai_context.py
```

## Kiểm tra trước khi phát hành

```bat
python tools\validate_tree.py
python tools\validate_native_sdk.py
python tools\validate_complete.py
```

Bộ `tools/validate_*.py` gồm **hơn 40** validator. `run.bat` cũng chạy validation
trước khi mở Studio.

## Nguyên tắc tương thích

Không kết luận VXP chạy được trên mọi máy chỉ vì:

- ELF hợp lệ;
- emulator chạy;
- hoặc build thành công.

Mỗi firmware VXP có thể khác nhau về ABI, RAM, audio codec, resource format,
binding policy và symbol availability.

Xem thêm [`doc/support/TROUBLESHOOTING.md`](../../doc/support/TROUBLESHOOTING.md).
