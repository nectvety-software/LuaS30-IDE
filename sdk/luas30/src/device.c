#include "ls30/api.h"

static ls30_device_profile current = {
    "generic-vxp", 240, 320, 15, 1536, 0, 0, 0, 0, 0, LS30_COMPAT_INCOMPATIBLE
};

const ls30_device_profile *ls30_device_current(void){ return &current; }

void ls30_device_refresh(void)
{
    int w=ls30_screen_width(), h=ls30_screen_height();
    const ls30_compat_report *r=ls30_compatibility_report();

    current.screen_width = w > 0 ? w : 240;
    current.screen_height = h > 0 ? h : 320;
    current.capabilities = ls30_capabilities();
    current.native_capabilities = ls30_native_capabilities();
    current.fallback_mask = r ? r->fallback_mask : 0;
    current.missing_required = r ? r->missing_required : 0;
    current.abi_alias_count = r ? r->alias_count : 0;
    current.compatibility_level = r ? r->level : LS30_COMPAT_INCOMPATIBLE;

    if(current.screen_width==240 && current.screen_height==320){
        current.family="qvga-240x320";
        current.preferred_fps=current.compatibility_level==LS30_COMPAT_DEGRADED?12:15;
        current.recommended_ram_kb=1536;
    }else if(current.screen_width<=176 && current.screen_height<=220){
        current.family="small-vxp";
        current.preferred_fps=12;
        current.recommended_ram_kb=1024;
    }else{
        current.family="generic-vxp";
        current.preferred_fps=current.compatibility_level==LS30_COMPAT_DEGRADED?12:15;
        current.recommended_ram_kb=2048;
    }
}
