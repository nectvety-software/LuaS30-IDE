#ifndef LS30_API_H
#define LS30_API_H

#include "base.h"
#include "events.h"
#include "graphics.h"
#include "filesystem.h"
#include "audio.h"
#include "device.h"
#include "compat.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Platform bootstrap. The resolver is supplied by the target VXP runtime. */
int ls30_platform_bind(ls30_symbol_resolver resolver);
int ls30_platform_ready(void);
ls30_u32 ls30_capabilities(void);
ls30_u32 ls30_native_capabilities(void);

/* Memory / process */
void *ls30_alloc(int size);
void *ls30_realloc(void *ptr, int size);
void  ls30_free(void *ptr);
int   ls30_ticks(void);
void  ls30_exit(void);

/* Events / timers */
void ls30_on_system(ls30_system_event_cb cb);
void ls30_on_key(ls30_key_event_cb cb);
void ls30_on_pen(ls30_pen_event_cb cb);
int  ls30_timer_start(unsigned ms, ls30_timer_cb cb);
void ls30_timer_stop(int timer_id);

/* Resource */
int      ls30_resource_init(void);
ls30_u8 *ls30_resource_load(const char *name, int *size);

/* Graphics */
int      ls30_screen_width(void);
int      ls30_screen_height(void);
int      ls30_layer_create(int x, int y, int w, int h, int transparent);
void     ls30_layer_delete(int layer);
ls30_u8 *ls30_layer_buffer(int layer);
void     ls30_clip(int x1, int y1, int x2, int y2);
void     ls30_font(int font);
void     ls30_fill(ls30_u8 *buf, int x, int y, int w, int h, ls30_u16 line, ls30_u16 back);
void     ls30_text(ls30_u8 *buf, int x, int y, ls30_wstr text, int len, ls30_u16 color);
int      ls30_text_width(ls30_wstr text);
int      ls30_font_height(void);
void     ls30_line(ls30_u8 *buf, int x0, int y0, int x1, int y1, ls30_u16 color);
int      ls30_flush(int *layers, int count);

int               ls30_image_open(ls30_u8 *data, int len);
ls30_image_frame *ls30_image_frame_info(int canvas, ls30_u8 frame);
ls30_u8          *ls30_image_pixels(int canvas);
void              ls30_image_close(int canvas);

/* Files */
int      ls30_system_drive(void);
int      ls30_removable_drive(void);
ls30_file ls30_file_open(ls30_cwstr path, ls30_uint mode, ls30_uint binary);
void      ls30_file_close(ls30_file file);
int       ls30_file_read(ls30_file file, void *data, ls30_uint len, ls30_uint *read_count);
int       ls30_file_write(ls30_file file, void *data, ls30_uint len, ls30_uint *write_count);
int       ls30_file_commit(ls30_file file);
int       ls30_file_size(ls30_file file, ls30_uint *size);
int       ls30_file_delete(ls30_cwstr path);
int       ls30_file_rename(ls30_cwstr old_path, ls30_cwstr new_path);

/* Audio */
int  ls30_audio_play(void *data, ls30_uint len, ls30_u8 format, ls30_uint path, ls30_audio_cb cb);
void ls30_audio_stop(void);
int  ls30_audio_playing(void);
void ls30_audio_volume(int volume);

/* Helpers implemented by the SDK itself. */
int       ls30_ascii_to_ucs2(ls30_wchar *dst, int cap, const char *src);
ls30_u16  ls30_color565(int r, int g, int b);
void      ls30_log_info(const char *text);
void      ls30_log_error(const char *text);

#ifdef __cplusplus
}
#endif
#endif
