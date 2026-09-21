# Hộp thoại modal — custom Title Bar (Studio 1.0.1)

Từ Studio 1.0.1, **mọi** hộp thoại modal của IDE bỏ thanh tiêu đề mặc định của
hệ điều hành và dùng custom Title Bar theo chuẩn hộp thoại **Cấu hình MediaTek
MRE SDK**: cửa sổ `FramelessWindowHint` + `WA_TranslucentBackground`, khung
`QFrame#DialogRoot` bo góc 12px có viền `#3A3A56` và drop-shadow, thanh title
riêng kéo thả được, footer chứa nút hành động.

## Họ `CustomDialog` — một hạ tầng, mọi modal

Nguồn: `studio/app/vxpui/custom_dialog.py`.

```text
CustomDialog          <- nền tảng: title bar, body scroll, footer, drag, size grip
├── NoticeDialog      <- thông báo (info / warning / error)
├── ConfirmDialog     <- hỏi yes/no; ConfirmDialog.ask(...) -> bool
├── TextInputDialog   <- nhập một dòng/đoạn; .get_text(...)
├── IntInputDialog    <- nhập số; .get_int(...)
├── ColorPickerDialog <- nhúng widget màu Qt (NoButtons) trong khung engine
├── FilePickerDialog  <- cây tệp/thư mục tự dựng: file | files | directory | save
├── RunSessionDialog  <- log phiên chạy build
├── AboutDialog       <- (app/ui/about_dialog.py) kế thừa trực tiếp
└── SetupDialog       <- (app/views/setup_dialog.py) kế thừa trực tiếp
```

Quy ước gọi:

```python
NoticeDialog("Title", "message", parent, warning=True).exec()
if ConfirmDialog.ask("Delete", "sure?", parent, confirm_text="Yes", danger=True): ...
name, ok = TextInputDialog.get_text(parent, "Rename", "Name:", text=old)
folder = FilePickerDialog.get_existing_directory(parent, "Select ARM Toolchain Root", start)
path   = FilePickerDialog.get_save_file_name(parent, "Save source file", start, "Lua (*.lua)")
```

Không còn chỗ nào gọi `QMessageBox` / `QInputDialog` / `QColorDialog` /
`QFileDialog` trong các luồng trên — `tools/validate_*.py` và
`tools/studio_theme_check.py` soi pixel để bảo đảm không rò theme sáng.

## Bo góc

`#DialogRoot`, `#DialogTitleBar`, `#DialogFooter` trong
`studio/app/vxpui/resources/dark_theme.qss` dùng bán kính **12px** — khớp
`QFrame#MREDialogCard` của hộp thoại MRE. Kiểm chứng bằng alpha pixel: góc
`(13,13)` trong suốt, mép giữa các cạnh đặc 255.

## Ngoại lệ — cố ý, không "sửa" lại

1. **Cửa sổ giả lập** (`app/widgets/vxp_emu_window.py`, `VxpEmuWindow`) giữ
   chrome hệ điều hành: người dùng cần kéo/đè lên cửa sổ khác như máy thật và
   `QFileDialog` bên trong nó là một phần của luồng chọn `.vxp` nạp máy.
2. **Mở dự án** (`VxpMainWindow.open_project_dialog`) dùng `QFileDialog`
   **native Windows**: chọn thư mục dự án sâu nhanh hơn nhiều so với cây tự
   dựng — đây là yêu cầu trực tiếp của người dùng, đừng thay bằng
   `FilePickerDialog`.
3. `CommandPalette` (overlay Ctrl+Shift+P) frameless không title bar — mô
   hình palette của VS Code.
4. `MediaTekMREConfigDialog` là **chuẩn tham chiếu**, có title bar riêng
   (`MREDialogTitleBar`) — không đổi sang `CustomDialog`.
5. `AIProviderDialog` và `ModalDialog` (UI Designer) đã có title bar tùy biến
   riêng từ trước.

## Nút mới / hộp thoại mới

Thêm modal mới = kế thừa `CustomDialog`, nội dung đặt qua `add_body_widget()`,
nút bấm qua `add_footer_button(text, accent=..., ghost=..., danger=...)`.
Không tự dựng `QDialog` trần, không dùng dialog native của hệ điều hành
(trừ 2 ngoại lệ trên). Sau đó chạy `tools/studio_theme_check.py` + sweep
`tools/validate_*.py` để chắc chắn không rò chrome sáng.
