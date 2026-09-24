-- src/hud.lua — HUD kieu GTA nhung tiet kiem rect.
--
-- Chien luoc chi phi: trong luc choi, chu dung engine.text (1 lan goi cho ca
-- chuoi) vi ngan sach rect da bi render 3D an gan het (~170 rect/khung hinh).
-- Font khoi 3x5 cua popart chi dung o MAN HINH TINH (tieu de, menu, banner
-- nhiem vu) — noi khong co 3D phia sau nen ngan sach con nguyen.
--
-- Radar la kieu BAC-UP (khong quay): rect khong xoay duoc, nen huong cua
-- nguoi choi the hien bang MOT vet nho lech theo goc, khong phai mui ten xoay.

local E = engine
local P = require("src.popart")
local C = require("src.city")

local M = {}

M.C = {}

M.C.radar_bg = E.color(16, 10, 30)
M.C.radar_bd = E.color(255, 45, 120)
M.C.road     = E.color(70, 62, 96)
M.C.block    = E.color(40, 28, 66)
M.C.blip     = E.color(0, 194, 209)
M.C.here     = E.color(255, 45, 120)
M.C.gold     = E.color(255, 210, 63)
M.C.hp_hi    = E.color(168, 225, 12)
M.C.hp_mid   = E.color(255, 210, 63)
M.C.hp_lo    = E.color(255, 45, 120)
M.C.chip     = E.color(20, 12, 34)

local DISTRICTS = {
    "DOWNTOWN", "DOCKS", "UPTOWN", "OLD TOWN",
    "HARBOR", "MIDTOWN", "SOUTH SIDE", "AIRPORT",
}

function M.district(x, y)
    local bx = math.floor(x / C.PERIOD)
    local by = math.floor(y / C.PERIOD)
    local i = (bx * 3 + by * 5) % #DISTRICTS
    return DISTRICTS[i + 1]
end

local COMPASS = { "E", "SE", "S", "SW", "W", "NW", "N", "NE" }

-- Goc 0 = +X = Dong. Chia 8 huong, lam tron ve huong gan nhat.
function M.compass(angle)
    local turns = angle / (2 * math.pi)
    local idx = math.floor(turns * 8 + 0.5) % 8
    return COMPASS[idx + 1]
end

-- ---------------------------------------------------------------------------
-- Chip (khung chu nho) — kieu o truyen: vien day + ruot toi.
-- ---------------------------------------------------------------------------
function M.chip(x, y, w, h, fill, border)
    P.panel(x, y, w, h, fill or M.C.chip, border or M.C.radar_bd, 2)
end

-- Chip chu can le trai / phai.
function M.text_chip(x, y, text, colour, align)
    local tw = E.text_width(text)
    local w = tw + 12
    local h = 18
    if align == "right" then x = x - w end
    if align == "center" then x = x - math.floor(w / 2) end
    M.chip(x, y, w, h)
    E.text(x + 6, y + 5, text, colour)
    return w
end

-- ---------------------------------------------------------------------------
-- Thanh chi so (mau tu chuyen theo ti le)
-- ---------------------------------------------------------------------------
function M.bar(x, y, w, h, ratio, colour)
    if ratio < 0 then ratio = 0 end
    if ratio > 1 then ratio = 1 end
    E.rect(x - 2, y - 2, w + 4, h + 4, P.C.ink)
    E.rect(x, y, w, h, P.C.bar_bg)
    local fill = math.floor(w * ratio)
    if fill > 0 then
        E.rect(x, y, fill, h, colour)
    end
end

function M.health_colour(ratio)
    if ratio > 0.5 then return M.C.hp_hi end
    if ratio > 0.25 then return M.C.hp_mid end
    return M.C.hp_lo
end

-- ---------------------------------------------------------------------------
-- Muc do truy na: 5 o vuong, o day = mau nong, o rong = vien.
-- ---------------------------------------------------------------------------
function M.wanted(x, y, level)
    for i = 1, 5 do
        local px = x + (i - 1) * 9
        if i <= level then
            E.rect(px, y, 7, 7, M.C.gold)
            E.rect(px, y, 7, 2, P.C.paper)
        else
            E.frame(px, y, 7, 7, M.C.radar_bd)
        end
    end
end

-- ---------------------------------------------------------------------------
-- Radar (bac-up). Chi ve duong bang vai rect nho nho gop cac o lien tiep.
-- ---------------------------------------------------------------------------
local function clamp(v, lo, hi)
    if v < lo then return lo end
    if v > hi then return hi end
    return v
end

function M.radar(x, y, cell, span, px, py, angle, mission)
    local inner = cell * span
    local half = math.floor(span / 2)
    local gx0 = math.floor(px) - half
    local gy0 = math.floor(py) - half

    E.rect(x - 2, y - 2, inner + 4, inner + 4, P.C.ink)
    E.rect(x, y, inner, inner, M.C.radar_bg)

    -- Vung nam TRONG ban do (ngoai le la "void" — mau nen radar).
    local ix0 = clamp(0 - gx0, 0, span)
    local ix1 = clamp(C.GRID - gx0, 0, span)
    local iy0 = clamp(0 - gy0, 0, span)
    local iy1 = clamp(C.GRID - gy0, 0, span)
    if ix1 > ix0 and iy1 > iy0 then
        E.rect(x + ix0 * cell, y + iy0 * cell,
               (ix1 - ix0) * cell, (iy1 - iy0) * cell, M.C.block)

        -- Cot duong: gop cac cot lien tiep thanh mot rect.
        local i = ix0
        while i < ix1 do
            local gx = gx0 + i
            if (gx % C.PERIOD) < C.ROAD_W then
                local j = i
                while j < ix1 and ((gx0 + j) % C.PERIOD) < C.ROAD_W do
                    j = j + 1
                end
                E.rect(x + i * cell, y + iy0 * cell,
                       (j - i) * cell, (iy1 - iy0) * cell, M.C.road)
                i = j
            else
                i = i + 1
            end
        end
        -- Hang duong
        local k = iy0
        while k < iy1 do
            local gy = gy0 + k
            if (gy % C.PERIOD) < C.ROAD_W then
                local j = k
                while j < iy1 and ((gy0 + j) % C.PERIOD) < C.ROAD_W do
                    j = j + 1
                end
                E.rect(x + ix0 * cell, y + k * cell,
                       (ix1 - ix0) * cell, (j - k) * cell, M.C.road)
                k = j
            else
                k = k + 1
            end
        end
    end

    local function blip(wx, wy, colour, size)
        local bx = x + (wx - gx0) * cell
        local by = y + (wy - gy0) * cell
        if bx >= x - 2 and bx <= x + inner + 2 and by >= y - 2 and by <= y + inner + 2 then
            E.rect(math.floor(bx), math.floor(by), size, size, colour)
        end
    end

    -- Vat the gan day
    local shown = 0
    for i = 1, #C.SPRITES do
        local s = C.SPRITES[i]
        local dx, dy = s.x - px, s.y - py
        if dx * dx + dy * dy < C.RADAR_RANGE * C.RADAR_RANGE and shown < 6 then
            blip(s.x, s.y, M.C.blip, 3)
            shown = shown + 1
        end
    end

    if mission then
        local dx, dy = mission.x - px, mission.y - py
        if dx * dx + dy * dy < C.RADAR_RANGE * C.RADAR_RANGE * 2.25 then
            blip(mission.x, mission.y, M.C.gold, 4)
        end
    end

    -- Nguoi choi: mot o + mot vet lech theo huong (rect khong xoay duoc).
    local cx = x + (px - gx0) * cell
    local cy = y + (py - gy0) * cell
    E.rect(math.floor(cx) - 1, math.floor(cy) - 1, 3, 3, M.C.here)
    E.rect(math.floor(cx + math.cos(angle) * 5) - 1,
           math.floor(cy + math.sin(angle) * 5) - 1, 2, 2, P.C.paper)
end

-- ---------------------------------------------------------------------------
-- Ban HUD day du trong luc choi.
-- `st` = { px, py, angle, hp, money, wanted, speed, in_car, toast }
-- ---------------------------------------------------------------------------
function M.draw(st)
    local W = P.W
    local H = P.H

    -- Dai la ban: ten khu + huong
    local name = M.district(st.px, st.py) .. "  " .. M.compass(st.angle)
    M.text_chip(6, 6, name, P.C.paper, "left")

    -- Nhiem vu
    if st.toast and st.toast ~= "" then
        M.text_chip(math.floor(W / 2), H - 92, st.toast, M.C.gold, "center")
    end

    -- Radar goc duoi trai
    M.radar(10, H - 74, 6, 9, st.px, st.py, st.angle, st.mission)

    -- Chi so goc duoi phai
    local rx = W - 10
    local bar_x = rx - 72
    M.wanted(rx - 5 * 9 + 2, H - 76, st.wanted)
    M.bar(bar_x, H - 60, 72, 8, st.hp / 100, M.health_colour(st.hp / 100))
    if st.in_car then
        M.bar(bar_x, H - 42, 72, 6, st.speed, M.C.blip)
    end

    local cash = "$" .. st.money
    E.text(rx - E.text_width(cash), H - 26, cash, M.C.gold)
    -- Nhan dat BEN TRAI thanh. Truoc day dat `rx - text_width(...)` tuc la NGAY
    -- TREN thanh: chu "HP" mau xam nam giua dai xanh cua thanh HP. Chi nhin thay
    -- tren may that (harness khong ve chu), xem tools/validate_popart_city_e2e.py.
    E.text(bar_x - 6 - E.text_width("HP"), H - 60, "HP", P.C.dim)
    if st.in_car then
        E.text(bar_x - 6 - E.text_width("SPD"), H - 42, "SPD", P.C.dim)
    end
end

return M
