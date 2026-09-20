-- CatBoxMRE SafeBoot production bundle
Engine={W=240,H=320,keys={},t=0,host=nil}
local H=nil
if type(engine)=="table" then H=engine end
if H==nil and type(mre)=="table" then H=mre end
Engine.host=H
local function hf(n)
if H and type(H[n])=="function" then return H[n] end
return nil
end
local clr=hf("clear")
local rect=hf("rect")
local text=hf("text")
local flush=hf("flush")
local tone=hf("play_tone")
if tone==nil then tone=hf("tone") end
local exitfn=hf("exit")
local fread=hf("file_read")
local fwrite=hf("file_write")
local tick=hf("tick_ms")
local function c565(c)
if type(c)~="number" then return 65535 end
if c<=65535 then return c end
local r=math.floor(c/65536)%256
local g=math.floor(c/256)%256
local b=c%256
return math.floor(r/8)*2048+math.floor(g/4)*32+math.floor(b/8)
end
function Engine.init()
if H and type(H.W)=="number" then Engine.W=H.W end
if H and type(H.H)=="number" then Engine.H=H.H end
end
function Engine.clear(c)
if clr then pcall(clr,c565(c or 0)); return end
if rect then pcall(rect,0,0,Engine.W,Engine.H,c565(c or 0)) end
end
function Engine.rect(x,y,w,h,c)
if not rect or w<=0 or h<=0 then return end
pcall(rect,math.floor(x),math.floor(y),math.floor(w),math.floor(h),c565(c or 65535))
end
function Engine.text(x,y,s,c)
if text then pcall(text,math.floor(x),math.floor(y),tostring(s or ""),c565(c or 65535)) end
end
function Engine.flush() if flush then pcall(flush) end end
function Engine.tone(f,ms) if tone then pcall(tone,f,ms) end end
function Engine.read(p) if fread then local ok,v=pcall(fread,p); if ok then return v end end return nil end
function Engine.write(p,s) if fwrite then pcall(fwrite,p,s) end end
function Engine.exit() if exitfn then pcall(exitfn) end end
function Engine.ms()
if tick then local ok,v=pcall(tick); if ok and type(v)=="number" then return v end end
return Engine.t
end
local KM={up="UP",down="DOWN",left="LEFT",right="RIGHT",ok="5",enter="5",softleft="SOFTLEFT",softright="SOFTRIGHT",back="BACK"}
local function nk(k)
local s=tostring(k or "")
local l=string.lower(s)
return KM[l] or string.upper(s)
end
function Engine.key_down(k) Engine.keys[nk(k)]=true end
function Engine.key_up(k) Engine.keys[nk(k)]=false end
function Engine.down(a,b) return Engine.keys[nk(a)] or (b and Engine.keys[nk(b)]) or false end
StageData={count=26,names={
"MEADOW START","NEIGHBOR YARD","BOX LESSON","SPRING LESSON","MOVING DAY","SPIKE ALLEY","MOSS KING",
"KEY AND LIFT","BUBBLE STEPS","CRUSHER HALL","DANGER ABOVE","CAT TOWER","PICNIC BRUTE",
"CLOUD PATH","PIPE PARADE","GHOST LIFT","CANYON BOX","BUBBLE RUN","PHANTOM KEEPER",
"STAIR HOP","KEY CANYON","GHOST CEILING","SIGN SCHOOL","DOUBLE LIFT","PICNIC RETURN","SKY WARDEN"}}
function StageData.name(i) return StageData.names[i] or ("LEVEL "..tostring(i)) end
function StageData.is_boss(i) return i==7 or i==13 or i==19 or i==26 end
function StageData.width(i) return 680+((i-1)%4)*80 end
function StageData.floor_y(i) return 252 end
function StageData.platform(i,n)
local w=StageData.width(i)
if n==1 then return 0,252,w,44 end
if n==2 then return 110+(i%3)*18,214,74,10 end
if n==3 then return 250+(i%5)*12,182,68,10 end
if n==4 then return 390+(i%4)*16,220,80,10 end
if n==5 then return 520+(i%3)*20,194,70,10 end
return nil
end
function StageData.coin(i,n)
local w=StageData.width(i)
if n>6 then return nil end
return 80+n*math.floor((w-150)/7),228-((n+i)%3)*28
end
function StageData.enemy(i,n)
if StageData.is_boss(i) then return nil end
if n>2 then return nil end
return 260+n*160+(i%3)*18,236
end
Audio={enabled=true,cool=0,f=0,ms=0}
function Audio.play(f,ms)
if not Audio.enabled then return end
Audio.f=f or 440
Audio.ms=ms or 30
Audio.cool=0.001
end
function Audio.update(dt)
if Audio.cool<=0 then return end
Audio.cool=Audio.cool-dt
if Audio.cool<=0 then Engine.tone(Audio.f,Audio.ms) end
end
Save={path="catbox.sav",unlocked=1,last=1}
function Save.load()
local s=Engine.read(Save.path)
if type(s)~="string" then return end
local a=string.match(s,"u=(%d+)")
local b=string.match(s,"l=(%d+)")
if a then Save.unlocked=tonumber(a) or 1 end
if b then Save.last=tonumber(b) or 1 end
if Save.unlocked<1 then Save.unlocked=1 end
if Save.unlocked>26 then Save.unlocked=26 end
if Save.last<1 then Save.last=1 end
if Save.last>Save.unlocked then Save.last=Save.unlocked end
end
function Save.write() Engine.write(Save.path,"u="..Save.unlocked.."\nl="..Save.last.."\n") end
Game={state="splash",level=1,t=0,cam=0,coins=0,lives=3}
local P={x=36,y=220,w=14,h=18,vx=0,vy=0,ground=false,inv=0}
Game.p=P
local E={{on=false,x=0,y=0,dir=1},{on=false,x=0,y=0,dir=-1}}
local C={{on=false,x=0,y=0},{on=false,x=0,y=0},{on=false,x=0,y=0},{on=false,x=0,y=0},{on=false,x=0,y=0},{on=false,x=0,y=0}}
local B={on=false,x=0,y=210,w=28,h=26,hp=3,max=3,dir=-1,phase=1,cd=1.5,inv=0}
local prev={}
local function press(n,v)
local r=v and not prev[n]
prev[n]=v
return r
end
local function hit(ax,ay,aw,ah,bx,by,bw,bh)
return ax<bx+bw and bx<ax+aw and ay<by+bh and by<ay+ah
end
local function load_level(i)
Game.level=i
Game.cam=0
Game.coins=0
P.x=36;P.y=220;P.vx=0;P.vy=0;P.ground=false;P.inv=0
local n=1
while n<=6 do
local x,y=StageData.coin(i,n)
C[n].on=x~=nil;C[n].x=x or 0;C[n].y=y or 0
n=n+1
end
n=1
while n<=2 do
local x,y=StageData.enemy(i,n)
E[n].on=x~=nil;E[n].x=x or 0;E[n].y=y or 0;E[n].dir=(n==1) and 1 or -1
n=n+1
end
B.on=StageData.is_boss(i)
B.x=StageData.width(i)-150;B.y=210;B.hp=3;B.max=3;B.dir=-1;B.phase=1;B.cd=1.4;B.inv=0
Game.state="play"
collectgarbage("collect")
end
Game.load_level=load_level
local function damage()
if P.inv>0 then return end
P.inv=1.0
Game.lives=Game.lives-1
Audio.play(180,70)
if Game.lives<=0 then Game.lives=3; load_level(Game.level) end
end
local function solid(px,py,pw,ph,dy)
local n=1
while n<=5 do
local x,y,w,h=StageData.platform(Game.level,n)
if x and hit(px,py,pw,ph,x,y,w,h) and dy>=0 and py+ph-dy<=y+4 then return y end
n=n+1
end
return nil
end
local function update_play(dt)
local l=Engine.down("LEFT","4")
local r=Engine.down("RIGHT","6")
local j=Engine.down("5","UP")
if l then P.vx=-72 end
if r then P.vx=72 end
if not l and not r then P.vx=P.vx*0.72 end
if press("jump",j) and P.ground then P.vy=-155;P.ground=false;Audio.play(520,25) end
P.vy=P.vy+380*dt
local ox=P.x
local oy=P.y
P.x=P.x+P.vx*dt
if P.x<0 then P.x=0 end
local sw=StageData.width(Game.level)
if P.x>sw-P.w then P.x=sw-P.w end
P.y=P.y+P.vy*dt
local sy=solid(P.x,P.y,P.w,P.h,P.y-oy)
if sy then P.y=sy-P.h;P.vy=0;P.ground=true else P.ground=false end
if P.y>310 then damage();P.x=36;P.y=200;P.vy=0 end
if P.inv>0 then P.inv=P.inv-dt end
local n=1
while n<=6 do
local c=C[n]
if c.on and hit(P.x,P.y,P.w,P.h,c.x-4,c.y-4,8,8) then c.on=false;Game.coins=Game.coins+1;Audio.play(880,25) end
n=n+1
end
n=1
while n<=2 do
local e=E[n]
if e.on then
e.x=e.x+e.dir*22*dt
if e.x<180 or e.x>sw-100 then e.dir=-e.dir end
if hit(P.x,P.y,P.w,P.h,e.x,e.y,16,14) then
if P.vy>45 and P.y+P.h<e.y+8 then e.on=false;P.vy=-110;Audio.play(740,30) else damage() end
end
end
n=n+1
end
if B.on then
B.cd=B.cd-dt
if B.inv>0 then B.inv=B.inv-dt end
B.x=B.x+B.dir*((B.phase==2) and 48 or 30)*dt
if B.x<sw-220 then B.x=sw-220;B.dir=1 end
if B.x>sw-70 then B.x=sw-70;B.dir=-1 end
if B.cd<=0 then B.cd=(B.phase==2) and 0.9 or 1.5;B.dir=(P.x>B.x) and 1 or -1;Audio.play((B.phase==2) and 260 or 220,35) end
if hit(P.x,P.y,P.w,P.h,B.x,B.y,B.w,B.h) then
if P.vy>45 and P.y+P.h<B.y+10 and B.inv<=0 then
B.hp=B.hp-1;B.inv=0.6;P.vy=-125;Audio.play(360,45)
if B.hp<=1 then B.phase=2 end
if B.hp<=0 then B.on=false;Audio.play(1040,90) end
else damage() end
end
end
if P.x>sw-34 and not B.on then
if Game.level<26 then
if Save.unlocked<Game.level+1 then Save.unlocked=Game.level+1 end
Save.last=Game.level+1;Save.write();Game.state="clear"
else
Game.state="clear"
end
end
Game.cam=P.x-90
if Game.cam<0 then Game.cam=0 end
local maxcam=sw-240
if Game.cam>maxcam then Game.cam=maxcam end
end
local function rectw(x,y,w,h,c) Engine.rect(math.floor(x-Game.cam),y,w,h,c) end
local function draw_cat()
local x=math.floor(P.x-Game.cam);local y=math.floor(P.y)
local c=0x1A2230
if P.inv>0 and math.floor(Engine.ms()/80)%2==0 then c=0xFFFFFF end
Engine.rect(x+2,y+5,12,12,c);Engine.rect(x+4,y+2,3,4,c);Engine.rect(x+10,y+2,3,4,c)
Engine.rect(x+5,y+8,2,2,0xFFFFFF);Engine.rect(x+11,y+8,2,2,0xFFFFFF)
end
local function draw_play()
Engine.clear(0x87D4FF)
Engine.rect(0,210,240,110,0x9AE39B)
local n=1
while n<=5 do
local x,y,w,h=StageData.platform(Game.level,n)
if x then rectw(x,y,w,h,(n==1) and 0xC98343 or 0xE2A65B) end
n=n+1
end
n=1
while n<=6 do local c=C[n]; if c.on then rectw(c.x-3,c.y-3,6,6,0xFFD54A) end; n=n+1 end
n=1
while n<=2 do local e=E[n]; if e.on then rectw(e.x,e.y,16,14,0x8B5A3C) end; n=n+1 end
if B.on then
rectw(B.x,B.y,B.w,B.h,(B.phase==2) and 0xB45A52 or 0x5D8B57)
Engine.rect(20,26,200,18,0xFFF1C8);Engine.text(26,30,"BOSS",0x222222)
Engine.rect(74,32,120,6,0xBDAA8A);Engine.rect(74,32,math.floor(120*B.hp/B.max),6,0xD95E55)
end
draw_cat()
Engine.text(4,4,"L"..Game.level.." "..StageData.name(Game.level),0x222222)
Engine.text(4,18,"COIN "..Game.coins.."  HP "..Game.lives,0x222222)
Engine.text(182,4,"512?",0x555555)
end
function Game.init()
Engine.init();Save.load();Game.level=Save.last or 1;Game.state="splash";Game.t=0;collectgarbage("collect")
end
function Game.update(dt)
dt=dt or 0.066
Engine.t=Engine.t+dt*1000
Audio.update(dt)
if Game.state=="splash" then
Game.t=Game.t+dt
if Game.t>0.7 then Game.state="menu" end
return
end
if Game.state=="menu" then
if press("ok",Engine.down("5","ENTER")) then load_level(Save.last or 1) end
if press("exit",Engine.down("SOFTRIGHT","BACK")) then Engine.exit() end
return
end
if Game.state=="clear" then
if press("next",Engine.down("5","ENTER")) then
local n=Game.level+1
if n>26 then n=1 end
load_level(n)
end
return
end
if Game.state=="play" then update_play(dt) end
if math.floor(Engine.t)%1500<70 then collectgarbage("step",20) end
end
function Game.draw()
if Game.state=="splash" then
Engine.clear(0x111820);Engine.text(48,130,"CAT IN A LITTLE BOX",0xFFF1C8);Engine.text(86,154,"SAFEBOOT",0xFFD54A);return
end
if Game.state=="menu" then
Engine.clear(0x87D4FF);Engine.rect(24,62,192,190,0xFFF1C8);Engine.text(56,82,"CAT IN A LITTLE BOX",0x222222);Engine.text(70,120,"ULTRA LOW MEMORY",0x555555);Engine.text(64,160,"5  START / CONTINUE",0x222222);Engine.text(64,190,"RSK  EXIT",0x222222);Engine.text(58,224,"LEVEL "..Save.last.." / 26",0x555555);return
end
if Game.state=="clear" then
Engine.clear(0x83D1FF);Engine.rect(30,90,180,120,0xFFF1C8);Engine.text(76,112,"LEVEL CLEAR",0x222222);Engine.text(72,142,"COINS "..Game.coins,0x555555);Engine.text(54,176,"5 NEXT LEVEL",0x222222);return
end
draw_play()
end
CatBoxRuntime={booted=false}
local L=nil
if type(engine)=="table" then L=engine end
if L==nil and type(mre)=="table" then L=mre end
local function boot() if CatBoxRuntime.booted then return end Game.init();CatBoxRuntime.booted=true end
function CatBoxRuntime.update(dt) boot();Game.update(dt or 0.066) end
function CatBoxRuntime.draw() boot();Game.draw();Engine.flush() end
function CatBoxRuntime.keypressed(k) boot();Engine.key_down(k) end
function CatBoxRuntime.keyreleased(k) Engine.key_up(k) end
if L then
L.load=function() boot() end
L.update=function(dt) CatBoxRuntime.update(dt) end
L.draw=function() CatBoxRuntime.draw() end
L.keypressed=function(k) CatBoxRuntime.keypressed(k) end
L.keyreleased=function(k) CatBoxRuntime.keyreleased(k) end
L.quit=function() Save.write() end
else
boot()
end
function update(dt) CatBoxRuntime.update(dt) end
function draw() CatBoxRuntime.draw() end
function key_down(k) CatBoxRuntime.keypressed(k) end
function key_up(k) CatBoxRuntime.keyreleased(k) end
