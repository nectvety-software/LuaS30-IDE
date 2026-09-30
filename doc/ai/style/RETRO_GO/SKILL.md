# SKILL.md — Kỹ năng UI Launcher phong cách Retro-Go (LuaS30 / MRE)

> **Vị trí**: `D:\MRE\LuaS30-IDE\doc\ai\RETRO_GO_SKILL.md`
> Dùng kèm `RETRO_GO_PROMPT.md`. Bổ sung cho `SKILL.md` / `MEMORY_*.md` —
> file này chỉ nói **UI + navigation kiểu Retro-Go**, không thay API contract.
>
> Mục tiêu thị giác: giống [Retro-Go](https://github.com/ducalex/retro-go) trên
> handheld có D-pad — **phẳng, tối, accent theo hệ máy, mật độ cao, không blur/gradient**.

---

## 1. Design tokens (`src/theme.lua`)

Lưu màu là **RGB565 number** (đã pack sẵn). **Không** dùng `{r,g,b}` table trong draw.

```lua
-- theme.lua (trích — đầy đủ xem project mẫu)
VXPPE.Theme = {}
local T = VXPPE.Theme
T.SCREEN_W = (engine and engine.W) or 240
T.SCREEN_H = (engine and engine.H) or 320
T.HEADER_H, T.TAB_H, T.STATUS_H, T.LIST_ROW_H = 24, 22, 18, 20
T.SCROLL_W = 3

T.DARK = {
  name = "DARK",
  bg = 0x0841,       -- nền app
  panel = 0x1082,    -- list row
  panel2 = 0x1904,   -- info bar / track
  panel3 = 0x2945,   -- toast
  border = 0x39E7,
  text = 0xEF7D,
  muted = 0x8C51,
  accent = 0x36DF,   -- tab active / selection bar
  select_bg = 0x2148,
  header_bg = 0x0C25,
  status_bg = 0x0A12,
  tab_bg = 0x10A3,
  cursor = 0xFFE0,
  ok = 0x5EE9, danger = 0xDC8D, warn = 0xFD20,
}
T.LIGHT = { name = "LIGHT", bg = 0xEBEF, panel = 0xFFFF, --[[ ... ]] }
T.current = T.DARK
function T.cycle() -- DARK <-> LIGHT
  if T.current == T.DARK then T.current = T.LIGHT else T.current = T.DARK end
  return T.current.name
end
```

**Accent theo hệ máy** (tab được chọn):

| Tab | Accent gợi ý | RGB565 |
|-----|--------------|--------|
| Favorites | gold | `0xFD20` |
| Recent | cyan | `0x36DF` |
| NES | red | `0xF800` |
| SNES | purple | `0x8A5F` |
| GB | pea green | `0x8C80` |
| GBC | teal | `0x07FF` |
| SMS / GG | blue | `0x001F` |
| PCE | orange | `0xFD20` |
| Genesis | black/silver | `0x8C51` |
| Settings | gray | `0x39E7` |

---

## 2. Chrome bắt buộc (thứ tự vẽ mỗi frame)

```text
clear(bg) → header → tab_bar → info_line → list + scrollbar → status_bar → (toast/popup)
```

### 2.1 Header (~24px)

```lua
function UI.header(title, right)
  local W, h = T.SCREEN_W, T.HEADER_H
  engine.rect(0, 0, W, h, C.header_bg)
  engine.rect(0, h - 1, W, 1, C.border)
  engine.text(4, 7, title, C.accent)          -- "Retro-Go" hoặc logo text
  engine.text(W - 8 - engine.text_width(right), 7, right, C.muted) -- clock/bat
end
```

### 2.2 Tab bar ngang (~22px)

- N tab chia đều `cell = floor(W / N)` (nếu `N` lớn: tab window 4–5 tab + fade số).
- Tab **active**: `select_bg` + gạch dưới `accent` 2px; text `accent`.
- Tab thường: `muted`. Chia tab bằng vạch `border` 1px.
- Icon: `engine.image_region` 12×12 nếu có atlas; nếu không — ô màu 8×8 + nhãn.

```lua
function UI.tab_bar(tabs, selected, y)
  local W, h = T.SCREEN_W, T.TAB_H
  engine.rect(0, y, W, h, C.tab_bg)
  engine.rect(0, y + h - 1, W, 1, C.border)
  local n, cell = #tabs, math.floor(W / #tabs)
  for i = 1, n do
    local x = (i - 1) * cell
    local on = (i == selected)
    if on then
      engine.rect(x, y, cell, h - 1, C.select_bg)
      engine.rect(x, y + h - 2, cell, 2, tabs[i].color or C.accent)
      engine.text(x + 3, y + 6, tabs[i].short, C.accent)
    else
      engine.text(x + 3, y + 6, tabs[i].short, C.muted)
    end
  end
end
```

### 2.3 List + scrollbar

```lua
function UI.list_row(y, name, selected, sub, accent)
  local W, rh = T.SCREEN_W, T.LIST_ROW_H
  local w = W - T.SCROLL_W - 8
  engine.rect(4, y, w, rh, selected and C.select_bg or C.panel)
  if selected then engine.rect(4, y, 2, rh, accent or C.accent) end
  engine.text(10, y + 5, name, C.text)
  if sub then engine.text(10, y + 5, sub, C.muted) end -- chỉ khi row cao ≥ 32
end

function UI.scrollbar(y, h, total, visible, index)
  local x, sw = T.SCREEN_W - T.SCROLL_W, T.SCROLL_W
  engine.rect(x, y, sw, h, C.panel2)
  if total <= visible then engine.rect(x, y, sw, h, C.accent); return end
  local thumb = math.floor(h * visible / total)
  if thumb < 8 then thumb = 8 end
  local off = math.floor((h - thumb) * (index - 1) / math.max(1, total - visible))
  engine.rect(x, y + off, sw, thumb, C.accent)
end
```

### 2.4 Status bar (~18px)

```lua
function UI.status_bar(hints, page)
  local y = T.SCREEN_H - T.STATUS_H
  engine.rect(0, y, T.SCREEN_W, T.STATUS_H, C.status_bg)
  engine.rect(0, y, T.SCREEN_W, 1, C.border)
  engine.text(4, y + 4, hints, C.muted)  -- "OK:Open  Menu:Opt"
  engine.text(T.SCREEN_W - 8 - engine.text_width(page), y + 4, page, C.muted)
end
```

Chuỗi hint **hằng số mô-đun** — không `..` trong draw.

### 2.5 Popup / Toast

- Confirm: khung `panel` + viền `accent`, `OK` = `ok`, `Cancel` = `danger`.
- Toast: `panel3` + text `text`, tự ẩn sau ~1.2s (`tick_ms`), không timer table mỗi frame.

---

## 3. Input map (`src/platform.lua`)

```lua
KEY_MAP = {
  up="UP", down="DOWN", left="LEFT", right="RIGHT",
  ok="OK", softleft="LSK", softright="RSK", back="RSK", clear="RSK",
  ["1"]="PGUP", ["3"]="PGDN", ["4"]="JMP-", ["6"]="JMP+",
  ["5"]="OK", ["2"]="UP", ["8"]="DOWN", ["4"]="LEFT", ["6"]="RIGHT",
  ["*"]="FAV", ["#"]="SORT", ["0"]="0",
}
-- 2/8/4/6 là backup D-pad theo Keypad.md
```

**Retro-Go actions** (trong `menu.lua` / list controller):

| Action | Keys | Behavior |
|--------|------|----------|
| `UP`/`DOWN` | up/down/2/8 | move selection; hold = accelerate |
| `TAB±` | left/right | cycle tabs wrap |
| `OPEN` | ok/5 | launch ROM |
| `BACK` | softright/back | pop menu / exit list |
| `MENU` | softleft | Options |
| `PGUP`/`PGDN` | 1/3 | page ±1 |
| `JMP±` | 4/6 | next/prev first-letter |
| `FAV` | * | toggle favorite + toast |
| `SORT` | # | name → path → size |

Hold-repeat: `CURSOR_REPEAT_DELAY_MS=130`, interval 70→42→26 ms (giống pixel editor).

---

## 4. Library / tabs (`tabs.lua`, `library.lua`)

```lua
Tabs = {
  { id="FAV",  label="Favorites", short="FAV", exts=nil,        color=0xFD20 },
  { id="HIST", label="Recent",    short="RCT", exts=nil,        color=0x36DF },
  { id="NES",  label="NES",       short="NES", exts={".nes"},   color=0xF800 },
  { id="GB",   label="Game Boy",  short="GB",  exts={".gb",".gbc"}, color=0x8C80 },
  -- ...
}
```

- `library.scan(tab)` quét **một tab** mỗi lần (không all-at-once).
- Entry gọn: `{ name=, path=, size=, letter= }` — **không** giữ handle file.
- `pretty_name(path)`: basename, bỏ extension, bỏ `(`…`)` `[`…`]`, trim.
- Lazy: cover chỉ khi `selected` đổi; `library.drop_cover()` khi đổi tab.
- `Hide empty tabs`: nếu `#items==0` thì không đưa tab vào `visible_tabs`.

---

## 5. Storage (`storage.lua`)

```text
favorites.txt   mỗi dòng: <system>\t<path>
recent.txt      tối đa 20, mới lên đầu
settings.ini    theme=dark|light, hide_empty=0|1, preview=cover|save|both|none,
                scroll=center|paging, sort=name|path|size, last_tab=, last_rom=
```

- Chỉ ghi khi `engine.has_files`. Thất bại → toast, **không crash**.
- Ghi ở điểm an toàn (đóng menu, thoát app) — không ghi mỗi frame.

---

## 6. Mở game

```lua
function launch(rom, system)
  -- TODO: thiếu API loader trên engine.* — hook chờ firmware/SDK
  if type(engine.launch) == "function" then
    engine.launch(rom, system)
    return
  end
  state = "LAUNCHING"
  pending = { rom = rom, system = system }
  -- draw "Launching <pretty name>" rồi chờ
end
```

---

## 7. RAM / OOM (bắt buộc — xem MEMORY_PROMPT)

| Cấm | Làm thay |
|-----|----------|
| `{...}` trong `draw`/`update` | hằng số / scratch table dùng lại |
| `s = s .. x` trong `draw` | memo có trần / chuỗi tĩnh |
| nạp cover mọi dòng | chỉ selected |
| quét mọi hệ một lần | scan theo tab |
| comment đầy trong production | minify khi bundle |

Ngân sách: heap sau boot ≤ ~250 KB; playing ≤ ~430 KB; rác/khung ổn định ≤ 32 B.

---

## 8. Checklist nghiệm thu UI

- [ ] Header + tab + list + scrollbar + status bar **đúng tỷ lệ** trên 240×320.
- [ ] Tab active đổi accent; Left/Right wrap.
- [ ] Selection highlight + scrollbar khớp `index/total`.
- [ ] Hold up/down mượt (accelerate), không nhảy 2–3 dòng.
- [ ] 1/3 trang, 4/6 jump letter, * favorite (toast), # sort.
- [ ] Theme Dark/Light đổi ngay.
- [ ] Không emoji; icon rect/image_region.
- [ ] Không hard-code 240/320 ngoài `theme.lua`.
- [ ] Không table/string mới trong `engine.draw`.
- [ ] 5 vòng tab↔list↔menu không tăng heap (OOM test).
- [ ] Smoke-test **máy thật** MTK6260 — emulator chưa đủ.

---

## 9. Ví dụ status / toast (chuỗi tĩnh)

```lua
HINT_MAIN   = "OK:Open  Menu:Opt  *:Fav  #:Sort"
HINT_MENU   = "OK:Select  RSK:Back"
HINT_EMPTY  = "No ROMs - scan storage"
MSG_FAV_ON  = "Added to Favorites"
MSG_FAV_OFF = "Removed Favorite"
MSG_SORT    = "Sort: name"
```
