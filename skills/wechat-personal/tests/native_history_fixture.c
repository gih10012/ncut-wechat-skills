#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

__attribute__((noinline)) void history_insert(void *a, void *b, void *c) {
    __asm__ volatile("" :: "r"(a), "r"(b), "r"(c) : "memory");
}
__attribute__((naked, noinline)) void assigned(void *a, void *b) {
    __asm__ volatile("push %r15; mov %rdi,%rax; mov %rsi,%r15;"
                     ".global history_assigned; history_assigned: nop; pop %r15; ret;");
}
__attribute__((noinline)) void history_send(void *a, void *b, void *c) {
    __asm__ volatile("" :: "r"(a), "r"(b), "r"(c) : "memory");
}
__attribute__((noinline)) void history_update(void *a, void *b, int c, int d) {
    __asm__ volatile("" :: "r"(a), "r"(b), "r"(c), "r"(d) : "memory");
}
static void number(unsigned char *p, int offset, uint32_t n) { memcpy(p+offset, &n, 4); }
static void message(unsigned char *p, const char *recipient, uint32_t id) {
    number(p, 0xc, 1); number(p, 0xf4, id); number(p, 0x114, 1700000000);
    number(p, 0x118, 1); p[0x30] = strlen(recipient)*2;
    memcpy(p+0x31, recipient, strlen(recipient));
    memcpy(p+0x130, "PRIVATE_FIXTURE_BODY_MUST_NOT_BE_CAPTURED", 39);
}
int main(void) {
    unsigned char before[0x278]={0}, after[0x278]={0}, second[0x278]={0}, wrong[0x278]={0};
    void *ctx[8]={0}, *other[8]={0}, *cp=ctx, *op=other, *mp=after;
    message(before,"filehelper",0); message(after,"filehelper",42);
    message(second,"filehelper",43); message(wrong,"someone",0);
    ctx[3]=wrong; history_insert(0,0,&cp);
    ctx[3]=before;
    if (getenv("NCUT_HISTORY_FIXTURE_TIMEOUT")) { sleep(20); return 0; }
    history_insert(0,0,&cp);
    assigned(after,&op); assigned(after,&cp); assigned(second,&cp);
    ctx[3]=after; other[3]=after;
    if (!getenv("NCUT_HISTORY_FIXTURE_SKIP_SEND")) {
        history_send(0,0,&op); history_send(0,0,&cp);
    }
    number(wrong,0xf4,42); void *wp=wrong;
    history_update(0,&wp,1,1);
    number(after,0x118,2); number(after,0xf8,99);
    history_update(0,&mp,1,1);
    sleep(20);
    return 0;
}
