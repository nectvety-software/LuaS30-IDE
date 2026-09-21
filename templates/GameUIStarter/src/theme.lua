local E = engine

local function c(r, g, b)
    return E.color(r, g, b)
end

local T = {
    bg = c(12, 18, 28),
    bg2 = c(18, 28, 42),
    panel = c(24, 37, 54),
    panel2 = c(31, 48, 68),
    border = c(58, 82, 108),
    text = c(239, 245, 250),
    muted = c(150, 169, 188),
    accent = c(255, 138, 0),
    accent2 = c(255, 188, 84),
    green = c(75, 205, 130),
    red = c(236, 84, 92),
    cyan = c(78, 195, 222),
    white = c(255, 255, 255),
    black = c(0, 0, 0),
}

return T
