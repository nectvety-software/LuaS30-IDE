from pathlib import Path
import tempfile,sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"tools"))
from s30plus_compat import detect_mre_sdk, resolve_compat_profile

with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    (root/"include").mkdir(parents=True)
    (root/"lib/MRE30/armgcc").mkdir(parents=True)
    (root/"include/vmsys.h").write_text("/* mock */",encoding="utf-8")
    (root/"lib/MRE30/armgcc/percommon.a").write_bytes(b"mock")
    (root/"lib/MRE30/armgcc/perfile.a").write_bytes(b"mock")
    (root/"scat.ld").write_text("ENTRY(gcc_entry)",encoding="utf-8")

    sdk=detect_mre_sdk(root)
    assert sdk is not None
    assert sdk.include_dir.name=="include"
    assert sdk.percommon.name=="percommon.a"
    assert len(sdk.libraries)==2
    assert resolve_compat_profile("auto",compiler_profile="gcc",mre_sdk=sdk)=="s30plus-native"
    assert resolve_compat_profile("nokia225-rm1011",compiler_profile="gcc",mre_sdk=sdk)=="nokia225-rm1011"

print("PASS: official-style lib/MRE30/armgcc layout detected")
print("PASS: auto prefers native SDK when available")
print("PASS: Nokia profile requires native GCC/MRE SDK")
