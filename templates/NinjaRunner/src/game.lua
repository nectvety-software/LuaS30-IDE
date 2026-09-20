-- Ninja Runner: auto-run parkour qua mai nha.
local E = engine
local Gfx = require("src.gfx")
local I18n = require("src.i18n")
local Save = require("src.save")
local C = Gfx.C

local M = {}

local PX = 54            -- player screen x
local PH, PW = 36, 16    -- sprite 14x18 @2, hitbox
local GRAV = 980
local JUMPV = 360
local RUN_FRAMES = { "run_a", "run_b", "run_c", "run_b" }

local w = {}             -- world state (single table, no per-frame allocs)

function M.start()
    w.cam = 0
    w.t = 0
    w.py = 230           -- feet y
    w.vy = 0
    w.grounded = true
    w.coyote = 0
    w.fast = false
    w.frame = 1
    w.animT = 0
    w.plats = { { x = -60, w = 320, top = 230, id = 0 } }
    w.seed = math.floor(E.tick_ms()) % 9999 + 1
    w.rnd = w.seed
    w.dist = 0
    w.score = 0
    w.dead = nil
    w.deadT = 0
    w.newBest = false
    w.parts = {}
    for i = 1, 20 do w.parts[i] = { on = false, x = 0, y = 0, vx = 0, vy = 0, life = 0 } end
    w.genUntil = 260
    w.platId = 1
    -- adaptive director state (Jev-style snapshot -> terrain decisions)
    w.dir = 0.15         -- smoothed difficulty in [0,1]
    w.streak = 0         -- consecutive safe landings
    w.spd = 60
    M.genAhead()
end

local function rnd()
    w.rnd = (w.rnd * 1103515 + 12345) % 2147483648
    return w.rnd / 2147483648
end

function M.speed()
    local base = ({ 60, 72, 88 })[Save.diff] or 72
    return base + math.min(46, w.dist * 0.012)
end

-- Read a snapshot of the live game state (streak, speed) and smooth a
-- difficulty value 0..1 toward it; terrain shape is derived from that value.
local function director()
    local target = 0.12 + math.min(0.55, w.streak * 0.035)
                         + math.min(0.30, (M.speed() - 60) * 0.004)
    if target > 1 then target = 1 end
    w.dir = w.dir + (target - w.dir) * 0.18
end

function M.genAhead()
    local last = w.plats[#w.plats]
    while last.x + last.w < w.cam + 480 do
        director()
        local d = w.dir
        local dmul = ({ 0.8, 1, 1.2 })[Save.diff] or 1
        local spd = M.speed()
        -- airtime of a full jump ~ 2*JUMPV/GRAV = 0.73s; keep gaps jumpable
        local gap = (12 + 26 * d + rnd() * (10 + 14 * d)) * dmul
        local gapCap = spd * 0.73 * 0.62
        if gap > gapCap then gap = gapCap end

        local pw = 55 + rnd() * math.max(30, 95 - 65 * d)

        local top = last.top
        local up = 16 + 30 * d
        local down = 44 + 46 * d
        local step = (rnd() - 0.5) * (70 + 90 * d)
        if step < -up then step = -up elseif step > down then step = down end
        top = top + step
        if top < 150 then top = 150 elseif top > 262 then top = 262 end
        -- climbing costs airtime: shrink the gap we can clear
        if step < 0 then gap = gap * math.max(0.45, 1 + step / 90) end

        last = { x = last.x + last.w + gap, w = pw, top = top, id = w.platId }
        w.platId = w.platId + 1
        table.insert(w.plats, last)
    end
    while #w.plats > 1 and w.plats[2].x + w.plats[2].w < w.cam - 40 do
        table.remove(w.plats, 1)
    end
end

local function puff(x, y, n, spread)
    local placed = 0
    for i = 1, 20 do
        local p = w.parts[i]
        if not p.on then
            p.on = true
            p.x = x
            p.y = y
            p.vx = (rnd() - 0.5) * spread
            p.vy = -rnd() * 40
            p.life = 0.35 + rnd() * 0.25
            placed = placed + 1
            if placed >= n then return end
        end
    end
end

function M.update(dt)
    w.t = w.t + dt
    -- particles always animate
    for i = 1, 20 do
        local p = w.parts[i]
        if p.on then
            p.life = p.life - dt
            p.x = p.x + p.vx * dt
            p.y = p.y + p.vy * dt
            p.vy = p.vy + 160 * dt
            if p.life <= 0 then p.on = false end
        end
    end

    if w.dead then
        w.deadT = w.deadT + dt
        return
    end

    local spd = M.speed()
    w.spd = spd
    local prevX = w.cam + PX
    local prevFeet = w.py
    w.cam = w.cam + spd * dt
    w.dist = w.cam
    w.score = math.floor(w.dist / 10)

    -- vertical physics
    w.vy = w.vy + GRAV * dt
    if w.fast and not w.grounded then w.vy = w.vy + GRAV * 0.9 * dt end
    if w.vy > 620 then w.vy = 620 end
    w.py = w.py + w.vy * dt

    local feetX = w.cam + PX
    local wasGrounded = w.grounded
    w.grounded = false
    for i = 1, #w.plats do
        local p = w.plats[i]
        -- landed on top?
        if w.vy >= 0 and feetX + PW / 2 > p.x and feetX - PW / 2 < p.x + p.w then
            if prevFeet <= p.top + 2 and w.py >= p.top then
                w.py = p.top
                w.vy = 0
                w.grounded = true
                w.coyote = 0.09
                -- director feedback: streak grows, edge-landing = near miss
                if not wasGrounded then
                    w.streak = w.streak + 1
                    if feetX - p.x < 12 then w.dir = math.max(0, w.dir - 0.18) end
                end
            end
        end
        -- crashed into wall?
        if not w.grounded and feetX + PW / 2 >= p.x and prevX + PW / 2 < p.x + 2
           and p.top < w.py - 6 and w.py - PH < p.top + 40 and w.py > p.top then
            M.die("wall")
            return
        end
    end
    if not w.grounded then
        if w.coyote > 0 then w.coyote = w.coyote - dt end
    else
        w.coyote = 0.09
        if not wasGrounded then
            puff(feetX - w.cam, w.py, 6, 90)
        end
    end

    if w.py > 340 then M.die("fall") return end

    -- run animation + dust
    w.animT = w.animT + dt * (w.grounded and spd * 0.12 or 4)
    if w.animT > 1 then
        w.animT = 0
        w.frame = w.frame % 4 + 1
        if w.grounded and rnd() > 0.55 then puff(feetX - w.cam - 6, w.py, 1, 40) end
    end

    M.genAhead()
end

function M.die(cause)
    w.dead = cause
    w.deadT = 0
    w.vy = 0
    if w.score > Save.best then
        Save.best = w.score
        w.newBest = true
    end
    Save.save()
end

function M.jump()
    if w.grounded or w.coyote > 0 then
        w.vy = -JUMPV
        w.grounded = false
        w.coyote = 0
        puff(w.cam + PX - w.cam, w.py, 4, 70)
    end
end

-- ------------------------------------------------------------------ input
function M.keypressed(k)
    if w.dead then
        if w.deadT > 0.5 then
            if k == "ok" then M.start()
            elseif k == "back" then M.onExit() end
        end
        return
    end
    if k == "up" or k == "ok" then M.jump()
    elseif k == "down" then w.fast = true end
end

function M.keyreleased(k)
    if k == "down" then w.fast = false end
end

-- ------------------------------------------------------------------- draw
function M.draw()
    E.clear(C.black)
    Gfx.sky(w.t)
    Gfx.skyline(w.cam, 0.12, 150, C.far, nil, 31, 26, 40, 110)
    Gfx.skyline(w.cam, 0.3, 196, C.mid, true, 77, 34, 44, 74, w.t)
    -- dark ground behind platforms, from mid-skyline base down
    E.rect(0, 196, 240, 124, C.black)

    -- speed streaks once the run picks up
    if not w.dead and w.spd > 88 then
        local n = w.spd > 110 and 7 or 4
        for i = 1, n do
            local sy = 190 + math.floor(Gfx.hash(i * 71 + 5) * 110)
            local len = 12 + math.floor(Gfx.hash(i * 17) * 22)
            local sx = 300 - ((w.cam * (1.25 + Gfx.hash(i * 9) * 0.6) + i * 97) % 340)
            Gfx.srect(math.floor(sx), sy, len, 1, i % 2 == 0 and C.violet or C.edgeGlow)
        end
    end

    Gfx.topBar("NINJA RUNNER", "RUN")

    for i = 1, #w.plats do
        local p = w.plats[i]
        local sx = math.floor(p.x - w.cam)
        if sx < 240 and sx + p.w > -4 then
            Gfx.rooftop(sx, p.top, math.floor(p.w))
            Gfx.rooftopProps(sx, p.top, math.floor(p.w), p.id, w.t)
        end
    end

    -- particles
    for i = 1, 20 do
        local p = w.parts[i]
        if p.on then
            Gfx.srect(math.floor(p.x), math.floor(p.y), 2, 2,
                      p.life > 0.3 and C.dim or C.violet)
        end
    end

    -- ninja
    local name
    if w.dead then name = "hurt"
    elseif not w.grounded then name = w.vy < 0 and "jump" or "fall"
    else name = RUN_FRAMES[w.frame] end
    local ny = math.floor(w.py) - Gfx.SPRH * 2
    Gfx.drawScarf(PX - 8, ny + 12, w.t * 6, 2, not w.dead)
    Gfx.drawSprite(name, PX - 14, ny, 2)

    -- HUD
    local hs = I18n.k.score .. ": " .. w.score
    Gfx.ptext(4, 17, hs, C.white, 1)
    local hb = I18n.k.best .. ": " .. Save.best
    Gfx.ptext(236 - Gfx.ptext_width(hb, 1), 17, hb, C.pink, 1)

    if w.dead and w.deadT > 0.5 then M.drawOver() end
end

function M.drawOver()
    E.rect(0, 96, 240, 2, C.pink)
    E.rect(0, 98, 240, 116, C.bar)
    E.rect(0, 214, 240, 2, C.cyan)
    Gfx.ptext_center(122, 112, I18n.k.over, C.pinkDk, 2)
    Gfx.ptext_center(120, 110, I18n.k.over, C.pink, 2)
    Gfx.ptext_center(120, 136, tostring(w.score), C.white, 2)
    if w.newBest then
        Gfx.ptext_center(120, 160, I18n.k.newbest, C.cyan, 1)
    else
        Gfx.ptext_center(120, 160, I18n.k.best .. ": " .. Save.best, C.dim, 1)
    end
    Gfx.ptext_center(120, 188, I18n.k.over_hint, C.white, 1)
end

return M
