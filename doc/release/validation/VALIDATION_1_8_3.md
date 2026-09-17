# Validation 1.8.3

```text
Python AST: PASS (60 files)
validate_tree.py: PASS
validate_native_sdk.py: PASS
validate_complete.py: PASS
validate_workbench.py: PASS
validate_agent_protocol.py: PASS
validate_release_security.py: PASS
validate_single_vxp.py: PASS
validate_runtime_compat.py: PASS
validate_runtime_matrix.py: PASS
Compatibility matrix generated: PASS (5 rows; PASS=1, DEGRADED=3, FAIL=1)
Markdown layout: PASS
```

The bundled firmware manifests are synthetic regression fixtures. The matrix validates the compatibility decision model and expected outcomes, not real-device firmware exports. Observed firmware must be added from an actual symbol inventory before making hardware claims.
