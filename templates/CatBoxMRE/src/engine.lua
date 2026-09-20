-- LuaS30 platform adapter for CatBoxMRE.
-- Modelled after the known-working VXP Pixel Editor adapter: capture the
-- runtime engine table directly without helper-global boot dependencies.
Engine = Engine or {}
Engine.W, Engine.H = 240, 320
Engine.keys = {}
Engine.time_ms = 0
Engine.host = nil
Engine.has_graphics = false
Engine.has_images = false
Engine.has_files = false
Engine._color_cache = {}
Engine.draw_count = 0
Engine.clear_count = 0
Engine.rect_count = 0
Engine.text_count = 0
Engine.flush_count = 0
Engine.boot_lines = {}
Engine.boot_line_count = 0
Engine.boot_log_path = "catbox_boot.log"

local host = nil
if type(engine) == "table" then
  host = engine
elseif type(mre) == "table" then
  host = mre
end
Engine.host = host

local function host_fn(name)
  if type(host) == "table" and type(host[name]) == "function" then
    return host[name]
  end
  return nil
end

-- Capture native functions before lifecycle callbacks are installed.
Engine._clear = host_fn("clear")
Engine._rect = host_fn("rect")
Engine._text = host_fn("text")
Engine._flush = host_fn("flush")
Engine._color = host_fn("color")
Engine._image = host_fn("image")
Engine._image_region = host_fn("image_region")
Engine._tick_ms = host_fn("tick_ms")
Engine._exit = host_fn("exit")
Engine._file_read = host_fn("file_read")
Engine._file_write = host_fn("file_write")
Engine._memory_info = host_fn("memory_info")
Engine._set_font = host_fn("set_font")
Engine._log = host_fn("log")
Engine._tone = host_fn("play_tone") or host_fn("tone")

local function rgb565_manual(rgb)
  if type(rgb) ~= "number" then return 0xFFFF end
  if rgb <= 0xFFFF then return rgb end
  local r = math.floor(rgb / 65536) % 256
  local g = math.floor(rgb / 256) % 256
  local b = rgb % 256
  return math.floor(r / 8) * 2048 + math.floor(g / 4) * 32 + math.floor(b / 8)
end

function Engine.color(rgb)
  if type(rgb) ~= "number" then return 0xFFFF end
  if rgb <= 0xFFFF then return rgb end
  local cached = Engine._color_cache[rgb]
  if cached ~= nil then return cached end
  local c = nil
  if Engine._color then
    local r = math.floor(rgb / 65536) % 256
    local g = math.floor(rgb / 256) % 256
    local b = rgb % 256
    local ok, v = pcall(Engine._color, r, g, b)
    if ok and type(v) == "number" then c = v end
  end
  if c == nil then c = rgb565_manual(rgb) end
  Engine._color_cache[rgb] = c
  return c
end

local function boot_dump()
  if not Engine._file_write then return end
  local text = ""
  local i = 1
  while i <= Engine.boot_line_count do
    text = text .. Engine.boot_lines[i] .. "\n"
    i = i + 1
  end
  pcall(Engine._file_write, Engine.boot_log_path, text)
end

function Engine.boot_log(msg)
  msg = tostring(msg or "")
  if Engine.boot_line_count < 16 then
    Engine.boot_line_count = Engine.boot_line_count + 1
    Engine.boot_lines[Engine.boot_line_count] = "[CatBox] " .. msg
  end
  if Engine._log then pcall(Engine._log, "[CatBox] " .. msg)
  elseif type(print) == "function" then print("[CatBox] " .. msg) end
  boot_dump()
end

function Engine.init()
  Engine.has_graphics = Engine._rect ~= nil or Engine._clear ~= nil
  -- Accept image_region when the runtime exposes it even if an older profile
  -- does not publish has_images. Explicit false still disables the feature.
  local allow_images = true
  if type(host) == "table" and host.has_images == false then allow_images = false end
  Engine.has_images = allow_images and Engine._image_region ~= nil
  Engine.has_files = Engine._file_read ~= nil and Engine._file_write ~= nil
  if type(host) == "table" then
    if type(host.W) == "number" then Engine.W = host.W end
    if type(host.H) == "number" then Engine.H = host.H end
  end
  if Engine._set_font then pcall(Engine._set_font, 12) end
  Engine.boot_log("ENGINE INIT gfx=" .. tostring(Engine.has_graphics) .. " img=" .. tostring(Engine.has_images) .. " files=" .. tostring(Engine.has_files))
end

function Engine.clear(color)
  Engine.clear_count = Engine.clear_count + 1
  local c = Engine.color(color or 0x000000)
  if Engine._clear then
    local ok = pcall(Engine._clear, c)
    if ok then return true end
    Engine._clear = nil
  end
  return Engine.rect(0, 0, Engine.W, Engine.H, color or 0x000000)
end

function Engine.rect(x, y, w, h, color)
  if w <= 0 or h <= 0 then return true end
  if not Engine._rect then return false end
  Engine.rect_count = Engine.rect_count + 1
  local ok = pcall(Engine._rect, math.floor(x), math.floor(y), math.floor(w), math.floor(h), Engine.color(color or 0xFFFFFF))
  if not ok then Engine._rect = nil; Engine.has_graphics = Engine._clear ~= nil end
  return ok
end

function Engine.text(x, y, s, color)
  if not Engine._text then return false end
  Engine.text_count = Engine.text_count + 1
  local ok = pcall(Engine._text, math.floor(x), math.floor(y), tostring(s or ""), Engine.color(color or 0xFFFFFF))
  if not ok then Engine._text = nil end
  return ok
end

function Engine.flush()
  Engine.flush_count = Engine.flush_count + 1
  if not Engine._flush then return false end
  local ok = pcall(Engine._flush)
  if not ok then Engine._flush = nil end
  return ok
end

function Engine.load_image(path)
  if not Engine.has_images then return nil end
  -- Stable LuaS30 image_region accepts the resource path directly.
  return tostring(path or "")
end

function Engine.image_region(img, sx, sy, sw, sh, dx, dy)
  if not Engine.has_images or not Engine._image_region or not img then return false end
  local ok, ret = pcall(Engine._image_region, img, sx, sy, sw, sh, math.floor(dx), math.floor(dy))
  if not ok or ret == false then
    Engine.has_images = false
    Engine._image_region = nil
    return false
  end
  return true
end

function Engine.play_tone(freq, ms)
  if not Engine._tone then return false end
  local ok, ret = pcall(Engine._tone, freq, ms)
  return ok and ret ~= false
end

function Engine.file_read(path)
  if not Engine._file_read then return nil end
  local ok, value = pcall(Engine._file_read, tostring(path or ""))
  if ok then return value end
  return nil
end

function Engine.file_write(path, data)
  if not Engine._file_write then return false end
  local ok, value = pcall(Engine._file_write, tostring(path or ""), tostring(data or ""))
  return ok and value ~= false
end

function Engine.exit()
  if Engine._exit then pcall(Engine._exit) end
end

function Engine.memory_info()
  if Engine._memory_info then
    local ok, value = pcall(Engine._memory_info)
    if ok then return value, true end
  end
  return collectgarbage("count"), false
end

function Engine.ticks()
  if Engine._tick_ms then
    local ok, value = pcall(Engine._tick_ms)
    if ok and type(value) == "number" then return value end
  end
  return Engine.time_ms
end

local KEY_MAP = {
  up="UP", down="DOWN", left="LEFT", right="RIGHT", ok="5",
  softleft="SOFTLEFT", softright="SOFTRIGHT", lsk="SOFTLEFT", rsk="SOFTRIGHT",
  clear="BACK", back="BACK", enter="5", ["return"]="5",
  ["0"]="0", ["1"]="1", ["2"]="2", ["3"]="3", ["4"]="4",
  ["5"]="5", ["6"]="6", ["7"]="7", ["8"]="8", ["9"]="9",
  ["*"]="*", ["#"]="#"
}

local function norm_key(k)
  local s = tostring(k or "")
  local low = string.lower(s)
  return KEY_MAP[low] or string.upper(s)
end

function Engine.key_down(k)
  local n = norm_key(k)
  if n ~= "" then Engine.keys[n] = true end
end

function Engine.key_up(k)
  local n = norm_key(k)
  if n ~= "" then Engine.keys[n] = false end
end

function Engine.down(a, b)
  return Engine.keys[norm_key(a)] or (b and Engine.keys[norm_key(b)]) or false
end
