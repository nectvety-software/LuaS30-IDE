# AI Agent Entry Point

Any AI agent that will create or substantially modify a LuaS30 project must begin here.

Read, in order:

1. [`SKILL.md`](SKILL.md)
2. [`PROMPT.md`](PROMPT.md)

Then inspect `VERSION`, root `README.md`, `doc/INDEX.md`, the selected device profile
and the current project template.

### Optional add-on contracts

| When the task is… | Also read |
|---|---|
| Memory / `not enough memory` / OOM | [`MEMORY_PROMPT.md`](MEMORY_PROMPT.md) + [`MEMORY_SKILLS.md`](MEMORY_SKILLS.md) |
| Keypad / physical keys | [`Keypad.md`](Keypad.md) |
| **Retro-Go style launcher / menu shell** | [`RETRO_GO_PROMPT.md`](RETRO_GO_PROMPT.md) + [`RETRO_GO_SKILL.md`](RETRO_GO_SKILL.md) |
| **Files in cache / `@App` data dir (every project)** | [`CACHE_PROMPT.md`](CACHE_PROMPT.md) + [`CACHE_SKILL.md`](CACHE_SKILL.md) |

Do not create project files before that preflight is complete.

LuaS30's target-side policy is engine-only: application code should use the stable
`engine.*` API and should not add external target runtime dependencies or vendor MRE SDK
build dependencies. Device-specific behavior belongs in a target profile/adapter below
the stable API.

LuaS30 1.8.1 creates one generic VXP artifact; Agents must not scaffold per-device application variants.
