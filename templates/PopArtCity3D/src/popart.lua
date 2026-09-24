-- src/popart.lua — "ngon ngu thi giac" pop-art cho LuaS30 / MRE.
--
-- Nguon that: doc/reference/API.md + engine/src/runtime_bridge.c.
-- Chi dung duoc: color clear rect frame line text image image_region set_font
-- text_width font_height flush tick_ms exit log.
-- KHONG co pixel / vline / hline. KHONG co alpha, KHONG co blend, KHONG co scale
-- anh. Moi thu o day vi vay deu la RECT DAC chong len nhau.
--
-- Vi khong co alpha nen "khoi xa" (depth fog) KHONG the pha mau tai cho: moi
-- mau tuong phai duoc TRON TRUOC voi mau khoi thanh N sac do roi chon theo
-- khoang cach. Do la ly do ton tai cua shade4().
--
-- Lua 5.1 (vendor/lua-5.1.5): khong co //, khong co toan tu bit, khong co goto.

local E = engine

local M = {}

M.W = (E and E.W) or 240
M.H = (E and E.H) or 320

-- ---------------------------------------------------------------------------
-- Mau khoi (fog). Tim dam = bong pop-art, khong phai xam.
-- ---------------------------------------------------------------------------
local FOG = { 58, 26, 96 }

-- Ti le tron voi FOG theo 4 muc khoang cach (0 = gan nhat).
local SHADE_MIX = { 0.00, 0.28, 0.54, 0.76 }
-- Toi dan nhe o xa de doc duoc chieu sau ngay ca khi mau nen da toi.
local SHADE_DIM = { 1.00, 0.90, 0.78, 0.66 }

local function clamp255(v)
    if v < 0 then return 0 end
    if v > 255 then return 255 end
    return math.floor(v + 0.5)
end

-- Tra ve r, g, b da tron voi FOG va lam toi theo muc `level` (0..3).
function M.shade_rgb(r, g, b, level)
    if level < 0 then level = 0 end
    if level > 3 then level = 3 end
    local t = SHADE_MIX[level + 1]
    local k = (1 - t) * SHADE_DIM[level + 1]
    local f = t
    return clamp255(r * k + FOG[1] * f),
           clamp255(g * k + FOG[2] * f),
           clamp255(b * k + FOG[3] * f)
end

-- Bang N sac do cho MOT mau nen: shades(base, n) -> { c0, c1, ..., c(n-1) }
function M.shade4(r, g, b)
    local out = {}
    for i = 0, 3 do
        local sr, sg, sb = M.shade_rgb(r, g, b, i)
        out[i + 1] = E.color(sr, sg, sb)
    end
    return out
end

-- ---------------------------------------------------------------------------
-- Bang mau
-- ---------------------------------------------------------------------------
M.C = {}

M.C.ink      = E.color(12, 8, 24)        -- vien den (xanh dam, khong den tuyet doi)
M.C.paper    = E.color(242, 242, 242)
M.C.hot      = E.color(255, 45, 120)     -- hong nong
M.C.sun      = E.color(255, 210, 63)     -- vang
M.C.cyan     = E.color(0, 194, 209)
M.C.orange   = E.color(255, 107, 53)
M.C.lime     = E.color(168, 225, 12)
M.C.dim      = E.color(168, 150, 200)

-- Mau nen phu. De trong MOT cho: harness kiem tra moi mau duoc ve deu phai
-- nam trong bang mau nay (bat loi go tay mot ma hex giua file).
M.C.deep     = E.color(18, 10, 30)     -- nen bang mo (tam dung / wasted)
M.C.chip_dim = E.color(24, 14, 40)     -- chip menu khong duoc chon
M.C.bar_bg   = E.color(30, 18, 46)     -- long thanh chi so
M.C.check_a  = E.color(26, 16, 44)     -- caro man hinh tinh
M.C.check_b  = E.color(32, 20, 54)

-- Nen troi: 6 dai ngang, gan duong chan troi sang nhat.
M.C.sky = {}
do
    local bands = {
        { 92, 26, 128 }, { 168, 32, 130 }, { 255, 45, 120 },
        { 255, 110, 78 }, { 255, 168, 54 }, { 255, 214, 92 },
    }
    for i = 1, #bands do
        M.C.sky[i] = E.color(bands[i][1], bands[i][2], bands[i][3])
    end
end

-- Nen duong: 5 dai, cang gan cang sang.
M.C.floor = {}
do
    local bands = {
        { 116, 92, 170 }, { 100, 78, 156 }, { 84, 64, 140 },
        { 70, 52, 122 }, { 58, 42, 104 },
    }
    for i = 1, #bands do
        M.C.floor[i] = E.color(bands[i][1], bands[i][2], bands[i][3])
    end
end

-- Toa nha: moi loai mot bang 4 sac do + mot he so cao.
M.BUILD = {
    { name = "cyan",    r = 0,   g = 194, b = 209, hs = 1.00 },
    { name = "yellow",  r = 255, g = 210, b = 63,  hs = 1.35 },
    { name = "orange",  r = 255, g = 107, b = 53,  hs = 0.85 },
    { name = "magenta", r = 255, g = 45,  b = 120, hs = 1.75 },
    { name = "lime",    r = 168, g = 225, b = 12,  hs = 1.15 },
    { name = "paper",   r = 242, g = 242, b = 242, hs = 2.10 },
}
for i = 1, #M.BUILD do
    local b = M.BUILD[i]
    b.shades = M.shade4(b.r, b.g, b.b)
end

-- ---------------------------------------------------------------------------
-- Hinh hoc
-- ---------------------------------------------------------------------------

-- Khung tran vien day 2 px (kieu o truyen): 1 rect nen den + 1 rect ruot.
function M.panel(x, y, w, h, fill, border, thick)
    thick = thick or 2
    border = border or M.C.ink
    E.rect(x - thick, y - thick, w + thick * 2, h + thick * 2, border)
    E.rect(x, y, w, h, fill)
end

-- Nua tren / nua duoi cua mot rect: dung de ve "vien" lech mau kieu pop-art
-- ma khong ton them mot lan goi frame (frame = 4 lan fill).
function M.top_half(x, y, w, h, c)
    E.rect(x, y, w, math.max(1, math.floor(h / 2)), c)
end

-- Luoi caro (checker) — hoa tiet pop-art, dung cho nen menu.
function M.checker(x, y, w, h, ca, cb, cell)
    cell = cell or 8
    local gy = 0
    local py = y
    while py < y + h do
        local step = math.min(cell, y + h - py)
        local gx = 0
        local px = x
        while px < x + w do
            local sw = math.min(cell, x + w - px)
            local c = ca
            if (gx + gy) % 2 == 1 then c = cb end
            E.rect(px, py, sw, step, c)
            px = px + sw
            gx = gx + 1
        end
        py = py + step
        gy = gy + 1
    end
end

-- ---------------------------------------------------------------------------
-- Font khoi 3x5 (rect). Font firmware chi toi ~10 px va khong scale duoc, nen
-- tieu de / so tien lon phai tu ve.
-- Moi glyph = 5 hang, moi hang la mask 3 bit (bit 2 = trai).
-- ---------------------------------------------------------------------------
local GLYPH = {
    ["0"] = { 7, 5, 5, 5, 7 }, ["1"] = { 2, 6, 2, 2, 7 },
    ["2"] = { 7, 1, 7, 4, 7 }, ["3"] = { 7, 1, 7, 1, 7 },
    ["4"] = { 5, 5, 7, 1, 1 }, ["5"] = { 7, 4, 7, 1, 7 },
    ["6"] = { 7, 4, 7, 5, 7 }, ["7"] = { 7, 1, 2, 2, 2 },
    ["8"] = { 7, 5, 7, 5, 7 }, ["9"] = { 7, 5, 7, 1, 7 },
    ["A"] = { 7, 5, 7, 5, 5 }, ["B"] = { 6, 5, 6, 5, 6 },
    ["C"] = { 7, 4, 4, 4, 7 }, ["D"] = { 6, 5, 5, 5, 6 },
    ["E"] = { 7, 4, 7, 4, 7 }, ["F"] = { 7, 4, 7, 4, 4 },
    ["G"] = { 7, 4, 5, 5, 7 }, ["H"] = { 5, 5, 7, 5, 5 },
    ["I"] = { 7, 2, 2, 2, 7 }, ["J"] = { 1, 1, 1, 5, 7 },
    ["K"] = { 5, 5, 6, 5, 5 }, ["L"] = { 4, 4, 4, 4, 7 },
    ["M"] = { 5, 7, 7, 5, 5 }, ["N"] = { 6, 5, 5, 5, 5 },
    ["O"] = { 7, 5, 5, 5, 7 }, ["P"] = { 7, 5, 7, 4, 4 },
    ["Q"] = { 7, 5, 5, 7, 3 }, ["R"] = { 7, 5, 7, 6, 5 },
    ["S"] = { 7, 4, 7, 1, 7 }, ["T"] = { 7, 2, 2, 2, 2 },
    ["U"] = { 5, 5, 5, 5, 7 }, ["V"] = { 5, 5, 5, 5, 2 },
    ["W"] = { 5, 5, 7, 7, 5 }, ["X"] = { 5, 5, 2, 5, 5 },
    ["Y"] = { 5, 5, 7, 2, 2 }, ["Z"] = { 7, 1, 2, 4, 7 },
    ["$"] = { 3, 6, 6, 3, 6 }, ["-"] = { 0, 0, 7, 0, 0 },
    ["+"] = { 0, 2, 7, 2, 0 }, ["."] = { 0, 0, 0, 0, 2 },
    [":"] = { 0, 2, 0, 2, 0 }, ["/"] = { 1, 1, 2, 4, 4 },
    ["!"] = { 2, 2, 2, 0, 2 }, ["?"] = { 7, 1, 3, 0, 2 },
    ["*"] = { 5, 2, 5, 0, 0 }, ["<"] = { 1, 2, 4, 2, 1 },
    [">"] = { 4, 2, 1, 2, 4 }, ["%"] = { 5, 1, 2, 4, 5 },
    ["'"] = { 2, 2, 0, 0, 0 }, [" "] = { 0, 0, 0, 0, 0 },
}

M.GLYPH = GLYPH

-- Chieu rong chuoi font khoi, tinh bang pixel (chua ke `scale`).
-- Moi glyph 3 px + 1 px khoang trang; khoang trang cuoi chuoi bi bo.
function M.text_w(s, scale)
    scale = scale or 1
    return math.max(0, #s * 4 - 1) * scale
end

-- Ve chuoi bang font khoi 3x5. Tra ve chieu rong da ve.
-- Gop cac bit lien tiep tren cung mot hang thanh MOT rect => trung binh
-- ~5-7 rect cho mot glyph o scale 1, thay vi 15.
function M.text(x, y, s, colour, scale)
    scale = scale or 1
    s = tostring(s or ""):upper()
    local cx = x
    for i = 1, #s do
        local rows = GLYPH[s:sub(i, i)]
        if rows then
            for row = 1, 5 do
                local mask = rows[row]
                if mask ~= 0 then
                    local col = 0
                    while col < 3 do
                        local bit = 4 / (2 ^ col)  -- col 0 -> 4, col 1 -> 2, col 2 -> 1
                        if mask >= bit then
                            local run = 1
                            mask = mask - bit
                            local nxt = 4 / (2 ^ (col + 1))
                            while col + run < 3 and mask >= nxt and nxt > 0 do
                                mask = mask - nxt
                                run = run + 1
                                nxt = nxt / 2
                            end
                            E.rect(cx + col * scale, y + (row - 1) * scale,
                                   run * scale, scale, colour)
                            col = col + run
                        else
                            col = col + 1
                        end
                    end
                end
            end
        end
        cx = cx + 4 * scale
    end
    return M.text_w(s, scale)
end

-- Ve chuoi can le phai / giua.
function M.text_right(x_right, y, s, colour, scale)
    return M.text(x_right - M.text_w(tostring(s or ""), scale), y, s, colour, scale)
end

function M.text_center(x, y, w, s, colour, scale)
    return M.text(x + math.floor((w - M.text_w(tostring(s or ""), scale)) / 2),
                  y, s, colour, scale)
end

-- Bong do chu (pop-art): ve lech 1*scale xuong duoi roi ve de len.
function M.text_shadow(x, y, s, colour, shadow, scale)
    M.text(x + (scale or 1), y + (scale or 1), s, shadow or M.C.ink, scale)
    return M.text(x, y, s, colour, scale)
end

return M
