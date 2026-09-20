DebugUI = DebugUI or {}
DebugUI.on=false; DebugUI.page=1; DebugUI.fps=0; DebugUI.acc=0; DebugUI.frames=0; DebugUI.peak=0; DebugUI.gc_step=0; DebugUI.gc_full=0
function DebugUI.update(dt)
  DebugUI.acc=DebugUI.acc+dt; DebugUI.frames=DebugUI.frames+1
  if DebugUI.acc>=1 then DebugUI.fps=DebugUI.frames/DebugUI.acc; DebugUI.acc=0; DebugUI.frames=0 end
  local k=collectgarbage("count"); if k>DebugUI.peak then DebugUI.peak=k end
end
function DebugUI.gcstep()
  collectgarbage("step",64); DebugUI.gc_step=DebugUI.gc_step+1
end
function DebugUI.fullgc() collectgarbage("collect"); DebugUI.gc_full=DebugUI.gc_full+1 end
function DebugUI.draw(g)
  if not DebugUI.on then return end
  Engine.rect(0,24,240,56,0x111111)
  local heap=math.floor(collectgarbage("count")); local m,real=Engine.memory_info()
  Engine.text(2,26,"DBG"..DebugUI.page.." #=OFF *=PAGE 9=GC",0xFFFFFF)
  Engine.text(2,38,string.format("FPS %.1f LUA %dK PK %dK",DebugUI.fps,heap,math.floor(DebugUI.peak)),0xFFFFFF)
  Engine.text(2,50,"OBJ E"..g.ecount.." FX"..g.fxcount.." C"..g.coins.." L"..g.lives,0xFFFFFF)
  Engine.text(2,62,"GC S"..DebugUI.gc_step.." F"..DebugUI.gc_full.." ATL "..(Sprites.atlas_enabled and "ON" or "OFF"),0xFFFFFF)
end
