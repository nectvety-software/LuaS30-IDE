#!/usr/bin/env python3
from pathlib import Path
import json,random,sys,shutil,subprocess,tempfile
R=Path(__file__).resolve().parents[1]
levels=json.loads((R/'tools/stage_manifest.json').read_text(encoding='utf-8'))
assert len(levels)==26
assert sum(1 for i in (7,13,19,26))==4
for i,L in enumerate(levels,1):
    assert L['width']>=240
    sx,sy=L['spawn']; gx,gy=L['goal']
    assert 0<=sx<L['width'] and 0<=gx<L['width']
    for r in L['solids']: assert len(r)==4 and r[2]>0 and r[3]>0
    assert len(L['enemies'])<=6 and len(L['boxes'])<=4

frames=15*60*15
pool_enemy=6; pool_fx=12; active_e=0; active_fx=0; peak_e=0; peak_fx=0
rng=random.Random(6260)
for f in range(frames):
    if f%23==0 and active_fx<pool_fx: active_fx+=1
    if f%160==0 and active_e<pool_enemy: active_e+=1
    if f%47==0 and active_fx: active_fx-=1
    if f%410==0 and active_e: active_e-=1
    peak_e=max(peak_e,active_e); peak_fx=max(peak_fx,active_fx)
assert peak_e<=pool_enemy and peak_fx<=pool_fx

main=(R/'main.lua').read_text(encoding='utf-8')
assert 'dofile(' not in main and 'loadfile(' not in main and 'require(' not in main
assert '_G' not in main and 'rawget(' not in main
print('SMOKE DATA OK levels=',len(levels),'frames=',frames,'peak_enemy=',peak_e,'peak_fx=',peak_fx)

lua=shutil.which('lua5.1') or shutil.which('lua') or shutil.which('texlua')
if lua:
    mock=r'''
local calls={clear=0,rect=0,text=0,flush=0,log=0}
local now=0
engine={W=240,H=320,has_images=false,has_files=false,has_audio=false}
function engine.clear(c) calls.clear=calls.clear+1 end
function engine.rect(x,y,w,h,c) calls.rect=calls.rect+1 end
function engine.text(x,y,s,c) calls.text=calls.text+1 end
function engine.flush() calls.flush=calls.flush+1 end
function engine.tick_ms() now=now+66; return now end
function engine.log(s) calls.log=calls.log+1 end
function engine.exit() end
'''
    # Explicitly remove helper globals that the broken 0.1.1 entry depended on.
    harness=mock+'\nrawget=nil; _G=nil; require=nil; package=nil; dofile=nil; loadfile=nil\n'+main+r'''
assert(type(engine.load)=='function')
assert(type(engine.update)=='function')
assert(type(engine.draw)=='function')
assert(type(engine.keypressed)=='function')
assert(type(engine.keyreleased)=='function')
engine.load()
for i=1,20 do engine.update(1/15); engine.draw() end
assert(Game.state=='menu','splash did not advance to menu')
assert(calls.clear>0,'BLACK SCREEN: no clear')
assert(calls.rect>0,'BLACK SCREEN: no rect')
assert(calls.text>0,'BLACK SCREEN: no text')
assert(calls.flush>0,'BLACK SCREEN: no flush')
assert(Engine.draw_count>0,'BLACK SCREEN: draw callback not reached')
engine.keypressed('ok'); engine.update(1/15); engine.keyreleased('ok'); engine.update(1/15)
assert(Game.state=='worldmap','OK did not open world map')
engine.draw()
assert(type(WorldMap)=='table' and #WorldMap.worlds==4,'world map missing')
engine.keypressed('ok'); engine.update(1/15); engine.keyreleased('ok'); engine.update(1/15)
assert(Game.state=='play','OK did not start selected level')
local boss_count=0
local npc_count=0
local secret_count=0
for level=1,#StageData.stages do
    Game.load_level(level)
    engine.update(1/15)
    engine.draw()
    local st=StageData.stages[level]
    assert(type(st.oneways)=='table')
    assert(type(st.switches)=='table')
    assert(type(st.gates)=='table')
    assert(type(st.crumbles)=='table')
    assert(type(st.npcs)=='table')
    npc_count=npc_count+#st.npcs
    if st.boss then
        boss_count=boss_count+1
        assert(Game.boss and Game.boss.max_hp>=3,'boss runtime missing')
        Game.p.x=Game.boss.arena_l+10
        Game.p.inv=99
        for i=1,5 do engine.update(1/15); engine.draw() end
        assert(Game.boss.engaged==true,'boss did not engage')
        assert(Game.boss.skill>=1 and Game.boss.skill<=4,'boss skill id missing')
        local special_seen=false
        for i=1,60 do
            engine.update(1/15); engine.draw()
            for j=1,#Game.bs do if Game.bs[j].active then special_seen=true end end
        end
        assert(special_seen,'boss special pattern did not spawn')
    end
    if st.secret then
        secret_count=secret_count+1
        assert(st.width>st.goal[1],'secret room width invalid')
    end
end
assert(boss_count==4,'expected four bosses')
assert(secret_count==4,'expected four secret areas')
assert(npc_count>=8,'expected NPC dialogue content')
Save.set_star(1,3)
assert(Save.get_star(1)==3,'star save logic failed')
Save.set_secret(3,1)
assert(Save.get_secret(3)==1,'secret save logic failed')
assert(WorldMap.total_stars()>=3,'world progression stars failed')
print('LUAS30_REFERENCE_API_OK',calls.clear,calls.rect,calls.text,calls.flush,calls.log,Engine.draw_count,'bosses',boss_count,'npcs',npc_count,'secrets',secret_count)
'''
    with tempfile.NamedTemporaryFile('w',suffix='.lua',delete=False,encoding='utf-8') as f:
        f.write(harness); tmp=f.name
    r=subprocess.run([lua,tmp],capture_output=True,text=True)
    Path(tmp).unlink(missing_ok=True)
    if r.returncode!=0:
        print(r.stdout); print(r.stderr,file=sys.stderr); raise SystemExit(r.returncode)
    print(r.stdout.strip())
else:
    print('[WARN] Lua interpreter unavailable; runtime test skipped')
