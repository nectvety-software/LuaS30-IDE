#ifndef LS30_GRAPHICS_H
#define LS30_GRAPHICS_H
#include "base.h"

#define LS30_FONT_SMALL      0
#define LS30_FONT_MEDIUM     1
#define LS30_FONT_LARGE      2
#define LS30_NO_TRANS_COLOR  (-1)
#define LS30_CANVAS_DATA_OFFSET 32

#define LS30_COLOR_BLACK 0x0000u
#define LS30_COLOR_WHITE 0xFFFFu
#define LS30_RGB565(r,g,b) ((ls30_u16)(((((r)&0xF8) + (((g)&0xE0)>>5))<<8) + (((g)&0x1C)<<3) + ((b)>>3)))

typedef struct ls30_image_frame {
    ls30_u8  flag;
    ls30_u16 left;
    ls30_u16 top;
    ls30_u16 width;
    ls30_u16 height;
    ls30_u16 delay_time;
    ls30_u8  trans_color_index;
    ls30_u16 trans_color;
    ls30_u32 offset;
} ls30_image_frame;
#endif
