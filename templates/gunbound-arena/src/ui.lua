-- Gunbound Arena: splash, menu, ngon ngu, huong dan, cai dat, gioi thieu.
local E = engine
local Gfx = require("src.gfx")
local I18n = require("src.i18n")
local Save = require("src.save")
local C = Gfx.C
local SH = require("src.screen").H

local M = {}
M.show = "splash"
M.go = function(name) end   -- replaced by main.lua

local t = 0
local menuIdx = 1
local langIdx = 1
local setIdx = 1
local guidePage = 1
local diffIdx = 2

local MENU_N = 7

-- fake heightmap for the menu/splash backdrop
local demoTerr = {}
local function demoTerrain()
    for x = 1, 240 do
        demoTerr[x] = math.floor(SH - 68 + math.sin(x * 0.05) * 10 + math.sin(x * 0.013 + 1) * 14)
    end
end
demoTerrain()

local function footer(y, s, col)
    local wpx = Gfx.ptext_width(s, 1) + 10
    local fx = math.floor(120 - wpx / 2)
    if fx < 0 then fx = 0 wpx = 240 end
    Gfx.srect(fx, y - 3, wpx, 13, C.bar)
    Gfx.ptext_center(120, y, s, col, 1)
end

function M.enter(name)
    M.show = name
    if name == "splash" then t = 0 end
    if name == "menu" then menuIdx = 1 end
    if name == "lang" then langIdx = Save.lang == "en" and 2 or 1 end
    if name == "diffsel" then diffIdx = Save.diff end
    if name == "guide" then guidePage = 1 end
    if name == "settings" then setIdx = 1 end
end

local drawTerrain = Gfx.newTerrain()
local drawDunes = Gfx.newDunes()

local function backdrop()
    Gfx.sky(t, 1)
    drawDunes(demoTerr, 1)
    drawTerrain(demoTerr, 1, SH)
    Gfx.srect(0, SH - 8, 240, 8, C.dirt3)
    Gfx.cactus(118, demoTerr[118])
end

function M.update(dt)
    t = t + dt
    if M.show == "splash" and t > 3.4 then M.go("menu") end
end

function M.draw()
    E.clear(C.skyTop)
    if M.show == "splash" then M.drawSplash()
    elseif M.show == "menu" then M.drawMenu()
    elseif M.show == "lang" then M.drawLang()
    elseif M.show == "diffsel" then M.drawDiffSel()
    elseif M.show == "guide" then M.drawGuide()
    elseif M.show == "about" then M.drawAbout()
    else M.drawSettings() end
end

-- --------------------------------------------------------------- splash
function M.drawSplash()
    backdrop()
    Gfx.topBar(nil, "SPLASH")
    -- two tanks trading shots across the title
    local gy = demoTerr[30] - 10
    Gfx.tank(1, C.blue1, C.blue2, C.blue3, 22, gy)
    Gfx.barrel(30, gy + 3, 55)
    local gy2 = demoTerr[214] - 10
    Gfx.tank(-1, C.red1, C.red2, C.red3, 206, gy2)
    Gfx.barrel(214, gy2 + 3, 125)
    local u = (t * 0.7) % 1
    local sx, sy = 30 + u * 184, gy - 4 - math.sin(u * math.pi) * 60
    Gfx.srect(math.floor(sx) - 1, math.floor(sy) - 1, 3, 3, C.shell)

    local glow = math.floor(t * 2) % 2 == 0
    Gfx.ptext_center(122, 66, "GUNBOUND", C.dirt3, 2)
    Gfx.ptext_center(120, 64, "GUNBOUND", glow and C.yellow or C.orange, 2)
    Gfx.ptext_center(120, 88, "A R E N A", C.white, 1)
    Gfx.ptext_center(120, 104, "ARTILLERY  DUEL", C.dim, 1)

    if t > 1 and math.floor(t * 2) % 2 == 0 then
        Gfx.ptext_center(120, 200, I18n.k.press5, C.cyan, 1)
    end
    footer(SH - 20, "V1.0  LUA S30 STUDIO", C.barEdge)
end

-- ------------------------------------------------------------------ menu
function M.menuItems()
    local k = I18n.k
    return { k.menu_play1, k.menu_play2, k.menu_lang, k.menu_guide,
             k.menu_set, k.menu_about, k.menu_exit }
end

function M.drawMenu()
    backdrop()
    Gfx.topBar(nil, "MENU")
    local gy = demoTerr[204] - 10
    local bob = math.floor(math.sin(t * 2) * 0.9 + 0.5)
    Gfx.tank(-1, C.red1, C.red2, C.red3, 196, gy + bob)
    Gfx.barrel(204, gy + 3 + bob, 140 - math.sin(t) * 18)

    Gfx.ptext_center(122, 30, "GUNBOUND ARENA", C.dirt3, 2)
    Gfx.ptext_center(120, 28, "GUNBOUND ARENA", C.yellow, 2)

    local px, py, pw, ph = 16, 50, 208, SH - 76
    Gfx.srect(px, py, pw, ph, C.bar)
    E.frame(px, py, pw, ph, C.barEdge)
    local items = M.menuItems()
    local cx = px + pw / 2
    for i = 1, MENU_N do
        local iy = py + 12 + (i - 1) * 24
        if i == menuIdx then
            Gfx.srect(px + 6, iy - 4, pw - 12, 22, C.dirt1)
            E.frame(px + 6, iy - 4, pw - 12, 22, C.yellow)
            Gfx.ptext(px + 11, iy + 2, ">", C.yellow, 1)
            Gfx.ptext_center(cx, iy + 2, items[i], C.white, 1)
        else
            Gfx.ptext_center(cx, iy + 2, items[i], C.dim, 1)
        end
    end
    footer(SH - 14, I18n.k.nav_hint_v, C.dim)
end

-- -------------------------------------------------------------- language
function M.drawLang()
    backdrop()
    Gfx.topBar(I18n.k.lang_title, "LANG")
    local px, py, pw, ph = 34, 90, 172, 96
    Gfx.srect(px, py, pw, ph, C.bar)
    E.frame(px, py, pw, ph, C.barEdge)
    local cx = px + pw / 2
    for i = 1, 2 do
        local iy = py + 20 + (i - 1) * 34
        if i == langIdx then
            Gfx.srect(px + 8, iy - 6, pw - 16, 24, C.dirt1)
            E.frame(px + 8, iy - 6, pw - 16, 24, C.yellow)
            Gfx.ptext(px + 13, iy, ">", C.yellow, 1)
        end
        local label = i == 1 and "TIẾNG VIỆT" or "ENGLISH"
        Gfx.ptext_center(cx + 6, iy, label, i == langIdx and C.white or C.dim, 1)
        if (i == 1 and Save.lang == "vi") or (i == 2 and Save.lang == "en") then
            Gfx.ptext(px + pw - 22, iy, "*", C.cyan, 1)
        end
    end
    footer(210, I18n.k.lang_hint, C.dim)
end

-- ------------------------------------------------------- difficulty select
function M.drawDiffSel()
    backdrop()
    Gfx.topBar(I18n.k.diff_title, "DIFF")
    local px, py, pw, ph = 34, 70, 172, 130
    Gfx.srect(px, py, pw, ph, C.bar)
    E.frame(px, py, pw, ph, C.barEdge)
    local cx = px + pw / 2
    for i = 1, 3 do
        local iy = py + 18 + (i - 1) * 36
        if i == diffIdx then
            Gfx.srect(px + 8, iy - 6, pw - 16, 24, C.dirt1)
            E.frame(px + 8, iy - 6, pw - 16, 24, C.yellow)
            Gfx.ptext(px + 13, iy, ">", C.yellow, 1)
        end
        Gfx.ptext_center(cx + 6, iy, I18n.k.diff[i], i == diffIdx and C.white or C.dim, 1)
        if Save.diff == i then
            Gfx.ptext(px + pw - 22, iy, "*", C.cyan, 1)
        end
    end
    footer(222, I18n.k.diff_hint, C.dim)
end

-- ----------------------------------------------------------------- guide
function M.drawGuide()
    backdrop()
    Gfx.topBar(I18n.k.guide_title, "GUIDE")
    local px, py, pw, ph = 12, 40, 216, SH - 62
    Gfx.srect(px, py, pw, ph, C.bar)
    E.frame(px, py, pw, ph, C.barEdge)
    local lines = I18n.k.guide[guidePage]
    local cx = px + pw / 2
    for i = 1, #lines do
        local col = i == 1 and C.cyan or C.white
        Gfx.ptext_center(cx, py + 18 + (i - 1) * 24, lines[i], col, 1)
    end
    Gfx.ptext_center(120, py + ph - 12, I18n.k.page .. " " .. guidePage .. "/" .. #I18n.k.guide, C.dim, 1)
    footer(py + ph + 8, I18n.k.next5, C.dim)
end

-- -------------------------------------------------------------- settings
function M.drawSettings()
    backdrop()
    Gfx.topBar(I18n.k.set_title, "SET")
    local k = I18n.k
    local px, py, pw = 16, 60, 208
    Gfx.srect(px, py, pw, 96, C.bar)
    E.frame(px, py, pw, 96, C.barEdge)
    local rows = {
        { k.set_sound, Save.sound == 1 and k.on or k.off },
        { k.set_diff, k.diff[Save.diff] or k.diff[2] },
    }
    local cx = px + pw / 2
    for i = 1, 2 do
        local iy = py + 18 + (i - 1) * 38
        if i == setIdx then
            Gfx.srect(px + 6, iy - 6, pw - 12, 32, C.dirt1)
            E.frame(px + 6, iy - 6, pw - 12, 32, C.yellow)
        end
        Gfx.ptext_center(cx, iy, rows[i][1], i == setIdx and C.white or C.dim, 1)
        Gfx.ptext_center(cx, iy + 13, "< " .. rows[i][2] .. " >",
                         i == setIdx and C.cyan or C.barEdge, 1)
    end
    footer(176, I18n.k.togg46, C.dim)
    footer(192, I18n.k.nav_hint_v, C.dim)
    Gfx.ptext_center(120, 232, I18n.k.score_line .. "  " .. Save.w1 .. " : " .. Save.w2, C.yellow, 1)
end

-- ----------------------------------------------------------------- about
function M.drawAbout()
    backdrop()
    Gfx.topBar(I18n.k.about_title, "ABOUT")
    local px, py, pw, ph = 12, 56, 216, 176
    Gfx.srect(px, py, pw, ph, C.bar)
    E.frame(px, py, pw, ph, C.barEdge)

    Gfx.ptext_center(122, 74, "GUNBOUND ARENA", C.dirt3, 2)
    Gfx.ptext_center(120, 72, "GUNBOUND ARENA", C.yellow, 2)

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
    footer(py + ph + 10, I18n.k.next5, C.dim)
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
            if menuIdx == 1 then M.go("diffsel")
            elseif menuIdx == 2 then M.go("play2")
            elseif menuIdx == 3 then M.go("lang")
            elseif menuIdx == 4 then M.go("guide")
            elseif menuIdx == 5 then M.go("settings")
            elseif menuIdx == 6 then M.go("about")
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
    if M.show == "diffsel" then
        if k == "up" then diffIdx = (diffIdx - 2) % 3 + 1
        elseif k == "down" then diffIdx = diffIdx % 3 + 1
        elseif k == "left" then diffIdx = math.max(1, diffIdx - 1)
        elseif k == "right" then diffIdx = math.min(3, diffIdx + 1)
        elseif k == "ok" then
            Save.diff = diffIdx
            Save.save()
            M.go("play1")
        elseif k == "back" then M.go("menu") end
        return
    end
    if M.show == "guide" then
        if k == "ok" or k == "right" then
            if guidePage < #I18n.k.guide then guidePage = guidePage + 1 else M.go("menu") end
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
        if k == "up" then setIdx = (setIdx - 2) % 2 + 1
        elseif k == "down" then setIdx = setIdx % 2 + 1
        elseif k == "left" or k == "right" then
            local d = k == "right" and 1 or -1
            if setIdx == 1 then
                Save.sound = Save.sound == 1 and 0 or 1
                if E.audio_set_volume then
                    E.audio_set_volume(Save.sound == 1 and 6 or 0)
                end
            else
                Save.diff = (Save.diff - 1 + d) % 3 + 1
            end
        elseif k == "ok" then
            Save.save()
        elseif k == "back" then
            Save.save()
            M.go("menu")
        end
    end
end

return M
