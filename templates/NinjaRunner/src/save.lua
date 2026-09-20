-- Ninja Runner: settings + high score persistence via engine file API.
local E = engine
local M = { lang = "en", sound = 1, diff = 1, best = 0 }

local FILE = "nr_save.dat"

function M.load()
    if not E.has_files then return end
    local ok, s = pcall(E.file_read, FILE)
    if not ok or type(s) ~= "string" then return end
    for kv in s:gmatch("[^;]+") do
        local k, v = kv:match("^(%w+)=(.-)$")
        if k and M[k] ~= nil then
            if type(M[k]) == "number" then
                local n = tonumber(v)
                if n then M[k] = n end
            elseif v ~= "" then
                M[k] = v
            end
        end
    end
end

function M.save()
    if not E.has_files then return end
    pcall(E.file_write, FILE,
        "lang=" .. M.lang .. ";sound=" .. M.sound ..
        ";diff=" .. M.diff .. ";best=" .. M.best)
end

return M
