-- LuaS30 IDE — khung khoi dong toi gian (Blank Project).
--
-- Hop dong phim theo doc/ai/Keypad.md: runtime chi gui ten phim chu thuong
--   up down left right ok softleft softright clear back 0-9 * #
-- Nhan nut vat ly trong tai lieu KHONG phai ten phim Lua.
-- Can ban day du hon (menu, nhap so, ve ban phim) thi xem template
-- "Keypad Demo" trong cung thu muc templates/.

local E = engine

local W, H = E.W or 240, E.H or 320

local x, y = 105, 140
local speed = 4

local bg     = E.color(35, 83, 47)
local white  = E.color(255, 255, 255)
local yellow = E.color(255, 210, 70)

-- Trang thai phim: true o keypressed, false o keyreleased.
local keys = {}
local last_key = "-"
local show_help = true

-- Alias so du phong D-Pad/OK: 2/8/4/6/5 (Keypad.md muc 2.3).
local function down(...)
    for i = 1, select("#", ...) do
        if keys[select(i, ...)] then return true end
    end
    return false
end

local function input_up()    return down("up", "2") end
local function input_down()  return down("down", "8") end
local function input_left()  return down("left", "4") end
local function input_right() return down("right", "6") end
local function input_ok()    return down("ok", "5") end

function E.load()
    E.set_font(8)
end

function E.update(dt)
    if input_left()  then x = x - speed end
    if input_right() then x = x + speed end
    if input_up()    then y = y - speed end
    if input_down()  then y = y + speed end
    if x < 0 then x = 0 elseif x > W - 16 then x = W - 16 end
    if y < 20 then y = 20 elseif y > H - 48 then y = H - 48 end
end

function E.draw()
    E.clear(bg)
    E.text(4, 4, "LuaS30 IDE", white)
    E.rect(x, y, 16, 16, yellow)
    E.text(4, H - 40, "key: " .. last_key, white)
    if show_help then
        E.text(4, H - 28, "2/4/6/8 move   5 ok", white)
        E.text(4, H - 16, "softL help     0 exit", white)
    end
end

function E.keypressed(k)
    k = tostring(k):lower()
    last_key = k
    keys[k] = true
    if k == "ok" or k == "5" then
        x, y = 105, 140
    elseif k == "softleft" then
        show_help = not show_help
    elseif k == "softright" or k == "back" or k == "0" then
        E.exit()
    end
end

function E.keyreleased(k)
    keys[tostring(k):lower()] = false
end

function E.pause()
    for name in pairs(keys) do keys[name] = false end
end

function E.resume()
    for name in pairs(keys) do keys[name] = false end
end
