Audio = Audio or {}
Audio.enabled=true; Audio.q={}; Audio.head=1; Audio.tail=1; Audio.count=0; Audio.cap=4; Audio.cool=0
for i=1,Audio.cap do Audio.q[i]={f=0,ms=0} end
function Audio.push(f,ms)
  if not Audio.enabled or Audio.count>=Audio.cap then return end
  local e=Audio.q[Audio.tail]; e.f=f; e.ms=ms; Audio.tail=Audio.tail%Audio.cap+1; Audio.count=Audio.count+1
end
function Audio.update(dt)
  if not Audio.enabled then return end
  if Audio.cool>0 then Audio.cool=Audio.cool-dt; return end
  if Audio.count>0 then
    local e=Audio.q[Audio.head]
    if not Engine.play_tone(e.f,e.ms) then Audio.enabled=false; return end
    Audio.head=Audio.head%Audio.cap+1; Audio.count=Audio.count-1; Audio.cool=(e.ms/1000)+0.02
  end
end
function Audio.coin() Audio.push(880,45) end
function Audio.jump() Audio.push(520,35) end
function Audio.hurt() Audio.push(180,90) end
function Audio.spring() Audio.push(740,70) end
function Audio.clear() Audio.push(1040,120) end
