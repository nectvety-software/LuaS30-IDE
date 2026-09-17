# ARM GCC toolchain

LuaS30 IDE is independent from the old Lua engine and from MRE static SDK
libraries. A compiler is still required to turn C into ARM machine code.

Accepted layout examples:

```
toolchain/arm-gcc/bin/arm-none-eabi-gcc.exe
toolchain/arm-gcc/bin/arm-none-eabi-readelf.exe
```

You can copy only the compiler directory from an existing environment by running:

```
toolchain\import_from_old_engine.bat D:\path\to\lua-engine
```

After that, builds do not use the old engine directory.
