# LuaS30 Engine 1.12.0 — Series 30+ High Compatibility

- Added S30+ compatibility profiles: auto, standalone, s30plus-native, nokia225-rm1011.
- Added native MRE SDK layout detection.
- Added ARM GCC high-compatibility MRE compile defines.
- Added native linking against local MRE SDK per*.a libraries and SDK scat.ld.
- Added explicit `vm_main()` application entry.
- Changed loader flow to `gcc_entry -> vm_main -> LuaS30 runtime`.
- Added Nokia 225 Dual SIM RM-1011 profile.
- Added project MRE API tag support.
- Added optional session-only Nokia IMSI install binding.
- Added `build/device/*.nokia225.vxp` install artifact without persisting IMSI.
- Added `s30plus_doctor.py`.
- Added Settings controls for S30+ profile, MRE SDK root and session-only IMSI.
- Updated basic/device-probe templates for S30+ metadata.
