# Validation Studio 1.0.3

Ngày chạy: 2026-09-25 · Máy: Windows 10 x64, Python 3.12, PySide6 6.11.2.
Mọi lệnh chạy với `PYTHONUTF8=1 QT_QPA_PLATFORM=offscreen
QT_QPA_FONTDIR="C:/Windows/Fonts"`.

Bản 1.0.3 là **bản đóng gói thứ hai**, không thêm tính năng mới so với cây nguồn
đã landed — mục tiêu kiểm chứng ở đây là (a) bộ hồi quy còn xanh, (b) phản chứng
còn đỏ vì **đúng lý do**, (c) artifact cài được và gỡ sạch.

## 1. Bộ kiểm tra hồi quy — chạy KHÔNG tương tác

Sweep toàn bộ `tools/validate_*.py`:

| | |
|---|---|
| Tổng | **70 validator** |
| PASS | **70** |
| SKIP | **0** |
| FAIL | **0** |
| Thời gian | 126 s |

> ⚠️ Con số này chỉ đáng tin khi chạy **không tương tác** (một lượt, không duyệt
> từng tool-call). Chạy tương tác thì host duyệt từng lệnh nên ngân sách xoá theo
> lượt không bị chạm; chạy cả suite trong một lượt thì chạm. Đây chính là cách
> suite từng xanh oan.

Ba validator chậm nhất (đều là E2E thật, có mở VXPEmu):

| Validator | Thời gian | Ghi chú |
|---|---|---|
| `validate_popart_city_e2e.py` | 38,5 s | build ARM + mở `VXPEmu.exe --autostart --testapi --screen-only`, đọc pixel framebuffer |
| `validate_keypad_emulation_e2e.py` | 36,8 s | bơm phím vào VXPEmu thật rồi đọc framebuffer |
| `validate_about_credits.py` | 11,1 s | render offscreen bằng theme gộp |

Các guard trọng tâm của bản này:

| Guard | Kết quả | Ghi chú |
|---|---|---|
| `validate_emulator_shell_frame.py` | PASS — **710 phép kiểm** | vỏ máy vẽ đúng mockup, cmap font, hành vi phím/rail/bong bóng |
| `validate_wiki.py` | PASS — **116 link tương đối** giải được, 16 link chéo ngôn ngữ giữ nguyên tên trang | `VERSION` 1.0.3 khớp ở **cả** `vi/Home.md` và `en/Home.md` |
| `validate_task_chip_dismiss.py` | PASS | chip tác vụ đóng đúng ở cả ba đường tắt giả lập |
| `validate_ai_task_memory.py` | PASS | gọi **thân hàm thật** `_earlier_work_digest` / `_nudge_unfinished_work` trên stub |
| `validate_prior_work_suggest.py` | PASS | gọi thật `AIChatView._run_tool` với một lời gọi `projects` |
| `validate_ai_goal_mode.py` | PASS | dựng **widget thật** offscreen |
| `validate_ai_goal_rollback.py` | PASS | round-trip trên đĩa |

## 2. Phản chứng (sabotage) — đỏ vì ĐÚNG lý do, rồi xanh lại

Mỗi harness phá từng hành vi một, khẳng định guard **FAIL** ở đúng dòng, rồi khôi
phục và khẳng định **PASS**. Đây là thứ phân biệt "guard xanh" với "guard có tác dụng".

| Harness | Kết quả | Chạy lại trong lượt này |
|---|---|---|
| `build/_rp_emulator_shell_frame.py` | **36/36** | ✅ có (1 m 29 s) |
| `build/_rp_task_memory.py` | 8/8 | theo ghi nhận ở `CHANGELOG.md` |
| `build/_rp_prior_work.py` | 14/14 | theo ghi nhận ở `CHANGELOG.md` |
| `tools/popart_city_check.lua` | 16/16 ca phá | theo ghi nhận ở `CHANGELOG.md` |
| `tools/validate_popart_city_e2e.py` (phản chứng) | 23/23 | theo ghi nhận ở `CHANGELOG.md` |

Danh sách 10 ca cuối của harness vỏ giả lập (nhóm rail/bong bóng):

```text
rail mất một chức năng (icon bấm không làm gì)
icon rail mất tên
icon đang bật thôi vẽ viền accent
`_sync_rail()` bị bỏ sót ở `process_stopped` (rail nói dối)
icon rail thôi báo hover khi rê chuột vào
rail thôi nối hover của icon tới bong bóng
quên cộng `rail.y()` khi trả toạ độ hover (lệch hệ toạ độ)
rời icon mà bong bóng không tắt
bong bóng không mang cờ trong suốt với chuột (chặn bàn phím bên dưới)
ẩn rail lúc đang rê chuột để bong bóng KẸT lại
```

## 3. Đóng gói

| Bước | Kết quả |
|---|---|
| `tools/build_frozen.py` (PyInstaller onedir) | `dist/frozen/LuaS30IDE/LuaS30IDE.exe` + 3022 tệp |
| `tools/verify_release.py` trên stage | **`RELEASE OK (version 1.0.3)`** — PE GUI subsystem OK, không lộ private key, probe `--version` OK, probe Python bundled OK |
| Inno Setup 6.7.3 | `Successful compile (272,406 s)` |
| Artifact | `dist/LuaS30IDE-Setup-1.0.3.exe` — **duy nhất 1 file**, 511 171 480 byte (487,5 MB) |
| SHA-256 | `f404099bd77aee23786102bbc59db2f4794a6c0368ae88f20263c8b7f13e47af` — khớp sidecar `.sha256` **và** khớp lại khi tính độc lập sau khi build xong |

### Cài → chạy → gỡ (chạy thật, temp cô lập)

Probe `%TEMP%\luas30_final`, cấu hình tách bằng `LUAS30_APPDATA` / `LUAS30_PROJECTS`,
cài bằng `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS /DIR=<probe>`:

```text
1) CAI IM LANG : INSTALL_EXIT=0 (40,4 s) · 4649 tệp · VERSION trên đĩa = 1.0.3
2) CHAY THAT   : RUN_EXIT=0 · stdout = "LuaS30 IDE 1.0.3"
                 11/11 tệp tính năng mới có mặt + wheel PySide6 offline
                 PhoneRailButton ×7 trong studio/app/widgets/vxp_emu_window.py
3) GO CAI DAT  : UNINSTALL_EXIT=0 (1,2 s) -> THƯ MỤC BIẾN MẤT HOÀN TOÀN sau 3 s
4) REGISTRY    : không còn khoá LuaS30 / A3F5C2D1 (kiểm bằng winreg)
```

Tệp tính năng mới đã xác nhận có mặt trong bản **đã cài**: `templates/PopArtCity3D/{main,conf}.lua`,
`tools/validate_emulator_shell_frame.py`, `doc/studio/EMULATOR_SHELL_FRAME_1_0_2.md`,
`studio/app/services/{ai_task_memory,prior_work_service}.py`,
`vendor/wheels/pyside6_essentials-6.11.2-cp310-abi3-win_amd64.whl`, `python/python.exe`,
`toolchain/arm-gcc/bin/arm-none-eabi-gcc.exe`, `emulator/VXPEmu.exe`, `app-icon/icon.ico`.

> Kiểm **tệp tính năng**, không chỉ kiểm cái `.exe` — stage cũ là cách phổ biến nhất
> để phát hành một bản "chạy được" nhưng thiếu việc của hôm nay.

## 4. Ghi chú trung thực — những phép đo KHÔNG dùng được

Ghi lại để lần sau không mất thời gian lại, và để không ai đọc nhầm chúng thành
bằng chứng:

1. **"Gỡ xong còn 40 tệp DLL/`.pyd`" là KẾT LUẬN SAI.** Uninstaller của Inno
   **tự relaunch** và **trả về TRƯỚC khi xoá xong**. Đo ngay sau khi lệnh trả về
   luôn thấy vài chục tệp "sót". Bộ 40 tệp đó **giống y hệt qua 3 lần chạy** và
   **cả 40 đều đổi tên được** — hai dấu hiệu khiến kết luận sai trông rất vững,
   nhưng đều vô nghĩa. Chờ đúng cách thì cả ba thư mục probe **mất hoàn toàn**.
   ⇒ Từ nay "gỡ xong" phải định nghĩa là **thư mục biến mất**, không phải "tiến
   trình trả về". Đã ghi vào `packaging/README.md`.
2. **`/LOG=<file> /LOGLEVEL=verbose` không sinh file log nào** — cho **cả** Setup lẫn
   uninstaller. Không đọc được lý do skip trực tiếp.
3. **Tìm tên trong `unins000.dat` là phép đo vô hiệu.** Mọi mục **có** dấu `/` báo
   `False`, mọi tên trần báo `True` ⇒ dat lưu đường dẫn bằng `\` và chỉ chứa File
   section của chính nó. Probe này đã bị loại, không dùng làm bằng chứng.
4. **`reg.exe` bị sandbox chặn** trong phiên agent ⇒ hai dòng kiểm registry bằng
   `reg.exe` là **fallback, không phải bằng chứng**. Đã kiểm lại bằng `winreg`.
5. **Không dùng tooltip làm phép kiểm.** `QTest.mouseMove()` rồi đọc
   `QToolTip.isVisible()` **luôn** ra "không hiện", kể cả với `QPushButton` thường
   (đã chạy đối chứng để biết phép đo vô hiệu, không phải app lỗi). Vì thế tên phím
   và tên công cụ được **vẽ** vào chỗ đo được, không dựa vào tooltip.
6. **`QWidget.grab()` offscreen tô vùng CHƯA VẼ bằng `#efefef`** ⇒ "đếm pixel khác
   nền" không chứng minh gì; phải đếm pixel **TRÙNG màu** và đo **đoạn liền mạch**.

## 5. Việc còn lại (không chặn phát hành)

- Setup **chưa ký** ⇒ SmartScreen sẽ cảnh báo; hết cảnh báo thì phải có cert thật
  (`--sign-pfx` + `LUAS30_SIGN_PASSWORD`). Không có cách nào khác.
- `dist/frozen/.old-*` (bản frozen cũ) được **đổi tên** chứ chưa xoá — dọn bằng tay
  khi thấy cần.
- Task `#16`–`#19` (template `LuaRunner`) vẫn chờ `#16` đo khả năng thật của VXPEmu
  (`LS30_CAP_FILES`, `file_*`, `loadstring`).
