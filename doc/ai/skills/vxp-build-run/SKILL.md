---
name: vxp-build-run
description: Quy trình build + chạy + tự kiểm chứng một dự án .vxp bằng toolchain LuaS30 (tools/build.py, tools/run_emulator.py, quét validate_*.py)
---

# Build · chạy · kiểm chứng .vxp

Dùng skill này khi người dùng yêu cầu build dự án, chạy giả lập, hoặc khi
bạn vừa sửa code và cần bằng chứng rằng dự án vẫn chạy được.

## Trình tự chuẩn

1. **Build**: shell action
   `{"command":"python tools/build.py <dự-án>","cwd":"project"}`
   (hoặc nút Build VXP của IDE — đừng gọi trực tiếp compiler từng phần).
   - Mọi tệp nguồn phải là UTF-8; pipeline build UTF-8 đã cố định — KHÔNG
     đổi encoding thủ công.
2. **Đọc kết quả build**: lỗi biên dịch Lua → sửa bằng `luas30-edit`;
   lỗi linker/toolchain → chạy `python tools/s30plus_doctor.py` và
   `python tools/toolchain_doctor.py` để chẩn đoán đường dẫn.
3. **Chạy giả lập**: `python tools/run_emulator.py <tệp.vxp>` — emulator
   nguồn thật là bản deploy VXPEmu; cần `--screen-only` khi nhúng cửa sổ.
4. **Tự kiểm chứng thay đổi IDE** (khi sửa chính studio/ hoặc tools/):
   - `PYTHONUTF8=1` + `QT_QPA_PLATFORM=offscreen` là BẮT BUỘC (console máy
     này cp1252, validator in tiếng Việt sẽ crash nếu thiếu).
   - Quét: `python tools/validate_<area>.py` từng cái, kỳ vọng rc=0.
   - Theme: `python tools/studio_theme_check.py` — dòng `FAIL: không có`
     nghĩa là XANH (không phải lỗi).

## Quy tắc an toàn

- Một lệnh shell mỗi lần; đọc kết quả rồi hãy lệnh tiếp (đừng đoán lệnh gộp).
- Không `git commit` trừ khi người dùng yêu cầu rõ.
- Lệnh build/emulator chạy trong `cwd:"project"`; đừng thoát khỏi gốc dự án.

## Khi thất bại lặp lại

- Cùng một lỗi build 2 lần với cùng một bản sửa → DỪNG, đọc tệp nguồn thật
  bằng read (đừng sửa mù), rồi mới thử lại.
- Lỗi "missing symbol" gọi hàm `engine.*` → `grep`/`read` tệp `src/engine.lua`
  của CHÍNH dự án để đối chiếu tên hàm thật; hàm không có ở đó thì không tồn tại.
