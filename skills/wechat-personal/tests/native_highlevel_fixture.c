#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>

/* These are ordinary child-process functions; no WeChat image or process is used. */
unsigned char highlevel_request_vtable[64];
#define MARK(name) __attribute__((noinline)) void highlevel_##name(void *a, void *b, void *c, int d) { \
    __asm__ volatile("" :: "r"(a), "r"(b), "r"(c), "r"(d) : "memory"); }
MARK(request)
MARK(insert)
__attribute__((naked, noinline)) void assigned(void *message __attribute__((unused)),
                                             void *context __attribute__((unused))) {
    __asm__ volatile("push %r15; mov %rdi,%rax; mov %rsi,%r15;"
                     ".global highlevel_assigned; highlevel_assigned: nop; pop %r15; ret;");
}
__attribute__((noinline)) void highlevel_update(void *a, void *b, int c, int d) {
    __asm__ volatile("" :: "r"(a), "r"(b), "r"(c), "r"(d) : "memory");
}
static void number(unsigned char *p, int off, uint32_t n) { memcpy(p+off,&n,4); }
static void pointer(unsigned char *p, int off, void *n) { memcpy(p+off,&n,8); }
static void string(unsigned char *p, const char *s, int longer) {
    size_t size=strlen(s);
    if (longer) { p[0]=33; memcpy(p+8,&size,8); memcpy(p+16,&s,8); }
    else { p[0]=size*2; memcpy(p+1,s,size); }
}
static void request(unsigned char *p, const char *to, int longer) {
    pointer(p,0,highlevel_request_vtable); number(p,0x7c,1); number(p,0xe4,1);
    string(p+0x90,to,longer);
    memcpy(p+0x5c8,"PRIVATE_REQUEST_BODY_NEVER_CAPTURE",33);
}
static void message(unsigned char *p, const char *to, uint32_t id, int longer) {
    number(p,0xc,1); number(p,0xf4,id); number(p,0x114,1700000000); number(p,0x118,1);
    string(p+0x30,to,longer);
    memcpy(p+0x130,"PRIVATE_MESSAGE_BODY_NEVER_CAPTURE",33);
}
static void *finish(void *message) {
    highlevel_update(0,&message,1,1);
    return 0;
}
int main(void) {
    unsigned char req[0x5f8]={0}, wrongreq[0x5f8]={0}, secondreq[0x5f8]={0};
    unsigned char before[0x278]={0}, after[0x278]={0}, unrelated[0x278]={0}, wrongmsg[0x278]={0};
    unsigned char ctx[0xe0]={0}, otherctx[0xe0]={0};
    void *rp=req,*wp=wrongreq,*sp=secondreq,*cp=ctx,*op=otherctx;
    int manager=0, sender=0;
    request(req,"filehelper",1); request(wrongreq,"someone",0); request(secondreq,"filehelper",0);
    message(before,"filehelper",0,0); message(after,"filehelper",42,1);
    message(unrelated,"filehelper",43,0); message(wrongmsg,"someone",42,0);
    pointer(ctx,8,req); pointer(ctx,0x18,before);
    pointer(otherctx,8,secondreq); pointer(otherctx,0x18,unrelated);
    const char *mode=getenv("NCUT_HIGHLEVEL_FIXTURE_MODE");
    if (mode && !strcmp(mode,"hit_limit")) {
        for (int i=0;i<110;i++) highlevel_request(0,&manager,&wp,1);
        sleep(20); return 0;
    }
    if (mode && !strcmp(mode,"read_error")) {
        void *bad=(void*)1;
        for (int i=0;i<8;i++) highlevel_request(0,&manager,&bad,1);
        sleep(20); return 0;
    }
    highlevel_request(0,&manager,&wp,1);
    if (mode && !strcmp(mode,"timeout")) { sleep(20); return 0; }
    highlevel_request(0,&manager,&rp,1);
    highlevel_request(0,&sender,&sp,1); /* ignored second matching send */
    highlevel_insert(0,&sender,&op,0);
    highlevel_insert(0,&sender,&cp,0);
    assigned(unrelated,&op); /* wrong context */
    assigned(after,&cp);
    pointer(ctx,0x18,after); /* native insertion replaces the message pointer */
    void *up=unrelated,*mp=wrongmsg;
    highlevel_update(0,&up,1,1); /* unrelated local ID */
    highlevel_update(0,&mp,1,1); /* same ID, wrong target */
    number(after,0x118,2); number(after,0xf8,99);
    pthread_t worker;
    pthread_create(&worker,0,finish,after); /* exercises native TID difference */
    pthread_join(worker,0);
    sleep(20);
    return 0;
}
