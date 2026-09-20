Save = Save or {}
Save.path="catbox.sav"
Save.data={unlocked=1,best_coins=0,sound=1,debug=0,last_level=1}
Save.stars={}
Save.secrets={}
for i=1,26 do
  Save.stars[i]=0
  Save.secrets[i]=0
end

local function parse(s)
  if type(s)~="string" then return end
  for line in string.gmatch(s,"[^\r\n]+") do
    local k,v=string.match(line,"^([%w_]+)=([%-%d]+)$")
    if k and v then
      local n=tonumber(v)
      local si=string.match(k,"^star_(%d+)$")
      local hi=string.match(k,"^secret_(%d+)$")
      if si then
        si=tonumber(si)
        if si and si>=1 and si<=26 then Save.stars[si]=math.max(0,math.min(3,n or 0)) end
      elseif hi then
        hi=tonumber(hi)
        if hi and hi>=1 and hi<=26 then Save.secrets[hi]=(n and n~=0) and 1 or 0 end
      elseif Save.data[k]~=nil then
        Save.data[k]=n or Save.data[k]
      end
    end
  end
end

function Save.load()
  parse(Engine.file_read(Save.path))
  Audio.enabled=Save.data.sound~=0
  if Save.data.unlocked<1 then Save.data.unlocked=1 end
  if Save.data.unlocked>26 then Save.data.unlocked=26 end
  if Save.data.last_level<1 then Save.data.last_level=1 end
  if Save.data.last_level>Save.data.unlocked then Save.data.last_level=Save.data.unlocked end
end

function Save.get_star(level)
  return Save.stars[level] or 0
end

function Save.set_star(level,value)
  if level<1 or level>26 then return end
  value=math.max(0,math.min(3,value or 0))
  if value>(Save.stars[level] or 0) then Save.stars[level]=value end
end

function Save.get_secret(level)
  return Save.secrets[level] or 0
end

function Save.set_secret(level,value)
  if level<1 or level>26 then return end
  Save.secrets[level]=(value and value~=0) and 1 or 0
end

function Save.total_stars()
  local n=0
  for i=1,26 do n=n+(Save.stars[i] or 0) end
  return n
end

function Save.total_secrets()
  local n=0
  for i=1,26 do n=n+(Save.secrets[i] or 0) end
  return n
end

function Save.write()
  local s="unlocked="..Save.data.unlocked..
    "\nbest_coins="..Save.data.best_coins..
    "\nsound="..(Audio.enabled and 1 or 0)..
    "\ndebug="..Save.data.debug..
    "\nlast_level="..Save.data.last_level.."\n"
  for i=1,26 do
    s=s.."star_"..i.."="..(Save.stars[i] or 0).."\n"
    s=s.."secret_"..i.."="..(Save.secrets[i] or 0).."\n"
  end
  Engine.file_write(Save.path,s)
end
