#include "ls30/api.h"
#include "luas30_runtime.h"
#include <stddef.h>
#include <string.h>
struct _reent;

#if defined(__GNUC__)
extern unsigned int __init_array_start;
extern unsigned int __init_array_end;
#define LS30_ENTRY_EXPORT __attribute__((used,visibility("default")))
#else
#define LS30_ENTRY_EXPORT
#endif

typedef void (**ls30_init_array_t)(void);

/* Vendor MRE static archives do NOT link against a fixed symbol table. Their
   rand.o / srand.o (and friends) look the symbol up AT RUN TIME through this
   global function pointer, which the loader hands to gcc_entry():

       vm_rand = (VMINT (*)(void))vm_get_sym_entry("vm_rand");
       if (!vm_rand) return;              // chua bind -> thoat em, khong crash

   LuaS30 da giu cung resolver do trong ls30_resolver (xem ls30_platform_bind),
   nhung bien do khong export nen trinh lien ket khong thay, va vendor archive
   bao "undefined reference to `vm_get_sym_entry'". Khai bao them bien nay --
   cung kieu, cung gia tri -- la du de chung link duoc.
   Kieu tra ve khop tuyet doi: VMINT (*)(char *) == ls30_symbol_resolver.

   LUU Y: co tinh KHONG viet ten tep cua vendor archive trong file nay.
   assert_native_sdk_independent() trong tools/build.py quet chinh cac file
   nguon nay de tim chuoi ten vendor va se bao loi. Ten vendor chi duoc phep
   xuat hien o buoc build (duong dan -L / -T), khong duoc nam trong tang nguon
   LuaS30 -- giu dung ranh gioi do thi viec thay SDK MRE moi khong keo theo
   phai sua ma nguon engine. */
LS30_ENTRY_EXPORT
ls30_symbol_resolver vm_get_sym_entry = 0;

void *malloc(size_t n){ return ls30_alloc((int)n); }
void free(void *p){ ls30_free(p); }
void *realloc(void *p,size_t n){ return ls30_realloc(p,(int)n); }
void *calloc(size_t count,size_t size)
{
    size_t total;void *p;
    if(count&&size>((size_t)-1)/count)return 0;
    total=count*size;p=malloc(total);if(p)memset(p,0,total);return p;
}
void *_calloc_r(struct _reent *u,size_t c,size_t s){(void)u;return calloc(c,s);}

#if defined(__GNUC__)
void *_sbrk(int incr)
{
    static unsigned char emergency_heap[8192];
    static int used=0;int old=used;
    if(incr<0||used+incr>(int)sizeof(emergency_heap))return(void*)-1;
    used+=incr;return emergency_heap+old;
}
void _exit(int code){(void)code;ls30_exit();for(;;){}}
int _kill(int p,int s){(void)p;(void)s;return-1;}
int _getpid(void){return 1;}
int _open(const char*p,int f,int m){(void)p;(void)f;(void)m;return-1;}
int _close(int f){(void)f;return-1;}
int _read(int f,void*b,unsigned int n){(void)f;(void)b;(void)n;return 0;}
int _write(int f,const void*b,unsigned int n){(void)f;(void)b;return(int)n;}
int _lseek(int f,long o,int w){(void)f;(void)o;(void)w;return-1;}
int _fstat(int f,void*s){(void)f;(void)s;return-1;}
int _isatty(int f){(void)f;return 1;}
void _fini(void){}
#endif

/* The actual MRE application entry. Public S30+/MRE projects expose vm_main()
   and let the compiler-specific loader entry call it after relocation/ctors. */
LS30_ENTRY_EXPORT
void vm_main(void)
{
    luas30_runtime_main();
}

static void ls30_entry_common(
    unsigned int resolver_entry,
    unsigned int init_array_start,
    unsigned int count)
{
    unsigned int i;
    ls30_init_array_t ptr;

    /* Giu lai resolver cho vendor MRE SDK: chung goi qua bien toan cuc nay,
       khong goi ham cua LuaS30. Phai gan TRUOC khi bat ky ma SDK nao chay. */
    vm_get_sym_entry = (ls30_symbol_resolver)(unsigned long)resolver_entry;

    if(!ls30_platform_bind((ls30_symbol_resolver)(unsigned long)resolver_entry))return;

#if defined(__GNUC__)
    if(init_array_start==0){
        init_array_start=(unsigned int)&__init_array_start;
        count=((unsigned int)&__init_array_end-(unsigned int)&__init_array_start)/4u;
    }
#else
    if(init_array_start==0)count=0;
#endif

    ptr=(ls30_init_array_t)init_array_start;
    if(ptr){
        /* Community MRE GCC stubs intentionally start at index 1. */
        for(i=1;i<count;i++)if(ptr[i])ptr[i]();
    }
    vm_main();
}

LS30_ENTRY_EXPORT
void gcc_entry(unsigned int resolver_entry,unsigned int init_array_start,unsigned int count)
{
    ls30_entry_common(resolver_entry,init_array_start,count);
}

LS30_ENTRY_EXPORT
void rvct_entry(unsigned int resolver_entry,unsigned int init_array_start,unsigned int count)
{
    ls30_entry_common(resolver_entry,init_array_start,count);
}

LS30_ENTRY_EXPORT
void ads_entry(unsigned int resolver_entry,unsigned int init_array_start,unsigned int count)
{
    ls30_entry_common(resolver_entry,init_array_start,count);
}
