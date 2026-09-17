# LuaS30 Engine 1.8.4 — Portable ARM GCC Compile Fix

- Fixed portable ARM GCC child backend/DLL lookup on Windows.
- Build process now prepends bundled `arm-gcc/bin` and `arm-none-eabi/bin` to its local PATH.
- Added automatic GCC driver/cc1/assembler compile preflight.
- Added `tools/toolchain_doctor.py`.
- Build failures now include compiler stderr in the raised error message.
- No global Windows PATH modification is required.
- No Native SDK ABI change.
