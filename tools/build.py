from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
TOOLS=ROOT/"tools"
sys.path.insert(0,str(TOOLS))
from utf8_stdio import configure_utf8_stdio, safe_print, utf8_env

configure_utf8_stdio()

from vxp_pack import pack_vxp
from vxp_inspect import inspect_file
# IMSI binding là bind thiết bị (ghi tag 0x12), KHÔNG phải ký — không có chữ ký
# nào được tạo. IDE này không ký VXP: xem doc/build/RELEASE_AND_HARDENING.md.
from vxp_bind_nokia225 import bind as bind_nokia225
from lua_harden import minify_file
from toolchain_profiles import (
    PROFILE_IDS, Toolchain, configure_environment, detect_toolchain, version_text
)
from s30plus_compat import (
    COMPAT_PROFILE_IDS, NOKIA225_PROFILE, MRESDKLayout, detect_mre_sdk,
    mre_sdk_search_report,
    native_compile_flags, native_library_args, native_link_flags,
    resolve_compat_profile,
)

LUA_SRC=ROOT/"vendor/lua-5.1.5/src"
ENGINE_SRC=ROOT/"engine/src"
ENGINE_INC=ROOT/"engine/include"
SDK_SRC=ROOT/"sdk/luas30/src"
SDK_INC=ROOT/"sdk/luas30/include"
LINKER=ROOT/"engine/linker/luas30.ld"

LUA_CORE=[
"lapi.c","lcode.c","ldebug.c","ldo.c","ldump.c","lfunc.c","lgc.c","llex.c",
"lmem.c","lobject.c","lopcodes.c","lparser.c","lstate.c","lstring.c","ltable.c",
"ltm.c","lundump.c","lvm.c","lzio.c","lauxlib.c","lbaselib.c","lmathlib.c",
"lstrlib.c","ltablib.c"
]
ASSET_EXT={".png",".bmp",".gif",".mp3",".wav",".aac",".amr",".mid",".midi",".txt",".bin",".dat"}


def run(cmd,cwd=None,timeout=240,env=None):
    argv=[str(x) for x in cmd]
    print("[RUN]"," ".join(argv),flush=True)
    p=subprocess.run(
        argv,cwd=cwd,capture_output=True,text=True,
        encoding="utf-8",errors="replace",
        timeout=timeout,env=utf8_env(env),
    )
    if p.stdout:
        print(p.stdout,end="",flush=True)
    if p.stderr:
        print(p.stderr,end="",file=sys.stderr,flush=True)
    if p.returncode:
        details=(p.stderr or p.stdout or "").strip()
        if len(details)>8000:
            details=details[-8000:]
        message=f"command failed ({p.returncode}): {argv[0]}"
        if details:
            message += "\n--- compiler/tool output ---\n" + details
        raise RuntimeError(message)
    return p.stdout


def write_probe(path: Path, entry_symbol: str) -> None:
    source=(
        f"void {entry_symbol}(unsigned int resolver_entry, "
        "unsigned int init_array_start, unsigned int count)\n"
        "{\n"
        "    (void)resolver_entry;\n"
        "    (void)init_array_start;\n"
        "    (void)count;\n"
        "}\n"
    )
    path.write_text(source,encoding="ascii",newline="\n")
    raw=path.read_bytes()
    if b"\\n" in raw or not raw.endswith(b"\n"):
        raise RuntimeError("Internal error: malformed compiler probe source.")


def include_flags(tc: Toolchain, compat_profile: str, mre_sdk: MRESDKLayout | None):
    if compat_profile in {"s30plus-native","nokia225-rm1011"}:
        if not mre_sdk:
            raise RuntimeError("Native S30+ build requires a detected MRE SDK.")
        return [
            f"-I{SDK_INC}",
            f"-I{ENGINE_INC}",
            f"-I{LUA_SRC}",
            f"-I{mre_sdk.include_dir}",
        ]
    if tc.profile_id=="gcc":
        return [f"-I{SDK_INC}",f"-I{ENGINE_INC}",f"-I{LUA_SRC}"]
    return ["-I",str(SDK_INC),"-I",str(ENGINE_INC),"-I",str(LUA_SRC)]


def compile_command(
    tc: Toolchain,
    src: Path,
    obj: Path,
    *,
    probe: bool=False,
    compat_profile: str="standalone",
    mre_sdk: MRESDKLayout | None=None,
):
    if compat_profile in {"s30plus-native","nokia225-rm1011"}:
        if tc.profile_id!="gcc":
            raise RuntimeError("Native S30+ compatibility currently requires ARM GCC.")
        flags=native_compile_flags()
        if not probe:
            flags += include_flags(tc,compat_profile,mre_sdk)
        return [tc.compiler,*flags,src,"-o",obj]

    flags=list(tc.compile_flags)
    if not probe:
        flags += include_flags(tc,compat_profile,mre_sdk)
    return [tc.compiler,*flags,src,"-o",obj]



def link_command(
    tc: Toolchain,
    objects: list[Path],
    axf: Path,
    entry_symbol: str,
    *,
    compat_profile: str="standalone",
    mre_sdk: MRESDKLayout | None=None,
):
    if compat_profile in {"s30plus-native","nokia225-rm1011"}:
        if not mre_sdk:
            raise RuntimeError("Native S30+ link requires a detected MRE SDK.")
        return [
            tc.linker,
            "-o",axf,
            *objects,
            *native_link_flags(mre_sdk),
            *native_library_args(mre_sdk, tc.root),
        ]

    if tc.profile_id=="gcc":
        return [
            tc.linker,"-o",axf,*objects,*tc.link_flags,
            f"-Wl,-e,{entry_symbol}","-T",LINKER,"-lm",
        ]
    if tc.profile_id=="rvds":
        return [
            tc.linker,*tc.link_flags,
            "--entry",entry_symbol,
            "--first",entry_symbol,
            "--output",axf,
            *objects,
        ]
    return [
        tc.linker,*tc.link_flags,
        "-entry",entry_symbol,
        "-first",entry_symbol,
        "-output",axf,
        *objects,
    ]

def toolchain_preflight(tc: Toolchain, probe_dir: Path, entry_symbol: str, *, compat_profile: str="standalone", mre_sdk: MRESDKLayout | None=None):
    probe_dir.mkdir(parents=True,exist_ok=True)
    print("[TOOLCHAIN] profile:",tc.profile_id,f"({tc.display_name})")
    print("[TOOLCHAIN] root:",tc.root)
    print("[TOOLCHAIN] compiler:",tc.compiler)
    print("[TOOLCHAIN] linker:",tc.linker)
    if tc.inspector: print("[TOOLCHAIN] inspector:",tc.inspector)

    version=version_text(tc.compiler,tc.compiler_family)
    if version:
        print("[TOOLCHAIN]",(version.splitlines() or [""])[0])

    src=probe_dir/"toolchain_probe.c"
    obj=probe_dir/"toolchain_probe.o"
    axf=probe_dir/"toolchain_probe.axf"
    write_probe(src,entry_symbol)

    try:
        run(compile_command(tc,src,obj,probe=True,compat_profile=compat_profile,mre_sdk=mre_sdk),timeout=35)
    except Exception as exc:
        raise RuntimeError(
            str(exc)+
            f"\n[HINT] {tc.display_name} compile probe failed. "
            "Check that the selected compiler profile matches the supplied toolchain "
            "and that any required ARM license/environment is available."
        ) from exc
    if not obj.is_file() or obj.stat().st_size==0:
        raise RuntimeError("Compiler probe did not produce an object file.")

    try:
        run(link_command(tc,[obj],axf,entry_symbol,compat_profile=compat_profile,mre_sdk=mre_sdk),timeout=70)
    except Exception as exc:
        raise RuntimeError(
            str(exc)+
            f"\n[HINT] {tc.display_name} compilation succeeded but the MRE entry/link "
            f"probe failed for `{entry_symbol}`. Check linker version, license, "
            "ARMLIB/ARMINC environment and the selected compiler profile."
        ) from exc
    if not axf.is_file() or axf.stat().st_size==0:
        raise RuntimeError("MRE link probe did not produce an AXF/ELF file.")

    print(
        f"[OK] {tc.display_name} preflight: compiler + assembler + linker "
        f"+ entry {entry_symbol}"
    )


def meta(project: Path):
    p=project/"project.json"
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"name":project.name,"appid":262567,"ram_kb":1536,"vendor":"LuaS30"}


def prepare_resources(project:Path,res:Path,luac:Path|None,lua_protection:str="auto"):
    count=0
    lua_mode="raw"
    hardened_files=0
    bytecode_files=0
    for src in sorted(project.rglob("*")):
        if not src.is_file(): continue
        rel=src.relative_to(project)
        if any(x in rel.parts for x in ("build","release","saves","tests","backups",".git",".luas30")): continue
        if src.suffix.lower()==".lua":
            mode=lua_protection
            if mode=="auto":
                mode="bytecode" if luac else "minify"
            if mode=="bytecode":
                if not luac:
                    raise RuntimeError("Lua bytecode protection requires --luac pointing to a Lua 5.1 luac executable.")
                dst=res/rel.with_suffix(".lub");dst.parent.mkdir(parents=True,exist_ok=True)
                run([luac,"-s","-o",dst,src],timeout=30)
                bytecode_files+=1;lua_mode="bytecode-stripped"
            elif mode=="minify":
                dst=res/rel;dst.parent.mkdir(parents=True,exist_ok=True)
                minify_file(src,dst)
                hardened_files+=1;lua_mode="source-minified"
            else:
                dst=res/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
                lua_mode="raw"
            count+=1
        elif src.suffix.lower() in ASSET_EXT:
            dst=res/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);count+=1
    print(f"[OK] resources: {count}; Lua protection: {lua_mode}")
    return {
        "resource_count":count,
        "lua_protection":lua_mode,
        "lua_minified_files":hardened_files,
        "lua_bytecode_files":bytecode_files,
    }


def compile_runtime(tc: Toolchain,obj:Path,compat_profile:str="standalone",mre_sdk:MRESDKLayout|None=None):
    """Compile LuaS30 Native SDK + runtime + embedded Lua without vendor MRE libs."""
    obj.mkdir(parents=True,exist_ok=True)
    sdk_sources=[
        SDK_SRC/"abi_resolver.c",SDK_SRC/"compat.c",SDK_SRC/"api.c",
        SDK_SRC/"utils.c",SDK_SRC/"device.c",
    ]
    runtime_sources=[
        ENGINE_SRC/"runtime_entry.c",ENGINE_SRC/"runtime_bridge.c",ENGINE_SRC/"runtime_lua.c",
    ]
    sources=sdk_sources+runtime_sources+[LUA_SRC/x for x in LUA_CORE]
    objs=[]
    for i,src in enumerate(sources):
        dst=obj/f"{i:02d}_{src.stem}.o"
        run(compile_command(tc,src,dst,compat_profile=compat_profile,mre_sdk=mre_sdk),timeout=100)
        objs.append(dst)
    return objs


def link_runtime(tc: Toolchain,objs:list[Path],axf:Path,entry_symbol:str,compat_profile:str="standalone",mre_sdk:MRESDKLayout|None=None):
    run(link_command(tc,objs,axf,entry_symbol,compat_profile=compat_profile,mre_sdk=mre_sdk),timeout=260)


def verify_elf(tc: Toolchain,axf:Path,report:Path,entry_symbol:str):
    if tc.profile_id=="gcc":
        run([sys.executable,TOOLS/"verify_elf.py",tc.inspector,axf,report],timeout=60)
    else:
        cmd=[sys.executable,TOOLS/"verify_armcc_elf.py",axf,entry_symbol,report]
        if tc.inspector:
            cmd += ["--inspector",tc.inspector]
        run(cmd,timeout=60)


def resources(res:Path):
    return [(p.relative_to(res).as_posix(),p.read_bytes()) for p in sorted(res.rglob("*")) if p.is_file()]


def sha256_file(p:Path):
    h=hashlib.sha256(p.read_bytes()).hexdigest().upper()
    p.with_name(p.name+".sha256").write_text(f"{h} *{p.name}\n",encoding="ascii")
    return h


def write_sync_manifest(path:Path, project:Path, final_vxp:Path, vxp_sha:str,
                        axf:Path, report:Path, appid:int, ram:int,
                        tc:Toolchain, entry_symbol:str, *, app_version:str,
                        mediatek_chipset:str, compat_profile:str, api_list:str,
                        device_vxp:Path|None, device_sha:str|None):
    data={
        "engine":"LuaS30 IDE",
        "engine_version":"1.14.0",
        "build_time_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "project":str(project),
        "vxp":str(final_vxp.resolve()),
        "vxp_sha256":vxp_sha,
        "axf":str(axf.resolve()),
        "axf_sha256":hashlib.sha256(axf.read_bytes()).hexdigest().upper(),
        "elf_report":str(report.resolve()),
        "appid":appid,
        "app_version":app_version,
        "mediatek_chipset":mediatek_chipset or None,
        "ram_kb":ram,
        "compiler_profile":tc.profile_id,
        "compiler_profile_name":tc.display_name,
        "compiler":str(tc.compiler),
        "linker":str(tc.linker),
        "entry_symbol":entry_symbol,
        "compat_profile":compat_profile,
        "mre_sdk_native_link":compat_profile in {"s30plus-native","nokia225-rm1011"},
        "mre_api":api_list,
        "device_install_vxp":str(device_vxp.resolve()) if device_vxp else None,
        "device_install_sha256":device_sha,
        "device_imsi_bound":bool(device_vxp),
        "emulator_policy":"launch_exact_final_vxp_after_sha256_verification",
        "sync_verified":False,
    }
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8",errors="replace")
    return data


def launch_emulator(vxp:Path, sha256:str, manifest:Path, emulator:str|None):
    runner=TOOLS/"run_emulator.py"
    cmd=[sys.executable,runner,"--vxp",vxp,"--sha256",sha256,"--manifest",manifest]
    if emulator: cmd += ["--emulator",emulator]
    print("[SYNC] Launching emulator with the exact VXP just built...")
    p=subprocess.run([str(x) for x in cmd])
    if p.returncode:
        raise RuntimeError(f"VXP built successfully but emulator launch failed ({p.returncode}).")


def assert_native_sdk_independent(compat_profile:str="standalone"):
    forbidden=("percommon.a","peraudio.a","vmsys.h","vmgraph.h","vmio.h","vmmm.h")
    native_paths=list(SDK_SRC.glob("*.c"))+list(ENGINE_SRC.glob("*.c"))+list(SDK_INC.glob("ls30/*.h"))
    text="\n".join(p.read_text(encoding="utf-8",errors="ignore") for p in native_paths)
    bad=[x for x in forbidden if x in text]
    if bad:
        raise RuntimeError("LuaS30 source-layer independence check failed: "+", ".join(bad))
    if compat_profile in {"s30plus-native","nokia225-rm1011"}:
        print("[COMPAT] Vendor MRE headers/libs are build inputs only; Lua application API remains ls30/engine.*")


def single_vxp_policy_note() -> str:
    """Ghi chú về model artifact. IDE KHÔNG ký — xem `doc/build/BUILD_VXP.md`."""
    return (
        "Single generic MRE/VXP package with runtime capability detection. "
        "The IDE produces UNSIGNED VXP only. Firmware trust/security policy "
        "remains authoritative."
    )


def harden_native(tc:Toolchain,source:Path,target:Path):
    if tc.profile_id=="gcc":
        if not tc.stripper:
            raise FileNotFoundError("arm-none-eabi-strip is required for GCC native hardening.")
        run([tc.stripper,"--strip-unneeded","-o",target,source],timeout=60)
        return target
    # ADS/RVDS link profiles already request unused-section removal. Do not
    # rewrite AXF with an unrelated GNU strip tool.
    shutil.copy2(source,target)
    return target


def main():
    ap=argparse.ArgumentParser(description="LuaS30 IDE MediaTek MRE / S30+ multi-toolchain builder")
    ap.add_argument("--toolchain",required=True,type=Path,
                    help="toolchain root containing ARM GCC, RVDS/RVCT, or ADS1.2 tools")
    ap.add_argument("--compiler-profile",choices=PROFILE_IDS,default="auto",
                    help="auto, gcc, rvds, or ads12")
    ap.add_argument("--compat-profile",choices=COMPAT_PROFILE_IDS,default="auto",
                    help="auto, standalone, s30plus-native, or nokia225-rm1011")
    ap.add_argument("--mre-sdk",type=Path,
                    help="MRE SDK root. Optional: when omitted it is auto-discovered from "
                         "MRE_SDK, the LuaS30 Studio setting, or a drop-in next to the "
                         "toolchain/engine")
    ap.add_argument("--device-imsi",
                    help="optional Nokia S30+ SIM IMSI for install-time binding; never written to manifests")
    ap.add_argument("--entry-symbol",
                    help="override the profile entry symbol (advanced compatibility testing)")
    ap.add_argument("--project",required=True,type=Path)
    ap.add_argument("--luac",type=Path,help="optional Lua 5.1 luac.exe")
    ap.add_argument("--appid",type=int)
    ap.add_argument("--ram",type=int)
    ap.add_argument("--release",action="store_true")
    ap.add_argument("--lua-protection",choices=("auto","bytecode","minify","off"),default="auto")
    ap.add_argument("--harden-native",action="store_true")
    run_group=ap.add_mutually_exclusive_group()
    run_group.add_argument("--run",action="store_true")
    run_group.add_argument("--no-run",action="store_true")
    ap.add_argument("--emulator")
    a=ap.parse_args()

    project=a.project.resolve()
    cfg=meta(project)
    name=str(cfg.get("name") or project.name)
    vendor=str(cfg.get("vendor") or "LuaS30")
    app_version=str(cfg.get("app_version") or "1.0.0")
    mediatek_chipset=str(cfg.get("mediatek_chipset") or "")
    appid=a.appid or int(cfg.get("appid",262567))

    tc=detect_toolchain(a.toolchain,a.compiler_profile)
    mre_sdk=detect_mre_sdk(a.mre_sdk,toolchain=tc.root)
    requested_compat=str(a.compat_profile or "auto")
    project_compat=str(cfg.get("compat_profile") or "auto")
    if requested_compat=="auto" and project_compat in {"standalone","s30plus-native","nokia225-rm1011"}:
        requested_compat=project_compat
    compat_profile=resolve_compat_profile(
        requested_compat,
        compiler_profile=tc.profile_id,
        mre_sdk=mre_sdk,
        mre_sdk_search="" if mre_sdk else mre_sdk_search_report(
            toolchain=tc.root, explicit=a.mre_sdk),
    )
    if mre_sdk:
        if a.mre_sdk:
            print(f"[COMPAT] MRE SDK (--mre-sdk): {mre_sdk.root}")
        else:
            print(f"[COMPAT] MRE SDK auto-detected: {mre_sdk.root}")

    ram=a.ram or int(cfg.get("ram_kb",1024))
    api_list=str(cfg.get("mre_api") or "Audio File ProMng")
    if compat_profile=="nokia225-rm1011":
        ram=a.ram or int(cfg.get("ram_kb") or NOKIA225_PROFILE["preferred_ram_kb"])
        api_list=str(cfg.get("mre_api") or NOKIA225_PROFILE["api"])
    entry_symbol=str(a.entry_symbol or tc.entry_symbol)
    configured_paths=configure_environment(tc)
    if configured_paths:
        print("[TOOLCHAIN] PATH +",os.pathsep.join(configured_paths))

    luac=a.luac.resolve() if a.luac else None
    if luac and not luac.is_file(): raise FileNotFoundError(luac)

    build=project/"build"
    shutil.rmtree(build,ignore_errors=True)
    res=build/"res";obj=build/"obj";res.mkdir(parents=True);obj.mkdir(parents=True)

    toolchain_preflight(tc,build/"toolchain-probe",entry_symbol,compat_profile=compat_profile,mre_sdk=mre_sdk)
    shutil.rmtree(build/"toolchain-probe",ignore_errors=True)
    assert_native_sdk_independent(compat_profile)

    print("=== LuaS30 IDE 1.14.0 AI Agent Shell Build ===")
    print("Runtime: LuaS30 Native SDK + embedded Lua 5.1.5")
    print("Artifact model: canonical generic VXP + optional install-time Nokia IMSI binding")
    print("S30+ compatibility:",compat_profile)
    if mre_sdk:
        print("[COMPAT] MRE SDK:",mre_sdk.root)
        print("[COMPAT] MRE libs:",mre_sdk.lib_dir)
        print("[COMPAT] scatter:",mre_sdk.scat_ld)
    else:
        print("[COMPAT] MRE SDK: not detected; standalone resolver path")
    print("Compiler profile:",tc.display_name,f"[{tc.profile_id}]")
    print("Entry convention:",entry_symbol)
    print("MRE link model:", "native SDK static libs + vendor scatter script" if compat_profile in {"s30plus-native","nokia225-rm1011"} else "standalone dynamic ABI resolver")
    print("Compiler:",tc.compiler)
    print("Linker:",tc.linker)

    resource_security=prepare_resources(project,res,luac,a.lua_protection)
    objs=compile_runtime(tc,obj,compat_profile,mre_sdk)
    axf=build/f"{name}.axf"
    link_runtime(tc,objs,axf,entry_symbol,compat_profile,mre_sdk)

    report=build/f"{name}.elf-report.txt"
    verify_elf(tc,axf,report,entry_symbol)

    pack_axf=axf
    native_hardened=bool(a.release or a.harden_native)
    if native_hardened:
        protected=build/f"{name}.release.axf"
        harden_native(tc,axf,protected)
        pack_axf=protected
        print("[OK] Native release hardening:", "GNU strip" if tc.profile_id=="gcc" else "link-time section removal")

    raw=pack_vxp(pack_axf,resources(res),name,vendor,appid,ram,api=api_list)
    dev=build/f"{name}.dev.vxp";dev.write_bytes(raw);sha256_file(dev)

    # IDE KHÔNG ký. Bản phát hành là chính bản dev, chỉ đổi tên.
    final_vxp=build/f"{name}.vxp"
    shutil.copy2(dev,final_vxp)
    print("[OK] Single generic VXP (unsigned):",final_vxp)

    final_sha=sha256_file(final_vxp)

    device_imsi=(a.device_imsi or os.environ.get("LUAS30_DEVICE_IMSI","")).strip()
    device_vxp=None
    device_sha=None
    if device_imsi:
        device_dir=build/"device"
        device_dir.mkdir(parents=True,exist_ok=True)
        device_vxp=device_dir/f"{name}.nokia225.vxp"
        device_sha=bind_nokia225(
            final_vxp,
            device_vxp,
            device_imsi,
            app_id=appid,
            ram_kb=ram,
            prefix9=True,
        )
        print("[OK] Nokia/S30+ IMSI-bound install VXP:",device_vxp)
        print("[OK] Nokia/S30+ install SHA-256:",device_sha)
    elif compat_profile=="nokia225-rm1011":
        safe_print("[WARN] VXP này CHƯA KÝ — firmware retail Nokia 225 sẽ từ chối mở.")
        safe_print("[WARN] IDE không còn chức năng ký. Dùng cho dev/emulator, hoặc tự ký ngoài IDE.")

    vxp_report=inspect_file(final_vxp)
    vxp_report_path=build/f"{name}.vxp-report.json"
    vxp_report_path.write_text(json.dumps(vxp_report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",errors="replace")
    if not vxp_report.get("valid"):
        raise RuntimeError("Final VXP metadata/trailer validation failed; see VXP report.")

    manifest=build/"sync_manifest.json"
    sync_data=write_sync_manifest(
        manifest,project,final_vxp,final_sha,pack_axf,report,appid,ram,tc,entry_symbol,
        app_version=app_version,
        mediatek_chipset=mediatek_chipset,
        compat_profile=compat_profile,
        api_list=api_list,
        device_vxp=device_vxp,
        device_sha=device_sha,
    )
    sync_data.update({
        "engine_version":"1.14.0",
        "artifact_model":"canonical-generic-plus-optional-install-binding",
        "device_specific_artifact":bool(device_vxp),
        "runtime_detection":True,
        "signing":"none (IDE does not sign VXP)",
        "release_mode":bool(a.release),
        "native_hardened":native_hardened,
        "lua_protection":resource_security.get("lua_protection"),
        "vxp_report":str(vxp_report_path.resolve()),
        "firmware_trust_note":single_vxp_policy_note(),
    })
    manifest.write_text(json.dumps(sync_data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",errors="replace")

    release_manifest=build/"release_manifest.json"
    release_manifest.write_text(json.dumps({
        "engine":"LuaS30 IDE","engine_version":"1.14.0","project":name,
        "app_version":app_version,"mediatek_chipset":mediatek_chipset or None,
        "artifact_model":"canonical-generic-plus-optional-install-binding",
        "device_specific_artifact":bool(device_vxp),
        "compat_profile":compat_profile,
        "runtime_detection":True,"artifact":str(final_vxp.resolve()),
        "sha256":final_sha,"compiler_profile":tc.profile_id,
        "compiler":str(tc.compiler),"linker":str(tc.linker),
        "entry_symbol":entry_symbol,
        "signing":"none (IDE does not sign VXP)",
        "mre_api":api_list,
        "device_install_vxp":str(device_vxp.resolve()) if device_vxp else None,
        "device_install_sha256":device_sha,
        "device_imsi_bound":bool(device_vxp),
        "release_mode":bool(a.release),"native_hardened":native_hardened,
        "lua_protection":resource_security.get("lua_protection"),
        "note":single_vxp_policy_note(),
    },indent=2,ensure_ascii=False)+"\n",encoding="utf-8",errors="replace")

    safe_print("[OK] Final VXP SHA-256:",final_sha)
    safe_print("[OK] Compiler profile:",tc.profile_id)
    safe_print("[OK] S30+ compatibility:",compat_profile)
    safe_print("[OK] Entry symbol:",entry_symbol)
    safe_print("[OK] VXP report:",vxp_report_path)
    safe_print("[OK] Sync manifest:",manifest)
    safe_print("[OK] Release manifest:",release_manifest)
    safe_print("[OK] ELF report:",report)

    if a.run and not a.no_run:
        launch_emulator(final_vxp,final_sha,manifest,a.emulator)


if __name__=="__main__":
    configure_utf8_stdio()
    try:
        main()
    except Exception as e:
        configure_utf8_stdio()
        try:
            safe_print("[ERROR]", e, file=sys.stderr)
        except Exception:
            pass
        raise SystemExit(1)
