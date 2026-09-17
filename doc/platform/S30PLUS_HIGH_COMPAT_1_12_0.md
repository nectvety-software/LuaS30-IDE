# Series 30+ High Compatibility 1.12.0

LuaS30's earlier standalone MRE ABI resolver is useful for portability research, but a
strict Series 30+ retail phone can be less tolerant than an emulator. Version 1.12.0 adds
a second build path that mirrors working MRE projects more closely.

## Nokia 225 Dual SIM target

```text
Model:       Nokia 225 Dual SIM
Type:        RM-1011
Platform:    Series 30+ / MediaTek MRE
Display:     240 x 320
CPU target:  ARMv5TE
Endian:      little
Code model:  PIC / PIE
```

## Entry chain

Phone MRE applications conventionally expose `vm_main()`. GCC builds use a loader entry
named `gcc_entry`.

LuaS30 now emits:

```text
MRE loader
    |
    v
gcc_entry(resolver, init_array, count)
    |
    +-- bind firmware symbol resolver
    +-- execute constructors
    |
    v
vm_main()
    |
    v
luas30_runtime_main()
```

This replaces the older pattern where LuaS30 jumped directly from `gcc_entry()` into the
runtime without exporting `vm_main()`.

## Build backends

### standalone

Uses LuaS30's own linker and runtime ABI resolver. No vendor MRE SDK is required.

Advantages:

```text
portable
self-contained
good for emulator/research
```

Limitation:

```text
lower confidence on strict S30+ retail firmware
```

### s30plus-native

Requires a local MRE SDK. LuaS30 automatically discovers:

```text
include/vmsys.h
lib/MRE30/armgcc/percommon.a
other per*.a libraries
scat.ld
```

Alternative SDK layouts with `lib/percommon.a` are also detected.

The compiler profile includes the conventional MRE/S30+ defines:

```text
_MINIGUI_LIB_
_USE_MINIGUIENTRY
_NOUNIX_
_FOR_WNC
__MRE_SDK__
__MRE_VENUS_NORMAL__
__MMI_MAINLCD_240X320__
MRE
GCC
__MRE_COMPILER_GCC__
```

The linker uses:

```text
ARM GCC
PIC / PIE
-fpcc-struct-return
--gc-sections
MRE SDK scat.ld
MRE SDK per*.a static libraries
```

The static libraries are grouped with GNU `--start-group/--end-group` to tolerate circular
dependencies.

LuaS30 does not redistribute the proprietary/preserved MRE SDK. Point Settings at your own
MRE SDK installation/archive.

### Locating the MRE SDK

`--mre-sdk` is optional. When it is omitted, the SDK is resolved automatically, in this
order (first valid layout wins):

```text
1. --mre-sdk PATH                     explicit flag (authoritative: if given but invalid, the build fails)
2. MRE_SDK environment variable
3. LuaS30 Studio setting              Settings > MRE SDK, stored in workspace_session.json
4. toolchain/mre-sdk                  drop-in next to the engine (also vendor/mre-sdk, mre-sdk)
5. <toolchain>/mre-sdk                drop-in beside the toolchain
6. toolchain import source            follows toolchain/.import-source back to a sibling SDK
```

Step 6 is what makes a copied toolchain self-sufficient: importing a toolchain from another
MRE engine dump (see `toolchain/import_from_old_engine.bat`) records where it came from, and
the MRE SDK normally sits next to it in that dump (`mre-core/gcc` + `mre-core/sdk`).

A directory counts as a valid MRE SDK root only if it contains `include/vmsys.h`, a library
directory holding `percommon.a`, and `scat.ld`.

If nothing is found, the build error lists every location it searched, so the missing piece
is obvious. Passing an invalid `--mre-sdk` fails immediately instead of silently falling
back to a different SDK.

## Auto compatibility

`compat-profile=auto` behaves as:

```text
ARM GCC + valid MRE_SDK -> s30plus-native
otherwise               -> standalone
```

For physical Nokia 225 testing, select `nokia225-rm1011` explicitly. That profile fails
early if the required native MRE SDK is unavailable rather than silently claiming high
compatibility.

## RAM and API tags

New basic projects use:

```text
RAM:     1024 KB
MRE API: Audio File ProMng
```

The Nokia device-probe template uses 768 KB and `File ProMng` to reduce its footprint.

## IMSI install binding

Public Nokia 225 MRE projects consistently report that retail Nokia firmware normally
requires VXP signing/binding to SIM 1 IMSI. The common compatibility convention prefixes
the IMSI with `9`.

LuaS30 supports this as an install step, not as the canonical build identity.

CLI:

```bat
set LUAS30_DEVICE_IMSI=<SIM1 IMSI>
python tools\build.py ^
  --project PROJECT ^
  --toolchain TOOLCHAIN ^
  --compiler-profile gcc ^
  --compat-profile nokia225-rm1011 ^
  --no-run
```

Add `--mre-sdk MRE_SDK` only when auto-discovery cannot locate the SDK (see
"Locating the MRE SDK" above).

Outputs:

```text
build/<App>.vxp
build/device/<App>.nokia225.vxp
```

The first is the canonical VXP. The second is the phone-install copy.

The IMSI is not written to:

```text
workspace_session.json
sync_manifest.json
release_manifest.json
ai config
documentation
```

Only `device_imsi_bound: true/false` is recorded.

## Doctor

```bat
python tools\s30plus_doctor.py ^
  --toolchain "D:\MRE\LuaS30-Engine\toolchain\arm-gcc" ^
  --project "C:\...\MyProject"
```

`--mre-sdk` is optional here too; add it to check a specific SDK root.

The doctor verifies GCC, MRE headers, static libraries, scatter script, `gcc_entry ->
vm_main`, project RAM/API metadata and whether a bound install package exists.

## Important limitation

This release materially increases structural compatibility with known MRE/S30+ build
recipes, but a physical Nokia 225 is still the authority. Firmware versions, product
codes, SIM policy and available MRE memory vary. Do not treat a successful desktop build
or emulator run as proof that a specific handset will accept the VXP.
