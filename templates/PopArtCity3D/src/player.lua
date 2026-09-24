-- src/player.lua — trang thai nguoi choi va xe.
--
-- Tach rieng khoi main.lua de: (a) main.lua chi con viec dieu phoi man hinh,
-- (b) harness tools/popart_city_check.lua doc duoc vi tri that thay vi phai
-- suy dien tu pixel da ve.
--
-- Don vi: 1.0 = mot o ban do (xem src/city.lua). Goc tinh bang radian,
-- 0 = huong +X, tang theo chieu +Y.

local M = {}

-- Nguoi choi
M.p = {
    x = 0, y = 0, angle = 0,
    hp = 100, money = 0, wanted = 0,
    in_car = true, speed = 0,
}

-- Xe (khi xuong xe thi xe dung yen tai cho)
M.car = { x = 0, y = 0, angle = 0 }

-- Hang so vat ly
M.FOOT_SPEED = 2.4
M.FOOT_TURN  = 2.9
M.CAR_ACCEL  = 5.5
M.CAR_BRAKE  = 8.5
M.CAR_DRAG   = 1.7
M.CAR_MAX    = 6.4
M.CAR_MAXR   = -2.2
M.CAR_TURN   = 2.5
M.ENTER_R    = 1.7
M.CRASH_KM   = 3.5
M.HP_REGEN   = 3.0

-- Dat lai ve diem xuat phat cua ban do.
function M.reset(spawn)
    local p = M.p
    p.x, p.y, p.angle = spawn.x, spawn.y, spawn.angle
    p.hp, p.money, p.wanted = 100, 0, 0
    p.in_car, p.speed = true, 0
    M.car.x, M.car.y, M.car.angle = p.x, p.y, p.angle
end

return M
