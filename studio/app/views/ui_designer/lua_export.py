"""
lua_export.py — Sinh `ui_design.lua` từ `DesignStore`.

Tệp sinh ra gồm hai phần:

1. `local design = { … }` — dữ liệu thuần: mọi màn hình, mọi thành phần, đúng
   bằng những gì canvas đang vẽ (kể cả `hidden`, `rot`, `fill`, `src`).
2. Bộ vẽ dùng API LuaS30 (`engine.color/rect/frame/text/line/image` — xem
   `doc/reference/API.md`), để game dùng được ngay:

       local ui = require("ui_design")

       function engine.draw()
           ui.draw("main")
       end

       function engine.keypressed(key)
           -- toạ độ phím không có sẵn trên S30+, nên `hit()` dành cho cảm ứng
           -- hoặc cho game tự tính vùng theo id:
           local item = ui.get("main", "btn_start")
           if key == "ok" and item then … end
       end

KHÁC BIỆT so với bản lua-engine: bên đó mỗi màn hình có tệp logic `.lua` riêng
để đồng bộ ID vào thân hàm người dùng viết. LuaS30 chỉ có một tệp sinh ra, nên
tệp này KHÔNG chứa mã người dùng — mọi thứ đều sinh lại từ JSON mỗi lần xuất.
Muốn thêm hành vi thì viết ở tệp Lua khác của game và tra cứu thành phần qua
`ui.get(screen, id)` / `ui.screen(screen)`.

GIỚI HẠN ĐÃ BIẾT: `engine` của LuaS30 chỉ vẽ hình chữ nhật trục thẳng, không có
phép xoay. Thành phần có `rot` = 90/270 được vẽ với chiều rộng/cao hoán đổi
(đúng bằng bao hình sau khi xoay); các góc khác được vẽ như không xoay — ghi rõ
trong phần đầu tệp sinh ra để người đọc không bị bất ngờ.
"""

from __future__ import annotations

from pathlib import Path

from .design_store import (
    CANVAS_H, CANVAS_W, EXPORT_FILENAME, MAIN_SCREEN_ID, DesignStore,
    export_path,
)

# Màu mặc định của từng loại thành phần — PHẢI khớp bảng `_PAINTERS` trong
# items.py, nếu không canvas và game sẽ vẽ khác nhau.
DEFAULT_FILL = {
    "panel": "#161d29",
    "card": "#1b2230",
    "button": "#007acc",
    "label": "#e6e6e6",
    "textbox": "#2d2d30",
    "progress": "#3a3a3a",
    "slider": "#3a3a3a",
    "switch": "#007acc",
    "divider": "#3a3a3a",
    "canvas": "#0e131b",
    "sprite": "#12181f",
    "tile": "#2d5d47",
    "rect": "#007acc",
    "checkbox": "#2d2d30",
    "row": "#3a3a3a",
    "column": "#3a3a3a",
    "spacer": "#3a3a3a",
    "image": "#10151e",
}

ACCENT = "#007acc"
TEXT = "#e6e6e6"
TEXT_DIM = "#8f8f8f"


def _lua_str(value) -> str:
    text = str(value or "")
    text = (text.replace("\\", "\\\\").replace('"', '\\"')
                .replace("\n", "\\n").replace("\r", "\\r"))
    return f'"{text}"'


def _lua_num(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0"
    if float(number).is_integer():
        return str(int(number))
    return f"{number:g}"


def _item_line(item: dict) -> str:
    parts = [
        f'id = {_lua_str(item.get("name"))}',
        f'type = {_lua_str(item.get("type"))}',
        f'x = {_lua_num(item.get("x"))}',
        f'y = {_lua_num(item.get("y"))}',
        f'w = {_lua_num(item.get("w"))}',
        f'h = {_lua_num(item.get("h"))}',
    ]
    text = item.get("text")
    if text:
        parts.append(f'text = {_lua_str(text)}')
    if item.get("src"):
        parts.append(f'src = {_lua_str(item["src"])}')
    if item.get("fill"):
        parts.append(f'fill = {_lua_str(item["fill"])}')
    if item.get("rot"):
        parts.append(f'rot = {_lua_num(item["rot"])}')
    if item.get("value") is not None:
        parts.append(f'value = {_lua_num(item["value"])}')
    if item.get("hidden"):
        parts.append("hidden = true")
    return "      { " + ", ".join(parts) + " },"


def _data_block(store: DesignStore) -> str:
    canvas_w, canvas_h = store.canvas_size()
    lines = ["local design = {",
             f"  canvas = {{ w = {canvas_w}, h = {canvas_h} }},",
             "  screens = {"]
    for screen in store.screens():
        sid = str(screen.get("id"))
        lines.append(f"    [{_lua_str(sid)}] = {{")
        lines.append(f"      name = {_lua_str(screen.get('name') or sid)},")
        lines.append("      items = {")
        for item in screen.get("items") or []:
            lines.append(_item_line(item))
        lines.append("      },")
        lines.append("    },")
    lines.append("  },")
    lines.append("}")
    return "\n".join(lines)


_HEADER = """-- ============================================================================
-- ui_design.lua — SINH TỰ ĐỘNG bởi UI Designer (LuaS30 Studio). ĐỪNG SỬA TAY:
-- mỗi lần bấm "Xuất Lua" tệp này được ghi lại từ đầu.
--
-- Nguồn sự thật: .luas30/ui_design.json  (mở tab UI Designer trong Studio)
-- Màn hình: @SCREENS@
--
-- Cách dùng:
--     local ui = require("ui_design")
--     function engine.draw() ui.draw("main") end
--
-- API:
--     ui.draw(screen_id)          vẽ một màn hình (mặc định "main")
--     ui.get(screen_id, id)       lấy bảng dữ liệu của một thành phần
--     ui.hit(screen_id, x, y)     id thành phần trên cùng chứa điểm (x, y)
--     ui.screen(screen_id)        toàn bộ bảng màn hình (name, items)
--     ui.canvas                   bảng kích thước màn hình
--
-- LƯU Ý: engine của LuaS30 chỉ vẽ hình chữ nhật trục thẳng, không xoay được.
-- Thành phần có rot = 90/270 được vẽ với w/h hoán đổi (đúng bao hình sau xoay);
-- góc khác được vẽ như không xoay.
-- ============================================================================
"""

_RENDERER = '''
local M = {}

M.canvas = design.canvas
M.screens = design.screens
-- Cỡ chữ khi vẽ nhãn; đổi trước khi gọi draw() nếu muốn khác.
M.font_size = 8

-- engine.color() tạo giá trị mới mỗi lần gọi, nên nhớ lại theo mã hex.
local colors = {}

local function rgb(hex)
  local cached = colors[hex]
  if cached ~= nil then
    return cached
  end
  local r = tonumber(string.sub(hex, 2, 3), 16) or 0
  local g = tonumber(string.sub(hex, 4, 5), 16) or 0
  local b = tonumber(string.sub(hex, 6, 7), 16) or 0
  local value = engine.color(r, g, b)
  colors[hex] = value
  return value
end

-- chữ đọc được trên nền `hex` (đen hay trắng tuỳ độ sáng) — giống canvas
local function readable(hex)
  local r = tonumber(string.sub(hex, 2, 3), 16) or 0
  local g = tonumber(string.sub(hex, 4, 5), 16) or 0
  local b = tonumber(string.sub(hex, 6, 7), 16) or 0
  if (0.299 * r + 0.587 * g + 0.114 * b) > 148 then
    return "#101010"
  end
  return "#ffffff"
end

local function fill_of(item, default)
  return item.fill or default
end

-- bao hình sau khi xoay: 90/270 thì hoán đổi w/h
local function box_of(item)
  local w, h = item.w, item.h
  local rot = item.rot
  if rot and (rot == 90 or rot == 270) then
    w, h = h, w
  end
  return item.x, item.y, w, h
end

local function text_in(x, y, w, h, text, color, centered)
  if not text or text == "" then
    return
  end
  local ty = y + math.floor((h - engine.font_height()) / 2)
  if centered then
    local tx = x + math.floor((w - engine.text_width(text)) / 2)
    engine.text(tx, ty, text, color)
  else
    engine.text(x + 3, ty, text, color)
  end
end

local function draw_item(item)
  local t = item.type
  local x, y, w, h = box_of(item)

  if t == "panel" then
    engine.rect(x, y, w, h, rgb(fill_of(item, "#161d29")))
    engine.frame(x, y, w, h, rgb("#3a3a3a"))

  elseif t == "card" then
    engine.rect(x, y, w, h, rgb(fill_of(item, "#1b2230")))
    engine.frame(x, y, w, h, rgb("#3a3a3a"))
    text_in(x, y, w, 16, item.text, rgb("#e6e6e6"), false)

  elseif t == "button" then
    local bg = fill_of(item, "#007acc")
    engine.rect(x, y, w, h, rgb(bg))
    text_in(x, y, w, h, item.text, rgb(readable(bg)), true)

  elseif t == "label" then
    text_in(x, y, w, h, item.text, rgb(fill_of(item, "#e6e6e6")), false)

  elseif t == "checkbox" then
    local side = 12
    local by = y + math.floor((h - side) / 2)
    engine.rect(x, by, side, side, rgb("#2d2d30"))
    engine.frame(x, by, side, side, rgb("#007acc"))
    engine.line(x + 3, by + math.floor(side / 2), x + 5, by + side - 3, rgb("#ffffff"))
    engine.line(x + 5, by + side - 3, x + side - 2, by + 3, rgb("#ffffff"))
    text_in(x + 16, y, w - 16, h, item.text, rgb("#e6e6e6"), false)

  elseif t == "textbox" then
    engine.rect(x, y, w, h, rgb(fill_of(item, "#2d2d30")))
    engine.frame(x, y, w, h, rgb("#3a3a3a"))
    local color = item.text and "#e6e6e6" or "#8f8f8f"
    text_in(x, y, w, h, item.text or "Nhap noi dung...", rgb(color), false)

  elseif t == "image" or t == "sprite" or t == "tile" then
    if item.src and engine.has_images then
      engine.image(x, y, item.src)
    else
      engine.rect(x, y, w, h, rgb(fill_of(item, "#10151e")))
      engine.frame(x, y, w, h, rgb("#3a3a3a"))
    end

  elseif t == "progress" then
    local pct = item.value or 62
    engine.rect(x, y, w, h, rgb(fill_of(item, "#3a3a3a")))
    engine.rect(x, y, math.floor(w * pct / 100), h, rgb(item.fill or "#007acc"))

  elseif t == "slider" then
    local mid = y + math.floor(h / 2)
    local pct = item.value or 55
    engine.line(x + 5, mid, x + w - 5, mid, rgb("#3a3a3a"))
    engine.line(x + 5, mid, x + 5 + math.floor((w - 10) * pct / 100), mid, rgb("#007acc"))
    engine.rect(x + 5 + math.floor((w - 10) * pct / 100) - 4, mid - 4, 8, 8, rgb("#ffffff"))

  elseif t == "switch" then
    local track_h = math.min(h, math.floor(w / 2))
    local ty = y + math.floor((h - track_h) / 2)
    engine.rect(x, ty, w, track_h, rgb(fill_of(item, "#007acc")))
    local knob = math.floor(track_h / 2)
    engine.rect(x + w - track_h + 2, ty + 2, track_h - 4, track_h - 4, rgb("#ffffff"))

  elseif t == "divider" then
    engine.line(x, y + math.floor(h / 2), x + w, y + math.floor(h / 2), rgb("#3a3a3a"))

  elseif t == "rect" then
    engine.rect(x, y, w, h, rgb(fill_of(item, "#007acc")))
    engine.frame(x, y, w, h, rgb("#007acc"))

  elseif t == "canvas" then
    engine.rect(x, y, w, h, rgb("#0e131b"))
    engine.frame(x, y, w, h, rgb("#3a3a3a"))

  elseif t == "row" or t == "column" then
    engine.frame(x, y, w, h, rgb("#3f6fa8"))
    text_in(x, y, w, h, item.text, rgb("#7fb4e8"), false)

  elseif t == "spacer" then
    -- vùng đệm bố cục: trong game không vẽ gì
  end
end

function M.screen(screen_id)
  return design.screens[screen_id or "main"]
end

function M.get(screen_id, id)
  local screen = M.screen(screen_id)
  if not screen then
    return nil
  end
  for i = 1, #screen.items do
    if screen.items[i].id == id then
      return screen.items[i]
    end
  end
  return nil
end

function M.draw(screen_id)
  local screen = M.screen(screen_id)
  if not screen then
    return
  end
  engine.set_font(M.font_size)
  for i = 1, #screen.items do
    local item = screen.items[i]
    if not item.hidden then
      draw_item(item)
    end
  end
end

-- id thành phần TRÊN CÙNG chứa điểm (x, y), hoặc nil. Duyệt từ trên xuống vì
-- items được ghi theo thứ tự vẽ (dưới trước).
function M.hit(screen_id, x, y)
  local screen = M.screen(screen_id)
  if not screen then
    return nil
  end
  for i = #screen.items, 1, -1 do
    local item = screen.items[i]
    if not item.hidden then
      local ix, iy, iw, ih = box_of(item)
      if x >= ix and x <= ix + iw and y >= iy and y <= iy + ih then
        return item.id
      end
    end
  end
  return nil
end

return M
'''


def render_lua(store: DesignStore) -> str:
    """Nội dung `ui_design.lua` cho toàn bộ project."""
    screens = ", ".join(store.screen_ids()) or MAIN_SCREEN_ID
    header = _HEADER.replace("@SCREENS@", screens)
    return header + "\n" + _data_block(store) + "\n" + _RENDERER


def export_lua(store: DesignStore, path: Path | None = None) -> Path | None:
    """Ghi `ui_design.lua`. Trả về đường dẫn, hoặc None nếu không ghi được."""
    if store.root is None:
        store.error = "Chưa mở project."
        return None
    target = Path(path) if path is not None else export_path(store.root)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_lua(store), encoding="utf-8")
    except OSError as exc:
        store.error = f"Không ghi được {target.name}: {exc}"
        return None
    return target


__all__ = [
    "CANVAS_H", "CANVAS_W", "EXPORT_FILENAME", "DEFAULT_FILL", "ACCENT", "TEXT",
    "TEXT_DIM", "render_lua", "export_lua",
]
