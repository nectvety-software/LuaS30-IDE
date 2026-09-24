-- src/render.lua — render gia 3D (raycasting DDA) cho Pop Art City 3D.
--
-- "3D" o day la PSEUDO-3D kieu Wolfenstein/Doom: khong co GPU, khong co phep
-- chieu da giac. Moi cot man hinh ban mot tia vao luoi, do dai tia quyet dinh
-- chieu cao cot tuong. Do la cach duy nhat de co chieu sau tren MRE 240x320.
--
-- Rang buoc that (doc truoc khi sua):
--   * Chi co rect / frame / line / text — KHONG co pixel, vline, hline.
--     => "cot tuong" la MOT rect 4 px rong, khong phai vong lap tung pixel.
--   * KHONG co alpha => khoi xa (fog) phai TRON TRUOC thanh 4 sac do
--     (popart.shade4) roi CHON theo khoang cach. Khong the pha mau tai cho.
--   * 240 px ngang chia 60 cot x 4 px => "pixel rong" 4x1, dung chat pop-art.
--
-- Thu tu ve (sau truoc): troi -> chan troi xa -> san -> tuong -> sprite -> HUD.
-- Moi lop deu la hinh chu nhat dac, lop sau de lop truoc.

local E = engine
local P = require("src.popart")
local C = require("src.city")

local M = {}

M.COLS = 60
M.COL_W = 4
M.HORIZON = 132
M.WALL_SCALE = 240     -- chieu cao cot tuong o khoang cach 1.0
M.FOV = 0.66           -- tan(fov/2) ~ 66 do
M.MAX_STEPS = 26       -- so o toi da mot tia di qua truoc khi bo cuoc
M.NEAR = 0.06

-- Mau troi xa (silhouette thanh pho phia sau) — mot mau dac, khong tron.
M.C_FAR = E.color(74, 44, 116)
M.C_SUN = E.color(255, 236, 140)
M.C_SUN2 = E.color(255, 200, 92)

-- Khoang cach danh thuc tung muc sac do.
local SHADE_AT = { 2.6, 5.2, 9.5 }

-- Bang khoang cach cot tuong gan nhat, dung de sprite bi tuong che dung cho.
-- Cap phat MOT lan, khong cap phat lai moi khung hinh.
M.zdist = {}
for i = 1, M.COLS do M.zdist[i] = 1e9 end

local function shade_level(dist, side)
    local lvl = 0
    if dist > SHADE_AT[1] then lvl = 1 end
    if dist > SHADE_AT[2] then lvl = 2 end
    if dist > SHADE_AT[3] then lvl = 3 end
    -- Mat huong Y (side == 1) toi hon: cho khoi nha co khoi, khong det.
    if side == 1 and lvl < 3 then lvl = lvl + 1 end
    return lvl
end

-- ---------------------------------------------------------------------------
-- Ban tia DDA. Tra ve kind, gx, gy, side, dist — hoac nil neu khong gap gi.
-- ---------------------------------------------------------------------------
local function cast(px, py, rdx, rdy)
    local gx = math.floor(px)
    local gy = math.floor(py)
    local ddx = (rdx == 0) and 1e30 or math.abs(1 / rdx)
    local ddy = (rdy == 0) and 1e30 or math.abs(1 / rdy)
    local sx, sy, sdx, sdy
    if rdx < 0 then
        sx = -1
        sdx = (px - gx) * ddx
    else
        sx = 1
        sdx = (gx + 1 - px) * ddx
    end
    if rdy < 0 then
        sy = -1
        sdy = (py - gy) * ddy
    else
        sy = 1
        sdy = (gy + 1 - py) * ddy
    end

    local side = 0
    for _ = 1, M.MAX_STEPS do
        if sdx < sdy then
            sdx = sdx + ddx
            gx = gx + sx
            side = 0
        else
            sdy = sdy + ddy
            gy = gy + sy
            side = 1
        end
        if C.solid(gx, gy) then
            local dist
            if side == 0 then
                dist = sdx - ddx
            else
                dist = sdy - ddy
            end
            if dist < M.NEAR then dist = M.NEAR end
            local k = C.kind(gx, gy)
            if k == 0 then k = 6 end   -- ngoai ban do: coi nhu nha "paper"
            return k, gx, gy, side, dist
        end
    end
    return nil
end

-- ---------------------------------------------------------------------------
-- Troi: 6 dai ngang, cang gan duong chan troi cang sang.
-- ---------------------------------------------------------------------------
local function draw_sky()
    local n = #P.C.sky
    local step = math.ceil(M.HORIZON / n)
    for i = 1, n do
        local y = (i - 1) * step
        local h = math.min(step, M.HORIZON - y)
        if h > 0 then
            E.rect(0, y, P.W, h, P.C.sky[i])
        end
    end
end

-- Mat troi pop-art: hinh tron ghep tu cac dai ngang (khong co ham ve tron).
local function draw_sun()
    local cx, cy, r = 178, 54, 22
    local rows = 8
    local rh = math.floor(r * 2 / rows)
    for i = 0, rows - 1 do
        local y0 = cy - r + i * rh
        local dy = (y0 + rh / 2) - cy
        local half = math.sqrt(math.max(0, r * r - dy * dy))
        if half > 1 then
            local col = M.C_SUN
            if i >= rows - 2 then col = M.C_SUN2 end
            E.rect(math.floor(cx - half), y0, math.floor(half * 2), rh, col)
        end
    end
end

-- Silhouette thanh pho xa: vai khoi chu nhat ngay tren duong chan troi.
-- Vua tao chieu sau, vua che cac "lo hong" chan troi khi nha gan thap hon nha xa.
local function draw_far_skyline()
    local x = -6
    local i = 0
    while x < P.W do
        local w = 14 + (i % 3) * 6
        local h = 12 + ((i * 37) % 5) * 8
        E.rect(x, M.HORIZON - h, w, h, M.C_FAR)
        x = x + w
        i = i + 1
    end
end

-- San: 6 dai, chia theo binh phuong nen dai rat mong sat chan troi (xa) va
-- day dan o duoi (gan). Do la phep chieu dung cua mat phang nen.
local function draw_floor()
    local n = #P.C.floor
    local span = P.H - M.HORIZON
    for i = 1, n do
        local t0 = ((i - 1) / n) ^ 2
        local t1 = (i / n) ^ 2
        local y0 = M.HORIZON + math.floor(t0 * span)
        local y1 = M.HORIZON + math.floor(t1 * span)
        local h = y1 - y0
        if h > 0 then
            E.rect(0, y0, P.W, h, P.C.floor[i])
        end
    end
end

-- ---------------------------------------------------------------------------
-- Tuong
-- ---------------------------------------------------------------------------
local function draw_walls(px, py, dirx, diry, planex, planey)
    local w = M.COL_W
    for col = 0, M.COLS - 1 do
        local camera = 2 * (col + 0.5) / M.COLS - 1
        local rdx = dirx + planex * camera
        local rdy = diry + planey * camera
        local k, gx, gy, side, dist = cast(px, py, rdx, rdy)
        M.zdist[col + 1] = dist or 1e9

        if k then
            local b = P.BUILD[k]
            local hs = b.hs * C.height_mul(gx, gy)
            local lvl = shade_level(dist, side)
            local line_h = (M.WALL_SCALE * hs) / dist
            local top = M.HORIZON - math.floor(line_h / 2)
            local bot = top + math.floor(line_h)
            if top < 0 then top = 0 end
            if bot > P.H then bot = P.H end
            local x = col * w
            local ww = math.min(w, P.W - x)
            if ww > 0 and bot - top > 0 then
                E.rect(x, top, ww, bot - top, b.shades[lvl + 1])
                -- Vien den tren dinh tuong: chu ky pop-art (vien day).
                E.rect(x, top, ww, 2, P.C.ink)
            end
        end
    end
end

-- ---------------------------------------------------------------------------
-- Sprite billboard. Moi sprite la danh sach hinh chu nhat CHUAN HOA
-- (u0, v0, u1, v1, mau) trong khung 0..1 x 0..1 cua no.
-- ---------------------------------------------------------------------------
local function sub(u0, v0, u1, v1, col)
    return { u0, v0, u1, v1, col }
end

local SHAPE = {}

-- Kich thuoc that cua tung loai vat the, tinh bang don vi the gioi
-- (1.0 = dung bang chieu cao mot o nha). `lift` = nang len khoi mat dat.
local META = {
    car    = { scale = 0.52, aspect = 1.50, lift = 0.00 },
    ped    = { scale = 0.62, aspect = 0.62, lift = 0.00 },
    booth  = { scale = 0.85, aspect = 0.85, lift = 0.00 },
    -- Cot moc: KHONG nang len. Nang len thi khi lai sat, phan vang bi day ra
    -- ngoai man hinh, chi con lai cai cot den — mat luon dau hieu nhiem vu.
    marker = { scale = 1.10, aspect = 0.55, lift = 0.00 },
}

SHAPE.car = function(b, ink)
    return {
        sub(0.00, 0.38, 1.00, 1.00, ink),
        sub(0.04, 0.44, 0.96, 0.96, b.shades[1]),
        sub(0.20, 0.06, 0.80, 0.44, ink),
        sub(0.24, 0.10, 0.76, 0.40, b.shades[2]),
        sub(0.10, 0.90, 0.30, 1.00, ink),
        sub(0.70, 0.90, 0.90, 1.00, ink),
    }
end

SHAPE.ped = function(b, ink)
    return {
        sub(0.36, 0.00, 0.64, 0.26, P.C.paper),
        sub(0.18, 0.26, 0.82, 0.70, ink),
        sub(0.24, 0.30, 0.76, 0.66, b.shades[1]),
        sub(0.26, 0.70, 0.46, 1.00, ink),
        sub(0.54, 0.70, 0.74, 1.00, ink),
    }
end

SHAPE.booth = function(b, ink)
    return {
        sub(0.14, 0.10, 0.86, 1.00, ink),
        sub(0.18, 0.14, 0.82, 1.00, b.shades[1]),
        sub(0.06, 0.00, 0.94, 0.12, ink),
        sub(0.30, 0.26, 0.70, 0.62, P.C.paper),
    }
end

-- Cot moc nhiem vu: cot vang dung tren mat dat, hai mui chevron trang o tren.
-- Doc duoc tu xa (cot vang noi bat tren nen tim) va khong bi che khi lai sat.
SHAPE.marker = function(b, ink)
    return {
        sub(0.28, 0.00, 0.72, 1.00, ink),
        sub(0.34, 0.00, 0.66, 1.00, P.C.sun),
        sub(0.16, 0.02, 0.84, 0.14, ink),
        sub(0.22, 0.05, 0.78, 0.11, P.C.paper),
        sub(0.16, 0.20, 0.84, 0.32, ink),
        sub(0.22, 0.23, 0.78, 0.29, P.C.paper),
    }
end

-- Ve MOT sprite. `sx` = tam ngang man hinh, `sy` = duong chan de len mat dat,
-- `sw`/`sh` = kich thuoc man hinh. Tra ve true neu da ve.
local function draw_one(shape, sx, sy, sw, sh, vis0, vis1)
    if sw < 2 or sh < 2 then return false end
    local x0 = math.floor(sx - sw / 2)
    local y0 = math.floor(sy - sh)
    local drew = false
    for i = 1, #shape do
        local r = shape[i]
        local rx = x0 + r[1] * sw
        local rw = (r[3] - r[1]) * sw
        local ry = y0 + r[2] * sh
        local rh = (r[4] - r[2]) * sh
        -- Cat theo khoang cot KHONG bi tuong che (xem ghi chu o draw_sprites).
        if rx < vis0 then
            rw = rw - (vis0 - rx)
            rx = vis0
        end
        if rx + rw > vis1 then rw = vis1 - rx end
        -- Tu cat vao man hinh. runtime_bridge.clip_ok() CHI kiem tra hinh chu
        -- nhat co GIAO voi man hinh khong, no KHONG kep toa do — nen rect
        -- tran man hinh se duoc chuyen nguyen cho firmware tu cat. Tu cat o
        -- day vua an toan vua do ton vo ich.
        local x0f = math.floor(rx)
        local x1f = math.floor(rx + rw)
        local y0f = math.floor(ry)
        local y1f = math.floor(ry + rh)
        if x0f < 0 then x0f = 0 end
        if y0f < 0 then y0f = 0 end
        if x1f > P.W then x1f = P.W end
        if y1f > P.H then y1f = P.H end
        if x1f > x0f and y1f > y0f then
            E.rect(x0f, y0f, x1f - x0f, y1f - y0f, r[5])
            drew = true
        end
    end
    return drew
end

-- Sap xep sprite xa -> gan de sprite gan ve de len sprite xa.
-- Sap xep CHON (selection sort) tren mang tai dung: so sprite nho (<16).
local order = {}
local odist = {}

local function sort_sprites(list, px, py)
    local n = #list
    for i = 1, n do
        order[i] = i
        local dx, dy = list[i].x - px, list[i].y - py
        odist[i] = dx * dx + dy * dy
    end
    for i = 1, n - 1 do
        local best = i
        for j = i + 1, n do
            if odist[order[j]] > odist[order[best]] then best = j end
        end
        order[i], order[best] = order[best], order[i]
    end
end

local function draw_sprites(px, py, dirx, diry, planex, planey, extra)
    -- Gop vat the tinh + moc nhiem vu vao mot danh sach tam thoi.
    local list = M._tmp
    local n = 0
    for i = 1, #C.SPRITES do
        local s = C.SPRITES[i]
        n = n + 1
        list[n] = s
    end
    if extra then
        n = n + 1
        list[n] = extra
    end
    for i = n + 1, #list do list[i] = nil end

    sort_sprites(list, px, py)

    local det = planex * diry - dirx * planey
    if det == 0 then return end
    local inv = 1 / det
    local half = P.W / 2

    for oi = 1, n do
        local s = list[order[oi]]
        local dx, dy = s.x - px, s.y - py
        local ty = inv * (-planey * dx + planex * dy)   -- do sau
        if ty > 0.25 then
            local tx = inv * (diry * dx - dirx * dy)
            local sx = half * (1 + tx / ty)
            local kind = s.kind or "car"
            local meta = META[kind] or META.car
            local scale = s.scale or meta.scale
            local sh = (M.WALL_SCALE * scale) / ty
            local sw = sh * (s.aspect or meta.aspect)

            -- Che khuat: thu hep khoang ngang cua sprite lai chi con cac cot
            -- ma tuong gan hon sprite. Re hon z-buffer tung cot, va dung voi
            -- vat can loi (goc nha). Chuan xac 100% thi phai ve tung dai cot.
            -- zdist[i] ung voi cot i-1 => x trong [(i-1)*COL_W, i*COL_W).
            local c0 = math.floor((sx - sw / 2) / M.COL_W) + 1
            local c1 = math.floor((sx + sw / 2) / M.COL_W)
            if c0 < 1 then c0 = 1 end
            if c1 > M.COLS then c1 = M.COLS end
            while c0 <= c1 and M.zdist[c0] <= ty do c0 = c0 + 1 end
            while c1 >= c0 and M.zdist[c1] <= ty do c1 = c1 - 1 end
            if c0 <= c1 then
                local shape = SHAPE[kind]
                if shape then
                    local b = P.BUILD[s.tint or 1]
                    -- Chan mat dat o khoang cach ty = day cua cot tuong cao
                    -- dung 1 don vi o cung khoang cach do.
                    local ground = M.HORIZON + (M.WALL_SCALE / ty) * 0.5
                    draw_one(shape(b, P.C.ink), sx,
                             ground - (meta.lift or 0) * sh, sw, sh,
                             (c0 - 1) * M.COL_W, c1 * M.COL_W)
                end
            end
        end
    end
end

-- ---------------------------------------------------------------------------
M._tmp = {}

-- Ve toan bo khung nhin 3D. `angle` tinh bang radian.
-- `extra` = sprite dong (moc nhiem vu), hoac nil.
function M.frame(px, py, angle, extra)
    local dirx = math.cos(angle)
    local diry = math.sin(angle)
    local planex = -diry * M.FOV
    local planey = dirx * M.FOV

    draw_sky()
    draw_sun()
    draw_far_skyline()
    draw_floor()
    draw_walls(px, py, dirx, diry, planex, planey)
    draw_sprites(px, py, dirx, diry, planex, planey, extra)
end

-- Nen cho man hinh tinh (tieu de / huong dan): troi + mat troi + chan troi xa
-- + san, KHONG co tuong. Dung lai dung cac ham cua khung nhin 3D nen man hinh
-- tinh va man hinh choi luon cung mot "the gioi mau".
function M.backdrop()
    draw_sky()
    draw_sun()
    draw_far_skyline()
    draw_floor()
end

-- Duong chan troi co dinh — HUD can biet de dat chip.
M.HORIZON_Y = M.HORIZON

return M
