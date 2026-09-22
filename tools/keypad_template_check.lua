-- keypad_template_check.lua — test stub cho template "Keypad Demo".
--
-- Thuc thi dung checklist doc/ai/Keypad.md muc 4: goi engine.keypressed("down")
-- bang stub roi assert trang thai, thay vi chi doc code.
--
-- Cach chay (can Lua 5.1 — cung ban voi vendor/lua-5.1.5):
--   1) build lua.exe tu source trong repo:
--        cd vendor/lua-5.1.5/src
--        gcc -O2 -w -o lua.exe $(ls *.c | grep -v -E '^(lua|luac)\.c$') lua.c -lm
--   2) chay harness tu thu muc template:
--        cd templates/keypad-demo && <duong-dan>/lua.exe <repo>/tools/keypad_template_check.lua
--
-- Khong import gi tu studio/ hay engine/: chi mot bang `engine` gia.

-- ---------------------------------------------------------------- stub engine
local calls = { texts = {}, writes = {} }
local exited = false
local clock = 0

local function noop() end

engine = {
    W = 240,
    H = 320,
    version = "stub/5.1.5",
    has_files = true,
    has_images = false,
    has_audio = false,
    has_touch = false,

    color = function(r, g, b) return r * 65536 + g * 256 + b end,
    clear = noop,
    rect = noop,
    frame = noop,
    line = noop,
    text = function(x, y, s, c) calls.texts[#calls.texts + 1] = tostring(s) end,
    set_font = noop,
    text_width = function(s) return #tostring(s) * 6 end,
    font_height = function() return 8 end,
    image = noop,
    image_region = noop,

    file_exists = function() return false end,
    file_write = function(name, data)
        calls.writes[#calls.writes + 1] = { name, data }
        return true
    end,
    file_read = function() return nil end,
    file_delete = function() return true end,

    audio_play = noop,
    audio_stop = noop,
    audio_set_volume = noop,
    audio_is_playing = function() return false end,

    flush = noop,
    tick_ms = function() return clock end,
    exit = function() exited = true end,
    log = noop,
    capabilities = function() return 0 end,
    device_info = function() return {} end,
    runtime_compat = function() return {} end,
}
mre = engine

-- ---------------------------------------------------------------- assert helpers
local checks, failures = 0, 0

local function check(label, ok, detail)
    checks = checks + 1
    if ok then
        print("ok   : " .. label)
    else
        failures = failures + 1
        print("FAIL : " .. label .. (detail and ("  [" .. tostring(detail) .. "]") or ""))
    end
end

local function drawn()
    calls.texts = {}
    engine.draw()
    return calls.texts
end

local function has(list, needle)
    for _, s in ipairs(list) do
        if s == needle then return true end
    end
    return false
end

local function starts_with(list, prefix)
    for _, s in ipairs(list) do
        if s:sub(1, #prefix) == prefix then return s end
    end
    return nil
end

local function cursor()
    local line = starts_with(drawn(), "> ")
    return line and line:sub(3) or "(none)"
end

local function last_key()
    local line = starts_with(drawn(), "Phim cuoi: ")
    return line and line:sub(12) or "(none)"
end

local function held()
    local line = starts_with(drawn(), "Dang giu: ")
    return line and line:sub(11) or "(none)"
end

local function press(k) engine.keypressed(k) end
local function release(k) engine.keyreleased(k) end
local function tap(k) press(k) release(k) end

-- Di con tro menu toi muc co nhan `label` (an toan voi moi thu tu).
local function menu_goto(label)
    for _ = 1, 8 do
        if cursor() == label then return true end
        tap("down")
    end
    return false
end

local function enter(label)
    menu_goto(label)
    tap("ok")
end

-- ---------------------------------------------------------------- load template
dofile("main.lua")
engine.load()

-- 1. Menu: khoi tao + wrap-around, ca D-Pad lan alias so
check("menu khoi tao o muc 1", cursor() == "Kiem tra phim", cursor())

tap("down")
check("down -> muc 2", cursor() == "Nhap so", cursor())

tap("8")
check("alias so 8 -> muc 3", cursor() == "Huong dan", cursor())

tap("down")
check("down -> muc 4", cursor() == "Thoat", cursor())

tap("down")
check("down qua cuoi -> wrap ve muc 1", cursor() == "Kiem tra phim", cursor())

tap("up")
check("up tu muc 1 -> wrap ve cuoi", cursor() == "Thoat", cursor())

tap("2")
check("alias so 2 (up) -> lui ve muc 3", cursor() == "Huong dan", cursor())

tap("8")
check("alias so 8 (down) -> muc 4", cursor() == "Thoat", cursor())

tap("8")
check("alias so 8 qua cuoi -> wrap ve muc 1", cursor() == "Kiem tra phim", cursor())

-- 2. softright/back thoat tu menu
menu_goto("Thoat")
tap("ok")
check("ok tren 'Thoat' -> E.exit()", exited == true)

-- 3. Man hinh Kiem tra phim: hien phim, giu/nha, ten phim la
exited = false
enter("Kiem tra phim")
check("ok -> man hinh kiem tra phim", has(drawn(), "Phim cuoi: ok"))

local pad = drawn()
check("ban phim vat ly ve bang text (khong anh)",
      has(pad, "OK") and has(pad, "L") and has(pad, "R") and has(pad, "#") and has(pad, "CLR"))

press("left")
check("giu left -> 'Dang giu: left'", held() == "left", held())
release("left")
check("nha left -> 'Dang giu: -'", held() == "-", held())

-- Giu nhieu phim cung luc: thu tu theo K.NAMES (up down left right ok
-- softleft softright clear back 0-9 * #). Dung phim thu dong tren man hinh
-- nay — softright/softleft se dieu huong, khong con o man hinh kiem tra.
press("right")
press("left")
press("3")
check("giu nhieu phim -> liet ke theo thu tu K.NAMES",
      held() == "left right 3", held())
release("right")
release("left")
release("3")
check("nha het -> 'Dang giu: -'", held() == "-", held())

-- Ten phim KHONG ton tai phai bi bo qua (khong bia ten phim).
local before = last_key()
tap("KEY_UP")
tap("KEY_OK")
tap("KEY_SOFT_LEFT")
tap("enter")
tap("touch")
tap("space")
tap("10")
tap("")
check("ten phim khong ton tai bi bo qua", last_key() == before, last_key())

-- Nhung chu HOA thi PHAI duoc chap nhan: template chuan hoa bang :lower()
-- truoc khi so sanh (Keypad.md muc 0), nen "SOFTLEFT" == "softleft".
tap("SOFTLEFT")
check("'SOFTLEFT' chuan hoa thanh softleft -> mo Huong dan",
      has(drawn(), "Ten phim runtime gui (chu thuong):"))
tap("softright")
check("quay lai man hinh kiem tra", last_key() == "softright", last_key())

tap("*")
check("'*' bao da xoa lich su phim", has(drawn(), "Da xoa lich su phim"))

tap("softright")
check("softright tu man hinh kiem tra -> ve menu", cursor() == "Kiem tra phim", cursor())

-- 4. Man hinh Nhap so: digit / clear / '#'
enter("Nhap so")
check("vao man hinh nhap so", has(drawn(), "_"))

tap("1") tap("2") tap("3")
check("digit noi chuoi -> 123", has(drawn(), "123"))

tap("clear")
check("clear xoa 1 ky tu -> 12", has(drawn(), "12"))

tap("#")
check("'#' xoa het -> trong", has(drawn(), "_"))

tap("5") tap("7")
check("nhap lai -> 57", has(drawn(), "57"))

-- 5. Repeat gate: giu ok chi luu MOT lan
calls.writes = {}
press("ok")
press("ok")
press("ok")
release("ok")
check("giu ok (su kien repeat) chi luu 1 lan", #calls.writes == 1, #calls.writes)
check("noi dung luu dung", calls.writes[1] and calls.writes[1][2] == "57",
      calls.writes[1] and calls.writes[1][2])
check("bao da luu", has(drawn(), "Da luu: 57"))

-- digit van cho repeat, nhung bi chan o MAX_TYPED
tap("#")
for _ = 1, 20 do press("9") end
release("9")
check("digit cho repeat, chan o MAX_TYPED = 16",
      starts_with(drawn(), string.rep("9", 16)) ~= nil)

tap("softright")
check("softright tu man hinh nhap -> ve menu", cursor() == "Nhap so", cursor())

-- 6. Man hinh Huong dan: softleft mo, softright dong
tap("softleft")
local help = drawn()
check("softleft tu menu -> Huong dan", has(help, "Ten phim runtime gui (chu thuong):"))
check("Huong dan liet ke du 4 nhom ten phim",
      has(help, "  up down left right ok")
      and has(help, "  softleft softright clear back")
      and has(help, "  0 1 2 3 4 5 6 7 8 9  *  #"))

tap("softright")
check("softright tu Huong dan -> ve man truoc", cursor() == "Nhap so", cursor())

-- 7. pause/resume go trang thai phim
enter("Kiem tra phim")
press("up")
check("giu up truoc khi pause", held() == "up", held())
engine.pause()
check("pause() go trang thai phim", held() == "-", held())
release("up")
engine.resume()
check("resume() cung go trang thai phim", held() == "-", held())

-- ---------------------------------------------------------------- ket qua
print("")
print("keypad_template_check: " .. (checks - failures) .. "/" .. checks .. " checks passed")
if failures > 0 then
    print("FAILED")
    os.exit(1)
end
print("PASS")
