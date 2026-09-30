---
name: vpe-assets
description: Do hoa game/app LuaS30 tu THU VIEN MAU CO SAN .vpe/.vpea cua VPEPixel (Documents\VPE Pixel) -- inspect/atlas/tileset/anim/header --lang c, RGB565 blit + colorkey, nearest + integer scale, verify bang build + emulator
---

# VPE assets cho LuaS30 — dùng mẫu VPEPixel, không vẽ lại từ đầu

Nguồn đồ họa chuẩn là **VPEPixel**
(`https://github.com/nectvety-software/VPEPixel`, nhánh `master`): editor
`vpx_editor`, CLI stdlib-only `scripts/vpe_tool.py`, và **thư viện asset vẽ
sẵn** xuất ra `Documents\VPE Pixel` (nền ~285 asset gốc: 9 title, 172
sprite/FX, 19 texture, 85 tile; trên máy này đã có 573 `.vpe` + 121 `.vpea`,
gồm cả bộ theo dự án: `PuzzleField/`, `fnynn/`, `fnynn_map/`, `summitecho/`,
`sprite/`, `texture/`, `tile/`, `titleset/`, `exports/`).

QUY TẮC SỐ 1: khi cần sprite/tile/texture/title/animation, **truy mẫu trước
khi vẽ**: `glob Documents\VPE Pixel\**\*.vpe` / `*.vpea` theo từ khóa
(player, heart, tile, boom, title…), chọn file khớp phong cách rồi tích hợp.
Chỉ sinh mẫu mới bằng VPEPixel/`make_samples.py` khi thư viện thật sự thiếu.

Copy `scripts/vpe_tool.py` (repo VPEPixel) vào project khi cần tool; KHÔNG
import `vpx_editor` chéo repo.

## Format phải nhớ

- `.vpe` = **VPE565**: header 16 byte — magic `VPE565` + u16 ver(=1) +
  u16 w + u16 h + u32 payload — rồi đúng `w*h*2` byte RGB565 little-endian,
  row-major. Sai kích thước là file hỏng, không phải biến thể. Max 640×640.
- `.vpea` = **VPEA01** (animation nhiều frame): header 20 byte — magic
  `VPEA01` + u16 ver(=1) + u16 w + u16 h + u16 frame_count + u16
  delay_ms/frame + u8 loop(0|1) + 3 byte reserved — tiếp đó là
  `frame_count` chunk VPE565 HOÀN CHỈNH (mỗi chunk mang cả header 16 byte
  riêng). Tổng file = `20 + n*(16+w*h*2)`. Tối đa 256 frame.
- RGB565 **không có alpha**. Trắng `0xFFFF` chỉ là quy ước trong suốt của
  editor — phía engine phải opt-in (`--transparent-white` / colorkey),
  không bao giờ mặc định trong suốt (kẻo ăn mất title/texture trắng).

## Tooling (stdlib-only, chạy mọi nơi)

```bat
python vpe_tool.py inspect *.vpe *.vpea         &rem LUÔN chạy trước; truyền FILE/glob, KHÔNG truyền thư mục (lỗi Permission denied)
python vpe_tool.py atlas --dir <dir> --out atlas.png --json atlas.json
python vpe_tool.py tileset --dir <dir> --out map.png --json map.json --size 16
python vpe_tool.py batch-export <dir> --out <assets-dir> --scale 2
python vpe_tool.py header FILE --lang c --out sprite.h
python vpe_tool.py png FILE --out preview.png --scale 4
```

- `inspect` trước mọi giả định kích thước; sai dims gây lệch hàng trông như
  lỗi palette.
- `atlas`: frame xếp theo chiều cao giảm dần + gutter 1px, lookup theo
  `filename` trừ `.vpe`. `tileset` từ chối tile lệch size (lọc `--size`).
- Mọi lệnh in một dòng/file và `ERROR <loại>: <msg>` khi lỗi.
- Recipe nạp asset cho Godot 4 / Pygame / HTML canvas / Unity C# / **C-MRE**
  nằm trong docs của VPEPixel (`docs/ASSET_TAXONOMY.md`).

## Đưa mẫu vào project LuaS30 (engine.*)

1. **Chọn mẫu** từ `Documents\VPE Pixel` (hoặc `git clone` VPEPixel rồi chạy
   `make_samples.py`) → convert/copy **vào project** (`assets/` hoặc
   `build/`), không bao giờ ghi ngược vào `Documents\VPE Pixel`.
2. Framebuffer máy đã là RGB565: với `header --lang c`, blit mảng `u16`
   trực tiếp + colorkey, đừng decode rồi encode lại.
3. Với atlas PNG + JSON: nạp một lần qua `engine.image` /
   `engine.image_region` (kiểm tra `engine.has_images` trước, fallback
   procedural `rect`/`text` khi thiếu như Keypad prompt mục image-optional).
4. `.vpea`: hoặc `png`/`atlas` từng frame rồi phát lần lượt theo
   `delay_ms` (đọc từ header, `loop` quy định lặp lại hay dừng ở frame cuối), hoặc `batch-export` ra PNG
   strip; giữ cùng timer 15 FPS của engine, không `time.sleep` trong draw.
5. Mọi nơi: nearest filtering, integer scale (1/2/4), không linear lên atlas
   packed (lem frame kề), không scale lẻ (nứt seam).
6. RAM 1 MB: atlas chung + cache màu, không nạp lại ảnh mỗi frame; giữ tổng
   asset dưới ngưỡng heap của profile (Nokia 225: 1024 KB).

## Definition of done (chứng minh bằng chạy, không nói suông)

- `inspect`: số file + dims khớp kỳ vọng, không dòng ERROR; `.vpea` có
  `len == 20 + n*(16+w*h*2)`.
- Atlas PNG trên đĩa đúng WxH JSON báo; frame count = file count.
- Round-trip: decode một frame rồi encode lại VPE565 — byte-identical file gốc.
- Nhìn thật atlas/PNG trên nền tối trước khi kết luận đúng.
- Trong engine: 1 sprite native scale + 1 tilemap + (nếu có) animation
  `.vpea` chạy vòng. Build VXP (`tools/build.py`) PASS rồi smoke trên
  emulator.
