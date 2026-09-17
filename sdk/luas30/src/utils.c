#include "ls30/api.h"

int ls30_ascii_to_ucs2(ls30_wchar *dst,int cap,const char *src)
{
    int i=0;
    if(!dst||cap<=0)return 0;
    if(!src){dst[0]=0;return 0;}
    while(src[i]&&i<cap-1){dst[i]=(ls30_wchar)(unsigned char)src[i];i++;}
    dst[i]=0;return i;
}

ls30_u16 ls30_color565(int r,int g,int b)
{
    if(r<0)r=0;else if(r>255)r=255;
    if(g<0)g=0;else if(g>255)g=255;
    if(b<0)b=0;else if(b>255)b=255;
    return LS30_RGB565(r,g,b);
}
