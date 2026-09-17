# LuaS30 Engine 1.6.0

## Explorer
- Rebuilt the Explorer as a VS Code-style directory tree.
- Added quick New File/New Folder/Refresh/Collapse controls.
- Added relative path copy, reveal, generated-folder toggle, rename and delete.

## Native SDK / API
- Added `sdk/luas30/` as a project-owned SDK.
- Replaced CoreMRE-facing runtime calls with stable `ls30_*` API calls.
- Isolated target firmware symbol resolution in `abi_resolver.c`.
- Removed native build dependence on vendor MRE headers/static libraries.
- Added capability detection for files, audio, images, touch, logging and rename.
- Added JSON target profiles.
- Runtime is no longer hard-coded to only 240x320 internally; logical projects
  can still request 240x320 for S30+ games.

## Build
- Build compiles SDK + runtime + Lua 5.1 source directly.
- `--profile generic-vxp-qvga` is the default.
- Added native SDK independence validation.

## Important compatibility note
The target firmware ABI itself cannot be removed: a `.vxp` needs the device
operating system for display, keys, timers, storage and audio. LuaS30 now owns
the SDK/API layer above that ABI.
