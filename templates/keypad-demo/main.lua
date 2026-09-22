-- Keypad Demo — mau minh hoa hop dong phim S30+ cho LuaS30 / MRE.
--
-- Nguon that: doc/ai/Keypad.md + doc/reference/API.md.
-- Runtime CHI gui ten phim chu thuong:
--     up down left right ok softleft softright clear back 0-9 * #
-- Khong dung chuot/touch: moi tuong tac di qua D-Pad + softkey + phim so.
--
-- Man hinh: MENU -> { Kiem tra phim | Nhap so | Huong dan | Thoat }
-- Softkey trai = options/help, softkey phai = back (khong dao nguoc).

local E = engine
local K = require("src.keypad")

local W = E.W or 240
local H = E.H or 320

local COL = {
    bg     = E.color(16, 20, 30),
    panel  = E.color(30, 36, 52),
    border = E.color(58, 58, 86),
    text   = E.color(235, 240, 250),
    dim    = E.color(140, 152, 175),
    hot    = E.color(255, 210, 70),
    accent = E.color(0, 122, 204),
}

local MENU = {
    { label = "Kiem tra phim", screen = "keys" },
    { label = "Nhap so",       screen = "input" },
    { label = "Huong dan",     screen = "help" },
    { label = "Thoat",         screen = "exit" },
}

local screen = "menu"
local previous = "menu"
local menu_index = 1
local last_key = "-"
local key_log = {}
local typed = ""
local saved = ""
local toast = ""
local toast_at = 0

local TOAST_MS = 1600
local MAX_TYPED = 16

local function say(msg)
    toast = msg
    toast_at = E.tick_ms()
end

-- Chuyen man hinh. Luon go trang thai phim: phim dang giu luc chuyen canh
-- co the khong bao gio nhan duoc keyreleased tuong ung.
local function go(name)
    if name == "exit" then
        E.exit()
        return
    end
    if name ~= "help" then
        previous = name
    end
    screen = name
    K.reset()
end

local function held_list()
    local out = {}
    for _, name in ipairs(K.NAMES) do
        if K.held[name] then
            out[#out + 1] = name
        end
    end
    if #out == 0 then
        return "-"
    end
    return table.concat(out, " ")
end

local function draw_chrome(hint_left, hint_right)
    E.rect(0, 0, W, 18, COL.panel)
    E.text(6, 5, "KEYPAD DEMO", COL.text)
    E.rect(0, H - 18, W, 18, COL.panel)
    E.text(6, H - 14, hint_left, COL.dim)
    local tw = E.text_width(hint_right)
    E.text(W - tw - 6, H - 14, hint_right, COL.dim)
end

local function draw_toast()
    if toast == "" then
        return
    end
    if E.tick_ms() - toast_at >= TOAST_MS then
        toast = ""
        return
    end
    E.rect(12, H - 42, W - 24, 16, COL.hot)
    E.text(18, H - 38, toast, COL.bg)
end

local function draw_menu()
    E.text(10, 28, "Chon muc roi bam OK", COL.dim)
    for i = 1, #MENU do
        local y = 54 + (i - 1) * 24
        local selected = (i == menu_index)
        if selected then
            E.rect(12, y - 5, W - 24, 20, COL.accent)
        end
        E.text(20, y, (selected and "> " or "  ") .. MENU[i].label,
               selected and COL.text or COL.dim)
    end
end

local function draw_keys()
    E.text(10, 26, "Phim cuoi: " .. last_key, COL.hot)
    E.text(10, 40, "Dang giu: " .. held_list(), COL.text)
    E.text(10, 54, "(* = xoa lich su)", COL.dim)

    for i = 1, math.min(#key_log, 4) do
        local name = key_log[#key_log - i + 1]
        E.text(14, 72 + (i - 1) * 12, name, COL.dim)
    end

    K.drawPad(39, 136, 52, 14, 3, COL)
end

local function draw_input()
    E.text(10, 30, "Nhap so 0-9:", COL.dim)
    E.rect(14, 46, W - 28, 26, COL.panel)
    E.frame(14, 46, W - 28, 26, COL.border)
    E.text(22, 55, (typed == "" and "_" or typed), COL.hot)

    local lines = {
        "0-9     nhap ky tu",
        "clear   xoa 1 ky tu",
        "#       xoa het",
        "ok      luu vao file",
        "*       doi kieu nhap",
        "softR   quay lai menu",
    }
    for i = 1, #lines do
        E.text(14, 86 + (i - 1) * 12, lines[i], COL.dim)
    end

    if saved ~= "" then
        E.text(14, 166, "Da luu: " .. saved, COL.text)
    end
end

local function draw_help()
    local lines = {
        { "Ten phim runtime gui (chu thuong):", COL.text },
        { "  up down left right ok", COL.text },
        { "  softleft softright clear back", COL.text },
        { "  0 1 2 3 4 5 6 7 8 9  *  #", COL.text },
        { "", COL.dim },
        { "Quy tac:", COL.text },
        { "  - Giu bang trang thai", COL.dim },
        { "    pressed / released", COL.dim },
        { "  - Khong dung chuot / touch", COL.dim },
        { "  - 2 8 4 6 5 du phong D-Pad + OK", COL.dim },
        { "  - softleft = menu, softright = back", COL.dim },
        { "  - Nhap lieu: digit noi chuoi,", COL.dim },
        { "    clear xoa 1 ky tu, # xoa het", COL.dim },
        { "", COL.dim },
        { "Nhan nut vat ly trong tai lieu", COL.dim },
        { "KHONG phai ten phim Lua.", COL.dim },
    }
    for i = 1, #lines do
        E.text(10, 26 + (i - 1) * 12, lines[i][1], lines[i][2])
    end
end

-- `fresh` = lan nhan dau tien cua phim. Runtime co the gui lai keypressed khi
-- phim dang duoc giu (su kien repeat), nen hanh dong mot lan phai chan bang
-- `fresh`; dieu huong thi de repeat de cuon nhanh.
local function menu_key(k, fresh)
    if k == "up" or k == "2" then
        menu_index = menu_index - 1
        if menu_index < 1 then
            menu_index = #MENU
        end
    elseif k == "down" or k == "8" then
        menu_index = menu_index + 1
        if menu_index > #MENU then
            menu_index = 1
        end
    elseif (k == "ok" or k == "5") and fresh then
        go(MENU[menu_index].screen)
    elseif k == "softleft" and fresh then
        go("help")
    elseif (k == "softright" or k == "back") and fresh then
        E.exit()
    end
end

local function keys_key(k, fresh)
    if (k == "softright" or k == "back" or k == "clear") and fresh then
        go("menu")
    elseif k == "softleft" and fresh then
        go("help")
    elseif k == "*" and fresh then
        key_log = {}
        say("Da xoa lich su phim")
    end
end

local function input_key(k, fresh)
    local d = K.digit(k)
    if d then
        if #typed < MAX_TYPED then
            typed = typed .. d
        end
    elseif k == "clear" and fresh then
        if #typed > 0 then
            typed = typed:sub(1, #typed - 1)
        end
    elseif k == "#" and fresh then
        typed = ""
        say("Da xoa het")
    elseif (k == "softright" or k == "back") and fresh then
        go("menu")
    elseif k == "softleft" and fresh then
        go("help")
    elseif k == "*" and fresh then
        say("Phim *: doi kieu nhap (demo)")
    elseif (k == "ok" or k == "5") and fresh then
        if typed == "" then
            say("Chua nhap gi")
        else
            saved = typed
            if E.has_files then
                E.file_write("keypad_input.txt", typed)
                say("Da luu vao file")
            else
                say("Da ghi nho (khong co file)")
            end
        end
    end
end

local function help_key(k, fresh)
    if fresh and (k == "softright" or k == "back" or k == "clear"
                  or k == "ok" or k == "softleft") then
        go(previous)
    end
end

function E.load()
    E.set_font(8)
    go("menu")
end

function E.update(dt)
    -- dt tinh tu FPS cua runtime (conf.lua). Khong dung cho timer o day.
end

function E.draw()
    E.clear(COL.bg)

    if screen == "menu" then
        draw_menu()
        draw_chrome("Huong dan", "Thoat")
    elseif screen == "keys" then
        draw_keys()
        draw_chrome("Huong dan", "Quay lai")
    elseif screen == "input" then
        draw_input()
        draw_chrome("Huong dan", "Quay lai")
    else
        draw_help()
        draw_chrome("Quay lai", "Quay lai")
    end

    draw_toast()
end

function E.keypressed(raw)
    local k, fresh = K.press(raw)
    if not k then
        return
    end

    last_key = k
    key_log[#key_log + 1] = k
    if #key_log > 8 then
        table.remove(key_log, 1)
    end

    if screen == "menu" then
        menu_key(k, fresh)
    elseif screen == "keys" then
        keys_key(k, fresh)
    elseif screen == "input" then
        input_key(k, fresh)
    else
        help_key(k, fresh)
    end
end

function E.keyreleased(raw)
    K.release(raw)
end

function E.pause()
    K.reset()
end

function E.resume()
    K.reset()
end
