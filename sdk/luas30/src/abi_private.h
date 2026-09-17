#ifndef LS30_ABI_PRIVATE_H
#define LS30_ABI_PRIVATE_H
#include "ls30/api.h"

/* Internal firmware ABI table. These function names are resolved at runtime;
 * no vendor MRE header or static library is linked into the application.
 */
typedef struct ls30_fw_api {
    void*  (*mem_alloc)(ls30_int size);
    void*  (*mem_realloc)(void *p, ls30_int size);
    void   (*mem_free)(void *p);
    void   (*reg_system)(ls30_system_event_cb cb);
    void   (*reg_key)(ls30_key_event_cb cb);
    void   (*reg_pen)(ls30_pen_event_cb cb);
    ls30_int (*ticks)(void);
    void   (*exit_app)(void);

    ls30_i32 (*res_init)(void);
    ls30_u8* (*res_load)(char *name, ls30_int *size);

    ls30_int (*timer_create)(ls30_u32 ms, ls30_timer_cb cb);
    ls30_int (*timer_delete)(ls30_int id);

    ls30_int (*screen_w)(void);
    ls30_int (*screen_h)(void);
    ls30_int (*layer_create)(ls30_int,ls30_int,ls30_int,ls30_int,ls30_int);
    ls30_int (*layer_delete)(ls30_int);
    void (*set_clip)(ls30_int,ls30_int,ls30_int,ls30_int);
    void (*set_font)(ls30_int);
    ls30_u8* (*layer_buffer)(ls30_int);
    void (*fill_rect)(ls30_u8*,ls30_int,ls30_int,ls30_int,ls30_int,ls30_u16,ls30_u16);
    void (*textout)(ls30_u8*,ls30_int,ls30_int,ls30_wstr,ls30_int,ls30_u16);
    ls30_int (*string_width)(ls30_wstr);
    ls30_int (*char_height)(void);
    void (*line)(ls30_u8*,ls30_int,ls30_int,ls30_int,ls30_int,ls30_u16);
    ls30_int (*flush)(ls30_int*,ls30_int);

    ls30_int (*image_load)(ls30_u8*,ls30_int);
    ls30_image_frame* (*image_prop)(ls30_int,ls30_u8);
    ls30_u8* (*image_buffer)(ls30_int);
    void (*image_release)(ls30_int);

    ls30_int (*system_drive)(void);
    ls30_int (*removable_drive)(void);
    ls30_file (*file_open)(ls30_cwstr,ls30_uint,ls30_uint);
    void (*file_close)(ls30_file);
    ls30_int (*file_read)(ls30_file,void*,ls30_uint,ls30_uint*);
    ls30_int (*file_write)(ls30_file,void*,ls30_uint,ls30_uint*);
    ls30_int (*file_commit)(ls30_file);
    ls30_int (*file_size)(ls30_file,ls30_uint*);
    ls30_int (*file_delete)(ls30_cwstr);
    ls30_int (*file_rename)(ls30_cwstr,ls30_cwstr);

    ls30_int (*audio_play)(void*,ls30_uint,ls30_u8,ls30_uint,ls30_audio_cb);
    ls30_int (*audio_stop)(void);
    ls30_bool (*audio_playing)(void);
    void (*volume)(ls30_int);

    void (*log_info)(const char*,...);
    void (*log_error)(const char*,...);
} ls30_fw_api;

extern ls30_fw_api ls30_fw;
extern ls30_symbol_resolver ls30_resolver;
void *ls30_resolve_symbol(const char *name);
#endif
