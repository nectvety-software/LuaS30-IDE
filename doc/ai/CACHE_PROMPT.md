# PROMPT.md — Files in cache / thư mục dữ liệu cho mọi project VXP (định dạng `@App`)

> Dùng như **prompt hệ thống** khi AI viết/sửa **mọi project** MRE / LuaS30 / VXP trên
> Nokia S30+ (MTK6260…), không riêng Pixel Editor hay dibo.
>
> Chuẩn này lấy từ project **dibo** (`E:\@dibo\world.sav`) và **VXP Pixel Editor**
> (`e:\@Pixl\autosave.vpe`).
>
> **Vị trí**: `D:\MRE\LuaS30-IDE\doc\ai\CACHE_PROMPT.md`
> — bổ sung cho `SKILL.md` / `PROMPT.md` / `MEMORY_PROMPT.md`.
> Đọc kèm `CACHE_SKILL.md`. Cập nhật: 2026.

---

## 0. Bất biến (vi phạm = phải sửa)

1. **Mọi file runtime ghi ra máy** phải nằm trong **một thư mục app** dạng:
   `<ổ>:\@<AppName>\`
   - Ví dụ đúng: `E:\@dibo\world.sav`, `e:\@Pixl\autosave.vpe`, `C:\@MyGame\cfg.ini`
   - Ví dụ sai: `world.sav` ở gốc ổ, `temp\foo`, `C:\Users\...\Desktop\x`, path tuyệt đối host PC.
2. **Tên thư mục** = `@` + tên app **viết liền, không dấu cách** (ASCII):
   `dibo`, `Pixl`, `MyGame`. Tên **không được đổi** giữa các phiên bản (migrate nếu bắt buộc).
3. **Ổ đĩa**: dò theo thứ tự (xem `CACHE_SKILL.md`):
   removable → system → fallback `E`.
   Không hard-code duy nhất `C:\`.
4. **Mọi path sinh ra** phải thử **cả `\\` và `/`**; cuối cùng là **flat fallback**
   (file cùng cấp VXP: `PixlCreate_autosave.vpe`).
5. **Không ghi cache vào `build/`, `.freebuff/`, `release/`** (MEMORY_PROMPT §1.10).
6. Cache **không** chứa secret/pin/key. Chỉ save game, config, export tạm, thumbnail.
7. Khi `engine.has_files == false` → không crash; lặng lẽ skip ghi/đọc cache.

---

## 1. Files in cache — danh mục chuẩn

Mọi project **nên** dùng đúng slot tên file dưới đây (đổi nội dung, không đổi tên nếu có thể):

| File trong `@App\` | Dùng cho | Ghi khi | Xóa khi |
|--------------------|----------|---------|---------|
| `autosave.vpe` / `world.sav` / `save.dat` | Trạng thái đang làm / save game | pause, quit, checkpoint | New game / Clear cache |
| `settings.ini` | Theme, volume, tùy chọn, last_* | khi đổi setting | Reset settings |
| `cache.idx` / `gallery.idx` | Index list (ROM, ảnh, level…) | khi scan thêm/sửa | Rescan full |
| `thumb_<id>.raw` | Thumbnail/preview đã decode | khi cần UI | khi evict / clear |
| `tmp_<op>.bin` | Buffer export/encode trung gian | trong encode | **ngay sau khi encode xong** |
| `export_<name>.bmp` (hoặc `.vpe`, `.png`) | Export người dùng | khi user Export | user xóa |
| `storage.ver` | Marker thư mục (1 dòng version) | khi `ensure_storage` | hiếm khi |
| `last.err` (tuỳ chọn) | Log lỗi ngắn (≤ 2KB) | khi lỗi I/O | khi mở app OK |

**Quy tắc slot:**

- **1 autosave duy nhất** — ghi đè (không xoay 10 file autosave).
- **tmp_*** phải được **xóa trong cùng hàm** encode/export (try/finally equivalent).
- **thumb_*** có trần số lượng (vd 16); LRU khi vượt — xóa file cũ nhất.
- **export_*** do user đặt tên; không ghi đè khi chưa confirm.
- Tên file: **ASCII**, `A-Za-z0-9._-`, tối đa ~24 ký tự base (ngoài prefix `tmp_`/`thumb_`/`export_`).

---

## 2. API bắt buộc (wrapper trong `src/platform.lua` hoặc `src/cache.lua`)

Phải có, không bịa API ngoài `engine.file_*`:

```lua
Cache.dirs()           -- { "e:\\@App", "E:\\@App", "@App" }
Cache.path(name)       -- 3 ứng viên path cho name
Cache.ensure_dir()     -- mkdir mọi ứng viên
Cache.write(name, data)
Cache.read(name)
Cache.delete(name)
Cache.clear_pattern(prefix)  -- tmp_/thumb_ nếu cần
App.cache_autosave()   -- gọi từ pause/quit
App.cache_autoload()   -- Resume / Continue
```

Gọi `Cache.ensure_dir()` từ `engine.load` / `ensure_storage` **một lần**.

---

## 3. Lifecycle bắt buộc

| Sự kiện | Hành động |
|---------|-----------|
| `load` | `ensure_dir()` + ghi `storage.ver` + (tuỳ chọn) autoload |
| đổi setting | `settings.ini` |
| pause / soft-exit / quit | **autosave** state |
| user chọn Resume | `cache_autoload` |
| Clear cache (menu) | xóa `autosave` + `tmp_*` + `thumb_*` (giữ `export_*` trừ khi user confirm) |
| encode xong | xóa `tmp_*` |
| OOM guard trước heavy | `collectgarbage("collect")` — xem MEMORY_PROMPT |

---

## 4. Host / emulator (Windows)

Emulator/host thường **map** `E:\@App\file` thành file cùng thư mục project:

```text
@App\file.ext          ← symlink/copy dạng @App trên "ổ" hiện tại
E__@App_file.ext       ← dạng flatten như dibo: E__@dibo_world.sav
```

- Tool build/preview **được phép** đọc/ghi hai dạng trên để debug.
- App **không** hard-code path `C:\Users\...`.
- Không commit `.sav` lớn; `.gitignore` nếu repo có git.

---

## 5. Câu trả lời khi AI sinh code

1. Liệt kê **Files in cache** dự kiến (bảng slot ở §1).
2. Ghi rõ **`@<AppName>`** và 3 path ứng viên.
3. Trích wrapper `Cache.*` đầy đủ trong `platform.lua`/`cache.lua`.
4. Nối **pause/quit → autosave**, **Resume → autoload**, **Clear cache**.
5. TODO: thiếu `engine.file_delete`/mkdir → fallback + ghi chú.

---

## 6. Nghiệm thu

- [ ] Mọi file runtime nằm dưới `@App\` (hoặc flat fallback), không rác ngoài root.
- [ ] Có `storage.ver` sau `load`.
- [ ] Pause/quit ghi autosave; Resume đọc lại được.
- [ ] `tmp_*` không còn sau khi export.
- [ ] Clear cache hoạt động (không xóa export user nếu chưa confirm).
- [ ] Chạy được khi `has_files == false` (không crash).
- [ ] Path thử `\\`, `/`, và flat fallback.
