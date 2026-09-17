# Building VXP

> **Language:** English · [Tiếng Việt](../vi/Building-VXP.md)

## Pipeline

```text
Project
  ↓
Validate configuration
  ↓
Collect Lua + assets
  ↓
Compile LuaS30 Native SDK
  ↓
Compile Runtime + Lua 5.1 VM
  ↓
ARM GCC link
  ↓
ELF verification
  ↓
VXP resource package
  ↓
Optional IMSI binding (not signing)
  ↓
SHA-256
  ↓
Optional VXP emulator
```

## Batch helpers

Build and run the emulator:

```bat
build.bat PROJECT_DIR
```

Build only:

```bat
build_only.bat PROJECT_DIR
```

Explicit toolchain and IMSI:

```bat
build.bat PROJECT_DIR TOOLCHAIN_DIR IMSI
```

## Full CLI

```bat
python tools\build.py ^
  --project PROJECT_DIR ^
  --toolchain toolchain\arm-gcc ^
  --no-run
```

Available arguments:

| Argument | Values |
|---|---|
| `--project` | project directory |
| `--toolchain` | ARM toolchain directory |
| `--compiler-profile` | `auto` \| `gcc` \| `rvds` \| `ads12` |
| `--compat-profile` | `auto` \| `standalone` \| `s30plus-native` \| `nokia225-rm1011` |
| `--mre-sdk` | MRE SDK path (optional, auto-detected) |
| `--device-imsi` | bind an IMSI into tag `0x12` |
| `--entry-symbol` | override the entry symbol |
| `--luac` | path to `luac.exe` (Lua 5.1) |
| `--appid` | override the AppID |
| `--ram` | override RAM (KB) |
| `--release` | enable hardening and emit SHA-256/manifest |
| `--lua-protection` | `auto` \| `bytecode` \| `minify` \| `off` |
| `--harden-native` | strip native symbols |
| `--run` / `--no-run` | run the emulator after building |
| `--emulator` | select the emulator |

> **There is no signing flag.** The IDE does not sign VXP.

Compiler profiles `rvds` and `ads12` require a legitimate local ARM toolchain
installation. The **ARM GCC path is the bundled, validated one**.

## Output

```text
PROJECT_DIR\build\
├── <Project>.axf
├── <Project>.elf-report.txt
├── <Project>.dev.vxp
├── <Project>.vxp            <- the canonical artifact
├── *.sha256
└── sync_manifest.json
```

`<Project>.vxp` is the **only** artifact. There are no per-device variants and no
device suffix in the filename.

## Raw Lua vs bytecode

Without `--luac`:

- `.lua` files are packed directly;
- the runtime compiles them at load time;
- convenient for development.

With Lua 5.1 `luac`:

```bat
--luac path\to\luac.exe
```

- Lua is compiled to `.lub`;
- stripped bytecode can reduce startup work;
- it **must** be Lua 5.1-compatible bytecode.

`require("src.player")` prefers `src/player.lub` and falls back to `src/player.lua`,
which lets development mode pack raw Lua without a host `luac`.

## ELF requirements

`tools/verify_elf.py` must check that the ARM output matches the runtime/build policy.
Do not swap ARM GCC for Clang/LLD and treat the binary as equivalent without
verification.

If the ARM GCC preflight fails:

```bat
python tools\toolchain_doctor.py --toolchain toolchain\arm-gcc
```

## Release and hardening

```bat
python tools\build.py --project PROJECT --toolchain toolchain\arm-gcc ^
  --release --no-run
```

`--release` **only** enables hardening and emits metadata:

- strips unneeded native symbols;
- applies Lua protection (stripped bytecode when `--luac` is supplied, otherwise
  conservative minification);
- generates SHA-256 and writes the VXP/release manifest.

It does **not** sign, and it does **not** create per-device packages.

Hardening raises the cost of reverse engineering but **cannot** make client-side
algorithms impossible to recover.

## The IDE does not sign VXP

This is an architectural decision, stated plainly so it is not mistaken for a bug.

**This repository contains no signing core, no key material, no `--cert100-key`
flag and no signature verification step.** `build/<ProjectName>.vxp` is **always**
unsigned:

```text
cert-id            1
signature block    64 bytes, all zeros
```

Consequences:

- The output is intended for the **emulator** and for **development/engineering
  units**.
- Retail firmware that enforces certificate trust **will refuse to open** an
  unsigned package.
- If signing is ever required, it must be done **outside this repository** using
  tooling the operator controls. The IDE ships no key material and no signing code,
  so a leaked build machine cannot produce trusted packages.

Removed from the repository for this reason:

```text
tools/vxp_sign_core.py
tools/vxp_sign_pure.py
doc/build/VXP_SIGNER.md
doc/build/SIGNING_AND_RELEASE.md
tools/validate_vxp_signer.py
--cert100-key
```

### IMSI binding is not signing

`tools/vxp_bind_nokia225.py` **remains**, because IMSI binding is not signing:

- it only writes the SIM IMSI into tag `0x12` and normalises `appid`/`ram`;
- the resulting file is **still unsigned**.

In other words, binding creates an **install condition**, not **trust**. On retail
firmware that enforces certificate trust, binding without signing is still refused.

Never write IMSI values or sensitive identifiers into documentation or the
repository.

## Single VXP model

```text
one Lua project
      ↓
one LuaS30 runtime
      ↓
one generic MRE/VXP package
      ↓
runtime capability detection / ABI aliases
      ↓
VXP-capable firmware
```

Applications must **not** fork a VXP per phone model. Firmware differences are
handled inside the engine:

```text
capability detection -> ABI aliases -> safe fallbacks
```

When a new firmware needs support, **extend the engine/resolver** rather than
creating another application variant.

`profiles/` may remain as internal compatibility research/documentation, but it is
no longer a project build selector.

## Release checklist

- validation PASS;
- ARM ELF report reviewed;
- VXP SHA-256 generated;
- emulator smoke test;
- smoke test on the **actual target hardware**;
- save/load;
- pause/resume;
- 30–120 minute endurance run for a large game.

## Compatibility principle

Never conclude that a VXP will certainly run on every phone just because:

- the ELF is valid;
- the emulator runs;
- or the build succeeded.

Every VXP firmware can differ in ABI, RAM, audio codec, resource format, binding
policy and symbol availability.

## Validating the source

```bat
python tools\validate_tree.py
python tools\validate_native_sdk.py
python tools\validate_complete.py
```

There are **more than 40** `tools/validate_*.py` validators, and all must pass before
a release.

See also:
[`doc/build/BUILD_VXP.md`](../../doc/build/BUILD_VXP.md) ·
[`doc/build/RELEASE_AND_HARDENING.md`](../../doc/build/RELEASE_AND_HARDENING.md) ·
[`doc/build/TOOLCHAIN_PROFILES_1_10_0.md`](../../doc/build/TOOLCHAIN_PROFILES_1_10_0.md)
