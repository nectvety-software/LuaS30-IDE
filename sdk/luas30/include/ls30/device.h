#ifndef LS30_DEVICE_H
#define LS30_DEVICE_H
#include "base.h"

#define LS30_CAP_FILES       (1u << 0)
#define LS30_CAP_AUDIO       (1u << 1)
#define LS30_CAP_IMAGES      (1u << 2)
#define LS30_CAP_TOUCH       (1u << 3)
#define LS30_CAP_LOG         (1u << 4)
#define LS30_CAP_RENAME      (1u << 5)
#define LS30_CAP_REMOVABLE   (1u << 6)
#define LS30_CAP_TEXT_METRICS (1u << 7)
#define LS30_CAP_LINE         (1u << 8)
#define LS30_CAP_CLIP         (1u << 9)
#define LS30_CAP_FONT_SELECT  (1u << 10)
#define LS30_CAP_TICKS        (1u << 11)
#define LS30_CAP_EXIT         (1u << 12)
#define LS30_CAP_RESOURCE_INIT (1u << 13)
#define LS30_CAP_FILE_COMMIT  (1u << 14)

typedef struct ls30_device_profile {
    const char *family;
    int screen_width;
    int screen_height;
    int preferred_fps;
    int recommended_ram_kb;
    ls30_u32 capabilities;
    ls30_u32 native_capabilities;
    ls30_u32 fallback_mask;
    ls30_u32 missing_required;
    int abi_alias_count;
    int compatibility_level;
} ls30_device_profile;

const ls30_device_profile *ls30_device_current(void);
void ls30_device_refresh(void);
#endif
