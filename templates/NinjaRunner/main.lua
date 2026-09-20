-- Ninja Runner: neon rooftop parkour cho may dial-key (LuaS30 / MTK MRE).
-- Man hinh: splash -> menu -> (play | lang | guide | settings | about) -> over.
local E = engine

local Gfx = require("src.gfx")
local I18n = require("src.i18n")
local Save = require("src.save")
local UI = require("src.ui")
local Game = require("src.game")

local screen = "splash"

local KEYMAP = {
    ["2"] = "up", ["8"] = "down", ["4"] = "left", ["6"] = "right",
    ["5"] = "ok", ["#"] = "ok",
    ["0"] = "back", ["clear"] = "back", ["back"] = "back",
    ["softleft"] = "left", ["softright"] = "right",
}

local function go(name)
    if name == "play" then
        screen = "play"
        Game.start()
    else
        screen = "ui"
        UI.enter(name)
    end
end

function E.load()
    Save.load()
    I18n.apply(Save.lang)
    if E.audio_set_volume then E.audio_set_volume(Save.sound == 1 and 6 or 0) end
    UI.go = go
    Game.onExit = function() go("menu") end
    E.set_font(8)
    go("splash")
end

function E.update(dt)
    if screen == "play" then Game.update(dt) else UI.update(dt) end
end

function E.draw()
    if screen == "play" then Game.draw() else UI.draw() end
    E.flush()
end

function E.keypressed(k)
    local key = KEYMAP[k] or k
    if screen == "play" then Game.keypressed(key) else UI.keypressed(key) end
end

function E.keyreleased(k)
    local key = KEYMAP[k] or k
    if screen == "play" then Game.keyreleased(key) end
end
