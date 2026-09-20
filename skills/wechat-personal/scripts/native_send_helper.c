/* Development-only adapter for one pinned Linux WeChat build.
 * No C++ standard library is linked: its libc++ function/string ABI is explicit.
 * The host keeps this small DSO mapped until client exit, so an asynchronous
 * callback can never return into unloaded code. No receiver or service runs.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

typedef struct { unsigned char bytes[24]; } NativeString;
typedef struct Callback Callback;
typedef struct {
    void (*destruct)(Callback *);
    void (*delete_object)(Callback *);
    Callback *(*clone)(const Callback *);
    void (*clone_into)(const Callback *, Callback *);
    void (*destroy)(Callback *);
    void (*destroy_deallocate)(Callback *);
    bool (*invoke)(Callback *, void **, const int *, const int *);
    const void *(*target)(const Callback *, const void *);
    const void *(*target_type)(const Callback *);
} CallbackTable;
struct Callback { const CallbackTable *vtable; };
typedef struct { unsigned char storage[32]; Callback *target; } NativeFunction;
_Static_assert(sizeof(NativeString) == 24, "libc++ string size");
_Static_assert(__builtin_offsetof(NativeFunction, target) == 32, "function pointer offset");

typedef struct {
    void (*request_ctor)(void *);
    void (*request_dtor)(void *);
    bool (*parse)(void *, const void *, int);
    bool (*serialize)(void *, NativeString *);
    void (*native_delete)(void *);
    void (*business_delete)(void *);
    uint32_t (*submit)(void *, void *, NativeString *, void *, NativeFunction *);
    void *service;
} NativeApi;

static NativeApi api;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static int output_fd = -1, started, worker_done, parsed, submitted;
static int callback_count, destroyed, live_callbacks, error_type, error_code, failure;
static uint32_t task_id;
static unsigned char payload[2048];
static size_t payload_size;
static int should_send;
static char arm_path[PATH_MAX];
static int submit_returned;
static void *pending_business;

/* Caller holds lock. Report only metadata; never copy account/request data. */
static void report_locked(void) {
    if (output_fd < 0) return;
    char json[768];
    int size = snprintf(json, sizeof(json),
        "{\"worker_done\":%s,\"native_roundtrip_verified\":%s,"
        "\"submission_entered\":%s,\"task_id\":%u,\"callback_count\":%d,"
        "\"callback_destroyed\":%d,\"live_callbacks\":%d,"
        "\"error_type\":%d,\"error_code\":%d,\"failure\":%d}\n",
        worker_done ? "true" : "false", parsed ? "true" : "false",
        submitted ? "true" : "false", task_id, callback_count,
        destroyed, live_callbacks, error_type, error_code, failure);
    if (size > 0 && (size_t)size < sizeof(json)) {
        if (pwrite(output_fd, json, (size_t)size, 0) == size)
            (void)ftruncate(output_fd, size);
    }
    if (worker_done && !live_callbacks) { close(output_fd); output_fd = -1; }
}

static void cb_destroy(Callback *self) {
    (void)self;
    pthread_mutex_lock(&lock);
    --live_callbacks;
    ++destroyed;
    report_locked();
    pthread_mutex_unlock(&lock);
}
static void cb_delete(Callback *self) { cb_destroy(self); free(self); }
static Callback *cb_clone(const Callback *self) {
    Callback *copy = malloc(sizeof(*copy));
    if (!copy) abort(); /* Same allocation-failure contract as throwing operator new. */
    *copy = *self;
    pthread_mutex_lock(&lock);
    ++live_callbacks;
    pthread_mutex_unlock(&lock);
    return copy;
}
static void cb_clone_into(const Callback *self, Callback *copy) {
    *copy = *self;
    pthread_mutex_lock(&lock);
    ++live_callbacks;
    pthread_mutex_unlock(&lock);
}
static bool cb_invoke(Callback *self, void **business, const int *type, const int *code) {
    (void)self;
    void *release = NULL;
    pthread_mutex_lock(&lock);
    ++callback_count;
    error_type = *type;
    error_code = *code;
    if (submit_returned) release = *business;
    else pending_business = *business;
    report_locked();
    pthread_mutex_unlock(&lock);
    /* submit still reads business after its lower call returns. A fast callback
     * must not delete it first. Take ownership with false, and release only once
     * submit has returned. The verified false branch is a register-only epilogue.
     * No self/business access is allowed after this unlocked ownership handoff. */
    if (release) api.business_delete(release);
    return false;
}
static const void *cb_target(const Callback *self, const void *type) {
    (void)self; (void)type; return NULL;
}
static const void *cb_type(const Callback *self) { (void)self; return NULL; }
static const CallbackTable callbacks = {
    cb_destroy, cb_delete, cb_clone, cb_clone_into, cb_destroy, cb_delete,
    cb_invoke, cb_target, cb_type
};

static size_t string_length(const NativeString *str) {
    size_t size;
    if (!(str->bytes[0] & 1)) return str->bytes[0] >> 1;
    memcpy(&size, str->bytes + 8, sizeof(size)); return size;
}
static const void *string_data(const NativeString *str) {
    const void *data;
    if (!(str->bytes[0] & 1)) return str->bytes + 1;
    memcpy(&data, str->bytes + 16, sizeof(data)); return data;
}

static void *worker(void *unused) {
    (void)unused;
    /* Do not run native work while the debugger is attached. The parent creates
     * this private marker only after checking that detach actually succeeded. */
    int armed = 0;
    for (int attempt = 0; attempt < 500; ++attempt) {
        struct stat info;
        if (!lstat(arm_path, &info) && S_ISREG(info.st_mode) && info.st_uid == getuid()
            && !(info.st_mode & 077)) { armed = 1; unlink(arm_path); break; }
        usleep(20000);
    }
    if (!armed) {
        pthread_mutex_lock(&lock);
        failure = 4; worker_done = 1; report_locked();
        pthread_mutex_unlock(&lock);
        return NULL;
    }
    _Alignas(16) unsigned char request[0x30] = {0};
    _Alignas(16) unsigned char config[0x28] = {0};
    NativeString roundtrip = {0}, addon = {0};
    NativeFunction function = {0};
    api.request_ctor(request);
    int ok = api.parse(request, payload, (int)payload_size);
    if (ok) ok = api.serialize(request, &roundtrip);
    if (ok) ok = string_length(&roundtrip) == payload_size &&
                 !memcmp(string_data(&roundtrip), payload, payload_size);
    if (roundtrip.bytes[0] & 1) api.native_delete((void *)string_data(&roundtrip));
    pthread_mutex_lock(&lock);
    parsed = !!ok;
    if (!ok) failure = 1;
    report_locked();
    pthread_mutex_unlock(&lock);
    if (ok && should_send) {
        function.target = malloc(sizeof(Callback));
        if (!function.target) {
            pthread_mutex_lock(&lock); failure = 2; pthread_mutex_unlock(&lock);
        } else {
            function.target->vtable = &callbacks;
            pthread_mutex_lock(&lock);
            ++live_callbacks;
            /* Persist uncertainty before the first possibly mutating call. */
            submitted = 1;
            report_locked();
            pthread_mutex_unlock(&lock);
            uint32_t returned_id = api.submit(api.service, request, &addon, config, &function);
            pthread_mutex_lock(&lock);
            task_id = returned_id;
            submit_returned = 1;
            void *release = pending_business;
            pending_business = NULL;
            pthread_mutex_unlock(&lock);
            if (release) api.business_delete(release);
            /* The verified heap branch transfers ownership and zeros target. */
            if (function.target) {
                cb_delete(function.target);
                pthread_mutex_lock(&lock); failure = 3; pthread_mutex_unlock(&lock);
            }
        }
    }
    api.request_dtor(request);
    memset(payload, 0, sizeof(payload));
    pthread_mutex_lock(&lock);
    worker_done = 1;
    report_locked();
    pthread_mutex_unlock(&lock);
    return NULL;
}

/* Called once by the debugger; native work waits for verified detach. */
__attribute__((visibility("default")))
int ncut_launch(uintptr_t base, const void *data, size_t length, const char *result, int send) {
    if (length == 0 || length > sizeof(payload) || !base || (send != 0 && send != 1)
        || strlen(result) + 5 >= sizeof(arm_path)) return EINVAL;
    pthread_mutex_lock(&lock);
    if (started) { pthread_mutex_unlock(&lock); return EALREADY; }
    started = 1;
    pthread_mutex_unlock(&lock);
    api = (NativeApi){
        .request_ctor = (void *) (base + 0x79ed4d0),
        .request_dtor = (void *) (base + 0x79ed660),
        .parse = (void *) (base + 0x8f500e0),
        .serialize = (void *) (base + 0x8f504c0),
        .native_delete = (void *) (base + 0x450a140),
        .business_delete = (void *) (base + 0x695c340),
        .submit = (void *) (base + 0x695bf60)
    };
    uintptr_t account = *(uintptr_t *)(base + 0xacef550);
    if (!account) return ENOTCONN;
    api.service = *(void **)(account + 0x250);
    if (!api.service || *(uintptr_t *)api.service != base + 0xa981948 ||
        !(*(unsigned char *)((char *)api.service + 8) & 1)) return ENOTCONN;
    output_fd = open(result, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (output_fd < 0) return errno;
    memcpy(payload, data, length);
    payload_size = length;
    should_send = send;
    snprintf(arm_path, sizeof(arm_path), "%s.arm", result);
    report_locked();
    pthread_t thread;
    pthread_attr_t attr;
    int code = pthread_attr_init(&attr);
    if (!code) {
        code = pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED);
        if (!code) code = pthread_create(&thread, &attr, worker, NULL);
        pthread_attr_destroy(&attr);
    }
    if (code) { close(output_fd); output_fd = -1; }
    return code;
}
