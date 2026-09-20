/* Real C/GDB fixture. No WeChat process, network or account data is used. */
#include "../scripts/native_send_helper.c"
#include <assert.h>
#include <signal.h>
#include <poll.h>

#ifdef NCUT_FIXTURE_DSO
static void *interrupt_loader(void *unused) {
    (void)unused;
    usleep(20000);
    raise(SIGUSR1); /* Another selected thread interrupts main's inferior call. */
    return NULL;
}
__attribute__((constructor)) static void loader_fixture(void) {
    if (getenv("NCUT_TEST_INTERRUPT_LOADER")) {
        pthread_t thread;
        assert(!pthread_create(&thread, NULL, interrupt_loader, NULL));
        assert(!pthread_join(thread, NULL));
    }
}
#endif

struct Request { unsigned char *data; size_t size; };
static int parse_fail, unconsumed, response_error;
static int actual_submissions;
static int early_completion;
struct Business { unsigned canary; Callback *callback; };
static void fake_business_delete(void *ptr) {
    struct Business *business = ptr;
    assert(business->canary == 0x12345678);
    business->canary = 0;
    business->callback->vtable->destroy_deallocate(business->callback);
    free(business);
}
static void fake_ctor(void *ptr) { memset(ptr, 0, 0x30); }
static void fake_dtor(void *ptr) { free(((struct Request *)ptr)->data); }
static bool fake_parse(void *ptr, const void *data, int size) {
    struct Request *req = ptr;
    if (parse_fail) return false;
    req->data = malloc(size); memcpy(req->data, data, size); req->size = size;
    return true;
}
static bool fake_serialize(void *ptr, NativeString *str) {
    struct Request *req = ptr;
    unsigned char *copy = malloc(req->size);
    memcpy(copy, req->data, req->size);
    str->bytes[0] = 1;
    memcpy(str->bytes + 8, &req->size, 8);
    memcpy(str->bytes + 16, &copy, 8);
    return true;
}
static void *fake_complete(void *ptr) {
    struct Business *business = ptr;
    Callback *cb = business->callback;
    if (!early_completion) usleep(50000);
    int type = response_error ? 4 : 0, code = response_error ? -123 : 0;
    void *argument = business;
    assert(!cb->vtable->invoke(cb, &argument, &type, &code));
    /* Exact native false branch: do not touch business/callback again. */
    return NULL;
}
static uint32_t fake_submit(void *svc, void *req, NativeString *extra, void *config, NativeFunction *fn) {
    (void)svc; (void)req; (void)extra; (void)config;
    ++actual_submissions;
    if (unconsumed) return 0;
    Callback *cb = fn->target;
    assert(cb && (void *)cb != (void *)fn);
    fn->target = NULL;
    struct Business *business = malloc(sizeof(*business));
    *business = (struct Business){0x12345678, cb};
    if (early_completion) {
        fake_complete(business);
        /* Model the real outer submit's post-callback business access. */
        assert(business->canary == 0x12345678);
    } else {
        pthread_t thread;
        assert(!pthread_create(&thread, NULL, fake_complete, business));
        assert(!pthread_detach(thread));
    }
    return 77;
}
__attribute__((visibility("default")))
int ncut_test_launch(uintptr_t base, const void *data, size_t length, const char *result, int send) {
    (void)base;
    if (started++) return EALREADY;
    api = (NativeApi){fake_ctor, fake_dtor, fake_parse, fake_serialize, free,
                     fake_business_delete, fake_submit, NULL};
    output_fd = open(result, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
    if (output_fd < 0) return errno;
    memcpy(payload, data, length); payload_size = length; should_send = send;
    snprintf(arm_path, sizeof(arm_path), "%s.arm", result);
    pthread_t thread;
    int code = pthread_create(&thread, NULL, worker, NULL);
    if (!code) pthread_detach(thread);
    return code;
}
__attribute__((noinline)) void fixture_idle(void) { asm volatile("" ::: "memory"); }
int main(int argc, char **argv) {
    if (argc == 1) {
        fixture_idle();
        const char *path = getenv("NCUT_TEST_RESUMED_PATH");
        if (path) {
            int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
            assert(fd >= 0);
            assert(write(fd, "returned to original main\n", 26) == 26);
            close(fd);
        }
        for (;;) {
            if (getenv("NCUT_TEST_POLL")) poll(NULL, 0, 100);
            else pause();
        }
    }
    parse_fail = !strcmp(argv[1], "parse-failure");
    unconsumed = !strcmp(argv[1], "unconsumed");
    response_error = !strcmp(argv[1], "server-error");
    early_completion = !strcmp(argv[1], "early-completion");
    unsigned char data[] = "synthetic request";
    assert(!ncut_test_launch(1, data, sizeof(data), argv[2], strcmp(argv[1], "check") != 0));
    assert(ncut_test_launch(1, data, sizeof(data), argv[2], 1) == EALREADY);
    int arm = open(arm_path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    assert(arm >= 0); close(arm);
    for (int i = 0; i < 500; ++i) {
        pthread_mutex_lock(&lock);
        int done = worker_done && !live_callbacks;
        pthread_mutex_unlock(&lock);
        if (done) break;
        usleep(10000);
    }
    assert(worker_done && !live_callbacks);
    assert(actual_submissions == (!parse_fail && should_send));
    assert(callback_count == (!parse_fail && should_send && !unconsumed));
    if (callback_count) assert(destroyed == 1);
    /* Also exercise all ownership branches of the explicit libc++ callback ABI. */
    Callback original = {&callbacks}, placed;
    live_callbacks = 1;
    Callback *copy = original.vtable->clone(&original);
    original.vtable->clone_into(&original, &placed);
    assert(live_callbacks == 3);
    placed.vtable->destroy(&placed);
    copy->vtable->destroy_deallocate(copy);
    original.vtable->destruct(&original);
    assert(live_callbacks == 0);
    return 0;
}
