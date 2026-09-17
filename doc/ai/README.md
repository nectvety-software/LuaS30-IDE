# AI Agent Entry Point

Any AI agent that will create or substantially modify a LuaS30 project must begin here.

Read, in order:

1. [`SKILL.md`](SKILL.md)
2. [`PROMPT.md`](PROMPT.md)

Then inspect `VERSION`, root `README.md`, `doc/INDEX.md`, the selected device profile
and the current project template.

Do not create project files before that preflight is complete.

LuaS30's target-side policy is engine-only: application code should use the stable
`engine.*` API and should not add external target runtime dependencies or vendor MRE SDK
build dependencies. Device-specific behavior belongs in a target profile/adapter below
the stable API.

LuaS30 1.8.1 creates one generic VXP artifact; Agents must not scaffold per-device application variants.
