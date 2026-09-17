# LuaS30 Engine 1.10.0 — Multi-Toolchain MRE Profiles

- Added `tools/toolchain_profiles.py`.
- Added ARM GCC, RVDS/RVCT and ARM ADS1.2 compiler profiles.
- Added `--compiler-profile auto|gcc|rvds|ads12`.
- Added `--entry-symbol` override.
- Added nested toolchain detection for gcc/readelf, armcc/armlink/fromelf and tcc.
- Added RVDS MRE flags and `rvct_entry`.
- Added ADS1.2 compatibility flags and `ads_entry`.
- Added shared runtime bootstrap for gcc_entry / rvct_entry / ads_entry.
- Added ARMCC/ADS ELF verification without GNU readelf.
- Updated VXP entry extraction to understand all three entry symbols.
- Rebuilt Toolchain Doctor around the selected compiler profile.
- Added Settings compiler-profile selector and toolchain-root browser.
- BuildService and Toolchain Doctor now share the Settings selection.
- ARM GCC remains the bundled validated path; ADS/RVDS binaries are not bundled.
