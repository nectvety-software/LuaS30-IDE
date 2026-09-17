#ifndef LS30_BASE_H
#define LS30_BASE_H

#ifdef __cplusplus
extern "C" {
#endif

typedef signed char        ls30_i8;
typedef unsigned char      ls30_u8;
typedef signed short       ls30_i16;
typedef unsigned short     ls30_u16;
typedef signed int         ls30_i32;
typedef unsigned int       ls30_u32;
typedef int                ls30_int;
typedef unsigned int       ls30_uint;
typedef int                ls30_bool;
typedef int                ls30_file;
typedef unsigned short     ls30_wchar;
typedef ls30_wchar*        ls30_wstr;
typedef const ls30_wchar*  ls30_cwstr;

typedef ls30_int (*ls30_symbol_resolver)(char *name);
typedef void (*ls30_system_event_cb)(ls30_int message, ls30_int param);
typedef void (*ls30_key_event_cb)(ls30_int event, ls30_int keycode);
typedef void (*ls30_pen_event_cb)(ls30_int event, ls30_int x, ls30_int y);
typedef void (*ls30_timer_cb)(ls30_int timer_id);
typedef void (*ls30_audio_cb)(ls30_int result);

#define LS30_TRUE  1
#define LS30_FALSE 0

#ifdef __cplusplus
}
#endif
#endif
