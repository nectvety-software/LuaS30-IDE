#ifndef LUAS30_RUNTIME_H
#define LUAS30_RUNTIME_H
#include "ls30/api.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct lua_State lua_State;
void luas30_runtime_main(void);
void luas30_runtime_shutdown(void);
void luas30_bridge_set_frame(ls30_u8 *buf,int w,int h,int layer);
void luas30_bridge_open(lua_State *L);
void luas30_bridge_shutdown(void);
#ifdef __cplusplus
}
#endif
#endif
