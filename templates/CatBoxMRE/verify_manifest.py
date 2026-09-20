import json
from pathlib import Path

root = Path(__file__).resolve().parent
m = json.loads((root/"manifest.json").read_text(encoding="utf-8"))
p = json.loads((root/"project.json").read_text(encoding="utf-8"))
s = json.loads((root/".luas30/mre_sdk.json").read_text(encoding="utf-8"))
conf = (root/"conf.lua").read_text(encoding="utf-8")

assert m.get("required_ram") == 256
assert p.get("required_ram") == 256
assert p.get("ram_kb") == 256
assert s.get("required_ram") == 256
assert s.get("heap_kb") == 256
assert "required_ram=256" in conf
print("MRE_MANIFEST_256_OK")
