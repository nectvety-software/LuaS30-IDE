# Build VXP

> **Ngôn ngữ:** Tiếng Việt · [English](../en/Building-VXP.md)

## Pipeline

```text
Project
  ↓
Validate configuration
  ↓
Collect Lua + assets
  ↓
Compile LuaS30 Native SDK
  ↓
Compile Runtime + Lua 5.1 VM
  ↓
ARM GCC link
  ↓
ELF verification
  ↓
VXP resource package
  ↓
Optional IMSI binding (không phải ký)
  ↓
SHA-256
  ↓
Optional VXP emulator
```

## Lệnh nhanh

Build + chạy emulator:

```bat
build.bat PROJECT_DIR
```

Chỉ build:

```bat
build_only.bat PROJECT_DIR
```

Chỉ định toolchain và IMSI:

```bat
build.bat PROJECT_DIR TOOLCHAIN_DIR IMSI
```

## CLI đầy đủ

```bat
python tools\build.py ^
  --project PROJECT_DIR ^
  --toolchain toolchain\arm-gcc ^
  --no-run
```

Các argument hiện có:

| Argument | Giá trị |
|---|---|
| `--project` | thư mục project |
| `--toolchain` | thư mục ARM toolchain |
| `--compiler-profile` | `auto` \| `gcc` \| `rvds` \| `ads12` |
| `--compat-profile` | `auto` \| `standalone` \| `s30plus-native` \| `nokia225-rm1011` |
| `--mre-sdk` | đường dẫn MRE SDK (không bắt buộc, tự dò) |
| `--device-imsi` | bind IMSI vào tag `0x12` |
| `--entry-symbol` | ghi đè entry symbol |
| `--luac` | đường dẫn `luac.exe` (Lua 5.1) |
| `--appid` | ghi đè AppID |
| `--ram` | ghi đè RAM (KB) |
| `--release` | bật hardening + sinh SHA-256/manifest |
| `--lua-protection` | `auto` \| `bytecode` \| `minify` \| `off` |
| `--harden-native` | strip ký hiệu native |
| `--run` / `--no-run` | chạy emulator sau build |
| `--emulator` | chọn emulator |

> **Không có cờ ký nào.** IDE không ký VXP.

Compiler profile `rvds` và `ads12` cần bản ARM toolchain hợp lệ do bạn tự cài.
Đường **ARM GCC là đường được bundle và đã validate**.

## Output

```text
PROJECT_DIR\build\
├── <Project>.axf
├── <Project>.elf-report.txt
├── <Project>.dev.vxp
├── <Project>.vxp            <- artifact chính
├── *.sha256
└── sync_manifest.json
```

`<Project>.vxp` là artifact **duy nhất**. Không có biến thể theo thiết bị và
không có hậu tố thiết bị trong tên file.

## Raw Lua và bytecode

Không truyền `--luac`:

- `.lua` được pack trực tiếp;
- runtime compile khi load;
- thuận tiện cho development.

Có Lua 5.1 `luac`:

```bat
--luac path\to\luac.exe
```

- Lua được compile thành `.lub`;
- stripped bytecode có thể giảm công việc lúc khởi động;
- **phải** dùng đúng Lua 5.1-compatible bytecode.

`require("src.player")` ưu tiên `src/player.lub`, sau đó fallback `src/player.lua`
— nhờ vậy development mode pack raw Lua mà không cần host `luac`.

## Yêu cầu ELF

`tools/verify_elf.py` phải kiểm tra output ARM phù hợp với runtime/build policy.
Không thay ARM GCC bằng Clang/LLD rồi coi binary là tương đương nếu chưa verify.

Nếu preflight ARM GCC fail:

```bat
python tools\toolchain_doctor.py --toolchain toolchain\arm-gcc
```

## Release và hardening

```bat
python tools\build.py --project PROJECT --toolchain toolchain\arm-gcc ^
  --release --no-run
```

`--release` **chỉ** bật hardening và sinh metadata:

- strip ký hiệu native không cần thiết;
- bảo vệ Lua (bytecode stripped nếu có `--luac`, nếu không thì minify thận trọng);
- sinh SHA-256 và ghi VXP/release manifest.

Nó **không** ký, và **không** tạo gói riêng theo thiết bị.

Hardening làm tăng chi phí reverse-engineering nhưng **không thể** làm cho thuật
toán phía client trở nên bất khả phục hồi.

## IDE không ký VXP

Đây là quyết định kiến trúc, cần nói rõ để không bị hiểu là lỗi.

**Trong repo này không có lõi ký, không có khóa, không có cờ `--cert100-key`,
không có bước verify chữ ký.** `build/<ProjectName>.vxp` **luôn** là bản chưa ký:

```text
cert-id            1
khối chữ ký        64 byte, toàn số 0
```

Hệ quả:

- Output dành cho **emulator** và **máy dev/engineering**.
- Firmware **retail có siết certificate trust sẽ từ chối mở** file chưa ký.
- Nếu cần ký thì phải làm **ngoài repo này**, bằng công cụ do người vận hành
  kiểm soát. IDE không mang khóa và không mang code ký, nên máy build bị lộ cũng
  không tạo được gói được tin cậy.

Các file đã được gỡ khỏi repo vì lý do này:

```text
tools/vxp_sign_core.py
tools/vxp_sign_pure.py
doc/build/VXP_SIGNER.md
doc/build/SIGNING_AND_RELEASE.md
tools/validate_vxp_signer.py
--cert100-key
```

### Bind IMSI không phải ký

`tools/vxp_bind_nokia225.py` **được giữ lại**, vì bind IMSI không phải là ký:

- nó chỉ ghi IMSI của SIM vào tag `0x12` và chuẩn hoá `appid`/`ram`;
- file kết quả **vẫn chưa ký**.

Nói cách khác, bind tạo ra **điều kiện cài đặt**, không tạo ra **trust**. Trên
firmware retail siết certificate trust, bind mà không ký vẫn bị từ chối.

Không ghi IMSI hay định danh nhạy cảm vào tài liệu hoặc repository.

## Mô hình VXP đơn nhất

```text
one Lua project
      ↓
one LuaS30 runtime
      ↓
one generic MRE/VXP package
      ↓
runtime capability detection / ABI aliases
      ↓
VXP-capable firmware
```

Ứng dụng **không** được tách VXP theo model điện thoại. Khác biệt firmware được
xử lý bên trong engine:

```text
capability detection -> ABI aliases -> safe fallbacks
```

Khi gặp firmware mới cần hỗ trợ, hãy **mở rộng engine/resolver**, không tạo thêm
biến thể ứng dụng.

`profiles/` có thể còn lại như tài liệu nghiên cứu tương thích nội bộ, nhưng
không còn là bộ chọn build của project.

## Checklist phát hành

- validation PASS;
- ARM ELF report đã review;
- VXP SHA-256 đã sinh;
- emulator smoke test;
- smoke test trên **chính thiết bị mục tiêu**;
- save/load;
- pause/resume;
- endurance 30–120 phút nếu là game lớn.

## Nguyên tắc tương thích

Không được kết luận một VXP chắc chắn chạy trên mọi điện thoại chỉ vì:

- ELF hợp lệ;
- emulator chạy;
- hoặc build thành công.

Mỗi firmware VXP có thể khác nhau về ABI, RAM, audio codec, resource format,
binding policy và symbol availability.

## Kiểm tra source

```bat
python tools\validate_tree.py
python tools\validate_native_sdk.py
python tools\validate_complete.py
```

Bộ `tools/validate_*.py` gồm **hơn 40** validator và phải xanh trước khi phát hành.

Xem thêm:
[`doc/build/BUILD_VXP.md`](../../doc/build/BUILD_VXP.md) ·
[`doc/build/RELEASE_AND_HARDENING.md`](../../doc/build/RELEASE_AND_HARDENING.md) ·
[`doc/build/TOOLCHAIN_PROFILES_1_10_0.md`](../../doc/build/TOOLCHAIN_PROFILES_1_10_0.md)
