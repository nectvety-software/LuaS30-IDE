# Runtime Compatibility Matrix 1.8.3

LuaS30 IDE 1.8.3 adds a host-side compatibility matrix that evaluates the same
runtime rules used by the Single-VXP compatibility layer against MRE firmware symbol
inventories.

The matrix reports, per firmware:

```text
native capabilities
effective capabilities
selected ABI aliases
activated fallbacks
missing required runtime groups
compatibility level
final result
```

## Run the matrix

```bat
python tools\runtime_compat_matrix.py
```

Default inputs:

```text
compat/runtime_abi_contract.json
compat/mre/*.json
```

Default reports:

```text
build/runtime_compat_matrix/runtime_compat_matrix.json
build/runtime_compat_matrix/runtime_compat_matrix.csv
build/runtime_compat_matrix/runtime_compat_matrix.txt
```

The Studio also exposes:

```text
Tools -> Runtime Compatibility Matrix
```

and streams the actual matrix process output into the integrated OUTPUT panel.

## Final result

```text
PASS      = compatibility level full
DEGRADED  = required runtime groups are available, but ABI alias and/or safe fallback is active
FAIL      = one or more required runtime groups cannot be provided
```

An expected `FAIL` fixture does not make the test suite fail. The matrix test fails only
when an actual row differs from its declared expected result, unless
`--fail-on-incompatible` is explicitly requested.

## Firmware manifest format

Example:

```json
{
  "schema": 1,
  "id": "firmware-build-x",
  "label": "Observed MRE firmware build X",
  "firmware": "build-x",
  "evidence": "observed",
  "exports": [
    "vm_malloc",
    "vm_realloc",
    "vm_free"
  ],
  "notes": "Symbol inventory captured from the target firmware."
}
```

For actual firmware, set:

```text
evidence = observed
```

Synthetic regression fixtures use:

```text
evidence = fixture
```

The package includes synthetic fixtures only. They verify the compatibility engine and
must not be interpreted as evidence for a real Nokia/S30+ firmware.

## Create a manifest from symbols

If you have a newline-delimited symbol list or simple `nm`/`readelf`-style text:

```bat
python tools\mre_symbol_manifest.py ^
  --id firmware-x ^
  --firmware "MRE build X" ^
  --symbols exported_symbols.txt ^
  --out compat\mre\firmware-x.json
```

Then rerun the matrix.

## Matrix columns

### Native capabilities

Capabilities directly supplied by firmware after primary/alias symbol resolution.

### Effective capabilities

Capabilities the runtime can expose after safe engine fallbacks.

### ABI aliases

Shows the exact choice, for example:

```text
reg_system:vm_reg_sysevt_callback->vm_reg_system_event_callback
```

### Fallbacks

Shows actual predicted fallback paths, for example:

```text
text_width_estimate
rename_copy_delete
touch_disabled
```

### Missing required

Required runtime groups that have neither a native implementation nor a supported
fallback.

### Compatibility level

```text
full
degraded
incompatible
```

### Final result

```text
PASS
DEGRADED
FAIL
```

## Source-of-truth relationship

`compat/runtime_abi_contract.json` mirrors the aliases implemented by
`sdk/luas30/src/abi_resolver.c`. `tools/validate_runtime_matrix.py` verifies that the
contract symbols still appear in the C resolver, reducing the risk that the host test
model silently drifts away from the runtime.

The matrix is a compatibility prediction based on an exported-symbol inventory. It does
not prove that an exported function behaves correctly on hardware; real-device smoke
testing remains required for observed firmware.
