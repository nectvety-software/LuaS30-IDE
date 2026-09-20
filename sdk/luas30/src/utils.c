#include "ls30/api.h"

/* Giai ma UTF-8 sang UCS2 (giu tuong thich ASCII: byte <0x80 map 1-1).
 * Kieu chu MRE/Nokia dung UCS2 nen tieng Viet co dau (U+00C0..U+1EF9)
 * chi hien dung khi decode UTF-8 o day. Byte loi -> '?'. */
int ls30_ascii_to_ucs2(ls30_wchar *dst,int cap,const char *src)
{
    int i=0;
    const unsigned char *s;
    if(!dst||cap<=0)return 0;
    if(!src){dst[0]=0;return 0;}
    s=(const unsigned char *)src;
    while(*s&&i<cap-1){
        unsigned long cp;
        if(*s<0x80){cp=*s;s++;}
        else if((*s&0xE0)==0xC0&&(s[1]&0xC0)==0x80){
            cp=((unsigned long)(*s&0x1F)<<6)|(s[1]&0x3F);s+=2;
            if(cp<0x80)cp='?'; /* overlong */
        }
        else if((*s&0xF0)==0xE0&&(s[1]&0xC0)==0x80&&(s[2]&0xC0)==0x80){
            cp=((unsigned long)(*s&0x0F)<<12)|(((unsigned long)(s[1]&0x3F))<<6)|(s[2]&0x3F);
            s+=3;
            if(cp<0x800||(cp>=0xD800&&cp<=0xDFFF))cp='?';
        }
        else if((*s&0xF8)==0xF0&&(s[1]&0xC0)==0x80&&(s[2]&0xC0)==0x80&&(s[3]&0xC0)==0x80){
            cp='?';s+=4; /* ngoai BMP: UCS2 khong bieu dien duoc */
        }
        else{cp='?';s++;}
        if(cp>0xFFFF)cp='?';
        dst[i++]=(ls30_wchar)cp;
    }
    dst[i]=0;return i;
}

ls30_u16 ls30_color565(int r,int g,int b)
{
    if(r<0)r=0;else if(r>255)r=255;
    if(g<0)g=0;else if(g>255)g=255;
    if(b<0)b=0;else if(b>255)b=255;
    return LS30_RGB565(r,g,b);
}
