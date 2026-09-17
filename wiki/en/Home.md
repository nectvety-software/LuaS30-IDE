# LuaS30 IDE

> **Language:** English · [Tiếng Việt](../vi/Home.md)

**LuaS30 IDE** is an integrated development environment for writing applications
and games in **Lua 5.1** and packaging them as **VXP** for **S30+ / MRE** devices.

The IDE has four main parts:

| Component | Role |
|---|---|
| **LuaS30 Studio** | VS Code-like desktop UI (PySide6): editor, Explorer, Assets, UI Designer, Emulator, terminal, ChatAI |
| **LuaS30 Runtime** | Embeds **Lua 5.1.5** and runs `main.lua` on the device |
| **LuaS30 Native SDK** | Its own C API `ls30_*`, with no dependency on vendor MRE headers or `percommon.a` |
| **Build tooling** | ARM GCC compile, ELF verification, VXP packaging, SHA-256, emulator launch |

```text
Lua game  →  engine.*  →  LuaS30 Runtime  →  Native SDK (ls30_*)  →  ABI resolver  →  VXP firmware
```

## Quick start

```bat
run.bat
new_project.bat HelloS30
build.bat "%USERPROFILE%\Documents\LuaS30IDE\HelloS30"
```

The first command opens Studio, the second creates a project, the third builds it
and runs it in the emulator. Details in [Getting Started](Getting-Started.md).

## The single most important thing to know

> **LuaS30 IDE does not sign VXP.**
>
> `build/<ProjectName>.vxp` is always **unsigned** (`cert-id 1`, empty signature
> block). It runs fine in the emulator and on development/engineering units, but
> **retail firmware that enforces certificate trust will refuse to open it**.
>
> This is a deliberate decision, not a bug. The IDE ships no signing code and no
> key material. If signing is ever required it must be done **outside this
> repository**.

## Wiki index

| Page | Contents |
|---|---|
| [Getting Started](Getting-Started.md) | Requirements, `run.bat`, first project, first build |
| [Studio UI](Studio-UI.md) | Layout, Activity Bar, bottom panel, Project Storage, UI Designer, theming |
| [Building VXP](Building-VXP.md) | Pipeline, full CLI, outputs, release/hardening, the no-signing limit |
| [Project Structure](Project-Structure.md) | `project.json`, `conf.lua`, `main.lua`, `src/`, `assets/`, `.luas30/` |
| [AI Agent](AI-Agent.md) | ChatAI, access modes, `luas30-*` protocols, AI Changes, UI design tools |
| [Troubleshooting](Troubleshooting.md) | Launcher won't open, missing PySide6, build failures, emulator OK but device not |
| [FAQ](FAQ.md) | Signing, single VXP, data paths, Lua version, adding a new device |

## Deep reference

This wiki is only the entry point. The authoritative material lives in `doc/`:

- [`doc/INDEX.md`](../../doc/INDEX.md) — the full documentation index.
- [`doc/getting-started/QUICKSTART.md`](../../doc/getting-started/QUICKSTART.md)
- [`doc/reference/API.md`](../../doc/reference/API.md) — the complete Lua API.
- [`doc/build/BUILD_VXP.md`](../../doc/build/BUILD_VXP.md)
- [`doc/build/RELEASE_AND_HARDENING.md`](../../doc/build/RELEASE_AND_HARDENING.md) — the no-signing model.
- [`doc/architecture/ARCHITECTURE.md`](../../doc/architecture/ARCHITECTURE.md)
- [`doc/support/TROUBLESHOOTING.md`](../../doc/support/TROUBLESHOOTING.md)
- [`doc/ai/SKILL.md`](../../doc/ai/SKILL.md) — engineering rules for AI agents.

## Version

The current version is read from [`VERSION`](../../VERSION): **1.0.1**.

Release history: [`doc/release/changelog/`](../../doc/release/changelog/).

## License

© Qeafivels All rights reserved. — <https://qeafivels.com/>

LuaS30 IDE (Studio, Native SDK/API, build tooling, templates, documentation and
assets) is the property of Qeafivels. Details: [`LICENSE`](../../LICENSE).

Third-party components are **not** covered by that notice and keep their own
licenses — see [`doc/legal/THIRD_PARTY_NOTICES.md`](../../doc/legal/THIRD_PARTY_NOTICES.md).
The Lua 5.1.5 license ships at [`vendor/lua-5.1.5/COPYRIGHT`](../../vendor/lua-5.1.5/COPYRIGHT).
