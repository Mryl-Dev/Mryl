"""CodeGenerator package.

ファイル構成:
  _util.py    - CodeGeneratorUtilMixin (_c_escape / _strip_outer_parens / _to_pascal)
                モジュールレベル: _C_KEYWORDS / _safe_c_name()
  _type.py    - CodeGeneratorTypeMixin (_type_to_c / _type_to_c_base / _type_to_fmt_spec /
                _emit_result_typedefs)
  _const.py   - CodeGeneratorConstMixin (_generate_const / _eval_const_expr)
  _struct.py  - CodeGeneratorStructMixin (_generate_struct / _generate_enum /
                _generate_enum_variant_expr / _infer_struct_name)
  _header.py  - CodeGeneratorHeaderMixin (_emit_includes / _emit_builtin_types /
                _collect_vec_elem_types / _emit_vec_helpers / _emit_builtin_functions /
                _emit_header)
  _stmt.py    - CodeGeneratorStmtMixin (_generate_statement / _generate_conditional_block /
                _generate_let / _generate_return / _generate_if / _generate_if_inline /
                _generate_while / _generate_for / _generate_array_element)
  _expr.py    - CodeGeneratorExprMixin (_generate_expr / _generate_expr_with_temps /
                _generate_function_call / _generate_print_call / _generate_struct_init /
                _generate_match_expr / _infer_match_result_c_type /
                _pattern_binding_types / _match_pattern_to_c / _generate_method_call)
  _lambda.py  - CodeGeneratorLambdaMixin (_body_has_await / _collect_captures /
                _generate_lambda / _generate_lambda_inline / _generate_async_lambda)
  _async.py   - CodeGeneratorAsyncMixin (_sm_let_c_type / _split_by_await /
                _generate_async_state_machine / _emit_await_setup / _emit_await_resume /
                _generate_sm_stmt / _emit_task_complete / _emit_task_factory /
                _emit_main_sm_entry / _emit_task_runtime)
  _generic.py - CodeGeneratorGenericMixin (_register_generic_instantiation /
                _substitute_function / _substitute_type_node /
                _get_instantiated_func_name / _infer_generic_type_args /
                _infer_expr_type / _scan_generic_calls /
                _scan_statement_for_generic_calls / _scan_expr_for_generic_calls)
  __init__.py - CodeGenerator (main class: __init__ / generate /
                _emit_pending_lambdas_at / _generate_function / _generate_method /
                _emit / _emit_raw)
"""

import re
from Ast import *  # noqa: F401,F403

from CodeGenerator._util    import CodeGeneratorUtilMixin
from CodeGenerator._type    import CodeGeneratorTypeMixin
from CodeGenerator._const   import CodeGeneratorConstMixin
from CodeGenerator._struct  import CodeGeneratorStructMixin
from CodeGenerator._header  import CodeGeneratorHeaderMixin
from CodeGenerator._stmt    import CodeGeneratorStmtMixin
from CodeGenerator._expr    import CodeGeneratorExprMixin
from CodeGenerator._lambda  import CodeGeneratorLambdaMixin
from CodeGenerator._async   import CodeGeneratorAsyncMixin
from CodeGenerator._generic import CodeGeneratorGenericMixin

class CodeGenerator(
    CodeGeneratorAsyncMixin,
    CodeGeneratorLambdaMixin,
    CodeGeneratorExprMixin,
    CodeGeneratorStmtMixin,
    CodeGeneratorStructMixin,
    CodeGeneratorConstMixin,
    CodeGeneratorHeaderMixin,
    CodeGeneratorTypeMixin,
    CodeGeneratorGenericMixin,
    CodeGeneratorUtilMixin,
):
    """Mryl → C コードジェネレータ """

    def __init__(self):
        self.code                        = []    # 出力 C コードの行リスト
        self.indent_level                = 0     # 現在のインデントレベル
        self.struct_defs                 = {}    # 構造体定義のマップ
        self.function_defs               = []    # 関数定義リスト
        self.structs                     = []    # プログラムの構造体リスト
        self.array_sizes                 = {}    # 変数名 → 配列サイズのマップ
        self.loop_counter                = 0     # ループインデックス変数カウンタ
        self.generic_instantiations      = {}    # ジェネリック実体化キャッシュ
        self.program_functions           = {}    # 関数テーブル: func_name -> FunctionDecl
        self.env                         = [{}]  # 変数スコープスタック
        self.temp_string_counter         = 0     # 一時文字列変数カウンタ
        self.const_table                 = {}    # Const values
        self.lambda_counter              = 0     # ラムダ関数連番カウンタ
        self.pending_lambdas             = []    # (name, ret_type, params_str, body_lines, captures)
        self.pending_async_lambda_blocks = []    # async lambda SM の生 C コード行リスト
        self.async_lambda_factories      = {}    # {var_name: factory_c_name}
        self.sm_mode                     = False # ステートマシン生成モードフラグ
        self.sm_vars                     = set() # SM 内変数名
        self.sm_await_handles            = {}    # await_index -> handle_field_name
        self.capture_map                 = {}    # {var_name: c_expr}
        self.closure_env_types           = {}    # {var_name: lambda_name}
        self.result_type_registry        = set() # set of (ok_c, err_c, struct_name)
        self.current_return_type         = None  # 現在処理中の関数の戻り値型
        self.enums                       = {}    # name -> EnumDecl
        self.ident_renames               = {}    # Mryl変数名 → C 安全変数名

    # ------------------------------------------------------------------
    # メインエントリポイント
    # ------------------------------------------------------------------
    def generate(self, program) -> str:
        """プログラム AST を受け取り、C ソースコード文字列を返す """
        self.code                        = []
        self.structs                     = program.structs
        self.lambda_counter              = 0
        self.pending_lambdas             = []
        self.pending_async_lambda_blocks = []
        self.async_lambda_factories      = {}
        self.loop_counter                = 0
        self.array_sizes                 = {}
        self.vec_var_types               = {}
        self.generic_instantiations      = {}
        self.const_table                 = {}
        self.capture_map                 = {}
        self.closure_env_types           = {}
        self.result_type_registry        = set()
        self.ident_renames               = {}

        # 全関数をキャッシュ
        self.program_functions = {func.name: func for func in program.functions}

        # #include 出力
        self._emit_includes()

        # Task ランタイム出力
        self._emit_task_runtime()

        # const 出力
        if program.consts:
            self._emit("// ============================================================")
            self._emit("// Constants")
            self._emit("// ============================================================")
            self._emit("")
            for const_decl in program.consts:
                self._generate_const(const_decl)
            self._emit("")

        # Built-in 型出力
        self._emit_builtin_types()
        # Result<T,E> typedef プレースホルダー
        self._emit("// __RESULT_TYPEDEFS_PLACEHOLDER__")

        # enum の C 定義を出力
        self.enums = {e.name: e for e in program.enums}
        for enum_decl in program.enums:
            self._generate_enum(enum_decl)

        # 構造体の出力
        for struct in program.structs:
            self._generate_struct(struct)

        # ジェネリック構造体の具体化 typedef を出力 (例: Box_i32, Pair_i32_string)
        generic_uses = self._scan_generic_struct_uses(program)
        for (sname, targs), fields in generic_uses.items():
            mono = f"{sname}_{'_'.join(targs)}"
            self._emit(f"// Generic struct {sname}<{', '.join(targs)}>")
            self._emit("typedef struct {")
            self.indent_level += 1
            for ctype, fname in fields:
                self._emit(f"{ctype} {fname};")
            self.indent_level -= 1
            self._emit(f"}} {mono};")
            self._emit("")

        # Built-in 関数の出力
        self._emit_builtin_functions()

        # 動的配列ヘルパー
        used_vec_types = self._collect_vec_elem_types(program)
        if used_vec_types:
            self._emit_vec_helpers(used_vec_types)

        # 構造体メソッドの出力
        for struct in program.structs:
            if struct.methods:
                self._emit("")
                self._emit(f"// Methods for {struct.name}")
                for method in struct.methods:
                    self._generate_method(struct.name, method)

        # Phase 1: ジェネリック呼び出しのスキャン
        for func in program.functions:
            self._scan_generic_calls(func.body)

        # Phase 2: 単相化関数の前方宣言
        if self.generic_instantiations:
            self._emit("// Forward declarations of monomorphized functions")
            for (_fn, _ta), inst_func in self.generic_instantiations.items():
                ret_t  = self._type_to_c(inst_func.return_type) if inst_func.return_type else "void"
                params = ", ".join(
                    f"{self._type_to_c(p.type_node)} {p.name}"
                    for p in inst_func.params
                )
                self._emit(f"{ret_t} {inst_func.name}({params});")
            self._emit("")

        # Phase 3: 非ジェネリック関数の定義
        for func in program.functions:
            if not func.type_params:
                self._generate_function(func)

        # Phase 4: 単相化ジェネリック関数の定義
        if self.generic_instantiations:
            self._emit("// ===== Monomorphized Generic Functions =====")
            for (func_name, type_args_tuple), inst_func in self.generic_instantiations.items():
                self._emit(f"// Generic instantiation: {func_name}{type_args_tuple}")
                self._generate_function(inst_func)

        # Phase 5: pending lambda の挿入
        if self.pending_lambdas or self.pending_async_lambda_blocks:
            lambda_lines = []
            if self.pending_async_lambda_blocks:
                lambda_lines.append("// ===== Async Lambda state machines =====")
                for block_lines in self.pending_async_lambda_blocks:
                    lambda_lines.extend(block_lines)
                self.pending_async_lambda_blocks = []
            if self.pending_lambdas:
                lambda_lines.append("// ===== Lambda static helper functions =====")
            for (lam_name, ret_type, params_str, body_lines, captures) in self.pending_lambdas:
                if captures:
                    env_struct   = f"{lam_name}_env_t"
                    lambda_lines.append(f"typedef struct {{")
                    for cap_name, cap_c_type in captures.items():
                        lambda_lines.append(f"    {cap_c_type} {cap_name};")
                    lambda_lines.append(f"}} {env_struct};")
                    lambda_lines.append(
                        f"typedef struct {{ {ret_type} (*fn)({params_str}, {env_struct}*); "
                        f"{env_struct} env; }} {lam_name}_closure_t;"
                    )
                    full_params = (
                        f"{params_str}, {env_struct}* __env" if params_str else f"{env_struct}* __env"
                    )
                    lambda_lines.append(f"static {ret_type} {lam_name}({full_params}) {{")
                else:
                    lambda_lines.append(f"static {ret_type} {lam_name}({params_str}) {{")
                lambda_lines.extend(body_lines)
                lambda_lines.append("}")
                lambda_lines.append("")
            self.pending_lambdas = []

            func_pattern = re.compile(
                r'^(?:int|void|int32_t|int64_t|float|double|uint\w+|MrylString)\s+\w+\s*\('
            )
            insert_at = len(self.code)
            for i, line in enumerate(self.code):
                if func_pattern.match(line.lstrip()):
                    insert_at = i
                    break

            for j, line in enumerate(lambda_lines):
                self.code.insert(insert_at + j, line)

        # Result<T,E> typedef を差し込む
        if self.result_type_registry:
            result_lines = ["// ===== Result<T,E> type structs ====="]
            for (ok_c, err_c, struct_name) in sorted(self.result_type_registry):
                result_lines.append(f"typedef struct {{")
                result_lines.append(f"    int is_ok;")
                result_lines.append(f"    union {{ {ok_c} ok_val; {err_c} err_val; }} data;")
                result_lines.append(f"}} {struct_name};")
            result_lines.append("")
            for i, line in enumerate(self.code):
                if "// __RESULT_TYPEDEFS_PLACEHOLDER__" in line:
                    self.code[i:i + 1] = result_lines
                    break
        else:
            self.code = [l for l in self.code if "// __RESULT_TYPEDEFS_PLACEHOLDER__" not in l]

        return '\n'.join(self.code)

    # ------------------------------------------------------------------
    # ヘルパー: lambda / pending lambda 挿入
    # ------------------------------------------------------------------
    def _emit_pending_lambdas_at(self, insert_pos: int):
        """pending_lambdas / pending_async_lambda_blocks を insert_pos に挿入する。"""
        if not self.pending_lambdas and not self.pending_async_lambda_blocks:
            return
        lambda_lines = []
        if self.pending_async_lambda_blocks:
            lambda_lines.append("// ===== Async Lambda state machines =====")
            for block_lines in self.pending_async_lambda_blocks:
                lambda_lines.extend(block_lines)
            self.pending_async_lambda_blocks = []
        if not self.pending_lambdas:
            for i, ln in enumerate(lambda_lines):
                self.code.insert(insert_pos + i, ln)
            return
        for (lam_name, ret_type, params_str, body_lines, captures) in self.pending_lambdas:
            if captures:
                env_struct = f"{lam_name}_env_t"
                lambda_lines.append(f"typedef struct {{")
                for cap_name, cap_c_type in captures.items():
                    lambda_lines.append(f"    {cap_c_type} {cap_name};")
                lambda_lines.append(f"}} {env_struct};")
                lambda_lines.append(
                    f"typedef struct {{ {ret_type} (*fn)({params_str}, {env_struct}*); "
                    f"{env_struct} env; }} {lam_name}_closure_t;"
                )
                full_params = (
                    f"{params_str}, {env_struct}* __env" if params_str else f"{env_struct}* __env"
                )
                lambda_lines.append(f"static {ret_type} {lam_name}({full_params}) {{")
            else:
                lambda_lines.append(f"static {ret_type} {lam_name}({params_str}) {{")
            lambda_lines.extend(body_lines)
            lambda_lines.append("}")
            lambda_lines.append("")
        for i, ln in enumerate(lambda_lines):
            self.code.insert(insert_pos + i, ln)
        self.pending_lambdas = []

    # ------------------------------------------------------------------
    # 関数・メソッド生成
    # ------------------------------------------------------------------
    def _generate_function(self, func):
        """関数宣言から C コードを生成する。"""
        self.env.append({})
        self.local_string_vars   = []
        self.temp_string_counter = 0
        saved_renames            = self.ident_renames.copy()
        self.ident_renames       = {}

        if getattr(func, 'is_async', False) or self._body_has_await(func.body):
            func_insert_pos = len(self.code)
            self._generate_async_state_machine(func)
            self.env.pop()
            self.ident_renames = saved_renames
            self._emit_pending_lambdas_at(func_insert_pos)
            return

        func_insert_pos = len(self.code)

        for param in func.params:
            self.env[-1][param.name] = param.type_node.name

        if func.name == "main":
            return_type              = "int"
            self.current_return_type = None
        else:
            return_type = self._type_to_c(func.return_type) if func.return_type else "void"
            if func.return_type and func.return_type.name == "Result":
                self.current_return_type = return_type
            else:
                self.current_return_type = None

        params = []
        for param in func.params:
            param_type = self._type_to_c(param.type_node)
            params.append(f"{param_type} {param.name}")

        params_str = ", ".join(params) if params else "void"

        self._emit(f"{return_type} {func.name}({params_str}) {{")
        self.indent_level += 1

        has_return = False
        if func.body:
            for stmt in func.body.statements:
                self._generate_statement(stmt)
                if stmt.__class__.__name__ == "ReturnStmt":
                    has_return = True

        # has_return=True の場合は _generate_return 内で cleanup 済みのため
        # ここで再度 free を emit すると return の後ろにデッドコードが並ぶ。
        if not has_return:
            for var_name in self.local_string_vars:
                self._emit(f"free_mryl_string({var_name});")

        if not has_return:
            if func.name == "main":
                self._emit("return 0;")
            elif func.return_type and func.return_type.name not in ["void"]:
                self._emit("return 0;")
            else:
                self._emit("return;")

        self.indent_level -= 1
        self._emit("}")
        self._emit("")

        self._emit_pending_lambdas_at(func_insert_pos)

        self.env.pop()
        self.ident_renames = saved_renames

    def _generate_method(self, struct_name: str, method):
        """構造体メソッドから C コードを生成する。"""
        func_name   = f"{struct_name}_{method.name}"
        return_type = self._type_to_c(method.return_type)

        if method.params and method.params[0].name == "self":
            self_type    = struct_name
            other_params = method.params[1:]
            param_strs   = [f"{self_type} self"]
            param_strs.extend(f"{self._type_to_c(p.type_node)} {p.name}" for p in other_params)
        else:
            self_type    = None
            other_params = method.params
            param_strs = [f"{self._type_to_c(p.type_node)} {p.name}" for p in method.params]

        params_str = ", ".join(param_strs)

        self._emit(f"{return_type} {func_name}({params_str}) {{")
        self.indent_level += 1

        # _generate_return 内の cleanup が参照するためメソッド開始時に初期化する
        saved_str_vars           = getattr(self, 'local_string_vars', [])
        saved_temp_ctr           = getattr(self, 'temp_string_counter', 0)
        self.local_string_vars   = []
        self.temp_string_counter = 0

        # env に self と引数を登録（_infer_expr_type が struct フィールド型を解決できるようにする）
        method_env: dict = {}
        if self_type:
            method_env["self"] = self_type
        for p in other_params:
            method_env[p.name] = p.type_node.name
        self.env.append(method_env)

        has_return = False
        for stmt in method.body.statements:
            self._generate_statement(stmt)
            if stmt.__class__.__name__ == "ReturnStmt":
                has_return = True

        self.env.pop()

        # has_return=False の場合のみここで cleanup（True の場合は _generate_return 内で処理済み）
        if not has_return:
            for var_name in self.local_string_vars:
                self._emit(f"free_mryl_string({var_name});")

        # 復元
        self.local_string_vars   = saved_str_vars
        self.temp_string_counter = saved_temp_ctr

        self.indent_level -= 1
        self._emit("}")
        self._emit("")

    # ------------------------------------------------------------------
    # 低レベル出力ユーティリティ
    # ------------------------------------------------------------------
    def _emit(self, line: str = ""):
        """インデントを付けて1行出力する。"""
        if line:
            self.code.append("    " * self.indent_level + line)
        else:
            self.code.append("")

    def _emit_raw(self, text: str):
        """直前の行末にテキストを追記する。"""
        if self.code:
            self.code[-1] = self.code[-1].rstrip() + text
        else:
            self.code.append(text)
