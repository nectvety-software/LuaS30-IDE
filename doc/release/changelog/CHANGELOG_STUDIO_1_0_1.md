# LuaS30 Studio 1.0.1 — chi tiết

Tóm tắt đầy đủ theo từng đợt nằm trong `CHANGELOG.md` gốc (mục `[1.0.1]`).
Tệp này nhóm lại theo hệ thống con và đi sâu vào đợt **Modal UI custom Title
Bar** — hạng mục chốt của bản 1.0.1, tài liệu sử dụng ở
[`doc/studio/MODAL_TITLEBAR_1_0_1.md`](../../studio/MODAL_TITLEBAR_1_0_1.md).

## 1. Chrome cửa sổ (nền tảng của mọi thứ bên dưới)

- Port giao diện VXPEngine vào `studio/app/vxpui/`: `VxpMainWindow` frameless
  với `CustomTitleBar` nhúng menu bar, họ `CustomDialog`, edge-resize thủ công,
  `WindowStateController`; lõi Lua/build giữ nguyên.
- Icon không phụ thuộc QtAwesome lúc chạy packaged: fallback Segoe MDL2/Fluent.
- Bảng màu UAGet đồng bộ toàn IDE (`palette.py` + `dark_theme.qss` + chrome
  `vxpui`); vùng Chat đổi thương hiệu "AI Trợ lý" → "AI Agent".

## 2. Hộp thoại modal — custom Title Bar, bo góc 12px (đợt chốt)

Mọi modal bỏ thanh tiêu đề hệ điều hành, dựng trên `CustomDialog` theo chuẩn
hộp thoại "Cấu hình MediaTek MRE SDK":

- **Họ hội thoại**: ~30 điểm gọi `QMessageBox`/`QInputDialog`/`QColorDialog`/
  `QFileDialog` chuyển sang `NoticeDialog`/`ConfirmDialog`/`TextInputDialog`/
  `IntInputDialog`/`ColorPickerDialog`/`FilePickerDialog` — phủ main window,
  editor tabs, project tree, AI chat, assets, project manager, settings,
  UI Designer (color button, import dialog), wizard MRE (warning nội bộ).
- **`FilePickerDialog` thêm chế độ save**: nhập tên tệp, chặn ghi đè không hỏi,
  xác nhận "Tệp đã tồn tại → Ghi đè" qua `ConfirmDialog` danger.
- **`AboutDialog` + `SetupDialog` dựng lại trên `CustomDialog`**: About cao
  mặc định 620px (chrome frameless chiếm ~100px; giữ cam kết "dòng bản quyền
  không phải cuộn"), footer nút "Đóng"; Setup bỏ scroll lồng, 4 nút footer giữ
  nguyên hành vi (Bỏ qua/Kiểm tra lại/Tự động cài đặt/Hoàn tất + `reject()` =
  `mark_setup_done`).
- **Bo góc 12px** cho `#DialogRoot`/`#DialogTitleBar`/`#DialogFooter`
  (`dark_theme.qss`), khớp `QFrame#MREDialogCard`; viền `#3A3A56`.
- **Ngoại lệ có chủ đích**: (a) cửa sổ giả lập `VxpEmuWindow` giữ chrome hệ
  điều hành; (b) "Mở dự án" dùng `QFileDialog` **native Windows** theo yêu cầu
  người dùng — chọn thư mục sâu nhanh hơn cây tự dựng; (c) `CommandPalette`
  overlay; (d) `MediaTekMREConfigDialog` là chuẩn tham chiếu; (e)
  `AIProviderDialog`/`ModalDialog` đã có title bar riêng.
- **Lỗi sửa kèm**: hộp thoại Delete trong Explorer in chuỗi `\n\n` thành text
  thô (escape nhân đôi trong f-string, `project_tree.py`) — phát hiện nhờ bài
  drive modal thật, không phải nhờ đọc code.
- **Validator cập nhật**: `validate_about_credits.py` render bằng theme gộp
  `APP_STYLE + dark_theme.qss` đúng như app thật nạp (chrome frameless sống
  nhờ QSS này) và resize 720×620 theo geometry mới.

## 3. Trang chủ / Project Hub

- Sidebar menu căn trái + tính năng thật: "Trang chủ" = 4 dự án gần đây + "Xem
  tất cả →"; "Dự án" = lưới đầy đủ; "Tài liệu" = mở `doc/INDEX.md`.

## 4. AI Agent

- Vòng lặp kiểu Cline (đa tool-call mỗi lượt, auto-apply, thẻ "Đã sửa N tệp",
  thẻ PROBLEM realtime, khoanh vùng project), bong bóng DuckChat/Codex,
  hiệu ứng suy luận, composer tự lớn + Esc dừng, `run_app` một phát chạy giả
  lập + smoke screenshot, parser dung cảm tool-call XML/JSON mọi kiểu.

## 5. UI Designer / Assets

- Cửa sổ "TÀI NGUYÊN · UI DESIGNER" kiểu Photoshop + modal asset picker;
  chỉnh sửa chuẩn Canva (undo/redo, 8 tay nắm, align, lock, pan/zoom);
  sửa ảnh AI tạo không hiện do registry lệch đĩa.

## 6. Build / Run / Đóng gói

- Nút "Dừng" diệt đúng cả cây tiến trình (`kill_process_tree`).
- IDE hết giật khi run giả lập (gom console buffer, repaint ~60ms).
- Pipeline một file Setup EXE: `build_frozen.py` + `package_single_exe.py`
  (Inno Setup, offline wheels, SHA-256); bắt buộc bundle `dark_theme.qss` +
  `VERSION` (thiếu là UI trong suốt qua cửa sổ / nhiễm `setup_state.json`).
