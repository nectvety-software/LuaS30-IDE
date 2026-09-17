#include "abi_private.h"
#include <string.h>

ls30_fw_api ls30_fw;
ls30_symbol_resolver ls30_resolver = 0;

void *ls30_resolve_symbol(const char *name)
{
    ls30_int p;
    if (!ls30_resolver || !name) return 0;
    p = ls30_resolver((char*)name);
    if (p == 0 || p == -1) return 0;
    return (void*)(unsigned long)(ls30_u32)p;
}

static void *resolve_aliases(const char *const *names, unsigned alias_slot)
{
    int i=0;
    while(names && names[i]){
        void *p=ls30_resolve_symbol(names[i]);
        if(p){
            if(i>0) ls30_compat_note_alias(alias_slot);
            return p;
        }
        i++;
    }
    return 0;
}

#define BIND(field, type, symbol_name) \
    ls30_fw.field = (type)ls30_resolve_symbol(symbol_name)

#define BIND_ALIASES(field, type, slot, ...) do { \
    static const char *const names[] = { __VA_ARGS__, 0 }; \
    ls30_fw.field=(type)resolve_aliases(names,(slot)); \
} while(0)

int ls30_platform_bind(ls30_symbol_resolver resolver)
{
    memset(&ls30_fw, 0, sizeof(ls30_fw));
    ls30_compat_reset();
    ls30_resolver = resolver;
    if (!resolver) return 0;

    BIND(mem_alloc, void*(*)(ls30_int), "vm_malloc");
    BIND(mem_realloc, void*(*)(void*,ls30_int), "vm_realloc");
    BIND(mem_free, void(*)(void*), "vm_free");

    BIND_ALIASES(reg_system, void(*)(ls30_system_event_cb), 0,
                 "vm_reg_sysevt_callback", "vm_reg_system_event_callback");
    BIND_ALIASES(reg_key, void(*)(ls30_key_event_cb), 1,
                 "vm_reg_keyboard_callback", "vm_reg_key_callback");
    BIND_ALIASES(reg_pen, void(*)(ls30_pen_event_cb), 2,
                 "vm_reg_pen_callback", "vm_reg_touch_callback");

    BIND_ALIASES(ticks, ls30_int(*)(void), 3,
                 "vm_get_tick_count", "vm_get_tick");
    BIND(exit_app, void(*)(void), "vm_exit_app");

    BIND_ALIASES(res_init, ls30_i32(*)(void), 4,
                 "vm_res_init", "vm_resource_init");
    BIND_ALIASES(res_load, ls30_u8*(*)(char*,ls30_int*), 5,
                 "vm_load_resource", "vm_res_load");

    BIND(timer_create, ls30_int(*)(ls30_u32,ls30_timer_cb), "vm_create_timer");
    BIND(timer_delete, ls30_int(*)(ls30_int), "vm_delete_timer");

    BIND_ALIASES(screen_w, ls30_int(*)(void), 6,
                 "vm_graphic_get_screen_width", "vm_graphic_get_screen_w");
    BIND_ALIASES(screen_h, ls30_int(*)(void), 7,
                 "vm_graphic_get_screen_height", "vm_graphic_get_screen_h");
    BIND(layer_create, ls30_int(*)(ls30_int,ls30_int,ls30_int,ls30_int,ls30_int), "vm_graphic_create_layer");
    BIND(layer_delete, ls30_int(*)(ls30_int), "vm_graphic_delete_layer");
    BIND(set_clip, void(*)(ls30_int,ls30_int,ls30_int,ls30_int), "vm_graphic_set_clip");
    BIND(set_font, void(*)(ls30_int), "vm_graphic_set_font");
    BIND(layer_buffer, ls30_u8*(*)(ls30_int), "vm_graphic_get_layer_buffer");
    BIND(fill_rect, void(*)(ls30_u8*,ls30_int,ls30_int,ls30_int,ls30_int,ls30_u16,ls30_u16), "vm_graphic_fill_rect");
    BIND(textout, void(*)(ls30_u8*,ls30_int,ls30_int,ls30_wstr,ls30_int,ls30_u16), "vm_graphic_textout");
    BIND_ALIASES(string_width, ls30_int(*)(ls30_wstr), 8,
                 "vm_graphic_get_string_width", "vm_graphic_get_text_width");
    BIND_ALIASES(char_height, ls30_int(*)(void), 9,
                 "vm_graphic_get_character_height", "vm_graphic_get_font_height");
    BIND(line, void(*)(ls30_u8*,ls30_int,ls30_int,ls30_int,ls30_int,ls30_u16), "vm_graphic_line");
    BIND(flush, ls30_int(*)(ls30_int*,ls30_int), "vm_graphic_flush_layer");

    BIND_ALIASES(image_load, ls30_int(*)(ls30_u8*,ls30_int), 10,
                 "vm_graphic_load_image", "vm_graphic_load_img");
    BIND_ALIASES(image_prop, ls30_image_frame*(*)(ls30_int,ls30_u8), 11,
                 "vm_graphic_get_img_property", "vm_graphic_get_image_property");
    BIND_ALIASES(image_buffer, ls30_u8*(*)(ls30_int), 12,
                 "vm_graphic_get_canvas_buffer", "vm_graphic_get_image_buffer");
    BIND_ALIASES(image_release, void(*)(ls30_int), 13,
                 "vm_graphic_release_canvas", "vm_graphic_release_image");

    BIND(system_drive, ls30_int(*)(void), "vm_get_system_driver");
    BIND_ALIASES(removable_drive, ls30_int(*)(void), 14,
                 "vm_get_removeable_driver", "vm_get_removable_driver");

    BIND(file_open, ls30_file(*)(ls30_cwstr,ls30_uint,ls30_uint), "vm_file_open");
    BIND(file_close, void(*)(ls30_file), "vm_file_close");
    BIND(file_read, ls30_int(*)(ls30_file,void*,ls30_uint,ls30_uint*), "vm_file_read");
    BIND(file_write, ls30_int(*)(ls30_file,void*,ls30_uint,ls30_uint*), "vm_file_write");
    BIND(file_commit, ls30_int(*)(ls30_file), "vm_file_commit");
    BIND_ALIASES(file_size, ls30_int(*)(ls30_file,ls30_uint*), 15,
                 "vm_file_getfilesize", "vm_file_get_file_size");
    BIND(file_delete, ls30_int(*)(ls30_cwstr), "vm_file_delete");
    BIND(file_rename, ls30_int(*)(ls30_cwstr,ls30_cwstr), "vm_file_rename");

    /* Audio aliases are deliberately conservative: alternate functions with
     * different callback/blocking signatures are not treated as ABI aliases. */
    BIND(audio_play, ls30_int(*)(void*,ls30_uint,ls30_u8,ls30_uint,ls30_audio_cb), "vm_audio_play_bytes_no_block");
    BIND(audio_stop, ls30_int(*)(void), "vm_audio_stop_all");
    BIND(audio_playing, ls30_bool(*)(void), "vm_audio_is_app_playing");
    BIND(volume, void(*)(ls30_int), "vm_set_volume");

    BIND_ALIASES(log_info, void(*)(const char*,...), 16,
                 "_vm_log_info", "vm_log_info");
    BIND_ALIASES(log_error, void(*)(const char*,...), 17,
                 "_vm_log_error", "vm_log_error");

    ls30_compat_finalize();
    ls30_device_refresh();
    return ls30_platform_ready();
}
