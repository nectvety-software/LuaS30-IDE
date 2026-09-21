local E = engine
local T = require("src.theme")

local M = {}
local current_settings = { sound = true, difficulty = 2 }

local function screen()
    return E.W or 240, E.H or 320
end

local function fill(x, y, w, h, color)
    E.rect(math.floor(x), math.floor(y), math.floor(w), math.floor(h), color)
end

local function outline(x, y, w, h, color)
    fill(x, y, w, 1, color)
    fill(x, y + h - 1, w, 1, color)
    fill(x, y, 1, h, color)
    fill(x + w - 1, y, 1, h, color)
end

local function approx_text_width(text)
    return #tostring(text) * 6
end

local function center_text(y, text, color)
    local w = screen()
    local x = math.floor((w - approx_text_width(text)) / 2)
    if x < 2 then x = 2 end
    E.text(x, y, text, color or T.text)
end

local function top_bar(title, chip)
    local w = screen()
    fill(0, 0, w, 31, T.bg2)
    fill(0, 30, w, 1, T.border)
    E.text(8, 10, title, T.text)
    if chip and chip ~= "" then
        local cw = approx_text_width(chip) + 10
        fill(w - cw - 7, 7, cw, 16, T.panel2)
        outline(w - cw - 7, 7, cw, 16, T.border)
        E.text(w - cw - 2, 11, chip, T.accent2)
    end
end

local function softkeys(left, right)
    local w, h = screen()
    fill(0, h - 22, w, 22, T.bg2)
    fill(0, h - 22, w, 1, T.border)
    E.text(7, h - 15, left or "", T.muted)
    local rt = right or ""
    E.text(w - approx_text_width(rt) - 7, h - 15, rt, T.muted)
end

local function panel(x, y, w, h, title)
    fill(x + 2, y + 2, w, h, T.black)
    fill(x, y, w, h, T.panel)
    outline(x, y, w, h, T.border)
    if title then
        E.text(x + 8, y + 7, title, T.accent2)
        fill(x + 7, y + 20, w - 14, 1, T.border)
    end
end

local function button(x, y, w, h, text, active)
    local bg = active and T.accent or T.panel2
    local fg = active and T.black or T.text
    fill(x + 2, y + 2, w, h, T.black)
    fill(x, y, w, h, bg)
    outline(x, y, w, h, active and T.accent2 or T.border)
    local tx = x + math.floor((w - approx_text_width(text)) / 2)
    E.text(tx, y + math.floor(h / 2) - 4, text, fg)
end

local function progress(x, y, w, value, max_value, color)
    local ratio = 0
    if max_value > 0 then ratio = value / max_value end
    if ratio < 0 then ratio = 0 end
    if ratio > 1 then ratio = 1 end
    fill(x, y, w, 7, T.bg)
    outline(x, y, w, 7, T.border)
    fill(x + 1, y + 1, math.floor((w - 2) * ratio), 5, color)
end

function M.set_settings(settings)
    current_settings = settings or current_settings
end

function M.splash(frame)
    local w, h = screen()
    E.clear(T.bg)

    -- Procedural logo: no external asset required.
    local cx = math.floor(w / 2)
    local cy = math.floor(h / 2) - 36
    fill(cx - 32, cy - 22, 64, 44, T.panel)
    outline(cx - 32, cy - 22, 64, 44, T.border)
    fill(cx - 22, cy - 12, 12, 12, T.accent)
    fill(cx - 5, cy - 12, 12, 12, T.cyan)
    fill(cx + 12, cy - 12, 12, 12, T.green)
    fill(cx - 22, cy + 5, 46, 5, T.accent2)

    center_text(cy + 34, "LUA S30", T.text)
    center_text(cy + 49, "GAME UI STARTER", T.accent2)

    local dots = (math.floor(frame / 4) % 3) + 1
    center_text(h - 60, "Loading" .. string.rep(".", dots), T.muted)
    softkeys("", "SKIP")
end

function M.main_menu(items, selected)
    local w, h = screen()
    E.clear(T.bg)
    top_bar("POCKET QUEST", "STARTER")

    center_text(44, "READY FOR YOUR GAME", T.muted)

    local button_w = math.min(w - 34, 206)
    local x = math.floor((w - button_w) / 2)
    local y = 67
    local button_h = 31
    local gap = 7

    for i, label in ipairs(items) do
        button(x, y + (i - 1) * (button_h + gap), button_w, button_h, label, i == selected)
    end

    local footer_y = h - 52
    E.text(10, footer_y, "2/8 Navigate", T.muted)
    E.text(w - 92, footer_y, "5 Select", T.muted)
    softkeys("0 EXIT", "5 SELECT")
end

function M.guide()
    local w, h = screen()
    E.clear(T.bg)
    top_bar("HOW TO PLAY", "GUIDE")
    panel(12, 45, w - 24, h - 92, "CONTROLS")

    E.text(24, 78, "2 / UP     Move up", T.text)
    E.text(24, 99, "8 / DOWN   Move down", T.text)
    E.text(24, 120, "4 / LEFT   Move left", T.text)
    E.text(24, 141, "6 / RIGHT  Move right", T.text)
    E.text(24, 170, "Collect orange gems.", T.accent2)
    E.text(24, 190, "Avoid the red drone.", T.red)
    E.text(24, 210, "Fill the goal counter", T.muted)
    E.text(24, 225, "to win the demo.", T.muted)

    softkeys("0 BACK", "5 BACK")
end

function M.settings(selected, settings)
    local w, h = screen()
    E.clear(T.bg)
    top_bar("SETTINGS", "GAME")
    panel(12, 47, w - 24, 168, "OPTIONS")

    local names = { "DIFFICULTY", "SOUND" }
    local values = {
        ({ "EASY", "NORMAL", "HARD" })[settings.difficulty or 2],
        settings.sound and "ON" or "OFF",
    }

    for i = 1, 2 do
        local y = 84 + (i - 1) * 56
        local active = i == selected
        fill(22, y, w - 44, 39, active and T.panel2 or T.bg2)
        outline(22, y, w - 44, 39, active and T.accent or T.border)
        E.text(31, y + 8, names[i], active and T.accent2 or T.muted)
        local value = values[i]
        E.text(w - approx_text_width(value) - 32, y + 22, value, T.text)
    end

    E.text(22, 230, "4/6 or 5 changes value", T.muted)
    softkeys("0 BACK", "5 CHANGE")
end

function M.about()
    local w, h = screen()
    E.clear(T.bg)
    top_bar("ABOUT", "1.0")
    panel(12, 48, w - 24, 187, "GAME UI STARTER")

    center_text(83, "LuaS30 IDE", T.accent2)
    center_text(104, "MRE / S30+ template", T.text)
    center_text(129, "Splash + Menu + HUD", T.muted)
    center_text(145, "Pause + Settings + Game Over", T.muted)

    fill(28, 178, w - 56, 1, T.border)
    center_text(192, "Replace colors, text and", T.text)
    center_text(207, "game logic with your own.", T.text)

    softkeys("0 BACK", "5 BACK")
end

function M.hud(score, hp, max_hp, collected, goal)
    local w = screen()
    fill(0, 0, w, 38, T.bg2)
    fill(0, 37, w, 1, T.border)

    E.text(7, 7, "HP", T.muted)
    progress(25, 8, 67, hp, max_hp, hp > 1 and T.green or T.red)

    E.text(105, 7, "SCORE", T.muted)
    E.text(105, 20, tostring(score), T.text)

    local goal_text = tostring(collected) .. "/" .. tostring(goal)
    E.text(w - approx_text_width(goal_text) - 8, 20, goal_text, T.accent2)
end

function M.pause(selected)
    local w, h = screen()
    local pw, ph = math.min(w - 50, 190), 158
    local x, y = math.floor((w - pw) / 2), math.floor((h - ph) / 2)
    panel(x, y, pw, ph, "PAUSED")

    local items = { "RESUME", "RESTART", "MAIN MENU" }
    for i, label in ipairs(items) do
        button(x + 18, y + 34 + (i - 1) * 34, pw - 36, 27, label, i == selected)
    end
end

function M.game_over(won, score)
    local w, h = screen()
    local pw, ph = math.min(w - 40, 202), 154
    local x, y = math.floor((w - pw) / 2), math.floor((h - ph) / 2)
    panel(x, y, pw, ph, won and "MISSION COMPLETE" or "GAME OVER")

    center_text(y + 43, won and "NICE RUN!" or "TRY AGAIN", won and T.green or T.red)
    center_text(y + 67, "SCORE  " .. tostring(score), T.text)
    center_text(y + 98, "5 RESTART", T.accent2)
    center_text(y + 116, "0 MAIN MENU", T.muted)
end

return M
