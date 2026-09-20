#include "ls30/api.h"
#include "luas30_runtime.h"
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include <string.h>

#define LS30_IMAGE_CACHE_MAX 12
#define LS30_NAME_MAX 96
#define LS30_TEXT_MAX 128
#define LS30_FILE_MAX 196608u

typedef struct cm_image {
    char name[LS30_NAME_MAX];
    int canvas;
    int w, h;
    ls30_u8 *pixels;
    ls30_u16 key;
    int has_key;
} cm_image;

static ls30_u8 *g_buf = 0;
static int g_w = 240, g_h = 320;
static int g_layer = -1;
static cm_image g_images[LS30_IMAGE_CACHE_MAX];
static int g_image_count = 0;
static ls30_u8 *g_audio_data = 0;
static int g_audio_size = 0;

void luas30_bridge_set_frame(ls30_u8 *buf, int w, int h, int layer)
{
    g_buf = buf; g_w = w; g_h = h; g_layer = layer;
}

static int clip_ok(int x, int y, int w, int h)
{
    return w > 0 && h > 0 && x < g_w && y < g_h && x + w > 0 && y + h > 0;
}

static ls30_u16 lua_color(lua_State *L, int idx)
{
    int top = lua_gettop(L);
    if (top >= idx + 2 && lua_isnumber(L, idx + 1) && lua_isnumber(L, idx + 2))
        return ls30_color565((int)lua_tonumber(L,idx),(int)lua_tonumber(L,idx+1),(int)lua_tonumber(L,idx+2));
    return (ls30_u16)luaL_checknumber(L, idx);
}

static int l_color(lua_State *L)
{
    lua_pushnumber(L, ls30_color565((int)luaL_checknumber(L,1),(int)luaL_checknumber(L,2),(int)luaL_checknumber(L,3)));
    return 1;
}

static int l_clear(lua_State *L)
{
    ls30_u16 c = lua_color(L,1);
    if (g_buf) ls30_fill(g_buf,0,0,g_w,g_h,c,c);
    return 0;
}

static int l_rect(lua_State *L)
{
    int x=(int)luaL_checknumber(L,1), y=(int)luaL_checknumber(L,2);
    int w=(int)luaL_checknumber(L,3), h=(int)luaL_checknumber(L,4);
    ls30_u16 c=lua_color(L,5);
    if (g_buf && clip_ok(x,y,w,h)) ls30_fill(g_buf,x,y,w,h,c,c);
    return 0;
}

static int l_frame(lua_State *L)
{
    int x=(int)luaL_checknumber(L,1), y=(int)luaL_checknumber(L,2);
    int w=(int)luaL_checknumber(L,3), h=(int)luaL_checknumber(L,4);
    ls30_u16 c=lua_color(L,5);
    if (!g_buf || w <= 0 || h <= 0) return 0;
    if (clip_ok(x,y,w,1)) ls30_fill(g_buf,x,y,w,1,c,c);
    if (clip_ok(x,y+h-1,w,1)) ls30_fill(g_buf,x,y+h-1,w,1,c,c);
    if (clip_ok(x,y,1,h)) ls30_fill(g_buf,x,y,1,h,c,c);
    if (clip_ok(x+w-1,y,1,h)) ls30_fill(g_buf,x+w-1,y,1,h,c,c);
    return 0;
}

static int l_line(lua_State *L)
{
    if (g_buf)
        ls30_line(g_buf,(int)luaL_checknumber(L,1),(int)luaL_checknumber(L,2),
                           (int)luaL_checknumber(L,3),(int)luaL_checknumber(L,4),lua_color(L,5));
    return 0;
}

static int l_text(lua_State *L)
{
    int x=(int)luaL_checknumber(L,1), y=(int)luaL_checknumber(L,2);
    const char *s=luaL_checkstring(L,3);
    ls30_u16 color = lua_gettop(L) >= 4 ? lua_color(L,4) : LS30_COLOR_WHITE;
    ls30_wchar ws[LS30_TEXT_MAX];
    int n;
    if (!g_buf) return 0;
    n=ls30_ascii_to_ucs2(ws,LS30_TEXT_MAX,s);
    ls30_text(g_buf,x,y,ws,n,color);
    return 0;
}

static int l_set_font(lua_State *L)
{
    int n=(int)luaL_optnumber(L,1,8);
    ls30_font(n <= 8 ? LS30_FONT_SMALL : (n <= 12 ? LS30_FONT_MEDIUM : LS30_FONT_LARGE));
    return 0;
}

static int l_text_width(lua_State *L)
{
    ls30_wchar ws[LS30_TEXT_MAX];
    ls30_ascii_to_ucs2(ws,LS30_TEXT_MAX,luaL_checkstring(L,1));
    lua_pushnumber(L, ls30_text_width(ws));
    return 1;
}

static int l_font_height(lua_State *L)
{
    lua_pushnumber(L, ls30_font_height());
    return 1;
}

static cm_image *image_find(const char *name)
{
    int i;
    for (i=0;i<g_image_count;i++) if (strcmp(g_images[i].name,name)==0) return &g_images[i];
    return 0;
}

static cm_image *image_load(const char *name)
{
    int size=0, canvas;
    ls30_u8 *res, *cbuf;
    ls30_image_frame *fp;
    cm_image *im;
    size_t n;
    if (!(ls30_capabilities() & LS30_CAP_IMAGES) || g_image_count >= LS30_IMAGE_CACHE_MAX) return 0;
    res=ls30_resource_load(name,&size);
    if (!res || size<=0) return 0;
    canvas=ls30_image_open(res,size);
    ls30_free(res);
    if (canvas<0) return 0;
    fp=ls30_image_frame_info(canvas,0);
    cbuf=ls30_image_pixels(canvas);
    if (!fp || !cbuf) { ls30_image_close(canvas); return 0; }
    im=&g_images[g_image_count++];
    memset(im,0,sizeof(*im));
    n=strlen(name); if(n>=LS30_NAME_MAX)n=LS30_NAME_MAX-1;
    memcpy(im->name,name,n); im->name[n]=0;
    im->canvas=canvas; im->w=fp->width; im->h=fp->height;
    im->pixels=cbuf+LS30_CANVAS_DATA_OFFSET;
    im->key=fp->trans_color; im->has_key=(fp->trans_color_index != 0xFFu);
    return im;
}

static void blit_region(cm_image *im,int sx,int sy,int sw,int sh,int dx,int dy)
{
    int row,col;
    const ls30_u16 *src; ls30_u16 *dst;
    if (!im || !g_buf) return;
    if(sx<0){sw+=sx;dx-=sx;sx=0;} if(sy<0){sh+=sy;dy-=sy;sy=0;}
    if(sx+sw>im->w)sw=im->w-sx; if(sy+sh>im->h)sh=im->h-sy;
    if(dx<0){sx-=dx;sw+=dx;dx=0;} if(dy<0){sy-=dy;sh+=dy;dy=0;}
    if(dx+sw>g_w)sw=g_w-dx; if(dy+sh>g_h)sh=g_h-dy;
    if(sw<=0||sh<=0)return;
    for(row=0;row<sh;row++){
        src=(const ls30_u16*)(im->pixels+((sy+row)*im->w+sx)*2);
        dst=(ls30_u16*)(g_buf+((dy+row)*g_w+dx)*2);
        if(!im->has_key) memcpy(dst,src,(size_t)sw*2);
        else for(col=0;col<sw;col++){ls30_u16 p=src[col];if(p!=im->key)dst[col]=p;}
    }
}

static int l_image(lua_State *L)
{
    int x=(int)luaL_checknumber(L,1), y=(int)luaL_checknumber(L,2);
    const char *name=luaL_checkstring(L,3);
    cm_image *im=image_find(name); if(!im)im=image_load(name);
    if(!im){lua_pushboolean(L,0);return 1;}
    blit_region(im,0,0,im->w,im->h,x,y); lua_pushboolean(L,1); return 1;
}

static int l_image_region(lua_State *L)
{
    const char *name=luaL_checkstring(L,1);
    int sx=(int)luaL_checknumber(L,2),sy=(int)luaL_checknumber(L,3);
    int sw=(int)luaL_checknumber(L,4),sh=(int)luaL_checknumber(L,5);
    int dx=(int)luaL_checknumber(L,6),dy=(int)luaL_checknumber(L,7);
    cm_image *im=image_find(name); if(!im)im=image_load(name);
    if(!im){lua_pushboolean(L,0);return 1;}
    blit_region(im,sx,sy,sw,sh,dx,dy); lua_pushboolean(L,1); return 1;
}

static int l_flush(lua_State *L){(void)L;if(g_layer>=0)ls30_flush(&g_layer,1);return 0;}
static int l_tick(lua_State *L){lua_pushnumber(L,ls30_ticks());return 1;}
static int l_exit(lua_State *L){(void)L;ls30_exit();return 0;}
static int l_log(lua_State *L){ls30_log_info(luaL_checkstring(L,1));return 0;}

static int make_user_path(const char *name, ls30_wchar *out, int cap)
{
    char p[96]; int d=-1,i,j=0;
    if(!name||!*name)return 0;
    d=ls30_system_drive();
    if(d<0)d=ls30_removable_drive();
    if(d<0)return 0;
    p[j++]=(char)d;p[j++]=':';p[j++]='\\';
    for(i=0;name[i]&&j<(int)sizeof(p)-1;i++){
        char c=name[i];
        if((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='.'||c=='_'||c=='-')p[j++]=c;
        else p[j++]='_';
    }
    p[j]=0;ls30_ascii_to_ucs2(out,cap,p);return 1;
}

static int file_api_ok(void)
{
    return (ls30_capabilities() & LS30_CAP_FILES) != 0;
}

static int l_file_exists(lua_State *L)
{
    const char *name;ls30_wchar p[96];ls30_file f;int size=0;ls30_u8 *res;
    name=luaL_checkstring(L,1);
    if(file_api_ok()&&make_user_path(name,p,96)){
        f=ls30_file_open(p,LS30_FILE_READ,1);
        if(f>=0){ls30_file_close(f);lua_pushboolean(L,1);return 1;}
    }
    /* Packed VXP resources are not filesystem files: also check the resource
       table so existence checks for assets (audio/images) succeed. Read-only. */
    res=ls30_resource_load(name,&size);
    if(res){ls30_free(res);lua_pushboolean(L,1);return 1;}
    lua_pushboolean(L,0);return 1;
}

static int direct_write(ls30_wchar *p,const char *data,size_t len)
{
    ls30_file f;ls30_uint wrote=0;int r;
    f=ls30_file_open(p,LS30_FILE_CREATE_ALWAYS_WRITE,1);if(f<0)return 0;
    r=ls30_file_write(f,(void*)data,(ls30_uint)len,&wrote);
    ls30_file_commit(f);ls30_file_close(f);
    return r>0&&wrote==(ls30_uint)len;
}

static int l_file_write(lua_State *L)
{
    const char *name=luaL_checkstring(L,1);size_t len=0;const char *data=luaL_checklstring(L,2,&len);
    ls30_wchar p[96],tmp[96];char tmpname[80];int ok;
    if(!file_api_ok()||!make_user_path(name,p,96)){lua_pushboolean(L,0);return 1;}
    if((ls30_capabilities() & LS30_CAP_RENAME)&&strlen(name)<70){
        strcpy(tmpname,name);strcat(tmpname,".tmp");
        if(make_user_path(tmpname,tmp,96)&&direct_write(tmp,data,len)){
            ls30_file_delete(p); ok=ls30_file_rename(tmp,p)>=0;
            if(!ok)ls30_file_delete(tmp);
            lua_pushboolean(L,ok);return 1;
        }
    }
    ok=direct_write(p,data,len);lua_pushboolean(L,ok);return 1;
}

static int l_file_read(lua_State *L)
{
    ls30_wchar p[96];ls30_file f;ls30_uint size=0,nread=0;char *buf;int r;
    if(!file_api_ok()||!make_user_path(luaL_checkstring(L,1),p,96)){lua_pushnil(L);return 1;}
    f=ls30_file_open(p,LS30_FILE_READ,1);if(f<0){lua_pushnil(L);return 1;}
    if(ls30_file_size(f,&size)<0||size>LS30_FILE_MAX){ls30_file_close(f);lua_pushnil(L);return 1;}
    if(size==0){ls30_file_close(f);lua_pushliteral(L,"");return 1;}
    buf=(char*)ls30_alloc((int)size);if(!buf){ls30_file_close(f);lua_pushnil(L);return 1;}
    r=ls30_file_read(f,buf,size,&nread);ls30_file_close(f);
    if(r<=0){ls30_free(buf);lua_pushnil(L);return 1;}
    lua_pushlstring(L,buf,(size_t)nread);ls30_free(buf);return 1;
}

static int l_file_delete(lua_State *L)
{
    ls30_wchar p[96];if(!(ls30_capabilities()&LS30_CAP_FILES)||!make_user_path(luaL_checkstring(L,1),p,96)){lua_pushboolean(L,0);return 1;}
    lua_pushboolean(L,ls30_file_delete(p)>=0);return 1;
}

static void audio_release(void){if(g_audio_data){ls30_free(g_audio_data);g_audio_data=0;g_audio_size=0;}}
static void audio_cb(int r){if(r==LS30_AUDIO_STOP||r==LS30_AUDIO_EOF||r==LS30_AUDIO_INTERRUPT)audio_release();}
static int audio_format(const char *n){size_t l=strlen(n);if(l>=4&&strcmp(n+l-4,".wav")==0)return LS30_AUDIO_WAV;if(l>=4&&strcmp(n+l-4,".aac")==0)return LS30_AUDIO_AAC;if(l>=4&&strcmp(n+l-4,".mid")==0)return LS30_AUDIO_MIDI;return LS30_AUDIO_MP3;}

static int l_audio_play(lua_State *L)
{
    const char *name=luaL_checkstring(L,1);int size=0,r;ls30_u8 *data;
    if(!(ls30_capabilities()&LS30_CAP_AUDIO)){lua_pushboolean(L,0);return 1;}
    ls30_audio_stop();audio_release();
    data=ls30_resource_load(name,&size);if(!data||size<=0){lua_pushboolean(L,0);return 1;}
    g_audio_data=data;g_audio_size=size;
    r=ls30_audio_play(data,(ls30_uint)size,(ls30_u8)audio_format(name),LS30_AUDIO_LOUDSPEAKER,audio_cb);
    if(r!=LS30_AUDIO_OK)audio_release();lua_pushboolean(L,r==LS30_AUDIO_OK);return 1;
}
static int l_audio_stop(lua_State *L){(void)L;ls30_audio_stop();audio_release();return 0;}
static int l_audio_volume(lua_State *L){int v=(int)luaL_checknumber(L,1);if(v<0)v=0;if(v>6)v=6;ls30_audio_volume(v);return 0;}
static int l_audio_playing(lua_State *L){lua_pushboolean(L,ls30_audio_playing());return 1;}

static ls30_u8 *load_module_resource(const char *mod, int *len, char *resolved, int cap)
{
    const char *p; char base[112], *q=base;
    if(strlen(mod)>100)return 0;
    for(p=mod;*p && (q-base)<(int)sizeof(base)-6;p++,q++)*q=(*p=='.')?'/':*p;
    *q=0;

    /* Prefer precompiled Lua 5.1 bytecode when present. */
    strncpy(resolved,base,(size_t)cap-1);resolved[cap-1]=0;
    strncat(resolved,".lub",(size_t)cap-strlen(resolved)-1);
    {
        ls30_u8 *b=ls30_resource_load(resolved,len);
        if(b && *len>0)return b;
    }

    /* Standalone mode: raw .lua needs no host luac executable. */
    strncpy(resolved,base,(size_t)cap-1);resolved[cap-1]=0;
    strncat(resolved,".lua",(size_t)cap-strlen(resolved)-1);
    return ls30_resource_load(resolved,len);
}

static int l_require(lua_State *L)
{
    const char *mod=luaL_checkstring(L,1);
    char res[128];int len=0;ls30_u8 *code;int st;

    lua_getglobal(L,"package_loaded");lua_getfield(L,-1,mod);
    if(!lua_isnil(L,-1)){lua_remove(L,-2);return 1;}
    lua_pop(L,1);lua_pop(L,1);

    code=load_module_resource(mod,&len,res,(int)sizeof(res));
    if(!code||len<=0)return luaL_error(L,"module '%s' missing",mod);

    st=luaL_loadbuffer(L,(const char*)code,(size_t)len,res);
    ls30_free(code);
    if(st!=0)return lua_error(L);

    st=lua_pcall(L,0,1,0);
    if(st!=0)return lua_error(L);
    if(lua_isnil(L,-1)){lua_pop(L,1);lua_pushboolean(L,1);}

    lua_getglobal(L,"package_loaded");lua_pushvalue(L,-2);lua_setfield(L,-2,mod);lua_pop(L,1);
    return 1;
}

static int l_print(lua_State *L)
{
    int i,n=lua_gettop(L);lua_getglobal(L,"tostring");
    for(i=1;i<=n;i++){const char*s;lua_pushvalue(L,-1);lua_pushvalue(L,i);lua_call(L,1,1);s=lua_tostring(L,-1);if(s)ls30_log_info(s);lua_pop(L,1);}return 0;
}


static int l_capabilities(lua_State *L)
{
    lua_pushnumber(L,(lua_Number)ls30_capabilities());
    return 1;
}

static int l_device_info(lua_State *L)
{
    const ls30_device_profile *d=ls30_device_current();
    lua_newtable(L);
    lua_pushstring(L,d&&d->family?d->family:"generic-vxp");lua_setfield(L,-2,"family");
    lua_pushnumber(L,d?d->screen_width:g_w);lua_setfield(L,-2,"width");
    lua_pushnumber(L,d?d->screen_height:g_h);lua_setfield(L,-2,"height");
    lua_pushnumber(L,d?d->preferred_fps:15);lua_setfield(L,-2,"preferred_fps");
    lua_pushnumber(L,d?d->recommended_ram_kb:1536);lua_setfield(L,-2,"recommended_ram_kb");
    lua_pushnumber(L,(lua_Number)(d?d->capabilities:ls30_capabilities()));lua_setfield(L,-2,"capabilities");
    lua_pushnumber(L,(lua_Number)(d?d->native_capabilities:ls30_native_capabilities()));lua_setfield(L,-2,"native_capabilities");
    lua_pushnumber(L,(lua_Number)(d?d->fallback_mask:0));lua_setfield(L,-2,"fallback_mask");
    lua_pushnumber(L,(lua_Number)(d?d->missing_required:0));lua_setfield(L,-2,"missing_required");
    lua_pushnumber(L,(lua_Number)(d?d->abi_alias_count:0));lua_setfield(L,-2,"abi_alias_count");
    lua_pushstring(L,ls30_compatibility_level_name());lua_setfield(L,-2,"compatibility");
    return 1;
}


static void push_fallback_flags(lua_State *L,ls30_u32 mask)
{
    lua_newtable(L);
    lua_pushboolean(L,(mask&LS30_FB_RES_INIT_NOOP)!=0);lua_setfield(L,-2,"resource_init_noop");
    lua_pushboolean(L,(mask&LS30_FB_SCREEN_240X320)!=0);lua_setfield(L,-2,"screen_240x320");
    lua_pushboolean(L,(mask&LS30_FB_CLIP_NOOP)!=0);lua_setfield(L,-2,"clip_noop");
    lua_pushboolean(L,(mask&LS30_FB_FONT_NOOP)!=0);lua_setfield(L,-2,"font_noop");
    lua_pushboolean(L,(mask&LS30_FB_TEXT_WIDTH_ESTIMATE)!=0);lua_setfield(L,-2,"text_width_estimate");
    lua_pushboolean(L,(mask&LS30_FB_FONT_HEIGHT_DEFAULT)!=0);lua_setfield(L,-2,"font_height_default");
    lua_pushboolean(L,(mask&LS30_FB_LINE_FROM_FILL)!=0);lua_setfield(L,-2,"line_software");
    lua_pushboolean(L,(mask&LS30_FB_FILL_FROM_LINE)!=0);lua_setfield(L,-2,"fill_software");
    lua_pushboolean(L,(mask&LS30_FB_FILE_COMMIT_NOOP)!=0);lua_setfield(L,-2,"file_commit_noop");
    lua_pushboolean(L,(mask&LS30_FB_RENAME_COPY_DELETE)!=0);lua_setfield(L,-2,"rename_copy_delete");
    lua_pushboolean(L,(mask&LS30_FB_REMOVABLE_SYSTEM_DRIVE)!=0);lua_setfield(L,-2,"removable_to_system");
    lua_pushboolean(L,(mask&LS30_FB_AUDIO_STATE_FALSE)!=0);lua_setfield(L,-2,"audio_state_false");
    lua_pushboolean(L,(mask&LS30_FB_LOG_NOOP)!=0);lua_setfield(L,-2,"log_noop");
    lua_pushboolean(L,(mask&LS30_FB_PEN_DISABLED)!=0);lua_setfield(L,-2,"touch_disabled");
}

static int l_runtime_compat(lua_State *L)
{
    const ls30_compat_report *r=ls30_compatibility_report();
    lua_newtable(L);
    lua_pushboolean(L,r&&r->compatible);lua_setfield(L,-2,"compatible");
    lua_pushstring(L,ls30_compatibility_level_name());lua_setfield(L,-2,"level");
    lua_pushnumber(L,(lua_Number)(r?r->native_capabilities:0));lua_setfield(L,-2,"native_capabilities");
    lua_pushnumber(L,(lua_Number)(r?r->effective_capabilities:ls30_capabilities()));lua_setfield(L,-2,"capabilities");
    lua_pushnumber(L,(lua_Number)(r?r->fallback_mask:0));lua_setfield(L,-2,"fallback_mask");
    lua_pushnumber(L,(lua_Number)(r?r->alias_mask:0));lua_setfield(L,-2,"alias_mask");
    lua_pushnumber(L,(lua_Number)(r?r->alias_count:0));lua_setfield(L,-2,"alias_count");
    lua_pushnumber(L,(lua_Number)(r?r->missing_required:0));lua_setfield(L,-2,"missing_required");
    push_fallback_flags(L,r?r->fallback_mask:0);lua_setfield(L,-2,"fallbacks");
    return 1;
}

static const luaL_Reg funcs[]={
 {"color",l_color},{"clear",l_clear},{"rect",l_rect},{"frame",l_frame},{"line",l_line},{"text",l_text},
 {"image",l_image},{"image_region",l_image_region},{"set_font",l_set_font},{"text_width",l_text_width},{"font_height",l_font_height},
 {"file_exists",l_file_exists},{"file_write",l_file_write},{"file_read",l_file_read},{"file_delete",l_file_delete},
 {"audio_play",l_audio_play},{"audio_stop",l_audio_stop},{"audio_set_volume",l_audio_volume},{"audio_is_playing",l_audio_playing},
 {"flush",l_flush},{"tick_ms",l_tick},{"exit",l_exit},{"log",l_log},{"capabilities",l_capabilities},{"device_info",l_device_info},{"runtime_compat",l_runtime_compat},{0,0}
};

void luas30_bridge_open(lua_State *L)
{
    lua_newtable(L);luaL_register(L,0,funcs);
    lua_pushnumber(L,g_w);lua_setfield(L,-2,"W");lua_pushnumber(L,g_h);lua_setfield(L,-2,"H");
    lua_pushstring(L,"LuaS30 IDE/1.8.2 RuntimeCompat");lua_setfield(L,-2,"version");
    /* Public name is `engine`; keep `mre` as a compatibility alias. */

    lua_pushboolean(L,(ls30_capabilities() & LS30_CAP_AUDIO)!=0);lua_setfield(L,-2,"has_audio");
    lua_pushboolean(L,file_api_ok());lua_setfield(L,-2,"has_files");
    lua_pushboolean(L,(ls30_capabilities() & LS30_CAP_IMAGES)!=0);lua_setfield(L,-2,"has_images");
    lua_pushboolean(L,(ls30_capabilities() & LS30_CAP_TOUCH)!=0);lua_setfield(L,-2,"has_touch");
    lua_pushboolean(L,(ls30_capabilities() & LS30_CAP_RENAME)!=0);lua_setfield(L,-2,"has_rename");
    lua_pushboolean(L,(ls30_native_capabilities() & LS30_CAP_REMOVABLE)!=0);lua_setfield(L,-2,"has_removable");
    lua_pushboolean(L,(ls30_native_capabilities() & LS30_CAP_LOG)!=0);lua_setfield(L,-2,"has_log");
    lua_pushboolean(L,ls30_compatibility_level()!=LS30_COMPAT_INCOMPATIBLE);lua_setfield(L,-2,"runtime_compatible");
    lua_pushvalue(L,-1);lua_setglobal(L,"engine");
    lua_setglobal(L,"mre");
    lua_pushcfunction(L,l_require);lua_setglobal(L,"require");
    lua_pushcfunction(L,l_print);lua_setglobal(L,"print");
}

void luas30_bridge_shutdown(void)
{
    int i;
    ls30_audio_stop();audio_release();
    for(i=0;i<g_image_count;i++)if(g_images[i].canvas>=0)ls30_image_close(g_images[i].canvas);
    g_image_count=0;
}
