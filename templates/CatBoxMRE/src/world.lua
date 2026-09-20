WorldMap = WorldMap or {}

WorldMap.worlds = {
  {name="GREEN HILLS", first=1,  last=7,  theme="meadow", accent=0x5FC875, boss="MOSS KING", tagline="Sunny paths and soft grass."},
  {name="MOVING SKIES",first=8, last=13, theme="moving", accent=0x72C6EA, boss="PICNIC BRUTE", tagline="Machines, lifts and shifting routes."},
  {name="GHOST GARDEN",first=14,last=19, theme="ghost", accent=0xA78AD8, boss="PHANTOM KEEPER", tagline="Hidden ledges and haunted air."},
  {name="CAT TOWER",first=20,last=26, theme="tower", accent=0xE3B95C, boss="SKY WARDEN", tagline="Climb above the clouds."},
}

WorldMap.node_xy = {
  {26,210},{62,179},{99,208},{137,172},{176,205},{207,170},{146,238}
}

WorldMap.secret_levels = {3,10,17,24}

function WorldMap.world_for_level(level)
  for i=1,#WorldMap.worlds do
    local w=WorldMap.worlds[i]
    if level>=w.first and level<=w.last then return i,w end
  end
  return 1,WorldMap.worlds[1]
end

function WorldMap.clamp_level(level, unlocked)
  local max=math.max(1,math.min(unlocked or 1,#StageData.stages))
  if level<1 then return max end
  if level>max then return 1 end
  return level
end

function WorldMap.next_unlocked(level, dir, unlocked)
  local max=math.max(1,math.min(unlocked or 1,#StageData.stages))
  local n=level+(dir or 1)
  if n<1 then n=max end
  if n>max then n=1 end
  return n
end

function WorldMap.world_star_total(world_i)
  local w=WorldMap.worlds[world_i]
  if not w then return 0 end
  local total=0
  for i=w.first,w.last do total=total+(Save.get_star(i) or 0) end
  return total
end

function WorldMap.world_secret_total(world_i)
  local w=WorldMap.worlds[world_i]
  if not w then return 0 end
  local total=0
  for i=w.first,w.last do total=total+(Save.get_secret(i) or 0) end
  return total
end

function WorldMap.world_max_stars(world_i)
  local w=WorldMap.worlds[world_i]
  if not w then return 0 end
  return (w.last-w.first+1)*3
end

function WorldMap.world_completion(world_i)
  local max=WorldMap.world_max_stars(world_i)
  if max<=0 then return 0 end
  return math.floor((WorldMap.world_star_total(world_i)*100)/max)
end

function WorldMap.total_stars()
  local total=0
  for i=1,#StageData.stages do total=total+(Save.get_star(i) or 0) end
  return total
end

function WorldMap.is_boss_level(level)
  local s=StageData.stages[level]
  return s and s.boss~=nil
end

function WorldMap.is_secret_level(level)
  local s=StageData.stages[level]
  return s and s.secret~=nil
end
