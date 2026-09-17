#include "ls30/api.h"
#include "luas30_runtime.h"
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"

#define LS30_MAX_W 480
#define LS30_MAX_H 640
#define LS30_DEFAULT_FRAME_MS 66

static lua_State *L=0;
static int layer=-1,timer_id=-1;
static ls30_u8 *frame=0;
static int width=240,height=320,started=0,paused=0,panic_state=0,frame_ms=LS30_DEFAULT_FRAME_MS;

static void flush_frame(void){if(layer>=0)ls30_flush(&layer,1);}

static void error_screen(const char *s)
{
    ls30_wchar w[96];int n;
    if(!frame)return;
    ls30_fill(frame,0,0,width,height,LS30_COLOR_BLACK,LS30_COLOR_BLACK);
    ls30_font(LS30_FONT_SMALL);
    n=ls30_ascii_to_ucs2(w,96,s?s:"Lua error");
    ls30_text(frame,3,3,w,n,LS30_COLOR_WHITE);flush_frame();
}

static int report(int st)
{
    if(st!=0&&L){
        const char*s=lua_tostring(L,-1);if(!s)s="Lua error";
        ls30_log_error(s);error_screen(s);lua_pop(L,1);panic_state=1;
    }
    return st;
}

static int hook(const char *name,double dt)
{
    int top,st,nargs=0;
    if(!L||panic_state)return-1;
    top=lua_gettop(L);lua_getglobal(L,"engine");
    if(!lua_istable(L,-1)){lua_pop(L,1);lua_getglobal(L,"mre");if(!lua_istable(L,-1)){lua_settop(L,top);return-1;}}
    lua_getfield(L,-1,name);if(!lua_isfunction(L,-1)){lua_settop(L,top);return 0;}
    if(dt>=0){lua_pushnumber(L,dt);nargs=1;}
    st=lua_pcall(L,nargs,0,0);if(st)report(st);lua_settop(L,top);return st;
}

static int load_res_chunk(const char *res,const char *chunk,int run)
{
    int n=0,st;ls30_u8*b=ls30_resource_load(res,&n);
    if(!b||n<=0)return-1;
    st=luaL_loadbuffer(L,(const char*)b,(size_t)n,chunk);ls30_free(b);
    if(st)return report(st);
    if(run)return report(lua_pcall(L,0,0,0));
    return 0;
}
static int load_first(const char*a,const char*b,const char*chunk,int run)
{
    int st=load_res_chunk(a,chunk,run);if(st>=0)return st;return load_res_chunk(b,chunk,run);
}

static void design_load(void){(void)load_first("ui_design.lub","ui_design.lua","ui_design",1);}
static void design_draw(void)
{
    int top;if(!L||panic_state)return;top=lua_gettop(L);lua_getglobal(L,"ui_design");
    if(!lua_istable(L,-1)){lua_settop(L,top);return;}
    lua_getfield(L,-1,"draw");if(!lua_isfunction(L,-1)){lua_settop(L,top);return;}
    lua_pushstring(L,"main");if(lua_pcall(L,1,0,0)!=0)report(1);lua_settop(L,top);
}

static void timer_cb(int id)
{
    (void)id;if(!started||paused||panic_state)return;
    hook("update",((double)frame_ms)/1000.0);design_draw();hook("draw",-1);flush_frame();
}

static void set_timer(int on)
{
    if(on){if(timer_id<0)timer_id=ls30_timer_start((unsigned)frame_ms,timer_cb);}
    else if(timer_id>=0){ls30_timer_stop(timer_id);timer_id=-1;}
}

static void sysevt(int msg,int param)
{
    (void)param;
    switch(msg){
    case LS30_MSG_CREATE:
    case LS30_MSG_PAINT:
        if(!paused&&!panic_state){design_draw();hook("draw",-1);flush_frame();}break;
    case LS30_MSG_ACTIVE:
        if(paused){paused=0;hook("resume",-1);set_timer(1);}
        if(!panic_state){design_draw();hook("draw",-1);flush_frame();}break;
    case LS30_MSG_INACTIVE:
    case LS30_MSG_HIDE:
        if(!paused){paused=1;set_timer(0);hook("pause",-1);}break;
    case LS30_MSG_QUIT:
        luas30_runtime_shutdown();break;
    default:break;
    }
}

static const char *key_name(int k)
{
    switch(k){
    case LS30_KEY_UP:return"up";case LS30_KEY_DOWN:return"down";case LS30_KEY_LEFT:return"left";case LS30_KEY_RIGHT:return"right";
    case LS30_KEY_OK:return"ok";case LS30_KEY_LSK:return"softleft";case LS30_KEY_RSK:return"softright";
    case LS30_KEY_CLEAR:return"clear";case LS30_KEY_BACK:return"back";
    case LS30_KEY_NUM0:return"0";case LS30_KEY_NUM1:return"1";case LS30_KEY_NUM2:return"2";case LS30_KEY_NUM3:return"3";
    case LS30_KEY_NUM4:return"4";case LS30_KEY_NUM5:return"5";case LS30_KEY_NUM6:return"6";case LS30_KEY_NUM7:return"7";
    case LS30_KEY_NUM8:return"8";case LS30_KEY_NUM9:return"9";case LS30_KEY_STAR:return"*";case LS30_KEY_POUND:return"#";
    default:return 0;}
}

static void keyevt(int event,int key)
{
    const char*k;int top;
    if(!L||panic_state)return;k=key_name(key);if(!k)return;top=lua_gettop(L);
    lua_getglobal(L,"engine");if(!lua_istable(L,-1)){lua_pop(L,1);lua_getglobal(L,"mre");}
    if(!lua_istable(L,-1)){lua_settop(L,top);return;}
    if(event==LS30_KEY_EVENT_DOWN||event==LS30_KEY_EVENT_REPEAT)lua_getfield(L,-1,"keypressed");
    else if(event==LS30_KEY_EVENT_UP)lua_getfield(L,-1,"keyreleased");
    else{lua_settop(L,top);return;}
    if(lua_isfunction(L,-1)){lua_pushstring(L,k);if(lua_pcall(L,1,0,0)!=0)report(1);}
    lua_settop(L,top);
}
static void penevt(int e,int x,int y){(void)e;(void)x;(void)y;}

static void read_config(void)
{
    int top,cw=0,ch=0,fps=0;
    if(load_first("conf.lub","conf.lua","conf",1)<0)return;
    top=lua_gettop(L);lua_getglobal(L,"config");
    if(lua_istable(L,-1)){
        lua_getfield(L,-1,"screen_width");if(lua_isnumber(L,-1))cw=(int)lua_tonumber(L,-1);lua_pop(L,1);
        lua_getfield(L,-1,"screen_height");if(lua_isnumber(L,-1))ch=(int)lua_tonumber(L,-1);lua_pop(L,1);
        lua_getfield(L,-1,"fps");if(lua_isnumber(L,-1))fps=(int)lua_tonumber(L,-1);lua_pop(L,1);
    }
    lua_settop(L,top);
    if(fps>=8&&fps<=30)frame_ms=1000/fps;
    if(cw>0&&cw<=width)width=cw;
    if(ch>0&&ch<=height)height=ch;
}

void luas30_runtime_main(void)
{
    int sw,sh;
    if(!ls30_platform_ready())return;
    {
        const ls30_compat_report *cr=ls30_compatibility_report();
        if(cr && cr->level==LS30_COMPAT_DEGRADED)
            ls30_log_info("LuaS30: compatible firmware with runtime fallbacks");
    }
    ls30_on_system(sysevt);ls30_on_key(keyevt);ls30_on_pen(penevt);
    ls30_resource_init();

    sw=ls30_screen_width();sh=ls30_screen_height();
    if(sw<=0)sw=240;if(sh<=0)sh=320;
    if(sw>LS30_MAX_W)sw=LS30_MAX_W;if(sh>LS30_MAX_H)sh=LS30_MAX_H;
    width=sw;height=sh;

    layer=ls30_layer_create(0,0,width,height,LS30_NO_TRANS_COLOR);if(layer<0)return;
    ls30_clip(0,0,width,height);ls30_font(LS30_FONT_SMALL);frame=ls30_layer_buffer(layer);
    if(!frame)return;

    L=lua_open();if(!L){error_screen("Lua VM alloc failed");return;}
    luaopen_base(L);lua_settop(L,0);luaopen_table(L);lua_settop(L,0);
    luaopen_string(L);lua_settop(L,0);luaopen_math(L);lua_settop(L,0);
    lua_newtable(L);lua_setglobal(L,"package_loaded");

    luas30_bridge_set_frame(frame,width,height,layer);luas30_bridge_open(L);
    read_config();
    if(load_first("main.lub","main.lua","main",1)<0){if(!panic_state)error_screen("main.lua missing");return;}
    design_load();hook("load",-1);if(panic_state)return;
    design_draw();hook("draw",-1);flush_frame();started=1;set_timer(1);
}

void luas30_runtime_shutdown(void)
{
    if(!started&&!L)return;
    set_timer(0);if(L&&!panic_state)hook("quit",-1);luas30_bridge_shutdown();
    if(L){lua_close(L);L=0;}
    if(layer>=0)ls30_layer_delete(layer);
    layer=-1;frame=0;started=0;paused=0;panic_state=0;
}
