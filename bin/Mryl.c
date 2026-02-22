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

// === State machine for double_value ===
typedef struct {
    int __state;
    int32_t n;
    MrylTask* __task;
} __DoubleValue_SM;

void __double_value_move_next(MrylTask* __task) {
    __DoubleValue_SM* __sm = (__DoubleValue_SM*)__task->sm;
    if (__task->state == MRYL_TASK_CANCELLED) return;
    switch (__sm->__state) {
        case 0: goto __state_0;
        default: return;
    }
    __state_0: {
        int32_t* __res = (int32_t*)malloc(sizeof(int32_t));
        *__res = (__sm->n * 2);
        __task->result = (void*)__res;
        __task->state = MRYL_TASK_COMPLETED;
        __task_release(__task);
        if (__task->awaiter) __scheduler_post(__task->awaiter);
        return;
    }
}

MrylTask* double_value(int32_t n) {
    MrylTask* __task = (MrylTask*)malloc(sizeof(MrylTask));
    __DoubleValue_SM* __sm = (__DoubleValue_SM*)malloc(sizeof(__DoubleValue_SM));
    memset(__sm, 0, sizeof(__DoubleValue_SM));
    __sm->n = n;
    __sm->__task  = __task;
    __task->strong_count = 1;
    __task->weak_count   = 0;
    __task->state        = MRYL_TASK_PENDING;
    __task->result       = NULL;
    __task->move_next    = __double_value_move_next;
    __task->on_cancel    = NULL;
    __task->awaiter      = NULL;
    __task->sm           = __sm;
    __scheduler_post(__task);
    return __task;
}

// ===== Async Lambda state machines =====
// === State machine for __lambda_0 ===
typedef struct {
    int __state;
    int32_t x;
    MrylTask* __task;
} __Lambda0_SM;

void ____lambda_0_move_next(MrylTask* __task) {
    __Lambda0_SM* __sm = (__Lambda0_SM*)__task->sm;
    if (__task->state == MRYL_TASK_CANCELLED) return;
    switch (__sm->__state) {
        case 0: goto __state_0;
        default: return;
    }
    __state_0: {
        println("%d", __sm->x);
        __task->state = MRYL_TASK_COMPLETED;
        __task_release(__task);
        if (__task->awaiter) __scheduler_post(__task->awaiter);
        return;
    }
}

MrylTask* __lambda_0(int32_t x) {
    MrylTask* __task = (MrylTask*)malloc(sizeof(MrylTask));
    __Lambda0_SM* __sm = (__Lambda0_SM*)malloc(sizeof(__Lambda0_SM));
    memset(__sm, 0, sizeof(__Lambda0_SM));
    __sm->x = x;
    __sm->__task  = __task;
    __task->strong_count = 1;
    __task->weak_count   = 0;
    __task->state        = MRYL_TASK_PENDING;
    __task->result       = NULL;
    __task->move_next    = ____lambda_0_move_next;
    __task->on_cancel    = NULL;
    __task->awaiter      = NULL;
    __task->sm           = __sm;
    __scheduler_post(__task);
    return __task;
}

// === State machine for __lambda_1 ===
typedef struct {
    int __state;
    int32_t x;
    int32_t result;
    MrylTask* __h_0;
    MrylTask* __task;
} __Lambda1_SM;

void ____lambda_1_move_next(MrylTask* __task) {
    __Lambda1_SM* __sm = (__Lambda1_SM*)__task->sm;
    if (__task->state == MRYL_TASK_CANCELLED) return;
    switch (__sm->__state) {
        case 0: goto __state_0;
        case 1: goto __state_1;
        default: return;
    }
    __state_0: {
        __sm->__h_0 = double_value(__sm->x);
        __task_retain(__sm->__h_0);
        __sm->__h_0->awaiter = __task;
        if (__sm->__h_0->state != MRYL_TASK_COMPLETED) {
            __sm->__state = 1;
            return;
        }
        goto __state_1;
    }
    __state_1: {
        if (__sm->__h_0->state == MRYL_TASK_CANCELLED) {
            __sm->result = 0;
        } else {
            __sm->result = *(int32_t*)__sm->__h_0->result;
        }
        __task_release(__sm->__h_0);
        println("%d", __sm->result);
        __task->state = MRYL_TASK_COMPLETED;
        __task_release(__task);
        if (__task->awaiter) __scheduler_post(__task->awaiter);
        return;
    }
}

MrylTask* __lambda_1(int32_t x) {
    MrylTask* __task = (MrylTask*)malloc(sizeof(MrylTask));
    __Lambda1_SM* __sm = (__Lambda1_SM*)malloc(sizeof(__Lambda1_SM));
    memset(__sm, 0, sizeof(__Lambda1_SM));
    __sm->x = x;
    __sm->__task  = __task;
    __task->strong_count = 1;
    __task->weak_count   = 0;
    __task->state        = MRYL_TASK_PENDING;
    __task->result       = NULL;
    __task->move_next    = ____lambda_1_move_next;
    __task->on_cancel    = NULL;
    __task->awaiter      = NULL;
    __task->sm           = __sm;
    __scheduler_post(__task);
    return __task;
}

// === State machine for main ===
typedef struct {
    int __state;
    void* greet;
    void* compute;
    MrylTask* __h_0;
    MrylTask* __h_1;
    MrylTask* __h_2;
    MrylTask* __h_3;
    MrylTask* __task;
} __Main_SM;

void __main_move_next(MrylTask* __task) {
    __Main_SM* __sm = (__Main_SM*)__task->sm;
    if (__task->state == MRYL_TASK_CANCELLED) return;
    switch (__sm->__state) {
        case 0: goto __state_0;
        case 1: goto __state_1;
        case 2: goto __state_2;
        case 3: goto __state_3;
        case 4: goto __state_4;
        default: return;
    }
    __state_0: {
        __sm->greet = (void*)__lambda_0;
        __sm->__h_0 = __lambda_0(42);
        __task_retain(__sm->__h_0);
        __sm->__h_0->awaiter = __task;
        if (__sm->__h_0->state != MRYL_TASK_COMPLETED) {
            __sm->__state = 1;
            return;
        }
        goto __state_1;
    }
    __state_1: {
        __task_release(__sm->__h_0);
        __sm->compute = (void*)__lambda_1;
        __sm->__h_1 = __lambda_1(5);
        __task_retain(__sm->__h_1);
        __sm->__h_1->awaiter = __task;
        if (__sm->__h_1->state != MRYL_TASK_COMPLETED) {
            __sm->__state = 2;
            return;
        }
        goto __state_2;
    }
    __state_2: {
        __task_release(__sm->__h_1);
        __sm->__h_2 = __lambda_0(100);
        __task_retain(__sm->__h_2);
        __sm->__h_2->awaiter = __task;
        if (__sm->__h_2->state != MRYL_TASK_COMPLETED) {
            __sm->__state = 3;
            return;
        }
        goto __state_3;
    }
    __state_3: {
        __task_release(__sm->__h_2);
        __sm->__h_3 = __lambda_1(10);
        __task_retain(__sm->__h_3);
        __sm->__h_3->awaiter = __task;
        if (__sm->__h_3->state != MRYL_TASK_COMPLETED) {
            __sm->__state = 4;
            return;
        }
        goto __state_4;
    }
    __state_4: {
        __task_release(__sm->__h_3);
        __task->state = MRYL_TASK_COMPLETED;
        __task_release(__task);
        if (__task->awaiter) __scheduler_post(__task->awaiter);
        return;
    }
}

int main(void) {
    __scheduler_init();
    MrylTask* __main_task = (MrylTask*)malloc(sizeof(MrylTask));
    __Main_SM* __main_sm = (__Main_SM*)malloc(sizeof(__Main_SM));
    memset(__main_sm, 0, sizeof(__Main_SM));
    __main_sm->__task  = __main_task;
    __main_task->strong_count = 2;
    __main_task->weak_count   = 0;
    __main_task->state        = MRYL_TASK_PENDING;
    __main_task->result       = NULL;
    __main_task->move_next    = __main_move_next;
    __main_task->on_cancel    = NULL;
    __main_task->awaiter      = NULL;
    __main_task->sm           = __main_sm;
    __scheduler_post(__main_task);
    __scheduler_run();
    __task_release(__main_task);
    return 0;
}
