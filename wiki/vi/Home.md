# LuaS30 IDE

> **Ngôn ngữ:** Tiếng Việt · [English](../en/Home.md)

**LuaS30 IDE** là môi trường phát triển tích hợp để viết ứng dụng và game bằng
**Lua 5.1** rồi đóng gói thành **VXP** chạy trên thiết bị **S30+ / MRE**.

IDE gồm bốn phần chính:

| Thành phần | Vai trò |
|---|---|
| **LuaS30 Studio** | Giao diện desktop kiểu VS Code (PySide6): editor, Explorer, Assets, UI Designer, Emulator, terminal, ChatAI |
| **LuaS30 Runtime** | Nhúng **Lua 5.1.5** và chạy `main.lua` trên máy |
| **LuaS30 Native SDK** | API C `ls30_*` riêng, không phụ thuộc vendor MRE header hay `percommon.a` |
| **Build tooling** | Biên dịch ARM GCC, verify ELF, đóng gói VXP, sinh SHA-256, chạy emulator |

```text
Game Lua  →  engine.*  →  LuaS30 Runtime  →  Native SDK (ls30_*)  →  ABI resolver  →  firmware VXP
```

## Bắt đầu nhanh

```bat
run.bat
new_project.bat HelloS30
build.bat "%USERPROFILE%\Documents\LuaS30IDE\HelloS30"
```

Lệnh đầu mở Studio, lệnh thứ hai tạo project, lệnh thứ ba build rồi chạy trong
emulator. Chi tiết ở [Bắt đầu](Getting-Started.md).

## Điều quan trọng nhất cần biết trước

> **LuaS30 IDE không ký VXP.**
>
> `build/<ProjectName>.vxp` luôn là bản **chưa ký** (`cert-id 1`, khối chữ ký
> rỗng). File này chạy tốt trên emulator và máy dev/engineering, nhưng firmware
> **retail có siết certificate trust sẽ từ chối mở**.
>
> Đây là lựa chọn có chủ ý, không phải lỗi. IDE không chứa code ký và không chứa
> khóa. Nếu cần ký thì phải làm **ngoài repo này**.

## Mục lục wiki

| Trang | Nội dung |
|---|---|
| [Bắt đầu](Getting-Started.md) | Cài đặt, `run.bat`, tạo project đầu tiên, build đầu tiên |
| [Giao diện Studio](Studio-UI.md) | Layout, Activity Bar, bottom panel, Project Storage, UI Designer, theme |
| [Build VXP](Building-VXP.md) | Pipeline, CLI đầy đủ, output, release/hardening, giới hạn không ký |
| [Cấu trúc project](Project-Structure.md) | `project.json`, `conf.lua`, `main.lua`, `src/`, `assets/`, `.luas30/` |
| [AI Agent](AI-Agent.md) | ChatAI, access mode, giao thức `luas30-*`, AI Changes, công cụ thiết kế UI |
| [Xử lý lỗi](Troubleshooting.md) | Launcher không mở, thiếu PySide6, build fail, emulator chạy mà máy thật không |
| [Câu hỏi thường gặp](FAQ.md) | Ký, VXP đơn nhất, đường dẫn dữ liệu, Lua version, thiết bị mới |

## Tài liệu chuyên sâu

Wiki này chỉ là cửa vào. Nguồn sự thật đầy đủ nằm trong `doc/`:

- [`doc/INDEX.md`](../../doc/INDEX.md) — mục lục toàn bộ tài liệu.
- [`doc/getting-started/QUICKSTART.md`](../../doc/getting-started/QUICKSTART.md)
- [`doc/reference/API.md`](../../doc/reference/API.md) — toàn bộ API Lua.
- [`doc/build/BUILD_VXP.md`](../../doc/build/BUILD_VXP.md)
- [`doc/build/RELEASE_AND_HARDENING.md`](../../doc/build/RELEASE_AND_HARDENING.md) — mô hình không ký.
- [`doc/architecture/ARCHITECTURE.md`](../../doc/architecture/ARCHITECTURE.md)
- [`doc/support/TROUBLESHOOTING.md`](../../doc/support/TROUBLESHOOTING.md)
- [`doc/ai/SKILL.md`](../../doc/ai/SKILL.md) — quy tắc kỹ thuật cho AI agent.

## Phiên bản

Phiên bản hiện tại đọc từ file [`VERSION`](../../VERSION): **1.0.1**.

Lịch sử thay đổi: [`doc/release/changelog/`](../../doc/release/changelog/).

## Bản quyền

© Qeafivels All rights reserved. — <https://qeafivels.com/>

LuaS30 IDE (Studio, Native SDK/API, build tooling, template, tài liệu và asset)
là tài sản của Qeafivels. Chi tiết: [`LICENSE`](../../LICENSE).

Các thành phần bên thứ ba **không** thuộc phạm vi trên và giữ giấy phép riêng —
xem [`doc/legal/THIRD_PARTY_NOTICES.md`](../../doc/legal/THIRD_PARTY_NOTICES.md).
Giấy phép Lua 5.1.5 ở [`vendor/lua-5.1.5/COPYRIGHT`](../../vendor/lua-5.1.5/COPYRIGHT).
