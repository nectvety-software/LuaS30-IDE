local E = engine
local T = require("src.theme")
local UI = require("src.ui")

local M = {}

local keys = {}
local player = { x = 28, y = 170, w = 12, h = 12 }
local enemy = { x = 60, y = 235, w = 20, h = 9, dir = 1 }
local gem_index = 1
local score_value = 0
local collected = 0
local goal = 5
local hp = 3
local max_hp = 3
local invulnerable = 0
local finished = false
local won = false
local difficulty = 2

local gem_positions = {
    { 52, 86 },
    { 178, 92 },
    { 112, 135 },
    { 38, 246 },
    { 184, 256 },
    { 120, 206 },
}

local function screen()
    return E.W or 240, E.H or 320
end

local function hit(a, b)
    return a.x < b.x + b.w
       and a.x + a.w > b.x
       and a.y < b.y + b.h
       and a.y + a.h > b.y
end

local function current_gem()
    local p = gem_positions[gem_index]
    return { x = p[1], y = p[2], w = 10, h = 10 }
end

function M.start(level)
    difficulty = tonumber(level) or 2
    keys = {}
    player.x, player.y = 28, 170
    enemy.x, enemy.y, enemy.dir = 60, 235, 1
    gem_index = 1
    score_value = 0
    collected = 0
    hp = difficulty == 3 and 2 or 3
    max_hp = hp
    invulnerable = 0
    finished = false
    won = false
end

function M.update(dt)
    if finished then return end

    local w, h = screen()
    local speed = difficulty == 1 and 3 or 4
    if keys.left then player.x = player.x - speed end
    if keys.right then player.x = player.x + speed end
    if keys.up then player.y = player.y - speed end
    if keys.down then player.y = player.y + speed end

    if player.x < 7 then player.x = 7 end
    if player.x > w - player.w - 7 then player.x = w - player.w - 7 end
    if player.y < 48 then player.y = 48 end
    if player.y > h - player.h - 29 then player.y = h - player.h - 29 end

    local enemy_speed = difficulty + 1
    enemy.x = enemy.x + enemy.dir * enemy_speed
    if enemy.x < 10 then
        enemy.x = 10
        enemy.dir = 1
    elseif enemy.x > w - enemy.w - 10 then
        enemy.x = w - enemy.w - 10
        enemy.dir = -1
    end

    if invulnerable > 0 then invulnerable = invulnerable - 1 end

    local gem = current_gem()
    if hit(player, gem) then
        collected = collected + 1
        score_value = score_value + 100
        gem_index = (gem_index % #gem_positions) + 1
        if collected >= goal then
            finished = true
            won = true
        end
    end

    if invulnerable == 0 and hit(player, enemy) then
        hp = hp - 1
        invulnerable = 18
        player.x = 28
        player.y = 170
        if hp <= 0 then
            hp = 0
            finished = true
            won = false
        end
    end
end

function M.draw()
    local w, h = screen()
    E.clear(T.bg)
    UI.hud(score_value, hp, max_hp, collected, goal)

    -- Arena.
    E.rect(7, 47, w - 14, h - 76, T.bg2)
    E.rect(7, 47, w - 14, 1, T.border)
    E.rect(7, h - 30, w - 14, 1, T.border)

    -- Minimal grid gives the project a graphical game feel without assets.
    local y = 66
    while y < h - 31 do
        E.rect(8, y, w - 16, 1, T.panel)
        y = y + 28
    end
    local x = 32
    while x < w - 8 do
        E.rect(x, 48, 1, h - 78, T.panel)
        x = x + 32
    end

    local gem = current_gem()
    E.rect(gem.x - 2, gem.y + 3, gem.w + 4, 4, T.accent2)
    E.rect(gem.x + 1, gem.y, gem.w - 2, gem.h, T.accent)

    E.rect(enemy.x, enemy.y, enemy.w, enemy.h, T.red)
    E.rect(enemy.x + 4, enemy.y - 3, enemy.w - 8, 3, T.accent2)

    local player_color = (invulnerable > 0 and invulnerable % 4 < 2) and T.white or T.cyan
    E.rect(player.x, player.y, player.w, player.h, player_color)
    E.rect(player.x + 3, player.y + 3, 2, 2, T.bg)

    E.rect(0, h - 22, w, 22, T.bg2)
    E.text(7, h - 15, "0 PAUSE", T.muted)
    E.text(w - 78, h - 15, "2/4/6/8", T.muted)
end

function M.keypressed(key)
    if key == "left" or key == "right" or key == "up" or key == "down" then
        keys[key] = true
    end
end

function M.keyreleased(key)
    if key == "left" or key == "right" or key == "up" or key == "down" then
        keys[key] = false
    end
end

function M.is_over()
    return finished
end

function M.did_win()
    return won
end

function M.score()
    return score_value
end

return M
