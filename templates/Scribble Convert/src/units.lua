-- src/units.lua -- offline conversion tables (fixed local rates, no network)
local M = {}

-- categories: 1=length, 2=mass, 3=currency
M.CAT_NAMES = { "Do dai", "Khoi luong", "Tien te" }
M.CAT_COUNT = 3

-- each unit: { symbol, to_base factor }  base: m / g / VND
M.UNITS = {
    [1] = {
        { "mm", 0.001 },
        { "cm", 0.01 },
        { "m",  1 },
        { "km", 1000 },
        { "in", 0.0254 },
        { "ft", 0.3048 },
        { "yd", 0.9144 },
        { "mi", 1609.344 },
    },
    [2] = {
        { "mg", 0.001 },
        { "g",  1 },
        { "kg", 1000 },
        { "t",  1000000 },
        { "oz", 28.349523 },
        { "lb", 453.59237 },
    },
    [3] = {
        -- fixed local rates vs VND (offline snapshot)
        { "VND", 1 },
        { "USD", 25400 },
        { "EUR", 27500 },
        { "JPY", 170 },
        { "GBP", 32200 },
        { "CNY", 3520 },
        { "KRW", 18.8 },
        { "THB", 720 },
        { "SGD", 19000 },
        { "AUD", 16800 },
    },
}

function M.count(cat)
    local u = M.UNITS[cat]
    return u and #u or 0
end

function M.symbol(cat, idx)
    local u = M.UNITS[cat]
    if not u or not u[idx] then return "?" end
    return u[idx][1]
end

function M.factor(cat, from_idx, to_idx)
    local u = M.UNITS[cat]
    if not u then return 1 end
    local a = u[from_idx]
    local b = u[to_idx]
    if not a or not b or b[2] == 0 then return 1 end
    return a[2] / b[2]
end

function M.convert(cat, from_idx, to_idx, value)
    return value * M.factor(cat, from_idx, to_idx)
end

-- format number for display: trim trailing zeros, cap length
function M.fmt(v)
    if v ~= v or v == math.huge or v == -math.huge then return "--" end
    local av = v < 0 and -v or v
    local s
    if av ~= 0 and (av >= 1e10 or av < 1e-4) then
        -- scientific-ish compact form
        s = string.format("%.4e", v)
        -- normalize e+09 -> e9 style lightly
        s = string.gsub(s, "e%+", "e")
        s = string.gsub(s, "e0+", "e")
        s = string.gsub(s, "e%-0+", "e-")
    elseif av >= 1000 then
        s = string.format("%.2f", v)
    elseif av >= 1 then
        s = string.format("%.4f", v)
    else
        s = string.format("%.6f", v)
    end
    -- strip trailing zeros after decimal point
    if string.find(s, "%.", 1, false) then
        s = string.gsub(s, "0+$", "")
        s = string.gsub(s, "%.$", "")
    end
    if #s > 14 then
        s = string.sub(s, 1, 14)
    end
    return s
end

-- short formula line for the faint note area
function M.formula_line(cat, from_idx, to_idx)
    local a = M.symbol(cat, from_idx)
    local b = M.symbol(cat, to_idx)
    local k = M.factor(cat, from_idx, to_idx)
    local ks
    if k >= 1000 or (k > 0 and k < 0.01) then
        ks = string.format("%.4g", k)
    else
        ks = M.fmt(k)
    end
    return "1 " .. a .. " = " .. ks .. " " .. b
end

function M.work_line(cat, from_idx, to_idx)
    local a = M.symbol(cat, from_idx)
    local b = M.symbol(cat, to_idx)
    return "x' = x * (" .. a .. "/" .. b .. ")"
end

return M
