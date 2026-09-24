-- Pop Art City 3D — project mau LuaS30 / MRE.
--
-- Phong cach: pop-art (mau nong, vien den day, pixel rong) + thanh pho mo
-- kieu GTA. "3D" o day la PSEUDO-3D (raycasting DDA, kieu Wolfenstein/Doom):
-- MRE khong co GPU, khong co alpha, khong co ham ve pixel — xem src/render.lua
-- de biet vi sao renderer phai be ngang (cot tuong 4 px, khoi xa tron truoc).
--
-- Vong choi: lai xe quanh thanh pho, chay vao cot moc vang de giao hang.
-- Moi 3 chuyen thi tang mot muc truy na. Dam vao tuong thi mat HP; het HP thi
-- bi "WASTED" va choi lai tu dau.
--
-- Hop dong phim: xem src/keypad.lua + doc/ai/Keypad.md.
--   up/down/left/right   lai xe / di bo        ok hoac 5   len / xuong xe
--   softleft             tam dung              softright hoac back  tam dung
--   *                    doc nhanh HP / tien

local E = engine
local K = require("src.keypad")
local P = require("src.popart")
local C = require("src.city")
local R = require("src.render")
local HUD = require("src.hud")
local PL = require("src.player")

local W, H = P.W, P.H

-- ---------------------------------------------------------------------------
-- Hang so vat ly + trang thai nguoi choi: xem src/player.lua
-- ---------------------------------------------------------------------------
local FOOT_SPEED = PL.FOOT_SPEED
local FOOT_TURN  = PL.FOOT_TURN
local CAR_ACCEL  = PL.CAR_ACCEL
local CAR_BRAKE  = PL.CAR_BRAKE
local CAR_DRAG   = PL.CAR_DRAG
local CAR_MAX    = PL.CAR_MAX
local CAR_MAXR   = PL.CAR_MAXR
local CAR_TURN   = PL.CAR_TURN
local ENTER_R    = PL.ENTER_R
local CRASH_KM   = PL.CRASH_KM
local HP_REGEN   = PL.HP_REGEN

local TOAST_MS   = 1900
local WASTED_MS  = 2200

-- ---------------------------------------------------------------------------
-- Trang thai man hinh
-- ---------------------------------------------------------------------------
local state = "title"
local previous = "title"
local menu_index = 1
local pause_index = 1
local toast = ""
local toast_at = 0
local wasted_at = 0
local mission_index = 1
local deliveries = 0

local TITLE_MENU = {
    { label = "BAT DAU",   go = "play" },
    { label = "HUONG DAN", go = "help" },
    { label = "THOAT",     go = "exit" },
}

local PAUSE_MENU = {
    { label = "TIEP TUC",  go = "resume" },
    { label = "HUONG DAN", go = "help" },
    { label = "CHOI LAI",  go = "restart" },
    { label = "THOAT",     go = "exit" },
}

local player = PL.p
local car = PL.car

local function say(msg)
    toast = msg
    toast_at = E.tick_ms()
end

local function toast_text()
    if toast == "" then return "" end
    if E.tick_ms() - toast_at >= TOAST_MS then
        toast = ""
        return ""
    end
    return toast
end

local function current_mission()
    local s = C.SPOTS[mission_index]
    return { x = s[1], y = s[2], kind = "marker" }
end

local function reset_run()
    PL.reset(C.SPAWN)
    mission_index, deliveries = 1, 0
    toast = ""
    K.reset()
end

-- ---------------------------------------------------------------------------
-- Di chuyen: thu truc X roi truc Y rieng => truot doc theo tuong thay vi
-- dung im khi dam cheo goc. Tra ve true neu bi chan.
-- ---------------------------------------------------------------------------
local function move_ent(ent, dx, dy, r)
    local hit = false
    if dx ~= 0 then
        if not C.blocked(ent.x + dx, ent.y, r) then
            ent.x = ent.x + dx
        else
            hit = true
        end
    end
    if dy ~= 0 then
        if not C.blocked(ent.x, ent.y + dy, r) then
            ent.y = ent.y + dy
        else
            hit = true
        end
    end
    return hit
end

local function drive(dt)
    if K.up() then player.speed = player.speed + CAR_ACCEL * dt end
    if K.down() then player.speed = player.speed - CAR_BRAKE * dt end

    local drag = CAR_DRAG * dt
    if player.speed > 0 then
        player.speed = player.speed - drag
        if player.speed < 0 then player.speed = 0 end
    elseif player.speed < 0 then
        player.speed = player.speed + drag
        if player.speed > 0 then player.speed = 0 end
    end
    if player.speed > CAR_MAX then player.speed = CAR_MAX end
    if player.speed < CAR_MAXR then player.speed = CAR_MAXR end

    -- Tay lai an theo toc do, NHUNG co san mot muc toi thieu: neu khong thi xe
    -- dung yen la khong quay duoc chut nao, ket vao tuong la het duong thoat.
    -- (Do la lua chon arcade co y — xe that phai chay moi lai duoc.)
    local grip = 0.35 + 0.65 * math.abs(player.speed) / 2.5
    if grip > 1 then grip = 1 end
    local sense = 1
    if player.speed < 0 then sense = -1 end
    if K.left() then
        player.angle = player.angle - CAR_TURN * grip * sense * dt
    end
    if K.right() then
        player.angle = player.angle + CAR_TURN * grip * sense * dt
    end

    local step = player.speed * dt
    local hit = move_ent(player, math.cos(player.angle) * step,
                         math.sin(player.angle) * step, 0.34)
    if hit then
        local dmg = math.floor(math.abs(player.speed) * CRASH_KM)
        if dmg > 0 then
            player.hp = player.hp - dmg
            if player.hp < 0 then player.hp = 0 end
            say("-" .. dmg .. " HP")
        end
        player.speed = -player.speed * 0.25
    end
    car.x, car.y, car.angle = player.x, player.y, player.angle
end

local function walk(dt)
    if K.left() then player.angle = player.angle - FOOT_TURN * dt end
    if K.right() then player.angle = player.angle + FOOT_TURN * dt end

    local mv = 0
    if K.up() then mv = mv + 1 end
    if K.down() then mv = mv - 1 end
    if mv ~= 0 then
        local step = mv * FOOT_SPEED * dt
        move_ent(player, math.cos(player.angle) * step,
                 math.sin(player.angle) * step, 0.26)
    end
    if player.hp < 100 then
        player.hp = math.min(100, player.hp + HP_REGEN * dt)
    end
end

local function check_mission()
    local m = current_mission()
    local dx, dy = player.x - m.x, player.y - m.y
    if dx * dx + dy * dy > C.MISSION_R2 then return end
    if not player.in_car then
        say("PHAI LAI XE MOI GIAO DUOC")
        return
    end
    deliveries = deliveries + 1
    player.money = player.money + 250
    if deliveries % 3 == 0 and player.wanted < 5 then
        player.wanted = player.wanted + 1
        say("+250$  TRUY NA CAP " .. player.wanted)
    else
        say("+250$  DA GIAO " .. deliveries)
    end
    mission_index = mission_index % #C.SPOTS + 1
end

local function update_play(dt)
    if player.in_car then drive(dt) else walk(dt) end
    check_mission()
    if player.hp <= 0 then
        state = "wasted"
        wasted_at = E.tick_ms()
        player.speed = 0
    end
end

-- ---------------------------------------------------------------------------
-- Ve
-- ---------------------------------------------------------------------------
local function draw_title()
    R.backdrop()

    local bw, bh = 208, 100
    local bx, by = math.floor((W - bw) / 2), 30
    P.panel(bx, by, bw, bh, P.C.ink, P.C.hot, 3)
    P.text_shadow(bx + 16, by + 16, "POP ART", P.C.sun, P.C.hot, 4)
    P.text_shadow(bx + 16, by + 44, "CITY 3D", P.C.cyan, P.C.hot, 4)
    E.text(bx + 16, by + 78, "PSEUDO-3D RAYCAST 240x320", P.C.paper)

    local my = 168
    for i = 1, #TITLE_MENU do
        local label = TITLE_MENU[i].label
        local tw = P.text_w(label, 2)
        local x = math.floor((W - tw) / 2)
        local y = my + (i - 1) * 28
        if i == menu_index then
            P.panel(x - 14, y - 7, tw + 28, 24, P.C.hot, P.C.ink, 2)
            P.text(x, y, label, P.C.paper, 2)
        else
            P.panel(x - 14, y - 7, tw + 28, 24, P.C.chip_dim, P.C.ink, 2)
            P.text(x, y, label, P.C.dim, 2)
        end
    end

    local foot = "UP/DOWN  OK  SOFT-R THOAT"
    E.text(math.floor((W - E.text_width(foot)) / 2), H - 20, foot, P.C.paper)
end

local function draw_pause()
    R.frame(player.x, player.y, player.angle, current_mission())

    local bw, bh = 200, 156
    local bx, by = math.floor((W - bw) / 2), 74
    P.panel(bx, by, bw, bh, P.C.deep, P.C.hot, 3)
    P.text_shadow(bx + 18, by + 14, "TAM DUNG", P.C.sun, P.C.hot, 3)

    for i = 1, #PAUSE_MENU do
        local label = PAUSE_MENU[i].label
        local tw = P.text_w(label, 2)
        local x = bx + 20
        local y = by + 48 + (i - 1) * 26
        if i == pause_index then
            P.panel(x - 8, y - 6, tw + 16, 22, P.C.hot, P.C.ink, 2)
            P.text(x, y, label, P.C.paper, 2)
        else
            P.text(x, y, label, P.C.dim, 2)
        end
    end
    E.text(bx + 18, by + bh - 16, "HP " .. math.floor(player.hp) ..
           "   $" .. player.money, P.C.paper)
end

local function draw_help()
    P.checker(0, 0, W, H, P.C.check_a, P.C.check_b, 10)
    P.text_shadow(12, 14, "HUONG DAN", P.C.sun, P.C.hot, 3)

    -- Moi dong <= 31 ky tu: 14 + 31 * 7.25 = 239 <= 240. Be rong 7.25 la so
    -- DO THAT cua font firmware o set_font(8) (text_width("ABCDEFGHIJ") = 72.2),
    -- khong phai uoc luong — xem tools/popart_city_check.lua phan F4.
    local lines = {
        { "LAI XE", P.C.cyan },
        { "  up / 2      tang toc", P.C.paper },
        { "  down / 8    phanh, lui", P.C.paper },
        { "  left right  lai (phai chay)", P.C.paper },
        { "", P.C.paper },
        { "DI BO", P.C.cyan },
        { "  up down     tien / lui", P.C.paper },
        { "  left right  quay", P.C.paper },
        { "  ok hoac 5   len / xuong xe", P.C.paper },
        { "", P.C.paper },
        { "CHOI", P.C.cyan },
        { "  Vao cot moc de giao hang.", P.C.paper },
        { "  Moi 3 chuyen +1 truy na.", P.C.paper },
        { "  Dam tuong mat HP -> WASTED.", P.C.paper },
        { "  *           xem HP / tien", P.C.paper },
        { "", P.C.paper },
        { "Phim vat ly KHONG phai ten Lua", P.C.dim },
        { "Runtime chi gui chu thuong.", P.C.dim },
    }
    for i = 1, #lines do
        E.text(14, 52 + (i - 1) * 13, lines[i][1], lines[i][2])
    end
    E.text(14, H - 22, "BAM OK / SOFT-R DE QUAY LAI", P.C.sun)
end

local function draw_wasted()
    local bw, bh = 200, 92
    local bx, by = math.floor((W - bw) / 2), 100
    P.panel(bx, by, bw, bh, P.C.ink, P.C.hot, 3)
    P.text_shadow(bx + 22, by + 16, "WASTED", P.C.hot, P.C.paper, 4)
    E.text(bx + 22, by + 58, "Xe hong. Choi lai tu dau...", P.C.paper)
end

function E.load()
    E.set_font(8)
    reset_run()
    state = "title"
    menu_index = 1
    pause_index = 1
end

function E.update(dt)
    if not dt or dt <= 0 then dt = 1 / 15 end
    if dt > 0.2 then dt = 0.2 end
    if state == "play" then
        update_play(dt)
    elseif state == "wasted" then
        if E.tick_ms() - wasted_at >= WASTED_MS then
            reset_run()
            state = "play"
        end
    end
end

function E.draw()
    if state == "title" then
        draw_title()
    elseif state == "help" then
        draw_help()
    elseif state == "pause" then
        draw_pause()
    else
        R.frame(player.x, player.y, player.angle, current_mission())
        HUD.draw({
            px = player.x, py = player.y, angle = player.angle,
            hp = player.hp, money = player.money, wanted = player.wanted,
            speed = math.abs(player.speed) / CAR_MAX,
            in_car = player.in_car,
            toast = toast_text(),
            mission = current_mission(),
        })
        if state == "wasted" then draw_wasted() end
    end
end

-- `fresh` = lan nhan DAU TIEN. Dieu huong (up/down) KHONG chan fresh de giu
-- phim con cuon nhanh; moi hanh dong mot lan (ok, softkey, *) thi phai chan.
local function key_title(k, fresh)
    if k == "up" or k == "2" then
        menu_index = menu_index - 1
        if menu_index < 1 then menu_index = #TITLE_MENU end
    elseif k == "down" or k == "8" then
        menu_index = menu_index + 1
        if menu_index > #TITLE_MENU then menu_index = 1 end
    elseif (k == "ok" or k == "5") and fresh then
        local go = TITLE_MENU[menu_index].go
        if go == "exit" then
            E.exit()
        elseif go == "help" then
            previous = "title"
            state = "help"
            K.reset()
        else
            reset_run()
            state = "play"
            K.reset()
        end
    elseif (k == "softright" or k == "back") and fresh then
        E.exit()
    end
end

local function key_play(k, fresh)
    if k == "softleft" and fresh then
        previous = "play"
        state = "pause"
        pause_index = 1
        K.reset()
    elseif (k == "softright" or k == "back") and fresh then
        previous = "play"
        state = "pause"
        pause_index = 1
        K.reset()
    elseif (k == "ok" or k == "5") and fresh then
        if player.in_car then
            player.in_car = false
            player.speed = 0
            say("DA XUONG XE")
        else
            local dx, dy = car.x - player.x, car.y - player.y
            if dx * dx + dy * dy < ENTER_R * ENTER_R then
                player.in_car = true
                player.x, player.y = car.x, car.y
                say("DA LEN XE")
            else
                say("LAI XE CHO GAN HON")
            end
        end
    elseif k == "*" and fresh then
        say("HP " .. math.floor(player.hp) .. "   $" .. player.money)
    end
end

local function key_pause(k, fresh)
    if k == "up" or k == "2" then
        pause_index = pause_index - 1
        if pause_index < 1 then pause_index = #PAUSE_MENU end
    elseif k == "down" or k == "8" then
        pause_index = pause_index + 1
        if pause_index > #PAUSE_MENU then pause_index = 1 end
    elseif (k == "ok" or k == "5") and fresh then
        local go = PAUSE_MENU[pause_index].go
        if go == "exit" then
            E.exit()
        elseif go == "help" then
            previous = "pause"
            state = "help"
            K.reset()
        elseif go == "restart" then
            reset_run()
            state = "play"
            K.reset()
        else
            state = "play"
            K.reset()
        end
    elseif (k == "softright" or k == "back") and fresh then
        state = "play"
        K.reset()
    end
end

function E.keypressed(raw)
    local k, fresh = K.press(raw)
    if not k then return end

    if state == "title" then
        key_title(k, fresh)
    elseif state == "play" then
        key_play(k, fresh)
    elseif state == "pause" then
        key_pause(k, fresh)
    elseif state == "help" then
        if fresh and (k == "ok" or k == "5" or k == "softleft"
                      or k == "softright" or k == "back" or k == "clear") then
            state = previous
            K.reset()
        end
    elseif state == "wasted" then
        if fresh and (k == "ok" or k == "5" or k == "softright" or k == "back") then
            reset_run()
            state = "play"
        end
    end
end

function E.keyreleased(raw)
    K.release(raw)
end

function E.pause()
    K.reset()
end

function E.resume()
    K.reset()
end
