# SKILL.md — Kỹ năng Files in cache (`@App` folder) cho VXP / MRE

> **Vị trí**: `D:\MRE\LuaS30-IDE\doc\ai\CACHE_SKILL.md`
> Dùng kèm `CACHE_PROMPT.md`. Bổ sung `MEMORY_*.md` — file này chỉ nói **cache/data dir**.
>
> Mẫu gốc: **dibo** `res.c` (`@dibo`, `E:\@dibo\world.sav`) và
> **VXP Pixel Editor** `30_platform.lua` (`@Pixl`, `e:\@Pixl\autosave.vpe`).

---

## 1. Cấu trúc thư mục chuẩn

```text
<drive>:\@<AppName>\
  storage.ver          -- marker, 1 dòng
  autosave.vpe         -- hoặc world.sav / save.dat
  settings.ini
  cache.idx
  thumb_00.raw         -- trần N (vd 16)
  tmp_bmp54.bin        -- xóa sau encode
  export_mypic.bmp     -- do user đặt
  last.err             -- optional, ≤ 2KB
```

Host PC / emulator (project folder):

```text
@Pixl\storage.ver
E__@Pixl_autosave.vpe     -- flatten kiểu dibo: E__@dibo_world.sav
```

---

## 2. Chọn ổ đĩa (copy logic dibo)

```lua
-- dibo res_prepare_storage(): removable → system → 'E'
local function pick_drives()
  local out, n = {}, 0
  -- engine.* hiện chưa export get_removable_driver — TODO wrapper nếu firmware có
  -- Thử theo thứ tự cố định, mỗi path thử mkdir:
  n = n + 1; out[n] = "e:"
  n = n + 1; out[n] = "E:"
  n = n + 1; out[n] = "c:"
  n = n + 1; out[n] = "C:"
  return out
end
```

Với LuaS30 `engine.file_*` (không có drive API trong API.md):

```lua
local APP = "@Pixl"
local CAND = {
  "e:\\" .. APP,
  "E:\\" .. APP,
  APP,                 -- relative cùng VXP
}
```

**Không** hard-code `C:\Users\<name>\...`.

---

## 3. Wrapper `Cache` (đầy đủ, Lua 5.1, không patterns)

```lua
-- src/cache.lua (hoặc chèn vào platform.lua)
VXPPE.Cache = VXPPE.Cache or {}
local K = VXPPE.Cache
local C = VXPPE.Config
local P = VXPPE.Platform

function K.dirs()
  return {
    C.CACHE_DIR or "e:\\@App",
    C.CACHE_DIR_ALT or "E:\\@App",
    C.CACHE_DIR_FLAT or "@App",
  }
end

function K.path(name)
  name = tostring(name or "cache.bin")
  local d = K.dirs()
  return d[1] .. "\\" .. name, d[2] .. "\\" .. name, d[3] .. "/" .. name
end

function K.ensure_dir()
  local d, ok = K.dirs(), false
  for i = 1, #d do
    if P.make_dir(d[i]) then ok = true end
  end
  return ok
end

function K.write(name, data)
  local a, b, c = K.path(name)
  local ok, actual = P.write_storage_file(a, data, b, nil)
  if ok then return true, actual end
  ok, actual = P.write_storage_file(c, data, (C.STORAGE_FALLBACK_PREFIX or "App_") .. name, nil)
  return ok, actual
end

function K.read(name)
  local a, b, c = K.path(name)
  local blob = P.read_file(a) or P.read_file(b) or P.read_file(c)
  if not blob then blob = P.read_file((C.STORAGE_FALLBACK_PREFIX or "App_") .. name) end
  return blob
end

function K.delete(name)
  local a, b, c = K.path(name)
  if not P._file_delete then return false end
  pcall(P._file_delete, a)
  pcall(P._file_delete, b)
  pcall(P._file_delete, c)
  return true
end
```

`P.write_storage_file` **bắt buộc** có: thử `\\` rồi `/`, verify size/magic, flat fallback.

---

## 4. Slot file — luật cứng

### 4.1 `autosave` / `world.sav` / `save.dat`

```lua
function App.cache_autosave()
  -- encode state → K.write("autosave.vpe", blob)
end
function App.cache_autoload()
  -- blob = K.read("autosave.vpe"); decode; nếu fail → "no-cache"
end
```

- **Ghi đè 1 file** (không vòng xoay nhiều backup trên máy 1MB).
- Gọi ở: `pause`, `quit`, checkpoint (đổi map / sau trận).
- Encode **nhỏ** (RLE / delta / VPE565) — dibo world 14400 ô ≈ 3KB.

### 4.2 `settings.ini`

```ini
theme=dark
lang=vi
paint_on_move=1
last_tab=FAV
sort=name
```

- Ghi khi user OK ở menu Settings (không mỗi frame).
- Khóa = ASCII nhỏ; value 1 dòng.

### 4.3 `cache.idx` / `gallery.idx`

- Một dòng / record, tab-separated, **không regex** khi parse (tự split `\t`).
- Giới hạn item (vd 16–48) theo MEMORY.

### 4.4 `thumb_*.raw`

- Header 4 byte: `u16le w`, `u16le h` + RGB565 payload.
- **Trần** `MAX_THUMBS = 16`; khi thêm mới mà đủ → `delete` file cũ nhất (theo thứ tự sort tên).
- Chỉ load thumb của **dòng đang chọn**; `K.delete` khi evict.

### 4.5 `tmp_*`

```lua
local tmp = "tmp_bmp54.bin"
K.write(tmp, blob)
local ok = real_export(blob)   -- hoặc write export_*
K.delete(tmp)                  -- LUÔN chạy sau encode (cả fail)
```

- Không giữ tmp sau khi ra khỏi hàm encode.
- MEMORY_PROMPT: tmp **không** nằm trong `.freebuff`.

### 4.6 `export_*`

- Tên do user chọn (sanitize ASCII).
- **Confirm overwrite** nếu đã tồn tại.
- Không auto-delete; chỉ user / Clear cache có confirm.

### 4.7 `storage.ver`

```lua
K.write("storage.ver", "<AppName> cache v1\n")
```

---

## 5. Lifecycle checklist (mọi project)

| Hook | Gọi |
|------|-----|
| `engine.load` | `K.ensure_dir()` + `storage.ver` |
| pause / quit | `App.cache_autosave()` |
| Resume / Continue | `App.cache_autoload()` |
| Settings save | `settings.ini` |
| Export xong | `K.delete("tmp_...")` |
| Menu Clear cache | xóa autosave + tmp_* + thumb_* (giữ export_* trừ confirm) |

---

## 6. Host / emulator

| Trên máy | Host (project folder) |
|----------|------------------------|
| `E:\@Pixl\autosave.vpe` | `@Pixl\autosave.vpe` **hoặc** `E__@Pixl_autosave.vpe` |
| `E:\@dibo\world.sav` | `E__@dibo_world.sav` |

- Script preview/test **được** đọc host path để assert round-trip.
- App chỉ dùng path **thiết bị** (`e:\@App\...`).

---

## 7. OOM / an toàn (liên kết MEMORY_PROMPT)

- Không `table`/`..` trong `draw`.
- Encode/decode cache **một buffer**, gán `blob = nil` + `collectgarbage("collect")` sau heavy.
- `ensure_dir` + write trong `pcall`/API boundary — fail → toast/`last.err`, **không** crash.
- Trần thumb/idx theo heap soft limit.

---

## 8. Checklist nghiệm thu

- [ ] Tên `@App` ASCII, cố định giữa version.
- [ ] Ứng viên `e:\`, `E:\`, relative + flat `App_*`.
- [ ] Bảng Files in cache khớp §CACHE_PROMPT (autosave, settings, idx, thumb, tmp, export, storage.ver).
- [ ] `tmp_*` xóa sau encode.
- [ ] Autosave pause/quit; autoload Resume.
- [ ] Clear cache không oan export user (trừ khi confirm).
- [ ] `has_files == false` → skip, không crash.
- [ ] Smoke-test **máy thật** / MREmu (emulator IDE chưa đủ).

---

## 9. Ví dụ khai báo config

```lua
C.DATA_FOLDER = "Pixl"          -- sau @
C.CACHE_DIR = "e:\\@Pixl"
C.CACHE_DIR_ALT = "E:\\@Pixl"
C.CACHE_DIR_FLAT = "@Pixl"
C.CACHE_AUTOSAVE = "autosave.vpe"
C.CACHE_SETTINGS = "settings.ini"
C.CACHE_EXPORT = "pixel_art.bmp"
C.STORAGE_FALLBACK_PREFIX = "PixlCreate_"
```
