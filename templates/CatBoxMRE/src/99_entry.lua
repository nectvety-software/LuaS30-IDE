-- CatBoxMRE LuaS30 lifecycle entry.
-- Deliberately follows the known-working VXP Pixel Editor binding pattern.
CatBoxRuntime = CatBoxRuntime or {}
CatBoxRuntime.booted = false
CatBoxRuntime.first_draw = false

local life = nil
if type(engine) == "table" then
  life = engine
elseif type(mre) == "table" then
  life = mre
end

local function boot()
  if CatBoxRuntime.booted then return end
  Engine.boot_log("LOAD ENTER")
  Game.init()
  CatBoxRuntime.booted = true
  Engine.boot_log("LOAD OK")
end

function CatBoxRuntime.update(dt)
  boot()
  Game.update(dt or (1 / 15))
end

function CatBoxRuntime.draw()
  boot()
  if not CatBoxRuntime.first_draw then Engine.boot_log("DRAW1 ENTER") end
  Game.draw()
  Engine.draw_count = Engine.draw_count + 1
  Engine.flush()
  if not CatBoxRuntime.first_draw then
    CatBoxRuntime.first_draw = true
    Engine.boot_log("DRAW1 OK clear=" .. tostring(Engine.clear_count) .. " rect=" .. tostring(Engine.rect_count) .. " text=" .. tostring(Engine.text_count) .. " flush=" .. tostring(Engine.flush_count))
  end
end

function CatBoxRuntime.keypressed(k)
  boot()
  Engine.key_down(k)
end

function CatBoxRuntime.keyreleased(k)
  Engine.key_up(k)
end

if life then
  Engine.boot_log("BIND engine lifecycle installed")
  life.load = function() boot() end
  life.update = function(dt) CatBoxRuntime.update(dt) end
  life.draw = function() CatBoxRuntime.draw() end
  life.keypressed = function(k) CatBoxRuntime.keypressed(k) end
  life.keyreleased = function(k) CatBoxRuntime.keyreleased(k) end
  life.pause = function() if CatBoxRuntime.booted and Game.state == "play" then Game.state = "pause" end end
  life.resume = function() end
  life.quit = function() if Save and Save.write then Save.write() end end
else
  -- Development-only fallback when no LuaS30 host table exists.
  boot()
end

-- Legacy compatibility hooks for older desktop stubs.
function update(dt) CatBoxRuntime.update(dt) end
function draw() CatBoxRuntime.draw() end
function key_down(k) CatBoxRuntime.keypressed(k) end
function key_up(k) CatBoxRuntime.keyreleased(k) end
function on_update(dt) CatBoxRuntime.update(dt) end
function on_draw() CatBoxRuntime.draw() end
function on_key_down(k) CatBoxRuntime.keypressed(k) end
function on_key_up(k) CatBoxRuntime.keyreleased(k) end
