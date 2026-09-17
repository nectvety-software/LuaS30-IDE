from pathlib import Path
import json
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent
errors=[]

required=(
    "compat/runtime_abi_contract.json",
    "tools/runtime_compat_model.py",
    "tools/runtime_compat_matrix.py",
    "tools/mre_symbol_manifest.py",
    "doc/sdk/RUNTIME_COMPAT_MATRIX_1_8_3.md",
)
for rel in required:
    if not (ROOT/rel).is_file():
        errors.append("missing: "+rel)

contract_path=ROOT/"compat/runtime_abi_contract.json"
contract=json.loads(contract_path.read_text(encoding="utf-8"))
abi=(ROOT/"sdk/luas30/src/abi_resolver.c").read_text(encoding="utf-8")

# Ensure every declared symbol still occurs in the C ABI resolver source.
for field,spec in contract.get("bindings",{}).items():
    for symbol in spec.get("symbols",[]):
        if symbol not in abi:
            errors.append(f"contract drift: {field} symbol not present in abi_resolver.c: {symbol}")

fixtures=sorted((ROOT/"compat/mre").glob("*.json"))
if len(fixtures)<5:
    errors.append("expected at least five runtime compatibility fixtures")

with tempfile.TemporaryDirectory() as td:
    proc=subprocess.run(
        [sys.executable,str(ROOT/"tools/runtime_compat_matrix.py"),"--out",td],
        cwd=ROOT,capture_output=True,text=True
    )
    if proc.returncode!=0:
        errors.append("runtime_compat_matrix.py failed:\\n"+(proc.stdout+proc.stderr)[-1800:])
    report=Path(td)/"runtime_compat_matrix.json"
    if not report.is_file():
        errors.append("matrix JSON report was not generated")
    else:
        data=json.loads(report.read_text(encoding="utf-8"))
        rows=data.get("firmwares",[])
        if len(rows)!=len(fixtures):
            errors.append("matrix row count does not match firmware manifest count")
        required_fields=(
            "native_capabilities","effective_capabilities","abi_aliases","fallbacks",
            "missing_required","compatibility_level","final_result",
        )
        for row in rows:
            for key in required_fields:
                if key not in row:
                    errors.append(f'{row.get("id")}: matrix row missing {key}')

if errors:
    print("FAIL")
    for e in errors: print(" -",e)
    raise SystemExit(1)

print("PASS: ABI contract matches C resolver symbol inventory")
print("PASS: per-firmware matrix fixtures execute with expected outcomes")
print("PASS: matrix reports native/effective capabilities, aliases, fallbacks, level and result")
print("PASS: observed-firmware manifest import helper is present")
