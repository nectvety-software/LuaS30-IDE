-- src/city.lua — thanh pho dang luoi cho Pop Art City 3D.
--
-- Ban do sinh bang HAM BAM TAT DINH, khong dung math.random: runtime LuaS30
-- chi mo base/table/string/math (engine/src/runtime_lua.c), KHONG co os nen
-- khong the math.randomseed(os.time()). Ban do vi vay giong nhau moi lan chay —
-- dung y do: nguoi hoc mo project phai thay dung thanh pho nhu tai lieu.
--
-- LUOI: o 1.0 x 1.0 (don vi the gioi). Duong chiem 2 o dau moi chu ky 5 o
-- (gx % 5 < 2 hoac gy % 5 < 2), con lai la 3x3 o nha. Duong rong 2 o de xe
-- con quay dau duoc.

local M = {}

M.GRID = 32          -- 32 x 32 o
M.PERIOD = 5         -- chu ky duong
M.ROAD_W = 2         -- so o duong

function M.is_road(gx, gy)
    return (gx % M.PERIOD) < M.ROAD_W or (gy % M.PERIOD) < M.ROAD_W
end

function M.inside(gx, gy)
    return gx >= 0 and gy >= 0 and gx < M.GRID and gy < M.GRID
end

-- Loai toa nha tai o (gx, gy): 0 = duong, 1..6 = chi so trong popart.BUILD.
-- Bam tat dinh, khong cap phat bo nho, goi duoc moi khung hinh.
function M.kind(gx, gy)
    if not M.inside(gx, gy) then return 0 end
    if M.is_road(gx, gy) then return 0 end
    local h = (gx * 31 + gy * 17 + gx * gy * 13) % 6
    return h + 1
end

-- He so cao cua o — tao duong chan troi rang cua. 1.0 / 1.25 / 1.5.
function M.height_mul(gx, gy)
    return 1 + ((gx * 5 + gy * 3) % 3) * 0.25
end

-- O chan duong di? Ngoai ban do cung tinh la chan (khong cho roi khoi thanh pho).
function M.solid(gx, gy)
    if not M.inside(gx, gy) then return true end
    return not M.is_road(gx, gy)
end

-- Chan theo toa do the gioi (float). Ban kinh `r` = nua be rong nhan vat.
-- Kiem tra 4 goc cua hinh vuong bao quanh: du de khong xuyen tuong, re hon
-- kiem tra hinh tron.
function M.blocked(x, y, r)
    r = r or 0.28
    local x0, x1 = math.floor(x - r), math.floor(x + r)
    local y0, y1 = math.floor(y - r), math.floor(y + r)
    if M.solid(x0, y0) then return true end
    if M.solid(x1, y0) then return true end
    if M.solid(x0, y1) then return true end
    if M.solid(x1, y1) then return true end
    return false
end

-- ---------------------------------------------------------------------------
-- Diem xuat phat & cac cot moc giao hang.
--
-- Duong chiem 2 o => tim duong nam o toa do nguyen: 1, 6, 11, 16, 21, 26, 31.
-- Dat dung TIM duong (khong phai 1.5) de xe con cho 0.5 o moi ben: be rong
-- xe la 0.34, neu dat lech thi chi con 0.16 va se ca vao tuong ngay.
-- ---------------------------------------------------------------------------
M.LANE = { 1, 6, 11, 16, 21, 26, 31 }   -- tim cac tuyen duong

M.SPAWN = { x = 1, y = 11, angle = 0.0 }

M.SPOTS = {
    { 11, 21 },
    { 21, 6 },
    { 6, 26 },
    { 26, 11 },
    { 16, 16 },
}

-- Ban kinh an cot moc, va binh phuong san de so sanh khong can sqrt.
M.MISSION_R = 1.3
M.MISSION_R2 = M.MISSION_R * M.MISSION_R

-- ---------------------------------------------------------------------------
-- Vat the tinh (billboard). `tint` chon bang mau trong popart.BUILD.
-- ---------------------------------------------------------------------------
M.SPRITES = {
    { x = 1.5,  y = 14.2, kind = "car",  tint = 1 },
    { x = 6.4,  y = 1.6,  kind = "car",  tint = 4 },
    { x = 11.4, y = 16.6, kind = "car",  tint = 2 },
    { x = 16.4, y = 6.5,  kind = "car",  tint = 6 },
    { x = 6.6,  y = 11.5, kind = "ped",  tint = 3 },
    { x = 11.5, y = 6.4,  kind = "ped",  tint = 5 },
    { x = 21.5, y = 11.6, kind = "ped",  tint = 1 },
    { x = 16.5, y = 21.4, kind = "booth", tint = 2 },
    { x = 21.4, y = 16.5, kind = "booth", tint = 4 },
}

-- Ban do nho (radar) chi ve cac vat the trong ban kinh nay.
M.RADAR_RANGE = 9.0

return M
