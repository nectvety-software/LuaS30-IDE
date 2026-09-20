Sprites = Sprites or {}
Sprites.atlas_enabled = false
Sprites.atlas = nil
Sprites.map = {
  cat={0,0,16,16}, slug={16,0,16,12}, ghost={32,0,16,16}, coin={48,0,8,12},
  key={56,0,12,8}, spring={68,0,16,8}, box={84,0,16,16}, door={100,0,16,24}
}
function Sprites.load()
  Sprites.atlas = Engine.load_image("assets/sprite_atlas.png")
  Sprites.atlas_enabled = Sprites.atlas ~= nil and Engine.has_images
end
function Sprites.draw(name,x,y)
  if not Sprites.atlas_enabled then return false end
  local r=Sprites.map[name]; if not r then return false end
  if not Engine.image_region(Sprites.atlas,r[1],r[2],r[3],r[4],x,y) then Sprites.atlas_enabled=false; return false end
  return true
end
