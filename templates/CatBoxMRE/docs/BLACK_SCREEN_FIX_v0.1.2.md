# CatBoxMRE 0.1.2 — LuaS30 IDE / VXPEmu black-screen fix

Reference project used: `VXP_Pixel_Editor_0.3.15_ExportVerify_Source`.

## Confirmed root cause

The CatBox adapter contained this Lua table entry:

```lua
return="5"
```

`return` is a reserved Lua keyword. In Lua 5.1 a reserved word cannot be used as a bare table-field name, so the production chunk fails to parse before any lifecycle callback or boot logger can run. VXPEmu therefore starts the VXP but the Lua application never installs `engine.load/update/draw`, leaving the application surface black.

It is fixed as:

```lua
["return"]="5"
```

This explains why an earlier host smoke test could miss the issue when it did not parse the exact final production bundle in the same way as the emulator.

## Compatibility changes copied from the working reference structure

- `project.json` now uses `type: application` and a target object.
- Added `compat_profile: nokia225-rm1011`.
- Added `appid`, QVGA fields, MTK6260 metadata and MRE API metadata.
- Added `src/99_entry.lua` for lifecycle binding.
- Lifecycle uses the same direct host discovery pattern as the working reference:
  - `type(engine) == "table"`
  - fallback to `mre`
- Removed production dependency on `_G` / `rawget`.
- Platform graphics functions are captured before lifecycle callbacks are installed.
- `engine.clear`, `engine.rect`, `engine.text`, `engine.flush`, `engine.image_region`, file I/O and logging are treated as capabilities.
- RGB888 game colors are converted to RGB565 only at the platform boundary.

## Boot diagnostic sequence

When `engine.log` is available the console should show approximately:

```text
[CatBox] BIND engine lifecycle installed
[CatBox] LOAD ENTER
[CatBox] ENGINE INIT gfx=true img=... files=...
[CatBox] LOAD OK
[CatBox] DRAW1 ENTER
[CatBox] DRAW1 OK clear=1 rect=... text=... flush=1
```

When file write is available, the same startup trace is also written to:

```text
catbox_boot.log
```

Interpretation:

- no `BIND`: production Lua chunk did not execute; inspect parser/build errors;
- `BIND`, no `LOAD`: runtime did not call the lifecycle;
- `LOAD ENTER`, no `LOAD OK`: initialization failed;
- `LOAD OK`, no `DRAW1`: runtime draw loop did not run;
- `DRAW1 ENTER`, no `DRAW1 OK`: first render pass failed;
- `DRAW1 OK` but screen black: inspect framebuffer/profile/flush in LuaS30/VXPEmu.

## Test result

Production bundle was executed against a reference-shaped LuaS30 API stub with helper globals disabled:

```text
rawget=nil
_G=nil
require=nil
package=nil
dofile=nil
loadfile=nil
```

Result:

```text
VALIDATION OK
SMOKE DATA OK levels=26 frames=13500 peak_enemy=20 peak_fx=24
LUAS30_REFERENCE_API_OK 46 7341 161 46 6 46
```

The numeric counters correspond to clear, rectangle, text, flush, log and draw callback activity. All are greater than zero, so the automated test now fails if the render path is never reached.
