# Third-party notices and environment credits

LuaS30 IDE Studio, LuaS30 Native SDK/runtime and LuaS30 VXP build tooling are
project code. The development environment also uses or bundles third-party
components.

> © Qeafivels All rights reserved.
> Website: <https://qeafivels.com/>

- **Python** — used by Studio launcher and build tooling.
- **PySide6 / Qt for Python** — used for the desktop Studio UI.
- **Qt 6 runtime** — used by desktop UI/emulator components where applicable.
- **Lua 5.1.5** — embedded language runtime source. The bundled license text is
  at `vendor/lua-5.1.5/COPYRIGHT`.
- **GNU ARM toolchain** — ARM compiler/binutils used by the native build.
- **Unicorn Engine** — CPU emulation component used by the bundled emulator
  workflow where applicable.
- **VXPEmu** — bundled emulator executable used for local VXP testing.

License/attribution files supplied with each component are authoritative and must
be preserved when redistributing those components.

LuaS30 Native SDK/API under `sdk/luas30/` is LuaS30 project code. Its native
build does not redistribute or link vendor MRE SDK headers/static libraries such
as `percommon.a` or `peraudio.a`.

Detected runtime versions are visible in **About → Environment & Libraries**.

- **Segoe Fluent Icons / Segoe MDL2 Assets** — Windows system icon fonts used by the Studio UI when present. LuaS30 does not bundle or redistribute Microsoft font files.
