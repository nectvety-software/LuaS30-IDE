# Colored Panel, HEX Viewer and Unique AppID 1.10.3

## Colored bottom-panel text

Console and Build output are color classified:

```text
ERROR / FAIL      red
WARNING           yellow
OK / PASS         green
RUN / command     cyan
BUILD / TOOLCHAIN blue
section headings  purple
normal text       light gray
```

Terminal keeps direct VS Code-style input and now colors the cwd prompt cyan, typed
command text light yellow, successful status text green, warnings yellow and failures red.

## HEX tab

The Compact Bottom Panel contains:

```text
CONSOLE | BUILD | PROBLEMS | TERMINAL | HEX
```

When an emulator launch is requested, LuaS30 reads the exact `vxp` path in
`sync_manifest.json`, opens the bottom panel and selects `HEX` before launching VXPEmu.

Each row is:

```text
00000000  4D 52 45  ...  |MRE....|
```

The viewer uses 16 bytes per row and 64 KiB pages.

Controls:

```text
Prev
Next
Reload
```

This keeps the UI responsive for larger VXP files.

## Unique project AppID

Managed project creation scans all `project.json` files under the LuaS30 project storage
root and selects an unused positive 31-bit AppID.

Range:

```text
100000 .. 2147483647
```

Behavior:

```text
New Project  -> new unique AppID
Duplicate    -> new unique AppID
Import       -> new unique AppID
Rename       -> keep AppID
Open         -> keep AppID
```

The template's AppID is therefore only a template placeholder and is replaced when a new
managed project is created.

The allocator uses cryptographically strong random selection with collision checks and a
deterministic sequential fallback if needed.
