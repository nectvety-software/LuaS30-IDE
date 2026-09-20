# VXP Build Checklist

- [x] 240x320 target
- [x] 15 FPS dt-based gameplay
- [x] Production `main.lua` bundled
- [x] No runtime `require/dofile/loadfile` in production
- [x] Fixed enemy / box / FX pools
- [x] Incremental GC every ~3 seconds
- [x] Atlas failure fallback
- [x] Tone failure fallback
- [x] Save failure fallback
- [x] Debug overlay
- [x] Project validator
- [x] 15-minute-equivalent pool stress model
- [ ] Bind exact LuaS30 graphics/key API names for your runtime if different
- [ ] Compile with real MRE SDK / LuaS30 VXP toolchain on Windows
- [ ] Smoke-test on MREmu
- [ ] Smoke-test on MTK6260/6261 device
- [ ] Sign/package `.vxp` with your toolchain
