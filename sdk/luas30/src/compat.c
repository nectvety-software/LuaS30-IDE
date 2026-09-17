#include "abi_private.h"

static ls30_compat_report report;

void ls30_compat_reset(void)
{
    report.compatible=0;
    report.level=LS30_COMPAT_INCOMPATIBLE;
    report.missing_required=0;
    report.native_capabilities=0;
    report.effective_capabilities=0;
    report.fallback_mask=0;
    report.alias_mask=0;
    report.alias_count=0;
}

void ls30_compat_note_alias(unsigned slot)
{
    if(slot<32u) report.alias_mask |= (1u << slot);
    report.alias_count++;
}

static int file_core_native(void)
{
    return ls30_fw.file_open && ls30_fw.file_close &&
           ls30_fw.file_read && ls30_fw.file_write &&
           ls30_fw.file_size && ls30_fw.file_delete;
}

ls30_u32 ls30_native_capabilities(void)
{
    ls30_u32 c=0;
    if(ls30_fw.file_open && ls30_fw.file_close && ls30_fw.file_read &&
       ls30_fw.file_write && ls30_fw.file_size) c|=LS30_CAP_FILES;
    if(ls30_fw.audio_play) c|=LS30_CAP_AUDIO;
    if(ls30_fw.image_load && ls30_fw.image_prop && ls30_fw.image_buffer) c|=LS30_CAP_IMAGES;
    if(ls30_fw.reg_pen) c|=LS30_CAP_TOUCH;
    if(ls30_fw.log_info || ls30_fw.log_error) c|=LS30_CAP_LOG;
    if(ls30_fw.file_rename) c|=LS30_CAP_RENAME;
    if(ls30_fw.removable_drive) c|=LS30_CAP_REMOVABLE;
    if(ls30_fw.string_width && ls30_fw.char_height) c|=LS30_CAP_TEXT_METRICS;
    if(ls30_fw.line) c|=LS30_CAP_LINE;
    if(ls30_fw.set_clip) c|=LS30_CAP_CLIP;
    if(ls30_fw.set_font) c|=LS30_CAP_FONT_SELECT;
    if(ls30_fw.ticks) c|=LS30_CAP_TICKS;
    if(ls30_fw.exit_app) c|=LS30_CAP_EXIT;
    if(ls30_fw.res_init) c|=LS30_CAP_RESOURCE_INIT;
    if(ls30_fw.file_commit) c|=LS30_CAP_FILE_COMMIT;
    return c;
}

ls30_u32 ls30_capabilities(void)
{
    ls30_u32 c=ls30_native_capabilities();

    /* Fallback rename is safe when the core file API and delete exist. */
    if(!(c&LS30_CAP_RENAME) && file_core_native()) c|=LS30_CAP_RENAME;

    /* Software line fallback is available when firmware can fill pixels/rects. */
    if(!(c&LS30_CAP_LINE) && ls30_fw.fill_rect) c|=LS30_CAP_LINE;

    /* Text metrics are estimated when the firmware omits metric helpers. */
    if(!(c&LS30_CAP_TEXT_METRICS) && ls30_fw.textout) c|=LS30_CAP_TEXT_METRICS;

    return c;
}

void ls30_compat_finalize(void)
{
    ls30_u32 missing=0, fb=0;
    ls30_u32 native_caps=ls30_native_capabilities();
    ls30_u32 effective_caps;

    if(!ls30_fw.mem_alloc || !ls30_fw.mem_realloc || !ls30_fw.mem_free)
        missing|=LS30_REQ_MEMORY;
    if(!ls30_fw.reg_system || !ls30_fw.reg_key)
        missing|=LS30_REQ_EVENTS;
    if(!ls30_fw.res_load)
        missing|=LS30_REQ_RESOURCE;
    if(!ls30_fw.timer_create || !ls30_fw.timer_delete)
        missing|=LS30_REQ_TIMER;
    if(!ls30_fw.layer_create || !ls30_fw.layer_buffer)
        missing|=LS30_REQ_LAYER;
    if(!ls30_fw.fill_rect && !ls30_fw.line)
        missing|=LS30_REQ_DRAW;
    if(!ls30_fw.textout)
        missing|=LS30_REQ_TEXT;
    if(!ls30_fw.flush)
        missing|=LS30_REQ_FLUSH;

    if(!ls30_fw.res_init) fb|=LS30_FB_RES_INIT_NOOP;
    if(!ls30_fw.screen_w || !ls30_fw.screen_h) fb|=LS30_FB_SCREEN_240X320;
    if(!ls30_fw.layer_delete) fb|=LS30_FB_LAYER_DELETE_NOOP;
    if(!ls30_fw.set_clip) fb|=LS30_FB_CLIP_NOOP;
    if(!ls30_fw.set_font) fb|=LS30_FB_FONT_NOOP;
    if(!ls30_fw.string_width) fb|=LS30_FB_TEXT_WIDTH_ESTIMATE;
    if(!ls30_fw.char_height) fb|=LS30_FB_FONT_HEIGHT_DEFAULT;
    if(!ls30_fw.line && ls30_fw.fill_rect) fb|=LS30_FB_LINE_FROM_FILL;
    if(!ls30_fw.fill_rect && ls30_fw.line) fb|=LS30_FB_FILL_FROM_LINE;
    if(!ls30_fw.file_commit && (native_caps&LS30_CAP_FILES)) fb|=LS30_FB_FILE_COMMIT_NOOP;
    if(!ls30_fw.file_rename && file_core_native()) fb|=LS30_FB_RENAME_COPY_DELETE;
    if(!ls30_fw.removable_drive && ls30_fw.system_drive) fb|=LS30_FB_REMOVABLE_SYSTEM_DRIVE;
    if(!ls30_fw.audio_stop) fb|=LS30_FB_AUDIO_STOP_NOOP;
    if(!ls30_fw.audio_playing) fb|=LS30_FB_AUDIO_STATE_FALSE;
    if(!ls30_fw.volume) fb|=LS30_FB_AUDIO_VOLUME_NOOP;
    if(!ls30_fw.log_info && !ls30_fw.log_error) fb|=LS30_FB_LOG_NOOP;
    if(!ls30_fw.ticks) fb|=LS30_FB_TICKS_ZERO;
    if(!ls30_fw.exit_app) fb|=LS30_FB_EXIT_NOOP;
    if(!ls30_fw.reg_pen) fb|=LS30_FB_PEN_DISABLED;

    effective_caps=ls30_capabilities();

    report.missing_required=missing;
    report.native_capabilities=native_caps;
    report.effective_capabilities=effective_caps;
    report.fallback_mask=fb;
    report.compatible=(missing==0);
    if(missing) report.level=LS30_COMPAT_INCOMPATIBLE;
    else if(fb || report.alias_count) report.level=LS30_COMPAT_DEGRADED;
    else report.level=LS30_COMPAT_FULL;
}

const ls30_compat_report *ls30_compatibility_report(void){ return &report; }
int ls30_compatibility_level(void){ return report.level; }

const char *ls30_compatibility_level_name(void)
{
    if(report.level==LS30_COMPAT_FULL) return "full";
    if(report.level==LS30_COMPAT_DEGRADED) return "degraded";
    return "incompatible";
}
