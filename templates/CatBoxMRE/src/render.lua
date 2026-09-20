Render = Render or {}
local floor=math.floor
local abs=math.abs
local sin=math.sin

local function sx(g,x) return floor(x-g.camera_x) end
local function px(x,y,w,h,c) if w>0 and h>0 then Engine.rect(x,y,w,h,c) end end

local THEMES = {
  meadow={sky=0x82CFFF, far=0xA4E7AE, mid=0x82D98D, near=0x63C875, ground=0xF6B45B, top=0x56C864, sun=0xFFE48A, flower=0xFFF4A0},
  moving={sky=0x86D0FE, far=0xA9E8B1, mid=0x8BDA92, near=0x66C97A, ground=0xF6B45B, top=0x56C864, sun=0xFFE58D, flower=0xDFF6FF},
  ghost={sky=0x8CCAF4, far=0xAFDEB2, mid=0x89CF91, near=0x61B977, ground=0xF1B15A, top=0x59C767, sun=0xFFF0A8, flower=0xEEDFFF},
  danger={sky=0x8ACAF9, far=0xA8E19F, mid=0x81D184, near=0x5FC06F, ground=0xF0B15A, top=0x59C766, sun=0xFFD97A, flower=0xFFD0A0},
  bubble={sky=0x8FD5FF, far=0xB3ECB7, mid=0x91DEA0, near=0x70CD83, ground=0xF7B75E, top=0x5DCB72, sun=0xFFF3B7, flower=0xD8F8FF},
  tower={sky=0x84CBFF, far=0xA6E2A6, mid=0x82D18B, near=0x62BF75, ground=0xF3B35C, top=0x59C868, sun=0xFFE28C, flower=0xFFF0A4},
  cloud={sky=0x92D9FF, far=0xB7EDBD, mid=0x95E2A3, near=0x76D18A, ground=0xF7BA64, top=0x61CD79, sun=0xFFF1B0, flower=0xF5FCFF},
  boxland={sky=0x8CCFFF, far=0xA8E5AB, mid=0x86D58C, near=0x64C277, ground=0xF3B45B, top=0x58C866, sun=0xFFE28C, flower=0xFFE7A0}
}

local function theme_for_name(name)
  return THEMES[name] or THEMES.meadow
end

local function get_theme(g)
  if g and g.st and g.st.theme then return theme_for_name(g.st.theme) end
  return THEMES.meadow
end

local function draw_cloud(x,y,scale)
  scale=scale or 1
  local h=4*scale
  px(x+4*scale,y+4*scale,22*scale,h,0xFFFFFF)
  px(x+9*scale,y,12*scale,8*scale,0xFFFFFF)
  px(x+18*scale,y+4*scale,12*scale,h,0xFFFFFF)
end

local function draw_hill(x,base,w,h,color)
  local step=8
  local rows=floor(h/step)
  for i=0,rows do
    local yy=base-i*step
    local inset=floor((i/rows)*(w*0.44))
    px(x+inset,yy,w-inset*2,step,color)
  end
end

local function draw_bush(x,y,w,h,c1,c2)
  c1=c1 or 0x51C86B
  c2=c2 or 0x73E38B
  px(x,y+6,w,h-6,c1)
  px(x+3,y+2,w-6,10,c2)
  px(x+5,y+8,2,2,0x2F8E46)
  px(x+w-8,y+9,2,2,0x2F8E46)
end

local function draw_sun(x,y,c)
  px(x+4,y,10,2,c)
  px(x+2,y+2,14,10,c)
  px(x+4,y+12,10,2,c)
end

local function draw_flower(x,y,c)
  px(x+2,y+2,1,4,0x2E934A)
  px(x,y,2,2,c)
  px(x+3,y,2,2,c)
  px(x+1,y+1,3,2,0xFFF7CC)
end

function Render.background(g)
  local t=get_theme(g)
  Engine.clear(t.sky)
  draw_sun(190-floor(g.camera_x*0.015)%8,18,t.sun)

  local p1=floor(g.camera_x*0.05)%120
  local p2=floor(g.camera_x*0.11)%150
  local p3=floor(g.camera_x*0.18)%170
  draw_hill(-70-p1,242,180,112,t.far)
  draw_hill(80-p1,242,190,128,t.far)
  draw_hill(-100-p2,246,210,102,t.mid)
  draw_hill(90-p2,246,220,118,t.mid)
  draw_hill(-90-p3,250,210,90,t.near)
  draw_hill(110-p3,250,220,100,t.near)

  for i=0,4 do
    draw_cloud(18+i*66-(floor(g.camera_x*0.07)%66),34+(i%2)*18,1)
  end

  px(0,240,240,80,0x9BE89F)
  for i=0,7 do
    local x=i*38-(floor(g.camera_x*0.22)%38)
    draw_bush(x,228+(i%2)*2,20,12)
  end
  for i=0,8 do
    local x=i*31-(floor(g.camera_x*0.28)%31)
    draw_flower(x+5,250+(i%2)*6,t.flower)
  end
end

local function platform_checker(x,y,w,h,fill,top)
  px(x,y,w,h,fill)
  px(x,y,w,4,top)
  px(x,y+4,w,2,0xA9E77B)
  local yy=y+7
  local row=0
  while yy<y+h do
    local xx=x+((row%2==0) and 0 or 8)
    while xx<x+w do
      px(xx,yy,8,8,0xF8D77D)
      xx=xx+16
    end
    row=row+1
    yy=yy+8
  end
end

function Render.platform(g,r,is_mover)
  local t=get_theme(g)
  local x=sx(g,r[1])
  local y=r[2]+24
  local w=r[3]
  local h=r[4]
  if x+w<0 or x>240 then return end
  platform_checker(x,y,w,h,is_mover and 0xE7BF6A or t.ground,is_mover and 0x88E8A4 or t.top)
  if is_mover then
    px(x+4,y+h-4,w-8,2,0x8F6A48)
    px(x+6,y+7,3,3,0xFFF0A3)
    px(x+w-9,y+7,3,3,0xFFF0A3)
  end
end

function Render.oneway(g,r)
  local x=sx(g,r[1])
  local y=r[2]+24
  if x+r[3]<0 or x>240 then return end
  px(x,y,r[3],r[4],0x75D889)
  px(x,y,r[3],2,0xC3F2A9)
  for i=4,r[3]-4,8 do px(x+i,y+r[4]-2,4,2,0x4DAF67) end
end

function Render.crumble(g,c)
  if not c.active then return end
  local x=sx(g,c.x)
  local y=c.y+24
  if x+c.w<0 or x>240 then return end
  local blink=(c.timer>c.delay*0.65) and (floor(Engine.time_ms/80)%2==0)
  local fill=blink and 0xFFD990 or 0xE7B96B
  px(x,y,c.w,c.h,fill)
  px(x,y,c.w,2,0x7ED88C)
  for i=4,c.w-4,10 do
    px(x+i,y+4,4,2,0xA97A45)
    px(x+i+2,y+7,2,2,0x8D653E)
  end
end

function Render.switch(g,s)
  local x=sx(g,s[1])
  local y=s[2]+24
  local on=g.switch_on[s[3]]==true
  px(x-2,y-4,14,8,0x6D6F79)
  px(x,y-7,10,5,on and 0x64D889 or 0xF0A85A)
  px(x+3,y-9,4,2,on and 0xB9F7C5 or 0xFFE4A0)
end

function Render.gate(g,d)
  if g.switch_on[d[5]] then return end
  local x=sx(g,d[1])
  local y=d[2]+24
  if x+d[3]<0 or x>240 then return end
  px(x,y,d[3],d[4],0x596174)
  px(x+3,y,d[3]-6,d[4],0x7F899E)
  local yy=y+4
  while yy<y+d[4] do
    px(x+2,yy,d[3]-4,2,0xB2BDCC)
    yy=yy+9
  end
end

function Render.coin(g,x,y)
  local t=Engine.time_ms*0.012+x*0.1
  local bob=sin(t)*1.5
  local phase=floor(t)%4
  local w=(phase==0 and 2) or (phase==1 and 4) or 6
  x=sx(g,x)
  y=y+24+bob
  if x<-10 or x>250 then return end
  px(x-floor(w/2),y-5,w,10,0xFFD85A)
  if w>=4 then px(x-1,y-3,2,6,0xFFF2A6) end
end

function Render.key(g,x,y)
  local t=Engine.time_ms*0.010+x*0.12
  local bob=sin(t)*1.0
  x=sx(g,x)
  y=y+24+bob
  if x<-14 or x>250 then return end
  px(x-6,y-2,9,4,0xF6D04D)
  px(x+2,y-4,5,8,0xF6D04D)
  if floor(Engine.time_ms/180)%4==0 then
    px(x+7,y-8,2,2,0xFFF6C5)
    px(x+10,y-5,1,1,0xFFFFFF)
  end
end

local function draw_cat_proc(p,x,y)
  local pose=p.pose or "idle"
  local dir=p.dir or 1
  local blink=floor(Engine.time_ms/220)%10==0
  local body_y=y+6
  local body_h=8
  local leg_y=y+13
  local leg1_x=x+4
  local leg2_x=x+10
  local tail_x=(dir>0) and (x+1) or (x+13)

  px(x+4,y+15,9,1,0x4A7659) -- tiny shadow

  if pose=="run1" then
    body_y=y+7
    leg1_x=x+3
    leg2_x=x+11
  elseif pose=="run2" then
    body_y=y+6
    leg_y=y+14
    leg1_x=x+5
    leg2_x=x+9
  elseif pose=="jump" then
    body_y=y+5
    leg_y=y+11
    leg1_x=x+5
    leg2_x=x+9
    tail_x=(dir>0) and x or (x+14)
  elseif pose=="fall" then
    body_y=y+7
    body_h=7
    leg_y=y+14
  end

  px(tail_x,y+7,2,5,0x1A2230)
  px(x+2,body_y,12,body_h,0x1A2230)
  px(x+3,y+1,10,7,0x1A2230)
  px(x+3,y,3,3,0x1A2230)
  px(x+10,y,3,3,0x1A2230)
  px(leg1_x,leg_y,2,3,0x111824)
  px(leg2_x,leg_y,2,3,0x111824)

  -- white muzzle and eyes
  px(x+6,y+7,4,3,0xEAEFF5)
  if not blink then
    if dir>0 then
      px(x+7,y+4,1,2,0xF5F5F5)
      px(x+11,y+4,1,2,0xF5F5F5)
    else
      px(x+4,y+4,1,2,0xF5F5F5)
      px(x+8,y+4,1,2,0xF5F5F5)
    end
  end
  px(x+7,y+8,2,1,0xF19AB3)
end

function Render.cat(g)
  local p=g.p
  if p.inv>0 and floor(Engine.time_ms/90)%2==0 then return end
  draw_cat_proc(p,sx(g,p.x),p.y+24)
end

function Render.enemy(g,e)
  local x=sx(g,e.x)
  local y=e.y+24
  if e.kind=="ghost" then
    local bob=floor(sin(e.t*4)*1.5)
    y=y+bob
    px(x+2,y+2,12,10,0xF7F7F7)
    px(x+4,y+12,2,2,0xF7F7F7)
    px(x+8,y+12,2,2,0xF7F7F7)
    px(x+12,y+12,2,2,0xF7F7F7)
    px(x+4,y+6,2,3,0x333333)
    px(x+10,y+6,2,3,0x333333)
    px(x+6,y+10,4,1,0xFFCAD6)
  else
    local lift=(floor(e.t*10)%2==0) and 0 or 1
    y=y+4+lift
    px(x+1,y+7,14,7,0xD75E4D)
    px(x+9,y+3,5,5,0xE87362)
    if e.dir>=0 then px(x+11,y+5,1,2,0x333333) else px(x+4,y+5,1,2,0x333333) end
    px(x+4,y+13,2,1,0x7E2F24)
    px(x+10,y+13,2,1,0x7E2F24)
  end
end

function Render.box(g,b)
  local x=sx(g,b.x)
  local y=b.y+24
  px(x,y,b.w,b.h,0xC98D55)
  px(x+3,y+3,b.w-6,b.h-6,0xE8B87C)
  px(x+11,y+11,6,2,0xA56D3C)
  px(x+3,y+3,2,b.h-6,0xB67843)
  px(x+b.w-5,y+3,2,b.h-6,0xB67843)
end

function Render.hazard(g,h)
  local x=sx(g,h[2])
  local y=h[3]+24
  if x+h[4]<-16 or x>256 then return end
  if h[1]=="spike" then
    local n=floor(h[4]/8)
    for i=0,n-1 do
      px(x+i*8,y+8,2,4,0x6A7180)
      px(x+i*8+2,y+5,2,7,0x838BA0)
      px(x+i*8+4,y+2,2,10,0xA4AFC2)
    end
  else
    local pulse=(floor(Engine.time_ms/180)%2==0) and 0x5D6576 or 0x70798C
    px(x+12,y-18,6,18,0x444D63)
    px(x,y,h[4],h[5],pulse)
    px(x+6,y+h[5]-12,h[4]-12,12,0x505766)
  end
end

function Render.spring(g,s)
  local x=sx(g,s[1])
  local y=s[2]+24
  local pulse=floor(Engine.time_ms/120)%2
  px(x,y,s[3],s[4],0x4CC67B)
  px(x+3,y+2+(pulse==1 and 1 or 0),s[3]-6,3,0x9BF0B0)
  px(x+2,y+7,s[3]-4,2,0x2C8C51)
end

function Render.goal(g)
  local x=sx(g,g.goal[1])
  local y=g.goal[2]+24
  px(x,y,18,40,0xB77A4C)
  px(x+3,y+4,12,32,0xE8B67F)
  px(x+12,y+21,2,2,0x3D2E2A)
  if (g.st.need_key and not g.has_key) or (g.boss and not g.boss.dead) then
    px(x+6,y+14,6,8,(g.boss and not g.boss.dead) and 0x7B8492 or 0xD6A847)
  else
    if floor(Engine.time_ms/220)%3==0 then px(x+5,y+8,2,2,0xFFF3B8) end
  end
end

function Render.decor(g,d)
  local kind=d[1]
  local x=sx(g,d[2])
  local y=(d[3] or 0)+24
  if kind=="sign" then
    px(x+4,y-18,2,18,0x7C5C38)
    px(x,y-18,28,14,0xF7D57D)
    px(x+2,y-16,24,10,0xD97C49)
    Engine.text(x+5,y-15,"!",0xFFFFFF)
  elseif kind=="house" then
    px(x,y-14,20,14,0xF7F7F7)
    px(x+3,y-10,14,10,0xC8D7F4)
    px(x+6,y-6,4,6,0xB77A4C)
    px(x+3,y-20,14,6,0xC84B4B)
  elseif kind=="bubble" then
    local b=floor(Engine.time_ms/200)%3
    px(x,y-b,10,2,0xD4F4FF)
    px(x,y+8-b,10,2,0xD4F4FF)
    px(x,y+2-b,2,6,0xD4F4FF)
    px(x+8,y+2-b,2,6,0xD4F4FF)
  elseif kind=="fence" then
    for i=0,4 do px(x+i*6,y-10,2,10,0xF4F4F4) end
    px(x,y-8,26,2,0xF4F4F4)
    px(x,y-4,26,2,0xF4F4F4)
  elseif kind=="pipe" then
    px(x,y-10,16,10,0x53C973)
    px(x-2,y-14,20,6,0x79E48B)
  elseif kind=="bush" then
    draw_bush(x,y-10,18,12)
  end
end

function Render.checkpoint(g,c,i)
  local x=sx(g,c[1])
  local y=c[2]+24
  local active=(g.active_checkpoint==i)
  local wave=floor(Engine.time_ms/180)%2
  px(x+2,y-16,2,16,0x7C5C38)
  px(x+4,y-16,10+wave*2,6,active and 0xFFD96E or 0xD0E4F8)
  if active then px(x+6,y-10,2,2,0xFFF5C8) end
end

function Render.fx(g)
  for i=1,#g.fx do
    local f=g.fx[i]
    if f.active then
      local x=sx(g,f.x)
      local y=f.y+24
      if x>-8 and x<248 and y>-8 and y<328 then
        px(x,y,f.w,f.h,f.color)
        if f.kind=="spark" then px(x+1,y+1,1,1,0xFFF8D0) end
      end
    end
  end
end

local function draw_star(x,y,on)
  local c=on and 0xFFD85A or 0xC8BFA7
  px(x+3,y,3,2,c)
  px(x+1,y+2,7,3,c)
  px(x+2,y+5,5,2,c)
  px(x+1,y+7,2,2,c)
  px(x+6,y+7,2,2,c)
end

local function softbar(left,right)
  px(0,302,240,18,0xEED9A8)
  Engine.text(4,305,left or "",0x3A3428)
  if right then Engine.text(168,305,right,0x3A3428) end
end

function Render.ui(g)
  px(0,0,240,24,0xF8E4B7)
  Engine.text(4,4,"LEVEL "..g.level_i,0x222222)
  for i=1,3 do
    local x=58+(i-1)*10
    local c=(i<=g.lives) and 0xB9D1F4 or 0xB8C5D7
    px(x,7,6,6,c)
    px(x+1,13,4,2,c)
  end
  if g.has_key then
    Render.key(g,g.camera_x+96,-10)
  else
    px(90,8,12,8,0xD8C68D)
  end
  Render.coin(g,g.camera_x+184,-8)
  Engine.text(194,4,tostring(g.level_coins).."/"..tostring(#g.st.coins),0x222222)
end

local function draw_lock(x,y)
  px(x+3,y,6,5,0x66707A)
  px(x+1,y+4,10,8,0x89939E)
  px(x+5,y+7,2,3,0x394149)
end

local function draw_secret_badge(x,y,found)
  local c=found and 0x9FEAFF or 0x9FA8AD
  px(x+3,y,3,2,c)
  px(x+1,y+2,7,4,c)
  px(x+3,y+6,3,2,c)
  if found then px(x+4,y+2,1,1,0xFFFFFF) end
end

local function draw_crown(x,y,on)
  local c=on and 0xFFD75A or 0x9EA4A7
  px(x,y+3,12,4,c)
  px(x+1,y,2,4,c)
  px(x+5,y+1,2,3,c)
  px(x+9,y,2,4,c)
end

local function draw_world_progress(x,y,w,pct,accent)
  px(x,y,w,6,0xD7CBAA)
  local fw=floor((w*pct)/100)
  if fw>0 then px(x,y,fw,6,accent) end
  px(x,y,w,1,0xFFF5D8)
end

local function map_player_marker(x,y)
  local bob=floor(sin(Engine.time_ms*0.01)*2)
  px(x+2,y-14+bob,10,7,0x1A2230)
  px(x+2,y-16+bob,3,3,0x1A2230)
  px(x+9,y-16+bob,3,3,0x1A2230)
  px(x+5,y-11+bob,1,1,0xFFFFFF)
  px(x+9,y-11+bob,1,1,0xFFFFFF)
  px(x+6,y-8+bob,2,1,0xF19AB3)
end

local function draw_worldmap(g)
  local wi,w=WorldMap.world_for_level(g.map_level)
  local t=theme_for_name(w.theme)
  Engine.clear(t.sky)

  -- premium map backdrop
  draw_sun(194,18,t.sun)
  draw_cloud(16,38,1)
  draw_cloud(150,54,1)
  draw_hill(-80,262,190,112,t.far)
  draw_hill(80,262,205,126,t.mid)
  px(0,244,240,58,0x98E5A0)
  for i=0,6 do
    draw_bush(i*42-(floor(Engine.time_ms/500)%8),235+(i%2)*3,18,11)
  end

  -- top chrome
  px(0,0,240,42,0xF7E7BC)
  px(0,40,240,2,w.accent)
  Engine.text(8,6,"WORLD "..wi.." / "..#WorldMap.worlds,0x39414A)
  Engine.text(8,21,w.name,0x222222)
  Engine.text(176,7,WorldMap.world_star_total(wi).."/"..WorldMap.world_max_stars(wi),0x5A513D)
  draw_star(210,5,true)
  Engine.text(176,22,WorldMap.world_completion(wi).."%",0x5A513D)

  -- world card
  px(10,48,220,72,0xFFF3D1)
  px(12,50,4,68,w.accent)
  Engine.text(22,56,w.tagline,0x4E5358)
  Engine.text(22,74,"Boss: "..w.boss,0x5D5545)
  Engine.text(22,92,"Secrets: "..WorldMap.world_secret_total(wi),0x5D5545)
  Engine.text(126,92,"Up/Down: world",0x6A685E)
  draw_world_progress(22,108,190,WorldMap.world_completion(wi),w.accent)

  local count=w.last-w.first+1
  local node_y_shift=-10
  for local_i=1,count do
    local level=w.first+local_i-1
    local pos=WorldMap.node_xy[local_i]
    local x=pos[1]
    local y=pos[2]+node_y_shift

    if local_i<count then
      local np=WorldMap.node_xy[local_i+1]
      local x2=np[1]
      local y2=np[2]+node_y_shift
      local minx=math.min(x,x2)
      local miny=math.min(y,y2)
      local ww=math.max(4,abs(x2-x))
      local hh=math.max(3,abs(y2-y))
      if abs(x2-x)>abs(y2-y) then
        px(minx+8,floor((y+y2)/2),math.max(3,ww-10),3,0xD5BE80)
      else
        px(floor((x+x2)/2),miny+8,3,math.max(3,hh-8),0xD5BE80)
      end
    end

    local unlocked=level<=Save.data.unlocked
    local selected=(level==g.map_level)
    local boss=WorldMap.is_boss_level(level)
    local secret=WorldMap.is_secret_level(level)
    local node_w=boss and 22 or 18
    local node_h=boss and 20 or 18
    local nx=x-floor(node_w/2)+4
    local ny=y-floor(node_h/2)+4

    if selected then
      px(nx-5,ny-5,node_w+10,node_h+10,0xF2CB58)
      px(nx-3,ny-3,node_w+6,node_h+6,0xFFF7D7)
      map_player_marker(nx+2,ny)
    end

    if unlocked then
      px(nx,ny,node_w,node_h,boss and 0xFFE29A or 0xFFF1C6)
      px(nx+2,ny+2,node_w-4,node_h-4,boss and 0xE7B05A or 0xE9D9AE)
      if boss then
        draw_crown(nx+5,ny-7,Save.get_star(level)>0)
      else
        Engine.text(nx+4,ny+2,tostring(level),0x2B2B2B)
      end
    else
      px(nx,ny,node_w,node_h,0xA9B4B0)
      draw_lock(nx+3,ny+3)
    end

    local stars=Save.get_star(level)
    for s=1,3 do
      draw_star(nx-2+(s-1)*7,ny+node_h+2,s<=stars)
    end
    if secret then
      draw_secret_badge(nx+node_w-1,ny-8,Save.get_secret(level)==1)
    end
  end

  local st=StageData.stages[g.map_level]
  px(10,250,220,48,0xFFF2CB)
  Engine.text(18,255,"LEVEL "..g.map_level.."  "..st.name,0x222222)
  if st.boss then
    Engine.text(18,273,"BOSS STAGE",0xA65A3A)
  elseif st.secret then
    Engine.text(18,273,(Save.get_secret(g.map_level)==1) and "SECRET FOUND" or "SECRET HIDDEN",0x4B7480)
  else
    Engine.text(18,273,"Best: "..Save.get_star(g.map_level).." star(s)",0x555555)
  end
  if g.map_level==Save.data.unlocked then Engine.text(170,273,"NEW",0xC46A3A) end
  softbar("4/6 MOVE  5 PLAY","RSK BACK")
end


local NPC_COLORS={
  MIMI=0xE8B07B,
  PIP=0xB7D5F1,
  TIKO=0xE7CE72,
  LUMA=0xC9B0E8
}

function Render.npc(g,n)
  local x=sx(g,n[1])
  local y=n[2]+24-16
  if x<-20 or x>250 then return end
  local c=NPC_COLORS[n[3]] or 0xE6C18C
  px(x+3,y+6,10,9,c)
  px(x+4,y+2,8,7,c)
  px(x+4,y,3,4,c)
  px(x+9,y,3,4,c)
  px(x+6,y+5,1,2,0x2A3036)
  px(x+10,y+5,1,2,0x2A3036)
  px(x+7,y+8,2,1,0xF5D2C3)
  px(x+4,y+15,2,2,0x735B48)
  px(x+10,y+15,2,2,0x735B48)

  local p=g.p
  if abs((p.x+p.w*0.5)-n[1])<28 and abs((p.y+p.h)-n[2])<32 and not g.dialog.active then
    px(x-5,y-15,27,12,0xFFF8DA)
    Engine.text(x+2,y-13,"5 TALK",0x514C42)
  end
end

function Render.dialog(g)
  if not g.dialog.active then return end
  local n=g.st.npcs[g.dialog.npc]
  if not n then return end
  local line=n[g.dialog.line+3] or "..."
  px(8,226,224,72,0x2B3038)
  px(10,228,220,68,0xFFF1CF)
  px(16,234,54,16,NPC_COLORS[n[3]] or 0xE6C18C)
  Engine.text(21,237,n[3],0x2A2A2A)
  Engine.text(16,257,line,0x3A3A3A)
  Engine.text(16,278,"5 NEXT",0x6B6254)
  Engine.text(166,278,"RSK CLOSE",0x6B6254)
end

local function draw_portal(g,x,y,active)
  x=sx(g,x)
  y=y+24-27
  local pulse=floor(Engine.time_ms/110)%3
  local c=active and 0x9FE8FF or 0xBDDDE8
  px(x+3,y,12,2,c)
  px(x+1,y+2,16,20,c)
  px(x+3,y+4,12,16,0x577E92)
  px(x+5,y+5,8,14,(pulse==0) and 0xC8F6FF or 0x91DBF4)
  px(x+7,y+8,4,8,0xE9FCFF)
end

function Render.secret(g)
  local s=g.st.secret
  if not s then return end
  if g.secret_inside then
    draw_portal(g,s[5],s[6],true)
    if Save.get_secret(g.level_i)==0 then
      local x=sx(g,s[9])
      local y=s[10]+24+floor(sin(Engine.time_ms*0.012)*2)
      px(x+3,y,4,2,0xBDF6FF)
      px(x+1,y+2,8,6,0x76D8F2)
      px(x+3,y+8,4,2,0xBDF6FF)
      px(x+4,y+2,1,2,0xFFFFFF)
    end
  else
    draw_portal(g,s[1],s[2],true)
    local x=sx(g,s[1])
    local y=s[2]+24-39
    if x>-20 and x<250 then
      px(x-1,y,24,10,0xFFF6D7)
      Engine.text(x+4,y+1,"8 ENTER",0x4F5960)
    end
  end
end

local function boss_body_moss(x,y,b)
  px(x+2,y+7,24,15,0x65B95D)
  px(x+6,y+2,16,11,0x81D575)
  px(x+7,y,4,4,0x81D575)
  px(x+18,y,4,4,0x81D575)
  px(x+9,y+6,2,3,0x24342B)
  px(x+18,y+6,2,3,0x24342B)
  draw_crown(x+8,y-6,b.hp>0)
end

local function boss_body_charge(x,y)
  px(x+2,y+6,24,16,0xC4724E)
  px(x+5,y+3,18,8,0xE29465)
  px(x,y+10,5,5,0x7D4937)
  px(x+23,y+10,5,5,0x7D4937)
  px(x+8,y+7,2,2,0x222222)
  px(x+18,y+7,2,2,0x222222)
  px(x+6,y+21,5,3,0x5A4034)
  px(x+17,y+21,5,3,0x5A4034)
end

local function boss_body_phantom(x,y)
  px(x+3,y+2,22,16,0xF2EDF8)
  px(x+5,y+16,4,5,0xF2EDF8)
  px(x+12,y+16,4,5,0xF2EDF8)
  px(x+20,y+16,4,5,0xF2EDF8)
  px(x+7,y+7,3,4,0x433A50)
  px(x+18,y+7,3,4,0x433A50)
  px(x+11,y+13,7,2,0xC49BCD)
end

local function boss_body_warden(x,y,b)
  px(x+4,y+4,20,17,0x47556F)
  px(x+7,y,14,8,0x617494)
  px(x+2,y+8,4,8,0xBDDFF5)
  px(x+24,y+8,4,8,0xBDDFF5)
  px(x+8,y+7,3,3,0xF7D967)
  px(x+18,y+7,3,3,0xF7D967)
  px(x+11,y+14,7,2,0x202633)
  if floor(Engine.time_ms/120)%2==0 then
    px(x-2,y+12,3,3,0xE7F9FF)
    px(x+28,y+12,3,3,0xE7F9FF)
  end
end

local function skill_icon(k,x,y,warn)
  px(x,y,16,16,warn and 0xF2C75C or 0xD4C49D);px(x+1,y+1,14,14,0xFFF5D8)
  if k==1 then px(x+5,y+3,2,9,0x65B95D);px(x+9,y+3,2,9,0x65B95D)
  elseif k==2 then px(x+3,y+6,4,4,0xC4724E);px(x+9,y+6,4,4,0xC4724E);px(x+7,y+4,2,8,0x7D4937)
  elseif k==3 then px(x+4,y+4,8,8,0xC49BCD);px(x+6,y+6,4,4,0xF2EDF8)
  else px(x+8,y+3,2,3,0x8DDCF8);px(x+6,y+6,3,2,0x8DDCF8);px(x+8,y+8,2,3,0x8DDCF8);px(x+5,y+11,3,2,0x8DDCF8) end
end

function Render.bs(g)
  for i=1,#g.bs do local s=g.bs[i]; if s.active then local x=sx(g,s.x);local y=s.y+24
    if s.k==1 then px(x,y,s.w,s.h,0x65B95D);px(x+3,y-2,3,2,0xA6E59D)
    elseif s.k==2 then px(x,y,s.w,s.h,0xE29465);px(x+2,y-2,s.w-4,2,0xFFD4A8)
    elseif s.k==3 then px(x,y,s.w,s.h,0xC49BCD);px(x+2,y+2,s.w-4,s.h-4,0xF2EDF8)
    elseif s.s==0 then if floor(Engine.time_ms/80)%2==0 then px(x+5,y,2,s.h,0xF7D967) end
    else px(x+3,y,6,s.h,0x8DDCF8);px(x+5,y,2,s.h,0xFFFFFF) end
  end end
end

local function boss_cut(g,b)
  if not b or (b.cut or 0)<=0 then return end
  local shake=(floor(Engine.time_ms/55)%2==0) and 2 or -2
  px(22+shake,82,196,78,0x20252E);px(26+shake,86,188,70,0xFFF3D1)
  px(30+shake,90,4,62,0xF0B85A);px(198+shake,90,4,62,0xF0B85A)
  local w=(b.word==2 and "BOOM!") or (b.word==3 and "WHOO!") or (b.word==4 and "ZAP!") or "ROAR!"
  px(66+shake,101,108,30,0xFFF8E8);Engine.text(81+shake,109,w,0x6A4436)
  px(44+shake,139,30,2,0xD56555);px(52+shake,135,2,10,0xD56555);px(166+shake,139,28,2,0xD56555);px(183+shake,134,2,11,0xD56555)
  px(34+shake,94,14,2,0xF2C75C);px(38+shake,96,14,2,0xF2C75C);px(186+shake,94,14,2,0xF2C75C)
end

function Render.boss(g)
  local b=g.boss
  if not b or b.dead then return end
  local x=sx(g,b.x)
  local y=b.y+24
  if x>-40 and x<260 then
    if b.kind=="moss" then boss_body_moss(x,y,b)
    elseif b.kind=="charge" then boss_body_charge(x,y)
    elseif b.kind=="phantom" then boss_body_phantom(x,y)
    else boss_body_warden(x,y,b) end
    if b.inv>0 and floor(Engine.time_ms/70)%2==0 then
      px(x-2,y-2,b.w+4,b.h+4,0xFFF2B5)
    end
  end

  if b.engaged then
    px(20,27,200,25,0x303640);px(22,29,196,21,0xFFF0CC)
    Engine.text(28,31,b.name,0x3A3330)
    local hpw=60;px(108,34,hpw,7,0xC7B79C);local fill=floor(hpw*(b.hp/b.max_hp));if fill>0 then px(108,34,fill,7,0xD56555) end
    skill_icon(b.skill or 1,178,31,b.warn==1)
    if b.warn==1 then Engine.text(198,31,"!",0xB94F45) end
    local barrier_x=sx(g,b.arena_l-10)
    if barrier_x>-12 and barrier_x<245 then
      local yy=60
      while yy<260 do
        px(barrier_x,yy,8,8,0x8DD9F2)
        px(barrier_x+2,yy+2,4,4,0xD9F7FF)
        yy=yy+12
      end
    end
  end
end

function Render.secret_banner(g)
  if g.secret_banner<=0 or not g.st.secret then return end
  px(42,86,156,46,0x26323B)
  px(44,88,152,42,0xE9F8FF)
  Engine.text(70,96,"SECRET AREA",0x365466)
  Engine.text(58,114,g.st.secret[11],0x4E6370)
end

function Render.draw(g)
  if g.state=="splash" then
    Render.background(g)
    px(30,82,180,132,0xFFF1C8)
    Engine.text(57,101,"CAT IN A LITTLE BOX",0x222222)
    Engine.text(76,124,"WORLD JOURNEY",0x6A5434)
    draw_cat_proc({pose=(floor(Engine.time_ms/240)%2==0) and "run1" or "run2",dir=1},110,151)
    Engine.text(70,184,"NOKIA 225 / MRE",0x555555)
    return
  end

  if g.state=="menu" then
    Render.background(g)
    px(28,48,184,238,0xFFF1C8)
    Engine.text(55,66,"CAT IN A LITTLE BOX",0x222222)
    draw_cat_proc({pose=(floor(Engine.time_ms/260)%2==0) and "run1" or "run2",dir=1},42,78)
    local items={"CONTINUE","WORLD MAP","SETTINGS","ABOUT","EXIT"}
    for i=1,#items do
      local y=106+(i-1)*31
      if i==g.menu_index then px(48,y-4,144,22,0xF6D67A) end
      Engine.text(70,y,items[i],0x222222)
    end
    Engine.text(48,264,"Stars: "..Save.total_stars().."/78",0x555555)
    return
  end

  if g.state=="worldmap" then
    draw_worldmap(g)
    return
  end

  if g.state=="settings" then
    Render.background(g)
    px(28,70,184,176,0xFFF1C8)
    Engine.text(84,88,"SETTINGS",0x222222)
    Engine.text(60,126,"SOUND: "..(Audio.enabled and "ON" or "OFF"),0x222222)
    Engine.text(46,152,"DEBUG: #  *  9 keys",0x555555)
    Engine.text(51,178,"5 toggle sound",0x555555)
    softbar("5 TOGGLE","RSK BACK")
    return
  end

  if g.state=="about" then
    Render.background(g)
    px(18,50,204,226,0xFFF1C8)
    Engine.text(92,67,"ABOUT",0x222222)
    Engine.text(28,97,"Cat platform adventure",0x333333)
    Engine.text(28,116,"26 stages / 4 worlds",0x333333)
    Engine.text(28,135,"One-way + crumble + gates",0x333333)
    Engine.text(28,154,"Stars + world progression",0x333333)
    Engine.text(28,173,"240x320 / 15 FPS",0x333333)
    Engine.text(28,192,"Nokia 225 RM-1011",0x333333)
    Engine.text(28,211,"VXPstore / Qeafivels",0x333333)
    softbar("","RSK BACK")
    return
  end

  Render.background(g)
  local st=g.st

  if st.decor then
    for i=1,#st.decor do Render.decor(g,st.decor[i]) end
  end

  for i=1,#st.solids do Render.platform(g,st.solids[i],false) end
  for i=1,#st.oneways do Render.oneway(g,st.oneways[i]) end
  for i=1,#g.crumbles do Render.crumble(g,g.crumbles[i]) end
  for i=1,#st.movers do
    local m=g.movers[i]
    if m then Render.platform(g,{m.x,m.y,m.w,m.h},true) end
  end

  for i=1,#st.gates do Render.gate(g,st.gates[i]) end
  for i=1,#st.switches do Render.switch(g,st.switches[i]) end
  for i=1,#st.hazards do Render.hazard(g,st.hazards[i]) end
  for i=1,#st.springs do Render.spring(g,st.springs[i]) end
  for i=1,#st.checkpoints do Render.checkpoint(g,st.checkpoints[i],i) end
  for i=1,#g.boxes do if g.boxes[i].active then Render.box(g,g.boxes[i]) end end
  for i=1,#st.coins do if g.coin_alive[i] then Render.coin(g,st.coins[i][1],st.coins[i][2]) end end
  for i=1,#st.keys do if g.key_alive[i] then Render.key(g,st.keys[i][1],st.keys[i][2]) end end
  for i=1,#g.enemies do
    local e=g.enemies[i]
    if e.active then Render.enemy(g,e) end
  end
  for i=1,#st.npcs do Render.npc(g,st.npcs[i]) end
  Render.secret(g)
  Render.boss(g)
  Render.bs(g)

  Render.fx(g)
  Render.goal(g)
  Render.cat(g)
  Render.ui(g)
  DebugUI.draw(g)
  Render.secret_banner(g)
  Render.dialog(g)
  boss_cut(g,g.boss)

  if g.intro_t>0 and g.state=="play" and not g.dialog.active then
    local wi,w=WorldMap.world_for_level(g.level_i)
    px(32,90,176,54,0xFFF1C8)
    Engine.text(50,100,"WORLD "..wi.." - LEVEL "..g.level_i,0x222222)
    Engine.text(46,121,g.st.name,0x555555)
  end

  if g.state=="pause" then
    px(38,118,164,82,0x222222)
    Engine.text(88,134,"PAUSED",0xFFFFFF)
    Engine.text(58,154,"5 resume  0 restart",0xFFFFFF)
    Engine.text(62,174,"RSK world map",0xFFFFFF)
  end

  if g.state=="clear" then
    px(28,104,184,112,0xFFF1C8)
    Engine.text(70,118,"LEVEL CLEAR!",0x222222)
    for i=1,3 do draw_star(90+(i-1)*20,140,i<=g.earned_stars) end
    Engine.text(58,165,"Coins: "..g.level_coins.."/"..#g.st.coins,0x333333)
    Engine.text(58,182,"Hits:  "..g.level_hits,0x333333)
    Engine.text(44,200,"5 MAP   0 REPLAY",0x222222)
  end

  if g.state=="gameover" then
    px(42,124,156,70,0x222222)
    Engine.text(78,140,"TRY AGAIN",0xFFFFFF)
    Engine.text(57,159,"5 restart level",0xFFFFFF)
    Engine.text(62,176,"RSK world map",0xFFFFFF)
  end
end
