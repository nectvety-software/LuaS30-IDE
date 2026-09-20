# LuaS30 / MRE API compatibility layer

All platform calls are isolated in `src/engine.lua`.

Probed drawing names:
- `draw_rect`, `vm_graphic_fill_rect`, `rect`
- `draw_text`, `vm_graphic_textout`, `text`

Optional image names:
- `image_load`, `load_image`
- `image_region`, `draw_image_region`

Optional audio names:
- `play_tone`, `tone`

Optional storage names:
- `file_read`
- `file_write`

Optional system names:
- `app_exit`, `exit_app`
- `memory_info`, `free_heap`

If the user's LuaS30/CoreMRE build uses a different API signature, only `src/engine.lua` needs to be adapted. The gameplay code does not call native APIs directly.
