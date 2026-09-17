# AI Design Tools — để AI Agent tạo thiết kế UI và tài nguyên

ChatAI không chỉ đọc mã nguồn: agent còn **tạo** được thiết kế giao diện và tài
nguyên cho game/app, qua hai công cụ `ui_design` và `asset`.

```text
studio/app/services/ai_design_tool_service.py    AIDesignToolService
studio/app/services/ai_agent_protocol.py         tên công cụ + lọc khối ```luas30-tool
studio/app/views/ai_chat_view.py                 _run_tool() — điều phối + gate quyền
```

## Gọi công cụ

Agent gửi đúng một khối `luas30-tool` mỗi lượt, giống `read`/`grep`/`glob`:

```text
```luas30-tool
{"tool":"ui_design","args":{"op":"add_item","screen":"main","type":"button",
 "name":"btn_start","x":64,"y":240,"text":"Bat dau"},"reason":"Add the start button"}
```
```

Tên công cụ hợp lệ nằm ở **một chỗ duy nhất**: `READONLY_TOOL_NAMES` /
`DESIGN_TOOL_NAMES` trong `ai_agent_protocol.py`. Bước lọc lúc parse và bước
quảng bá trong prompt đều dùng chung hằng số đó — thêm công cụ mới thì thêm ở
đó, đừng sửa hai nơi.

## `ui_design` — thiết kế giao diện

Thao tác trên đúng `.luas30/ui_design.json` mà UI Designer dùng.

Đọc (chạy được ở mọi access mode):

| op | Tham số | Trả về |
|---|---|---|
| `catalog` | — | Mọi loại thành phần kèm kích thước mặc định, khung màn hình, lưới, danh sách op |
| `screens` | — | Danh sách màn hình + số thành phần |
| `get` | `screen` | Toàn bộ thành phần của một màn hình (JSON) |

Ghi (cần quyền sửa):

| op | Tham số | Ghi chú |
|---|---|---|
| `add_screen` | `id`, `name` | `id` được làm sạch thành ID hợp lệ |
| `rename_screen` | `screen`, `to` | Không đổi tên được màn hình `main` |
| `delete_screen` | `screen` | Không xoá được màn hình `main` |
| `set_screen` | `screen`, `items` | Thay toàn bộ thành phần của màn hình |
| `add_item` | `screen`, `type`, `name`, `x`, `y`, `w`, `h`, `text`, `src`, `fill` | Thêm một thành phần |
| `update_item` | `screen`, `name`, `fields` | Sửa một số trường của thành phần có sẵn |
| `remove_item` | `screen`, `name` | Xoá một thành phần |
| `export` | — | Sinh `ui_design.lua` để game `require()` |

Các loại thành phần (`type`) là **đúng danh mục của Designer** — `button`,
`label`, `checkbox`, `textbox`, `image`, `progress`, `slider`, `switch`,
`panel`, `card`, `row`, `column`, `divider`, `spacer`, `canvas`, `sprite`,
`tile`, `rect`. Gọi `catalog` để lấy kích thước mặc định; danh mục này đọc
trực tiếp từ `items.COMPONENTS` nên thêm thành phần vào Designer là công cụ tự
biết, không phải sửa gì.

### Bảo đảm khi ghi

- **Toạ độ snap về lưới 4px** và **kẹp trong khung 240×320** — agent không thể
  đặt thành phần ra ngoài màn hình.
- **Tên luôn hợp lệ**: `"btn start"` → `btn_start`; không đặt tên thì tự sinh
  theo quy ước Designer (`button_1`, `label_2`…); trùng tên thì thêm hậu tố.
- **Loại lạ bị từ chối** kèm danh sách loại hợp lệ.
- Hình dạng item đi qua `design_store.coerce_item()` — cùng một định nghĩa với
  thứ Designer đọc, nên tệp agent ghi ra không lệch dần theo thời gian.

## `asset` — tài nguyên

| op | Tham số | Ghi chú |
|---|---|---|
| `list` | — | Ảnh đang có trong `assets/`, kèm thư mục đích hợp lệ và các kind |
| `make` | `kind`, `name`, `target`, `width`, `height`, `color`, `color2`, `radius`, `text`, `font_size`, `value`, `cell`, `alpha` | Sinh một PNG thật |

Các `kind`:

| kind | Thư mục mặc định | Kích thước mặc định | Dùng cho |
|---|---|---|---|
| `solid` | `ui` | 32×32 | Mảng màu phẳng |
| `gradient` | `background` | 240×320 | Nền chuyển sắc dọc |
| `checker` | `tiles` | 64×64 | Caro (thử lát / kiểm trong suốt) |
| `grid` | `tiles` | 64×64 | Lưới ô, nền trong suốt |
| `button` | `ui` | 78×24 | Nút bo góc + viền + chữ |
| `panel` | `ui` | 140×90 | Khung nền bo góc |
| `frame` | `ui` | 120×80 | Khung **rỗng** (chỉ viền) |
| `bar` | `ui` | 110×12 | Thanh tiến trình (track + fill theo `value`) |
| `label` | `ui` | 96×20 | Chữ trên nền trong suốt |

`target` phải là một trong `assets`, `ui`, `sprites`, `background`, `tiles`,
`maps` — đúng thư mục mà `asset_import.IMAGE_TARGETS` quy định, nên tài nguyên
sinh ra nằm ngay chỗ palette của Designer quét tới.

**Màu mặc định lấy từ `lua_export`** (bảng màu NỘI DUNG game), không phải accent
chrome của IDE. Viền mặc định suy ra từ chính màu tô (đậm hơn) nên tài nguyên
luôn cùng họ màu; truyền `color`/`color2` để ghi đè.

Tên tệp được làm sạch (`safe_asset_name`) nên không thể ghi ra ngoài project.

## Quyền: đọc luôn được, ghi phải được phép

`AIDesignToolService.execute(..., allow_write=...)`. ChatAI truyền
`allow_write = self._edit_policy() != "disabled"`, tức thao tác ghi của công cụ
thiết kế đi **cùng một cửa** với code edit:

| Access mode | Đọc (`catalog`/`screens`/`get`/`list`) | Ghi (`add_item`, `make`, `export`…) |
|---|---|---|
| Ask before changes | có | có |
| Edit automatically | có | có |
| Plan mode | có | **không** |
| Code edits tắt trong Settings | có | **không** |

Khi bị chặn, công cụ trả lỗi rõ ràng (`Design changes are not permitted in the
current access mode…`) và prompt cũng không quảng bá thao tác ghi, nên model
không đề xuất việc nó không được làm.

## Kiểm chứng

```text
QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
  py -3.12 -u tools/validate_ai_design_tools.py
```

Validator dựng một project tạm rồi để agent đi **đúng đường thật** (khối
`luas30-tool` → `parse_agent_response` → service), và kiểm cả những thứ dễ hỏng
âm thầm:

- `catalog` liệt kê đủ mọi thành phần của Designer;
- snap lưới, kẹp khung, làm sạch tên, chống trùng tên;
- `main` không xoá được; loại thành phần lạ bị từ chối;
- **ảnh sinh ra là PNG thật**: đọc lại bằng `QImage`, đúng kích thước, `solid`
  đúng màu, **`frame` rỗng** (alpha tâm = 0), có chữ thì khác ảnh không chữ,
  `gradient` đổi màu theo chiều dọc;
- `target` lạ bị từ chối và **không ghi được ra ngoài project**;
- `ui_design.lua` sinh ra biên dịch được bằng `luac -p` và không lọt màu chrome;
- `DesignStore` của Designer đọc lại được tệp agent ghi.

`tools/studio_theme_check.py` cũng canh việc này: mọi hex trong `studio/**/*.py`
phải thuộc `palette.py`, trừ danh sách `ALLOWLIST` có ghi lý do.
