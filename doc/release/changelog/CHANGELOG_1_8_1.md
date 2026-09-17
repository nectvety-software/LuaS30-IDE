# LuaS30 Engine 1.8.1 — Single VXP

- Removed normal per-device VXP build selection.
- Removed `build_matrix.py`.
- Removed `--profile`, `--imsi` and device-bound application artifact mode from the normal builder.
- Canonical final artifact is always `build/<ProjectName>.vxp`.
- Templates no longer contain `target_profile`.
- Device differences are handled by runtime capability detection and ABI compatibility.
- Project Doctor no longer requires a target profile.
- SKILL.md and PROMPT.md instruct Agents not to create per-device application variants.
- Release hardening and optional cert100-format signing remain on the same single VXP.
- No firmware trust/security bypass is implemented.
