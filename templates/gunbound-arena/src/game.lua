-- Gunbound Arena: dot bo phao binh pha duoc dat, gio thay doi, AI mo phong quy dao.
local E = engine
local Gfx = require("src.gfx")
local I18n = require("src.i18n")
local Save = require("src.save")
local C = Gfx.C
local M = {}
M.onExit = function() end

local G_ACC   = 300      -- gravity px/s^2
local WIND_U  = 3        -- wind quantised to multiples of 3, max +/-45
local TURN_T  = 25
local HIT_R    = 32      -- splash damage radius
local MOVE_SPD = 26      -- tank drive speed px/s
local MOVE_MP  = 60      -- move points per turn (1 per px)
local CHG_SPD  = 95      -- power bar sweep speed units/s
local AN_SPD   = 55      -- barrel sweep speed deg/s

-- canvas that 240x320 (src/screen.lua); HUD neo day qua SH
local SH = require("src.screen").H
local PANEL_Y = SH - 26  -- bottom HUD top edge
local TERR_B  = SH - 30  -- terrain digging floor / lethal hole depth

-- each gun has its own usable angle zone, blast radius, damage and ammo
local WEAPONS = {
    { a0 = 5,  a1 = 175, r = 16, dmg = 48, ammo = 99, sz = 3, tag = "P" },
    { a0 = 20, a1 = 160, r = 18, dmg = 60, ammo = 3,  sz = 4, tag = "B" },
    { a0 = 60, a1 = 120, r = 20, dmg = 72, ammo = 2,  sz = 5, tag = "M" },
}
local DLY_MOVE, DLY_ITEM, DLY_GUN, DLY_BASE = 2, 4, 2, 3

local mode     -- 1 = vs CPU, 2 = hotseat
local st       -- intro|aim|bag|planex|plane|aimove|aithink|flight|msg|boom|fall|over
local terr = {}
local terrVer = 0
local drawTerrain = Gfx.newTerrain()
local drawDunes = Gfx.newDunes()
local tanks = {}
local cur, wind, timer
local stateT, msgText, nextAct
local proj, fx, fxN, t, seed
local aiShot, aiMoveX
local charging, charge, chargeDir
local lastEx, lastEy
local bagIdx, planeX, planeFx, planeFy, dying, turnStarted

-- particle pool: fixed tables, swap-remove, never allocated mid-battle
fx, fxN = {}, 0
for i = 1, 48 do fx[i] = { x = 0, y = 0, vx = 0, vy = 0, life = 0, ttl = 1, col = nil, big = false } end
local function spawnP(x, y, vx, vy, life, col, big)
    if fxN >= #fx then return end
    fxN = fxN + 1
    local p = fx[fxN]
    p.x = x; p.y = y; p.vx = vx; p.vy = vy; p.life = life; p.col = col; p.big = big
end

-- shell trail: ring buffer of 14 preallocated points
local TRN = 14
local trX, trY, trHead, trCount = {}, {}, 0, 0
for i = 1, TRN do trX[i], trY[i] = 0, 0 end
local function trailReset() trHead, trCount = 0, 0 end
local function trailPush(x, y)
    trHead = trHead % TRN + 1
    trX[trHead], trY[trHead] = x, y
    if trCount < TRN then trCount = trCount + 1 end
end

-- HUD value strings are memoized: concatenation happens only when the
-- shown number changes, not every frame
local hudA, hudP, hudM, hudS = -1, -1, -1, -1
local sA, sP, sM, sS = "", "", "", ""
local hudWind, sWs, sWsLine = nil, "", ""
local hudThink = ""
local tagV, tagS = -1, "GB"

-- small deterministic LCG (double-safe range)
local function rnd()
    seed = (seed * 125 + 2013) % 16777216
    return seed / 16777216
end

local function tcol(x)
    if x < 1 then x = 1 elseif x > 240 then x = 240 end
    return terr[math.floor(x + 0.5)]
end

local useItem   -- forward decl: AI helpers reference it

local function powerToV(p) return 90 + p * 1.7 end

-- angle is ABSOLUTE: 0 = shoot left, 90 = straight up, 180 = shoot right
local function gunTip(tk)
    local rad = tk.angle * math.pi / 180
    return tk.x + 8 + math.cos(rad) * 10, tk.y + 3 - math.sin(rad) * 10
end

local function tryMove(tk, dir, dt, foeX)
    if tk.mp <= 0 or tk.webbed > 0 then return false end
    local nx = tk.x + MOVE_SPD * dt * dir
    if nx < 4 then nx = 4 elseif nx > 219 then nx = 219 end
    if math.abs(nx - foeX) < 20 then return false end
    -- cannot climb crater walls steeper than ~5px per px
    if tcol(nx + 8) < tcol(tk.x + 8) - 5 then return false end
    local d = math.abs(nx - tk.x)
    if d > tk.mp then
        nx = tk.x + (dir > 0 and tk.mp or -tk.mp)
        d = tk.mp
    end
    if d <= 0 then return false end
    tk.mp = tk.mp - d
    tk.x = nx
    if not tk.moved then tk.moved = true; tk.dly = tk.dly + DLY_MOVE end
    return true
end

-- every action costs delay points; turns come by lowest accumulated clock
local function endTurn()
    local tk = tanks[cur]
    tk.clock = tk.clock + (DLY_BASE + tk.dly) / tk.agi
    if tk.webbed > 0 then tk.webbed = tk.webbed - 1 end
    local a, b = tanks[1].clock, tanks[2].clock
    local nxt
    if a < b - 0.0001 then nxt = 1
    elseif b < a - 0.0001 then nxt = 2
    else nxt = 3 - cur end
    startTurn(nxt)
end

local function switchWeapon(tk)
    for k = 1, 3 do
        local nw = ((tk.wpn - 1 + k) % 3) + 1
        if tk.ammo[nw] > 0 then
            tk.wpn = nw
            local w = WEAPONS[nw]
            if tk.angle < w.a0 then tk.angle = w.a0
            elseif tk.angle > w.a1 then tk.angle = w.a1 end
            tk.dly = tk.dly + DLY_GUN
            return true
        end
    end
    return false
end

-- ------------------------------------------------------------------ setup
local function genTerrain()
    local pts = {}
    for i = 0, 15 do pts[i + 1] = SH - 152 + rnd() * 78 end
    for x = 1, 240 do
        local f = (x - 1) / 16
        local i = math.floor(f) + 1
        local u = f - math.floor(f)
        u = u * u * (3 - 2 * u)
        terr[x] = pts[i] + (pts[i + 1] - pts[i]) * u
    end
    for pass = 1, 2 do
        local old = {}
        for x = 1, 240 do old[x] = terr[x] end
        for x = 2, 239 do terr[x] = (old[x - 1] + 2 * old[x] + old[x + 1]) / 4 end
    end
    for x = 1, 240 do terr[x] = math.floor(terr[x] + 0.5) end
    for _, tx in ipairs({ tanks[1].x + 8, tanks[2].x + 8 }) do
        local y0 = tcol(tx)
        for x = tx - 10, tx + 10 do
            if x >= 1 and x <= 240 then terr[x] = y0 end
        end
    end
    terrVer = terrVer + 1
end

function M.start(m)
    mode = m
    local clock = (os and os.time and os.time()) or 777
    seed = (clock * 65537 + 12345) % 16777216
    local cpuAgi = ({ 8, 10, 12 })[Save.diff] or 10
    tanks = {
        { x = 24 + math.floor(rnd() * 16), dir = 1,  hp = 100, mp = MOVE_MP, angle = 60,  power = 60,
          agi = 10, c1 = C.blue1, c2 = C.blue2, c3 = C.blue3 },
        { x = 196 + math.floor(rnd() * 16), dir = -1, hp = 100, mp = MOVE_MP, angle = 120, power = 60,
          agi = mode == 1 and cpuAgi or 10, c1 = C.red1, c2 = C.red2, c3 = C.red3 },
    }
    for _, tk in ipairs(tanks) do
        tk.wpn, tk.ammo, tk.items = 1, { 99, 3, 2 }, { 2, 1, 1 }
        tk.webbed, tk.frozen, tk.clock, tk.dly, tk.moved = 0, 0, 0, 0, false
    end
    genTerrain()
    for _, tk in ipairs(tanks) do tk.y = tcol(tk.x + 8) - 10 end
    proj, t, aiShot = nil, 0, nil
    fxN = 0
    trailReset()
    -- reset memoized HUD strings (language may have changed in the menu)
    hudA, hudP, hudM, hudS = -1, -1, -1, -1
    hudWind = nil
    hudThink = (mode == 1 and I18n.k.name_ai or I18n.k.name_p2) .. " ..."
    tagV = -1
    cur, turnStarted, dying = nil, false, nil
    st = "intro"
    msgText = nil
    startTurn(1)
end

local function nameOf(i)
    local k = I18n.k
    if mode == 1 then return i == 1 and k.name_you or k.name_ai end
    return i == 1 and k.name_p1 or i == 2 and k.name_p2 or "P1"
end

-- ASCII-only status tag: gun code + remaining special ammo (P3 = bazooka x3)
-- memoized: rebuilt only when gun/ammo actually change
function weaponTag()
    if not cur then return "GB" end
    local tk = tanks[cur]
    local v = tk.wpn * 256 + tk.ammo[tk.wpn]
    if v ~= tagV then
        tagV = v
        local w = WEAPONS[tk.wpn]
        local a = tk.ammo[tk.wpn]
        tagS = w.tag .. (a < 99 and tostring(a) or "")
    end
    return tagS
end

function startTurn(i)
    local again = turnStarted and cur == i
    cur = i
    local tk = tanks[i]
    wind = (math.floor(rnd() * 31) - 15) * WIND_U
    timer = TURN_T
    proj = nil
    charging = false
    tk.mp = MOVE_MP
    tk.dly = 0
    tk.moved = false
    turnStarted = true
    if tk.frozen > 0 then
        tk.frozen = tk.frozen - 1
        st = "msg"
        stateT = 1.1
        nextAct = "frozen"
        msgText = I18n.k.frozen_skip
        return
    end
    st = "intro"
    stateT = 1.0
    nextAct = "begin"
    if again then
        msgText = I18n.k.turn_again
        return
    end
    msgText = I18n.k.turn_you
    if mode == 1 then
        if i == 1 then msgText = I18n.k.turn_you else msgText = I18n.k.turn_ai end
    else
        msgText = i == 1 and I18n.k.turn_p1 or I18n.k.turn_p2
    end
end

-- --------------------------------------------------------------------- AI
-- returns landing x, or nil when the shell leaves the field
local function simulate(x, y, vx, vy, w)
    local dt = 1 / 30
    for _ = 1, 600 do
        vx = vx + w * dt
        vy = vy + G_ACC * dt
        x = x + vx * dt
        y = y + vy * dt
        if x < -10 or x > 250 or y > SH + 10 then return nil end
        local foe = tanks[1]
        if math.abs(x - (foe.x + 8)) <= 9 and y >= foe.y and y <= foe.y + 11 then
            return x
        end
        if y >= tcol(x) then return x end
    end
    return nil
end

local function aiCompute()
    local me, foe = tanks[2], tanks[1]
    local w = WEAPONS[me.wpn]
    local lo, hi = w.a0, w.a1
    local best, ba, bp = nil, nil, nil
    local function consider(a, p)
        if a < lo or a > hi or p < 5 or p > 100 then return end
        local rad = a * math.pi / 180
        local v = powerToV(p)
        local x, y = gunTip(me)
        local lx = simulate(x, y, math.cos(rad) * v, -math.sin(rad) * v, wind)
        if lx then
            local sc = math.abs(lx - (foe.x + 8))
            if not best or sc < best then best, ba, bp = sc, a, p end
        end
    end
    if me.webbed > 0 then
        -- barrel frozen: only the power dial is left
        for p = 5, 100, 2 do consider(me.angle, p) end
    else
        for a = lo, hi, 10 do
            for p = 25, 100, 15 do consider(a, p) end
        end
        if ba then
            for a = ba - 10, ba + 10, 5 do
                for p = bp - 15, bp + 15, 5 do consider(a, p) end
            end
        end
    end
    if not ba then ba, bp = me.webbed > 0 and me.angle or 135, 60 end
    local errA = ({ 8, 4, 1.5 })[Save.diff] or 4
    local errP = ({ 16, 8, 3 })[Save.diff] or 8
    ba = math.min(hi, math.max(lo, math.floor(ba + (rnd() * 2 - 1) * errA + 0.5)))
    bp = math.min(100, math.max(5, math.floor(bp + (rnd() * 2 - 1) * errP + 0.5)))
    aiShot = { a = ba, p = bp }
end

-- CPU throws web / freezes when it can afford the delay
local function aiWantItem()
    local me, foe = tanks[2], tanks[1]
    local p = ({ 0.12, 0.25, 0.45 })[Save.diff] or 0.25
    if foe.webbed > 0 or foe.frozen > 0 then return false end
    if rnd() > p then return false end
    if me.items[1] > 0 and (me.items[2] == 0 or rnd() < 0.6) then
        useItem(2, 1)
        return true
    elseif me.items[2] > 0 then
        useItem(2, 2)
        return true
    end
    return false
end

-- AI drives a bit before shooting: too close -> back off, too far -> close in
local function aiPickMove()
    local me, foe = tanks[2], tanks[1]
    local d = math.abs((me.x + 8) - (foe.x + 8))
    local want
    if d < 70 then want = (me.x < foe.x and -1 or 1) * (20 + rnd() * 25)
    elseif d > 160 then want = (me.x < foe.x and 1 or -1) * (20 + rnd() * 20)
    elseif rnd() < 0.4 then want = (rnd() * 2 - 1) * 14
    else want = 0 end
    aiMoveX = me.x + want
    if aiMoveX < 4 then aiMoveX = 4 elseif aiMoveX > 219 then aiMoveX = 219 end
    if math.abs(aiMoveX - foe.x) < 20 then aiMoveX = me.x end
end

-- ---------------------------------------------------------------- effects
local function disc(x, y, r, col)
    for dy = -r, r do
        local half = math.floor(math.sqrt(math.max(0, r * r - dy * dy)))
        Gfx.srect(x - half, y + dy, half * 2 + 1, 1, col)
    end
end

local function explodeAt(ex, ey, w)
    lastEx, lastEy = ex, ey
    for x = math.max(1, ex - w.r), math.min(240, ex + w.r) do
        local dx = x - ex
        local dy = math.floor(math.sqrt(math.max(0, w.r * w.r - dx * dx)))
        local bottom = math.min(TERR_B, ey + dy)
        if bottom > terr[x] then terr[x] = bottom end
    end
    terrVer = terrVer + 1
    for i = 1, 2 do
        local tk = tanks[i]
        local dx = (tk.x + 8) - ex
        local dy = (tk.y + 5) - ey
        local d = math.sqrt(dx * dx + dy * dy)
        if d < HIT_R then
            local dmg = math.floor(w.dmg * (1 - d / HIT_R) + 0.5)
            if d < 9 then dmg = dmg + 8 end
            tk.hp = tk.hp - math.max(2, dmg)
        end
    end
    for i = 1, 26 do
        local a = Gfx.hash(seed + i * 77) * 6.28
        local sp = 26 + Gfx.hash(seed + i * 31) * 70
        spawnP(ex, ey, math.cos(a) * sp, math.sin(a) * sp - 30,
            0.35 + Gfx.hash(seed + i * 13) * 0.55,
            i % 3 == 0 and C.fire2 or (i % 2 == 0 and C.fire or C.flash), false)
    end
    for i = 1, 8 do
        local a = Gfx.hash(seed + 400 + i * 57) * 6.28
        spawnP(ex, ey - 4, math.cos(a) * 12, -22 - Gfx.hash(seed + i) * 16,
            0.8, C.smoke, true)
    end
    st = "boom"
    stateT = 1.0
    nextAct = "settle"
end

local function fire()
    local tk = tanks[cur]
    local w = WEAPONS[tk.wpn]
    if tk.ammo[tk.wpn] < 99 then tk.ammo[tk.wpn] = tk.ammo[tk.wpn] - 1 end
    local x, y = gunTip(tk)
    local rad = tk.angle * math.pi / 180
    local v = powerToV(tk.power)
    proj = { x = x, y = y, vx = math.cos(rad) * v, vy = -math.sin(rad) * v, w = w }
    trailReset()
    charging = false
    st = "flight"
end

-- idx: 1 web, 2 ice, 3 plane
useItem = function(i, idx)
    local tk, foe = tanks[i], tanks[3 - i]
    if tk.items[idx] <= 0 then return false end
    if idx == 3 then
        planeX = tk.x
        st = "planex"
        return true
    end
    tk.items[idx] = tk.items[idx] - 1
    tk.dly = tk.dly + DLY_ITEM
    if idx == 1 then
        foe.webbed = 2
        msgText = I18n.k.used_web
    else
        foe.frozen = 1
        msgText = I18n.k.used_ice
    end
    st = "msg"
    stateT = 0.9
    nextAct = "resume"
    return true
end

-- ----------------------------------------------------------------- update
local held = {}

local function finishOver()
    st = "over"
    stateT = 0
    if tanks[1].hp > 0 then Save.w1 = Save.w1 + 1 else Save.w2 = Save.w2 + 1 end
    Save.save()
end

local function settle()
    if tanks[1].hp <= 0 or tanks[2].hp <= 0 then finishOver() return end
    -- shell dug the ground under a tank out: it falls into the hole and dies
    for i = 1, 2 do
        if tanks[i].hp > 0 and tcol(tanks[i].x + 8) >= TERR_B - 1 then
            dying = i
            st = "fall"
            stateT = 1.2
            msgText = I18n.k.fell
            return
        end
    end
    endTurn()
end

local function confirmPlane()
    local tk = tanks[cur]
    tk.items[3] = tk.items[3] - 1
    tk.dly = tk.dly + DLY_ITEM
    planeFx, planeFy = tk.x, tk.y
    st = "plane"
    stateT = 1.2
end

function M.update(dt)
    t = t + dt
    -- tanks sink when terrain under them is blown away (fall/plane animate y themselves)
    if st ~= "fall" and st ~= "plane" then
        for _, tk in ipairs(tanks) do
            local gy = tcol(tk.x + 8) - 10
            if tk.y < gy then
                tk.y = math.min(gy, tk.y + 150 * dt)
            elseif tk.y > gy then
                tk.y = gy
            end
        end
    end
    -- particles (swap-remove keeps the pool dense, no shifting, no GC)
    local i = 1
    while i <= fxN do
        local p = fx[i]
        p.life = p.life - dt
        if p.life <= 0 then
            local last = fx[fxN]
            fx[fxN], fx[i] = p, last
            fxN = fxN - 1
        else
            p.vy = p.vy + 90 * dt
            p.x = p.x + p.vx * dt
            p.y = p.y + p.vy * dt
            i = i + 1
        end
    end

    if st == "intro" then
        stateT = stateT - dt
        if stateT <= 0 then
            if mode == 1 and cur == 2 then
                if aiWantItem() then
                    -- st is now "msg" with nextAct "resume"
                else
                    aiPickMove()
                    st = "aimove"
                    stateT = 4
                end
            else
                st = "aim"
                timer = TURN_T
            end
        end
    elseif st == "aimove" then
        local tk = tanks[2]
        stateT = stateT - dt
        if stateT <= 0 or math.abs(tk.x - aiMoveX) < 0.7 or tk.mp <= 0
           or not tryMove(tk, aiMoveX > tk.x and 1 or -1, dt, tanks[1].x) then
            st = "aithink"
            stateT = 0.7
            aiCompute()
        end
    elseif st == "aithink" then
        stateT = stateT - dt
        if stateT <= 0 then
            local tk = tanks[2]
            tk.angle, tk.power = aiShot.a, aiShot.p
            fire()
        end
    elseif st == "planex" then
        if held["left"]  then planeX = planeX - 70 * dt end
        if held["right"] then planeX = planeX + 70 * dt end
        if planeX < 4 then planeX = 4 elseif planeX > 219 then planeX = 219 end
        local foe = tanks[3 - cur]
        if math.abs(planeX - foe.x) < 20 then
            planeX = foe.x + (planeX >= foe.x and 20 or -20)
        end
    elseif st == "plane" then
        stateT = stateT - dt
        local tk = tanks[cur]
        local k = 1 - math.max(0, stateT) / 1.2
        local ty = tcol(planeX + 8) - 10
        tk.x = planeFx + (planeX - planeFx) * k
        tk.y = planeFy + (ty - planeFy) * k - math.sin(k * math.pi) * 55
        if stateT <= 0 then
            tk.x = planeX
            tk.y = tcol(planeX + 8) - 10
            msgText = I18n.k.used_plane
            st = "msg"
            stateT = 0.7
            nextAct = "resume"
        end
    elseif st == "fall" then
        stateT = stateT - dt
        local tk = tanks[dying]
        tk.y = tk.y + 130 * dt
        if stateT <= 0 then
            tk.hp = 0
            finishOver()
        end
    elseif st == "aim" then
        local tk = tanks[cur]
        local w = WEAPONS[tk.wpn]
        if tk.webbed == 0 then
            if held["up"]   then tk.angle = math.min(w.a1, tk.angle + AN_SPD * dt) end
            if held["down"] then tk.angle = math.max(w.a0, tk.angle - AN_SPD * dt) end
            if held["left"]  then tryMove(tk, -1, dt, tanks[3 - cur].x) end
            if held["right"] then tryMove(tk, 1, dt, tanks[3 - cur].x) end
        end
        if charging then
            charge = charge + CHG_SPD * dt * chargeDir
            if charge >= 100 then charge = 100; chargeDir = -1
            elseif charge <= 5 then charge = 5; chargeDir = 1 end
        end
        timer = timer - dt
        if timer <= 0 then
            charging = false
            msgText = I18n.k.skipped
            st = "msg"
            stateT = 0.9
            nextAct = "switch"
        end
    elseif st == "flight" then
        local sub = 4
        local sdt = dt / sub
        for _ = 1, sub do
            proj.vx = proj.vx + wind * sdt
            proj.vy = proj.vy + G_ACC * sdt
            proj.x = proj.x + proj.vx * sdt
            proj.y = proj.y + proj.vy * sdt
            if proj.x < -20 or proj.x > 260 or proj.y > SH + 20 then
                msgText = I18n.k.flying
                st = "msg"
                stateT = 0.4
                nextAct = "switch"
                break
            end
            local hit = false
            for i = 1, 2 do
                local tk = tanks[i]
                if math.abs(proj.x - (tk.x + 8)) <= 9 and proj.y >= tk.y - 1 and proj.y <= tk.y + 11 then
                    hit = true
                    break
                end
            end
            if not hit and proj.y >= tcol(proj.x) then hit = true end
            if hit then
                explodeAt(math.floor(proj.x + 0.5), math.floor(proj.y + 0.5), proj.w)
                break
            end
        end
        if st == "flight" then
            trailPush(proj.x, proj.y)
        end
    elseif st == "boom" then
        stateT = stateT - dt
        if stateT <= 0 then settle() end
    elseif st == "msg" then
        stateT = stateT - dt
        if stateT <= 0 then
            if nextAct == "settle" then
                settle()
            elseif nextAct == "resume" then
                if mode == 1 and cur == 2 then
                    aiPickMove()
                    st = "aimove"
                    stateT = 4
                else
                    st = "aim"
                    timer = TURN_T
                end
            else
                endTurn()
            end
        end
    end
end

-- ------------------------------------------------------------------- draw
-- hull always faces the opponent; the barrel itself covers 0..180 deg
local function facing()
    tanks[1].dir = tanks[2].x >= tanks[1].x and 1 or -1
    tanks[2].dir = tanks[1].x >= tanks[2].x and 1 or -1
end

local function drawTank(tk, i)
    Gfx.tank(tk.dir, tk.c1, tk.c2, tk.c3, tk.x, tk.y)
    Gfx.barrel(tk.x + 8, tk.y + 3, tk.angle)
    Gfx.hpBar(tk.x - 3, tk.y - 8, tk.hp, false)
    Gfx.ptext_center(tk.x + 8, tk.y - 17, nameOf(i), tk.c3, 1)
    if tk.webbed > 0 then Gfx.itemIcon(1, tk.x + 5, tk.y) end
    if tk.frozen > 0 then Gfx.itemIcon(2, tk.x + 5, tk.y) end
    if i == cur and (st == "aim" or st == "aithink") and math.floor(t * 3) % 2 == 0 then
        Gfx.ptext_center(tk.x + 8, tk.y - 25, "v", tk.c3, 1)
    end
end

function M.draw()
    facing()
    E.clear(C.skyTop)
    Gfx.sky(t, wind / 14)
    Gfx.windStreaks(t, wind)
    drawDunes(terr, terrVer)
    drawTerrain(terr, terrVer, PANEL_Y)
    for x = 9, 235, 9 do
        Gfx.srect(x - 1, terr[x] + 1, 1, 1, C.grassHi)
    end
    Gfx.srect(0, PANEL_Y - 10, 240, 10, C.dirt3)
    Gfx.cactus(120, tcol(120))
    Gfx.cactus(78, tcol(78))

    drawTank(tanks[1], 1)
    drawTank(tanks[2], 2)

    if st == "plane" then
        local tk = tanks[cur]
        Gfx.srect(tk.x + 7, tk.y - 5, 2, 5, C.dim)   -- sling rope
        Gfx.planeSprite(tk.x + 8, tk.y - 10, 1, t)
    end

    if proj and (st == "flight") then
        for k = 1, trCount - 1, 2 do
            local idx = (trHead - k - 1) % TRN + 1
            Gfx.srect(math.floor(trX[idx]) - 1, math.floor(trY[idx]) - 1, 1, 1, C.smoke2)
        end
        local sz = proj.w and proj.w.sz or 3
        disc(proj.x, proj.y, 1, C.flash)
        Gfx.srect(math.floor(proj.x - sz / 2), math.floor(proj.y - sz / 2), sz, sz, C.shell)
        Gfx.srect(math.floor(proj.x), math.floor(proj.y) - 1, 1, 1, C.shellHi)
    end
    for i = 1, fxN do
        local p = fx[i]
        local s = p.big and 4 or (p.life > 0.4 and 2 or 1)
        Gfx.srect(math.floor(p.x), math.floor(p.y), s, s, p.col)
    end
    if st == "boom" and stateT > 0.85 then
        disc(math.floor(lastEx or 0), math.floor(lastEy or 0), 12, C.flash)
    end

    -- top HUD
    Gfx.topBar(nil, weaponTag())
    local k = I18n.k
    Gfx.ptext(4, 5, nameOf(cur), tanks[cur].c3, 1)
    Gfx.windGauge(112, 3, wind)
    if wind ~= hudWind then
        hudWind = wind
        sWs = tostring(math.floor(math.abs(wind) / WIND_U))
        sWsLine = k.lbl_wind .. " " .. sWs
    end
    Gfx.ptext(140, 5, sWs, wind == 0 and C.dim or C.yellow, 1)
    if st == "aim" then
        local secs = math.max(0, math.ceil(timer))
        if secs ~= hudS then hudS = secs; sS = tostring(secs) end
        Gfx.ptext(204, 5, sS, secs <= 5 and C.red or C.white, 1)
    end

    -- bottom HUD
    Gfx.srect(0, PANEL_Y, 240, 26, C.bar)
    Gfx.srect(0, PANEL_Y, 240, 1, C.barEdge)
    local tk = tanks[cur]
    if st == "aim" then
        local pw = charging and charge or tk.power
        local a = math.floor(tk.angle + 0.5)
        local p = math.floor(pw + 0.5)
        local m = math.floor(tk.mp + 0.5)
        if a ~= hudA then hudA = a; sA = k.lbl_angle .. " " .. a end
        if p ~= hudP then hudP = p; sP = k.lbl_power .. " " .. p end
        if m ~= hudM then hudM = m; sM = k.lbl_mp .. " " .. m end
        Gfx.ptext(5, PANEL_Y + 4, sA, C.cyan, 1)
        Gfx.ptext(62, PANEL_Y + 4, sP, C.yellow, 1)
        Gfx.gauge(62, PANEL_Y + 12, 52, 3, pw / 100,
                  charging and (math.floor(t * 8) % 2 == 0 and C.orange or C.yellow) or C.yellow)
        Gfx.ptext(126, PANEL_Y + 4, sM, C.green, 1)
        Gfx.gauge(126, PANEL_Y + 12, 40, 3, tk.mp / MOVE_MP, C.green)
        if tk.webbed > 0 then
            Gfx.ptext_center(120, PANEL_Y + 17, k.webbed, C.red, 1)
        else
            Gfx.ptext_center(120, PANEL_Y + 17, k.hint_aim, C.dim, 1)
        end
    elseif st == "aithink" or st == "aimove" then
        Gfx.ptext_center(120, PANEL_Y + 8, hudThink, C.red3, 1)
    elseif st == "flight" then
        Gfx.ptext_center(120, PANEL_Y + 8, k.flying, C.white, 1)
    else
        Gfx.ptext_center(120, PANEL_Y + 8, sWsLine, C.dim, 1)
    end

    -- overlays
    if (st == "intro" or st == "msg" or st == "fall") and msgText then
        local wpx = Gfx.ptext_width(msgText, 1) + 16
        local my = SH - 180
        Gfx.srect(math.floor(120 - wpx / 2), my, wpx, 18, C.bar)
        Gfx.srect(math.floor(120 - wpx / 2), my, wpx, 1, C.barEdge)
        Gfx.ptext_center(120, my + 6, msgText, C.white, 1)
    end
    if st == "bag" then
        local k2 = I18n.k
        Gfx.srect(30, 56, 180, 104, C.bar)
        E.frame(30, 56, 180, 104, C.barEdge)
        Gfx.ptext_center(120, 62, k2.bag_title, C.cyan, 1)
        local names = { k2.it_web, k2.it_ice, k2.it_plane }
        local bt = tanks[cur]
        for idx = 1, 3 do
            local iy = 80 + (idx - 1) * 20
            if idx == bagIdx then
                Gfx.srect(36, iy - 3, 168, 14, C.dirt1)
                E.frame(36, iy - 3, 168, 14, C.yellow)
            end
            Gfx.itemIcon(idx, 40, iy)
            local col = bt.items[idx] > 0 and (idx == bagIdx and C.white or C.dim) or C.dirt3
            Gfx.ptext(54, iy, names[idx], col, 1)
            Gfx.ptext(186, iy, "x" .. bt.items[idx], idx == bagIdx and C.yellow or C.dim, 1)
        end
        Gfx.ptext_center(120, 146, k2.bag_hint, C.dim, 1)
    end
    if st == "planex" then
        local gy = tcol(planeX + 8)
        for yv = 20, gy - 6, 8 do Gfx.srect(planeX + 8, yv, 1, 4, C.yellow) end
        Gfx.srect(planeX + 5, gy - 5, 7, 2, C.yellow)
        local s = I18n.k.px_hint
        local wpx = Gfx.ptext_width(s, 1) + 12
        Gfx.srect(math.floor(120 - wpx / 2), 100, wpx, 14, C.bar)
        Gfx.ptext_center(120, 104, s, C.white, 1)
    end
    if st == "over" then
        Gfx.srect(28, 108, 184, 96, C.bar)
        E.frame(28, 108, 184, 96, C.barEdge)
        local win = tanks[1].hp > 0 and 1 or 2
        local wt = I18n.k.win_you
        if mode == 1 then wt = win == 1 and I18n.k.win_you or I18n.k.win_ai
        else wt = win == 1 and I18n.k.win_p1 or I18n.k.win_p2 end
        Gfx.ptext_center(122, 128, wt, tanks[win].c3, 2)
        Gfx.ptext_center(122, 130, wt, tanks[win].c1, 2)
        Gfx.ptext_center(120, 158, I18n.k.score_line .. "  " .. Save.w1 .. " : " .. Save.w2, C.white, 1)
        Gfx.ptext_center(120, 184, I18n.k.over_hint, C.dim, 1)
    end
end

-- ------------------------------------------------------------------ input
function M.keypressed(key)
    held[key] = true
    if st == "aim" then
        local tk = tanks[cur]
        if key == "ok" and not charging then
            charging, charge, chargeDir = true, 5, 1
        elseif key == "7" then
            charging = false
            st = "bag"
            bagIdx = 1
        elseif key == "3" then
            switchWeapon(tk)
        elseif key == "back" then M.onExit() end
    elseif st == "bag" then
        if key == "up" then bagIdx = bagIdx == 1 and 3 or bagIdx - 1
        elseif key == "down" then bagIdx = bagIdx == 3 and 1 or bagIdx + 1
        elseif key == "ok" then useItem(cur, bagIdx)
        elseif key == "back" then st = "aim" end
    elseif st == "planex" then
        if key == "ok" then confirmPlane()
        elseif key == "back" then st = "aim" end
    elseif st == "over" then
        if key == "ok" then M.start(mode)
        elseif key == "back" then M.onExit() end
    elseif key == "back" and (st == "intro" or st == "aim" or st == "msg" or st == "fall") then
        M.onExit()
    end
end

function M.keyreleased(key)
    held[key] = nil
    if key == "ok" and charging and st == "aim" then
        tanks[cur].power = math.floor(charge + 0.5)
        fire()
    end
end

return M
