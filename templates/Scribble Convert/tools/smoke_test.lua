-- tools/smoke_test.lua -- headless smoke: conversion math + draw/key path
-- Run: lua tools/smoke_test.lua   (or luac-compatible Lua 5.1)

local ROOT = arg and arg[0] and string.match(arg[0], "^(.*)[/\\]") or "."
if ROOT == "." then ROOT = "" end
local PROJ = ROOT .. "/.."
if string.sub(PROJ, -2) == "/." then PROJ = string.sub(PROJ, 1, -3) end

-- package path for require("src.*")
package.path = PROJ .. "/?.lua;" .. PROJ .. "/?/init.lua;" .. package.path

local calls = { clear = 0, rect = 0, line = 0, text = 0, flush = 0, exit = 0 }
local texts = {}

engine = {
    W = 240,
    H = 320,
    has_files = false,
    has_images = false,
    has_audio = false,
}

function engine.color(r, g, b)
    -- pack roughly as rgb565 for identity
    return (math.floor(r / 8) * 2048) + (math.floor(g / 4) * 32) + math.floor(b / 8)
end

function engine.clear(c)
    calls.clear = calls.clear + 1
end

function engine.rect(x, y, w, h, c)
    calls.rect = calls.rect + 1
end

function engine.line(x1, y1, x2, y2, c)
    calls.line = calls.line + 1
end

function engine.text(x, y, s, c)
    calls.text = calls.text + 1
    texts[#texts + 1] = { x = x, y = y, s = tostring(s) }
end

function engine.set_font(n) end

function engine.text_width(s)
    return #tostring(s or "") * 6
end

function engine.flush()
    calls.flush = calls.flush + 1
end

function engine.exit()
    calls.exit = calls.exit + 1
end

function engine.tick_ms()
    return 0
end

function engine.log(m) end

-- load main
local ok, err = pcall(function()
    dofile(PROJ .. "/main.lua")
end)
if not ok then
    print("FAIL load main: " .. tostring(err))
    os.exit(1)
end

assert(type(engine.load) == "function", "missing engine.load")
assert(type(engine.update) == "function", "missing engine.update")
assert(type(engine.draw) == "function", "missing engine.draw")
assert(type(engine.keypressed) == "function", "missing engine.keypressed")

engine.load()

-- conversion unit tests via require
local U = require("src.units")
local function approx(a, b, eps)
    eps = eps or 1e-6
    return math.abs(a - b) <= eps
end

assert(approx(U.convert(1, 3, 2, 1), 100), "1 m -> cm should be 100, got " .. U.convert(1, 3, 2, 1))
assert(approx(U.convert(2, 3, 2, 1), 1000), "1 kg -> g should be 1000")
assert(approx(U.convert(3, 2, 1, 1), 25400), "1 USD -> VND should be 25400")
assert(approx(U.convert(1, 3, 4, 2), 0.002), "2 m -> km should be 0.002")

-- draw several frames
for i = 1, 5 do
    engine.update(1 / 15)
    engine.draw()
end

assert(calls.clear > 0, "clear not called")
assert(calls.rect > 0, "rect not called")
assert(calls.line > 0, "line not called")
assert(calls.text > 0, "text not called")
assert(calls.flush > 0, "flush not called")

-- key path: type digits, swap, change category
engine.keypressed("7")
engine.keypressed("7")
engine.keypressed("*")   -- on input focus -> decimal? wait focus is IN so *
engine.keypressed("softleft")
engine.keypressed("ok")
engine.keypressed("6")
engine.keypressed("2")
engine.keypressed("#")
engine.keypressed("softright")
engine.update(1)
engine.update(1)
engine.draw()

assert(calls.exit > 0, "exit not called after softright")

-- layout bounds: all drawn text within screen
for i = 1, #texts do
    local t = texts[i]
    assert(t.x >= -2 and t.x < 240, "text x out of bounds: " .. t.x .. " '" .. t.s .. "'")
    assert(t.y >= 0 and t.y < 320, "text y out of bounds: " .. t.y .. " '" .. t.s .. "'")
end

-- key content present
local joined = {}
for i = 1, #texts do joined[#joined + 1] = texts[i].s end
local blob = table.concat(joined, "|")
assert(string.find(blob, "DOI DON VI", 1, true), "title missing")
assert(string.find(blob, "Do dai", 1, true), "category tab missing")
assert(string.find(blob, "GOC", 1, true), "from frame label missing")
assert(string.find(blob, "DICH", 1, true), "to frame label missing")
assert(string.find(blob, "Ket qua", 1, true), "result label missing")

print("SMOKE_OK clear=" .. calls.clear .. " rect=" .. calls.rect
    .. " line=" .. calls.line .. " text=" .. calls.text
    .. " flush=" .. calls.flush .. " exit=" .. calls.exit)
