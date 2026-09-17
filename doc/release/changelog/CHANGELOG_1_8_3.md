# LuaS30 Engine 1.8.3 — Runtime Compatibility Matrix

- Added `compat/runtime_abi_contract.json`.
- Added per-firmware MRE symbol manifests under `compat/mre/`.
- Added host-side runtime compatibility evaluator.
- Matrix rows report native/effective capabilities, selected ABI aliases, activated
  fallbacks, missing required groups, compatibility level and final result.
- Added JSON, CSV and text matrix reports.
- Added helper for importing an observed firmware exported-symbol list.
- Added Tools -> Runtime Compatibility Matrix to Studio.
- Added synthetic full/alias/degraded/file-fallback/incompatible regression fixtures.
- Synthetic fixtures are explicitly not treated as real-device firmware evidence.
