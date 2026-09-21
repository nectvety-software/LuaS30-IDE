# Validation Studio 1.0.1 (đợt Modal UI)

Ngày chạy: 2026-09-21 · Máy: Windows 10 x64, Python 3.12, PySide6.
Mọi lệnh chạy với `PYTHONUTF8=1 QT_QPA_PLATFORM=offscreen
QT_QPA_FONTDIR="C:/Windows/Fonts"`.

## 1. Tĩnh

| Hạng mục | Kết quả |
|---|---|
| `py_compile` 14 tệp sửa trong đợt modal | PASS |
| Import toàn bộ module đã sửa (offscreen) | PASS |
| Quét CJK lạc vào text tiếng Việt (`[㐀-䶿一-鿿]`) trên các tệp sửa + CHANGELOG | SẠCH |

## 2. Động — drive hộp thoại THẬT

Script tạm (đã dọn sau khi chạy) dựng `VxpMainWindow` thật, gọi đúng luồng sản
xuất, timer soi hộp thoại đang sống trong `exec()` rồi đóng. Mỗi luồng phải mở
ĐÚNG loại dialog + frameless + có `DialogTitleBar` + alpha pixel góc bo tròn:

| Luồng thật | Hộp thoại | Kết quả |
|---|---|---|
| Help → Giới thiệu LuaS30 IDE | `AboutDialog` 720×620 | OK |
| Settings → Select ARM Toolchain Root | `FilePickerDialog` 752×650 | OK |
| Assets → Import (project đã gán) | `FilePickerDialog` 752×650 | OK |
| Explorer → New file | `TextInputDialog` 520×300 | OK |
| Explorer → Delete | `ConfirmDialog` 500×280 | OK |
| Thiết lập lần đầu | `SetupDialog` 640×560 | OK |

Góc bo đo bằng alpha: pixel `(13,13)` = 12 (trong suốt — nằm ngoài cung
12px), mép trên/trái = 255 (đặc). **6/6 PASS.**

Nhờ bài drive này phát hiện lỗi thật: hộp thoại Delete in `\n\n` thành text
thô (escape nhân đôi trong f-string `project_tree.py:260`) — đã sửa, ảnh render
lại xác nhận xuống dòng đúng.

## 3. Render + theme

- `tools/studio_theme_check.py`: FULL PASS — `VxpMainWindow` + hộp thoại MRE +
  tab đóng; 0 khối sáng, 0 dải sáng.
- Render offscreen 9 hộp thoại họ `CustomDialog` (Notice/Confirm/TextInput/
  ColorPicker/FilePicker dir+save/About/Setup/MRE) — đã soi từng ảnh, không rò
  chrome sáng.
- `validate_about_credits.py` cập nhật: render bằng theme GỘP
  `APP_STYLE + dark_theme.qss` đúng như `studio/main.py` nạp (chrome frameless
  phụ thuộc QSS này; soi bằng `APP_STYLE` đơn là soi môi trường giả), geometry
  720×620 theo mặc định mới.

## 4. Bộ kiểm tra hồi quy

- Sweep `tools/validate_*.py`: **57/57 PASS** (chạy 3 lần: trước/sau sửa
  AboutDialog, sau sửa Delete-escape).

## 5. Đóng gói

- `tools/build_frozen.py --out dist/frozen` → `dist/frozen/LuaS30IDE` (566 MB),
  đã kiểm chứng stage chứa `app/vxpui/resources/dark_theme.qss` bản mới
  (bo góc 12px) và `VERSION` = `1.0.1`.
- `tools/package_single_exe.py --out dist` (Inno Setup offline): **DUY NHẤT 1
  FILE** `dist/LuaS30IDE-Setup-1.0.1.exe` — 511.012.892 byte (~487,3 MB),
  compile 493,2 s, cài wizard hoặc im lặng `/SILENT`.
- Build đóng gói được chạy LẠI trên HEAD sau khi rebase các PR remote vừa
  merge (template DoodleQuest + selector template dự án + AI assistant
  refresh); trước khi đóng gói, `studio_theme_check.py`,
  `validate_about_credits.py` và `validate_ai_assistant_ui_refresh.py` đều
  PASS trên tree đã merge.
- SHA-256: `02f4eb591eb9582902dca7a04f9a40db766f5da91b85074f1926ee7b8e56690b`
  (sidecar `LuaS30IDE-Setup-1.0.1.exe.sha256` cạnh tệp).
