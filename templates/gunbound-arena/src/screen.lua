-- Canvas that = 240x320, phep 1:1 (bang chung: E.clear to day 320 dong,
-- VXPEmu khong keu gian). HUD that cua bay tran ra ngoai la do clip rect
-- cham bien cua runtime, khong phai do chieu cao man hinh.
local function readH()
    local ok, di = pcall(function()
        return engine.device_info and engine.device_info()
    end)
    if ok and type(di) == "table" then
        return tonumber(di.height)
    end
end

local H = readH() or (engine and tonumber(engine.H)) or 320
if H < 240 or H > 320 then H = 320 end

return { W = 240, H = H }
