# Test report

Tests executed in the build environment:

- Project validator: PASS
- 12 level manifests: PASS
- Bounds / positive solid dimensions: PASS
- Enemy pool budget <= 20: PASS
- Box pool budget <= 8: PASS
- Production source scan for `dofile`, `loadfile`, and `require("src.`: PASS
- 15-minute-equivalent fixed-pool stress model: PASS (13,500 frames at 15 FPS)
- Pool saturation behavior: PASS; saturation increments counters in the stress model instead of growing pools
- Actual Lua syntax/runtime smoke with `texlua`: PASS
- Production environment with `require=nil`, `package=nil`, `dofile=nil`, `loadfile=nil`: PASS
- Splash -> menu -> gameplay transition: PASS
- 1,500-frame movement/jump headless runtime loop: PASS

Not tested here because the real toolchain/device is unavailable:

- Real MediaTek MRE SDK compilation/signing
- MREmu graphical output
- Nokia/MTK6260 physical-device heap and FPS
- Exact vendor-specific graphics/key/audio function signatures
