from __future__ import annotations
from CodeGenerator._proto import _CodeGeneratorBase

class CodeGeneratorAsyncMixin(_CodeGeneratorBase):
    """非同期ステートマシン生成を担当する Mixin
    _sm_let_c_type / _split_by_await /
    _generate_async_state_machine / _emit_await_setup /
    _emit_await_resume / _generate_sm_stmt /
    _emit_task_complete / _emit_task_factory /
    _emit_main_sm_entry / _emit_task_runtime
    """

    def _sm_let_c_type(self, stmt) -> str:
        """SM フィールドの C 型を LetDecl ノードから決定する """
        init_cls = stmt.init_expr.__class__.__name__ if stmt.init_expr else None
        if init_cls == 'Lambda':
            return 'void*'
        if init_cls == 'FunctionCall':
            f = self.program_functions.get(stmt.init_expr.name)
            if f and getattr(f, 'is_async', False):
                return 'MrylTask*'
            for scope in reversed(self.env):
                if stmt.init_expr.name in scope and scope[stmt.init_expr.name] == 'async_fn':
                    return 'MrylTask*'
        if init_cls == 'AwaitExpr' and stmt.type_node:
            return self._type_to_c(stmt.type_node)
        if stmt.type_node:
            return self._type_to_c(stmt.type_node)
        return 'int32_t'

    def _split_by_await(self, stmts):
        """文リストを await ごとにセグメント分割する
        戻り値: [(pre_stmts, await_stmt_or_None)]
        """
        segments = []
        current  = []
        for stmt in stmts:
            cls      = stmt.__class__.__name__
            is_await = (
                (cls == 'LetDecl' and stmt.init_expr and
                 stmt.init_expr.__class__.__name__ == 'AwaitExpr') or
                (cls == 'ExprStmt' and stmt.expr.__class__.__name__ == 'AwaitExpr')
            )
            if is_await:
                segments.append((current, stmt))
                current = []
            else:
                current.append(stmt)
        segments.append((current, None))
        return segments

    def _generate_async_state_machine(self, func):
        """async 関数をステートマシン形式の C コードとして出力する """
        func_name      = func.name
        is_main        = (func_name == 'main')
        has_return_val = (not is_main) and \
                         func.return_type and func.return_type.name != 'void'

        sm_struct  = f"__{self._to_pascal(func_name)}_SM"
        move_next  = f"__{func_name}_move_next"

        # SM フィールド収集
        sm_fields = []
        if not is_main:
            for p in (func.params or []):
                sm_fields.append((
                    self._type_to_c(p.type_node),
                    p.name,
                    p.type_node.name if p.type_node else 'any',
                ))
        for stmt in (func.body.statements if func.body else []):
            if stmt.__class__.__name__ == 'LetDecl':
                sm_fields.append((self._sm_let_c_type(stmt), stmt.name, 'any'))

        stmts_preview    = func.body.statements if func.body else []
        sm_await_handles = {}
        for i, (_, aw) in enumerate(self._split_by_await(stmts_preview)):
            if aw is None:
                continue
            aw_cls = aw.__class__.__name__
            inner  = aw.expr.expr if aw_cls == 'ExprStmt' else aw.init_expr.expr
            if inner.__class__.__name__ == 'FunctionCall':
                hf = f"__h_{i}"
                sm_await_handles[i] = hf
                sm_fields.append(('MrylTask*', hf, 'any'))
        self.sm_await_handles = sm_await_handles

        for (_, fname, mtype) in sm_fields:
            self.env[-1][fname] = mtype

        # 1. SM 構造体を出力
        self._emit(f"// === State machine for {func_name} ===")
        self._emit(f"typedef struct {{")
        self.indent_level += 1
        self._emit("int __state;")
        for (ctype, fname, _) in sm_fields:
            self._emit(f"{ctype} {fname};")
        self._emit("MrylTask* __task;")
        self.indent_level -= 1
        self._emit(f"}} {sm_struct};")
        self._emit("")

        # 2. move_next 関数を出力
        stmts    = func.body.statements if func.body else []
        segments = self._split_by_await(stmts)
        num_states = len(segments)

        self._emit(f"void {move_next}(MrylTask* __task) {{")
        self.indent_level += 1
        self._emit(f"{sm_struct}* __sm = ({sm_struct}*)__task->sm;")
        self._emit("if (__task->state == MRYL_TASK_CANCELLED) return;")
        self._emit(f"switch (__sm->__state) {{")
        self.indent_level += 1
        for i in range(num_states):
            self._emit(f"case {i}: goto __state_{i};")
        self._emit("default: return;")
        self.indent_level -= 1
        self._emit("}")

        self.sm_mode = True
        self.sm_vars = {fname for (_, fname, _) in sm_fields}

        for i, (pre_stmts, await_stmt) in enumerate(segments):
            self._emit(f"__state_{i}: {{")
            self.indent_level += 1

            if i > 0:
                self._emit_await_resume(segments[i - 1][1], i - 1)

            for stmt in pre_stmts:
                self._generate_sm_stmt(stmt, func, has_return_val)

            if await_stmt is not None:
                self._emit_await_setup(await_stmt, i + 1, i)
                self._emit(f"goto __state_{i + 1};")
            else:
                has_explicit_return = any(
                    s.__class__.__name__ == 'ReturnStmt' for s in pre_stmts
                )
                if not has_explicit_return:
                    self._emit_task_complete(func, has_return_val)

            self.indent_level -= 1
            self._emit("}")

        self.sm_mode = False
        self.sm_vars = set()

        self.indent_level -= 1
        self._emit("}")
        self._emit("")

        # 3. ファクトリ関数 or main エントリポイント
        if is_main:
            self._emit_main_sm_entry(sm_struct, move_next)
        else:
            self._emit_task_factory(func, sm_struct, move_next)

    def _emit_await_setup(self, await_stmt, next_state: int, await_index: int = 0):
        """await セットアップ(タスクの awaiter 設定 + サスペンド)を出力する """
        cls = await_stmt.__class__.__name__
        if await_index in self.sm_await_handles:
            hf         = self.sm_await_handles[await_index]
            inner      = await_stmt.expr.expr if cls == 'ExprStmt' else await_stmt.init_expr.expr
            call_code  = self._generate_expr(inner)
            self._emit(f"__sm->{hf} = {call_code};")
            self._emit(f"__task_retain(__sm->{hf});")
            handle = f"__sm->{hf}"
        else:
            if cls == 'ExprStmt':
                handle = self._generate_expr(await_stmt.expr.expr)
            else:
                handle = self._generate_expr(await_stmt.init_expr.expr)

        self._emit(f"{handle}->awaiter = __task;")
        self._emit(f"if ({handle}->state != MRYL_TASK_COMPLETED) {{")
        self.indent_level += 1
        self._emit(f"__sm->__state = {next_state};")
        self._emit("return;")
        self.indent_level -= 1
        self._emit("}")

    def _emit_await_resume(self, await_stmt, await_index: int = 0):
        """await 再開時( resume )の結果取得コードを出力する """
        cls = await_stmt.__class__.__name__
        if await_index in self.sm_await_handles:
            handle = f"__sm->{self.sm_await_handles[await_index]}"
        else:
            if cls == 'ExprStmt':
                handle = self._generate_expr(await_stmt.expr.expr)
            else:
                handle = self._generate_expr(await_stmt.init_expr.expr)

        if cls == 'LetDecl':
            var = await_stmt.name
            if await_stmt.type_node and await_stmt.type_node.name != 'void':
                ctype = self._type_to_c(await_stmt.type_node)
                self._emit(f"if ({handle}->state == MRYL_TASK_CANCELLED) {{")
                self.indent_level += 1
                self._emit(f"__sm->{var} = 0;")
                self.indent_level -= 1
                self._emit("} else {")
                self.indent_level += 1
                self._emit(f"__sm->{var} = *({ctype}*){handle}->result;")
                self.indent_level -= 1
                self._emit("}")
        self._emit(f"__task_release({handle});")

    def _generate_sm_stmt(self, stmt, func, has_return_val: bool):
        """SM 内文を出力する (LetDecl/ReturnStmt は SM フィールドへ代入) """
        cls      = stmt.__class__.__name__
        if cls == 'LetDecl':
            init_cls     = stmt.init_expr.__class__.__name__ if stmt.init_expr else None
            if init_cls == 'Lambda':
                lam_func = self._generate_expr(stmt.init_expr)
                self._emit(f"__sm->{stmt.name} = (void*){lam_func};")
                if getattr(stmt.init_expr, 'is_async', False):
                    self.env[-1][stmt.name] = "async_fn"
                    self.async_lambda_factories[stmt.name] = lam_func
                else:
                    self.env[-1][stmt.name] = "fn"
                return
            if init_cls == 'FunctionCall':
                f            = self.program_functions.get(stmt.init_expr.name)
                is_async_call = f and getattr(f, 'is_async', False)
                if not is_async_call:
                    for scope in reversed(self.env):
                        if stmt.init_expr.name in scope and scope[stmt.init_expr.name] == 'async_fn':
                            is_async_call = True
                            break
                if is_async_call:
                    args        = [self._generate_expr(a) for a in stmt.init_expr.args]
                    args_str    = ", ".join(args)
                    call_target = self.async_lambda_factories.get(stmt.init_expr.name, stmt.init_expr.name)
                    self._emit(f"__sm->{stmt.name} = {call_target}({args_str});")
                    self._emit(f"__task_retain(__sm->{stmt.name});")
                    return
            if stmt.init_expr:
                init_code = self._generate_expr(stmt.init_expr)
                self._emit(f"__sm->{stmt.name} = {init_code};")
        elif cls == 'ReturnStmt':
            if has_return_val and stmt.expr:
                ret_ctype = self._type_to_c(func.return_type)
                ret_code  = self._generate_expr(stmt.expr)
                self._emit(f"{ret_ctype}* __res = ({ret_ctype}*)malloc(sizeof({ret_ctype}));")
                self._emit(f"*__res = {ret_code};")
                self._emit(f"__task->result = (void*)__res;")
            self._emit("__task->state = MRYL_TASK_COMPLETED;")
            self._emit("__task_release(__task);")
            self._emit("if (__task->awaiter) __scheduler_post(__task->awaiter);")
            self._emit("return;")
        else:
            self._generate_statement(stmt)

    def _emit_task_complete(self, func, has_return_val: bool):
        """タスク完了コードを出力する (戻り値なしの場合) """
        if not has_return_val:
            self._emit("__task->state = MRYL_TASK_COMPLETED;")
            self._emit("__task_release(__task);")
            self._emit("if (__task->awaiter) __scheduler_post(__task->awaiter);")
            self._emit("return;")

    def _emit_task_factory(self, func, sm_struct: str, move_next: str):
        """タスクファクトリ関数を出力する (async fn の entry point) """
        func_name  = func.name
        params     = [f"{self._type_to_c(p.type_node)} {p.name}" for p in (func.params or [])]
        params_str = ", ".join(params) if params else "void"
        self._emit(f"MrylTask* {func_name}({params_str}) {{")
        self.indent_level += 1
        self._emit(f"MrylTask* __task = (MrylTask*)malloc(sizeof(MrylTask));")
        self._emit(f"{sm_struct}* __sm = ({sm_struct}*)malloc(sizeof({sm_struct}));")
        self._emit(f"memset(__sm, 0, sizeof({sm_struct}));")
        for p in (func.params or []):
            self._emit(f"__sm->{p.name} = {p.name};")
        self._emit(f"__sm->__task  = __task;")
        self._emit(f"__task->strong_count = 1;")
        self._emit(f"__task->weak_count   = 0;")
        self._emit(f"__task->state        = MRYL_TASK_PENDING;")
        self._emit(f"__task->result       = NULL;")
        self._emit(f"__task->move_next    = {move_next};")
        self._emit(f"__task->on_cancel    = NULL;")
        self._emit(f"__task->awaiter      = NULL;")
        self._emit(f"__task->sm           = __sm;")
        self._emit(f"__scheduler_post(__task);")
        self._emit(f"return __task;")
        self.indent_level -= 1
        self._emit("}")
        self._emit("")

    def _emit_main_sm_entry(self, sm_struct: str, move_next: str):
        """main 関数のスケジューラエントリポイントを出力する """
        self._emit("int main(void) {")
        self.indent_level += 1
        self._emit("__scheduler_init();")
        self._emit(f"MrylTask* __main_task = (MrylTask*)malloc(sizeof(MrylTask));")
        self._emit(f"{sm_struct}* __main_sm = ({sm_struct}*)malloc(sizeof({sm_struct}));")
        self._emit(f"memset(__main_sm, 0, sizeof({sm_struct}));")
        self._emit(f"__main_sm->__task  = __main_task;")
        self._emit(f"__main_task->strong_count = 2;")
        self._emit(f"__main_task->weak_count   = 0;")
        self._emit(f"__main_task->state        = MRYL_TASK_PENDING;")
        self._emit(f"__main_task->result       = NULL;")
        self._emit(f"__main_task->move_next    = {move_next};")
        self._emit(f"__main_task->on_cancel    = NULL;")
        self._emit(f"__main_task->awaiter      = NULL;")
        self._emit(f"__main_task->sm           = __main_sm;")
        self._emit(f"__scheduler_post(__main_task);")
        self._emit(f"__scheduler_run();")
        self._emit(f"__task_release(__main_task);")
        self._emit("return 0;")
        self.indent_level -= 1
        self._emit("}")
        self._emit("")

    def _emit_task_runtime(self):
        """Mryl Task Runtime (MrylTask 構造体・スケジューラ) を出力する """
        lines = [
            "// ============================================================",
            "// Mryl Task Runtime",
            "// ============================================================",
            "",
            "typedef enum {",
            "    MRYL_TASK_PENDING,",
            "    MRYL_TASK_RUNNING,",
            "    MRYL_TASK_COMPLETED,",
            "    MRYL_TASK_CANCELLED,",
            "    MRYL_TASK_FAULTED",
            "} MrylTaskState;",
            "",
            "typedef struct MrylTask {",
            "    int           strong_count;",
            "    int           weak_count;",
            "    MrylTaskState state;",
            "    void*         result;",
            "    void        (*move_next)(struct MrylTask*);",
            "    void        (*on_cancel)(struct MrylTask*);",
            "    void*         sm;",
            "    struct MrylTask* awaiter;",
            "} MrylTask;",
            "",
            "#define __SCHEDULER_CAP 256",
            "typedef struct {",
            "    MrylTask* queue[__SCHEDULER_CAP];",
            "    int head, tail;",
            "} MrylScheduler;",
            "",
            "static MrylScheduler __scheduler;",
            "",
            "static inline void __scheduler_init(void) {",
            "    __scheduler.head = __scheduler.tail = 0;",
            "}",
            "static inline void __scheduler_post(MrylTask* t) {",
            "    __scheduler.queue[__scheduler.tail++ % __SCHEDULER_CAP] = t;",
            "}",
            "static inline void __scheduler_run(void) {",
            "    while (__scheduler.head != __scheduler.tail) {",
            "        MrylTask* t = __scheduler.queue[__scheduler.head++  % __SCHEDULER_CAP];",
            "        if (t->state != MRYL_TASK_CANCELLED) t->move_next(t);",
            "    }",
            "}",
            "",
            "static inline MrylTask* __task_retain(MrylTask* t) {",
            "    if (t) t->strong_count++;",
            "    return t;",
            "}",
            "static inline void __task_release(MrylTask* t) {",
            "    if (!t) return;",
            "    if (--t->strong_count == 0) {",
            "        if (t->result) { free(t->result); t->result = NULL; }",
            "        if (t->sm)     { free(t->sm);     t->sm     = NULL; }",
            "        if (t->weak_count == 0) free(t);",
            "    }",
            "}",
            "static inline MrylTask* __task_weak_retain(MrylTask* t) {",
            "    if (t) t->weak_count++;",
            "    return t;",
            "}",
            "static inline void __task_weak_release(MrylTask* t) {",
            "    if (!t) return;",
            "    if (--t->weak_count == 0 && t->strong_count == 0) free(t);",
            "}",
            "static inline MrylTask* __task_lock(MrylTask* t) {",
            "    if (!t) return NULL;",
            "    if (t->state == MRYL_TASK_CANCELLED ||",
            "        t->state == MRYL_TASK_COMPLETED) return NULL;",
            "    t->strong_count++;",
            "    return t;",
            "}",
            "static inline void __task_cancel(MrylTask* t) {",
            "    if (!t) return;",
            "    if (t->state == MRYL_TASK_PENDING || t->state == MRYL_TASK_RUNNING) {",
            "        t->state = MRYL_TASK_CANCELLED;",
            "        if (t->on_cancel) t->on_cancel(t);",
            "        if (t->awaiter)  __scheduler_post(t->awaiter);",
            "    }",
            "}",
            "",
        ]
        for line in lines:
            self._emit(line)
