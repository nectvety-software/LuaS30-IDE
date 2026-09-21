-- Game UI Starter for LuaS30 IDE / MediaTek MRE.
-- Flow: Splash -> Main Menu -> Game -> Pause/Game Over.
local E = engine

local UI = require("src.ui")
local Game = require("src.game")

local state = "splash"
local splash_frames = 0
local menu_index = 1
local settings_index = 1
local pause_index = 1

local settings = {
    sound = true,
    difficulty = 2,
}

local MENU_ITEMS = {
    "PLAY",
    "HOW TO PLAY",
    "SETTINGS",
    "ABOUT",
    "EXIT",
}

local KEYMAP = {
    ["2"] = "up",
    ["8"] = "down",
    ["4"] = "left",
    ["6"] = "right",
    ["5"] = "ok",
    ["#"] = "ok",
    ["0"] = "back",
    ["clear"] = "back",
    ["back"] = "back",
    ["enter"] = "ok",
    ["return"] = "ok",
    ["escape"] = "back",
}

local function clamp_index(value, count)
    if value < 1 then return count end
    if value > count then return 1 end
    return value
end

local function start_game()
    Game.start(settings.difficulty)
    state = "game"
end

local function open_menu()
    state = "menu"
    menu_index = 1
end

local function activate_menu()
    local item = MENU_ITEMS[menu_index]
    if item == "PLAY" then
        start_game()
    elseif item == "HOW TO PLAY" then
        state = "guide"
    elseif item == "SETTINGS" then
        state = "settings"
        settings_index = 1
    elseif item == "ABOUT" then
        state = "about"
    elseif item == "EXIT" then
        E.exit()
    end
end

function E.load()
    E.set_font(8)
    UI.set_settings(settings)
end

function E.update(dt)
    if state == "splash" then
        splash_frames = splash_frames + 1
        if splash_frames >= 24 then
            open_menu()
        end
        return
    end

    if state == "game" then
        Game.update(dt)
        if Game.is_over() then
            state = "gameover"
        end
    end
end

function E.draw()
    if state == "splash" then
        UI.splash(splash_frames)
    elseif state == "menu" then
        UI.main_menu(MENU_ITEMS, menu_index)
    elseif state == "guide" then
        UI.guide()
    elseif state == "settings" then
        UI.settings(settings_index, settings)
    elseif state == "about" then
        UI.about()
    elseif state == "game" then
        Game.draw()
    elseif state == "pause" then
        Game.draw()
        UI.pause(pause_index)
    elseif state == "gameover" then
        Game.draw()
        UI.game_over(Game.did_win(), Game.score())
    end

    if E.flush then E.flush() end
end

function E.keypressed(raw)
    local key = KEYMAP[raw] or raw

    if state == "splash" then
        open_menu()
        return
    end

    if state == "menu" then
        if key == "up" then
            menu_index = clamp_index(menu_index - 1, #MENU_ITEMS)
        elseif key == "down" then
            menu_index = clamp_index(menu_index + 1, #MENU_ITEMS)
        elseif key == "ok" then
            activate_menu()
        elseif key == "back" then
            E.exit()
        end
        return
    end

    if state == "guide" or state == "about" then
        if key == "back" or key == "ok" then open_menu() end
        return
    end

    if state == "settings" then
        if key == "up" then
            settings_index = clamp_index(settings_index - 1, 2)
        elseif key == "down" then
            settings_index = clamp_index(settings_index + 1, 2)
        elseif key == "left" or key == "right" or key == "ok" then
            if settings_index == 1 then
                settings.difficulty = settings.difficulty + (key == "left" and -1 or 1)
                if settings.difficulty < 1 then settings.difficulty = 3 end
                if settings.difficulty > 3 then settings.difficulty = 1 end
            else
                settings.sound = not settings.sound
            end
            UI.set_settings(settings)
        elseif key == "back" then
            open_menu()
        end
        return
    end

    if state == "game" then
        if key == "back" then
            pause_index = 1
            state = "pause"
        else
            Game.keypressed(key)
        end
        return
    end

    if state == "pause" then
        if key == "up" then
            pause_index = clamp_index(pause_index - 1, 3)
        elseif key == "down" then
            pause_index = clamp_index(pause_index + 1, 3)
        elseif key == "ok" then
            if pause_index == 1 then
                state = "game"
            elseif pause_index == 2 then
                start_game()
            else
                open_menu()
            end
        elseif key == "back" then
            state = "game"
        end
        return
    end

    if state == "gameover" then
        if key == "ok" then
            start_game()
        elseif key == "back" then
            open_menu()
        end
    end
end

function E.keyreleased(raw)
    local key = KEYMAP[raw] or raw
    if state == "game" then
        Game.keyreleased(key)
    end
end
