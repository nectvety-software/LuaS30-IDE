-- Ninja Runner: splash, main menu, language, guide, settings, about screens.
local E = engine
local Gfx = require("src.gfx")
local I18n = require("src.i18n")
local Save = require("src.save")
local C = Gfx.C

local M = {}
M.show = "splash"
M.go = function(name) end   -- replaced by main.lua

local t = 0
local cam = 0
local menuIdx = 1
local langIdx = 1
local setIdx = 1
local guidePage = 1
local flashMsg = ""
local flashT = 0

local MENU_N = 6

local function speedScroll()
    if M.show == "splash" then return 18 + t * 26 end
    return 14
end

-- centered hint line on a dark chip so it stays readable over the backdrop
local function footer(y, s, col)
    local wpx = Gfx.ptext_width(s, 1) + 10
    local fx = math.floor(120 - wpx / 2)
    if fx < 0 then
        fx = 0
        wpx = 240
    end
    E.rect(fx, y - 3, wpx, 13, C.bar)
    Gfx.ptext_center(120, y, s, col, 1)
end

function M.enter(name)
    M.show = name
    if name == "splash" then t = 0 end
    if name == "menu" then menuIdx = 1 end
    if name == "lang" then langIdx = Save.lang == "en" and 2 or 1 end
    if name == "guide" then guidePage = 1 end
    if name == "settings" then setIdx = 1 end
end

-- shared animated city backdrop
local function backdrop()
    Gfx.sky(t)
    Gfx.skyline(cam, 0.12, 150, C.far, nil, 31, 26, 40, 110)
    Gfx.skyline(cam, 0.3, 196, C.mid, true, 77, 34, 44, 74)
    E.rect(0, 196, 240, 124, C.black)
    Gfx.rooftop(-10, 262, 130)
    Gfx.rooftop(150, 250, 120)
    Gfx.rooftop(112, 274, 46)
end

function M.update(dt)
    t = t + dt
    cam = cam + dt * speedScroll()
    if flashT > 0 then flashT = flashT - dt end
    if M.show == "splash" and t > 3.4 then M.go("menu") end
end

function M.draw()
    E.clear(C.black)
    if M.show == "splash" then M.drawSplash()
    elseif M.show == "menu" then M.drawMenu()
    elseif M.show == "lang" then M.drawLang()
    elseif M.show == "guide" then M.drawGuide()
    elseif M.show == "about" then M.drawAbout()
    else M.drawSettings() end
end

-- ---------------------------------------------------------------- splash
function M.drawSplash()
    backdrop()
    Gfx.topBar("NINJA RUNNER", "SPLASH")
    local frame = ({ "run_a", "run_b", "run_c", "run_b" })[math.floor(t * 8) % 4 + 1]
    Gfx.drawScarf(52, 262 - 36 + 12, t * 6, 2, true)
    Gfx.drawSprite(frame, 46, 262 - 36, 2)

    local glow = math.floor(t * 2) % 2 == 0
    Gfx.ptext_center(122, 66, "NINJA RUNNER", C.pinkDk, 2)
    Gfx.ptext_center(120, 64, "NINJA RUNNER", glow and C.cyan or C.cyanHi, 2)
    Gfx.ptext_center(120, 88, "PARKOUR 2077", C.white, 1)

    if t > 1 and math.floor(t * 2) % 2 == 0 then
        Gfx.ptext_center(120, 300, I18n.k.press5, C.pink, 1)
    end
end

-- ------------------------------------------------------------------ menu
function M.menuItems()
    local k = I18n.k
    return { k.menu_play, k.menu_lang, k.menu_guide, k.menu_set, k.menu_about, k.menu_exit }
end

function M.drawMenu()
    backdrop()
    Gfx.topBar("MENU", "MENU")
    -- idle ninja on the right rooftop
    local bob = math.floor(math.sin(t * 3) + 0.5)
    Gfx.drawScarf(206, 214 + bob + 12, t * 3, 2, true)
    Gfx.drawSprite("run_b", 200, 214 + bob, 2)

    Gfx.ptext_center(122, 34, "NINJA RUNNER", C.pinkDk, 2)
    Gfx.ptext_center(120, 32, "NINJA RUNNER", C.cyan, 2)

    -- panel
    local px, py, pw, ph = 24, 70, 192, 172
    E.rect(px, py, pw, ph, C.bar)
    E.frame(px, py, pw, ph, C.violet)
    E.frame(px + 1, py + 1, pw - 2, ph - 2, C.violet)
    local items = M.menuItems()
    local cx = px + pw / 2
    for i = 1, MENU_N do
        local iy = py + 14 + (i - 1) * 26
        if i == menuIdx then
            E.rect(px + 6, iy - 4, pw - 12, 20, C.pinkDk)
            E.frame(px + 6, iy - 4, pw - 12, 20, C.pink)
            Gfx.ptext(px + 11, iy + 1, ">", C.cyanHi, 1)
            Gfx.ptext(px + pw - 16, iy + 1, "<", C.cyanHi, 1)
            Gfx.ptext_center(cx, iy + 2, items[i], C.white, 1)
        else
            Gfx.ptext_center(cx, iy + 2, items[i], C.dim, 1)
        end
    end
    footer(262, I18n.k.nav_hint_v, C.dim)
    footer(280, "V1.0  LUA S30 STUDIO", C.violet)
end

-- -------------------------------------------------------------- language
function M.drawLang()
    backdrop()
    Gfx.topBar(I18n.k.lang_title, "LANG")
    local px, py, pw, ph = 34, 90, 172, 96
    E.rect(px, py, pw, ph, C.bar)
    E.frame(px, py, pw, ph, C.violet)
    local names = { "TIENG VIET", "ENGLISH" }
    local cx = px + pw / 2
    for i = 1, 2 do
        local iy = py + 20 + (i - 1) * 34
        if i == langIdx then
            E.rect(px + 8, iy - 6, pw - 16, 24, C.pinkDk)
            E.frame(px + 8, iy - 6, pw - 16, 24, C.pink)
            Gfx.ptext(px + 13, iy, ">", C.cyanHi, 1)
        end
        local label = i == 1 and "TIẾNG VIỆT" or "ENGLISH"
        Gfx.ptext_center(cx + 6, iy, label, i == langIdx and C.white or C.dim, 1)
        if (i == 1 and Save.lang == "vi") or (i == 2 and Save.lang == "en") then
            Gfx.ptext(px + pw - 22, iy, "*", C.cyan, 1)
        end
    end
    footer(210, I18n.k.lang_hint, C.dim)
end

-- ----------------------------------------------------------------- guide
function M.drawGuide()
    backdrop()
    Gfx.topBar(I18n.k.guide_title, "GUIDE")
    local px, py, pw, ph = 12, 40, 216, 200
    E.rect(px, py, pw, ph, C.bar)
    E.frame(px, py, pw, ph, C.violet)
    local lines = I18n.k.guide[guidePage]
    local cx = px + pw / 2
    for i = 1, #lines do
        local col = i == 1 and C.cyan or C.white
        Gfx.ptext_center(cx, py + 18 + (i - 1) * 24, lines[i], col, 1)
    end
    Gfx.ptext_center(120, py + ph - 12, I18n.k.page .. " " .. guidePage .. "/2", C.dim, 1)
    footer(py + ph + 12, I18n.k.next5, C.dim)
end

-- -------------------------------------------------------------- settings
function M.drawSettings()
    backdrop()
    Gfx.topBar(I18n.k.set_title, "SET")
    local k = I18n.k
    local px, py, pw = 16, 60, 208
    local rows = {
        { k.set_sound, k.sound_on },
        { k.set_diff, k.diff[Save.diff] },
        { k.set_reset, "" },
    }
    rows[1][2] = Save.sound == 1 and k.on or k.off
    E.rect(px, py, pw, 118, C.bar)
    E.frame(px, py, pw, 118, C.violet)
    local cx = px + pw / 2
    for i = 1, 3 do
        local iy = py + 14 + (i - 1) * 34
        if i == setIdx then
            E.rect(px + 6, iy - 6, pw - 12, 30, C.pinkDk)
            E.frame(px + 6, iy - 6, pw - 12, 30, C.pink)
        end
        Gfx.ptext_center(cx, iy, rows[i][1], i == setIdx and C.white or C.dim, 1)
        if i < 3 then
            Gfx.ptext_center(cx, iy + 13, "< " .. rows[i][2] .. " >",
                              i == setIdx and C.cyan or C.violet, 1)
        end
    end
    footer(200, I18n.k.togg46, C.dim)
    footer(216, I18n.k.nav_hint_v, C.dim)
    if flashT > 0 then
        E.rect(40, 240, 160, 22, C.bar)
        E.frame(40, 240, 160, 22, C.cyan)
        Gfx.ptext_center(120, 247, flashMsg, C.cyanHi, 1)
    end
end

-- ----------------------------------------------------------------- about
function M.drawAbout()
    backdrop()
    Gfx.topBar(I18n.k.about_title, "ABOUT")
    local px, py, pw, ph = 12, 56, 216, 176
    E.rect(px, py, pw, ph, C.bar)
    E.frame(px, py, pw, ph, C.violet)

    Gfx.ptext_center(122, 74, "NINJA RUNNER", C.pinkDk, 2)
    Gfx.ptext_center(120, 72, "NINJA RUNNER", C.cyan, 2)

    local lines = I18n.k.about
    local iy = 98
    for i = 1, #lines do
        local s = lines[i]
        if s ~= "" then
            local col = C.white
            if s:sub(1, 1) == "©" or s:sub(1, 4) == "http" then col = C.cyan end
            Gfx.ptext_center(120, iy, s, col, 1)
            iy = iy + 14
        else
            iy = iy + 6
        end
    end
    footer(py + ph + 14, I18n.k.next5, C.dim)
end

-- ----------------------------------------------------------------- input
function M.keypressed(k)
    if M.show == "splash" then
        M.go("menu")
        return
    end
    if M.show == "menu" then
        if k == "up" then menuIdx = (menuIdx - 2) % MENU_N + 1
        elseif k == "down" then menuIdx = menuIdx % MENU_N + 1
        elseif k == "ok" then
            if menuIdx == 1 then M.go("play")
            elseif menuIdx == 2 then M.go("lang")
            elseif menuIdx == 3 then M.go("guide")
            elseif menuIdx == 4 then M.go("settings")
            elseif menuIdx == 5 then M.go("about")
            else E.exit() end
        elseif k == "back" then
            E.exit()
        end
        return
    end
    if M.show == "lang" then
        if k == "up" or k == "down" or k == "left" or k == "right" then
            langIdx = 3 - langIdx
        elseif k == "ok" then
            Save.lang = langIdx == 1 and "vi" or "en"
            I18n.apply(Save.lang)
            Save.save()
            M.go("menu")
        elseif k == "back" then M.go("menu") end
        return
    end
    if M.show == "guide" then
        if k == "ok" or k == "right" then
            if guidePage < 2 then guidePage = guidePage + 1 else M.go("menu") end
        elseif k == "left" then
            if guidePage > 1 then guidePage = guidePage - 1 end
        elseif k == "back" then M.go("menu") end
        return
    end
    if M.show == "about" then
        if k == "back" or k == "ok" then M.go("menu") end
        return
    end
    if M.show == "settings" then
        if k == "up" then setIdx = (setIdx - 2) % 3 + 1
        elseif k == "down" then setIdx = setIdx % 3 + 1
        elseif k == "left" or k == "right" then
            local d = k == "right" and 1 or -1
            if setIdx == 1 then
                Save.sound = Save.sound == 1 and 0 or 1
                if E.audio_set_volume then
                    E.audio_set_volume(Save.sound == 1 and 6 or 0)
                end
            elseif setIdx == 2 then
                Save.diff = (Save.diff - 1 + d) % 3 + 1
            end
        elseif k == "ok" then
            if setIdx == 3 then
                Save.best = 0
                flashMsg = I18n.k.reset_done
                flashT = 1.6
            end
            Save.save()
        elseif k == "back" then
            Save.save()
            M.go("menu")
        end
    end
end

return M
