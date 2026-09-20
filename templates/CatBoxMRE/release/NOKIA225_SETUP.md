# CatBoxMRE — LuaS30 IDE 1.15 / Nokia 225 Dual SIM setup

Use these exact MediaTek MRE SDK wizard values:

- APPNAME: `CatBoxMRE`
- APPVER: `0.1.3`
- VENDOR: `VXPstore / Qeafivels Software`
- Resolution: `240x320 (QVGA / Nokia default)`
- Chipset: `MTK6260 (Nokia 220 / Nokia 225)`
- Heap RAM: `768 KB`
- Compatibility profile: `nokia225-rm1011`
- MRE API: `Audio File ProMng`
- Device: `Nokia 225 Dual SIM / RM-1011`

## Important IDE workflow

1. In LuaS30 IDE 1.15 choose **File -> New Project**.
2. Fill the values above and press **Lưu thiết lập**.
3. The managed project must be under `Documents\\LuaS30Engine\\CatBoxMRE`.
4. Close the generated project.
5. Copy this package contents into that generated `CatBoxMRE` directory **without deleting the hidden `.luas30` directory**.
6. Re-open the project in LuaS30 IDE.
7. Run `tools\\check_nokia225_config.py` before Build/Run.
8. The project should report `nokia225-rm1011`, not a Generic compatibility profile.

The `.luas30/mre_sdk.json` in this package mirrors the same Nokia 225 settings so a normal folder open/import also has the Studio metadata available.

## If the IDE still says Generic

Do not trust the current Build/Run session. Re-create the project with the wizard and copy the CatBox files into the managed folder. The New Project wizard is the authoritative path for producing the Studio-side MRE metadata.

## Emulator vs phone

VXPEmu is still an emulator. Nokia 225 retail firmware may additionally require the real MRE SDK build path and phone install signing/binding. Do not use emulator success as proof that the physical RM-1011 will accept the package.


## Low-memory profile

This build intentionally requests **768 KB** instead of 1024 KB. On MRE, the VXP heap reservation is fixed at startup; requesting too much can fail before Lua reaches the first frame. The runtime is also trimmed to the v0.3 stable feature core and uses smaller fixed pools.
