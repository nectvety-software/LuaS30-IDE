-- src/art.lua -- sketch notebook drawing kit (pencil + ballpoint primitives)
local E = engine

local M = {}

local floor, sqrt = math.floor, math.sqrt

M.W = E.W or 240
M.H = E.H or 320

M.PAPER  = E.color(250, 248, 236)
M.RULE   = E.color(186, 208, 228)
M.MARGIN = E.color(230, 168, 172)
M.PENCIL = E.color(108, 110, 120)
M.PENCIL2 = E.color(160, 162, 172)
M.PEN    = E.color(30, 52, 140)
M.PEN2   = E.color(84, 112, 196)
M.INK    = E.color(22, 24, 34)
M.LEAD   = E.color(108, 110, 120)
M.LEAD2  = E.color(160, 162, 172)
M.RED    = E.color(198, 38, 44)
M.SHADOW = E.color(206, 216, 226)
M.WHITE  = E.color(255, 255, 255)

-- deterministic jitter so strokes do not shimmer every frame
local jcount = 0
local jseed = 7

function M.jit_reset(seed)
    jcount = 0
    if seed then jseed = seed end
end

local function jr()
    jcount = jcount + 1
    local x = (jcount * 1103515245 + jseed * 12345 + 2531011) % 2147483648
    x = floor(x / 65536) % 32768
    return x / 16384 - 1
end

local function clampx(v)
    if v < 0 then return 0 end
    if v > M.W - 1 then return M.W - 1 end
    return v
end

local function clampy(v)
    if v < 0 then return 0 end
    if v > M.H - 1 then return M.H - 1 end
    return v
end

function M.stroke(x1, y1, x2, y2, c, amp)
    x1, y1, x2, y2 = floor(x1), floor(y1), floor(x2), floor(y2)
    if (x1 < 0 and x2 < 0) or (x1 > M.W - 1 and x2 > M.W - 1)
        or (y1 < 0 and y2 < 0) or (y1 > M.H - 1 and y2 > M.H - 1) then
        return
    end
    amp = amp or 0
    local dx, dy = x2 - x1, y2 - y1
    if amp <= 0 then
        E.line(clampx(x1), clampy(y1), clampx(x2), clampy(y2), c)
        return
    end
    local len = sqrt(dx * dx + dy * dy)
    local n = floor(len / 13) + 1
    if n > 5 then n = 5 end
    if n <= 1 then
        E.line(clampx(x1), clampy(y1), clampx(x2), clampy(y2), c)
        return
    end
    local px, py = clampx(x1), clampy(y1)
    local i = 1
    while i <= n do
        local t = i / n
        local nx, ny = x1 + dx * t, y1 + dy * t
        if i < n then
            nx = nx + jr() * amp
            ny = ny + jr() * amp
        end
        nx, ny = clampx(nx), clampy(ny)
        E.line(px, py, nx, ny, c)
        px, py = nx, ny
        i = i + 1
    end
end

function M.outline(x, y, w, h, c, amp)
    local x2, y2 = x + w, y + h
    amp = amp or 0.8
    M.stroke(x, y, x2, y, c, amp)
    M.stroke(x2, y, x2, y2, c, amp)
    M.stroke(x2, y2, x, y2, c, amp)
    M.stroke(x, y2, x, y, c, amp)
end

function M.fill(x, y, w, h, c)
    x, y, w, h = floor(x), floor(y), floor(w), floor(h)
    if w <= 0 or h <= 0 then return end
    local x2, y2 = x + w, y + h
    if x < 0 then x = 0 end
    if y < 0 then y = 0 end
    if x2 > M.W then x2 = M.W end
    if y2 > M.H then y2 = M.H end
    if x2 <= x or y2 <= y then return end
    E.rect(x, y, x2 - x, y2 - y, c)
end

-- notebook paper: horizontal rules + red margin
function M.paper()
    E.clear(M.PAPER)
    local y = 16
    while y < M.H do
        E.line(0, y, M.W - 1, y, M.RULE)
        y = y + 16
    end
    E.line(26, 0, 26, M.H - 1, M.MARGIN)
    E.line(29, 0, 29, M.H - 1, M.MARGIN)
end

function M.set_font(n)
    E.set_font(n)
end

function M.text(x, y, s, c)
    E.text(floor(x), floor(y), tostring(s or ""), c or M.INK)
end

function M.tw(s)
    if E.text_width then
        return E.text_width(tostring(s or ""))
    end
    return #tostring(s or "") * 6
end

function M.ctext(cx, y, s, c)
    M.text(cx - M.tw(s) / 2, y, s, c)
end

function M.rtext(rx, y, s, c)
    M.text(rx - M.tw(s), y, s, c)
end

-- slight per-char vertical drift = handwritten slant
function M.slanted(x, y, s, c, slope)
    s = tostring(s or "")
    slope = slope or 0.2
    local i, n = 1, #s
    while i <= n do
        M.text(x + (i - 1) * 6, y + (i - 1) * slope, string.sub(s, i, i), c)
        i = i + 1
    end
end

-- title with double hand underline
function M.header(title, y)
    y = y or 6
    M.set_font(14)
    local w = M.tw(title)
    local x0 = M.W / 2 - w / 2
    M.text(x0, y, title, M.INK)
    M.stroke(x0, y + 14, x0 + w, y + 15, M.PEN, 0.8)
    M.stroke(x0 + 3, y + 17, x0 + w - 2, y + 18, M.PEN2, 0.8)
    M.set_font(8)
end

-- blue ballpoint arrow between the two unit frames
function M.pen_arrow(x1, y, x2, c)
    c = c or M.PEN
    local mid = (x1 + x2) / 2
    -- shaft with slight bow (ballpoint pressure)
    M.stroke(x1, y, mid, y - 2, c, 0.5)
    M.stroke(mid, y - 2, x2 - 8, y, c, 0.5)
    -- open chevron head
    M.stroke(x2 - 9, y - 6, x2, y, c, 0.3)
    M.stroke(x2, y, x2 - 9, y + 6, c, 0.3)
    -- ballpoint blob at tip
    M.fill(x2 - 2, y - 1, 3, 3, c)
    M.fill(x2 - 1, y - 2, 2, 2, c)
end

-- sunken ink field: paper well + hand outline + bottom/right shadow lip
function M.sunk_box(x, y, w, h, focused)
    M.fill(x, y, w, h, M.PAPER)
    -- inner shadow lip (sunken)
    M.fill(x + 1, y + h - 2, w - 2, 1, M.SHADOW)
    M.fill(x + w - 2, y + 1, 1, h - 3, M.SHADOW)
    local edge = focused and M.PEN or M.PENCIL
    M.outline(x, y, w, h, edge, 0.7)
    if focused then
        -- second light pass = pressed / active ink
        M.outline(x + 2, y + 2, w - 4, h - 4, M.PEN2, 0.5)
    end
end

-- pencil unit frame (the two rectangles in the brief)
function M.pencil_frame(x, y, w, h, label, value, focused)
    M.fill(x, y, w, h, M.PAPER)
    -- light hatch corner tick
    M.stroke(x + 3, y + 3, x + 10, y + 3, M.PENCIL2, 0)
    M.stroke(x + 3, y + 3, x + 3, y + 10, M.PENCIL2, 0)
    local edge = focused and M.PEN or M.PENCIL
    M.outline(x, y, w, h, edge, 1.0)
    if focused then
        M.outline(x - 2, y - 2, w + 4, h + 4, M.PEN2, 0.6)
    end
    M.set_font(8)
    M.ctext(x + w / 2, y + 6, label, focused and M.PEN or M.LEAD)
    M.set_font(14)
    M.ctext(x + w / 2, y + 24, value, M.INK)
    M.set_font(8)
    if focused then
        -- small caret marks under value
        local vw = M.tw(value)
        local cx = x + w / 2
        M.stroke(cx - vw / 2, y + h - 6, cx + vw / 2, y + h - 5, M.RED, 0.5)
    end
end

-- faint handwritten formula note
function M.note(x, y, s, slope)
    M.set_font(8)
    M.slanted(x, y, s, M.LEAD2, slope or 0.15)
end

-- softkey bar
function M.softkeys(left, right, center)
    local y0 = M.H - 22
    M.fill(0, y0, M.W, M.H - y0, M.PAPER)
    E.line(0, y0, M.W - 1, y0, M.RULE)
    M.set_font(8)
    local ty = M.H - 14
    if left then M.text(4, ty, left, M.PEN) end
    if right then M.rtext(M.W - 6, ty, right, M.PEN) end
    if center then M.ctext(M.W / 2, ty, center, M.LEAD) end
end

return M
