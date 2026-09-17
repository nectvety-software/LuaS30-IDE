local E=engine
local white=E.color(255,255,255)
local green=E.color(70,190,110)
local bg=E.color(12,22,34)
local d={}
function E.load() d=E.device_info() end
function E.draw()
  E.clear(bg)
  E.text(6,8,"LuaS30 Native SDK",green)
  E.text(6,28,"family: "..tostring(d.family),white)
  E.text(6,44,"screen: "..d.width.."x"..d.height,white)
  E.text(6,60,"fps: "..d.preferred_fps,white)
  E.text(6,76,"ram: "..d.recommended_ram_kb.." KB",white)
  E.text(6,92,"caps: "..E.capabilities(),white)
  E.text(6,292,"0 = Exit",white)
end
function E.keypressed(k) if k=="0" then E.exit() end end
