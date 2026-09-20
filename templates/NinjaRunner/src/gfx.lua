-- Ninja Runner: palette, pixel font, sprites, nen khi synthwave, rooftop brick.
local E = engine
local M = {}

local cache = {}
function M.col(r, g, b)
    local k = r * 65536 + g * 256 + b
    local c = cache[k]
    if not c then
        c = E.color(r, g, b)
        cache[k] = c
    end
    return c
end

local C = {}
C.black    = M.col(8, 5, 16)
C.bar      = M.col(16, 10, 30)
C.white    = M.col(235, 240, 248)
C.dim      = M.col(120, 110, 150)
C.cyan     = M.col(46, 222, 206)
C.cyanHi   = M.col(185, 255, 240)
C.pink     = M.col(240, 70, 125)
C.pinkDk   = M.col(160, 40, 95)
C.violet   = M.col(90, 55, 140)
-- sky bands
C.sky = {
    M.col(16, 9, 34), M.col(30, 12, 52), M.col(52, 16, 74),
    M.col(84, 22, 88), M.col(122, 30, 92), M.col(168, 46, 82),
    M.col(212, 74, 66), M.col(236, 120, 60), M.col(246, 172, 82),
    M.col(250, 214, 116),
}
C.star     = M.col(255, 235, 170)
C.cloud    = M.col(64, 18, 66)
C.cloudHi  = M.col(96, 28, 82)
C.sunTop   = M.col(252, 214, 110)
C.sunMid   = M.col(246, 138, 84)
C.sunLow   = M.col(238, 84, 122)
C.far      = M.col(26, 14, 46)
C.mid      = M.col(38, 21, 64)
C.midWinC  = M.col(64, 190, 196)
C.midWinP  = M.col(204, 62, 122)
C.brick    = M.col(26, 22, 52)
C.mortar   = M.col(58, 38, 92)
C.edgeGlow = M.col(120, 60, 160)
-- ninja palette
C.nHead    = M.col(30, 27, 52)
C.nBody    = M.col(52, 48, 88)
C.nDark    = M.col(36, 32, 62)
C.nVisor   = M.col(56, 232, 216)
C.nScarf   = M.col(240, 70, 125)
C.nScarf2  = M.col(176, 44, 96)
C.nFoot    = M.col(232, 238, 246)
M.C = C

-- deterministic pseudo random for static scenery (Lua 5.1: no bit ops)
function M.hash(n)
    local x = (n * 7919 + 104729) % 65536
    x = (x * 31 + 17) % 65536
    x = (x * 379 + 1231) % 65536
    return x / 65536
end

-- runtime clip_ok() drops the WHOLE rect when it touches the border,
-- so clamp every draw call to the screen ourselves
function M.srect(x, y, w, h, c)
    local x2, y2 = x + w, y + h
    if x < 0 then x = 0 end
    if y < 0 then y = 0 end
    if x2 > 240 then x2 = 240 end
    if y2 > 320 then y2 = 320 end
    if x2 > x and y2 > y then E.rect(x, y, x2 - x, y2 - y, c) end
end

-- ---------------------------------------------------------------- pixel font
-- 5x7 glyphs (rows packed as 5-bit strings), UTF-8 Vietnamese via src/vnfont.
local VN = require("src.vnfont")

local GLYPH = {
    A = "01110,10001,10001,11111,10001,10001,10001",
    B = "11110,10001,10001,11110,10001,10001,11110",
    C = "01111,10000,10000,10000,10000,10000,01111",
    D = "11110,10001,10001,10001,10001,10001,11110",
    E = "11111,10000,10000,11110,10000,10000,11111",
    F = "11111,10000,10000,11110,10000,10000,10000",
    G = "01111,10000,10000,10111,10001,10001,01111",
    H = "10001,10001,10001,11111,10001,10001,10001",
    I = "11111,00100,00100,00100,00100,00100,11111",
    J = "00111,00010,00010,00010,00010,10010,01100",
    K = "10001,10010,10100,11000,10100,10010,10001",
    L = "10000,10000,10000,10000,10000,10000,11111",
    M = "10001,11011,10101,10101,10001,10001,10001",
    N = "10001,11001,10101,10011,10001,10001,10001",
    O = "01110,10001,10001,10001,10001,10001,01110",
    P = "11110,10001,10001,11110,10000,10000,10000",
    Q = "01110,10001,10001,10001,10101,10010,01101",
    R = "11110,10001,10001,11110,10100,10010,10001",
    S = "01111,10000,10000,01110,00001,00001,11110",
    T = "11111,00100,00100,00100,00100,00100,00100",
    U = "10001,10001,10001,10001,10001,10001,01110",
    V = "10001,10001,10001,10001,10001,01010,00100",
    W = "10001,10001,10001,10101,10101,11011,10001",
    X = "10001,10001,01010,00100,01010,10001,10001",
    Y = "10001,10001,01010,00100,00100,00100,00100",
    Z = "11111,00001,00010,00100,01000,10000,11111",
    a = "00000,00000,01110,00001,01111,10001,01111",
    b = "10000,10000,11110,10001,10001,10001,11110",
    c = "00000,00000,01111,10000,10000,10000,01111",
    d = "00001,00001,01111,10001,10001,10001,01111",
    e = "00000,00000,01110,10001,11111,10000,01110",
    f = "00110,01000,01000,11110,01000,01000,01000",
    g = "00000,01111,10001,10001,01111,00001,01110",
    h = "10000,10000,11110,10001,10001,10001,10001",
    i = "00100,00000,01100,00100,00100,00100,01110",
    j = "00010,00000,00110,00010,00010,10010,01100",
    k = "10000,10000,10010,10100,11000,10100,10010",
    l = "01100,00100,00100,00100,00100,00100,01110",
    m = "00000,00000,10110,10101,10101,10101,10101",
    n = "00000,00000,11110,10001,10001,10001,10001",
    o = "00000,00000,01110,10001,10001,10001,01110",
    p = "00000,00000,11110,10001,10001,11110,10000",
    q = "00000,00000,01111,10001,10001,01111,00001",
    r = "00000,00000,10110,11001,10000,10000,10000",
    s = "00000,00000,01111,10000,01110,00001,11110",
    t = "01000,01000,11110,01000,01000,01001,00110",
    u = "00000,00000,10001,10001,10001,10011,01101",
    v = "00000,00000,10001,10001,10001,01010,00100",
    w = "00000,00000,10001,10001,10101,11111,01010",
    x = "00000,00000,10001,01010,00100,01010,10001",
    y = "00000,10001,10001,01111,00001,00010,01100",
    z = "00000,00000,11111,00010,00100,01000,11111",
    ["0"] = "01110,10001,10011,10101,11001,10001,01110",
    ["1"] = "00100,01100,00100,00100,00100,00100,01110",
    ["2"] = "01110,10001,00001,00010,00100,01000,11111",
    ["3"] = "11110,00001,00001,01110,00001,00001,11110",
    ["4"] = "00010,00110,01010,10010,11111,00010,00010",
    ["5"] = "11111,10000,11110,00001,00001,10001,01110",
    ["6"] = "00110,01000,10000,11110,10001,10001,01110",
    ["7"] = "11111,00001,00010,00100,01000,01000,01000",
    ["8"] = "01110,10001,10001,01110,10001,10001,01110",
    ["9"] = "01110,10001,10001,01111,00001,00010,01100",
    ["."] = "00000,00000,00000,00000,00000,01100,01100",
    [","] = "00000,00000,00000,00000,01100,00100,01000",
    ["-"] = "00000,00000,00000,11111,00000,00000,00000",
    ["!"] = "00100,00100,00100,00100,00100,00000,00100",
    ["?"] = "01110,10001,00001,00110,00100,00000,00100",
    [":"] = "00000,01100,01100,00000,01100,01100,00000",
    ["/"] = "00001,00010,00010,00100,01000,01000,10000",
    ["("] = "00010,00100,01000,01000,01000,00100,00010",
    [")"] = "01000,00100,00010,00010,00010,00100,01000",
    ["+"] = "00000,00100,00100,11111,00100,00100,00000",
    ["="] = "00000,00000,11111,00000,11111,00000,00000",
    ["<"] = "00010,00100,01000,10000,01000,00100,00010",
    [">"] = "01000,00100,00010,00001,00010,00100,01000",
    ["*"] = "00000,10101,01110,11111,01110,10101,00000",
    ["'"] = "00100,00100,00000,00000,00000,00000,00000",
    ["%"] = "11001,11010,00010,00100,01001,01011,10011",
    ["#"] = "01010,01010,11111,01010,11111,01010,01010",
    ["@"] = "01110,10001,10111,10101,10111,10000,01111",
    ["&"] = "01100,10010,10100,01000,10101,10010,01101",
    ["["] = "01110,01000,01000,01000,01000,01000,01110",
    ["]"] = "01110,00010,00010,00010,00010,00010,01110",
    ["_"] = "00000,00000,00000,00000,00000,00000,11111",
    ["©"] = "01110,10001,10111,10100,10111,10001,01110",
    ["("] = "00010,00100,01000,01000,01000,00100,00010",
    [" "] = "00000,00000,00000,00000,00000,00000,00000",
}

-- tone marks: slot 2 (rows y-4..y-3), shape marks: slot 1 (rows y-2..y-1)
local MARK2 = {
    ACUTE = "00010,00100",
    GRAVE = "00100,00010",
    HOOK  = "00110,00010",
    TILDE = "01010",
    DOTA  = "00100",
}
local MARK1 = {
    CIRC  = "00100,01010",
    BREVE = "01010,00100",
    HORN  = "00001,00011",
}

local function glyph_rows(bits, x, y, scale, color)
    local row = 0
    for bits2 in bits:gmatch("[01]+") do
        for cx = 1, 5 do
            if bits2:sub(cx, cx) == "1" then
                M.srect(x + (cx - 1) * scale, y + row * scale, scale, scale, color)
            end
        end
        row = row + 1
    end
end

local function cluster_len(b)
    if b < 128 then return 1 elseif b < 224 then return 2
    elseif b < 240 then return 3 else return 4 end
end

function M.ptext_width(s, scale)
    scale = scale or 1
    local n, i = 0, 1
    while i <= #s do
        i = i + cluster_len(s:byte(i))
        n = n + 1
    end
    return n * 6 * scale
end

-- y = top of the 7-row base; marks may extend 4px above and 1px below
function M.ptext(x, y, s, color, scale)
    scale = scale or 1
    local col, i = 0, 1
    while i <= #s do
        local len = cluster_len(s:byte(i))
        local ch = s:sub(i, i + len - 1)
        i = i + len
        local spec = VN[ch]
        local base = spec and spec[1] or ch
        local g = GLYPH[base] or GLYPH["?"]
        local gx = x + col * 6 * scale
        glyph_rows(g, gx, y, scale, color)
        if spec then
            for k = 2, #spec do
                local m = spec[k]
                if m == "DOTB" then
                    M.srect(gx + 2 * scale, y + 8 * scale, scale, scale, color)
                elseif m == "STROKE" then
                    M.srect(gx + 3 * scale, y + 3 * scale, 4 * scale, scale, color)
                elseif MARK1[m] then
                    glyph_rows(MARK1[m], gx, y - 2 * scale, scale, color)
                else
                    glyph_rows(MARK2[m], gx, y - 4 * scale, scale, color)
                end
            end
        end
        col = col + 1
    end
end

function M.ptext_center(cx, y, s, color, scale)
    M.ptext(math.floor(cx - M.ptext_width(s, scale) / 2), y, s, color, scale)
end

-- ------------------------------------------------------------------- sprites
local SPR = {
    run_a = {
        "..............",
        "....HHHHHH....",
        "...HHHHHHHH...",
        "...HHHHHHHH...",
        "...HCCCCCC....",
        "...HHHHHHHH...",
        "..s..BBBBB....",
        ".SS..BBBBB....",
        "SSS..BBBB.....",
        ".S...BBBB.....",
        ".....BBB......",
        "....BBBB......",
        "....BB.BB.....",
        "...BB...BB....",
        "...B.....B....",
        "..DD.....DD...",
        "..FF.....FF...",
        "..............",
    },
    run_b = {
        "..............",
        "....HHHHHH....",
        "...HHHHHHHH...",
        "...HHHHHHHH...",
        "...HCCCCCC....",
        "...HHHHHHHH...",
        "..s..BBBBB....",
        ".SS..BBBBB....",
        "SSS..BBBB.....",
        ".S...BBBB.....",
        ".....BBBB.....",
        ".....BBB......",
        ".....BBBB.....",
        ".....BB.B.....",
        ".....B..B.....",
        "....DD..DD....",
        "....FF..FF....",
        "..............",
    },
    run_c = {
        "..............",
        "....HHHHHH....",
        "...HHHHHHHH...",
        "...HHHHHHHH...",
        "...HCCCCCC....",
        "...HHHHHHHH...",
        "..s..BBBBB....",
        ".SS..BBBBB....",
        "SSS..BBBB.....",
        ".S...BBBB.....",
        ".....BBB......",
        "....BBBB......",
        "...BB...BB....",
        "...B.....BB...",
        "..B.......B...",
        "..DD.....DD...",
        "..FF.....FF...",
        "..............",
    },
    jump = {
        "..............",
        "....HHHHHH....",
        "...HHHHHHHH...",
        "...HHHHHHHH...",
        "...HCCCCCC....",
        "...HHHHHHHH...",
        "..s..BBBBB....",
        ".SS.BBBBBB....",
        "SSS.BBBBB.....",
        ".S..BBBB......",
        "....BBBB......",
        "....BBB.......",
        "...BB.BB......",
        "...B...BB.....",
        "..BB....B.....",
        "..FF....DD....",
        ".........FF...",
        "..............",
    },
    fall = {
        "..............",
        "....HHHHHH....",
        "...HHHHHHHH...",
        "...HHHHHHHH...",
        "...HCCCCCC....",
        "...HHHHHHHH...",
        "..s..BBBBB....",
        ".SS..BBBBB....",
        "SSS..BBBB.....",
        ".S...BBBB.....",
        ".....BBB......",
        "....BBBB......",
        "....BB..BB....",
        "....B....B....",
        "...B......B...",
        "...D......D...",
        "...F......F...",
        "..............",
    },
    hurt = {
        "..............",
        "..............",
        "....HHHHHH....",
        "...HHHHHHHH...",
        "...HCCCCCC....",
        "...HHHHHHHH...",
        ".....BBBBB..s.",
        ".....BBBBB.SS.",
        ".....BBBB..SSS",
        ".....BBBB...S.",
        "......BBB.....",
        ".....BBBB.....",
        ".....BB.BB....",
        "....BB...BB...",
        "...BB.....B...",
        "...D......DD..",
        "..FF......FF..",
        "..............",
    },
}
local SPRC = { H = C.nHead, B = C.nBody, D = C.nDark, C = C.nVisor,
               S = C.nScarf, s = C.nScarf2, F = C.nFoot }
M.SPR = SPR
M.SPRW, M.SPRH = 14, 18

function M.drawSprite(name, x, y, scale)
    local rows = SPR[name]
    if not rows then return end
    for r = 1, M.SPRH do
        local line = rows[r]
        for cx = 1, M.SPRW do
            local c = SPRC[line:sub(cx, cx)]
            if c then
                M.srect(x + (cx - 1) * scale, y + (r - 1) * scale, scale, scale, c)
            end
        end
    end
end

-- trailing scarf ribbon, drawn behind the head
function M.drawScarf(hx, hy, t, scale, flapping)
    local amp = flapping and 2.2 or 1.2
    for i = 1, 7 do
        local px = hx - i * (scale + 1)
        local py = hy + math.floor(math.sin(t * 0.35 + i * 1.1) * amp) * scale
        M.srect(px, py, scale + 1, scale, i % 2 == 0 and C.nScarf2 or C.nScarf)
        if i == 3 or i == 6 then
            M.srect(px - scale, py - scale, scale, scale, C.nScarf)
        end
    end
end

-- ------------------------------------------------------------------ scenery
M.HORIZON = 176

function M.sky(t)
    local bands = #C.sky
    local bh = math.ceil(M.HORIZON / bands)
    for i = 1, bands do
        E.rect(0, (i - 1) * bh, 240, bh, C.sky[i])
    end
    for i = 1, 26 do
        local sx = math.floor(M.hash(i * 7 + 1) * 239)
        local sy = math.floor(M.hash(i * 13 + 5) * 52)
        local tw = M.hash(i * 3 + math.floor((t or 0) * 2)) > 0.75
        if not tw then E.rect(sx, sy, 1, 1, C.star) end
    end
    -- synthwave sun
    local cx, cy, rad = 168, 118, 30
    for dy = -rad, rad do
        local half = math.floor(math.sqrt(rad * rad - dy * dy))
        local frac = (dy + rad) / (2 * rad)
        local col = frac < 0.45 and C.sunTop or (frac < 0.75 and C.sunMid or C.sunLow)
        if (dy + rad) % 5 < 3 or dy < 0 then
            E.rect(cx - half, cy + dy, half * 2 + 1, 1, col)
        end
    end
    -- clouds (dithered slabs)
    for i = 1, 7 do
        local cxx = (M.hash(i * 31 + 9) * 300 + (t or 0) * 2) % 300 - 40
        local cyy = 30 + M.hash(i * 17 + 3) * 90
        local cw = 34 + M.hash(i * 23) * 40
        M.srect(math.floor(cxx), math.floor(cyy), math.floor(cw), 3, C.cloud)
        M.srect(math.floor(cxx + 6), math.floor(cyy - 3), math.floor(cw * 0.6), 3, C.cloud)
        M.srect(math.floor(cxx + 4), math.floor(cyy + 3), math.floor(cw * 0.7), 2, C.cloudHi)
    end
end

-- parallax silhouette skyline; windows stable per building, some flicker when t given
function M.skyline(cam, parallax, baseY, body, win, seed, slot, hmin, hmax, t)
    local off = cam * parallax
    local first = math.floor(off / slot) - 1
    for i = first, first + math.ceil(240 / slot) + 1 do
        local h = hmin + M.hash(seed + i * 37) * (hmax - hmin)
        h = math.floor(h / 4) * 4
        local w = slot - 2 - math.floor(M.hash(seed + i * 91) * 4)
        local x = math.floor(i * slot - off)
        M.srect(x, baseY - h, w, h, body)
        -- antenna
        if M.hash(seed + i * 11) > 0.72 then
            M.srect(x + w / 2, baseY - h - 8, 1, 8, body)
            M.srect(x + w / 2, baseY - h - 9, 1, 1, C.pink)
        end
        if win then
            local lit = M.hash(seed + i * 53)
            for wy = baseY - h + 6, baseY - 8, 10 do
                for wx = x + 3, x + w - 4, 7 do
                    local k = M.hash(seed + wx * 3 + wy * 7)
                    local on = k < lit * 0.55
                    if t and k > 0.40 and k < 0.46 then
                        on = math.floor(t * 2 + wx + wy) % 2 == 0
                    end
                    if on then
                        M.srect(wx, wy, 2, 3, k < 0.2 and C.midWinP or C.midWinC)
                    end
                end
            end
        end
    end
end

-- brick rooftop platform; x,y = screen pos of top-left, w wide, drop to bottom
function M.rooftop(x, y, w, bottom)
    bottom = bottom or 320
    local h = bottom - y
    if h <= 0 or w <= 0 then return end
    M.srect(x, y + 4, w, h - 4, C.brick)
    -- neon edge
    M.srect(x, y, w, 1, C.cyanHi)
    M.srect(x, y + 1, w, 2, C.cyan)
    M.srect(x, y + 3, w, 1, C.edgeGlow)
    -- mortar rows + staggered vertical joints
    local row = 0
    local yy = y + 4 + 6
    while yy < bottom do
        M.srect(x, yy, w, 1, C.mortar)
        local shift = (row % 2) * 7
        local xx = x + 7 + shift
        while xx < x + w - 2 do
            M.srect(xx, yy - 5, 1, 5, C.mortar)
            xx = xx + 14
        end
        yy = yy + 6
        row = row + 1
    end
    -- side rim light
    M.srect(x, y + 4, 1, h - 4, C.violet)
    M.srect(x + w - 1, y + 4, 1, h - 4, C.pinkDk)
end

-- decorative rooftop props keyed by platform id (never solid)
function M.rooftopProps(x, y, wpx, id, t)
    if wpx < 30 then return end
    local r = M.hash(id * 977 + 13)
    local inner = wpx - 26
    if inner < 10 then inner = 10 end
    if r > 0.72 and wpx > 60 then
        -- antenna mast with blinking red beacon
        local ax = x + math.floor(10 + M.hash(id * 31) * inner)
        M.srect(ax, y - 14, 1, 14, C.mortar)
        M.srect(ax - 2, y - 10, 5, 1, C.mortar)
        M.srect(ax - 1, y - 14, 3, 1, C.mortar)
        if math.floor((t or 0) * 2 + M.hash(id * 3)) % 2 == 0 then
            M.srect(ax, y - 16, 1, 2, C.pink)
        end
    elseif r > 0.45 then
        -- AC unit
        local bx = x + math.floor(10 + M.hash(id * 17) * inner)
        M.srect(bx, y - 7, 12, 7, C.mid)
        M.srect(bx, y - 7, 12, 1, C.edgeGlow)
        M.srect(bx + 2, y - 5, 8, 3, C.brick)
        M.srect(bx + 3, y - 4, 1, 1, C.cyan)
        M.srect(bx + 6, y - 4, 1, 1, C.cyan)
    elseif r > 0.30 then
        -- vent pipe
        local bx = x + math.floor(10 + M.hash(id * 23) * inner)
        M.srect(bx, y - 5, 4, 5, C.mortar)
        M.srect(bx - 1, y - 6, 6, 1, C.violet)
    end
    -- flickering neon sign on wide roofs
    if M.hash(id * 613 + 7) > 0.78 and wpx > 70 then
        local sx = x + math.floor(wpx * 0.55)
        M.srect(sx, y - 12, 18, 8, C.bar)
        M.srect(sx, y - 12, 18, 1, C.pinkDk)
        M.srect(sx, y - 5, 18, 1, C.pinkDk)
        local on = math.floor((t or 0) * 3 + id) % 5 ~= 0
        M.srect(sx + 3, y - 10, 2, 5, on and C.cyanHi or C.violet)
        M.srect(sx + 8, y - 10, 2, 5, on and C.pink or C.pinkDk)
        M.srect(sx + 13, y - 10, 2, 5, on and C.cyanHi or C.violet)
    end
end

function M.topBar(title, tag)
    E.rect(0, 0, 240, 12, C.bar)
    E.rect(0, 12, 240, 1, C.violet)
    M.ptext(4, 5, title, C.cyan, 1)
    -- ASCII tag: screen id for lua_preview tooling + device status line
    E.set_font(8)
    E.text(240 - E.text_width(tag or "NR") - 4, 3, tag or "NR", C.dim)
end

return M
