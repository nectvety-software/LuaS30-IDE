# AI Agent

> **Ngôn ngữ:** Tiếng Việt · [English](../en/AI-Agent.md)

LuaS30 Studio tích hợp **ChatAI** ở sidebar bên phải — một workspace kiểu agent,
có thể đọc codebase, đề xuất sửa file và chạy lệnh trong terminal mà người dùng
nhìn thấy.

## Preflight bắt buộc

Bất kỳ AI agent nào tạo, scaffold, import, migrate, sinh hoặc sửa đáng kể một
project LuaS30 **phải** đọc hai file này, **đúng thứ tự**:

```text
1. doc/ai/SKILL.md
2. doc/ai/PROMPT.md
```

Sau đó phải kiểm tra source/config hiện tại liên quan tới target được yêu cầu.
**Không** tạo project từ ký ức, từ context chat cũ, từ kiến thức MRE chung chung
hoặc từ phiên bản LuaS30 cũ.

Preflight tối thiểu cho một project mới:

```text
doc/ai/SKILL.md
doc/ai/PROMPT.md
VERSION
README.md
doc/INDEX.md
profiles/<selected-target>.json
templates/basic/
```

Nếu chưa có profile đúng target:

```text
profiles/generic-vxp-qvga.json
templates/device_probe/
sdk/luas30/include/ls30/
sdk/luas30/src/abi_resolver.c
```

Rồi hoặc dùng profile generic thận trọng và **ghi rõ tương thích phần cứng chưa
được kiểm chứng**, hoặc thêm profile/adapter cho target trước, validate, rồi mới
scaffold ứng dụng.

Điểm vào cho agent: [`doc/ai/README.md`](../../doc/ai/README.md).

## Provider

Hỗ trợ các transport:

```text
OpenAI
Anthropic
Google Gemini
OpenAI Compatible
Ollama Local
```

**AI Provider Settings** là modal không viền, gồm: Provider, Model, Base URL, API
key, Timeout, Allow shell requests, Allow code-change proposals, Show reasoning
summary/activity trace.

Nút: **Test Connection**, **Apply**, **Save & Close**, **Cancel**.

`Test Connection` chạy một request thật tối thiểu trong QThread nên UI không bị
block, và báo `Connected` hoặc lỗi kết nối/API trả về.

API key mặc định **chỉ tồn tại trong phiên**. Nếu người dùng chọn lưu, key được
ghi vào:

```text
%APPDATA%/LuaS30IDE/config/ai_credentials.json
```

Đây là JSON **plaintext** nằm ngoài thư mục project, được ghi atomically và IDE cố
gắng siết quyền filesystem nơi hệ điều hành hỗ trợ. Hộp thoại nói rõ điều này và
cho phép xoá key đã lưu bằng cách bỏ chọn rồi Apply. Cấu hình
provider/model/base URL/timeout nằm riêng ở `ai_providers.json`.

## Chế độ truy cập

Selector nằm ngay dưới ô nhập chat:

| Chế độ | Hành vi |
|---|---|
| **Ask before changes** | đề xuất sửa file mở tab `AI Changes` để review; người dùng bấm `Apply Code` hoặc `Reject`. Yêu cầu shell cần bấm Run |
| **Edit automatically** | thay đổi đã validate được áp dụng tự động; shell **vẫn** cần phê duyệt; file bị thay thế được backup |
| **Plan mode** | prompt tắt hẳn `luas30-edit` và `luas30-shell`; AI vẫn đọc context và trả về kế hoạch |
| **Full access** | áp dụng tự động thay đổi đã validate; lệnh phân loại `safe`/`project` chạy tự động trong Terminal hiển thị |

> Lệnh `sensitive` hoặc `dangerous` **không bao giờ** chạy ngầm — kể cả ở Full
> access vẫn phải xác nhận.

Selector đổi **hành vi xác nhận**, không đổi **sandbox**.

## Luồng hoạt động và reasoning

LuaS30 **không** hiển thị chain-of-thought thô của provider. Panel hiển thị:

```text
AI ACTIVITY · REASONING SUMMARY
```

Nội dung có thể gồm: file/quy tắc context được chọn, tóm tắt reasoning mức cao,
tóm tắt đề xuất code, đề xuất shell kèm mức rủi ro, kết quả chạy shell, kết quả
apply/reject, lỗi provider/tool. Model dùng block có giới hạn `luas30-summary`.

## Giao thức

| Giao thức | Vai trò |
|---|---|
| `luas30-edit` | đề xuất sửa file trong project (patch `find`/`replace` hoặc full file `content`) |
| `luas30-shell` | đề xuất chạy lệnh trong Terminal hiển thị |
| `luas30-tool` | công cụ chỉ đọc: `read`, `grep`, `glob` |
| `luas30-summary` | tóm tắt activity/reasoning mức cao |

Ví dụ `luas30-edit` dạng patch:

````text
```luas30-edit
[{"path":"main.lua","find":"old","replace":"new","reason":"Fix logic"}]
```
````

Dạng full file:

````text
```luas30-edit
{"path":"src/module.lua","content":"-- complete file\n","reason":"Add module"}
```
````

Giao thức được parse **tách khỏi** văn bản chat hiển thị.

## AI Changes

Khi có đề xuất sửa file, LuaS30 tạo một tab công cụ bình thường:

```text
AI Changes
```

Tab chứa: danh sách file thay đổi, pane `CURRENT`, pane `PROPOSED`, highlight dòng
thay đổi, thống kê dòng +/−, nút `Reject` và `Apply Code`.

Ở chế độ `Ask before changes`, tab diff tự mở. Các chế độ auto chuẩn bị cùng bộ
thay đổi đã validate nhưng có thể áp dụng mà không cướp focus editor.

Nếu editor đang có nội dung chưa lưu, **chính nội dung đó** được dùng làm bản gốc
để review — tránh việc review âm thầm bỏ qua thứ người dùng đang thấy.

### Apply và backup

File bị ghi đè được copy vào:

```text
<project>/.luas30/ai-backups/<timestamp>/<relative path>
```

trước khi thay thế atomically. File mới không cần backup nguồn. Sau khi áp dụng,
LuaS30 refresh editor, project index và cây Explorer, rồi báo lại danh sách file
đã ghi cho agent.

## Ranh giới project

Sửa code bằng AI bị giới hạn trong thư mục project đang mở. LuaS30 từ chối:

```text
đường dẫn tuyệt đối
../ đi ra ngoài project
.git / .hg / .svn
.venv / venv
node_modules
release
các tên file credential / secret / private-key thông dụng
```

## Tích hợp shell

Lệnh do AI đề xuất chạy trong **đúng Terminal tích hợp** mà người dùng nhìn thấy.
Agent **không** mở được shell thứ hai ẩn. Output thu về bị giới hạn kích thước và
các biến môi trường chứa secret thông dụng được redact trước khi gửi cho provider
từ xa.

Phân loại lệnh:

| Mức | Hành vi |
|---|---|
| `safe` | chỉ đọc, có thể auto-run ở Full access |
| `project` | thao tác trong project, có thể auto-run ở Full access |
| `sensitive` | luôn hỏi |
| `dangerous` | luôn hỏi, kèm xác nhận bổ sung |

## Phiên chat

ChatAI lưu session theo project ở:

```text
%APPDATA%/LuaS30IDE/config/ai_sessions.json
```

Nút Sessions ở header cho phép tạo, resume, đổi tên và xoá hội thoại. Session
đang hoạt động được khôi phục theo project. Kết quả tool nội bộ vẫn được giữ để
model liên tục ngữ cảnh nhưng không hiện lại như tin nhắn chat sau khi resume.

Lệnh cục bộ hỗ trợ:

```text
/new
/clear
/sessions
/resume
/continue
/rename <name>
/help
```

## Công cụ thiết kế UI và asset

Ngoài công cụ đọc/ghi code, agent còn có hai tool thiết kế dùng chung
`design_store` / `lua_export` / `items.COMPONENTS` với UI Designer (không chép lại
schema):

- **`ui_design`** — `catalog`, `screens`, `get` để đọc; `add_screen`,
  `rename_screen`, `delete_screen`, `set_screen`, `add_item`, `update_item`,
  `remove_item`, `export` để ghi.
- **`asset`** — `list` và `make` (sinh PNG, 9 loại).

Ghi dữ liệu chỉ được phép khi `allow_write` bật (tức chính sách sửa khác
`disabled`). Hít dính 4px, kẹp trong 240×320, màu asset mặc định lấy từ
`lua_export` (màu **nội dung**, không phải màu IDE).

Tên tool là **một nguồn duy nhất** (`TOOL_NAMES` trong `ai_agent_protocol.py`) —
dùng cho cả lọc lúc parse lẫn prompt. Thêm tool mà quên khai báo ở đó thì khối
tool bị bỏ **im lặng** (0 action, không báo lỗi).

## Context tự động

ChatAI đọc cấu trúc project, source đang mở/liên quan, `SKILLS.md` / `SKILL.md` /
`PROMPT.md` của project và của engine, và loại trừ các file secret thông dụng như
`.env`, credential, private-key.

> **Bẫy cần biết:** tài liệu hướng dẫn bị cắt theo giới hạn ký tự khi nạp context.
> Nếu nội dung quan trọng nằm ở cuối một file quá dài, nó có thể **không tới được
> model**. Giới hạn hiện tại là 64.000 ký tự mỗi file và 160.000 ký tự tổng, và
> thông báo cắt sẽ ghi rõ số ký tự bị bỏ. Validator
> `tools/validate_ai_context.py` canh việc này.

Xem thêm [`doc/studio/AI_WORKBENCH_V1_1_15_0.md`](../../doc/studio/AI_WORKBENCH_V1_1_15_0.md),
[`doc/studio/AI_AGENT_SHELL_1_14_0.md`](../../doc/studio/AI_AGENT_SHELL_1_14_0.md) và
[`doc/studio/AI_DESIGN_TOOLS.md`](../../doc/studio/AI_DESIGN_TOOLS.md).
