# Câu hỏi thường gặp

> **Ngôn ngữ:** Tiếng Việt · [English](../en/FAQ.md)

## Ký và chữ ký

### Máy retail của tôi từ chối mở VXP. Sao vậy?

Vì **LuaS30 IDE không ký VXP**. File xuất ra luôn chưa ký (`cert-id 1`, khối chữ
ký 64 byte toàn số 0). Firmware retail có siết certificate trust sẽ từ chối mở
file chưa ký. Đây là hành vi **đúng theo thiết kế**, không phải lỗi.

### Tôi có thể bật ký trong IDE không?

Không. Repo này không chứa lõi ký, không chứa khóa, không có cờ `--cert100-key`.
Máy build bị lộ cũng không tạo được gói được tin cậy — đó chính là mục đích của
quyết định này.

### Vậy muốn ký thì làm thế nào?

Làm **ngoài repo này**, bằng công cụ do người vận hành kiểm soát. IDE chỉ xuất
bản chưa ký.

### Nút "Sign and Build" đâu rồi?

Đã gỡ khỏi GUI cùng toàn bộ chức năng ký. `build.bat` / `build_only.bat` chỉ
build.

### `--device-imsi` có phải là ký không?

Không. Nó chỉ ghi IMSI của SIM vào tag `0x12` và chuẩn hoá `appid`/`ram`. File
kết quả **vẫn chưa ký**. Bind tạo **điều kiện cài đặt**, không tạo **trust** —
trên firmware siết trust, bind mà không ký vẫn bị từ chối.

## Build và artifact

### Vì sao chỉ có một file VXP, không có bản riêng theo máy?

LuaS30 dùng **mô hình một VXP duy nhất**: một project → một runtime → một gói
MRE/VXP. Khác biệt firmware được xử lý bên trong engine:

```text
capability detection -> ABI aliases -> safe fallbacks
```

Muốn hỗ trợ firmware mới thì mở rộng engine/resolver, **không** tạo thêm biến thể
ứng dụng.

### VXP nằm ở đâu?

```text
<project>\build\<ProjectName>.vxp
```

Cùng thư mục có `.axf`, `.elf-report.txt`, `.dev.vxp`, `*.sha256` và
`sync_manifest.json`.

### `--release` có ký không?

Không. `--release` chỉ bật hardening (strip ký hiệu native, bảo vệ Lua) và sinh
SHA-256/manifest.

### Hardening có làm code không thể dịch ngược?

Không. Nó làm **tăng chi phí** reverse-engineering, nhưng thuật toán phía client
luôn có thể phục hồi được.

### Emulator chạy được, máy thật có chạy được không?

Không chắc. Emulator là bước test desktop, **không** phải bằng chứng tương thích.
Hãy build `templates/device_probe` và smoke test trên chính thiết bị mục tiêu.

## Môi trường

### Cần cài gì?

Windows 10/11 và Python 3.10+. PySide6 (`>=6.7,<7`) do launcher tự cài vào venv
riêng. ARM GCC và emulator đã bundle sẵn trong repo.

### Có cần MediaTek MRE SDK không?

Không bắt buộc. Đường mặc định (`standalone`) là resolver động của LuaS30. Nếu
có MRE SDK hợp lệ, backend `s30plus-native` sẽ dùng header/lib thật của SDK —
build tool tự dò.

### Dùng Lua phiên bản nào?

**Lua 5.1.5**, bundle trong `vendor/lua-5.1.5/`. Code target nên tương thích
Lua 5.1; tránh syntax/API chỉ có ở 5.2/5.3/5.4 nếu chưa được implement riêng.

### Hỗ trợ thiết bị nào?

Có preset cho `MTK6260` (Nokia 220/225), `MTK6261` (Nokia 3310 3G/216),
`MTK6250` (Q-Mobile, K-Touch) và `MTK6225` (legacy MRE 2.0). Chọn `MTK6260` sẽ
ghi profile `nokia225-rm1011`.

### Thêm thiết bị mới thế nào?

Mở rộng **engine ở trung tâm**: thêm API trung lập `ls30_*`, thêm capability nếu
service là optional, rồi resolve symbol trong `sdk/luas30/src/abi_resolver.c`.
Runtime chỉ gọi `ls30_*`, **không** gọi firmware symbol trực tiếp.

## File và đường dẫn

### Project và cấu hình nằm ở đâu?

```text
%APPDATA%\LuaS30IDE\        config, logs, cache, temp, backups, venv
Documents\LuaS30IDE\        project được quản lý
```

Có thể override bằng `LUAS30_APPDATA`, `LUAS30_DOCUMENTS`, `LUAS30_PROJECTS`.

### Thư mục `.luas30/` để làm gì?

Là dữ liệu riêng của IDE, không phải mã nguồn game:

- `ui_design.json` — nguồn sự thật của UI Designer;
- `mre_sdk.json` — cấu hình MediaTek MRE SDK;
- `ai-backups/<timestamp>/` — bản sao file trước khi AI Agent ghi đè.

### Xoá `build/` có sao không?

Không sao. Đó là output sinh ra. Project Storage khi nhân bản cũng **không** copy
`build`/`release`.

### Vì sao AppID của tôi thay đổi?

Mỗi project mới nhận AppID mới; **Duplicate** và **Import** cũng cấp AppID mới.
**Rename giữ nguyên** AppID.

## Studio và AI

### Studio chạy trên điện thoại được không?

Không. `studio/` chỉ chạy trên PC; PySide6 không bao giờ được đóng vào VXP.

### AI Agent có đọc được file secret của tôi không?

Context tự động **loại trừ** các file secret thông dụng (`.env`, credential,
private-key). Sửa code bằng AI bị giới hạn trong project và bị từ chối với đường
dẫn tuyệt đối, `../` ra ngoài project, `.git`, `.venv`, `node_modules`,
`release`. Output shell được redact các biến môi trường chứa secret trước khi gửi
cho provider từ xa.

### API key có bị lưu không?

Mặc định **chỉ trong phiên**. Nếu bạn chọn lưu, key ghi vào
`%APPDATA%/LuaS30IDE/config/ai_credentials.json` — JSON **plaintext** nằm ngoài
thư mục project. Hộp thoại nói rõ điều này và cho phép xoá key đã lưu.

### Vì sao AI không thấy phần cuối file tài liệu dài?

Vì tài liệu hướng dẫn bị cắt theo giới hạn ký tự khi nạp context (hiện tại
64.000 ký tự/file, 160.000 tổng). Nội dung vượt giới hạn **không** tới được
model. `tools/validate_ai_context.py` canh việc này.

### AI có hiện chain-of-thought thô không?

Không. Panel chỉ hiện `AI ACTIVITY · REASONING SUMMARY` với tóm tắt mức cao:
file context đã đọc, tóm tắt kế hoạch, đề xuất shell kèm rủi ro, kết quả chạy.

## Khác

### `engine.*` và `mre.*` khác nhau thế nào?

`engine` là global table chính. `mre` chỉ là **alias tương thích**. Code mới nên
dùng `engine.*`.

### Cần viết native extension không?

Chỉ khi cần dịch vụ mà Lua API chưa có. Khi đó thêm API trung lập vào `ls30_*`
rồi resolve trong `abi_resolver.c`, **không** import firmware trực tiếp.

### Làm sao kiểm tra source trước khi phát hành?

```bat
python tools\validate_tree.py
python tools\validate_native_sdk.py
python tools\validate_complete.py
```

Tổng cộng **hơn 40** validator trong `tools/validate_*.py`.

### IDE có miễn phí không?

LuaS30 IDE là tài sản của Qeafivels:

```text
© Qeafivels All rights reserved. — https://qeafivels.com/
```

Chi tiết ở [`LICENSE`](../../LICENSE). Thành phần bên thứ ba giữ giấy phép riêng:
[`doc/legal/THIRD_PARTY_NOTICES.md`](../../doc/legal/THIRD_PARTY_NOTICES.md).
