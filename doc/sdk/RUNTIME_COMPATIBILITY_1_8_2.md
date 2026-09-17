# Runtime Compatibility Layer 1.8.2

LuaS30 IDE 1.8.2 keeps the **Single VXP** model and adds a compatibility layer
between the generic runtime and different MRE firmware implementations.

```text
ProjectName.vxp
      ↓
engine.* API
      ↓
LuaS30 runtime compatibility layer
      ├── capability detection
      ├── conservative ABI aliases
      └── transparent fallbacks
      ↓
MRE/VXP firmware
```

## Compatibility levels

```text
full
degraded
incompatible
```

- `full`: primary firmware APIs resolved and no fallback was needed.
- `degraded`: all required runtime groups are available, but one or more aliases/fallbacks are active.
- `incompatible`: a required runtime group is missing.

Required groups are memory, lifecycle/key events, resource loading, timers, layer
creation/buffer access, basic drawing, text and layer flush.

## ABI aliases

`abi_resolver.c` tries a small conservative list of alternate names where the expected
C signature is the same.

Examples include:

```text
vm_reg_sysevt_callback
vm_reg_system_event_callback

vm_get_removeable_driver
vm_get_removable_driver

_vm_log_info
vm_log_info
```

Audio APIs deliberately do not alias blocking/non-blocking functions with different
signatures.

If the second or later name is selected, the runtime records an ABI alias hit.

## Capability detection

Lua can inspect:

```lua
local c = engine.runtime_compat()

print(c.compatible)
print(c.level)
print(c.capabilities)
print(c.native_capabilities)
print(c.alias_count)
print(c.fallback_mask)
print(c.missing_required)
```

`engine.device_info()` also exposes:

```text
native_capabilities
fallback_mask
missing_required
abi_alias_count
compatibility
```

Convenience flags include:

```lua
engine.has_audio
engine.has_files
engine.has_images
engine.has_touch
engine.has_rename
engine.has_removable
engine.has_log
engine.runtime_compatible
```

## Transparent fallbacks

When the firmware omits an API that can be safely emulated, LuaS30 uses a fallback.

Current fallbacks include:

```text
resource init missing        -> no-op success
screen size missing          -> 240 x 320 baseline
layer delete missing         -> no-op
clip missing                 -> no-op
font select missing          -> no-op
text width missing           -> character-count estimate
font height missing          -> 10 px baseline
line missing                 -> Bresenham using 1x1 fill
fill missing                 -> scan lines using firmware line API
file commit missing          -> no-op
file rename missing          -> copy + delete
removable drive missing      -> system-drive API return path
audio stop missing           -> no-op
audio playing missing        -> false
volume missing               -> no-op
logging missing              -> no-op
tick counter missing         -> 0
exit API missing             -> no-op
touch callback missing       -> touch disabled
```

Fallbacks are intentionally limited to behavior that can be emulated without inventing
unsafe ABI signatures.

## Effective vs native capability

`native_capabilities` reports services directly exported by firmware.

`capabilities` reports what the LuaS30 runtime can effectively provide after safe
fallbacks. For example, rename may be effectively available through copy/delete even when
the firmware has no native rename call.

## Single VXP rule

Compatibility work belongs in the engine. A project still produces only:

```text
build/<ProjectName>.vxp
```

Do not generate per-device application variants merely because a firmware uses an API
alias or needs a safe fallback.

## Limits

This layer improves ABI/service portability. It cannot make incompatible CPU architecture,
package format, secure-loader trust policy or fundamentally different firmware ABI
automatically compatible.
