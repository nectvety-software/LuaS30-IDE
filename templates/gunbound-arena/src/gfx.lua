-- Gunbound Arena: palette sa mạc, pixel font, nền trời, đồi cát, tăng phao binh.
local E = engine
local SH = require("src.screen").H
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
-- day sky
C.skyTop   = M.col(74, 142, 208)
C.skyMid   = M.col(126, 182, 224)
C.skyLow   = M.col(196, 224, 232)
C.skyHaze  = M.col(232, 232, 206)
C.sun      = M.col(255, 248, 214)
C.sunGlow  = M.col(255, 238, 180)
C.cloud    = M.col(248, 250, 252)
C.cloudSh  = M.col(214, 226, 236)
-- dunes / terrain
C.duneFar  = M.col(214, 188, 148)
C.duneMid  = M.col(198, 166, 120)
C.grass    = M.col(108, 176, 72)
C.grassHi  = M.col(152, 208, 96)
C.dirt1    = M.col(150, 108, 64)
C.dirt2    = M.col(118, 82, 48)
C.dirt3    = M.col(86, 60, 36)
C.rock     = M.col(64, 46, 30)
-- HUD
C.bar      = M.col(18, 22, 38)
C.barEdge  = M.col(64, 76, 120)
C.white    = M.col(240, 244, 250)
C.dim      = M.col(140, 148, 170)
C.cyan     = M.col(70, 210, 230)
C.yellow   = M.col(250, 216, 90)
C.orange   = M.col(246, 150, 60)
C.red      = M.col(232, 76, 60)
C.green    = M.col(96, 210, 96)
C.black    = M.col(10, 8, 12)
-- tanks
C.blue1    = M.col(58, 92, 186)
C.blue2    = M.col(30, 46, 112)
C.blue3    = M.col(120, 160, 236)
C.red1     = M.col(204, 66, 52)
C.red2     = M.col(118, 30, 24)
C.red3     = M.col(244, 132, 92)
C.tread    = M.col(40, 38, 44)
C.metal    = M.col(90, 92, 100)
-- fx
C.shell    = M.col(46, 44, 50)
C.shellHi  = M.col(150, 148, 156)
C.flash    = M.col(255, 250, 224)
C.fire     = M.col(255, 172, 62)
C.fire2    = M.col(240, 92, 40)
C.smoke    = M.col(120, 114, 110)
C.smoke2   = M.col(78, 74, 72)
M.C = C

-- deterministic pseudo random (Lua 5.1: no bit ops)
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
    if y2 > SH then y2 = SH end
    if x2 > x and y2 > y then E.rect(x, y, x2 - x, y2 - y, c) end
end

-- ---------------------------------------------------------------- pixel font
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

-- Glyph rows are parsed ONCE into run lists {dx, row, runLen}; drawing a
-- text string then replays cached rects instead of re-scanning bitmaps.
local glyph_runs = {}
local function runs_of(bits)
    local r = glyph_runs[bits]
    if r then return r end
    r = {}
    local row = 0
    for bits2 in bits:gmatch("[01]+") do
        local cx = 1
        while cx <= 5 do
            if bits2:sub(cx, cx) == "1" then
                local run = 1
                while cx + run <= 5 and bits2:sub(cx + run, cx + run) == "1" do
                    run = run + 1
                end
                r[#r + 1] = { (cx - 1), row, run }
                cx = cx + run
            else
                cx = cx + 1
            end
        end
        row = row + 1
    end
    glyph_runs[bits] = r
    return r
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

-- y = top of the 7-row base; marks may extend 4px above and 1px below.
-- A string is parsed ONCE into a flat {dx,row,run} triple list and cached
-- (bounded: static labels); anything past the cap is rebuilt into a shared
-- scratch buffer each call -- zero per-frame allocation either way.
local LAYOUT_MAX = 120
local layout, layoutN, scratch = {}, 0, { n = 0, w = 0 }
local function fill_layout(s, L)
    local n, col, i = 0, 0, 1
    while i <= #s do
        local len = cluster_len(s:byte(i))
        local ch = s:sub(i, i + len - 1)
        i = i + len
        local spec = VN[ch]
        local base = spec and spec[1] or ch
        local g = GLYPH[base] or GLYPH["?"]
        local gx = col * 6
        local gr = runs_of(g)
        for k = 1, #gr do
            local e = gr[k]
            n = n + 1; L[n] = gx + e[1]; L[n + 1] = e[2]; L[n + 2] = e[3]; n = n + 2
        end
        if spec then
            for m = 2, #spec do
                local mk = spec[m]
                if mk == "DOTB" then
                    n = n + 1; L[n] = gx + 2; L[n + 1] = 8; L[n + 2] = 1; n = n + 2
                elseif mk == "STROKE" then
                    n = n + 1; L[n] = gx + 3; L[n + 1] = 3; L[n + 2] = 4; n = n + 2
                else
                    local bits = MARK1[mk]
                    local dy = -2
                    if not bits then bits = MARK2[mk]; dy = -4 end
                    if bits then
                        local mr = runs_of(bits)
                        for k = 1, #mr do
                            local e = mr[k]
                            n = n + 1; L[n] = gx + e[1]; L[n + 1] = e[2] + dy; L[n + 2] = e[3]; n = n + 2
                        end
                    end
                end
            end
        end
        col = col + 1
    end
    L.n = n
    L.wc = col * 6
    return L
end

local function layout_for(s, scale)
    local byScale = layout[s]
    if not byScale then byScale = {}; layout[s] = byScale end
    local L = byScale[scale]
    if L then return L end
    if layoutN < LAYOUT_MAX then
        L = fill_layout(s, {})
        L.w = L.wc * scale
        byScale[scale] = L
        layoutN = layoutN + 1
        return L
    end
    fill_layout(s, scratch)
    scratch.w = scratch.wc * scale
    return scratch
end

function M.ptext(x, y, s, color, scale)
    scale = scale or 1
    local L = layout_for(s, scale)
    local n, i = L.n, 1
    while i <= n do
        M.srect(x + L[i] * scale, y + L[i + 1] * scale, L[i + 2] * scale, scale, color)
        i = i + 3
    end
end

function M.ptext_center(cx, y, s, color, scale)
    scale = scale or 1
    local L = layout_for(s, scale)
    M.ptext(math.floor(cx - L.w / 2), y, s, color, scale)
end
-- --------------------------------------------------------------- scenery
-- daytime desert sky with sun, drifting clouds and far dune ridges
local SKY_BANDS = { C.skyTop, C.skyTop, C.skyMid, C.skyMid, C.skyLow, C.skyHaze }
local SKY_BH = math.ceil(150 / #SKY_BANDS)

-- sun is a static sprite: its scanline spans are computed once at load
local sunCore, sunGlow = {}, {}
do
    local cx, cy, rad = 196, 40, 13
    for dy = -rad - 3, rad + 3 do
        local half = math.floor(math.sqrt(math.max(0, (rad + 3) * (rad + 3) - dy * dy)))
        local half2 = math.floor(math.sqrt(math.max(0, rad * rad - dy * dy)))
        if half > 0 then
            if half2 > 0 then
                sunCore[#sunCore + 1] = { cx - half2, cy + dy, half2 * 2 + 1 }
            end
            if half2 > 0 then
                if cx - half <= cx - half2 - 1 then sunGlow[#sunGlow + 1] = { cx - half, cy + dy, half - half2 } end
                if cx + half2 + 1 <= cx + half then sunGlow[#sunGlow + 1] = { cx + half2 + 1, cy + dy, half - half2 } end
            else
                sunGlow[#sunGlow + 1] = { cx - half, cy + dy, half * 2 + 1 }
            end
        end
    end
end

function M.sky(t, wind)
    for i = 1, #SKY_BANDS do
        M.srect(0, (i - 1) * SKY_BH, 240, SKY_BH, SKY_BANDS[i])
    end
    for i = 1, #sunGlow do
        local g = sunGlow[i]
        M.srect(g[1], g[2], g[3], 1, C.sunGlow)
    end
    for i = 1, #sunCore do
        local g = sunCore[i]
        M.srect(g[1], g[2], g[3], 1, C.sun)
    end
    -- clouds drift with the wind
    wind = wind or 1
    for i = 1, 5 do
        local w = 30 + M.hash(i * 41 + 7) * 34
        local x = (M.hash(i * 91 + 3) * 320 + (t or 0) * wind * 3) % 340 - 50
        local y = 22 + M.hash(i * 23 + 11) * 66
        M.srect(math.floor(x), math.floor(y), math.floor(w), 4, C.cloud)
        M.srect(math.floor(x + 7), math.floor(y - 3), math.floor(w * 0.55), 3, C.cloud)
        M.srect(math.floor(x + 3), math.floor(y + 4), math.floor(w * 0.7), 2, C.cloudSh)
    end
end

-- animated wind streaks in the sky; wind is the signed px/s value
function M.windStreaks(t, wind)
    if not wind or wind == 0 then return end
    local spd = wind * 2.2
    for i = 1, 7 do
        local y = 18 + M.hash(i * 61 + 5) * 88
        local w = 8 + math.floor(M.hash(i * 37 + 9) * 10)
        local x = (M.hash(i * 97 + 13) * 300 + (t or 0) * spd) % 300 - 30
        if wind < 0 then x = 240 - w - x end
        M.srect(math.floor(x), math.floor(y), w, 1, C.cloudSh)
        M.srect(math.floor(x + 2), math.floor(y + 2), math.floor(w * 0.6), 1, C.cloud)
    end
end

-- decorative far dunes behind the destructible terrain.
-- The ridge line only depends on SH, so precompute it once and merge
-- neighbouring columns of equal height into wide rects (cached per
-- terrain version by newDunes). Dunes extend to the bottom edge; the
-- terrain drawn afterwards always covers what must stay hidden.
local duneY = {}
do
    for x = 1, 240 do
        duneY[x] = SH - 202 + math.floor(math.sin(x * 0.021) * 14 + math.sin(x * 0.061 + 2) * 7)
    end
end

function M.newDunes()
    local cver, runs, runN = nil, {}, 0
    return function(terr, ver)
        if cver ~= ver then
            cver = ver
            runN = 0
            local x = 1
            while x <= 240 do
                local y = duneY[x]
                if terr[x] > y + 4 then
                    local x2 = x
                    while x2 < 240 and duneY[x2 + 1] == y and terr[x2 + 1] > y + 4 do
                        x2 = x2 + 1
                    end
                    runN = runN + 1
                    local r = runs[runN]
                    if not r then r = {}; runs[runN] = r end
                    r[1] = x - 1; r[2] = y; r[3] = x2 - x + 1
                    x = x2 + 1
                else
                    x = x + 1
                end
            end
        end
        for i = 1, runN do
            local r = runs[i]
            M.srect(r[1], r[2], r[3], SH - r[2], C.duneFar)
            if (r[1] + r[2]) % 7 == 0 then M.srect(r[1], r[2], 1, 2, C.duneMid) end
        end
    end
end

-- solid terrain body: RLE-merge columns of equal height into wide rects;
-- runs are rebuilt only when the terrain version changes (explosions).
function M.newTerrain()
    local cver, runs, runN = nil, {}, 0
    return function(terr, ver, bottomY)
        if cver ~= ver then
            cver = ver
            runN = 0
            local x = 1
            while x <= 240 do
                local y = terr[x]
                local x2 = x
                while x2 < 240 and terr[x2 + 1] == y do x2 = x2 + 1 end
                runN = runN + 1
                local r = runs[runN]
                if not r then r = {}; runs[runN] = r end
                r[1] = x - 1; r[2] = y; r[3] = x2 - x + 1
                x = x2 + 1
            end
        end
        for i = 1, runN do
            local r = runs[i]
            local x, y, w = r[1], r[2], r[3]
            M.srect(x, y, w, 2, C.grass)
            M.srect(x, y + 2, w, 8, C.dirt1)
            local h = bottomY - y - 10
            if h > 0 then M.srect(x, y + 10, w, h, C.dirt2) end
        end
    end
end

-- cactus prop at a fixed column, purely decorative
function M.cactus(x, gy)
    if gy > SH - 28 then return end
    M.srect(x, gy - 12, 2, 12, C.grass)
    M.srect(x - 3, gy - 9, 3, 2, C.grass)
    M.srect(x - 3, gy - 11, 2, 3, C.grass)
    M.srect(x + 2, gy - 7, 3, 2, C.grass)
    M.srect(x + 3, gy - 10, 2, 4, C.grass)
end

-- ------------------------------------------------------------------- tanks
-- tank body 17x11 at x,y (top-left, sits on ground); dir=+1 faces right
-- barrel drawn separately so it can rotate: Gfx.barrel(cx, cy, dir, angDeg)
function M.tank(dir, c1, c2, c3, x, y)
    -- treads
    M.srect(x, y + 8, 17, 3, C.tread)
    for i = 0, 3 do M.srect(x + 2 + i * 4, y + 9, 1, 1, C.metal) end
    -- hull
    local hx = dir > 0 and x or x
    M.srect(hx + 1, y + 4, 15, 5, c1)
    M.srect(hx + 1, y + 4, 15, 1, c3)
    -- turret dome
    local tx = dir > 0 and hx + 3 or hx + 4
    M.srect(tx, y + 1, 9, 4, c2)
    M.srect(tx + 1, y, 7, 2, c1)
    M.srect(tx + 2, y, 3, 1, c3)
end

-- barrel aims at an ABSOLUTE angle: 0 = left, 90 = up, 180 = right
function M.barrel(cx, cy, angDeg)
    local rad = angDeg * 3.14159 / 180
    for i = 1, 8 do
        local bx = cx + math.floor(math.cos(rad) * i + 0.5)
        local by = cy - math.floor(math.sin(rad) * i + 0.5)
        M.srect(bx - 1, by - 1, 2, 2, C.metal)
    end
    local mx = cx + math.floor(math.cos(rad) * 8 + 0.5)
    local my = cy - math.floor(math.sin(rad) * 8 + 0.5)
    M.srect(mx - 1, my - 1, 2, 2, C.tread)
end

-- generic horizontal gauge (power / move points)
function M.gauge(x, y, w, h, frac, col)
    M.srect(x - 1, y - 1, w + 2, h + 2, C.black)
    if frac < 0 then frac = 0 elseif frac > 1 then frac = 1 end
    M.srect(x, y, math.floor(w * frac + 0.5), h, col)
end

-- HP bar above a tank
function M.hpBar(x, y, hp, flip)
    M.srect(x - 1, y - 1, 22, 5, C.black)
    local w = math.floor(hp * 20 / 100 + 0.5)
    if w < 0 then w = 0 end
    local col = hp > 55 and C.green or (hp > 25 and C.yellow or C.red)
    if flip then M.srect(x + 20 - w + 1, y, w, 3, col)
    else M.srect(x, y, w, 3, col) end
end

-- wind flag: arrows pointing in blow direction, strength 0..5
local WINDSTR = { [0] = "-" }
for n = 1, 5 do
    WINDSTR[n] = string.rep(">", n)
    WINDSTR[-n] = string.rep("<", n)
end

function M.windGauge(cx, y, wind)
    local n = math.min(5, math.floor(math.abs(wind) / 9 + 0.5))
    local s = WINDSTR[wind ~= 0 and (wind > 0 and n or -n) or 0]
    M.ptext(math.floor(cx - #s * 3), y, s, n == 0 and C.white or C.yellow, 1)
end

function M.topBar(title, tag)
    M.srect(0, 0, 240, 13, C.bar)
    M.srect(0, 13, 240, 1, C.barEdge)
    if title then M.ptext(4, 5, title, C.cyan, 1) end
    -- ASCII tag: screen id for lua_preview tooling + device status line
    E.set_font(8)
    E.text(240 - E.text_width(tag or "GB") - 4, 3, tag or "GB", C.dim)
end

-- ------------------------------------------------------------- item icons
-- kind: 1 = spider web, 2 = ice, 3 = plane. drawn in a 7x7 box at x,y
function M.itemIcon(kind, x, y)
    x, y = math.floor(x), math.floor(y)
    if kind == 1 then
        local g = C.cloud
        M.srect(x + 3, y, 1, 7, g)      -- vertical
        M.srect(x, y + 3, 7, 1, g)      -- horizontal
        M.srect(x, y, 2, 1, g);   M.srect(x + 5, y, 2, 1, g)
        M.srect(x, y + 6, 2, 1, g); M.srect(x + 5, y + 6, 2, 1, g)
        M.srect(x + 1, y + 1, 1, 1, g); M.srect(x + 5, y + 1, 1, 1, g)
        M.srect(x + 1, y + 5, 1, 1, g); M.srect(x + 5, y + 5, 1, 1, g)
        M.srect(x + 3, y + 3, 1, 1, C.white)
    elseif kind == 2 then
        local c = C.cyan
        M.srect(x + 3, y, 1, 7, c)
        M.srect(x + 1, y + 1, 1, 1, c); M.srect(x + 5, y + 1, 1, 1, c)
        M.srect(x + 2, y + 2, 1, 1, c); M.srect(x + 4, y + 2, 1, 1, c)
        M.srect(x, y + 3, 7, 1, C.white)
        M.srect(x + 2, y + 4, 1, 1, c); M.srect(x + 4, y + 4, 1, 1, c)
        M.srect(x + 1, y + 5, 1, 1, c); M.srect(x + 5, y + 5, 1, 1, c)
    else
        local b = C.white
        M.srect(x, y + 3, 7, 1, b)          -- fuselage
        M.srect(x + 2, y + 1, 3, 2, b)      -- wing
        M.srect(x + 5, y + 1, 1, 2, C.red)  -- tail
        M.srect(x + 6, y + 2, 1, 1, C.red)
        M.srect(x + 1, y + 4, 2, 1, C.dim)  -- shadow
    end
end

-- transport plane (16 px wide) flying at x,y; hull dir -1/1
function M.planeSprite(x, y, dir, t)
    x, y = math.floor(x), math.floor(y)
    local b = C.cloud
    M.srect(x - 8, y, 16, 2, b)            -- fuselage
    M.srect(x - 10, y - 1, 6, 1, b)        -- wing
    M.srect(x + 4, y - 3, 4, 3, C.red3)    -- tail fin
    M.srect(x - 8, y + 2, 2, 1, C.dim)     -- landing skids
    M.srect(x + 5, y + 2, 2, 1, C.dim)
    -- spinning rotor blurs above the hull
    local r = math.floor(t * 12) % 2
    if r == 0 then M.srect(x - 6, y - 3, 12, 1, C.dim)
    else M.srect(x - 3, y - 3, 6, 1, C.dim) end
end

return M
