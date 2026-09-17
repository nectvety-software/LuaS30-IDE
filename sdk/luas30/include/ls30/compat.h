#ifndef LS30_COMPAT_H
#define LS30_COMPAT_H
#include "base.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Compatibility level after ABI resolution and fallback planning. */
#define LS30_COMPAT_INCOMPATIBLE 0
#define LS30_COMPAT_DEGRADED     1
#define LS30_COMPAT_FULL         2

/* Required runtime groups. Missing bits make the runtime incompatible. */
#define LS30_REQ_MEMORY      (1u << 0)
#define LS30_REQ_EVENTS      (1u << 1)
#define LS30_REQ_RESOURCE    (1u << 2)
#define LS30_REQ_TIMER       (1u << 3)
#define LS30_REQ_LAYER       (1u << 4)
#define LS30_REQ_DRAW        (1u << 5)
#define LS30_REQ_TEXT        (1u << 6)
#define LS30_REQ_FLUSH       (1u << 7)

/* Transparent fallback paths used when a firmware API is absent. */
#define LS30_FB_RES_INIT_NOOP          (1u << 0)
#define LS30_FB_SCREEN_240X320         (1u << 1)
#define LS30_FB_LAYER_DELETE_NOOP      (1u << 2)
#define LS30_FB_CLIP_NOOP              (1u << 3)
#define LS30_FB_FONT_NOOP              (1u << 4)
#define LS30_FB_TEXT_WIDTH_ESTIMATE    (1u << 5)
#define LS30_FB_FONT_HEIGHT_DEFAULT    (1u << 6)
#define LS30_FB_LINE_FROM_FILL         (1u << 7)
#define LS30_FB_FILL_FROM_LINE         (1u << 8)
#define LS30_FB_FILE_COMMIT_NOOP       (1u << 9)
#define LS30_FB_RENAME_COPY_DELETE     (1u << 10)
#define LS30_FB_REMOVABLE_SYSTEM_DRIVE (1u << 11)
#define LS30_FB_AUDIO_STOP_NOOP        (1u << 12)
#define LS30_FB_AUDIO_STATE_FALSE      (1u << 13)
#define LS30_FB_AUDIO_VOLUME_NOOP      (1u << 14)
#define LS30_FB_LOG_NOOP               (1u << 15)
#define LS30_FB_TICKS_ZERO             (1u << 16)
#define LS30_FB_EXIT_NOOP               (1u << 17)
#define LS30_FB_PEN_DISABLED            (1u << 18)

typedef struct ls30_compat_report {
    int compatible;
    int level;
    ls30_u32 missing_required;
    ls30_u32 native_capabilities;
    ls30_u32 effective_capabilities;
    ls30_u32 fallback_mask;
    ls30_u32 alias_mask;
    int alias_count;
} ls30_compat_report;

void ls30_compat_reset(void);
void ls30_compat_note_alias(unsigned slot);
void ls30_compat_finalize(void);
const ls30_compat_report *ls30_compatibility_report(void);
int ls30_compatibility_level(void);
const char *ls30_compatibility_level_name(void);

#ifdef __cplusplus
}
#endif
#endif
