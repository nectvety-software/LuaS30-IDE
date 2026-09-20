# SKILLS.md — Kỹ năng tối ưu bộ nhớ LuaS30 / MRE (chống "not enough memory")

Bộ kỹ năng đã dùng thật cho game **Biển Mực (Chetaslua)**; mọi con số trong ngoặc là số đo
trên runtime của IDE (`tools/lua_preview.py`: Lua 5.1 thật). Dùng kèm **MEMORY_PROMPT.md**.

> **Vị trí**: `D:\MRE\LuaS30-IDE\doc\ai\MEMORY_SKILLS.md` — bổ sung cho `doc/ai/SKILL.md`
> của IDE, chỉ nói về bộ nhớ. Mã mẫu trong đây đã được compile lại bằng Lua 5.1 (`doc_check.py`).
> Cập nhật: 09/2026 theo số đo của dự án Chetaslua.

Đường dẫn dùng trong ví dụ: `PROJECT = thư mục dự án`, `IDE = D:\MRE\LuaS30-IDE`.

---

## 1. Đo đúng cách trước khi sửa

**Dùng khi**: bắt đầu bất kỳ việc tối ưu bộ nhớ nào.

**Cách làm**: chạy vòng lặp khung **trong Lua**, Python chỉ gọi vào một lần rồi đọc kết quả.
Nếu Python gọi `engine.update/draw` từng khung, chính đường đi qua cầu Lua↔Python làm tăng heap
(~170 byte/khung) và làm sai kết quả.

```lua
-- Đo rác/khung: GC TAT, đo chênh lệch heap qua n khung.
function bench(n)
    collectgarbage("collect"); collectgarbage("collect")
    collectgarbage("stop")
    local before = collectgarbage("count")
    for _ = 1, n do engine.update(1/15); engine.draw() end
    local after = collectgarbage("count")
    collectgarbage("restart")
    return (after - before) * 1024.0 / n      -- byte/khung
end
```

Bốn chỉ số phải có: **rác/khung** từng màn, **heap sau khi nạp**, **đỉnh khi chơi**, **bytecode so
với bảng dữ liệu**. Đo hai cửa sổ liên tiếp: cửa sổ đầu gồm phí "khởi động" (nan glyph, nạp đệm),
cửa sổ sau mới là rác thật (dự án mẫu: màn Cài đặt 237–265 B/khung ở cửa sổ đầu, **2 B/khung**
ở cửa sổ sau → đừng kết luận sớm).

---

## 2. Bản đồ bộ nhớ: bytecode vs bảng dữ liệu

**Dùng khi**: cần biết file nào đáng sửa.

**Cách làm**: `loadstring(src)` đo phần *compile* (bytecode luôn nằm trong heap), rồi `require`
trong runtime sạch đo phần *chạy mô-đun* (bảng + chuỗi).

```lua
-- bytecode: nap chunk, KHONG chay
local base = collectgarbage("count")
local fn = loadstring(source, "@" .. path)
collectgarbage("collect")
local code_kb = collectgarbage("count") - base
```

Kết luận thực tế: bytecode ~300 KB/14 file (luôn thường trú, GC không dọn) trong khi bảng dữ liệu
sửa được thì ~96 KB (`font` 64 + `i18n` 32). ⇒ Ưu tiên: **bảng dữ liệu trước, bytecode sau**.

---

## 3. Nạp màn hình theo nhu cầu + trả bytecode khi máy chặt

**Dùng khi**: dự án có nhiều màn hình mỗi màn vài chục KB bytecode.

```lua
local Screens, LOADED = {}, {}          -- LOADED: thu tu su dung (cu -> moi)

local function max_keep()
    if Mem.level >= 2 then return 1 end -- may chat: giu dung man hinh dang mo
    if Mem.level >= 1 then return 3 end
    return 8
end

local function touch(name)
    local i = 1
    while i <= #LOADED do
        if LOADED[i] == name then table.remove(LOADED, i); break end
        i = i + 1
    end
    LOADED[#LOADED + 1] = name
end

local function evict()
    local keep, have = max_keep(), 0
    local i = 1
    while i <= #LOADED do
        if Screens[LOADED[i]] then have = have + 1 end
        i = i + 1
    end
    while have > keep and #LOADED > 0 do
        local old = LOADED[1]
        table.remove(LOADED, 1)
        if Screens[old] then
            Screens[old] = nil
            if package and package.loaded then
                package.loaded["src.screens." .. old] = nil
            end
            have = have - 1
        end
    end
end

function S.go(name)
    touch(name)
    evict()                 -- tra bytecode TRUOC
    Mem.sweep()             -- don rac TRUOC khi nap (nap sau khi don thi khong bi thieu)
    A.trim(); I.trim()      -- xoa dem ve chu (chi o diem an toan nay)
    local sc = Screens[name] or require("src.screens." .. name)
    Screens[name] = sc
    if sc.enter then sc.enter(S) end
end
```

**Kiểm tra**: với `Mem.force(2)`, đi qua hết các màn hình rồi về menu, `package.loaded["src.screens.play"]`
phải là `nil`. Đo được: trả **61 KB** bytecode khi ở menu.

---

## 4. Đệm chống chuỗi dài (nguyên nhân âm thầm tốn nhiều nhất)

**Dùng khi**: mọi cache khoá bằng chuỗi hiển thị/hay ghép.

Vấn đề: Lua 5.1 chỉ intern chuỗi ≤ 40 ký tự. Chuỗi ghép mỗi khung là đối tượng mới → đệm thêm
mục mới mỗi khung rồi xoá sạch → vừa tốn RAM vừa sinh rác (dự án mẫu: 237 B/khung).

```lua
local LONG_MAX = 8

function M.memo_new(max)
    return { bag = {}, ring = {}, val = {}, n = 0, max = max or 48, miss = 0, reset = 0 }
end

function M.memo_get(m, s)
    if #s <= 40 then return m.bag[s] end
    local ring, i, n = m.ring, 1, #m.ring
    while i <= n do
        if ring[i] == s then return m.val[i] end   -- so sanh NOI DUNG, khong tao doi tuong
        i = i + 1
    end
    return nil
end

function M.memo_put(m, s, v)
    m.miss = m.miss + 1
    if #s <= 40 then
        if m.n > m.max then m.bag = {}; m.n = 0; m.reset = m.reset + 1 end
        m.bag[s] = v
        m.n = m.n + 1
        return v
    end
    local ring = m.ring
    if #ring >= LONG_MAX then table.remove(ring, 1); table.remove(m.val, 1) end
    ring[#ring + 1] = s
    m.val[#m.val + 1] = v
    return v
end

function M.memo_clear(m) m.bag = {}; m.ring = {}; m.val = {}; m.n = 0 end
```

Bọc mỗi cache thành `local C = I.memo_new(48)` rồi đọc/ghi bằng `memo_get/memo_put`.
Giữ lại `miss`/`reset` để tool đọc được (đếm "trượt đệm"); **đệm tốt phải có 0 trượt/khung**.

---

## 5. Sinh dữ liệu ngay khi dùng

**Glyph font** (dự án mẫu: 64 KB → ~6 KB):

```lua
local GLYPH, GLYPH_N, GLYPH_MAX = {}, 0, 96
local function spec_of(ch) ... end            -- chu goc + cac dau ghep lai
function M.glyph_of(ch)
    local g = GLYPH[ch]
    if g then return g end
    local spec = spec_of(ch)
    if spec == nil then return nil end
    g = parse(spec)
    if GLYPH_N > GLYPH_MAX then GLYPH = {}; GLYPH_N = 0 end
    GLYPH[ch] = g
    GLYPH_N = GLYPH_N + 1
    return g
end
function M.has(ch) return BASE[ch] ~= nil or COMPOSE[ch] ~= nil end
```

**Gói ngôn ngữ** (dự án mẫu: 32 KB → ~10 KB): bảng bỏ dấu và bảng chữ HOA sinh khi gọi lần đầu;
bản "không dấu" sinh **từng khoá** ngay khi hiển thị bằng `__index`:

```lua
local VI_ND = setmetatable({}, {
    __index = function(t, k)
        local v = VI[k]
        if type(v) == "string" then v = M.strip(v)
        elseif type(v) == "table" then
            local out, i = {}, 1
            while i <= #v do out[i] = M.strip(v[i]); i = i + 1 end
            v = out
        end
        t[k] = v
        return v
    end
})
M.t = { vi = VI, ["vi_nd"] = VI_ND, en = EN }
```

**Kiểm tra**: sau khi hiển thị vài màn hình ở chế độ không dấu, `#keys` sinh ra phải ≈ 40
(không phải toàn bộ ~90 khoá); và không chuỗi nào còn dấu (quét mã U+1EA0..U+1EFF).

---

## 6. Bảng nhẩm chuỗi hiển thị (ghép chỉ khi số liệu / ngôn ngữ đổi)

```lua
local STAT = { key = -1, s = "", lang = "" }
...
local key = d.hi * 65536 + (d.total or 0) * 4 + (d.grade or 0)
if STAT.key ~= key or STAT.lang ~= d.lang then      -- THIEU d.lang => hien tieng cu
    STAT.key, STAT.lang = key, d.lang
    STAT.s = S.tr("hud_hi") .. ": " .. d.hi .. "  " .. S.tr("total") .. ": "
        .. (d.total or 0) .. "  " .. S.tr("grade_of") .. ": " .. grade
end
A.ctext(A.W / 2, 236, STAT.s, A.LEAD)
```

Tương tự cho mọi dòng có số liệu (điểm cao, số trận, yêu cầu mở khoá, RAM). Tên theo chỉ số thì
dùng bảng hằng (`PEN_KEYS = {"pen1","pen2","pen3","pen4"}`) thay cho `"pen" .. i`.
Khi đổi ngôn ngữ, gọi `I.set_lang(lang)` để xoá đệm chữ HOA.

---

## 7. Chỉnh GC và chọn điểm dọn rác

```lua
-- Lua don rac khi heap gap 'pause' lan so vat song; mac dinh 200% => heap phinh gap doi.
pcall(collectgarbage, "setpause", 130)
pcall(collectgarbage, "setstepmul", 250)

function M.sweep()                     -- goi o diem an toan
    collectgarbage("collect")
    M.used = collectgarbage("count")
    if M.used > M.peak then M.peak = M.used end
    new_label()                        -- dung lai chuoi hien thi (khong tao moi moi khung)
end
```

Điểm an toàn: đổi màn hình, **đổi đợt sóng** (`Mem.sweep()` trong `spawn_wave`), chấm điểm cuối
trận. Không gọi giữa lúc đang bắn.

---

## 8. Thang hạ chất lượng tự động

```lua
local HI = { 1.30, 1.55, 1.85, 2.20 }   -- nguong len theo boi so moc nen
local LO = { 1.20, 1.45, 1.72, 2.05 }   -- nguong xuong lai (co tre)
local ABS = 0.80                        -- tran tuyet doi: 80% heap may

function M.level_for(used)
    local cap, lvl, i = M.budget * ABS, 0, 1
    while i <= 4 do
        local hi = M.base * HI[i]
        if hi > cap then hi = cap end
        if used > hi then lvl = i end
        i = i + 1
    end
    return lvl
end

function M.tick(dt)                     -- do 2 lan/giay cho nhe may
    M.t = M.t + dt
    if M.t < 0.5 then return M.level end
    M.t = 0
    local used = collectgarbage("count")
    M.used = used
    if used > M.peak then M.peak = used end
    if M.forced then ... end
    local lvl = M.level
    while lvl > 0 and used < M.base * LO[lvl] do lvl = lvl - 1 end
    if M.level_for(used) > lvl then lvl = M.level_for(used) end
    if lvl ~= M.level then M.level = lvl; M.sweep() end
    return M.level
end
```

`M.mark()` chụp mốc nền ngay sau khi nạp xong các mô-đun lõi (dự án mẫu: 231 KB). Nếu mốc nền đã
> 44% heap máy thì vào thẳng L1/L2 (máy nhỏ không phải chờ bộ nhớ tăng mới hạ).
`M.force(n)` ép mức ngay (dùng cho test và đo lệnh vẽ).

Nơi đọc `Mem.level` để giảm chi tiết: độ dày tô gạch, số dòng kẻ vở, mưa/mây/sét, trần vật thể,
trần hiệu ứng, loại địch, nhạc nền (`if Mem.level >= 3 then name = nil end` trong `music`, và dừng
nhạc trong `update` **trước** khi kiểm tra `HAS_AUDIO` để trạng thái luôn đúng).

---

## 9. Truy tìm chỗ tạo rác (khi số liệu bất thường)

**Cách làm**: giữ nguyên một `Sim`, đo rác/khung, rồi **thay từng hàm bằng bản rỗng** và đo lại;
mỗi lần đo phải xác nhận vẫn đang ở đúng màn hình. Luôn đo lặp 2–3 lần cùng một phép đo trước khi
kết luận (lần đầu thường gồm phí khởi động).

**Cạm bẫy**: đừng vội đổ lỗi cho `engine.line`. Đo trực tiếp `engine.line/rect/frame/text` 2000
lần: **0 byte/lần gọi**. Vòng lặp khung do Python điều khiển mới là thứ tạo ra hàng trăm byte/khung
giả. Bài học: tách "chi phí của harness" khỏi "chi phí của game".

---

## 10. Kiểm thử bộ nhớ bắt buộc

```bash
# 1. Rác/khung từng màn + rò rỉ + đỉnh khi chơi 40 s
python .freebuff/tools/ram_check.py

# 2. Test OOM 5 vong menu -> tran -> boss -> menu + MAY CHAT 512 KB tu ha cap
python .freebuff/tools/mem_budget.py

# 3. Bytecode vs bang du lieu tung file
python .freebuff/tools/mem_map.py

# 4. Do "truot dem" cua cac cache chuoi (phai ~0/khung)
python .freebuff/tools/memo_probe.py
```

Khung test OOM tối thiểu (chạy trong Lua cho chính xác):

```lua
function rush_waves(k)              -- nhay nhanh toi dot co boss
    local st = engine.debug_state()
    for _ = 1, k do
        st.p.next_wave = 0
        engine.update(1/15); engine.draw()
        st.p.hp = 3                 -- giu tau song de do tiep
    end
    return st.p.wave
end
```

Mô phỏng máy nhỏ: `Mem.budget = 512; Mem.level = 0; Mem.mark()` rồi kiểm tra game **tự** vào L2,
trả bytecode màn chơi, giới hạn vật thể, tắt nhạc ở L3 — không được crash.

---

## 11. Kiểm tra hình vẽ và bố cục bằng máy

Tối ưu bộ nhớ rất dễ làm hỏng hình. Sau mỗi lần sửa, chạy:

```bash
python .freebuff/tools/visual_check.py   # dem pixel: tau, tim, la chan, duong dan, diem do
python .freebuff/tools/text_check.py     # chu co tran le / de nhau khong (doc A.debug_texts)
python .freebuff/tools/font_check.py     # thieu glyph nao khong, dau tieng Viet hien du
python .freebuff/tools/lang_check.py     # 3 ngon ngu x moi man hinh, khong sot dau/chu cu
```

`text_check` cần cờ `A.debug_log = true` để ghi lại `A.debug_texts`/`A.debug_events` (ghi cả lớp
đặc để biết chữ nào bị che). Đây là cách duy nhất kiểm tra bố cục mà không nhìn màn hình.

---

## 12. Đóng gói và kiểm tra gói

```bash
cd D:/MRE/LuaS30-IDE
python tools/build.py --project "<PROJECT>" \
    --toolchain "D:/MRE/LuaS30-IDE/toolchain/arm-gcc" \
    --compat-profile standalone --no-run
python <PROJECT>/.freebuff/tools/vxp_pack_check.py
```

* `--lua-protection auto` (mặc định) = minify. **Không** dùng `bytecode` với `luac` PC.
* `tools/build.py` bỏ qua `build/ release/ saves/ tests/ backups/ .git/ .luas30` nhưng **không** bỏ
  qua `.freebuff` → cho tool ghi ảnh/file tạm vào `build/`, và đừng để `.lua` trong `.freebuff`.
* Luôn đối chiếu: dung lượng VXP, SHA-256, số file trong gói, metadata khớp `project.json`, và
  **chạy bản Lua đã nén trong `build/res`** (bản nén có thể lộ lỗi mà bản gốc không có).
* Build lại sẽ **xoá** artifact cũ trong `build/` — VXP đã ký tay trước đó phải ký lại theo SHA mới.

---

## 13. Vì sao không dùng `.lub` sinh từ máy tính

Header bytecode Lua 5.1 có ghi `sizeof(size_t)`: PC 64-bit = 8, ARM 32-bit của máy = 4 → firmware
báo `bad bytecode` (không fallback về `.lua`). Chỉ dùng `.lub` khi có `luac` 32-bit cùng
`luaconf.h` với runtime; còn lại giữ `.lua` + minify.

---

## 14. Số tham chiếu (game Biển Mực, heap 1024 KB)

| Chỉ số | Trước | Sau |
|---|---|---|
| Heap sau khi nạp | 391 KB | **231 KB** |
| MENU / CHƠI đang dùng | 410 / 431 KB | **287 / 371 KB** |
| Đỉnh khi chơi 40 s (có boss) | 472 KB (46%) | **415 KB (41%)** |
| Rác/khung ổn định | 0–26 B | 0–29 B |
| 5 vòng menu→trận→boss→menu | — | **−0.9 KB** (không rò) |
| Bytecode trả lại khi ở menu (máy L2) | 0 | **61 KB** |
| Lệnh vẽ 1 khung | 712–1468 | 634–1468 (1398 khi ở L2) |

---

## 15. Checklist 10 dòng (dán vào cuối mọi lần tối ưu)

1. Đã đo trước khi sửa (rác/khung, heap nạp, đỉnh, bytecode vs dữ liệu).
2. Không còn table/chuỗi tạo trong hàm vẽ.
3. Mọi cache có trần **và** chống chuỗi dài; `memo_probe` báo ~0 trượt/khung.
4. Dữ liệu nặng sinh khi dùng (glyph, ngôn ngữ).
5. Màn hình nạp theo nhu cầu; máy chặt thì trả bytecode màn không dùng.
6. GC: `setpause` ~130, dọn rác ở điểm an toàn, không dọn giữa trận.
7. Thang L0–L4 tự động, có trần 80% heap, có trễ, hiện mức cho người chơi xem.
8. Test OOM 5 vòng không rò + mô phỏng máy 512 KB tự hạ cấp.
9. `visual/text/font/lang_check` đều PASS.
10. Gói VXP không chứa file tạm, bản nén chạy đúng, có SHA-256 trong báo cáo.
