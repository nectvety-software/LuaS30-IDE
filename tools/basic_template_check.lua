-- basic_template_check.lua — smoke test cho template "Blank Project" (basic).
--
-- basic/main.lua la khung khoi dong toi gian ma MOI du an moi deu duoc copy,
-- nen no phai: nap duoc, ve duoc, va xu ly phim theo dung hop dong
-- doc/ai/Keypad.md (ten phim chu thuong + alias so du phong D-Pad/OK).
--
-- Cach chay (can Lua 5.1):
--     cd templates/basic && <duong-dan>/lua.exe <repo>/tools/basic_template_check.lua

local log = {}
local exited = false

local function noop() end

engine = {
    W = 240, H = 320, version = "stub/5.1.5", has_files = true,
    color = function(r, g, b) return r * 65536 + g * 256 + b end,
    clear = noop, rect = noop, frame = noop, line = noop,
    text = function(x, y, s, c) log[#log + 1] = tostring(s) end,
    set_font = noop,
    text_width = function(s) return #tostring(s) * 6 end,
    font_height = function() return 8 end,
    image = noop, image_region = noop,
    file_exists = function() return false end,
    file_write = function() return true end,
    file_read = function() return nil end,
    file_delete = function() return true end,
    audio_play = noop, audio_stop = noop, audio_set_volume = noop,
    audio_is_playing = function() return false end,
    flush = noop,
    tick_ms = function() return 0 end,
    exit = function() exited = true end,
    log = noop,
    capabilities = function() return 0 end,
    device_info = function() return {} end,
    runtime_compat = function() return {} end,
}
mre = engine

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

local function find(prefix)
    for _, s in ipairs(log) do
        if s:sub(1, #prefix) == prefix then return s end
    end
    return nil
end

local function draw()
    log = {}
    engine.draw()
end

local function tap(k)
    engine.keypressed(k)
    engine.keyreleased(k)
end

dofile("main.lua")

check("E.load/update/draw/keypressed/keyreleased deu duoc dinh nghia",
      type(engine.load) == "function" and type(engine.update) == "function"
      and type(engine.draw) == "function" and type(engine.keypressed) == "function"
      and type(engine.keyreleased) == "function")

engine.load()
engine.update(0.066)
draw()
check("draw() chay khong loi va ve dong 'key:'", find("key: ") ~= nil, find("key: "))
check("khoi tao last_key = '-'", find("key: -") ~= nil, find("key: "))

tap("right")
draw()
check("keypressed('right') cap nhat last_key", find("key: right") ~= nil, find("key: "))

tap("4")
draw()
check("alias so 4 (left) duoc chap nhan", find("key: 4") ~= nil, find("key: "))

tap("SOFTLEFT")
draw()
check("chu HOA duoc chuan hoa (:lower)", find("2/4/6/8 move") == nil)

tap("softleft")
draw()
check("softleft bat lai help", find("2/4/6/8 move") ~= nil)

-- Giu phim qua nhieu frame update() khong duoc loi, va keyreleased phai go co.
engine.keypressed("right")
for _ = 1, 5 do engine.update(0.066) end
engine.keyreleased("right")
draw()
check("giu right 5 frame roi nha: khong loi", find("key: right") ~= nil)

engine.keypressed("up")
engine.pause()
engine.update(0.066)
engine.resume()
draw()
check("pause()/resume() khong loi", find("key: up") ~= nil)

engine.keypressed("softright")
engine.keyreleased("softright")
check("softright -> E.exit()", exited == true)

print("")
print("basic_template_check: " .. (checks - failures) .. "/" .. checks .. " checks passed")
if failures > 0 then
    print("FAILED")
    os.exit(1)
end
print("PASS")
