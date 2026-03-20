# Mryl async/await 再設計メモ

---

## 実装済み（旧設計・pthreads）

- [x] `async fn` 宣言 (`is_async=True`)
- [x] `await` 式
- [x] pthreads ベースの C コード生成（`pthread_create` / `pthread_join`）
- [x] Python Interpreter: `threading.Thread` ベース

---

## 新設計の方針

### 採用するモデル
- **C# 形式**: Task + continuation + scheduler（単一スレッドのイベントループ）
- **メモリ管理**: strong_count + weak_count（`shared_ptr` + `weak_ptr` 相当）
- **Python Interpreter**: `asyncio` ベースへ移行

### 採用しない / 将来対応
- `pthread` は削除（`-lpthread` 不要になる）
- `weak Task<T>` 構文・`cancel()` は Phase D 以降
- `move` セマンティクス（`await move h`）は将来拡張

---

## Phase A: ランタイム生成（CodeGenerator）

### 対象ファイル
- `core/CodeGenerator.py` に `_emit_task_runtime()` を追加
- `Mryl.py` から `-lpthread` を削除

### 生成する C コード

```c
// === Mryl Task Runtime ===

typedef enum {
    MRYL_TASK_PENDING,
    MRYL_TASK_RUNNING,
    MRYL_TASK_COMPLETED,
    MRYL_TASK_CANCELLED,
    MRYL_TASK_FAULTED      // 将来の例外用（予約）
} MrylTaskState;

typedef struct MrylTask {
    int           strong_count;
    int           weak_count;
    MrylTaskState state;
    void*         result;                      // heap 上の戻り値
    void        (*move_next)(struct MrylTask*); // 状態機械ステップ
    void        (*on_cancel)(struct MrylTask*); // キャンセルフック（NULLも可）
    void*         sm;                          // SM 構造体へのポインタ
    struct MrylTask* awaiter;                  // await している親 Task
} MrylTask;

// strong 操作
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

// weak 操作
static inline MrylTask* __task_weak_retain(MrylTask* t) {
    if (t) t->weak_count++;
    return t;
}
static inline void __task_weak_release(MrylTask* t) {
    if (!t) return;
    if (--t->weak_count == 0 && t->strong_count == 0) free(t);
}

// weak → strong の昇格（lock）
// 成功: retain 済み strong ポインタ, 失敗（完了/キャンセル済み）: NULL
static inline MrylTask* __task_lock(MrylTask* t) {
    if (!t) return NULL;
    if (t->state == MRYL_TASK_CANCELLED ||
        t->state == MRYL_TASK_COMPLETED) return NULL;
    t->strong_count++;
    return t;
}

// キャンセル
static inline void __task_cancel(MrylTask* t) {
    if (!t) return;
    if (t->state == MRYL_TASK_PENDING || t->state == MRYL_TASK_RUNNING) {
        t->state = MRYL_TASK_CANCELLED;
        if (t->on_cancel) t->on_cancel(t);
        if (t->awaiter) __scheduler_post(t->awaiter);
    }
}

// スケジューラ（循環キュー）
#define __SCHEDULER_CAP 256
typedef struct {
    MrylTask* queue[__SCHEDULER_CAP];
    int head, tail;
} MrylScheduler;

static MrylScheduler __scheduler;

static inline void __scheduler_init() {
    __scheduler.head = __scheduler.tail = 0;
}
static inline void __scheduler_post(MrylTask* t) {
    __scheduler.queue[__scheduler.tail++ % __SCHEDULER_CAP] = t;
}
static inline void __scheduler_run() {
    while (__scheduler.head != __scheduler.tail) {
        MrylTask* t = __scheduler.queue[__scheduler.head++ % __SCHEDULER_CAP];
        if (t->state != MRYL_TASK_CANCELLED) t->move_next(t);
    }
}
```

---

## Phase B: async fn → 状態機械への変換（CodeGenerator）

### 対象ファイル
- `core/CodeGenerator.py`: `_generate_async_state_machine(func)` を新規作成
  - 従来の `_generate_async_thread_wrapper()` を置き換える

### 変換ルール

**Mryl ソース:**
```mryl
async fn compute_sum(n: i32) -> i32 {
    let result: i32 = n * n;
    return result;
}
```

**生成 C コード:**
```c
// 1. SM 構造体（MrylTask は分離 malloc）
typedef struct {
    int     __state;
    int32_t n;           // 引数
    int32_t result;      // ローカル変数
    MrylTask* __task;    // ← 埋め込みではなくポインタ
} __ComputeSum_SM;

// 2. move_next（状態機械本体）
void __compute_sum_move_next(MrylTask* __task) {
    __ComputeSum_SM* __sm = (__ComputeSum_SM*)__task->sm;
    if (__task->state == MRYL_TASK_CANCELLED) return;
    switch (__sm->__state) {
        case 0: {
            int32_t result = (__sm->n * __sm->n);
            __sm->result = result;
            int32_t* __res = (int32_t*)malloc(sizeof(int32_t));
            *__res = __sm->result;
            __task->result = (void*)__res;
            __task->state  = MRYL_TASK_COMPLETED;
            __task_release(__task);          // スケジューラ分 -1
            if (__task->awaiter) __scheduler_post(__task->awaiter);
            return;
        }
    }
}

// 3. ファクトリ関数
MrylTask* compute_sum(int32_t n) {
    MrylTask* __task = (MrylTask*)malloc(sizeof(MrylTask));
    __task->strong_count = 2;               // スケジューラ +1、呼び出し元 +1
    __task->weak_count   = 0;
    __task->state        = MRYL_TASK_PENDING;
    __task->result       = NULL;
    __task->move_next    = __compute_sum_move_next;
    __task->on_cancel    = NULL;
    __task->awaiter      = NULL;
    __ComputeSum_SM* __sm = (__ComputeSum_SM*)malloc(sizeof(__ComputeSum_SM));
    __sm->__state = 0;
    __sm->n       = n;
    __sm->__task  = __task;
    __task->sm    = __sm;
    __scheduler_post(__task);
    return __task;
}
```

### await ポイントが複数ある async fn の状態分割

```mryl
async fn process(n: i32) -> i32 {
    let raw: i32 = await fetch_data(n);   // await ポイント → state 0→1
    let r: i32   = await transform(raw);  // await ポイント → state 1→2
    return r;
}
```

```c
void __process_move_next(MrylTask* __task) {
    __Process_SM* __sm = (__Process_SM*)__task->sm;
    if (__task->state == MRYL_TASK_CANCELLED) return;
    switch (__sm->__state) {
        case 0:
            __sm->__fetch = fetch_data(__sm->n);
            __sm->__fetch->awaiter = __task;
            __task_retain(__sm->__fetch);
            if (__sm->__fetch->state != MRYL_TASK_COMPLETED) {
                __sm->__state = 1;
                return;   // スケジューラに制御を返す
            }
            // fall-through（既に完了）
        case 1:
            if (__sm->__fetch->state == MRYL_TASK_CANCELLED) { __sm->raw = 0; }
            else { __sm->raw = *(int32_t*)__sm->__fetch->result; }
            __task_release(__sm->__fetch);
            __sm->__transform = transform(__sm->raw);
            __sm->__transform->awaiter = __task;
            __task_retain(__sm->__transform);
            if (__sm->__transform->state != MRYL_TASK_COMPLETED) {
                __sm->__state = 2;
                return;
            }
        case 2:
            if (__sm->__transform->state == MRYL_TASK_CANCELLED) { __sm->r = 0; }
            else { __sm->r = *(int32_t*)__sm->__transform->result; }
            __task_release(__sm->__transform);
            int32_t* __res = (int32_t*)malloc(sizeof(int32_t));
            *__res = __sm->r;
            __task->result = (void*)__res;
            __task->state  = MRYL_TASK_COMPLETED;
            __task_release(__task);
            if (__task->awaiter) __scheduler_post(__task->awaiter);
            return;
    }
}
```

---

## Phase C: await を含む通常関数の状態機械化（CodeGenerator）

### 対象
`await` を使う **全関数**（`async fn` でない `fn` も含む）を状態機械化する。  
`main()` も同様。

### main() の変換

**Mryl ソース:**
```mryl
fn main() {
    let handle = compute_sum(7);
    let result: i32 = await handle;
    println("{}", result);
    let h2 = print_message();
    await h2;
}
```

**生成 C コード:**
```c
typedef struct {
    int      __state;
    MrylTask* handle;
    MrylTask* h2;
    int32_t  result;
    MrylTask* __task;
} __Main_SM;

void __main_move_next(MrylTask* __task) {
    __Main_SM* __sm = (__Main_SM*)__task->sm;
    switch (__sm->__state) {
        case 0:
            __sm->handle = compute_sum(7);
            __task_retain(__sm->handle);
            __sm->handle->awaiter = __task;
            if (__sm->handle->state != MRYL_TASK_COMPLETED) {
                __sm->__state = 1; return;
            }
        case 1:
            if (__sm->handle->state == MRYL_TASK_CANCELLED) { __sm->result = 0; }
            else { __sm->result = *(int32_t*)__sm->handle->result; }
            __task_release(__sm->handle);
            println("%d", __sm->result);
            __sm->h2 = print_message();
            __task_retain(__sm->h2);
            __sm->h2->awaiter = __task;
            if (__sm->h2->state != MRYL_TASK_COMPLETED) {
                __sm->__state = 2; return;
            }
        case 2:
            __task_release(__sm->h2);
            __task->state = MRYL_TASK_COMPLETED;
            __task_release(__task);
            return;
    }
}

int main(void) {
    __scheduler_init();
    MrylTask* __main_task = (MrylTask*)malloc(sizeof(MrylTask));
    __Main_SM* __main_sm  = (__Main_SM*)malloc(sizeof(__Main_SM));
    __main_sm->__state = 0;
    __main_sm->__task  = __main_task;
    __main_task->strong_count = 1;
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
```

---

## Phase D: Python Interpreter → asyncio 移行

### 対象ファイル
- `core/Interpreter.py`

### 変更方針

| 現在 | 移行後 |
|------|--------|
| `threading.Thread` | `asyncio` コルーチン + `asyncio.Task` |
| `thread.join()` | `await asyncio.Task` |
| `{'__future__': True, 'thread', 'result'}` | `asyncio.Task` オブジェクト |
| main 実行 | `asyncio.run(eval_main())` |

### 実装イメージ

```python
import asyncio

# async fn の本体を async def コルーチンとして実行
async def _eval_async_body(self, func, env):
    return await self._run_block_async(func.body, env)

# eval_expr 内での変更
# async fn 呼び出し
if isinstance(func_decl, FunctionDecl) and func_decl.is_async:
    loop = asyncio.get_event_loop()
    task = loop.create_task(self._eval_async_body(func_decl, env))
    return task   # asyncio.Task を返す（Task<T> 相当）

# await 式
if isinstance(expr, AwaitExpr):
    task = self.eval_expr(expr.expr)
    return await task   # asyncio の await

# main 実行
asyncio.run(self.eval_main())
```

---

## 将来対応（Phase E 以降）

### - [ ] `weak Task<T>` 構文
```mryl
let token = weak(handle);   // weak 参照取得
```
- Lexer: `weak` キーワード追加
- TypeChecker: `WeakTask<T>` 型
- CodeGenerator: `__task_weak_retain()` / `__task_weak_release()` 呼び出し生成

### - [ ] `cancel()` 組み込み関数
```mryl
cancel(token);   // weak 参照経由でキャンセル
```
- CodeGenerator: `__task_cancel()` 呼び出し生成
- Interpreter: `asyncio.Task.cancel()` に対応

### - [ ] `move` セマンティクス（`await move handle`）
```mryl
let r: i32 = await move handle;   // 所有権移転、handle は以降使用不可
```
- TypeChecker に「move 後の変数使用禁止」チェック追加（Rust borrow checker 的な解析）
- 2重 await を型レベルで防止

### - [ ] `Option<T>` 型の導入
- `await` キャンセル済み Task の戻り値を `None` にする
- 現状はゼロ値（`0` / `false` / `""`）で代替

### - [ ] `MRYL_TASK_FAULTED`（例外/エラー）
- `async fn` から例外的な失敗を伝える仕組み
- `result` に `MrylError*` を格納するか、専用フィールドを追加

---

## 影響ファイル一覧

| ファイル | Phase | 変更内容 |
|---------|-------|---------|
| `core/CodeGenerator.py` | A B C | `_emit_task_runtime()`, `_generate_async_state_machine()`, main 状態機械化 |
| `core/Interpreter.py` | D | `threading` → `asyncio` |
| `core/TypeChecker.py` | B | `Future<T>` → `Task<T>`（将来: `WeakTask<T>`） |
| `core/Ast.py` | — | 変更なし |
| `core/Lexer.py` | E | `weak` キーワード（将来） |
| `core/Parser.py` | E | `weak(expr)` 構文（将来） |
| `core/Mryl.py` | A | `-lpthread` 削除 |
| `my/test_async.ml` | C | 動作確認用（変更不要。既存テストが通ることを確認） |
