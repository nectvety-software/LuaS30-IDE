-- popart_city_check.lua — harness cho template "Pop Art City 3D".
--
-- Khong doc code roi doan: harness nay CHAY that main.lua + src/*.lua tren mot
-- bang `engine` gia, GHI LAI tung loi goi rect/text, roi RASTER HOA chung vao
-- mot luoi 240x320. Nho vay kiem duoc nhung thu ma kiem tra tinh khong thay:
--   * man hinh co bi ho lo nao khong (moi o phai duoc to),
--   * tuong nam dung cot nao (doc pixel da ve),
--   * sprite co bi tuong che khong,
--   * moi khung hinh ton bao nhieu rect va bao nhieu pixel,
--   * HUD co khop voi trang thai that khong.
--
-- Cach chay (can Lua 5.1 — cung ban voi vendor/lua-5.1.5):
--     cd templates/PopArtCity3D
--     <repo>/build/_lua51/lua.exe <repo>/tools/popart_city_check.lua
--
-- Khong import gi tu studio/ hay engine/: chi mot bang `engine` gia.

local SW, SH = 240, 320

-- ---------------------------------------------------------------- stub engine
--
-- Bang gia nay CO Y kiem tra kieu tham so y nhu `engine/src/runtime_bridge.c`:
--
--   * `l_rect` / `l_frame` / `l_line` goi `luaL_checknumber` cho toa do va
--     `lua_color()` (-> `luaL_checknumber`) cho mau => mau thieu la LOI.
--   * `l_text` chi kiem tra mau khi tham so #4 CO MAT
--     (`lua_gettop(L) >= 4 ? lua_color(L,4) : LS30_COLOR_WHITE`). Lua dem ca
--     `nil` o cuoi danh sach, nen `E.text(x, y, s, nil)` la loi #4 that.
--     Vi vay phai dung `select("#", ...)` chu khong the so `c == nil`.
--
-- Khong co phan nay thi mot mau `nil` (vi du `P.C.gold` khi bang mau chi co
-- `HUD.C.gold`) di qua harness IM LANG, roi no ra tren may that duoi dang
-- "bad argument #4" — dung nhu da mac.
local rec = {
    rects = {}, texts = {}, misses = {}, args = {}, exit = false,
    colours = {},      -- moi mau da ve, tren MOI man hinh (de doi chieu bang mau)
    all_texts = {},    -- moi loi goi engine.text (de kiem tra tran man hinh)
}
local clock = 0
local in_frame = false

--: Be rong trung binh MOT ky tu cua font firmware o `set_font(8)`.
--:
--: DO THAT tren VXPEmu (build/_font_probe.py + do tu anh chup), khong suy doan:
--:   text_width("0123456789") = 71.4 fb px  -> 7.14 px/ky tu
--:   text_width("ABCDEFGHIJ") = 72.2 fb px  -> 7.22 px/ky tu
--:   text_width(".....")      = 26.6 fb px  -> 5.32 px/ky tu
--: Font firmware la font TY LE, nen day chi la gia tri trung binh — dung 7.2
--: (lech len) de phep kiem tra "chu co tran ra ngoai man hinh khong" la bao thu.
local ADVANCE = 7.2

local function bad_arg(fn, idx, want, got)
    rec.args[#rec.args + 1] = fn .. " #" .. idx .. ": can " .. want ..
                              ", nhan " .. type(got)
end

local function num(fn, idx, v)
    if type(v) ~= "number" then bad_arg(fn, idx, "number", v) return nil end
    return v
end

local function colour(fn, idx, v)
    if type(v) ~= "number" then bad_arg(fn, idx, "colour(number)", v) return nil end
    return v
end

local function str(fn, idx, v)
    if type(v) ~= "string" and type(v) ~= "number" then
        bad_arg(fn, idx, "string", v) return nil
    end
    return tostring(v)
end

-- Ghi mot hinh chu nhat. Bo qua neu tham so da hong: nho vay loi kieu tham so
-- chi hien o F2 (mot nguon), khong lam ban them cac phep kiem tra khac.
local function record_rect(x, y, w, h, c)
    if not (x and y and w and h and c) then return end
    rec.colours[c] = true
    if in_frame then
        rec.rects[#rec.rects + 1] = { x, y, w, h, c }
    end
end

engine = {
    W = SW,
    H = SH,
    version = "stub/5.1.5",

    color = function(r, g, b)
        local cr, cg, cb = num("color", 1, r), num("color", 2, g), num("color", 3, b)
        if not (cr and cg and cb) then return 0 end
        return cr * 65536 + cg * 256 + cb
    end,
    clear = function(c) record_rect(0, 0, SW, SH, colour("clear", 1, c)) end,
    rect = function(x, y, w, h, c)
        record_rect(num("rect", 1, x), num("rect", 2, y),
                    num("rect", 3, w), num("rect", 4, h), colour("rect", 5, c))
    end,
    frame = function(x, y, w, h, c)
        local cx, cy = num("frame", 1, x), num("frame", 2, y)
        local cw, ch = num("frame", 3, w), num("frame", 4, h)
        local cc = colour("frame", 5, c)
        if not (cx and cy and cw and ch and cc) then return end
        record_rect(cx, cy, cw, 1, cc)
        record_rect(cx, cy + ch - 1, cw, 1, cc)
        record_rect(cx, cy, 1, ch, cc)
        record_rect(cx + cw - 1, cy, 1, ch, cc)
    end,
    line = function(x0, y0, x1, y1, c)
        record_rect(num("line", 1, x0), num("line", 2, y0), 1, 1,
                    colour("line", 5, c))
    end,
    text = function(...)
        local n = select("#", ...)
        local x, y, s, c = ...
        local tx, ty, ts = num("text", 1, x), num("text", 2, y), str("text", 3, s)
        if n >= 4 then
            c = colour("text", 4, c)
        else
            c = 0xFFFFFF      -- LS30_COLOR_WHITE khi tham so #4 vang mat
        end
        if not (tx and ty and ts and c) then return end
        rec.colours[c] = true
        rec.all_texts[#rec.all_texts + 1] = { x = tx, y = ty, s = ts }
        if in_frame then
            rec.texts[#rec.texts + 1] = { x = tx, y = ty, s = ts, c = c }
        end
    end,
    -- `luaL_optnumber`: vang mat hoac nil deu lay mac dinh, KHONG phai loi.
    set_font = function(n)
        if n ~= nil then num("set_font", 1, n) end
    end,
    text_width = function(s)
        local v = str("text_width", 1, s)
        if not v then return 0 end
        return math.ceil(#v * ADVANCE)
    end,
    font_height = function() return 8 end,
    image = function() end,
    image_region = function() end,
    flush = function() end,
    tick_ms = function() return clock end,
    exit = function() rec.exit = true end,
    log = function() end,
    capabilities = function() return 0 end,
    device_info = function() return {} end,
    runtime_compat = function() return {} end,
}
mre = engine

-- Tra ve mot ham RONG chu khong phai nil: nho vay mot loi goi ham khong co
-- trong API (vi du engine.pixel) se duoc F1 bao cao tu te, thay vi lam harness
-- vo bang "attempt to call a nil value" — do vi sup, khong phai vi guard.
setmetatable(engine, {
    __index = function(_, k)
        rec.misses[#rec.misses + 1] = tostring(k)
        return function() end
    end,
})

-- ---------------------------------------------------------------- helpers
local checks, failures = 0, 0

local function check(label, ok, detail)
    checks = checks + 1
    if ok then
        print("ok   : " .. label)
    else
        failures = failures + 1
        print("FAIL : " .. label .. (detail and ("  [" .. tostring(detail) .. "]") or ""))
    end
end

local function capture()
    rec.rects = {}
    rec.texts = {}
    in_frame = true
    engine.draw()
    in_frame = false
    return rec.rects, rec.texts
end

local function stats(rects)
    local n, px = 0, 0
    local bad = nil
    for i = 1, #rects do
        local r = rects[i]
        n = n + 1
        px = px + r[3] * r[4]
        if not bad then
            if r[3] < 1 or r[4] < 1 then
                bad = "rect " .. i .. " w/h <= 0: " .. r[3] .. "x" .. r[4]
            elseif r[1] ~= math.floor(r[1]) or r[2] ~= math.floor(r[2])
                   or r[3] ~= math.floor(r[3]) or r[4] ~= math.floor(r[4]) then
                bad = "rect " .. i .. " toa do khong nguyen"
            elseif r[1] + r[3] <= 0 or r[2] + r[4] <= 0
                   or r[1] >= SW or r[2] >= SH then
                bad = "rect " .. i .. " nam hoan toan ngoai man hinh"
            end
        end
    end
    return n, px, bad
end

local function raster(rects)
    local grid = {}
    for y = 0, SH - 1 do grid[y] = {} end
    local painted = 0
    for i = 1, #rects do
        local r = rects[i]
        local x0, y0 = r[1], r[2]
        local x1, y1 = x0 + r[3] - 1, y0 + r[4] - 1
        if x0 < 0 then x0 = 0 end
        if y0 < 0 then y0 = 0 end
        if x1 > SW - 1 then x1 = SW - 1 end
        if y1 > SH - 1 then y1 = SH - 1 end
        for y = y0, y1 do
            local row = grid[y]
            for x = x0, x1 do
                if row[x] == nil then painted = painted + 1 end
                row[x] = r[5]
            end
        end
    end
    return grid, painted
end

local function at(grid, x, y)
    if x < 0 or y < 0 or x >= SW or y >= SH then return nil end
    return grid[y][x]
end

local function press(k) engine.keypressed(k) end
local function release(k) engine.keyreleased(k) end
local function tap(k) press(k) release(k) end

local function advance(ms, steps)
    steps = steps or 1
    for _ = 1, steps do
        clock = clock + ms
        engine.update(ms / 1000)
    end
end

-- ---------------------------------------------------------------- load template
dofile("main.lua")
local P = require("src.popart")
local C = require("src.city")
local R = require("src.render")
local HUD = require("src.hud")
local PL = require("src.player")

engine.load()
capture()

-- Bang mau day du: moi mau duoc ve PHAI nam trong day.
local PALETTE = {}
do
    local function add(v)
        if type(v) == "number" then PALETTE[v] = true end
    end
    for _, v in pairs(P.C) do
        if type(v) == "table" then
            for _, x in ipairs(v) do add(x) end
        else
            add(v)
        end
    end
    for i = 1, #P.BUILD do
        for _, x in ipairs(P.BUILD[i].shades) do add(x) end
    end
    for _, v in pairs(HUD.C) do add(v) end
    add(R.C_FAR)
    add(R.C_SUN)
    add(R.C_SUN2)
    -- `l_text` mac dinh ve mau TRANG khi tham so #4 vang mat (xem stub engine).
    add(0xFFFFFF)
end

-- Doc HP that tu thanh HP trong HUD (khong doc bien noi bo).
local function read_hp()
    local W = SW
    local fill = 0
    for _, r in ipairs(rec.rects) do
        if r[2] == SH - 60 and r[4] == 8 and r[1] >= 150 then
            if r[5] == HUD.C.hp_hi or r[5] == HUD.C.hp_mid or r[5] == HUD.C.hp_lo then
                fill = r[3]
            end
        end
    end
    return math.floor(fill / 72 * 100 + 0.5)
end

-- Doc tien tu chu HUD (chuoi bat dau bang "$").
local function read_money()
    for _, t in ipairs(rec.texts) do
        local n = t.s:match("^%$(%d+)$")
        if n then return tonumber(n) end
    end
    return nil
end

-- Chi so muc dang duoc chon trong menu: tim bang mau nong cao 22-24 px.
-- (Man hinh tieu de ve o chon cao 24, man hinh tam dung ve cao 22.)
local function hot_panel_y(rects, y_min, y_max)
    for _, r in ipairs(rects) do
        if r[5] == P.C.hot and (r[4] == 24 or r[4] == 22)
           and r[2] >= y_min and r[2] <= y_max then
            return r[2]
        end
    end
    return nil
end

-- =========================================================== A. Bang mau / font
do
    local n = 0
    for _ in pairs(P.GLYPH) do n = n + 1 end
    check("A1 font khoi co du bo glyph", n >= 50, n)

    local missing = {}
    for c in ("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$-.+:/!?*<>%'"):gmatch(".") do
        if not P.GLYPH[c] then missing[#missing + 1] = c end
    end
    check("A2 khong thieu glyph nao dang dung", #missing == 0, table.concat(missing, ","))

    local bad = nil
    for c, rows in pairs(P.GLYPH) do
        rec.rects = {}
        in_frame = true
        P.text(0, 0, c, P.C.paper, 1)
        in_frame = false
        local x0, y0, x1, y1 = 999, 999, -1, -1
        for _, r in ipairs(rec.rects) do
            if r[1] < x0 then x0 = r[1] end
            if r[2] < y0 then y0 = r[2] end
            if r[1] + r[3] - 1 > x1 then x1 = r[1] + r[3] - 1 end
            if r[2] + r[4] - 1 > y1 then y1 = r[2] + r[4] - 1 end
        end
        local empty = true
        for i = 1, 5 do
            if rows[i] ~= 0 then empty = false end
        end
        if empty then
            if #rec.rects ~= 0 then bad = "glyph trong '" .. c .. "' lai ve" end
        elseif x0 < 0 or y0 < 0 or x1 > 2 or y1 > 4 then
            bad = "glyph '" .. c .. "' tran ra ngoai 3x5: " ..
                  x0 .. "," .. y0 .. " -> " .. x1 .. "," .. y1
        end
    end
    check("A3 moi glyph nam gon trong 3x5", bad == nil, bad)

    rec.rects = {}
    in_frame = true
    P.text(10, 10, "CITY 3D", P.C.paper, 2)
    in_frame = false
    local x1 = -1
    for _, r in ipairs(rec.rects) do
        if r[1] + r[3] - 1 > x1 then x1 = r[1] + r[3] - 1 end
    end
    check("A4 be rong ve ra khop text_w",
          x1 - 10 + 1 == P.text_w("CITY 3D", 2),
          "ve=" .. (x1 - 10 + 1) .. " text_w=" .. P.text_w("CITY 3D", 2))

    local l0r, l0g, l0b = P.shade_rgb(0, 194, 209, 0)
    local l3r, l3g, l3b = P.shade_rgb(0, 194, 209, 3)
    check("A5 sac do xa toi hon sac do gan",
          (l3r + l3g + l3b) < (l0r + l0g + l0b),
          (l0r + l0g + l0b) .. " -> " .. (l3r + l3g + l3b))

    -- Khoi xa phai HOI TU: hai mau khac nhau cang ra xa cang giong nhau.
    -- (Khong doi chung bang DUNG mau khoi — chi doi khoang cach THU HEP lai.)
    local n0r, n0g, n0b = P.shade_rgb(255, 210, 63, 0)
    local n1r, n1g, n1b = P.shade_rgb(58, 26, 96, 0)
    local f0r, f0g, f0b = P.shade_rgb(255, 210, 63, 3)
    local f1r, f1g, f1b = P.shade_rgb(58, 26, 96, 3)
    local near = math.abs(n0r - n1r) + math.abs(n0g - n1g) + math.abs(n0b - n1b)
    local far = math.abs(f0r - f1r) + math.abs(f0g - f1g) + math.abs(f0b - f1b)
    check("A6 hai mau khac nhau hoi tu ve mau khoi khi ra xa",
          far < near * 0.5, near .. " -> " .. far)
end

-- =========================================================== B. Ban do
do
    check("B1 diem xuat phat khong bi chan", not C.blocked(C.SPAWN.x, C.SPAWN.y, 0.34))

    local ok_spots = true
    for i = 1, #C.SPOTS do
        local s = C.SPOTS[i]
        if C.blocked(s[1], s[2], 0.34) then ok_spots = false end
    end
    check("B2 moi cot moc deu nam tren duong", ok_spots)

    check("B3 ngoai ban do la vat can", C.blocked(-1.0, 5.5, 0.2) == true)

    local same = true
    for gx = 0, 15 do
        for gy = 0, 15 do
            if C.kind(gx, gy) ~= C.kind(gx, gy) then same = false end
        end
    end
    check("B4 ban do tat dinh (khong dung math.random)", same)

    local bad = nil
    for gx = 0, 31 do
        for gy = 0, 31 do
            local k = C.kind(gx, gy)
            if k < 0 or k > 6 then bad = gx .. "," .. gy .. "=" .. k end
        end
    end
    check("B5 loai o luon trong 0..6", bad == nil, bad)

    local kinds = {}
    for gx = 0, 31 do
        for gy = 0, 31 do
            local k = C.kind(gx, gy)
            if k > 0 then kinds[k] = true end
        end
    end
    local nk = 0
    for _ in pairs(kinds) do nk = nk + 1 end
    check("B6 thanh pho dung du 6 loai nha", nk == 6, nk)

    -- Tim duong phai cho xe di lot: kiem tra ca 7 tuyen.
    local narrow = nil
    for _, v in ipairs(C.LANE) do
        if C.blocked(v, 1, 0.34) or C.blocked(v, 31, 0.34) or C.blocked(1, v, 0.34) then
            narrow = v
        end
    end
    check("B7 tim duong du rong cho xe", narrow == nil, narrow)
end

-- =========================================================== C. Render
do
    local rects, texts = capture()
    local n, px, bad = stats(rects)
    print(string.format("info : man hinh tieu de: %d rect, %d px", n, px))
    check("C1 rect tieu de deu hop le", bad == nil, bad)
    local grid, painted = raster(rects)
    check("C2 tieu de phu kin man hinh", painted == SW * SH, painted .. "/" .. (SW * SH))
    check("C3 tieu de co chu (engine.text)", #texts > 0, #texts)

    tap("ok")
    advance(16)
    rects, texts = capture()
    n, px, bad = stats(rects)
    print(string.format("info : khung hinh choi: %d rect, %d px", n, px))
    check("C4 rect trong game deu hop le", bad == nil, bad)
    grid, painted = raster(rects)
    check("C5 khung nhin 3D phu kin man hinh", painted == SW * SH, painted .. "/" .. (SW * SH))
    check("C6 ngan sach rect moi khung <= 260", n <= 260, n)
    check("C7 ngan sach pixel moi khung <= 150000", px <= 150000, px)

    -- Moi mau ve ra phai nam trong bang mau.
    local strays = {}
    for _, r in ipairs(rects) do
        if not PALETTE[r[5]] then strays[#strays + 1] = tostring(r[5]) end
    end
    check("C8 moi mau deu thuoc bang mau", #strays == 0,
          table.concat(strays, ",", 1, math.min(3, #strays)))

    -- Nhin thang vao tuong: dinh cot giua phai co vien den.
    local INK = P.C.ink
    rec.rects = {}
    in_frame = true
    R.frame(2.5, 21.5, -math.pi / 2, nil)
    in_frame = false
    grid = raster(rec.rects)
    local top_ink = 0
    for x = 118, 121 do
        if at(grid, x, 0) == INK then top_ink = top_ink + 1 end
    end
    check("C9 nhin thang tuong: dinh tuong co vien den", top_ink == 4, top_ink)

    -- Nhin doc hanh lang duong: cot giua KHONG duoc co tuong.
    -- Lay mau o y=20 (tren cao chan troi xa, xem draw_far_skyline) — neu lay
    -- sat duong chan troi thi se cham vao silhouette thanh pho xa, khong phai tuong.
    rec.rects = {}
    in_frame = true
    R.frame(1, 11, 0, nil)
    in_frame = false
    grid = raster(rec.rects)
    local mid = at(grid, 120, 20)
    local sky = false
    for i = 1, #P.C.sky do
        if mid == P.C.sky[i] then sky = true end
    end
    check("C10 nhin doc duong: cot giua la troi, khong co tuong", sky, mid)

    -- Che khuat sprite: so khung hinh CO sprite voi khung hinh KHONG co.
    -- Do la phep kiem manh nhat — khong phu thuoc vao mau nao duoc ve hay ve o
    -- dau. (Ban dau toi chi tim mau vang o nua TREN man hinh; sprite bi che ma
    -- lot xuong nua duoi thi guard van xanh — da mac that.)
    local function frame_grid(extra)
        rec.rects = {}
        in_frame = true
        R.frame(2.5, 21.5, -math.pi / 2, extra)
        in_frame = false
        return raster(rec.rects)
    end
    local function grid_diff(a, b)
        local d = 0
        for y = 0, SH - 1 do
            for x = 0, SW - 1 do
                if a[y][x] ~= b[y][x] then d = d + 1 end
            end
        end
        return d
    end

    local plain = frame_grid(nil)
    local behind = frame_grid({ x = 2.5, y = 10.5, kind = "marker" })
    check("C11 sprite sau tuong bi che (khung hinh khong doi)",
          grid_diff(plain, behind) == 0, grid_diff(plain, behind))

    local infront = frame_grid({ x = 2.5, y = 20.2, kind = "marker" })
    check("C12 sprite truoc mat duoc ve (khung hinh phai doi)",
          grid_diff(plain, infront) > 100, grid_diff(plain, infront))

    -- Do sau: cang xa tuong cang thap (do bang so pixel tuong o cot giua).
    local function centre_wall_h(px_, py_, ang)
        rec.rects = {}
        in_frame = true
        R.frame(px_, py_, ang, nil)
        in_frame = false
        local g = raster(rec.rects)
        local h = 0
        for y = 0, SH - 1 do
            local c = at(g, 120, y)
            if c and c ~= INK then
                local is_bg = false
                for i = 1, #P.C.sky do
                    if c == P.C.sky[i] then is_bg = true end
                end
                for i = 1, #P.C.floor do
                    if c == P.C.floor[i] then is_bg = true end
                end
                if c == R.C_FAR then is_bg = true end
                if not is_bg then h = h + 1 end
            end
        end
        return h
    end
    local near_h = centre_wall_h(2.5, 21.5, -math.pi / 2)
    local far_h = centre_wall_h(2.5, 27.5, -math.pi / 2)
    check("C13 tuong o xa thap hon tuong o gan", far_h < near_h,
          "xa=" .. far_h .. " gan=" .. near_h)
end

-- =========================================================== D. Lai xe
do
    -- Dang o man hinh choi, vua bam BAT DAU o phan C.
    check("D1 bat dau: HP 100, tien 0, dang trong xe, dung diem xuat phat",
          PL.p.hp == 100 and PL.p.money == 0 and PL.p.in_car == true
          and PL.p.x == C.SPAWN.x and PL.p.y == C.SPAWN.y,
          string.format("hp=%s money=%s in_car=%s x=%s y=%s",
                        tostring(PL.p.hp), tostring(PL.p.money),
                        tostring(PL.p.in_car), tostring(PL.p.x), tostring(PL.p.y)))

    local rects = capture()
    check("D2 HUD doc ra HP 100 khop trang thai", read_hp() == 100, read_hp())
    check("D3 HUD doc ra tien 0 khop trang thai", read_money() == 0, tostring(read_money()))

    -- Chay thang 1 giay theo huong dang nhin (angle 0 = +x, duong mo).
    local x0 = PL.p.x
    local before = raster(rects)
    press("up")
    advance(100, 20)            -- 2 giay: 1 giay dau chi de tang toc (~2 o)
    release("up")
    local after = raster(capture())
    local moved = PL.p.x - x0
    check("D4 giu up thi xe chay dung huong dang nhin (+x)", moved > 5.0, moved)

    local diff = 0
    for y = 0, SH - 1 do
        for x = 0, SW - 1 do
            if before[y][x] ~= after[y][x] then diff = diff + 1 end
        end
    end
    check("D5 khung hinh doi khi xe chay", diff > 3000, diff)

    -- Quay 90 do roi dam vao day nha: phai mat HP.
    local hp0 = PL.p.hp
    for _ = 1, 40 do
        press("left")
        advance(50)
        release("left")
    end
    local crashed = false
    for _ = 1, 120 do
        press("up")
        advance(60)
        release("up")
        if PL.p.hp < hp0 then crashed = true break end
    end
    check("D6 dam vao tuong thi mat HP", crashed,
          string.format("hp %s -> %s", hp0, PL.p.hp))
    capture()   -- phai ve lai khung hinh roi moi doc HUD
    -- Thanh HP rong 72 px nen 1 px = 1.39%: chi khop trong sai so luong tu.
    check("D7 HUD HP khop voi trang thai sau khi dam (sai so 2%)",
          math.abs(read_hp() - PL.p.hp) <= 2,
          read_hp() .. " vs " .. PL.p.hp)

    -- Tua lai tu dau
    tap("softright")
    advance(16)
    tap("down"); tap("down"); tap("ok")
    advance(16)
    check("D8 CHOI LAI dua ve diem xuat phat va hoi day HP",
          PL.p.x == C.SPAWN.x and PL.p.y == C.SPAWN.y and PL.p.hp == 100
          and PL.p.money == 0,
          string.format("x=%s y=%s hp=%s", tostring(PL.p.x), tostring(PL.p.y),
                        tostring(PL.p.hp)))

    -- Lai toi cot moc theo 2 chang vuong goc (duong luoi).
    -- Quay TAI CHO truoc (khong dap ga) roi moi chay: neu vua chay vua quay thi
    -- xe veo vao le duong va ca vao day nha.
    local function drive_to(tx, ty, max_steps)
        for _ = 1, max_steps do
            local dx, dy = tx - PL.p.x, ty - PL.p.y
            if dx * dx + dy * dy < 0.36 then return true end
            local want = math.atan2(dy, dx)
            local d = want - PL.p.angle
            while d > math.pi do d = d - 2 * math.pi end
            while d < -math.pi do d = d + 2 * math.pi end
            if d > 0.12 then press("right")
            elseif d < -0.12 then press("left") end
            if math.abs(d) < 0.35 then press("up") end
            advance(80)
            release("up")
            release("left")
            release("right")
        end
        return false
    end

    local ok1 = drive_to(C.SPAWN.x, C.SPOTS[1][2], 300)
    local ok2 = drive_to(C.SPOTS[1][1], C.SPOTS[1][2], 300)
    check("D9 lai duoc toi cot moc theo duong luoi", ok1 and ok2,
          string.format("x=%.2f y=%.2f", PL.p.x, PL.p.y))
    check("D10 giao hang: cong 250$ va doi cot moc",
          PL.p.money == 250,
          string.format("money=%s x=%.2f y=%.2f", tostring(PL.p.money), PL.p.x, PL.p.y))
    capture()   -- phai ve lai khung hinh roi moi doc HUD
    check("D11 HUD tien khop sau khi giao", read_money() == 250, tostring(read_money()))

    -- Xuong xe roi kiem tra cac truong hop khong duoc phep len xe.
    tap("ok")
    advance(16)
    check("D12 ok lat trang thai len/xuong xe", PL.p.in_car == false, tostring(PL.p.in_car))

    -- O xa cho xe thi bam ok khong len duoc.
    PL.p.x, PL.p.y = C.SPAWN.x, C.SPAWN.y
    advance(16)
    tap("ok")
    advance(16)
    check("D13 ok khi xa xe thi khong len duoc", PL.p.in_car == false,
          tostring(PL.p.in_car))

    -- Di bo dung vao cot moc: khong duoc cong tien (phai ngoi xe).
    local money_before = PL.p.money
    local m2 = C.SPOTS[2]
    PL.p.x, PL.p.y = m2[1], m2[2]
    advance(16)
    check("D14 di bo vao cot moc khong cong tien", PL.p.money == money_before,
          tostring(PL.p.money))

    -- Dung ngay cho xe thi len duoc.
    PL.p.x, PL.p.y = PL.car.x, PL.car.y
    advance(16)
    tap("ok")
    advance(16)
    check("D15 dung gan xe thi len duoc", PL.p.in_car == true, tostring(PL.p.in_car))

    -- Het HP -> WASTED -> tu choi lai.
    -- "WASTED" ve bang font khoi (rect), khong qua engine.text — nen tim dong
    -- chu engine.text cua bang do ("Xe hong").
    PL.p.hp = 0
    advance(16)
    local _, texts = capture()
    local wasted = false
    for _, t in ipairs(texts) do
        if t.s:find("Xe hong", 1, true) then wasted = true end
    end
    check("D16 het HP hien man hinh WASTED", wasted)
    advance(2400, 1)
    check("D17 het WASTED thi choi lai tu dau",
          PL.p.hp == 100 and PL.p.money == 0
          and PL.p.x == C.SPAWN.x and PL.p.y == C.SPAWN.y,
          string.format("hp=%s money=%s", tostring(PL.p.hp), tostring(PL.p.money)))
end

-- =========================================================== E. Hop dong phim
do
    -- Phan loai man hinh dang hien tu CHINH khung hinh da ve, khong doan.
    local function screen_of()
        local _, texts = capture()
        local function has(s)
            for _, t in ipairs(texts) do
                if t.s:find(s, 1, true) then return true end
            end
            return false
        end
        if has("Xe hong") then return "wasted" end
        if has("PSEUDO-3D") then return "title" end
        -- KHONG dung "LAI XE": toast "LAI XE CHO GAN HON" o man hinh choi
        -- cung chua chuoi do => nhan nham man hinh. Dung cau chi co o
        -- man hinh huong dan.
        if has("BAM OK / SOFT-R") then return "help" end
        for _, t in ipairs(texts) do
            if t.s:match("^HP %d") then return "pause" end
        end
        for _, t in ipairs(texts) do
            if t.s:match("^%$%d+$") then return "play" end
        end
        return "?"
    end

    -- Muc nao cua menu tam dung dang duoc chon, suy ra tu vi tri bang chon.
    -- (Man hinh tam dung dat muc i tai y = 116 + (i-1)*26.)
    local function pause_index_of()
        local y = hot_panel_y(capture(), 100, 260)
        if not y then return nil end
        return math.floor((y - 116) / 26 + 0.5) + 1
    end

    -- Chon muc thu `target` trong menu tam dung bang VI TRI bang chon.
    local function pause_select(target)
        for _ = 1, 8 do
            if pause_index_of() == target then return true end
            tap("down")
        end
        return false
    end

    check("E1 bat dau phan E o man hinh choi", screen_of() == "play", screen_of())

    tap("softright")
    advance(16)
    check("E2 softright tu man hinh choi mo tam dung", screen_of() == "pause", screen_of())

    pause_select(2)             -- HUONG DAN
    tap("ok")
    advance(16)
    check("E3 chon HUONG DAN mo man hinh huong dan", screen_of() == "help", screen_of())

    local _, htexts = capture()
    local found, uniq = false, false
    for _, t in ipairs(htexts) do
        -- Hai cau chi co o man hinh huong dan, khong xuat hien trong toast nao.
        if t.s:find("tang toc", 1, true) then found = true end
        if t.s:find("phai chay", 1, true) then uniq = true end
    end
    check("E4 man hinh huong dan hien noi dung", found and uniq,
          tostring(found) .. "/" .. tostring(uniq))

    tap("ok")
    advance(16)
    check("E5 ok tu huong dan quay ve dung man hinh truoc (tam dung)",
          screen_of() == "pause", screen_of())

    pause_select(1)             -- TIEP TUC
    tap("ok")
    advance(16)
    check("E6 chon TIEP TUC quay lai man hinh choi", screen_of() == "play", screen_of())

    -- `fresh`: giu ok (runtime gui lai keypressed) KHONG duoc lat xe lien tuc.
    local flips, prev = 0, PL.p.in_car
    for _ = 1, 6 do
        press("ok")             -- khong release => repeat, fresh = false
        advance(16)
        if PL.p.in_car ~= prev then flips = flips + 1; prev = PL.p.in_car end
    end
    check("E7 giu ok chi lat xe MOT lan (fresh chan repeat)", flips <= 1, flips)
    release("ok")

    -- Nha roi bam lai thi lat duoc tiep.
    local before_flip = PL.p.in_car
    tap("ok")
    advance(16)
    check("E8 nha roi bam lai thi lat duoc tiep", PL.p.in_car ~= before_flip,
          tostring(before_flip) .. " -> " .. tostring(PL.p.in_car))

    -- Dieu huong PHAI an khi giu (repeat) — neu khong, menu khong cuon nhanh.
    tap("softright")
    advance(16)
    check("E9 dang o tam dung de kiem tra cuon menu", screen_of() == "pause", screen_of())
    -- Phai bam 3 lan KHONG nha: lan 1 la `fresh`, lan 2-3 la repeat. Neu repeat
    -- bi chan thi chi nhich duoc 1 muc. (Ban dau toi chi bam 2 lan, ma lan 2 da
    -- du de nhich — guard xanh sai — da mac that.)
    local i0 = pause_index_of()
    press("down")
    advance(16)
    press("down")
    advance(16)
    press("down")
    advance(16)
    release("down")
    local i3 = pause_index_of()
    check("E10 giu down cuon duoc 3 muc (repeat khong bi chan)",
          i0 == 1 and i3 == 4, tostring(i0) .. " -> " .. tostring(i3))

    -- THOAT goi E.exit()
    pause_select(4)
    tap("ok")
    check("E11 muc THOAT goi E.exit()", rec.exit == true, tostring(rec.exit))
    rec.exit = false

    -- Hop dong 21 ten phim
    local K = require("src.keypad")
    check("E12 hop dong co dung 21 ten phim", #K.NAMES == 21, #K.NAMES)
    local bad = {}
    for _, name in ipairs(K.NAMES) do
        local got = K.press(name)
        if got ~= name then bad[#bad + 1] = name end
        K.release(name)
    end
    check("E13 ca 21 ten phim deu hop le", #bad == 0, table.concat(bad, ","))
    check("E14 ten phim KHONG hop le bi tu choi", K.press("KEY_UP") == nil)
    check("E15 ten phim chu HOA van nhan (runtime gui chu thuong la chuan)",
          K.press("UP") == "up")
end

-- =========================================================== F. Ky luat API
do
    check("F1 khong goi ham nao ngoai API cong bo", #rec.misses == 0,
          table.concat(rec.misses, ","))

    -- Kieu tham so: phai khop runtime_bridge.c. Mot mau `nil` o day chinh la
    -- "bad argument #4" tren may that — dung loi da lam man hinh huong dan chet
    -- ma ca harness lan validator tinh deu khong thay.
    check("F2 khong co loi goi sai kieu tham so", #rec.args == 0,
          table.concat(rec.args, " | ", 1, math.min(3, #rec.args)))

    -- Bang mau: gom ca mau cua `engine.text` va gom MOI man hinh da di qua
    -- (loi da mac nam o man hinh huong dan, khong phai khung hinh choi).
    local strays = {}
    for c in pairs(rec.colours) do
        if not PALETTE[c] then strays[#strays + 1] = tostring(c) end
    end
    table.sort(strays)
    check("F3 moi mau tren MOI man hinh deu thuoc bang mau", #strays == 0,
          table.concat(strays, ",", 1, math.min(4, #strays)))

    -- Chu phai nam trong man hinh. Dung be rong DO THAT cua font firmware
    -- (ADVANCE), khong dung uoc luong cua chinh template — neu khong thi phep
    -- kiem tra chi xac nhan lai gia dinh cua no.
    local over = {}
    for _, t in ipairs(rec.all_texts) do
        local w = math.ceil(#t.s * ADVANCE)
        if t.x < 0 or t.x + w > SW then
            over[#over + 1] = string.format("%q x=%d w=%d", t.s, t.x, w)
        end
    end
    check("F4 khong dong chu nao tran ra ngoai man hinh", #over == 0,
          #over .. " dong: " .. table.concat(over, " | "))
end

-- ---------------------------------------------------------------- ket qua
print("")
print(string.format("TONG: %d kiem tra, %d loi", checks, failures))
if failures > 0 then
    os.exit(1)
end
print("PASS: Pop Art City 3D")
