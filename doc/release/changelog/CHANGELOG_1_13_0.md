# LuaS30 Engine 1.13.0 — MediaTek MRE Project Wizard

- Replaced the old one-line New Project name prompt with a custom MediaTek MRE SDK modal.
- Added APPNAME, APPVER and VENDOR fields.
- Added screen-resolution preset selection.
- Added MTK6260, MTK6261, MTK6250 and MTK6225 presets.
- Added Heap RAM presets with chipset-specific recommended defaults.
- New Project is not created until `Lưu thiết lập` succeeds.
- Every project still receives a fresh unique AppID.
- Wizard metadata is stored in `project.json` and `.luas30/mre_sdk.json`.
- MTK6260 selects the Nokia 225 RM-1011 compatibility profile by default.
- Fixed build profile resolution so project `compat_profile` is honored when CLI/Studio is `auto`.
- Fixed the v1.12 build-order bug where `compat_profile` could be referenced before resolution.
- Added APPVER and MediaTek chipset to build/release manifests.
