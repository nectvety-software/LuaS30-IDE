# LuaS30 Engine 1.9.7 — MRE GCC Build Fix

- Fixed literal `\n` being written into generated GCC probe C source.
- Fixed the same probe-source bug in `toolchain_doctor.py`.
- Added shared MRE GCC compile/link flag definitions.
- Added `MRE`, `GCC` and `__MRE_COMPILER_GCC__` compile defines.
- Preflight now verifies GCC driver, cc1, assembler and the MRE-style linker path.
- Preflight uses a real `gcc_entry` symbol and the LuaS30 MRE linker script.
- Runtime compile/link commands now use the same shared MRE GCC profile as preflight.
- Compiler error hints no longer misclassify probe syntax errors as DLL/backend failures.
