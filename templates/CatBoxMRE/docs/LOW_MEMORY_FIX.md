# CatBoxMRE v0.14.1-LM — not enough memory fix

## Symptom
VXPEmu shows `not enough memory` before normal rendering.

## Root cause
The v0.14 production `main.lua` grew to about 167 KB and the project requested a 1024 KB MRE heap. A host Lua 5.1-compatible compile profile showed roughly 430 KB of compiled-chunk heap before runtime tables, making the previous build unsuitable for the 1 MB target budget.

## Fix
- Production runtime returned to the stable v0.3 gameplay core.
- 26 stages, 4-world map, four bosses, NPCs and secret areas remain.
- Advanced v0.14 quest/shop/comic systems are not included in the low-memory VXP runtime.
- Declared MRE heap: 768 KB.
- Enemy pool: 6 slots (stage maximum is 5).
- Box pool: 4 slots (stage maximum is 3).
- FX pool: 16 slots.
- Audio queue: 4 entries.
- Lua GC tuned at startup and stepped every ~1.5 seconds.
- Build now has a memory guard so source growth cannot silently return to the v0.14 level.

The host Lua measurement is a regression metric, not a claim of exact MTK6260 heap usage. Final verification still requires VXPEmu and preferably the physical Nokia 225.
