#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include <time.h>
#include <regex.h>

// ============================================================
// Mryl Task Runtime
// ============================================================

typedef enum {
    MRYL_TASK_PENDING,
    MRYL_TASK_RUNNING,
    MRYL_TASK_COMPLETED,
    MRYL_TASK_CANCELLED,
    MRYL_TASK_FAULTED
} MrylTaskState;

typedef struct MrylTask {
    int           strong_count;
    int           weak_count;
    MrylTaskState state;
    void*         result;
    void        (*move_next)(struct MrylTask*);
    void        (*on_cancel)(struct MrylTask*);
    void*         sm;
    struct MrylTask* awaiter;
} MrylTask;

#define __SCHEDULER_CAP 256
typedef struct {
    MrylTask* queue[__SCHEDULER_CAP];
    int head, tail;
} MrylScheduler;

static MrylScheduler __scheduler;

static inline void __scheduler_init(void) {
    __scheduler.head = __scheduler.tail = 0;
}
static inline void __scheduler_post(MrylTask* t) {
    __scheduler.queue[__scheduler.tail++ % __SCHEDULER_CAP] = t;
}
static inline void __scheduler_run(void) {
    while (__scheduler.head != __scheduler.tail) {
        MrylTask* t = __scheduler.queue[__scheduler.head++  % __SCHEDULER_CAP];
        if (t->state != MRYL_TASK_CANCELLED) t->move_next(t);
    }
}

static inline MrylTask* __task_retain(MrylTask* t) {
    if (t) t->strong_count++;
    return t;
}
static inline void __task_release(MrylTask* t) {
    if (!t) return;
    if (--t->strong_count == 0) {
        if (t->result) { free(t->result); t->result = NULL; }
        if (t->sm)     { free(t->sm);     t->sm     = NULL; }
        if (t->weak_count == 0) free(t);
    }
}
static inline MrylTask* __task_weak_retain(MrylTask* t) {
    if (t) t->weak_count++;
    return t;
}
static inline void __task_weak_release(MrylTask* t) {
    if (!t) return;
    if (--t->weak_count == 0 && t->strong_count == 0) free(t);
}
static inline MrylTask* __task_lock(MrylTask* t) {
    if (!t) return NULL;
    if (t->state == MRYL_TASK_CANCELLED ||
        t->state == MRYL_TASK_COMPLETED) return NULL;
    t->strong_count++;
    return t;
}
static inline void __task_cancel(MrylTask* t) {
    if (!t) return;
    if (t->state == MRYL_TASK_PENDING || t->state == MRYL_TASK_RUNNING) {
        t->state = MRYL_TASK_CANCELLED;
        if (t->on_cancel) t->on_cancel(t);
        if (t->awaiter)  __scheduler_post(t->awaiter);
    }
}

// ============================================================
// Built-in types and structures
// ============================================================

typedef struct {
    char* data;
    int length;
} MrylString;

// ============================================================
// Built-in functions
// ============================================================

static void mryl_panic(
        const char* error_type, const char* message,
        const char* func, const char* file, int line) {
    time_t __now = time(NULL);
    struct tm* __tm = localtime(&__now);
    char __timebuf[24];
    strftime(__timebuf, sizeof(__timebuf), "%Y-%m-%d %H:%M:%S", __tm);
    // Brief one-liner to stdout
    printf("[FATAL] %s: %s\n  See stderr for full error report.\n", error_type, message);
    // Detailed report to stderr
    fprintf(stderr, "[%s] ERROR %s: %s\n", __timebuf, error_type, message);
    fprintf(stderr, "  function: %s\n", func);
    fprintf(stderr, "  file: %s\n", file);
    fprintf(stderr, "  line: %d\n", line);
    fprintf(stderr, "\nStacktrace:\n");
    fprintf(stderr, "  %s(%s:%d)\n", func, file, line);
    exit(1);
}

void print(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    vprintf(fmt, args);
    va_end(args);
}

void println(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    vprintf(fmt, args);
    va_end(args);
    printf("\n");
}

// MrylString helper functions
MrylString make_mryl_string(const char* str) {
    MrylString s;
    s.data = (char*)malloc(strlen(str) + 1);
    strcpy(s.data, str);
    s.length = strlen(str);
    return s;
}

void free_mryl_string(MrylString s) {
    if (s.data != NULL) {
        free(s.data);
    }
}

MrylString mryl_string_concat(MrylString a, MrylString b) {
    int new_length = a.length + b.length;
    MrylString result;
    result.data = (char*)malloc(new_length + 1);
    strcpy(result.data, a.data);
    strcat(result.data, b.data);
    result.length = new_length;
    return result;
}

MrylString to_string(int32_t n) {
    char buf[32];
    snprintf(buf, sizeof(buf), "%d", n);
    return make_mryl_string(buf);
}

int main(void) {
    println("=== 15: Loop Boundary Tests ===");
    println("--- while ---");
    int32_t w0 = 0;
    int32_t wi0 = 0;
    while (wi0 < 0) {
        w0 = (w0 + wi0);
        wi0++;
    }
    println("while_0iter_sum=%d", w0);
    int32_t w1 = 0;
    int32_t wi1 = 0;
    while (wi1 < 1) {
        w1 = (w1 + wi1);
        wi1++;
    }
    println("while_1iter_sum=%d", w1);
    int32_t w5 = 0;
    int32_t wi5 = 0;
    while (wi5 < 5) {
        w5 = (w5 + wi5);
        wi5++;
    }
    println("while_5iter_sum=%d", w5);
    int32_t w10 = 0;
    int32_t wi10 = 0;
    while (wi10 < 10) {
        w10 = (w10 + wi10);
        wi10++;
    }
    println("while_10iter_sum=%d", w10);
    println("--- for range ---");
    int32_t fr0 = 0;
    for (int _n0 = 0; _n0 < 0; _n0++) {
        fr0 = (fr0 + 1);
    }
    println("range_0iter_count=%d", fr0);
    int32_t fr1 = 0;
    for (int _n1 = 0; _n1 < 1; _n1++) {
        fr1 = (fr1 + 1);
    }
    println("range_1iter_count=%d", fr1);
    int32_t fr5 = 0;
    for (int _n5 = 0; _n5 < 5; _n5++) {
        fr5 = (fr5 + 1);
    }
    println("range_5iter_count=%d", fr5);
    int32_t fr5s = 0;
    for (int ns = 0; ns < 5; ns++) {
        fr5s = (fr5s + ns);
    }
    println("range_5iter_sum=%d", fr5s);
    println("--- for C-style ---");
    int32_t fc0 = 0;
    for (int32_t j0 = 0; j0 < 0; j0++) {
        fc0 = (fc0 + 1);
    }
    println("cfor_0iter_count=%d", fc0);
    int32_t fc1 = 0;
    for (int32_t j1 = 0; j1 < 1; j1++) {
        fc1 = (fc1 + 1);
    }
    println("cfor_1iter_count=%d", fc1);
    int32_t fc_last = (-1);
    for (int32_t j2 = 0; j2 <= 8; j2 = (j2 + 2)) {
        fc_last = j2;
    }
    println("cfor_step2_last=%d", fc_last);
    println("--- break ---");
    int32_t br_last = (-1);
    for (int nb = 0; nb < 10; nb++) {
        if (nb == 3) {
            break;
        }
        br_last = nb;
    }
    println("break_last=%d", br_last);
    int32_t br0 = 0;
    for (int nb0 = 0; nb0 < 10; nb0++) {
        if (nb0 == 0) {
            break;
        }
        br0 = (br0 + 1);
    }
    println("break_0iter_count=%d", br0);
    println("--- continue ---");
    int32_t cont = 0;
    int32_t cont_last = (-1);
    for (int nc = 0; nc < 5; nc++) {
        if ((nc % 2) == 0) {
            continue;
        }
        cont = (cont + 1);
        cont_last = nc;
    }
    println("continue_odd_count=%d", cont);
    println("continue_last=%d", cont_last);
    println("=== OK ===");
    return 0;
}
