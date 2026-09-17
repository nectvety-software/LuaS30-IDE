#include "abi_private.h"

int ls30_platform_ready(void)
{
    const ls30_compat_report *r=ls30_compatibility_report();
    return r && r->compatible;
}

void *ls30_alloc(int n){ return ls30_fw.mem_alloc ? ls30_fw.mem_alloc(n) : 0; }
void *ls30_realloc(void *p,int n){ return ls30_fw.mem_realloc ? ls30_fw.mem_realloc(p,n) : 0; }
void ls30_free(void *p){ if(p && ls30_fw.mem_free) ls30_fw.mem_free(p); }
int ls30_ticks(void){ return ls30_fw.ticks ? ls30_fw.ticks() : 0; }
void ls30_exit(void){ if(ls30_fw.exit_app) ls30_fw.exit_app(); }

void ls30_on_system(ls30_system_event_cb cb){ if(ls30_fw.reg_system) ls30_fw.reg_system(cb); }
void ls30_on_key(ls30_key_event_cb cb){ if(ls30_fw.reg_key) ls30_fw.reg_key(cb); }
void ls30_on_pen(ls30_pen_event_cb cb){ if(ls30_fw.reg_pen) ls30_fw.reg_pen(cb); }
int ls30_timer_start(unsigned ms,ls30_timer_cb cb){ return ls30_fw.timer_create ? ls30_fw.timer_create(ms,cb) : -1; }
void ls30_timer_stop(int id){ if(id>=0 && ls30_fw.timer_delete) ls30_fw.timer_delete(id); }

int ls30_resource_init(void){ return ls30_fw.res_init ? ls30_fw.res_init() : 0; }
ls30_u8 *ls30_resource_load(const char *name,int *size){
    ls30_int n=0; ls30_u8 *p;
    if(size)*size=0;
    if(!ls30_fw.res_load || !name) return 0;
    p=ls30_fw.res_load((char*)name,&n);
    if(size)*size=n;
    return p;
}

int ls30_screen_width(void){ return ls30_fw.screen_w ? ls30_fw.screen_w() : 240; }
int ls30_screen_height(void){ return ls30_fw.screen_h ? ls30_fw.screen_h() : 320; }
int ls30_layer_create(int x,int y,int w,int h,int t){ return ls30_fw.layer_create ? ls30_fw.layer_create(x,y,w,h,t) : -1; }
void ls30_layer_delete(int l){ if(ls30_fw.layer_delete) ls30_fw.layer_delete(l); }
ls30_u8 *ls30_layer_buffer(int l){ return ls30_fw.layer_buffer ? ls30_fw.layer_buffer(l) : 0; }
void ls30_clip(int a,int b,int c,int d){ if(ls30_fw.set_clip) ls30_fw.set_clip(a,b,c,d); }
void ls30_font(int f){ if(ls30_fw.set_font) ls30_fw.set_font(f); }

static void software_line_from_fill(ls30_u8 *b,int x0,int y0,int x1,int y1,ls30_u16 c)
{
    int dx=x1>x0?x1-x0:x0-x1;
    int sx=x0<x1?1:-1;
    int dy=-(y1>y0?y1-y0:y0-y1);
    int sy=y0<y1?1:-1;
    int err=dx+dy;
    for(;;){
        ls30_fw.fill_rect(b,x0,y0,1,1,c,c);
        if(x0==x1 && y0==y1) break;
        {
            int e2=2*err;
            if(e2>=dy){err+=dy;x0+=sx;}
            if(e2<=dx){err+=dx;y0+=sy;}
        }
    }
}

static void software_fill_from_line(ls30_u8 *b,int x,int y,int w,int h,ls30_u16 c)
{
    int row;
    if(w<=0||h<=0)return;
    for(row=0;row<h;row++) ls30_fw.line(b,x,y+row,x+w-1,y+row,c);
}

void ls30_fill(ls30_u8*b,int x,int y,int w,int h,ls30_u16 l,ls30_u16 c)
{
    (void)l;
    if(ls30_fw.fill_rect) ls30_fw.fill_rect(b,x,y,w,h,l,c);
    else if(ls30_fw.line) software_fill_from_line(b,x,y,w,h,c);
}

void ls30_text(ls30_u8*b,int x,int y,ls30_wstr s,int n,ls30_u16 c)
{
    if(ls30_fw.textout)ls30_fw.textout(b,x,y,s,n,c);
}

int ls30_text_width(ls30_wstr s)
{
    int n=0;
    if(ls30_fw.string_width)return ls30_fw.string_width(s);
    if(!s)return 0;
    while(s[n])n++;
    return n*6;
}

int ls30_font_height(void){ return ls30_fw.char_height ? ls30_fw.char_height() : 10; }

void ls30_line(ls30_u8*b,int x0,int y0,int x1,int y1,ls30_u16 c)
{
    if(ls30_fw.line)ls30_fw.line(b,x0,y0,x1,y1,c);
    else if(ls30_fw.fill_rect)software_line_from_fill(b,x0,y0,x1,y1,c);
}

int ls30_flush(int *layers,int n){ return ls30_fw.flush ? ls30_fw.flush(layers,n) : -1; }

int ls30_image_open(ls30_u8*d,int n){ return ls30_fw.image_load ? ls30_fw.image_load(d,n) : -1; }
ls30_image_frame *ls30_image_frame_info(int c,ls30_u8 f){ return ls30_fw.image_prop ? ls30_fw.image_prop(c,f) : 0; }
ls30_u8 *ls30_image_pixels(int c){ return ls30_fw.image_buffer ? ls30_fw.image_buffer(c) : 0; }
void ls30_image_close(int c){ if(ls30_fw.image_release)ls30_fw.image_release(c); }

int ls30_system_drive(void){ return ls30_fw.system_drive ? ls30_fw.system_drive() : -1; }
int ls30_removable_drive(void)
{
    if(ls30_fw.removable_drive)return ls30_fw.removable_drive();
    return ls30_fw.system_drive ? ls30_fw.system_drive() : -1;
}

ls30_file ls30_file_open(ls30_cwstr p,ls30_uint m,ls30_uint b){ return ls30_fw.file_open ? ls30_fw.file_open(p,m,b) : -1; }
void ls30_file_close(ls30_file f){ if(ls30_fw.file_close)ls30_fw.file_close(f); }
int ls30_file_read(ls30_file f,void*d,ls30_uint n,ls30_uint*r){ return ls30_fw.file_read ? ls30_fw.file_read(f,d,n,r) : -1; }
int ls30_file_write(ls30_file f,void*d,ls30_uint n,ls30_uint*w){ return ls30_fw.file_write ? ls30_fw.file_write(f,d,n,w) : -1; }
int ls30_file_commit(ls30_file f){ return ls30_fw.file_commit ? ls30_fw.file_commit(f) : 0; }
int ls30_file_size(ls30_file f,ls30_uint*s){ return ls30_fw.file_size ? ls30_fw.file_size(f,s) : -1; }
int ls30_file_delete(ls30_cwstr p){ return ls30_fw.file_delete ? ls30_fw.file_delete(p) : -1; }

static int fallback_file_rename(ls30_cwstr a,ls30_cwstr b)
{
    unsigned char buf[256];
    ls30_file in,out;
    ls30_uint got=0,wrote=0;
    int status=0;

    if(!ls30_fw.file_open || !ls30_fw.file_close || !ls30_fw.file_read ||
       !ls30_fw.file_write || !ls30_fw.file_delete)return -1;

    in=ls30_fw.file_open(a,LS30_FILE_READ,1);
    if(in<0)return -1;
    out=ls30_fw.file_open(b,LS30_FILE_CREATE_ALWAYS_WRITE,1);
    if(out<0){ls30_fw.file_close(in);return -1;}

    for(;;){
        got=0;
        status=ls30_fw.file_read(in,buf,(ls30_uint)sizeof(buf),&got);
        if(status<0)break;
        if(got==0){status=0;break;}
        wrote=0;
        if(ls30_fw.file_write(out,buf,got,&wrote)<0 || wrote!=got){status=-1;break;}
    }

    if(status==0 && ls30_fw.file_commit)ls30_fw.file_commit(out);
    ls30_fw.file_close(out);
    ls30_fw.file_close(in);

    if(status==0){
        if(ls30_fw.file_delete(a)<0)return -1;
        return 0;
    }
    if(ls30_fw.file_delete)ls30_fw.file_delete(b);
    return -1;
}

int ls30_file_rename(ls30_cwstr a,ls30_cwstr b)
{
    if(ls30_fw.file_rename)return ls30_fw.file_rename(a,b);
    return fallback_file_rename(a,b);
}

int ls30_audio_play(void*d,ls30_uint n,ls30_u8 f,ls30_uint p,ls30_audio_cb cb)
{
    return ls30_fw.audio_play ? ls30_fw.audio_play(d,n,f,p,cb) : -1;
}
void ls30_audio_stop(void){ if(ls30_fw.audio_stop)ls30_fw.audio_stop(); }
int ls30_audio_playing(void){ return ls30_fw.audio_playing ? !!ls30_fw.audio_playing() : 0; }
void ls30_audio_volume(int v){ if(v<0)v=0;if(v>6)v=6;if(ls30_fw.volume)ls30_fw.volume(v); }

void ls30_log_info(const char *s){ if(s && ls30_fw.log_info)ls30_fw.log_info("%s",s); }
void ls30_log_error(const char *s){ if(s && ls30_fw.log_error)ls30_fw.log_error("%s",s); }
