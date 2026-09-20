# CatBoxMRE v0.14.1 Low-Memory

> Stability build for Nokia 225 / MTK6260. Production VXP runtime uses the stable v0.3 feature core to stay inside the MRE heap budget.

# CatBoxMRE v0.3.0

# Cat in a Little Box — MRE/VXP platformer

A lightweight 2D cat platformer inspired by the gameplay structure visible in the provided reference video: horizontal platforming, collectibles, keys, boxes, springs, moving platforms, spikes/crushers, ground enemies and flying enemies.

## Controls
- D-pad Left/Right or 4/6: move
- Up or 5: jump / confirm
- Soft-left or P: pause
- 0: restart stage
- #: debug overlay
- *: debug page
- 9: manual full GC (debug)

## Production architecture
`main_dev.lua` loads modules for development. `tools/bundle_main.py` concatenates modules into production `main.lua`; the release entry does not use `require`, `dofile`, `loadfile`, or `package`.

## Build
Run `build_vxp.bat`. Without the real MediaTek MRE/LuaS30 Windows SDK this repository can only generate **VXP-ready source**, not a real signed `.vxp` binary.

## Runtime adapter
`src/engine.lua` probes optional drawing, image, tone, file and memory APIs. Missing image/tone/save APIs degrade gracefully rather than terminating gameplay. If your LuaS30 build exposes different function names, map them only in `src/engine.lua`.
