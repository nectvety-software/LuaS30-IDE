Game = Game or {}
local G=Game
local abs=math.abs
local sin=math.sin
local cos=math.cos
local floor=math.floor

G.state="splash"
G.level_i=1
G.map_level=1
G.camera_x=0
G.coins=0
G.level_coins=0
G.level_hits=0
G.lives=3
G.has_key=false
G.gc_timer=0
G.splash_t=0
G.menu_index=1
G.input_lock=0
G.active_checkpoint=0
G.level_clear_timer=0
G.earned_stars=0
G.intro_t=0
G.secret_inside=false
G.secret_banner=0
G.dialog={active=false,npc=0,line=1}
G.boss=nil

G.enemies={}
G.boxes={}
G.fx={}
G.bs={}
G.movers={}
G.crumbles={}
G.coin_alive={}
G.key_alive={}
G.switch_on={}
G.ecount=0
G.fxcount=0

for i=1,6 do
  G.enemies[i]={active=false,kind="slug",x=0,y=0,w=16,h=16,vx=0,vy=0,origin=0,range=0,t=0,dir=1,base_y=0}
end
for i=1,4 do
  G.boxes[i]={active=false,x=0,y=0,w=28,h=32,vx=0,vy=0}
end
for i=1,12 do
  G.fx[i]={active=false,kind="spark",t=0,max=0.3,x=0,y=0,vx=0,vy=0,color=0xFFFFFF,w=2,h=2}
end
for i=1,4 do G.bs[i]={active=false,k=0,t=0,x=0,y=0,vx=0,vy=0,w=8,h=8,s=0} end

G.p={
  x=20,y=220,w=16,h=16,vx=0,vy=0,on_ground=false,coyote=0,jump_buf=0,inv=0,
  checkpoint_x=20,checkpoint_y=220,dir=1,pose="idle",anim_t=0,step_t=0,
  standing_mover=nil,step_emit=0,checkpoint_id=0
}

local prev={
  jump=false,pause=false,dbg=false,page=false,gc=false,restart=false,
  menu_up=false,menu_down=false,confirm=false,back=false,left=false,right=false,
  map_up=false,map_down=false,talk=false,secret=false
}

local function hit(ax,ay,aw,ah,bx,by,bw,bh)
  return ax<bx+bw and ax+aw>bx and ay<by+bh and ay+ah>by
end

local function pressed(name,now)
  local v=now and not prev[name]
  prev[name]=now
  return v
end

local function fx_spawn(kind,x,y,vx,vy,color,life,w,h)
  for i=1,#G.fx do
    local f=G.fx[i]
    if not f.active then
      f.active=true
      f.kind=kind or "spark"
      f.x=x or 0
      f.y=y or 0
      f.vx=vx or 0
      f.vy=vy or 0
      f.color=color or 0xFFFFFF
      f.t=0
      f.max=life or 0.35
      f.w=w or 2
      f.h=h or 2
      return f
    end
  end
  return nil
end

local function fx_burst(x,y,count,color,speed,life)
  count=count or 4
  speed=speed or 34
  life=life or 0.30
  for i=1,count do
    local a=(i/count)*6.28318
    fx_spawn("spark",x,y,cos(a)*speed,(sin(a)*speed)-12,color,life,2,2)
  end
end

local function gate_open(id)
  return G.switch_on[id]==true
end

local function solid_iter(cb)
  local st=G.st
  for i=1,#st.solids do
    local r=st.solids[i]
    cb(r[1],r[2],r[3],r[4],nil)
  end
  for i=1,#G.movers do
    local m=G.movers[i]
    cb(m.x,m.y,m.w,m.h,m)
  end
  for i=1,#G.crumbles do
    local c=G.crumbles[i]
    if c.active then cb(c.x,c.y,c.w,c.h,c) end
  end
  for i=1,#st.gates do
    local d=st.gates[i]
    if not gate_open(d[5]) then cb(d[1],d[2],d[3],d[4],nil) end
  end
  if G.boss and G.boss.engaged and not G.boss.dead then
    cb(G.boss.arena_l-10,24,10,236,nil)
  end
end

local function reset_runtime_level(i)
  if i<1 then i=1 end
  if i>#StageData.stages then i=#StageData.stages end
  G.level_i=i
  G.map_level=i
  G.st=StageData.stages[i]
  G.goal=G.st.goal
  G.camera_x=0
  G.has_key=false
  G.state="play"
  G.input_lock=0.18
  G.level_clear_timer=0
  G.active_checkpoint=0
  G.level_coins=0
  G.level_hits=0
  G.earned_stars=0
  G.intro_t=0.85
  G.switch_on={}
  G.secret_inside=false
  G.secret_banner=0
  G.dialog.active=false
  G.dialog.npc=0
  G.dialog.line=1
  G.boss=nil
  if G.st.boss then
    local b=G.st.boss
    G.boss={
      kind=b[1],name=b[2],x=b[3],y=b[4],base_x=b[3],base_y=b[4],
      arena_l=b[5],arena_r=b[6],hp=b[7],max_hp=b[7],
      w=28,h=24,vx=0,vy=0,t=0,attack_t=0,attack=0,phase=1,
      dir=-1,engaged=false,dead=false,inv=0,sp=2.4,warn=0,skill=1,cut=0,word=0
    }
  end

  local p=G.p
  p.x=G.st.spawn[1]
  p.y=G.st.spawn[2]
  p.vx=0
  p.vy=0
  p.inv=0
  p.on_ground=false
  p.coyote=0
  p.jump_buf=0
  p.checkpoint_x=p.x
  p.checkpoint_y=p.y
  p.dir=1
  p.pose="idle"
  p.anim_t=0
  p.step_t=0
  p.step_emit=0
  p.standing_mover=nil
  p.checkpoint_id=0

  G.coin_alive={}
  for n=1,#G.st.coins do G.coin_alive[n]=true end
  G.key_alive={}
  for n=1,#G.st.keys do G.key_alive[n]=true end

  for n=1,#G.enemies do G.enemies[n].active=false end
  for n=1,#G.st.enemies do
    local d=G.st.enemies[n]
    local e=G.enemies[n]
    e.active=true
    e.kind=d[1]
    e.x=d[2]
    e.y=d[3]
    e.base_y=d[3]
    e.origin=d[2]
    e.range=d[4]
    e.vx=(d[1]=="slug") and 26 or 0
    e.vy=0
    e.t=n*0.7
    e.dir=1
  end

  for n=1,#G.boxes do G.boxes[n].active=false end
  for n=1,#G.st.boxes do
    local d=G.st.boxes[n]
    local b=G.boxes[n]
    b.active=true
    b.x=d[1]
    b.y=d[2]
    b.w=d[3]
    b.h=d[4]
    b.vx=0
    b.vy=0
  end

  G.movers={}
  for n=1,#G.st.movers do
    local d=G.st.movers[n]
    G.movers[n]={
      x=d[1],y=d[2],w=d[3],h=d[4],axis=d[5],range=d[6],speed=d[7],
      ox=d[1],oy=d[2],phase=n*0.9,dx=0,dy=0,active=true,carry=true
    }
  end

  G.crumbles={}
  for n=1,#G.st.crumbles do
    local d=G.st.crumbles[n]
    G.crumbles[n]={
      x=d[1],y=d[2],w=d[3],h=d[4],delay=d[5] or 0.5,respawn=d[6] or 2.0,
      timer=0,respawn_t=0,active=true,touch=false,crumble=true
    }
  end

  for n=1,#G.fx do G.fx[n].active=false end
  for n=1,#G.bs do G.bs[n].active=false end
  Save.data.last_level=i
  Save.write()
  collectgarbage("collect")
end

function G.load_level(i)
  reset_runtime_level(i)
end

function G.open_world_map(level)
  G.map_level=WorldMap.clamp_level(level or Save.data.last_level,Save.data.unlocked)
  G.state="worldmap"
  G.camera_x=0
end

local function update_movers(dt)
  local t=Engine.time_ms/1000
  for i=1,#G.movers do
    local m=G.movers[i]
    local px0,py0=m.x,m.y
    local off=sin((t+m.phase)*m.speed/60)*m.range
    if m.axis=="x" then m.x=m.ox+off else m.y=m.oy+off end
    m.dx=m.x-px0
    m.dy=m.y-py0
  end
end

local function update_crumbles(dt)
  for i=1,#G.crumbles do
    local c=G.crumbles[i]
    if c.active then
      if c.touch then
        c.timer=c.timer+dt
        if c.timer>=c.delay then
          c.active=false
          c.respawn_t=c.respawn
          c.timer=0
          fx_burst(c.x+c.w*0.5,c.y+2,5,0xE9C27A,32,0.28)
          Audio.push(240,45)
        end
      elseif c.timer>0 then
        c.timer=math.max(0,c.timer-dt*0.35)
      end
    else
      c.respawn_t=c.respawn_t-dt
      if c.respawn_t<=0 then
        c.active=true
        c.timer=0
        fx_burst(c.x+c.w*0.5,c.y+2,4,0xD8F0A0,24,0.22)
      end
    end
    c.touch=false
  end
end

local function apply_mover_carry()
  local p=G.p
  local m=p.standing_mover
  if m and m.active and m.carry then
    p.x=p.x+m.dx
    p.y=p.y+m.dy
  end
end

local function update_player_pose(dt,moving)
  local p=G.p
  p.anim_t=p.anim_t+dt
  if not p.on_ground then
    p.pose=(p.vy<0) and "jump" or "fall"
    p.step_emit=0
    return
  end
  if moving then
    p.step_t=p.step_t+dt*(1.5+abs(p.vx)/45)
    p.step_emit=p.step_emit+dt*abs(p.vx)
    if p.step_t>=0.36 then p.step_t=p.step_t-0.36 end
    if p.step_emit>40 then
      p.step_emit=0
      fx_spawn("dust",p.x+((p.dir>0) and 3 or 11),p.y+p.h-2,-p.dir*8,-6,0xD9F1BE,0.20,3,2)
    end
    if p.step_t<0.18 then p.pose="run1" else p.pose="run2" end
  else
    p.step_t=0
    p.step_emit=0
    p.pose="idle"
  end
end

local function resolve_oneways(oldy,ny)
  local p=G.p
  if p.vy<0 then return ny,nil end
  local stand=nil
  for i=1,#G.st.oneways do
    local r=G.st.oneways[i]
    local y=r[2]
    if oldy+p.h<=y+3 and hit(p.x,ny,p.w,p.h,r[1],y,r[3],r[4]) then
      ny=y-p.h
      p.vy=0
      p.on_ground=true
      stand=r
      break
    end
  end
  return ny,stand
end

local function move_player(dt)
  local p=G.p
  apply_mover_carry()

  local left=Engine.down("LEFT","4")
  local right=Engine.down("RIGHT","6")
  local jump=Engine.down("UP","5")
  if left and not right then
    p.vx=p.vx-420*dt
    p.dir=-1
  elseif right and not left then
    p.vx=p.vx+420*dt
    p.dir=1
  else
    p.vx=p.vx*(1-math.min(1,9*dt))
  end
  if p.vx>92 then p.vx=92 elseif p.vx<-92 then p.vx=-92 end

  if G.input_lock<=0 and pressed("jump",jump) then p.jump_buf=0.12 end
  p.jump_buf=math.max(0,p.jump_buf-dt)
  p.coyote=math.max(0,p.coyote-dt)

  if p.jump_buf>0 and (p.on_ground or p.coyote>0) then
    p.vy=-178
    p.on_ground=false
    p.coyote=0
    p.jump_buf=0
    p.standing_mover=nil
    Audio.jump()
    fx_spawn("dust",p.x+5,p.y+p.h-1,-10,-20,0xF4F4F4,0.18,3,2)
    fx_spawn("dust",p.x+10,p.y+p.h-1,10,-20,0xF4F4F4,0.18,3,2)
  elseif not jump and p.vy<-80 then
    p.vy=p.vy+460*dt
  end

  p.vy=p.vy+430*dt
  if p.vy>210 then p.vy=210 end

  local nx=p.x+p.vx*dt
  solid_iter(function(x,y,w,h)
    if hit(nx,p.y,p.w,p.h,x,y,w,h) then
      if p.vx>0 then nx=x-p.w elseif p.vx<0 then nx=x+w end
      p.vx=0
    end
  end)

  for i=1,#G.boxes do
    local b=G.boxes[i]
    if b.active and hit(nx,p.y,p.w,p.h,b.x,b.y,b.w,b.h) then
      local dir=(p.vx>=0) and 1 or -1
      local bx=b.x+dir*38*dt
      local blocked=false
      solid_iter(function(x,y,w,h)
        if hit(bx,b.y,b.w,b.h,x,y,w,h) then blocked=true end
      end)
      if not blocked then
        b.x=bx
        nx=p.x+p.vx*dt
        fx_spawn("dust",b.x+b.w*0.5,b.y+b.h-2,dir*5,-4,0xD5BB84,0.16,3,2)
      else
        nx=p.x
        p.vx=0
      end
    end
  end
  p.x=nx

  local oldy=p.y
  local ny=p.y+p.vy*dt
  local was_ground=p.on_ground
  local landed_mover=nil
  p.on_ground=false

  solid_iter(function(x,y,w,h,obj)
    if hit(p.x,ny,p.w,p.h,x,y,w,h) then
      if p.vy>0 and oldy+p.h<=y+4 then
        ny=y-p.h
        if not was_ground and p.vy>70 then
          fx_spawn("dust",p.x+4,ny+p.h-2,-8,-8,0xE8F4D2,0.18,3,2)
          fx_spawn("dust",p.x+11,ny+p.h-2,8,-8,0xE8F4D2,0.18,3,2)
        end
        p.vy=0
        p.on_ground=true
        if obj and obj.carry then landed_mover=obj end
        if obj and obj.crumble then obj.touch=true end
      elseif p.vy<0 and oldy>=y+h-4 then
        ny=y+h
        p.vy=0
      end
    end
  end)

  if not p.on_ground then
    local oy
    ny,oy=resolve_oneways(oldy,ny)
  end

  if was_ground and not p.on_ground then p.coyote=0.10 end
  p.y=ny
  p.standing_mover=landed_mover
  update_player_pose(dt,(left and not right) or (right and not left))
end

local function hurt()
  local p=G.p
  if p.inv>0 then return end
  G.level_hits=G.level_hits+1
  G.lives=G.lives-1
  Audio.hurt()
  p.inv=1.2
  fx_burst(p.x+8,p.y+8,6,0xFFB0A0,44,0.34)
  if G.lives<=0 then
    G.state="gameover"
    G.lives=3
  else
    p.x=p.checkpoint_x
    p.y=p.checkpoint_y
    p.vx=0
    p.vy=0
    p.standing_mover=nil
  end
end

local function bs_spawn(k,x,y,vx,vy,w,h,life)
  for i=1,#G.bs do local s=G.bs[i]; if not s.active then s.active=true;s.k=k;s.t=life;s.x=x;s.y=y;s.vx=vx;s.vy=vy;s.w=w;s.h=h;s.s=0;return end end
end

local function update_bs(dt)
  local p=G.p
  for i=1,#G.bs do local s=G.bs[i]; if s.active then
    s.t=s.t-dt; if s.t<=0 then s.active=false else
      if s.k<4 then s.x=s.x+s.vx*dt;s.y=s.y+s.vy*dt elseif s.s==0 and s.t<0.28 then s.s=1;fx_burst(s.x+4,110,5,0xEAFBFF,38,0.2) end
      if (s.k~=4 or s.s==1) and hit(p.x,p.y,p.w,p.h,s.x,s.y,s.w,s.h) then hurt(); if s.k<4 then s.active=false end end
    end
  end end
end

local function boss_special(b,p,p2)
  local cx=b.x+14; b.cut=0.65;b.warn=0
  if b.kind=="moss" then b.skill=1;b.word=1;bs_spawn(1,cx,b.base_y+18,(p.x<cx) and -105 or 105,0,14,7,1.0);Audio.push(420,55)
  elseif b.kind=="charge" then b.skill=2;b.word=2;bs_spawn(2,cx,b.base_y+20,(p.x<cx) and -145 or 145,0,18,6,0.9);Audio.push(180,65)
  elseif b.kind=="phantom" then b.skill=3;b.word=3;local dx=p.x-cx;local dy=p.y-b.y;local m=math.max(1,abs(dx)+abs(dy));bs_spawn(3,cx,b.y+8,dx/m*90,dy/m*90,10,10,2.0);Audio.push(560,45)
  else b.skill=4;b.word=4;local x=math.max(b.arena_l+8,math.min(b.arena_r-8,p.x));bs_spawn(4,x,40,0,0,12,220,0.72);Audio.push(760,45) end
  fx_burst(cx,b.y+10,p2 and 7 or 5,(b.kind=="phantom") and 0xDCCBFF or ((b.kind=="warden") and 0xBDEFFF or 0xFFD0A0),42,0.28)
end

local function update_boxes(dt)
  for i=1,#G.boxes do
    local b=G.boxes[i]
    if b.active then
      b.vy=b.vy+360*dt
      if b.vy>180 then b.vy=180 end
      local ny=b.y+b.vy*dt
      solid_iter(function(x,y,w,h)
        if hit(b.x,ny,b.w,b.h,x,y,w,h) and b.y+b.h<=y+5 and b.vy>=0 then
          ny=y-b.h
          b.vy=0
        end
      end)
      b.y=ny
    end
  end
end

local function update_enemies(dt)
  G.ecount=0
  for i=1,#G.enemies do
    local e=G.enemies[i]
    if e.active then
      G.ecount=G.ecount+1
      e.t=e.t+dt
      if e.kind=="slug" then
        e.x=e.x+e.vx*dt
        if e.x<e.origin-e.range then e.x=e.origin-e.range; e.vx=abs(e.vx) end
        if e.x>e.origin+e.range then e.x=e.origin+e.range; e.vx=-abs(e.vx) end
        e.dir=(e.vx>=0) and 1 or -1
      else
        e.x=e.origin+sin(e.t*1.4)*e.range
        e.y=e.base_y+sin(e.t*2.1)*6
      end
      local p=G.p
      if hit(p.x,p.y,p.w,p.h,e.x,e.y,e.w,e.h) then
        if p.vy>45 and p.y+p.h<e.y+9 then
          e.active=false
          p.vy=-125
          Audio.push(330,55)
          G.coins=G.coins+2
          fx_burst(e.x+8,e.y+8,5,0xFFF0B0,40,0.28)
        else
          hurt()
        end
      end
    end
  end
end

local function update_fx(dt)
  G.fxcount=0
  for i=1,#G.fx do
    local f=G.fx[i]
    if f.active then
      G.fxcount=G.fxcount+1
      f.t=f.t+dt
      if f.t>=f.max then
        f.active=false
      else
        if f.kind=="dust" then
          f.vy=f.vy+14*dt
          f.vx=f.vx*0.94
        else
          f.vy=f.vy+56*dt
        end
        f.x=f.x+f.vx*dt
        f.y=f.y+f.vy*dt
      end
    end
  end
end


local function boss_is_clear()
  return (not G.boss) or G.boss.dead
end

local function boss_defeat()
  local b=G.boss
  if not b or b.dead then return end
  b.dead=true
  b.engaged=false
  b.hp=0
  b.vx=0
  b.vy=0
  Audio.push(1040,150)
  fx_burst(b.x+b.w*0.5,b.y+b.h*0.5,12,0xFFF0A0,60,0.50)
end

local function boss_take_hit()
  local b=G.boss
  if not b or b.dead or b.inv>0 then return end
  b.hp=b.hp-1
  b.inv=0.55
  G.p.vy=-138
  Audio.push(360,70)
  fx_burst(b.x+b.w*0.5,b.y+5,7,0xFFF2B0,44,0.32)
  if b.hp<=0 then boss_defeat() end
end

local function update_boss(dt)
  local b=G.boss
  if not b or b.dead then return end
  b.t=b.t+dt
  b.attack_t=b.attack_t+dt
  b.inv=math.max(0,b.inv-dt)

  local p=G.p
  if not b.engaged then
    if p.x>b.arena_l-36 then
      b.engaged=true
      b.attack_t=0
      Audio.push(220,110)
      b.cut=0.8;b.word=1
      fx_burst(b.x+14,b.y+12,8,0xFFE2A0,40,0.35)
    else
      return
    end
  end

  local left=b.arena_l+18
  local right=b.arena_r-b.w-8
  b.cut=math.max(0,(b.cut or 0)-dt);b.sp=(b.sp or 2.4)-dt;b.warn=(b.sp<0.65) and 1 or 0
  if b.sp<=0 then boss_special(b,p,b.phase==2);b.sp=(b.phase==2) and 2.4 or 3.6 end

  if b.kind=="moss" then
    if b.attack_t>((b.hp<=1) and 1.35 or 2.2) and b.vy==0 then
      b.attack_t=0
      b.dir=(p.x>b.x) and 1 or -1
      b.vx=b.dir*54
      b.vy=-132
    end
    b.vy=b.vy+360*dt
    b.x=b.x+b.vx*dt
    b.y=b.y+b.vy*dt
    if b.y>=b.base_y then b.y=b.base_y; b.vy=0; b.vx=b.dir*26 end
    if b.x<left then b.x=left; b.dir=1; b.vx=abs(b.vx) end
    if b.x>right then b.x=right; b.dir=-1; b.vx=-abs(b.vx) end

  elseif b.kind=="charge" then
    if b.attack==1 then
      b.x=b.x+b.vx*dt
      if b.attack_t>0.72 or b.x<=left or b.x>=right then
        b.attack=0
        b.attack_t=0
        b.vx=0
      end
    else
      if b.attack_t>((b.hp<=2) and 1.05 or 1.8) then
        b.attack=1
        b.attack_t=0
        b.dir=(p.x>b.x) and 1 or -1
        b.vx=b.dir*110
        Audio.push(170,55)
      else
        b.x=b.x+sin(b.t*2.1)*7*dt
      end
    end
    if b.x<left then b.x=left end
    if b.x>right then b.x=right end

  elseif b.kind=="phantom" then
    if b.attack==1 then
      b.y=b.y+120*dt
      b.x=b.x+b.dir*42*dt
      if b.y>=218 then
        b.y=218
        b.attack=2
        b.attack_t=0
        Audio.push(260,55)
      end
    elseif b.attack==2 then
      b.y=b.y-92*dt
      if b.y<=b.base_y then
        b.y=b.base_y
        b.attack=0
        b.attack_t=0
      end
    else
      b.x=(b.arena_l+b.arena_r-b.w)*0.5+sin(b.t*1.25)*62
      b.y=b.base_y+sin(b.t*2.2)*18
      if b.attack_t>((b.hp<=2) and 1.15 or 2.0) then
        b.attack=1
        b.attack_t=0
        b.dir=(p.x>b.x) and 1 or -1
      end
    end

  else -- warden
    if b.attack==1 then
      b.x=b.x+b.vx*dt
      b.y=b.y+b.vy*dt
      if b.attack_t>0.55 then
        b.attack=0
        b.attack_t=0
        b.vx=0
        b.vy=0
      end
    else
      b.x=(b.arena_l+b.arena_r-b.w)*0.5+sin(b.t*1.35)*82
      b.y=b.base_y+sin(b.t*2.0)*34
      if b.attack_t>((b.hp<=2) and 0.95 or 1.55) then
        b.attack=1
        b.attack_t=0
        local dx=p.x-b.x
        local dy=p.y-b.y
        local mag=math.max(1,abs(dx)+abs(dy))
        b.vx=dx/mag*160
        b.vy=dy/mag*160
        Audio.push(300,45)
      end
    end
  end

  if hit(p.x,p.y,p.w,p.h,b.x,b.y,b.w,b.h) then
    if p.vy>38 and p.y+p.h<b.y+10 and b.inv<=0 then
      boss_take_hit()
    elseif b.inv<=0 then
      hurt()
    end
  end
end

local function npc_near_index()
  if not G.st or not G.st.npcs then return 0 end
  local p=G.p
  for i=1,#G.st.npcs do
    local n=G.st.npcs[i]
    if abs((p.x+p.w*0.5)-n[1])<28 and abs((p.y+p.h)-n[2])<32 then return i end
  end
  return 0
end

local function handle_dialog(back)
  local confirm=Engine.down("5","ENTER")
  if G.dialog.active then
    prev.jump=confirm
    if pressed("talk",confirm) then
      local n=G.st.npcs[G.dialog.npc]
      G.dialog.line=G.dialog.line+1
      if not n or G.dialog.line>5 or n[G.dialog.line+3]==nil then
        G.dialog.active=false
        G.dialog.npc=0
        G.dialog.line=1
      else
        Audio.push(680,18)
      end
    elseif pressed("back",back) then
      G.dialog.active=false
      G.dialog.npc=0
      G.dialog.line=1
    end
    return true
  end

  local ni=npc_near_index()
  if ni>0 and pressed("talk",confirm) then
    prev.jump=confirm
    G.dialog.active=true
    G.dialog.npc=ni
    G.dialog.line=1
    Audio.push(700,25)
    return true
  end
  return false
end

local function handle_secret()
  local s=G.st.secret
  if not s then return false end
  local p=G.p
  local down=Engine.down("DOWN","8")
  local near_entry=hit(p.x,p.y,p.w,p.h,s[1]-8,s[2]-28,28,34)
  local near_exit=hit(p.x,p.y,p.w,p.h,s[5]-8,s[6]-28,28,34)

  if pressed("secret",down) then
    if (not G.secret_inside) and near_entry then
      G.secret_inside=true
      G.secret_banner=1.25
      p.x=s[3]
      p.y=s[4]
      p.vx=0
      p.vy=0
      p.standing_mover=nil
      G.camera_x=math.max(0,p.x-84)
      Audio.push(820,70)
      fx_burst(p.x+8,p.y+8,8,0xBEEFFF,42,0.35)
      return true
    elseif G.secret_inside and near_exit then
      G.secret_inside=false
      p.x=s[7]
      p.y=s[8]
      p.vx=0
      p.vy=0
      p.standing_mover=nil
      G.camera_x=math.max(0,p.x-84)
      Audio.push(620,70)
      fx_burst(p.x+8,p.y+8,6,0xD8F6FF,36,0.28)
      return true
    end
  end

  if G.secret_inside and Save.get_secret(G.level_i)==0 then
    if hit(p.x,p.y,p.w,p.h,s[9]-6,s[10]-8,14,16) then
      Save.set_secret(G.level_i,1)
      Save.write()
      G.coins=G.coins+5
      Audio.push(1180,120)
      fx_burst(s[9],s[10],10,0xA8F4FF,52,0.44)
    end
  end
  return false
end

local function activate_switches()
  local p=G.p
  for i=1,#G.st.switches do
    local s=G.st.switches[i]
    local id=s[3]
    if not G.switch_on[id] and hit(p.x,p.y,p.w,p.h,s[1]-4,s[2]-8,18,16) then
      G.switch_on[id]=true
      Audio.push(760,80)
      fx_burst(s[1]+5,s[2]-3,7,0xA8F0FF,42,0.32)
    end
  end
end

local function compute_level_stars()
  local total=#G.st.coins
  local stars=1
  if total==0 or G.level_coins*100>=total*70 then stars=2 end
  if (total==0 or G.level_coins>=total) and G.level_hits==0 then stars=3 end
  return stars
end

local function triggers()
  local p=G.p
  local st=G.st

  activate_switches()

  for i=1,#st.coins do
    if G.coin_alive[i] then
      local c=st.coins[i]
      if hit(p.x,p.y,p.w,p.h,c[1]-4,c[2]-6,8,12) then
        G.coin_alive[i]=false
        G.coins=G.coins+1
        G.level_coins=G.level_coins+1
        Audio.coin()
        fx_burst(c[1],c[2],4,0xFFE07A,32,0.22)
      end
    end
  end

  for i=1,#st.keys do
    if G.key_alive[i] then
      local c=st.keys[i]
      if hit(p.x,p.y,p.w,p.h,c[1]-6,c[2]-4,12,8) then
        G.key_alive[i]=false
        G.has_key=true
        Audio.push(980,70)
        fx_burst(c[1],c[2],5,0xFFF2A6,40,0.26)
      end
    end
  end

  for i=1,#st.springs do
    local s=st.springs[i]
    if p.vy>=0 and hit(p.x,p.y,p.w,p.h,s[1],s[2],s[3],s[4]) then
      p.vy=-s[5]
      p.y=s[2]-p.h
      p.on_ground=false
      p.standing_mover=nil
      Audio.spring()
      fx_burst(s[1]+s[3]*0.5,s[2],5,0xB5F4C2,40,0.24)
    end
  end

  for i=1,#st.hazards do
    local h=st.hazards[i]
    if hit(p.x,p.y,p.w,p.h,h[2],h[3],h[4],h[5]) then hurt() end
  end

  for i=1,#st.checkpoints do
    local c=st.checkpoints[i]
    if abs(p.x-c[1])<18 then
      p.checkpoint_x=c[1]
      p.checkpoint_y=c[2]
      p.checkpoint_id=i
      if G.active_checkpoint~=i then
        G.active_checkpoint=i
        Audio.push(690,45)
        fx_burst(c[1]+4,c[2]-10,5,0xFFF2A6,30,0.26)
      end
    end
  end

  if p.y>330 then hurt() end

  if hit(p.x,p.y,p.w,p.h,G.goal[1],G.goal[2],22,44) and (not st.need_key or G.has_key) and boss_is_clear() then
    G.state="clear"
    G.level_clear_timer=0
    G.earned_stars=compute_level_stars()
    Audio.clear()
    fx_burst(G.goal[1]+8,G.goal[2]+10,8,0xFFF2A6,48,0.40)
    if G.level_i>=Save.data.unlocked then
      Save.data.unlocked=math.min(#StageData.stages,G.level_i+1)
    end
    Save.set_star(G.level_i,G.earned_stars)
    Save.data.last_level=math.min(Save.data.unlocked,G.level_i+1)
    if G.coins>Save.data.best_coins then Save.data.best_coins=G.coins end
    Save.write()
  end
end

local function handle_worldmap(back)
  local left=Engine.down("LEFT","4")
  local right=Engine.down("RIGHT","6")
  local up=Engine.down("UP","2")
  local down=Engine.down("DOWN","8")

  if pressed("left",left) then
    G.map_level=WorldMap.next_unlocked(G.map_level,-1,Save.data.unlocked)
    Audio.push(620,20)
  end
  if pressed("right",right) then
    G.map_level=WorldMap.next_unlocked(G.map_level,1,Save.data.unlocked)
    Audio.push(620,20)
  end

  if pressed("map_up",up) then
    local wi=WorldMap.world_for_level(G.map_level)
    wi=wi-1
    if wi<1 then wi=#WorldMap.worlds end
    local w=WorldMap.worlds[wi]
    if w.first<=Save.data.unlocked then G.map_level=w.first end
  end

  if pressed("map_down",down) then
    local wi=WorldMap.world_for_level(G.map_level)
    wi=wi+1
    if wi>#WorldMap.worlds then wi=1 end
    local w=WorldMap.worlds[wi]
    if w.first<=Save.data.unlocked then G.map_level=w.first end
  end

  if pressed("confirm",Engine.down("5","ENTER")) then
    if G.map_level<=Save.data.unlocked then G.load_level(G.map_level) end
  elseif pressed("back",back) then
    G.state="menu"
  end
end

function G.update(dt)
  if dt>0.10 then dt=0.10 end
  Engine.time_ms=Engine.time_ms+dt*1000
  DebugUI.update(dt)
  Audio.update(dt)
  update_fx(dt)

  if G.input_lock>0 then G.input_lock=math.max(0,G.input_lock-dt) end
  if G.intro_t>0 then G.intro_t=math.max(0,G.intro_t-dt) end
  if G.secret_banner>0 then G.secret_banner=math.max(0,G.secret_banner-dt) end
  local back=Engine.down("SOFTRIGHT","BACK")

  if G.state=="splash" then
    G.splash_t=G.splash_t+dt
    if G.splash_t>=1.2 or pressed("confirm",Engine.down("5","ENTER")) then G.state="menu" end
    return
  end

  if G.state=="menu" then
    local up=Engine.down("UP","2")
    local down=Engine.down("DOWN","8")
    if pressed("menu_up",up) then
      G.menu_index=G.menu_index-1
      if G.menu_index<1 then G.menu_index=5 end
      Audio.push(620,25)
    end
    if pressed("menu_down",down) then
      G.menu_index=G.menu_index+1
      if G.menu_index>5 then G.menu_index=1 end
      Audio.push(620,25)
    end
    if pressed("confirm",Engine.down("5","ENTER")) then
      if G.menu_index==1 or G.menu_index==2 then
        G.open_world_map(Save.data.last_level)
      elseif G.menu_index==3 then
        G.state="settings"
      elseif G.menu_index==4 then
        G.state="about"
      else
        Engine.exit()
      end
    end
    return
  end

  if G.state=="worldmap" then
    handle_worldmap(back)
    return
  end

  if G.state=="settings" then
    if pressed("confirm",Engine.down("5","ENTER")) then
      Audio.enabled=not Audio.enabled
      Save.data.sound=Audio.enabled and 1 or 0
      Save.write()
    end
    if pressed("back",back) then G.state="menu" end
    return
  end

  if G.state=="about" then
    if pressed("back",back) or pressed("confirm",Engine.down("5","ENTER")) then G.state="menu" end
    return
  end

  if G.state=="play" then
    if handle_dialog(back) then return end
    if handle_secret() then return end
  end

  local pa=Engine.down("SOFTLEFT","P")
  if pressed("pause",pa) then
    G.state=(G.state=="pause") and "play" or ((G.state=="play") and "pause" or G.state)
  end
  local db=Engine.down("#")
  if pressed("dbg",db) then DebugUI.on=not DebugUI.on end
  local pg=Engine.down("*")
  if pressed("page",pg) then DebugUI.page=DebugUI.page%2+1 end
  local gc=Engine.down("9")
  if pressed("gc",gc) then DebugUI.fullgc() end
  local rs=Engine.down("0")
  if pressed("restart",rs) then G.load_level(G.level_i); return end

  if G.state=="pause" then
    if pressed("confirm",Engine.down("5","ENTER")) then
      G.state="play"
    elseif pressed("back",back) then
      G.open_world_map(G.level_i)
    end
    return
  end

  if G.state=="clear" then
    G.level_clear_timer=G.level_clear_timer+dt
    if pressed("confirm",Engine.down("5","ENTER")) then
      G.open_world_map(Save.data.last_level)
    elseif pressed("restart",Engine.down("0")) then
      G.load_level(G.level_i)
    elseif pressed("back",back) then
      G.open_world_map(G.level_i)
    end
    return
  end

  if G.state=="gameover" then
    if pressed("confirm",Engine.down("5","ENTER")) then
      G.load_level(G.level_i)
    elseif pressed("back",back) then
      G.open_world_map(G.level_i)
    end
    return
  end

  G.p.inv=math.max(0,G.p.inv-dt)
  update_movers(dt)
  move_player(dt)
  update_boxes(dt)
  update_enemies(dt)
  update_boss(dt)
  update_bs(dt)
  triggers()
  update_crumbles(dt)

  local target=G.p.x-84
  if target<0 then target=0 end
  local max=math.max(0,G.st.width-240)
  if target>max then target=max end
  G.camera_x=G.camera_x+(target-G.camera_x)*math.min(1,6*dt)

  G.gc_timer=G.gc_timer+dt
  if G.gc_timer>1.5 then
    G.gc_timer=0
    DebugUI.gcstep()
  end
end

function G.draw()
  Render.draw(G)
end

function G.init()
  Engine.init()
  pcall(collectgarbage,"setpause",110)
  pcall(collectgarbage,"setstepmul",400)
  collectgarbage("collect")
  Sprites.load()
  Save.load()
  G.level_i=math.min(Save.data.last_level,#StageData.stages)
  G.map_level=G.level_i
  G.state="splash"
  G.splash_t=0
end
