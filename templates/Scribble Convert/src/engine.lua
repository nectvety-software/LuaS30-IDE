-- src/engine.lua -- thin optional helpers (main uses global `engine` directly)
local E = engine

local M = {}

function M.screen()
    return E.W or 240, E.H or 320
end

function M.rgb(r, g, b)
    return E.color(r, g, b)
end

function M.save(name, data)
    if E.file_write then
        return E.file_write(name, data)
    end
    return false
end

function M.load(name)
    if E.file_read then
        return E.file_read(name)
    end
    return nil
end

return M
