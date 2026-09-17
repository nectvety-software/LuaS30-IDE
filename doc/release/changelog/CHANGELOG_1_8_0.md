# LuaS30 Engine 1.8.0 — Release Security

## VXP release pipeline
- Added explicit signing modes: dev, device-bound, cert100.
- Added profile-level direct-run signing policy.
- `--release` refuses signing modes that the selected profile does not declare trusted.
- Added VXP structure/trailer inspection and release manifests.
- Added multi-target `build_matrix.py` for separate device-specific artifacts.

## Hardening
- Release builds can strip unneeded native symbols after entry-point capture.
- Added dependency-free Lua source minifier.
- `--lua-protection auto` prefers stripped Lua 5.1 bytecode when `--luac` is available.
- Signing credentials are not copied into release output; device binding is redacted in manifests.

## Trust boundary
- No certificate/secure-loader bypass is implemented.
- Generic VXP profile intentionally cannot claim direct retail execution.
- A self-signed cert100 artifact is not treated as firmware-trusted unless a verified
  target profile explicitly says so.
