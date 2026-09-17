# FAQ

> **Language:** English · [Tiếng Việt](../vi/FAQ.md)

## Signing and signatures

### My retail phone refuses to open the VXP. Why?

Because **LuaS30 IDE does not sign VXP**. The output is always unsigned (`cert-id 1`,
a 64-byte all-zero signature block). Retail firmware that enforces certificate trust
will refuse to open an unsigned package. This is **correct behaviour by design**, not
a bug.

### Can I enable signing inside the IDE?

No. This repository contains no signing core, no key material and no `--cert100-key`
flag. A leaked build machine cannot produce trusted packages — that is precisely the
point of this decision.

### So how do I sign?

**Outside this repository**, using tooling the operator controls. The IDE only
produces unsigned output.

### Where did the "Sign and Build" button go?

It was removed from the GUI along with the entire signing feature. `build.bat` /
`build_only.bat` only build.

### Is `--device-imsi` a form of signing?

No. It only writes the SIM IMSI into tag `0x12` and normalises `appid`/`ram`. The
resulting file is **still unsigned**. Binding creates an **install condition**, not
**trust** — on trust-enforcing firmware, binding without signing is still refused.

## Building and artifacts

### Why is there only one VXP instead of per-device builds?

LuaS30 uses a **single-VXP model**: one project → one runtime → one MRE/VXP package.
Firmware differences are handled inside the engine:

```text
capability detection -> ABI aliases -> safe fallbacks
```

To support a new firmware, extend the engine/resolver — do **not** create another
application variant.

### Where is the VXP?

```text
<project>\build\<ProjectName>.vxp
```

The same folder holds `.axf`, `.elf-report.txt`, `.dev.vxp`, `*.sha256` and
`sync_manifest.json`.

### Does `--release` sign?

No. `--release` only enables hardening (strip native symbols, protect Lua) and emits
SHA-256/manifest metadata.

### Does hardening make the code impossible to reverse?

No. It raises the **cost** of reverse engineering, but client-side algorithms can
always be recovered.

### The emulator runs — will the real device?

Not necessarily. The emulator is a desktop test step, **not** proof of compatibility.
Build `templates/device_probe` and smoke-test on the actual target device.

## Environment

### What do I need installed?

Windows 10/11 and Python 3.10+. PySide6 (`>=6.7,<7`) is installed by the launcher into
a private venv. ARM GCC and the emulator are already bundled in the repo.

### Do I need the MediaTek MRE SDK?

Not required. The default path (`standalone`) uses LuaS30's dynamic firmware-symbol
resolver. If a valid MRE SDK is present, the `s30plus-native` backend links its real
headers/libs, and the build tool auto-detects it.

### Which Lua version?

**Lua 5.1.5**, bundled in `vendor/lua-5.1.5/`. Target code should be Lua 5.1
compatible; avoid syntax/APIs that exist only in 5.2/5.3/5.4 unless they have been
implemented specifically.

### Which devices are supported?

There are presets for `MTK6260` (Nokia 220/225), `MTK6261` (Nokia 3310 3G/216),
`MTK6250` (Q-Mobile, K-Touch) and `MTK6225` (legacy MRE 2.0). Selecting `MTK6260`
writes the `nokia225-rm1011` profile.

### How do I add a new device?

Extend the **engine centrally**: add a neutral `ls30_*` API, add a capability if the
service is optional, then resolve the symbol in `sdk/luas30/src/abi_resolver.c`. The
runtime only calls `ls30_*` and never calls firmware symbols directly.

## Files and paths

### Where are my projects and configuration?

```text
%APPDATA%\LuaS30IDE\        config, logs, cache, temp, backups, venv
Documents\LuaS30IDE\        managed projects
```

Override with `LUAS30_APPDATA`, `LUAS30_DOCUMENTS`, `LUAS30_PROJECTS`.

### What is the `.luas30/` folder for?

IDE-private data, not game source:

- `ui_design.json` — the UI Designer's source of truth;
- `mre_sdk.json` — MediaTek MRE SDK configuration;
- `ai-backups/<timestamp>/` — copies of files before the AI Agent overwrites them.

### Is it safe to delete `build/`?

Yes. It is generated output. Project Storage also **skips** `build`/`release` when
duplicating a project.

### Why did my AppID change?

Every new project receives a fresh AppID; **Duplicate** and **Import** also assign a
new one. **Rename preserves** the AppID.

## Studio and AI

### Can Studio run on the phone?

No. `studio/` is PC-only; PySide6 is never packaged into a VXP.

### Can the AI Agent read my secret files?

Automatic context **excludes** common secret files (`.env`, credentials, private
keys). AI code edits are confined to the project and rejected for absolute paths,
`../` traversal outside the project, `.git`, `.venv`, `node_modules` and `release`.
Shell output is redacted for secret-bearing environment values before being sent to a
remote provider.

### Are API keys stored?

**Session-only by default.** If you choose to save one, it goes to
`%APPDATA%/LuaS30IDE/config/ai_credentials.json` — **plaintext** JSON outside project
folders. The dialog states this explicitly and lets you remove a saved key.

### Why can't the AI see the end of a long document?

Because instruction documents are truncated by a character limit when context is
built (currently 64,000 chars/file, 160,000 total). Content past the limit **never**
reaches the model. `tools/validate_ai_context.py` guards this.

### Does the AI show raw chain-of-thought?

No. The panel shows only `AI ACTIVITY · REASONING SUMMARY` with high-level summaries:
context files read, plan summary, shell proposals with risk, and execution results.

## Other

### What is the difference between `engine.*` and `mre.*`?

`engine` is the primary global table. `mre` is only a **compatibility alias**. New
code should use `engine.*`.

### Do I need to write native extensions?

Only when you need a service the Lua API does not expose. In that case add a neutral
API to `ls30_*` and resolve it in `abi_resolver.c` — never import firmware directly.

### How do I validate the source before a release?

```bat
python tools\validate_tree.py
python tools\validate_native_sdk.py
python tools\validate_complete.py
```

There are **more than 40** validators in `tools/validate_*.py`.

### Is the IDE free?

LuaS30 IDE is the property of Qeafivels:

```text
© Qeafivels All rights reserved. — https://qeafivels.com/
```

Details in [`LICENSE`](../../LICENSE). Third-party components keep their own licenses:
[`doc/legal/THIRD_PARTY_NOTICES.md`](../../doc/legal/THIRD_PARTY_NOTICES.md).
