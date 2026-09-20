# Black screen fix

## Root cause

The previous build used legacy/global callbacks (`update`, `draw`) and attempted to discover raw drawing functions such as `draw_rect` / `vm_graphic_fill_rect`.

Current LuaS30 exposes the application lifecycle and rendering surface through the global `engine` table:

- `engine.load`
- `engine.update(dt)`
- `engine.draw()`
- `engine.keypressed(key)` / `engine.keyreleased(key)`
- `engine.clear`, `engine.rect`, `engine.text`, `engine.flush`

On the real LuaS30 runtime, the old callbacks could therefore load without producing any visible frame.

## Fixes

- Registered the game on `engine.*` lifecycle callbacks.
- Added `Engine.flush()` after every frame.
- Switched graphics adapter to `engine.clear/rect/text` first, keeping old raw APIs only as fallback.
- Added RGB888 -> RGB565 color conversion through `engine.color` or manual conversion.
- Normalized LuaS30 lowercase keys (`left`, `right`, `up`, `ok`, `softleft`, etc.).
- Kept procedural sprite fallback when `engine.has_images` is false.
- Added a LuaS30 API-shaped smoke test that fails if no clear/rect/text/flush calls are produced.
