# LuaS30 Engine 1.7.1 — AI Agent Project Protocol

## AI agent workflow
- Added a mandatory two-file preflight: `doc/ai/SKILL.md`, then `doc/ai/PROMPT.md`.
- Added `doc/ai/README.md` as the AI-agent entry point.
- Agents must inspect the selected target profile and current project template before
  creating files.
- Agents must select `GENERIC_VXP`, `KNOWN_DEVICE_PROFILE` or `NEW_DEVICE_PORT`.

## Dependency policy
- Target application code is engine-only and should not add external runtime frameworks.
- Vendor MRE SDK headers/static libraries remain forbidden in the native build.
- Clarified that phone firmware services remain the unavoidable OS/ABI boundary.

## S30+/MRE specialization
- Documented one stable `engine.*` application API with per-device profiles/adapters
  underneath it.
- New device ports should run `templates/device_probe` before the real application is
  scaffolded.
- No Native SDK ABI change in this release.
