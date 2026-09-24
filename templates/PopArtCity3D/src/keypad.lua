-- src/keypad.lua — hop dong phim S30+ cho LuaS30 / MRE.
--
-- Nguon that: doc/ai/Keypad.md + doc/reference/API.md + engine/src/runtime_lua.c
-- Runtime CHI gui ten phim chu thuong qua engine.keypressed / engine.keyreleased:
--
--     up  down  left  right  ok  softleft  softright  clear  back  0-9  *  #
--
-- Cac hang KEY_UP / KEY_OK / KEY_SOFT_LEFT trong tai lieu chi la NHAN cho nut
-- VAT LY, KHONG phai identifier Lua. Khong bao gio viet:
--
--     if k == "KEY_UP" then end      -- SAI
--     if k == "LEFT" then end        -- SAI
--     if k == "SOFTLEFT" then end    -- SAI
--
-- Module nay gom: bang trang thai giu phim, helper alias so du phong D-Pad,
-- va bo cuc ban phim vat ly de ve bang rect/text (khong phu thuoc anh).

local M = {}

-- Tap 21 ten phim hop le (doc/ai/Keypad.md muc 0).
M.NAMES = {
    "up", "down", "left", "right", "ok",
    "softleft", "softright", "clear", "back",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "*", "#",
}

M.valid = {}
for _, name in ipairs(M.NAMES) do
    M.valid[name] = true
end

-- Bang trang thai: true o keypressed, false o keyreleased.
-- Khong suy dien "dang giu" tu mot su kien don (Keypad.md muc 2.1).
M.held = {}

local function norm(k)
    return tostring(k or ""):lower()
end

-- Tra ve (ten phim chuan hoa, fresh), hoac (nil, false) neu runtime gui ten la.
-- `fresh` = true chi o lan nhan DAU TIEN: runtime co the gui lai keypressed cho
-- phim dang duoc giu (su kien repeat), nen hanh dong mot lan phai chan bang
-- `fresh`, con dieu huong thi de repeat cho cuon nhanh.
function M.press(k)
    k = norm(k)
    if not M.valid[k] then
        return nil, false
    end
    local fresh = not M.held[k]
    M.held[k] = true
    return k, fresh
end

function M.release(k)
    k = norm(k)
    if not M.valid[k] then
        return nil
    end
    M.held[k] = false
    return k
end

-- Go het trang thai khi doi man hinh: phim dang giu luc chuyen canh co the
-- khong bao gio nhan duoc keyreleased tuong ung.
function M.reset()
    for name in pairs(M.held) do
        M.held[name] = false
    end
end

-- down("up", "2") -> true neu MOT trong cac phim dang duoc giu.
function M.down(...)
    for i = 1, select("#", ...) do
        if M.held[select(i, ...)] then
            return true
        end
    end
    return false
end

-- Alias so du phong: 2/8/4/6/5 thay cho D-Pad va OK khi mot huong bi liet
-- (Keypad.md muc 2.3).
function M.up()
    return M.down("up", "2")
end

function M.downKey()
    return M.down("down", "8")
end

function M.left()
    return M.down("left", "4")
end

function M.right()
    return M.down("right", "6")
end

function M.ok()
    return M.down("ok", "5")
end

-- Softkey trai = menu/options, softkey phai = back (Keypad.md muc 2.4).
-- Khong dao nguoc hai phim nay.
function M.options()
    return M.down("softleft")
end

function M.back()
    return M.down("softright", "back")
end

-- Tra ve chu so "0".."9" neu k la phim so, nguoc lai nil.
function M.digit(k)
    k = norm(k)
    if #k == 1 and k >= "0" and k <= "9" then
        return k
    end
    return nil
end

-- Bo cuc ban phim vat ly: { {ten Lua, nhan hien thi}, ... } theo tung hang.
M.PAD = {
    { { "softleft", "L" }, { "ok", "OK" }, { "softright", "R" } },
    { { "left", "<" }, { "up", "^" }, { "right", ">" } },
    { { "down", "v" }, { "clear", "CLR" }, { "back", "BK" } },
    { { "1", "1" }, { "2", "2" }, { "3", "3" } },
    { { "4", "4" }, { "5", "5" }, { "6", "6" } },
    { { "7", "7" }, { "8", "8" }, { "9", "9" } },
    { { "*", "*" }, { "0", "0" }, { "#", "#" } },
}

-- Ve ban phim vat ly; o nao dang duoc giu thi to sang mau `hot`.
-- colors = { panel = ..., border = ..., text = ..., hot = ... }
function M.drawPad(x, y, cell_w, cell_h, gap, colors)
    local E = engine
    for row = 1, #M.PAD do
        local cells = M.PAD[row]
        local cy = y + (row - 1) * (cell_h + gap)
        for col = 1, #cells do
            local key, label = cells[col][1], cells[col][2]
            local cx = x + (col - 1) * (cell_w + gap)
            if M.held[key] then
                E.rect(cx, cy, cell_w, cell_h, colors.hot)
                E.text(cx + 4, cy + (cell_h - 8) / 2, label, colors.bg)
            else
                E.rect(cx, cy, cell_w, cell_h, colors.panel)
                E.frame(cx, cy, cell_w, cell_h, colors.border)
                E.text(cx + 4, cy + (cell_h - 8) / 2, label, colors.text)
            end
        end
    end
end

return M
