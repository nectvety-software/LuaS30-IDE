# LuaS30 Native MRE SDK 1.0

This SDK is LuaS30 project code. It intentionally does **not** include or link
vendor MRE SDK headers/libraries such as `percommon.a` or `peraudio.a`.

The target VXP firmware remains the operating system. The only irreducible
boundary is its runtime symbol ABI: the VXP loader supplies a symbol resolver
to `gcc_entry()`, and `abi_resolver.c` resolves the small set of services that
LuaS30 needs.

Application/runtime code talks only to the stable `ls30_*` API declared in:

- `include/ls30/api.h`
- `include/ls30/events.h`
- `include/ls30/graphics.h`
- `include/ls30/filesystem.h`
- `include/ls30/audio.h`
- `include/ls30/device.h`

This separates the engine from vendor headers and makes missing firmware
features capability-based instead of hard build dependencies.
