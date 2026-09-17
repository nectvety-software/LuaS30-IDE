-- LuaS30 IDE standalone example.
local E = engine

local x, y = 105, 140
local speed = 4
local bg = E.color(35, 83, 47)
local white = E.color(255, 255, 255)
local yellow = E.color(255, 210, 70)
local keys = {}

function E.load()
    E.set_font(8)
end

function E.update(dt)
    if keys.left  then x = x - speed end
    if keys.right then x = x + speed end
    if keys.up    then y = y - speed end
    if keys.down  then y = y + speed end
    if x < 0 then x = 0 elseif x > 224 then x = 224 end
    if y < 20 then y = 20 elseif y > 304 then y = 304 end
end

function E.draw()
    E.clear(bg)
    E.text(4, 4, "LuaS30 IDE 1.6.1", white)
    E.rect(x, y, 16, 16, yellow)
    E.text(4, 306, "2/4/6/8 move  0 exit", white)
end

function E.keypressed(k)
    if k == "4" or k == "left"  then keys.left = true end
    if k == "6" or k == "right" then keys.right = true end
    if k == "2" or k == "up"    then keys.up = true end
    if k == "8" or k == "down"  then keys.down = true end
    if k == "0" then E.exit() end
end

function E.keyreleased(k)
    if k == "4" or k == "left"  then keys.left = false end
    if k == "6" or k == "right" then keys.right = false end
    if k == "2" or k == "up"    then keys.up = false end
    if k == "8" or k == "down"  then keys.down = false end
end
