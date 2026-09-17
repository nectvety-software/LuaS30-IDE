# Troubleshooting

> **Language:** English · [Tiếng Việt](../vi/Troubleshooting.md)

## `run.bat` does not open Studio

Check the log:

```text
%APPDATA%\LuaS30IDE\logs\launcher.log
```

Then rerun just the dependency stage:

```bat
run.bat --deps-only
```

If the machine is offline:

```bat
run.bat --offline
```

## PySide6 is missing

The launcher only installs/updates when the current version does not satisfy:

```text
PySide6>=6.7,<7
```

If you are offline and the package is not cached, it must be installed before
offline mode is usable. To force a reinstall:

```bat
run.bat --force-deps
```

## ARM GCC not found

Expected files:

```text
toolchain\arm-gcc\bin\arm-none-eabi-gcc.exe
toolchain\arm-gcc\bin\arm-none-eabi-readelf.exe
```

Diagnose:

```bat
python tools\toolchain_doctor.py --toolchain toolchain\arm-gcc
```

`toolchain_doctor` checks the **linker** as well as GCC/cc1/assembler. When the
preflight fails it is usually because the `cc1.exe` backend cannot load its runtime
DLLs — the build tool prepends the toolchain directories to the child process `PATH`
so no global MSYS2 install or manual `PATH` edit is required.

## Build fails at the native SDK

```bat
python tools\validate_native_sdk.py
```

If the source contains `percommon.a`, `peraudio.a` or vendor MRE headers, that is a
**regression** — the Native SDK is not allowed to depend on the vendor.

## Project will not open

Default project path:

```text
Documents\LuaS30IDE\<ProjectName>
```

The Explorer root must point at the directory that **contains** `project.json`.
Opening the parent folder instead will not show the project structure.

## Emulator runs but the real device does not

Emulator success does **not** prove firmware compatibility. Try, in order:

1. build `templates/device_probe` to separate engine faults from game faults;
2. reduce RAM/profile;
3. read `build\<Project>.elf-report.txt`;
4. check binding/sign policy;
5. check firmware ABI aliases;
6. try a build without optional audio/image;
7. check hide / inactive / resume lifecycle.

## A retail device refuses to open the VXP

**This is correct behaviour, not a bug.**

LuaS30 IDE **does not sign** VXP. The output is always unsigned:

```text
cert-id            1
signature block    64 bytes, all zeros
```

Retail firmware that enforces certificate trust will refuse to open it. This
repository contains no signing code and no key material, so there is **no way** to
enable signing from inside the IDE. If signing is required, it must be done outside
the repository with tooling the operator controls.

Details: [Building VXP](Building-VXP.md).

## Audio does not play

```lua
print(engine.has_audio)
```

Codec support depends on the firmware. Always provide a fallback when audio is
unavailable.

## Image does not draw

```lua
print(engine.has_images)
```

Make sure the resource is actually packed and the path matches the exact **case** and
name.

## Save does not work

```lua
print(engine.has_files)
```

Do not assume writable storage exists on every firmware.

## The data folder is still named `LuaS30Engine`

The product name is **LuaS30 IDE** and the target data folder is `LuaS30IDE`; the
system renames the legacy `LuaS30Engine` folder at startup.

If you still see the old name, the usual cause is that **a process is holding the
folder** (for example a running emulator or `python.exe`). Windows refuses
`os.rename` on a directory held by a running process, and the code **deliberately**
falls back to the legacy name rather than risk data loss.

Fix: close the related processes and start again. Do **not** "fix" it by copying then
deleting — that can lose configuration.

## Light stripes in the UI

A region that stays light in a dark theme is almost always a **widget that was never
styled**, not just one of its subcontrols. The classic case: declaring only
`QHeaderView::section` without a background for `QHeaderView` itself — the area after
the last section falls back to the default light palette.

Check with:

```text
QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
  py -3.12 -u tools/studio_theme_check.py
```

Also review `QTabBar`, `QTableView`, `QTreeView`, `QListWidget` and `QScrollArea` —
if you only see `::subcontrol` rules and no rule for the widget itself, there is
almost certainly an unstyled background left.

## The AI Agent "cannot see" the end of a document

Instruction documents are truncated by a character limit when the context is built.
Content past the limit **silently** never reaches the model.

Current limits: 64,000 characters per file and 160,000 total, with the truncation
notice reporting how many characters were dropped.

```bat
python tools\validate_ai_context.py
```

## Pre-release checks

```bat
python tools\validate_tree.py
python tools\validate_native_sdk.py
python tools\validate_complete.py
```

There are **more than 40** `tools/validate_*.py` validators. `run.bat` also runs
validation before opening Studio.

## Compatibility principle

Never conclude that a VXP will run on every phone just because:

- the ELF is valid;
- the emulator runs;
- or the build succeeded.

Every VXP firmware can differ in ABI, RAM, audio codec, resource format, binding
policy and symbol availability.

See also [`doc/support/TROUBLESHOOTING.md`](../../doc/support/TROUBLESHOOTING.md).
