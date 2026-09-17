from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"tools"))

from s30plus_compat import detect_mre_sdk, mre_sdk_search_report, NOKIA225_PROFILE
from toolchain_profiles import detect_toolchain


def main() -> int:
    ap=argparse.ArgumentParser(description="LuaS30 Series 30+ / Nokia 225 compatibility doctor")
    ap.add_argument("--toolchain",required=True,type=Path)
    ap.add_argument("--mre-sdk",type=Path,
                    help="MRE SDK root to check. Optional: auto-discovered when omitted")
    ap.add_argument("--project",type=Path)
    args=ap.parse_args()

    failures=0
    print("=== LuaS30 S30+ Compatibility Doctor ===")
    print("Target:",NOKIA225_PROFILE["model"],NOKIA225_PROFILE["rm"])
    print("Display: 240x320")
    print("Expected loader/application entries: gcc_entry -> vm_main")

    toolchain_root: Path | None = None
    try:
        tc=detect_toolchain(args.toolchain,"gcc")
        toolchain_root=tc.root
        print("[PASS] ARM GCC:",tc.compiler)
    except Exception as exc:
        print("[FAIL] ARM GCC:",exc)
        failures+=1

    # Pass the toolchain through: that is what lets discovery follow the
    # toolchain's import-source marker back to a sibling MRE SDK, so a
    # toolchain-only setup no longer needs --mre-sdk.
    sdk=detect_mre_sdk(args.mre_sdk,toolchain=toolchain_root)
    if not sdk:
        print("[FAIL] Native MRE SDK layout not found.")
        print("       Need include/vmsys.h, percommon.a and scat.ld.")
        print("       Searched:")
        print(mre_sdk_search_report(toolchain=toolchain_root))
        print("       Fix: --mre-sdk PATH, MRE_SDK=PATH, or Settings > MRE SDK.")
        failures+=1
    else:
        print("[PASS] MRE SDK root:",sdk.root)
        print("[PASS] include:",sdk.include_dir)
        print("[PASS] MRE libraries:",sdk.lib_dir,f"({len(sdk.libraries)} .a files)")
        print("[PASS] percommon.a:",sdk.percommon)
        print("[PASS] scat.ld:",sdk.scat_ld)
        for wanted in ("perfile.a","peraudio.a"):
            path=sdk.lib_dir/wanted
            print("[PASS]" if path.is_file() else "[WARN]",wanted,":",path if path.is_file() else "not present")

    runtime=(ROOT/"engine/src/runtime_entry.c").read_text(encoding="utf-8")
    if "void vm_main(void)" in runtime and "void gcc_entry(" in runtime and "vm_main();" in runtime:
        print("[PASS] runtime entry chain: gcc_entry -> vm_main")
    else:
        print("[FAIL] runtime entry chain missing")
        failures+=1

    if args.project:
        project=args.project.resolve()
        descriptor=project/"project.json"
        if descriptor.is_file():
            try:
                cfg=json.loads(descriptor.read_text(encoding="utf-8-sig"))
            except Exception as exc:
                print("[FAIL] project.json:",exc);failures+=1
            else:
                print("[INFO] AppID:",cfg.get("appid"))
                print("[INFO] RAM KB:",cfg.get("ram_kb"))
                print("[INFO] MRE API:",cfg.get("mre_api","Audio File ProMng"))
                if int(cfg.get("screen_width",240))!=240 or int(cfg.get("screen_height",320))!=320:
                    print("[WARN] Nokia 225 RM-1011 is normally 240x320.")
        built=project/"build"/f"{project.name}.vxp"
        # Project display name can differ from folder name, so also scan.
        vxps=list((project/"build").glob("*.vxp")) if (project/"build").is_dir() else []
        if vxps:
            print("[INFO] Built VXP:",vxps[0])
        device_dir=project/"build"/"device"
        if device_dir.is_dir() and list(device_dir.glob("*.vxp")):
            print("[PASS] IMSI-bound device install package exists.")
        else:
            print("[WARN] No IMSI-bound install package found.")
            print("       Nokia 225 retail firmware commonly needs SIM IMSI binding.")

    print()
    if failures:
        print(f"[FAIL] {failures} blocking compatibility issue(s)")
        return 2
    print("[PASS] Native S30+ build prerequisites look complete.")
    print("[NOTE] Physical Nokia execution is still the final compatibility test.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
