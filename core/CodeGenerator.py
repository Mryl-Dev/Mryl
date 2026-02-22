from Ast import *

# C言語予約語 (Mint変数名と衝突する可能性がある)
_C_KEYWORDS = {
    'auto','break','case','char','const','continue','default','do','double',
    'else','enum','extern','float','for','goto','if','inline','int','long',
    'register','restrict','return','short','signed','sizeof','static','struct',
    'switch','typedef','union','unsigned','void','volatile','while',
    '_Bool','_Complex','_Imaginary',
}

def _safe_c_name(name: str) -> str:
    """C予約語と衝突する Mryl 変数名を安全な名前に変換する"""
    return f'_mryl_{name}' if name in _C_KEYWORDS else name


class CodeGenerator:
    """(Implementation detail)"""
    
    def __init__(self):
        self.code = []                      # 出力 C コードの行リスト
        self.indent_level = 0               # 現在のインデントレベル
        self.struct_defs = {}               # 構造体定義のマップ
        self.function_defs = []             # 関数定義リスト
        self.structs = []                   # プログラムの構造体リスト
        self.array_sizes = {}               # 変数名 → 配列サイズのマップ {var_name: size}
        self.loop_counter = 0               # ループインデックス変数カウンタ
        self.generic_instantiations = {}    # ジェネリック実体化: (func_name, type_args_tuple) -> FunctionDecl
        self.program_functions = {}         # プログラム関数テーブル: func_name -> FunctionDecl
        self.env = [{}]                     # 変数スコープスタック (辞書のリスト)
        self.temp_string_counter = 0        # 一時文字列変数カウンタ
        self.const_table = {}               # Const values for code generation
        self.lambda_counter = 0             # ラムダ関数の連番カウンタ
        self.pending_lambdas = []           # List of (name, ret_type, params_str, body_lines, captures)
        self.sm_mode = False                # ステートマシン生成モードのフラグ
        self.sm_vars = set()                # SM 内変数名のセット
        self.sm_await_handles = {}          # await_index -> handle_field_name (inline FunctionCall await 用)
        self.capture_map = {}               # {var_name: c_expr} クロージャキャプチャ
        self.closure_env_types = {}         # {var_name: lambda_name} クロージャ環境型のマップ
        self.result_type_registry = set()   # set of (ok_c, err_c, struct_name)
        self.current_return_type = None     # 現在処理中の関数の戻り値型
        self.enums = {}                     # name -> EnumDecl (enum 宣言のマップ)
        self.ident_renames = {}             # Mint変数名 → C 安全変数名 (C予約語回避)
        
    def generate(self, program) -> str:
        """(Implementation detail)"""
        self.code = []
        self.structs = program.structs      # 構造体リストをキャッシュ
        self.lambda_counter = 0             # ラムダ連番カウンタをリセット
        self.pending_lambdas = []           # List of (name, ret_type, params_str, body_lines, captures)
        self.loop_counter = 0               # ループカウンタをリセット
        self.array_sizes = {}               # 変数名 → 配列サイズのマップ
        self.vec_var_types = {}             # 変数名 → 動的配列の要素型名 (e.g. "i32")
        self.generic_instantiations = {}    # ジェネリック関数の実体化キャッシュ
        self.const_table = {}               # Const values テーブル
        self.capture_map = {}               # クロージャ変数キャプチャのマッピング
        self.closure_env_types = {}         # クロージャ変数 → ラムダ名のマップ
        self.result_type_registry = set()   # Result<T,E> 型の実体化レジストリ
        self.ident_renames = {}             # Mint変数名 → C 安全変数名 (C予約語回避)
        
        # プログラム内の全関数をキャッシュ
        self.program_functions = {func.name: func for func in program.functions}
        
        # #include の出力
        self._emit_includes()

        # Task ランタイムの出力
        self._emit_task_runtime()

        # const の出力 (#include の後、built-in の前)
        if program.consts:
            self._emit("// ============================================================")
            self._emit("// Constants")
            self._emit("// ============================================================")
            self._emit("")
            for const_decl in program.consts:
                self._generate_const(const_decl)
            self._emit("")
        
        # Built-in 型の出力
        self._emit_builtin_types()
        # Result<T,E> typedef 出力用プレースホルダー (後で差し込む)
        self._emit("// __RESULT_TYPEDEFS_PLACEHOLDER__")

        # enum の C 定義を出力
        self.enums = {e.name: e for e in program.enums}
        for enum_decl in program.enums:
            self._generate_enum(enum_decl)

        # 全構造体を built-in の後に出力
        for struct in program.structs:
            self._generate_struct(struct)

        # Built-in 関数の出力
        self._emit_builtin_functions()

        # 動的配列ヘルパー (MrylVec_<T>) の出力
        used_vec_types = self._collect_vec_elem_types(program)
        if used_vec_types:
            self._emit_vec_helpers(used_vec_types)

        # 各構造体のメソッド (impl ブロック相当)
        for struct in program.structs:
            if struct.methods:
                self._emit("")
                self._emit(f"// Methods for {struct.name}")
                for method in struct.methods:
                    self._generate_method(struct.name, method)
        
        # Phase 1: Pre-scan all function bodies for generic calls
        for func in program.functions:
            self._scan_generic_calls(func.body)
        
        # Phase 2: Emit forward declarations for monomorphized functions
        if self.generic_instantiations:
            self._emit("// Forward declarations of monomorphized functions")
            for (func_name, type_args_tuple), instantiated_func in self.generic_instantiations.items():
                return_type = self._type_to_c(instantiated_func.return_type) if instantiated_func.return_type else "void"
                params = ", ".join(
                    f"{self._type_to_c(p.type_node)} {p.name}"
                    for p in instantiated_func.params
                )
                self._emit(f"{return_type} {instantiated_func.name}({params});")
            self._emit("")
        
        # Phase 3: Generate all function definitions (non-generic and monomorphized)
        for func in program.functions:
            if not func.type_params:  # Non-generic functions only
                self._generate_function(func)
        
        # Phase 4: Generate monomorphized generic functions
        if self.generic_instantiations:
            self._emit("// ===== Monomorphized Generic Functions =====")
            for (func_name, type_args_tuple), instantiated_func in self.generic_instantiations.items():
                self._emit(f"// Generic instantiation: {func_name}{type_args_tuple}")
                self._generate_function(instantiated_func)

        # Phase 5: Insert pending lambda static functions before any function that uses them.
        # Find the first function definition line and insert lambdas just before it.
        if self.pending_lambdas:
            lambda_lines = []
            lambda_lines.append("// ===== Lambda static helper functions =====")
            for (lam_name, ret_type, params_str, body_lines, captures) in self.pending_lambdas:
                if captures:
                    # クロージャ: env 構造体と closure_t 型を出力
                    env_struct = f"{lam_name}_env_t"
                    lambda_lines.append(f"typedef struct {{")
                    for cap_name, cap_c_type in captures.items():
                        lambda_lines.append(f"    {cap_c_type} {cap_name};")
                    lambda_lines.append(f"}} {env_struct};")
                    lambda_lines.append(f"typedef struct {{ {ret_type} (*fn)({params_str}, {env_struct}*); {env_struct} env; }} {lam_name}_closure_t;")
                    full_params = f"{params_str}, {env_struct}* __env" if params_str else f"{env_struct}* __env"
                    lambda_lines.append(f"static {ret_type} {lam_name}({full_params}) {{")
                else:
                    lambda_lines.append(f"static {ret_type} {lam_name}({params_str}) {{")
                lambda_lines.extend(body_lines)
                lambda_lines.append("}")
                lambda_lines.append("")
            self.pending_lambdas = []

            # Find insertion point: first line starting with a C type followed by a function name
            # We look for the first non-comment, non-preprocessor line that looks like a function def
            import re
            insert_at = len(self.code)
            func_pattern = re.compile(r'^(?:int|void|int32_t|int64_t|float|double|uint\w+|MrylString)\s+\w+\s*\(')
            for i, line in enumerate(self.code):
                if func_pattern.match(line.lstrip()):
                    insert_at = i
                    break

            # Insert lambda definitions before the first function
            for j, line in enumerate(lambda_lines):
                self.code.insert(insert_at + j, line)

        # Result<T,E> typedef を差し込む: プレースホルダー行を型定義で置換
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
                    self.code[i:i+1] = result_lines
                    break
        else:
            # プレースホルダー行を削除
            self.code = [l for l in self.code if "// __RESULT_TYPEDEFS_PLACEHOLDER__" not in l]

        return '\n'.join(self.code)
    
    def _generate_const(self, const_decl: ConstDecl):
        """Generate #define directive for const declaration"""
        # Evaluate the const expression and generate #define
        try:
            value = self._eval_const_expr(const_decl.init_expr)
            self._emit(f"#define {const_decl.name} {value}")
            self.const_table[const_decl.name] = value
        except Exception as e:
            # If evaluation fails, just comment it out
            error_msg = str(e).replace('"', "'")
            self._emit(f"// #define {const_decl.name} (error: {error_msg})")
    
    def _eval_const_expr(self, expr):
        """Evaluate const expression at code generation time"""
        if isinstance(expr, NumberLiteral):
            return expr.value
        elif isinstance(expr, StringLiteral):
            return f'"{expr.value}"'
        elif isinstance(expr, BoolLiteral):
            return "1" if expr.value else "0"
        elif hasattr(expr, '__class__') and expr.__class__.__name__ == 'VarRef':
            # VarRef: identifier reference (might be a const)
            if hasattr(expr, 'name') and expr.name in self.const_table:
                return self.const_table[expr.name]
            else:
                raise ValueError(f"Undefined const: {expr.name if hasattr(expr, 'name') else expr}")
        elif hasattr(expr, '__class__') and expr.__class__.__name__ == 'Identifier':
            # Identifier
            if hasattr(expr, 'name') and expr.name in self.const_table:
                return self.const_table[expr.name]
            else:
                raise ValueError(f"Undefined const: {expr.name if hasattr(expr, 'name') else expr}")
        elif hasattr(expr, '__class__') and expr.__class__.__name__ == 'UnaryOp':
            operand_val = self._eval_const_expr(expr.operand)
            if expr.op == '-':
                return -operand_val
            elif expr.op == '+':
                return operand_val
            elif expr.op == '!':
                return 0 if operand_val else 1
            elif expr.op == '~':
                return ~operand_val
            else:
                raise ValueError(f"Unsupported unary operator in const expression: {expr.op}")
        elif isinstance(expr, BinaryOp):
            left_val = self._eval_const_expr(expr.left)
            right_val = self._eval_const_expr(expr.right)
            
            # Handle string operations
            if isinstance(left_val, str) or isinstance(right_val, str):
                if expr.op == '+':
                    # String concatenation
                    return f'({left_val} {right_val})'
                else:
                    raise ValueError(f"Unsupported operator on strings: {expr.op}")
            
            # Numeric operations
            if expr.op == '+':
                return left_val + right_val
            elif expr.op == '-':
                return left_val - right_val
            elif expr.op == '*':
                return left_val * right_val
            elif expr.op == '/':
                if right_val == 0:
                    raise ValueError("Division by zero in const expression")
                return left_val // right_val if isinstance(left_val, int) else left_val / right_val
            elif expr.op == '%':
                return left_val % right_val
            elif expr.op == '==':
                return 1 if left_val == right_val else 0
            elif expr.op == '!=':
                return 1 if left_val != right_val else 0
            elif expr.op == '<':
                return 1 if left_val < right_val else 0
            elif expr.op == '>':
                return 1 if left_val > right_val else 0
            elif expr.op == '<=':
                return 1 if left_val <= right_val else 0
            elif expr.op == '>=':
                return 1 if left_val >= right_val else 0
            elif expr.op == '&&':
                return 1 if left_val and right_val else 0
            elif expr.op == '||':
                return 1 if left_val or right_val else 0
            elif expr.op == '&':
                return left_val & right_val
            elif expr.op == '|':
                return left_val | right_val
            elif expr.op == '^':
                return left_val ^ right_val
            elif expr.op == '<<':
                return left_val << right_val
            elif expr.op == '>>':
                return left_val >> right_val
            else:
                raise ValueError(f"Unsupported operator in const expression: {expr.op}")
        else:
            raise ValueError(f"Cannot evaluate expression type in const context: {type(expr)}")
    
    def _emit_includes(self):
        """Emit #include directives for C file"""
        self._emit("#include <stdio.h>")
        self._emit("#include <stdlib.h>")
        self._emit("#include <string.h>")
        self._emit("#include <stdint.h>")
        self._emit("#include <stdarg.h>")
        self._emit("#include <time.h>")
        self._emit("#include <regex.h>")
        self._emit("")

    def _emit_builtin_types(self):
        """Emit built-in type definitions for C file"""
        self._emit("// ============================================================")
        self._emit("// Built-in types and structures")
        self._emit("// ============================================================")
        self._emit("")
        self._emit("typedef struct {")
        self.indent_level += 1
        self._emit("char* data;")
        self._emit("int length;")
        self.indent_level -= 1
        self._emit("} MrylString;")
        self._emit("")

    def _collect_vec_elem_types(self, program) -> set:
        """Walk AST top-level and collect element type names of dynamic arrays (array_size == -1)."""
        types = set()
        def walk_type(t):
            if t and getattr(t, 'array_size', None) == -1:
                types.add(t.name)
        def walk_stmt(s):
            if s is None: return
            cls = s.__class__.__name__
            if cls == 'LetDecl':
                walk_type(s.type_node)
            elif cls == 'Block':
                for st in s.statements: walk_stmt(st)
            elif cls == 'IfStmt':
                walk_stmt(s.then_block)
                if s.else_block: walk_stmt(s.else_block)
            elif cls in ('WhileStmt',):
                walk_stmt(s.body)
            elif cls == 'ForStmt':
                walk_stmt(s.body)
        for func in program.functions:
            for p in func.params:
                walk_type(getattr(p, 'type_node', None))
            if func.body: walk_stmt(func.body)
        return types

    def _emit_vec_helpers(self, elem_types: set):
        """Emit MrylVec_<T> struct + helper functions for each used element type."""
        _c_map = {
            "i8": "int8_t", "i16": "int16_t", "i32": "int32_t", "i64": "int64_t",
            "u8": "uint8_t", "u16": "uint16_t", "u32": "uint32_t", "u64": "uint64_t",
            "f32": "float", "f64": "double", "bool": "int",
        }
        self._emit("// ============================================================")
        self._emit("// Dynamic array (MrylVec_<T>) types and helpers")
        self._emit("// ============================================================")
        self._emit("")
        for et in sorted(elem_types):
            ct = _c_map.get(et, "int32_t")
            T = et  # e.g. "i32"
            C = ct  # e.g. "int32_t"
            self._emit(f"typedef struct {{ {C}* data; int32_t len; int32_t cap; }} MrylVec_{T};")
            self._emit(f"static inline MrylVec_{T} mryl_vec_{T}_new(void) {{")
            self._emit(f"    MrylVec_{T} v; v.data = NULL; v.len = 0; v.cap = 0; return v;")
            self._emit(f"}}")
            self._emit(f"static inline MrylVec_{T} mryl_vec_{T}_from({C}* elems, int32_t n) {{")
            self._emit(f"    MrylVec_{T} v; v.len = n; v.cap = n;")
            self._emit(f"    v.data = ({C}*)malloc(sizeof({C}) * n);")
            self._emit(f"    for (int32_t i = 0; i < n; i++) v.data[i] = elems[i];")
            self._emit(f"    return v;")
            self._emit(f"}}")
            self._emit(f"static inline void mryl_vec_{T}_push(MrylVec_{T}* v, {C} val) {{")
            self._emit(f"    if (v->len == v->cap) {{")
            self._emit(f"        v->cap = v->cap ? v->cap * 2 : 4;")
            self._emit(f"        v->data = ({C}*)realloc(v->data, sizeof({C}) * v->cap);")
            self._emit(f"    }}")
            self._emit(f"    v->data[v->len++] = val;")
            self._emit(f"}}")
            self._emit(f"static inline {C} mryl_vec_{T}_pop(MrylVec_{T}* v) {{")
            self._emit(f"    return v->data[--v->len];")
            self._emit(f"}}")
            self._emit(f"static inline void mryl_vec_{T}_remove(MrylVec_{T}* v, int32_t idx) {{")
            self._emit(f"    for (int32_t i = idx; i < v->len - 1; i++) v->data[i] = v->data[i+1];")
            self._emit(f"    v->len--;")
            self._emit(f"}}")
            self._emit(f"static inline void mryl_vec_{T}_insert(MrylVec_{T}* v, int32_t idx, {C} val) {{")
            self._emit(f"    if (v->len == v->cap) {{")
            self._emit(f"        v->cap = v->cap ? v->cap * 2 : 4;")
            self._emit(f"        v->data = ({C}*)realloc(v->data, sizeof({C}) * v->cap);")
            self._emit(f"    }}")
            self._emit(f"    for (int32_t i = v->len; i > idx; i--) v->data[i] = v->data[i-1];")
            self._emit(f"    v->data[idx] = val;")
            self._emit(f"    v->len++;")
            self._emit(f"}}")
            self._emit(f"")

    def _emit_builtin_functions(self):
        """(Implementation detail)"""
        self._emit("// ============================================================")
        self._emit("// Built-in functions")
        self._emit("// ============================================================")
        self._emit("")
        # ---- mryl_panic: structured fatal-error reporter ----
        self._emit("static void mryl_panic(")
        self._emit("        const char* error_type, const char* message,")
        self._emit("        const char* func, const char* file, int line) {")
        self.indent_level += 1
        self._emit("time_t __now = time(NULL);")
        self._emit("struct tm* __tm = localtime(&__now);")
        self._emit("char __timebuf[24];")
        self._emit("strftime(__timebuf, sizeof(__timebuf), \"%Y-%m-%d %H:%M:%S\", __tm);")
        self._emit("// Brief one-liner to stdout")
        self._emit("printf(\"[FATAL] %s: %s\\n  See stderr for full error report.\\n\", error_type, message);")
        self._emit("// Detailed report to stderr")
        self._emit("fprintf(stderr, \"[%s] ERROR %s: %s\\n\", __timebuf, error_type, message);")
        self._emit("fprintf(stderr, \"  function: %s\\n\", func);")
        self._emit("fprintf(stderr, \"  file: %s\\n\", file);")
        self._emit("fprintf(stderr, \"  line: %d\\n\", line);")
        self._emit("fprintf(stderr, \"\\nStacktrace:\\n\");")
        self._emit("fprintf(stderr, \"  %s(%s:%d)\\n\", func, file, line);")
        self._emit("exit(1);")
        self.indent_level -= 1
        self._emit("}")
        self._emit("")
        self._emit("void print(const char* fmt, ...) {")
        self.indent_level += 1
        self._emit("va_list args;")
        self._emit("va_start(args, fmt);")
        self._emit("vprintf(fmt, args);")
        self._emit("va_end(args);")
        self.indent_level -= 1
        self._emit("}")
        self._emit("")
        self._emit("void println(const char* fmt, ...) {")
        self.indent_level += 1
        self._emit("va_list args;")
        self._emit("va_start(args, fmt);")
        self._emit("vprintf(fmt, args);")
        self._emit("va_end(args);")
        self._emit("printf(\"\\n\");")
        self.indent_level -= 1
        self._emit("}")
        self._emit("")        
        # MrylString ヘルパー関数
        self._emit("// MrylString helper functions")
        self._emit("MrylString make_mryl_string(const char* str) {")
        self.indent_level += 1
        self._emit("MrylString s;")
        self._emit("s.data = (char*)malloc(strlen(str) + 1);")
        self._emit("strcpy(s.data, str);")
        self._emit("s.length = strlen(str);")
        self._emit("return s;")
        self.indent_level -= 1
        self._emit("}")
        self._emit("")
        self._emit("void free_mryl_string(MrylString s) {")
        self.indent_level += 1
        self._emit("if (s.data != NULL) {")
        self.indent_level += 1
        self._emit("free(s.data);")
        self.indent_level -= 1
        self._emit("}")
        self.indent_level -= 1
        self._emit("}")
        self._emit("")
        self._emit("MrylString mryl_string_concat(MrylString a, MrylString b) {")
        self.indent_level += 1
        self._emit("int new_length = a.length + b.length;")
        self._emit("MrylString result;")
        self._emit("result.data = (char*)malloc(new_length + 1);")
        self._emit("strcpy(result.data, a.data);")
        self._emit("strcat(result.data, b.data);")
        self._emit("result.length = new_length;")
        self._emit("return result;")
        self.indent_level -= 1
        self._emit("}")
        self._emit("")
        self._emit("MrylString to_string(int32_t n) {")
        self.indent_level += 1
        self._emit("char buf[32];")
        self._emit("snprintf(buf, sizeof(buf), \"%d\", n);")
        self._emit("return make_mryl_string(buf);")
        self.indent_level -= 1
        self._emit("}")
        self._emit("")

    def _emit_header(self):
        """(Implementation detail)"""
        self._emit_builtin_types()
        self._emit_builtin_functions()

    def _generate_struct(self, struct):
        """(Implementation detail)"""
        self._emit(f"// Struct: {struct.name}")
        self._emit(f"typedef struct {{")
        self.indent_level += 1
        
        for field in struct.fields:
            field_type = self._type_to_c(field.type_node)
            self._emit(f"{field_type} {field.name};")
        
        self.indent_level -= 1
        self._emit(f"}} {struct.name};")
        self._emit("")

    def _generate_enum(self, enum_decl):
        """Generate C code for an enum declaration.
        
        - Simple enum (no variant has data): typedef enum { Name_A, Name_B } Name;
        - Data-carrying enum: tagged union with constructor functions.
        """
        name = enum_decl.name
        variants = enum_decl.variants
        has_data = any(v.fields for v in variants)

        self._emit(f"// Enum: {name}")

        if not has_data:
            # Simple C enum
            constants = ", ".join(f"{name}_{v.name}" for v in variants)
            self._emit(f"typedef enum {{ {constants} }} {name};")
            self._emit("")
            return

        # --- Data-carrying enum: tagged union ---
        # 1. Tag enum
        tag_entries = ", ".join(f"{name}_Tag_{v.name}" for v in variants)
        self._emit(f"typedef enum {{ {tag_entries} }} {name}_Tag;")

        # 2. Outer struct with tag + union
        self._emit(f"typedef struct {{")
        self.indent_level += 1
        self._emit(f"{name}_Tag tag;")
        data_variants = [v for v in variants if v.fields]
        if data_variants:
            self._emit("union {")
            self.indent_level += 1
            for v in data_variants:
                self._emit("struct {")
                self.indent_level += 1
                for i, field_type_node in enumerate(v.fields):
                    c_type = self._type_to_c(field_type_node)
                    self._emit(f"{c_type} _{i};")
                self.indent_level -= 1
                self._emit(f"}} {v.name};")
            self.indent_level -= 1
            self._emit("} data;")
        self.indent_level -= 1
        self._emit(f"}} {name};")
        self._emit("")

        # 3. Constructor functions (static inline)
        for v in variants:
            params_list = [
                f"{self._type_to_c(ft)} _{i}" for i, ft in enumerate(v.fields)
            ]
            params_str = ", ".join(params_list) if params_list else "void"
            self._emit(f"static inline {name} {name}_{v.name}({params_str}) {{")
            self.indent_level += 1
            self._emit(f"{name} __v;")
            self._emit(f"__v.tag = {name}_Tag_{v.name};")
            for i in range(len(v.fields)):
                self._emit(f"__v.data.{v.name}._{i} = _{i};")
            self._emit("return __v;")
            self.indent_level -= 1
            self._emit("}")
            self._emit("")

    def _emit_pending_lambdas_at(self, insert_pos):
        """pending_lambdas を insert_pos に挿入して pending を空にする"""
        if not self.pending_lambdas:
            return
        lambda_lines = []
        for (lam_name, ret_type, params_str, body_lines, captures) in self.pending_lambdas:
            if captures:
                env_struct = f"{lam_name}_env_t"
                lambda_lines.append(f"typedef struct {{")  
                for cap_name, cap_c_type in captures.items():
                    lambda_lines.append(f"    {cap_c_type} {cap_name};")
                lambda_lines.append(f"}} {env_struct};")
                lambda_lines.append(f"typedef struct {{ {ret_type} (*fn)({params_str}, {env_struct}*); {env_struct} env; }} {lam_name}_closure_t;")
                full_params = f"{params_str}, {env_struct}* __env" if params_str else f"{env_struct}* __env"
                lambda_lines.append(f"static {ret_type} {lam_name}({full_params}) {{")
            else:
                lambda_lines.append(f"static {ret_type} {lam_name}({params_str}) {{")
            lambda_lines.extend(body_lines)
            lambda_lines.append("}")
            lambda_lines.append("")
        for i, ln in enumerate(lambda_lines):
            self.code.insert(insert_pos + i, ln)
        self.pending_lambdas = []

    def _generate_function(self, func):
        """(Implementation detail)"""
        # スコープを開く
        self.env.append({})
        self.local_string_vars = []  # 関数内で宣言した MrylString 変数リスト
        self.temp_string_counter = 0  # 一時変数カウンタ
        # ident_renames を関数スコープでリセット(ネストしない前提)
        saved_renames = self.ident_renames.copy()
        self.ident_renames = {}

        # async fn または body に await を含む fn はステートマシン生成へ
        if getattr(func, 'is_async', False) or self._body_has_await(func.body):
            self._generate_async_state_machine(func)
            self.env.pop()
            self.ident_renames = saved_renames
            return

        # ラムダ挿入位置を記録（この関数定義の直前）
        func_insert_pos = len(self.code)

        # パラメータをスコープに登録
        for param in func.params:
            self.env[-1][param.name] = param.type_node.name
            # 注意: string 型パラメータは関数終了時の free は不要 (呼び出し元が管理)
        
        # main 関数の場合は戻り値型を int に固定
        if func.name == "main":
            return_type = "int"
            self.current_return_type = None
        else:
            return_type = self._type_to_c(func.return_type) if func.return_type else "void"
            # Result<T,E> 戻り値の場合: struct 名を current_return_type に保存
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
        
        # 関数本体の生成
        has_return = False
        if func.body:
            for stmt in func.body.statements:
                self._generate_statement(stmt)
                # return 文が含まれていれば記録
                if stmt.__class__.__name__ == "ReturnStmt":
                    has_return = True
        
        # ローカル MrylString 変数のメモリ解放
        for var_name in self.local_string_vars:
            self._emit(f"free_mryl_string({var_name});")
        
        # 明示的な return がない場合はデフォルトの return を追加
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

        # 本関数内で蓄積されたラムダを関数定義の直前に挿入
        self._emit_pending_lambdas_at(func_insert_pos)

        # スコープを閉じる
        self.env.pop()
        self.ident_renames = saved_renames
    
    def _generate_statement(self, stmt):
        """(Implementation detail)"""
        stmt_class = stmt.__class__.__name__
        
        if stmt_class == "LetDecl":
            self._generate_let(stmt)
        elif stmt_class == "ReturnStmt":
            self._generate_return(stmt)
        elif stmt_class == "BreakStmt":
            self._emit("break;")
        elif stmt_class == "ContinueStmt":
            self._emit("continue;")
        elif stmt_class == "IfStmt":
            self._generate_if(stmt)
        elif stmt_class == "WhileStmt":
            self._generate_while(stmt)
        elif stmt_class == "ForStmt":
            self._generate_for(stmt)
        elif stmt_class == "ExprStmt":
            expr_code = self._generate_expr(stmt.expr)
            self._emit(f"{self._strip_outer_parens(expr_code)};")
        elif stmt_class == "Assignment":
            # Handle assignment statement
            target = self._generate_expr(stmt.target)
            value = self._generate_expr(stmt.expr)
            self._emit(f"{target} = {value};")
        elif stmt_class == "ConditionalBlock":
            self._generate_conditional_block(stmt)
        else:
            self._emit(f"// Unknown statement: {stmt_class}")
    
    def _generate_conditional_block(self, stmt):
        """Generate conditional compilation block"""
        # Evaluate condition
        condition_value = False
        
        if isinstance(stmt.condition_expr, str):
            # Simple const name: #ifdef CONST_NAME
            if stmt.condition_expr in self.const_table:
                condition_value = bool(self.const_table[stmt.condition_expr])
        elif isinstance(stmt.condition_expr, tuple) and stmt.condition_expr[0] == 'not':
            # #ifndef: negated condition
            const_name = stmt.condition_expr[1]
            if const_name not in self.const_table:
                condition_value = True
            else:
                condition_value = not bool(self.const_table[const_name])
        else:
            # Expression: #if EXPR
            try:
                result = self._eval_const_expr(stmt.condition_expr)
                condition_value = bool(result)
            except Exception:
                condition_value = False
        
        # Generate appropriate block
        if condition_value:
            for s in stmt.then_block.statements:
                self._generate_statement(s)
        elif stmt.else_block:
            for s in stmt.else_block.statements:
                self._generate_statement(s)
    
    def _generate_let(self, stmt):
        """(Implementation detail)"""
        type_node = stmt.type_node
        init_expr_class = stmt.init_expr.__class__.__name__ if stmt.init_expr else None

        var_type = self._type_to_c(type_node)

        # Special case: Lambda expression → typed function pointer variable
        if init_expr_class == "Lambda":
            lam_name, ret_type, params_str, captures = self._generate_lambda_inline(stmt.init_expr, stmt.name)
            c_var_name = _safe_c_name(stmt.name)
            if c_var_name != stmt.name:
                self.ident_renames[stmt.name] = c_var_name
            if captures:
                # クロージャ: closure_t 構造体を宣言し env フィールドを初期化
                env_struct = f"{lam_name}_env_t"
                closure_type = f"{lam_name}_closure_t"
                full_params = f"{params_str}, {env_struct}*" if params_str else f"{env_struct}*"
                self._emit(f"{closure_type} {c_var_name};")
                self._emit(f"{c_var_name}.fn = {lam_name};")
                for cap_name in captures:
                    self._emit(f"{c_var_name}.env.{cap_name} = {cap_name};")
                self.env[-1][stmt.name] = "fn_closure"
                self.closure_env_types[stmt.name] = lam_name
            else:
                self._emit(f"{ret_type} (*{c_var_name})({params_str}) = {lam_name};")
                self.env[-1][stmt.name] = "fn"
            return

        # FunctionCall の引数に StringLiteral がある場合の前処理 (temp 変数化)
        temp_string_mapping = {}
        if init_expr_class == "FunctionCall":
            for i, arg in enumerate(stmt.init_expr.args):
                if arg.__class__.__name__ == "StringLiteral":
                    temp_var_name = f"__temp_str_{self.temp_string_counter}"
                    self.temp_string_counter += 1
                    # StringLiteral を make_mryl_string() で一時変数に変換
                    escaped = self._c_escape(arg.value)
                    self._emit(f'MrylString {temp_var_name} = make_mryl_string("{escaped}");')
                    # 解放リストに追加 (関数終了時に free)
                    self.local_string_vars.append(temp_var_name)
                    # StringLiteral オブジェクトの id を temp 変数名にマップ
                    temp_string_mapping[id(arg)] = temp_var_name
        
        # temp 変数マップを使って init_expr を生成
        init_expr = self._generate_expr_with_temps(stmt.init_expr, temp_string_mapping)

        # 動的配列(array_size == -1): MrylVec_<T> を生成
        if type_node and type_node.array_size == -1:
            et = type_node.name
            _c_map = {
                "i8": "int8_t", "i16": "int16_t", "i32": "int32_t", "i64": "int64_t",
                "u8": "uint8_t", "u16": "uint16_t", "u32": "uint32_t", "u64": "uint64_t",
                "f32": "float", "f64": "double", "bool": "int",
            }
            ct = _c_map.get(et, "int32_t")
            if init_expr_class == "ArrayLiteral" and stmt.init_expr.elements:
                elements = [self._generate_expr(elem) for elem in stmt.init_expr.elements]
                elems_str = ", ".join(elements)
                n = len(stmt.init_expr.elements)
                self._emit(f"MrylVec_{et} {stmt.name} = mryl_vec_{et}_from(({ct}[]){{{elems_str}}}, {n});")
            else:
                self._emit(f"MrylVec_{et} {stmt.name} = mryl_vec_{et}_new();")
            self.vec_var_types[stmt.name] = et
            self.env[-1][stmt.name] = f"vec_{et}"
            return

        # 固定長配列の処理
        if type_node and type_node.array_size is not None and type_node.array_size > 0:
            base_type = self._type_to_c_base(type_node.name)
            
            # ArrayLiteral が初期値の場合は初期化子リストを生成
            if init_expr_class == "ArrayLiteral":
                array_lit = stmt.init_expr
                elements = [self._generate_expr(elem) for elem in array_lit.elements]
                init_values = "{" + ", ".join(elements) + "}"
                self._emit(f"{base_type} {stmt.name}[{type_node.array_size}] = {init_values};")
            else:
                self._emit(f"{base_type} {stmt.name}[{type_node.array_size}] = {{0}};")
            
            # 配列サイズをマップに記録
            self.array_sizes[stmt.name] = type_node.array_size
            # 変数の型をスコープに登録
            self.env[-1][stmt.name] = type_node.name
        elif init_expr_class == "ArrayLiteral":
            # ArrayLiteral だが type_node に array_size がない場合: サイズを要素数から推定
            array_lit = stmt.init_expr
            array_size = len(array_lit.elements)
            
            # 各要素を生成
            elements = [self._generate_expr(elem) for elem in array_lit.elements]
            init_values = "{" + ", ".join(elements) + "}"
            
            # C 配列として宣言 (int32_t[])
            self._emit(f"int32_t {stmt.name}[{array_size}] = {init_values};")
            # 配列サイズをマップに記録
            self.array_sizes[stmt.name] = array_size
            # 変数の型をスコープに登録
            self.env[-1][stmt.name] = "i32"
        else:
            # var_type が "any" の場合は init_expr から再推論
            if var_type in ("any",) and stmt.init_expr is not None:
                inferred_mryl = self._infer_expr_type(stmt.init_expr)
                if inferred_mryl == "string":
                    var_type = "MrylString"
                else:
                    c = self._type_to_c_base(inferred_mryl)
                    var_type = c if c not in ("any", "") else "int32_t"
            self._emit(f"{var_type} {stmt.name} = {init_expr};")
                # string 型の場合は MrylString 解放リストに追加
            if type_node:
                self.env[-1][stmt.name] = type_node.name
                if type_node.name == "string":
                    self.local_string_vars.append(stmt.name)
            else:
                # 型が不明な場合は式から推論
                inferred_type = self._infer_expr_type(stmt.init_expr)
                self.env[-1][stmt.name] = inferred_type
                if inferred_type == "string":
                    self.local_string_vars.append(stmt.name)
    
    def _generate_return(self, stmt):
        """(Implementation detail)"""
        if stmt.expr:
            expr_class = stmt.expr.__class__.__name__
            # Ok(val) / Err(val) を Result compound literal に変換
            if expr_class == "FunctionCall" and stmt.expr.name in ("Ok", "Err") and self.current_return_type:
                val_code = self._generate_expr(stmt.expr.args[0]) if stmt.expr.args else "0"
                struct_name = self.current_return_type
                # result_type_registry から対応する struct 名を検索
                for (ok_c, err_c, sname) in self.result_type_registry:
                    if sname == struct_name:
                        if stmt.expr.name == "Ok":
                            self._emit(f"return ({struct_name}){{1, {{.ok_val = {val_code}}}}};")
                        else:
                            self._emit(f"return ({struct_name}){{0, {{.err_val = {val_code}}}}};")
                        return
                # fallback: struct 名が見つからなくてもそのまま出力
                if stmt.expr.name == "Ok":
                    self._emit(f"return ({struct_name}){{1, {{.ok_val = {val_code}}}}};")
                else:
                    self._emit(f"return ({struct_name}){{0, {{.err_val = {val_code}}}}};")
                return
            expr_code = self._generate_expr(stmt.expr)
            self._emit(f"return {expr_code};")
        else:
            self._emit("return;")
    
    def _generate_if(self, stmt):
        """(Implementation detail)"""
        cond = self._generate_expr(stmt.condition)
        self._emit(f"if ({self._strip_outer_parens(cond)}) {{")
        self.indent_level += 1
        for s in stmt.then_block.statements:
            self._generate_statement(s)
        self.indent_level -= 1

        # else_block の出力 (else if チェーンを再帰的に処理)
        cur = stmt.else_block
        while cur is not None:
            if cur.__class__.__name__ == 'IfStmt':
                # else if
                cur_cond = self._generate_expr(cur.condition)
                self._emit(f"}} else if ({self._strip_outer_parens(cur_cond)}) {{")
                self.indent_level += 1
                for s in cur.then_block.statements:
                    self._generate_statement(s)
                self.indent_level -= 1
                cur = cur.else_block
            else:
                # 通常の else ブロック (Block)
                self._emit("} else {")
                self.indent_level += 1
                for s in cur.statements:
                    self._generate_statement(s)
                self.indent_level -= 1
                cur = None

        self._emit("}")

    def _emit_raw(self, text: str):
        """(Implementation detail)"""
        if self.code:
            self.code[-1] = self.code[-1].rstrip() + text
        else:
            self.code.append(text)

    def _generate_if_inline(self, stmt):
        """(Implementation detail)"""
        self._generate_if(stmt)
    
    def _strip_outer_parens(self, s: str) -> str:
        """Remove one redundant layer of outer parentheses if present.
        e.g. '(a < 10)' -> 'a < 10', '((a+b) > c)' -> '(a+b) > c', 'running' -> 'running'
        Inner parens needed for precedence (e.g. compound conditions) are preserved.
        """
        s = s.strip()
        if len(s) < 2 or s[0] != '(' or s[-1] != ')':
            return s
        depth = 0
        for i, c in enumerate(s):
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            if depth == 0 and i < len(s) - 1:
                # Outer parens close before the end → not a simple wrapper
                return s
        return s[1:-1]

    def _generate_while(self, stmt):
        """(Implementation detail)"""
        cond = self._generate_expr(stmt.condition)
        self._emit(f"while ({self._strip_outer_parens(cond)}) {{")
        self.indent_level += 1
        for s in stmt.body.statements:
            self._generate_statement(s)
        self.indent_level -= 1
        self._emit("}")
    
    def _generate_for(self, stmt):
        """(Implementation detail)"""
        if stmt.is_c_style:
            # C スタイル: for (let i = 0; i < 10; i++)
            # variable: ループ変数名
            # iterable: 初期値式
            # condition: 条件式
            # update: 更新式
            var_name = stmt.variable
            init_expr = self._generate_expr(stmt.iterable)
            
            # 変数の型 (int32_t に固定)
            init_type = "int32_t"
            init_code = f"{init_type} {var_name} = {init_expr}"
            
            cond_code = self._generate_expr(stmt.condition) if stmt.condition else "1"
            # update は Assignment ノード (k = k + 2) か式 (i++) のどちらかになる
            if stmt.update:
                if stmt.update.__class__.__name__ == "Assignment":
                    target_c = self._generate_expr(stmt.update.target)
                    value_c = self._generate_expr(stmt.update.expr)
                    update_code = f"{target_c} = {value_c}"
                else:
                    update_code = self._generate_expr(stmt.update)
                update_code = self._strip_outer_parens(update_code)
            else:
                update_code = ""
            cond_code = self._strip_outer_parens(cond_code)
            self._emit(f"for ({init_code}; {cond_code}; {update_code}) {{")
        else:
            # Rust スタイル: for x in range/array
            # Range の場合: start と end を取得
            if stmt.iterable.__class__.__name__ == "Range":
                range_expr = stmt.iterable
                start = self._generate_expr(range_expr.start)
                end = self._generate_expr(range_expr.end)
                # Range.inclusive が True なら <= を、False なら < を使用
                cmp_op = "<=" if range_expr.inclusive else "<"
                self._emit(f"for (int {stmt.variable} = {start}; {stmt.variable} {cmp_op} {end}; {stmt.variable}++) {{")
            elif stmt.iterable.__class__.__name__ == "ArrayLiteral":
                # ArrayLiteral はインデックス変数でループして要素にアクセス
                array_size = len(stmt.iterable.elements)
                loop_var_name = f"__i{self.loop_counter}"
                self.loop_counter += 1
                self._emit(f"for (int {loop_var_name} = 0; {loop_var_name} < {array_size}; {loop_var_name}++) {{")
                self.indent_level += 1
                # ループ変数に配列要素の値を代入
                self._emit(f"int32_t {stmt.variable} = ({self._generate_array_element(stmt.iterable, loop_var_name)});")
                for s in stmt.body.statements:
                    self._generate_statement(s)
                self.indent_level -= 1
                self._emit("}")
                return
            elif stmt.iterable.__class__.__name__ == "VarRef":
                # VarRef の場合: 配列サイズのキャッシュをルックアップ
                var_name = stmt.iterable.name
                if var_name in self.vec_var_types:
                    # 動的配列(ベク)のループ: .len と .data[i]
                    et = self.vec_var_types[var_name]
                    loop_var_name = f"__i{self.loop_counter}"
                    self.loop_counter += 1
                    self._emit(f"for (int32_t {loop_var_name} = 0; {loop_var_name} < {var_name}.len; {loop_var_name}++) {{")
                    self.indent_level += 1
                    ct = {"i8":"int8_t","i16":"int16_t","i32":"int32_t","i64":"int64_t",
                          "u8":"uint8_t","u16":"uint16_t","u32":"uint32_t","u64":"uint64_t",
                          "f32":"float","f64":"double","bool":"int"}.get(et, "int32_t")
                    self._emit(f"{ct} {stmt.variable} = {var_name}.data[{loop_var_name}];")
                    for s in stmt.body.statements:
                        self._generate_statement(s)
                    self.indent_level -= 1
                    self._emit("}")
                    return
                elif var_name in self.array_sizes:
                    array_size = self.array_sizes[var_name]
                    loop_var_name = f"__i{self.loop_counter}"
                    self.loop_counter += 1
                    self._emit(f"for (int {loop_var_name} = 0; {loop_var_name} < {array_size}; {loop_var_name}++) {{")
                    self.indent_level += 1
                    # ループ変数に配列要素の値を代入
                    self._emit(f"int32_t {stmt.variable} = {var_name}[{loop_var_name}];")
                    for s in stmt.body.statements:
                        self._generate_statement(s)
                    self.indent_level -= 1
                    self._emit("}")
                    return
                else:
                    # 配列サイズが不明な場合は sizeof を使ったフォールバック
                    self._emit(f"// WARNING: Array size unknown for {var_name}, using fallback")
                    self._emit(f"for (int {stmt.variable} = 0; {stmt.variable} < sizeof({var_name})/sizeof({var_name}[0]); {stmt.variable}++) {{")
            else:
                # その他のイテレータ型 (フォールバック)
                iterable = self._generate_expr(stmt.iterable)
                self._emit(f"// for ({stmt.variable} in {iterable})")
                self._emit(f"for (int {stmt.variable} = 0; {stmt.variable} < 10; {stmt.variable}++) {{")
        
        self.indent_level += 1
        for s in stmt.body.statements:
            self._generate_statement(s)
        self.indent_level -= 1
        self._emit("}")
    
    def _generate_array_element(self, array_expr, index) -> str:
        """(Implementation detail)"""
        arr_code = self._generate_expr(array_expr)
        return f"{arr_code}[{index}]"
    
    def _generate_expr(self, expr) -> str:
        """(Implementation detail)"""
        if expr is None:
            return ""
        
        expr_class = expr.__class__.__name__
        
        if expr_class == "NumberLiteral":
            return str(expr.value)
        
        if expr_class == "FloatLiteral":
            return str(expr.value)
        
        if expr_class == "StringLiteral":
            escaped = self._c_escape(expr.value)
            return f'make_mryl_string("{escaped}")'
        
        if expr_class == "BoolLiteral":
            return "1" if expr.value else "0"
        
        if expr_class == "VarRef":
            if self.sm_mode and expr.name in self.sm_vars:
                return f"__sm->{expr.name}"
            if expr.name in self.capture_map:
                return self.capture_map[expr.name]
            # C予約語回避のためのリネームをチェック
            if expr.name in self.ident_renames:
                return self.ident_renames[expr.name]
            return _safe_c_name(expr.name)
        
        if expr_class == "BinaryOp":
            left = self._generate_expr(expr.left)
            right = self._generate_expr(expr.right)
            op = expr.op
            # string + string は mryl_string_concat 関数を呼ぶ
            left_type = self._infer_expr_type(expr.left)
            right_type = self._infer_expr_type(expr.right)
            if left_type == "string" and right_type == "string" and op == "+":
                return f"mryl_string_concat({left}, {right})"
            
            # C 演算子へのマッピング
            c_op = op
            if op == "&&":
                c_op = "&&"
            elif op == "||":
                c_op = "||"
            elif op == "&":
                c_op = "&"
            elif op == "|":
                c_op = "|"
            elif op == "^":
                c_op = "^"
            elif op == "<<":
                c_op = "<<"
            elif op == ">>":
                c_op = ">>"
            
            return f"({left} {c_op} {right})"
        
        if expr_class == "UnaryOp":
            operand = self._generate_expr(expr.operand)
            if expr.op == "post++":
                return f"({operand}++)"
            elif expr.op == "post--":
                return f"({operand}--)"
            elif expr.op == "!":
                # Logical NOT
                return f"(!{operand})"
            elif expr.op == "~":
                # Bitwise NOT
                return f"(~{operand})"
            else:
                return f"({expr.op}{operand})"
        
        if expr_class == "FunctionCall":
            return self._generate_function_call(expr)
        
        if expr_class == "StructAccess":
            obj = self._generate_expr(expr.obj)
            return f"{obj}.{expr.field}"
        
        if expr_class == "ArrayAccess":
            arr = self._generate_expr(expr.array)
            idx = self._generate_expr(expr.index)
            # 動的配列(MintVec)の場合は .data[idx]
            arr_name = expr.array.name if expr.array.__class__.__name__ == 'VarRef' else None
            if arr_name and arr_name in self.vec_var_types:
                return f"{arr}.data[{idx}]"
            return f"{arr}[{idx}]"
        
        if expr_class == "StructInit":
            return self._generate_struct_init(expr)
        
        if expr_class == "EnumVariantExpr":
            return self._generate_enum_variant_expr(expr)

        if expr_class == "MatchExpr":
            return self._generate_match_expr(expr)

        if expr_class == "MethodCall":
            return self._generate_method_call(expr)
        
        if expr_class == "Lambda":
            return self._generate_lambda(expr)

        if expr_class == "AwaitExpr":
            # Inline await: returns void* pthread_join result (caller must cast)
            # For expression context, generate a block expression (GCC extension)
            handle = self._generate_expr(expr.expr)
            tmp = f"__await_tmp_{self.lambda_counter}"
            self.lambda_counter += 1
            # Emit the join as a side-effect statement before this expression
            # (This is emitted as a compound statement; generate inline)
            return f"/* await {handle} - use let statement for typed await */"

            value = self._generate_expr(expr.expr)
            return f"{target} = {value}"
        
        return "0"
    
    def _generate_expr_with_temps(self, expr, temp_string_mapping: dict) -> str:
        """(Implementation detail)"""
        if expr is None:
            return ""
        
        expr_class = expr.__class__.__name__
        
        if expr_class == "StringLiteral":
            # temp_string_mapping に登録済みなら temp 変数名を返す
            if id(expr) in temp_string_mapping:
                return temp_string_mapping[id(expr)]
            # 未登録ならそのまま _generate_expr に委譲
            return self._generate_expr(expr)
        
        if expr_class == "FunctionCall":
            # クロージャ / fn スコープ変数の呼び出しは _generate_function_call に委譲
            for scope in reversed(self.env):
                if expr.name in scope and scope[expr.name] in ('fn', 'fn_closure'):
                    return self._generate_function_call(expr)
            # 各引数も再帰的に _generate_expr_with_temps で生成
            args = []
            for arg in expr.args:
                arg_code = self._generate_expr_with_temps(arg, temp_string_mapping)
                args.append(arg_code)
            
            # print/println は専用ルーティングへ
            if expr.name in ["print", "println"]:
                # print/println の特別処理
                return self._generate_print_call(expr)
            
            func = self.program_functions.get(expr.name)
            if func and func.type_params:
                type_args = self._infer_generic_type_args(func, expr.args)
                type_args_tuple = tuple(str(t) for t in type_args)
                self._register_generic_instantiation(expr.name, type_args)
                instantiated_name = self._get_instantiated_func_name(expr.name, type_args_tuple)
                return f"{instantiated_name}({', '.join(args)})"
            
            # ジェネリック関数の呼び出し
            return f"{expr.name}({', '.join(args)})"
        
        if expr_class == "BinaryOp":
            left = self._generate_expr_with_temps(expr.left, temp_string_mapping)
            right = self._generate_expr_with_temps(expr.right, temp_string_mapping)
            op = expr.op
            left_type = self._infer_expr_type(expr.left)
            right_type = self._infer_expr_type(expr.right)
            if left_type == "string" and right_type == "string" and op == "+":
                return f"mryl_string_concat({left}, {right})"
            return f"({left} {op} {right})"
        
        # その他の式は _generate_expr に委譲
        return self._generate_expr(expr)
    
    def _generate_function_call(self, expr) -> str:
        """(Implementation detail)"""
        # print/println は専用のルーティングへ
        if expr.name in ["print", "println"]:
            return self._generate_print_call(expr)

        # Ok/Err compound literal の生成
        if expr.name in ("Ok", "Err"):
            val_code = self._generate_expr(expr.args[0]) if expr.args else "0"
            # current_return_type から Result の struct 名を取得
            struct_name = self.current_return_type or "MrylResult_i32_i32"
            if expr.name == "Ok":
                return f"({struct_name}){{1, {{.ok_val = {val_code}}}}}"
            else:
                return f"({struct_name}){{0, {{.err_val = {val_code}}}}}"

        # Check if name is a lambda variable in scope (function pointer or closure call)
        for scope in reversed(self.env):
            if expr.name in scope and scope[expr.name] == "fn":
                c_name = self.ident_renames.get(expr.name, _safe_c_name(expr.name))
                args = ", ".join(self._generate_expr(arg) for arg in expr.args)
                return f"{c_name}({args})"
            if expr.name in scope and scope[expr.name] == "fn_closure":
                c_name = self.ident_renames.get(expr.name, _safe_c_name(expr.name))
                args = ", ".join(self._generate_expr(arg) for arg in expr.args)
                all_args = f"{args}, &{c_name}.env" if args else f"&{c_name}.env"
                return f"{c_name}.fn({all_args})"

        # ジェネリック関数の処理
        func = self.program_functions.get(expr.name)
        if func and func.type_params:
            # 型引数を推論してキャッシュに登録
            type_args = self._infer_generic_type_args(func, expr.args)
            type_args_tuple = tuple(str(t) for t in type_args)
            self._register_generic_instantiation(expr.name, type_args)
            
            # 実体化済み関数名を生成
            instantiated_name = self._get_instantiated_func_name(expr.name, type_args_tuple)
            args = ", ".join(self._generate_expr(arg) for arg in expr.args)
            return f"{instantiated_name}({args})"
        
        # 通常の関数呼び出し
        args = ", ".join(self._generate_expr(arg) for arg in expr.args)
        return f"{expr.name}({args})"
    
    def _type_to_fmt_spec(self, arg_expr) -> str:
        """(Implementation detail)"""
        t = self._infer_expr_type(arg_expr)
        if t in ("string", "str"):
            return "%s"
        if t in ("f32", "f64", "float"):
            return "%f"
        if t in ("bool",):
            return "%d"
        return "%d"

    def _generate_print_call(self, expr) -> str:
        """(Implementation detail)"""
        if not expr.args:
            return f'{expr.name}("")'

        first_arg = expr.args[0]

        # 書式指定子を引数の型に応じて選択
        if first_arg.__class__.__name__ == "StringLiteral":
            if len(expr.args) > 1:
                # 書式文字列: {} をフォーマット指定子に変換
                fmt_str = first_arg.value
                format_args = expr.args[1:]
                parts = fmt_str.split("{}")
                if len(parts) != len(format_args) + 1:
                    # {} の数と引数の数が一致しない場合は %d を fallback 指定子として使用
                    fmt_c = self._c_escape(fmt_str.replace("{}", "%d"))
                    args = [f'"{fmt_c}"']
                    for a in format_args:
                        arg_type = self._infer_expr_type(a)
                        arg_code = self._generate_expr(a)
                        args.append(f"{arg_code}.data" if arg_type in ("string", "str") else arg_code)
                    return f'{expr.name}({", ".join(args)})'

                # 各 {} を引数の型に応じた書式指定子と部分文字列に変換
                fmt_c = ""
                for i, part in enumerate(parts[:-1]):
                    spec = self._type_to_fmt_spec(format_args[i])
                    fmt_c += part.replace("%", "%%") + spec
                fmt_c += parts[-1].replace("%", "%%")
                fmt_c = fmt_c.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
                c_args = [f'"{fmt_c}"']
                for a in format_args:
                    arg_type = self._infer_expr_type(a)
                    arg_code = self._generate_expr(a)
                    c_args.append(f"{arg_code}.data" if arg_type in ("string", "str") else arg_code)
                return f'{expr.name}({", ".join(c_args)})'
            else:
                # 書式引数なし: fmt 文字列のみをそのまま出力
                escaped = self._c_escape(first_arg.value)
                return f'{expr.name}("{escaped}")'
        else:
            # 書式文字列でない引数 (例: println(i)) は型に応じて指定子を選択
            arg_type = self._infer_expr_type(first_arg)
            if arg_type in ("string", "str"):
                arg_code = self._generate_expr(first_arg)
                return f'{expr.name}("%s", {arg_code}.data)'
            elif arg_type in ("f32", "f64", "float"):
                arg_code = self._generate_expr(first_arg)
                return f'{expr.name}("%f", {arg_code})'
            else:
                arg_code = self._generate_expr(first_arg)
                return f'{expr.name}("%d", {arg_code})'
    
    def _generate_struct_init(self, expr) -> str:
        """(Implementation detail)"""
        # 注: C99 Compound literal 形式でフィールドを初期化
        fields = ", ".join(
            f".{name} = {self._generate_expr(value)}"
            for name, value in expr.fields
        )
        return f"({expr.struct_name}){{ {fields} }}"

    def _generate_match_expr(self, expr) -> str:
        """Generate a GCC compound statement expression for a match expression."""
        n = self.lambda_counter
        self.lambda_counter += 1
        mv = f"__mv_{n}"
        mr = f"__mr_{n}"

        scrutinee_c = self._generate_expr(expr.scrutinee)
        scrutinee_type = self._infer_expr_type(expr.scrutinee)
        scrutinee_is_string = (scrutinee_type == "string")

        result_c_type = self._infer_match_result_c_type(expr.arms)

        # Default zero value for the result variable
        zero_val = '""' if result_c_type == "const char*" \
            else 'make_mryl_string("")' if result_c_type == "MrylString" \
            else "0"

        lines = ["({",
                 f"    __auto_type {mv} = ({scrutinee_c});",
                 f"    {result_c_type} {mr} = {zero_val};"]

        has_catch_all = False
        first = True
        for arm in expr.arms:
            pattern = arm.pattern
            klass = pattern.__class__.__name__

            if klass == "BindingPattern" and pattern.name == "_":
                # Error arm: _ always matches but raises a panic
                has_catch_all = True
                kw = "else" if not first else ""
                if kw:
                    lines.append(f"    {kw} {{")
                else:
                    lines.append("    {")
                lines.append(f'        mryl_panic("MatchError", "reached \'_\' error arm", __func__, __FILE__, __LINE__);')
                lines.append("    }")
                first = False
                continue

            cond, bindings = self._match_pattern_to_c(mv, pattern, scrutinee_is_string)

            if isinstance(pattern, BindingPattern) or isinstance(pattern, StructPattern):
                has_catch_all = True

            kw = ("else if (1)" if not first else "if (1)") if cond == "1" else \
                 ("else if" if not first else "if")
            cond_part = "" if cond == "1" else f" ({cond})"
            lines.append(f"    {kw}{cond_part} {{")
            for b in bindings:
                lines.append(f"        {b}")
            body_c = self._generate_expr(arm.body)
            lines.append(f"        {mr} = {body_c};")
            lines.append("    }")
            first = False

        if not has_catch_all:
            kw = "else" if len(expr.arms) > 0 else ""
            if kw:
                lines.append(f"    {kw} {{")
            else:
                lines.append("    {")
            lines.append(f'        mryl_panic("MatchError", "no arm matched", __func__, __FILE__, __LINE__);')
            lines.append("    }")

        lines.append(f"    {mr};")
        lines.append("})")
        return "\n".join(lines)

    def _infer_match_result_c_type(self, arms) -> str:
        """Infer the C result type for a match expression from arm bodies."""
        for arm in arms:
            if isinstance(arm.pattern, BindingPattern) and arm.pattern.name == "_":
                continue
            scope = self._pattern_binding_types(arm.pattern)
            self.env.append(scope)
            t = self._infer_expr_type(arm.body)
            self.env.pop()
            if t == "string":
                return "MrylString"
            c = self._type_to_c_base(t)
            if c not in ("any", ""):
                return c
        return "int32_t"

    def _pattern_binding_types(self, pattern) -> dict:
        """Return {binding_name: mint_type_name} for pattern variable bindings."""
        if isinstance(pattern, EnumPattern):
            enum_decl = self.enums.get(pattern.enum_name)
            if enum_decl:
                variant = next(
                    (v for v in enum_decl.variants if v.name == pattern.variant_name), None
                )
                if variant:
                    return {
                        name: (variant.fields[i].name if i < len(variant.fields) else "any")
                        for i, name in enumerate(pattern.bindings)
                    }
        if isinstance(pattern, BindingPattern):
            return {pattern.name: "any"}
        if isinstance(pattern, StructPattern):
            return {f: "any" for f in pattern.fields}
        return {}

    def _match_pattern_to_c(self, mv: str, pattern, scrutinee_is_string: bool):
        """Returns (condition_str, bindings_list) for a match pattern."""
        klass = pattern.__class__.__name__

        if klass == "LiteralPattern":
            val = pattern.value
            if isinstance(val, bool):
                cond = f"{mv} == {1 if val else 0}"
            elif isinstance(val, str):
                escaped = val.replace('"', '\\"')
                cond = f'strcmp({mv}.data, "{escaped}") == 0' if scrutinee_is_string \
                    else f'strcmp({mv}, "{escaped}") == 0'
            elif isinstance(val, float):
                cond = f"{mv} == {val}"
            else:
                cond = f"{mv} == {val}"
            return cond, []

        if klass == "BindingPattern":
            name = pattern.name
            return "1", [f"__auto_type {name} = {mv};"]

        if klass == "EnumPattern":
            enum_name = pattern.enum_name
            variant_name = pattern.variant_name
            enum_decl = self.enums.get(enum_name)
            has_data = enum_decl and any(v.fields for v in enum_decl.variants)
            if has_data:
                cond = f"{mv}.tag == {enum_name}_Tag_{variant_name}"
                bindings = [
                    f"__auto_type {name} = {mv}.data.{variant_name}._{i};"
                    for i, name in enumerate(pattern.bindings)
                ]
            else:
                cond = f"{mv} == {enum_name}_{variant_name}"
                bindings = []
            return cond, bindings

        if klass == "StructPattern":
            bindings = [f"__auto_type {f} = {mv}.{f};" for f in pattern.fields]
            return "1", bindings

        if klass == "RegexPattern":
            pat_escaped = pattern.pattern_str.replace("\\", "\\\\").replace('"', '\\"')
            # POSIX regex check inline via GCC compound expression
            mv_data = f"{mv}.data" if scrutinee_is_string else mv
            cond = (
                f"({{ regex_t __re_{id(pattern) & 0xFFFF}; "
                f"regcomp(&__re_{id(pattern) & 0xFFFF}, \"{pat_escaped}\", REG_EXTENDED | REG_NOSUB); "
                f"int __rc_{id(pattern) & 0xFFFF} = regexec(&__re_{id(pattern) & 0xFFFF}, {mv_data}, 0, NULL, 0); "
                f"regfree(&__re_{id(pattern) & 0xFFFF}); "
                f"__rc_{id(pattern) & 0xFFFF} == 0; }})"
            )
            return cond, []

        return "0", []

    def _generate_enum_variant_expr(self, expr) -> str:
        """Generate C expression for an enum variant construction.

        Simple enum  (no variant has fields): generate constant  EnumName_VariantName
        Data enum  (some variant carries data): call constructor  EnumName_VariantName(args)
        """
        enum_name = expr.enum_name
        variant_name = expr.variant_name
        enum_decl = self.enums.get(enum_name)

        # Determine if this enum has any data-carrying variants
        has_data = enum_decl and any(v.fields for v in enum_decl.variants)

        if has_data:
            arg_strs = [self._generate_expr(a) for a in expr.args]
            args_str = ", ".join(arg_strs)
            return f"{enum_name}_{variant_name}({args_str})"
        else:
            return f"{enum_name}_{variant_name}"

    def _generate_method_call(self, expr) -> str:
        """(Implementation detail)"""
        obj_type = self._infer_expr_type(expr.obj)

        # 動的配列(MrylVec_<T>)のメソッド処理
        if obj_type.startswith("vec_"):
            et = obj_type[4:]  # "i32" from "vec_i32"
            obj_name = expr.obj.name if expr.obj.__class__.__name__ == 'VarRef' else self._generate_expr(expr.obj)
            if expr.method == 'push':
                arg = self._generate_expr(expr.args[0])
                return f"mryl_vec_{et}_push(&{obj_name}, {arg})"
            elif expr.method == 'pop':
                return f"mryl_vec_{et}_pop(&{obj_name})"
            elif expr.method == 'len':
                return f"{obj_name}.len"
            elif expr.method == 'is_empty':
                return f"({obj_name}.len == 0)"
            elif expr.method == 'remove':
                arg = self._generate_expr(expr.args[0])
                return f"mryl_vec_{et}_remove(&{obj_name}, {arg})"
            elif expr.method == 'insert':
                idx = self._generate_expr(expr.args[0])
                val = self._generate_expr(expr.args[1])
                return f"mryl_vec_{et}_insert(&{obj_name}, {idx}, {val})"

        # Result<T,E> のメソッド処理: is_ok/is_err/try/err/unwrap/unwrap_err/unwrap_or
        obj_type = self._infer_expr_type(expr.obj)
        if obj_type == "Result":
            obj_code = self._generate_expr(expr.obj)
            if expr.method == "is_ok":
                return f"({obj_code}.is_ok)"
            if expr.method == "is_err":
                return f"(!{obj_code}.is_ok)"
            if expr.method in ("try", "unwrap", "err"):
                # .try() : Ok値を取り出す。Err なら構造化エラーで終了
                return (
                    f"({{ __auto_type __uw = {obj_code}; "
                    f"if (!__uw.is_ok) {{ "
                    f"char __em[64]; snprintf(__em, sizeof(__em), \"Err(%d)\", (int)__uw.data.err_val); "
                    f'mryl_panic("Error", __em, __func__, __FILE__, __LINE__); }} '
                    f"__uw.data.ok_val; }})"
                )
            if expr.method == "unwrap_err":
                return (
                    f"({{ __auto_type __uw = {obj_code}; "
                    f"if (__uw.is_ok) {{ "
                    f'mryl_panic("UnwrapError", "unwrap_err() called on Ok value", __func__, __FILE__, __LINE__); }} '
                    f"__uw.data.err_val; }})"
                )
            if expr.method == "unwrap_or":
                default_code = self._generate_expr(expr.args[0]) if expr.args else "0"
                return f"({obj_code}.is_ok ? {obj_code}.data.ok_val : {default_code})"

        obj = self._generate_expr(expr.obj)
        args_list = [self._generate_expr(arg) for arg in expr.args]
        
        # struct_name を推論してメソッドを解決
        struct_name = self._infer_struct_name(expr.method)
        
        # 呼び出し形式: struct_name_method_name(obj, args)
        all_args = [obj] + args_list
        args_str = ", ".join(all_args) if all_args else ""
        return f"{struct_name}_{expr.method}({args_str})"

    def _collect_captures(self, node, param_names: set) -> dict:
        """(Implementation detail)"""
        captures = {}
        def walk(n):
            if n is None: return
            cls = n.__class__.__name__
            if cls == 'VarRef' and n.name not in param_names and n.name not in captures:
                for scope in reversed(self.env):
                    if n.name in scope:
                        t = scope[n.name]
                        c_t = {"i8":"int8_t","i16":"int16_t","i32":"int32_t","i64":"int64_t",
                               "u8":"uint8_t","u16":"uint16_t","u32":"uint32_t","u64":"uint64_t",
                               "f32":"float","f64":"double","string":"MrylString",
                               "bool":"int","fn":"void*","fn_closure":"void*",
                               "int":"int32_t"}.get(t, "int32_t")
                        captures[n.name] = c_t
                        break
            elif cls in ('BinaryOp', 'CompareOp'): walk(n.left); walk(n.right)
            elif cls == 'UnaryOp': walk(n.operand)
            elif cls == 'FunctionCall':
                for a in n.args: walk(a)
            elif cls == 'Block':
                for s in n.statements: walk(s)
            elif cls == 'LetDecl':
                if n.init_expr: walk(n.init_expr)
            elif cls == 'ReturnStmt':
                if n.expr: walk(n.expr)
            elif cls == 'ExprStmt': walk(n.expr)
            elif cls in ('IfStmt', 'IfExpr'):
                walk(n.condition); walk(n.then_block)
                if n.else_block: walk(n.else_block)
            elif cls == 'MethodCall':
                walk(n.obj)
                for a in (n.args or []): walk(a)
        walk(node)
        return captures

    # ============================================================
    # Lambda: (params) => body を static helper function に変換
    # ============================================================
    def _generate_lambda(self, expr) -> str:
        """(Implementation detail)"""
        lam_name = f"__lambda_{self.lambda_counter}"
        self.lambda_counter += 1

        param_names = {p.name for p in expr.params}
        captures = self._collect_captures(expr.body, param_names)

        # Determine parameter types (default to int32_t when unannotated)
        params_c = []
        for p in expr.params:
            if p.type_node:
                ptype = self._type_to_c(p.type_node)
            else:
                ptype = "int32_t"
            params_c.append(f"{ptype} {p.name}")
        params_str = ", ".join(params_c) if params_c else "void"

        # Capture body code by temporarily redirecting output
        saved_code = self.code
        saved_indent = self.indent_level
        saved_capture_map = dict(self.capture_map)
        self.code = []
        self.indent_level = 1  # Inside static function body
        if captures:
            self.capture_map = {n: f"__env->{n}" for n in captures}

        if isinstance(expr.body, Block):
            for stmt in expr.body.statements:
                self._generate_statement(stmt)
            ret_type = "void"
        else:
            body_expr = self._generate_expr(expr.body)
            self._emit(f"return {body_expr};")
            ret_type = "int32_t"  # Default; proper inference handled by TypeChecker

        body_lines = self.code
        self.code = saved_code
        self.indent_level = saved_indent
        self.capture_map = saved_capture_map

        # Store for emission before the enclosing function
        self.pending_lambdas.append((lam_name, ret_type, params_str, body_lines, captures))

        return lam_name  # Function pointer (name of the static function)

    def _generate_lambda_inline(self, expr, var_name: str):
        """(Implementation detail)"""
        lam_name = f"__lambda_{self.lambda_counter}"
        self.lambda_counter += 1

        param_names = {p.name for p in expr.params}
        captures = self._collect_captures(expr.body, param_names)

        # Determine parameter types (default to int32_t when unannotated)
        params_c = []
        for p in expr.params:
            if p.type_node:
                ptype = self._type_to_c(p.type_node)
            else:
                ptype = "int32_t"
            params_c.append(f"{ptype} {p.name}")
        params_str = ", ".join(params_c) if params_c else "void"

        # Determine return type from body
        if isinstance(expr.body, Block):
            ret_type = "void"
        else:
            ret_type = "int32_t"

        # Capture body code by temporarily redirecting output
        saved_code = self.code
        saved_indent = self.indent_level
        saved_capture_map = dict(self.capture_map)
        body_lines_code = []
        self.code = body_lines_code
        self.indent_level = 1
        if captures:
            self.capture_map = {n: f"__env->{n}" for n in captures}

        if isinstance(expr.body, Block):
            for stmt in expr.body.statements:
                self._generate_statement(stmt)
        else:
            body_expr_code = self._generate_expr(expr.body)
            self._emit(f"return {body_expr_code};")

        self.code = saved_code
        self.indent_level = saved_indent
        self.capture_map = saved_capture_map

        self.pending_lambdas.append((lam_name, ret_type, params_str, body_lines_code, captures))

        return lam_name, ret_type, params_str, captures

    # ============================================================
    # Async: generate pthread thread wrapper for async fn
    # ============================================================
    def _body_has_await(self, body):
        """(Implementation detail)"""
        if not body:
            return False
        for stmt in body.statements:
            cls = stmt.__class__.__name__
            if cls == 'LetDecl' and stmt.init_expr and \
               stmt.init_expr.__class__.__name__ == 'AwaitExpr':
                return True
            if cls == 'ExprStmt' and stmt.expr.__class__.__name__ == 'AwaitExpr':
                return True
        return False

    def _to_pascal(self, name: str) -> str:
        """(Implementation detail)"""
        return ''.join(w.capitalize() for w in name.split('_'))

    def _sm_let_c_type(self, stmt) -> str:
        """(Implementation detail)"""
        init_cls = stmt.init_expr.__class__.__name__ if stmt.init_expr else None
        if init_cls == 'FunctionCall':
            f = self.program_functions.get(stmt.init_expr.name)
            if f and getattr(f, 'is_async', False):
                return 'MrylTask*'
        if init_cls == 'AwaitExpr' and stmt.type_node:
            return self._type_to_c(stmt.type_node)
        if stmt.type_node:
            return self._type_to_c(stmt.type_node)
        return 'int32_t'

    def _split_by_await(self, stmts):
        """(Implementation detail)"""
        segments = []
        current = []
        for stmt in stmts:
            cls = stmt.__class__.__name__
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
        """(Implementation detail)"""
        func_name = func.name
        is_main = (func_name == 'main')
        has_return_val = (not is_main) and \
                         func.return_type and func.return_type.name != 'void'

        sm_struct = f"__{self._to_pascal(func_name)}_SM"
        move_next = f"__{func_name}_move_next"

        # SM フィールドを収集 (c_type, field_name, mint_type)
        sm_fields = []
        if not is_main:
            for p in (func.params or []):
                sm_fields.append((self._type_to_c(p.type_node),
                                   p.name,
                                   p.type_node.name if p.type_node else 'any'))
        for stmt in (func.body.statements if func.body else []):
            if stmt.__class__.__name__ == 'LetDecl':
                sm_fields.append((self._sm_let_c_type(stmt), stmt.name, 'any'))

        # 直接 FunctionCall を await している場合の隠しハンドルフィールドを追加
        # 例: let a: i32 = await square(x)  →  __h_0 として MrylTask* を追加
        stmts_preview = func.body.statements if func.body else []
        sm_await_handles = {}  # await_index -> handle_field_name
        for i, (_, aw) in enumerate(self._split_by_await(stmts_preview)):
            if aw is None:
                continue
            aw_cls = aw.__class__.__name__
            inner = aw.expr.expr if aw_cls == 'ExprStmt' else aw.init_expr.expr
            if inner.__class__.__name__ == 'FunctionCall':
                hf = f"__h_{i}"
                sm_await_handles[i] = hf
                sm_fields.append(('MrylTask*', hf, 'any'))
        self.sm_await_handles = sm_await_handles

        # env フィールドをスコープに登録
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

        # 2. move_next 関数を生成
        stmts = func.body.statements if func.body else []
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

        # SM モードを ON に切り替え
        self.sm_mode = True
        self.sm_vars = {fname for (_, fname, _) in sm_fields}

        for i, (pre_stmts, await_stmt) in enumerate(segments):
            self._emit(f"__state_{i}: {{")
            self.indent_level += 1

            # 前の await から result を受け取る
            if i > 0:
                self._emit_await_resume(segments[i - 1][1], i - 1)

            # pre_stmts を出力
            for stmt in pre_stmts:
                self._generate_sm_stmt(stmt, func, has_return_val)

            # 次の await または終了処理を出力
            if await_stmt is not None:
                self._emit_await_setup(await_stmt, i + 1, i)
                self._emit(f"goto __state_{i + 1};")
            else:
                # pre_stmts に ReturnStmt が含まれる場合は完了コード生成済みのためスキップ
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

        # 3. ファクトリ関数 or main エントリポイントの出力
        if is_main:
            self._emit_main_sm_entry(sm_struct, move_next)
        else:
            self._emit_task_factory(func, sm_struct, move_next)

    def _emit_await_setup(self, await_stmt, next_state: int, await_index: int = 0):
        """(Implementation detail)"""
        cls = await_stmt.__class__.__name__
        if await_index in self.sm_await_handles:
            # 直接 FunctionCall を await: ハンドルを SM フィールドに保存して retain
            hf = self.sm_await_handles[await_index]
            inner = await_stmt.expr.expr if cls == 'ExprStmt' else await_stmt.init_expr.expr
            call_code = self._generate_expr(inner)
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
        """(Implementation detail)"""
        cls = await_stmt.__class__.__name__
        # 保存済みハンドルフィールドがあればそれを使う（inline FunctionCall await）
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
        """(Implementation detail)"""
        cls = stmt.__class__.__name__
        if cls == 'LetDecl':
            init_cls = stmt.init_expr.__class__.__name__ if stmt.init_expr else None
            if init_cls == 'FunctionCall':
                f = self.program_functions.get(stmt.init_expr.name)
                if f and getattr(f, 'is_async', False):
                    # async 関数呼び出しは SM タスクを生成して retain
                    args = [self._generate_expr(a) for a in stmt.init_expr.args]
                    args_str = ", ".join(args)
                    self._emit(f"__sm->{stmt.name} = {stmt.init_expr.name}({args_str});")
                    self._emit(f"__task_retain(__sm->{stmt.name});")
                    return
            # 通常の let は SM フィールドに代入
            if stmt.init_expr:
                init_code = self._generate_expr(stmt.init_expr)
                self._emit(f"__sm->{stmt.name} = {init_code};")
            return
        elif cls == 'ReturnStmt':
            if has_return_val and stmt.expr:
                ret_ctype = self._type_to_c(func.return_type)
                ret_code = self._generate_expr(stmt.expr)
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
        """(Implementation detail)"""
        if not has_return_val:
            self._emit("__task->state = MRYL_TASK_COMPLETED;")
            self._emit("__task_release(__task);")
            self._emit("if (__task->awaiter) __scheduler_post(__task->awaiter);")
            self._emit("return;")

    def _emit_task_factory(self, func, sm_struct: str, move_next: str):
        """(Implementation detail)"""
        func_name = func.name
        params = [f"{self._type_to_c(p.type_node)} {p.name}" for p in (func.params or [])]
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
        """(Implementation detail)"""
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
        """(Implementation detail)"""
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

    # (removed: _generate_async_thread_wrapper - pthreads design was replaced by state machine)

    def _infer_struct_name(self, method_name) -> str:
        """(Implementation detail)"""
        for struct in self.structs:
            for method in struct.methods:
                if method.name == method_name:
                    return struct.name
        
        # 見つからない場合のフォールバック
        return "Object"
    
    def _generate_method(self, struct_name, method):
        """(Implementation detail)"""
        # 関数名を生成
        func_name = f"{struct_name}_{method.name}"
        
        # 戻り値型
        return_type = self._type_to_c(method.return_type)
        
        # 第1引数が self かどうか確認
        if method.params and method.params[0].name == "self":
            # 第1引数の型を struct_name (値渡し) に設定
            self_type = struct_name
            other_params = method.params[1:]
            param_strs = [f"{self_type} self"]
            param_strs.extend(f"{self._type_to_c(p.type_node)} {p.name}" for p in other_params)
        else:
            # self がない場合は全パラメータをそのまま使用
            param_strs = [f"{self._type_to_c(p.type_node)} {p.name}" for p in method.params]
        
        params_str = ", ".join(param_strs)
        
        # 本体を生成
        self._emit(f"{return_type} {func_name}({params_str}) {{")
        self.indent_level += 1
        
        # 各ステートメントを生成
        for stmt in method.body.statements:
            self._generate_statement(stmt)
        
        self.indent_level -= 1
        self._emit("}")
        self._emit("")
    
    def _emit_result_typedefs(self):
        """(Implementation detail)"""
        if not self.result_type_registry:
            return
        self._emit("// ===== Result<T,E> type structs =====")
        for (ok_c, err_c, struct_name) in sorted(self.result_type_registry):
            self._emit(f"typedef struct {{")
            self._emit(f"    int is_ok;")
            self._emit(f"    union {{ {ok_c} ok_val; {err_c} err_val; }} data;")
            self._emit(f"}} {struct_name};")
        self._emit("")

    def _type_to_c(self, type_node) -> str:
        """(Implementation detail)"""
        if not type_node:
            return "void"
        
        # 組み込み型マッピング
        type_map = {
            "i8": "int8_t",
            "i16": "int16_t",
            "i32": "int32_t",
            "i64": "int64_t",
            "u8": "uint8_t",
            "u16": "uint16_t",
            "u32": "uint32_t",
            "u64": "uint64_t",
            "f32": "float",
            "f64": "double",
            "string": "MrylString",
            "bool": "int",
            "int": "int32_t",
            "void": "void",
        }
        
        base_type = type_map.get(type_node.name, type_node.name)
        
        # Future<T> は MrylTask* に変換
        if type_node.name == "Future":
            return "MrylTask*"
        
        # Result<T,E> は MrylResult_T_E に変換
        if type_node.name == "Result":
            if type_node.type_args and len(type_node.type_args) == 2:
                ok_c = self._type_to_c(type_node.type_args[0])
                err_c = self._type_to_c(type_node.type_args[1])
                struct_name = f"MrylResult_{ok_c}_{err_c}".replace("*", "Ptr").replace(" ", "_")
                self.result_type_registry.add((ok_c, err_c, struct_name))
                return struct_name
            return "MrylResult_i32_i32"  # fallback

        # fn type (lambda function pointer) は void* に変換
        if type_node.name == "fn":
            return "void*"
        
        # 配列型の処理
        if type_node.array_size:
            return f"{base_type}[{type_node.array_size}]"
        
        return base_type
    
    def _type_to_c_base(self, type_name: str) -> str:
        """(Implementation detail)"""
        type_map = {
            "i8": "int8_t",
            "i16": "int16_t",
            "i32": "int32_t",
            "i64": "int64_t",
            "u8": "uint8_t",
            "u16": "uint16_t",
            "u32": "uint32_t",
            "u64": "uint64_t",
            "f32": "float",
            "f64": "double",
            "string": "MrylString",
            "bool": "int",
            "int": "int32_t",
            "void": "void",
        }
        return type_map.get(type_name, type_name)
    
    @staticmethod
    def _c_escape(s: str) -> str:
        """Escape a Python string for use in a C string literal."""
        return (
            s
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
            .replace("\r", "\\r")
        )

    def _emit(self, line: str = ""):
        """(Implementation detail)"""
        if line:
            self.code.append("    " * self.indent_level + line)
        else:
            self.code.append("")
    
    def _register_generic_instantiation(self, func_name: str, type_args):
        """(Implementation detail)"""
        func = self.program_functions.get(func_name)
        if not func or not func.type_params:
            return
        
        type_args_tuple = tuple(str(t) for t in type_args)
        key = (func_name, type_args_tuple)
        
        # 既に登録済みならスキップ
        if key in self.generic_instantiations:
            return
        
        # 型引数を用いて関数を特殊化して登録
        subst = dict(zip(func.type_params, type_args))
        instantiated_func = self._substitute_function(func, subst, type_args_tuple)
        self.generic_instantiations[key] = instantiated_func
    
    def _substitute_function(self, func: FunctionDecl, subst: dict, type_args_tuple):
        """(Implementation detail)"""
        # 特殊化関数名を生成
        new_name = self._get_instantiated_func_name(func.name, type_args_tuple)
        
        # パラメータの型を特殊化
        new_params = []
        for param in func.params:
            new_type = self._substitute_type_node(param.type_node, subst)
            new_params.append(Param(param.name, new_type, param.line, param.column))
        
        # 戻り値型を特殊化
        new_return_type = self._substitute_type_node(func.return_type, subst) if func.return_type else None
        
        # 特殊化した FunctionDecl を生成 (is_async を正しく引き継ぐ)
        new_func = FunctionDecl(new_name, new_params, new_return_type, func.body, [], func.is_async, func.line, func.column)
        return new_func
    
    def _substitute_type_node(self, type_node, subst):
        """(Implementation detail)"""
        if not type_node:
            return type_node
        
        # 型変数の置換
        if type_node.name in subst:
            replacement = subst[type_node.name]
            
            # TypeNode インスタンスならそのまま使用
            if isinstance(replacement, TypeNode):
                return replacement
            else:
                # 文字列の場合は TypeNode でラップ
                return TypeNode(str(replacement).split('[')[0])  # 文字列から TypeNode を生成
        
        
        if type_node.array_size:
            return TypeNode(type_node.name, type_node.array_size, None)
        
        # 型引数がある場合は再帰的に置換
        if type_node.type_args:
            new_type_args = [self._substitute_type_node(arg, subst) for arg in type_node.type_args]
            return TypeNode(type_node.name, type_node.array_size, new_type_args)
        
        return type_node
    
    def _get_instantiated_func_name(self, func_name: str, type_args_tuple) -> str:
        """(Implementation detail)"""
        # 型引数を文字列化して末尾に付加
        type_str = "_".join(str(t).replace("<", "_").replace(">", "").replace(",", "_") for t in type_args_tuple)
        return f"{func_name}_{type_str}"
    
    def _infer_generic_type_args(self, func: FunctionDecl, arg_exprs):
        """(Implementation detail)"""
        type_args = [None] * len(func.type_params)
        param_type_map = {param.name: param.type_node for param in func.params}
        
        for i, arg_expr in enumerate(arg_exprs):
            if i >= len(func.params):
                break
            
            param_type = func.params[i].type_node
            arg_type = self._infer_expr_type(arg_expr)
            
            # 型パラメータと引数型を対応付け
            if param_type.name in func.type_params:
                param_idx = func.type_params.index(param_type.name)
                if type_args[param_idx] is None:
                    type_args[param_idx] = arg_type
        
        return [t if t else "int32_t" for t in type_args]
    
    def _infer_expr_type(self, expr):
        """(Implementation detail)"""
        expr_class = expr.__class__.__name__
        
        if expr_class == "NumberLiteral":
            if expr.explicit_type:
                return expr.explicit_type
            return "i32"
        
        if expr_class == "FloatLiteral":
            if expr.explicit_type:
                return expr.explicit_type
            return "f64"
        
        if expr_class == "StringLiteral":
            return "string"
        
        if expr_class == "BoolLiteral":
            return "bool"
        
        if expr_class == "VarRef":
            # スコープを逆順に検索
            for env_dict in reversed(self.env):
                if expr.name in env_dict:
                    return env_dict[expr.name]
            return "i32"  # デフォルト型
        
        if expr_class == "BinaryOp":
            # BinaryOp は左辺の型を返す
            return self._infer_expr_type(expr.left)

        if expr_class == "FunctionCall":
            if expr.name in ("Ok", "Err"):
                return "Result"
            fn = self.program_functions.get(expr.name)
            if fn and fn.return_type:
                if fn.return_type.name == "Result":
                    return "Result"
                return fn.return_type.name
            return "i32"

        if expr_class == "MethodCall":
            # Result 型メソッドの戻り値型を解決
            obj_t = self._infer_expr_type(expr.obj)
            if obj_t == "Result":
                if expr.method in ("is_ok", "is_err"): return "bool"
                if expr.method in ("try", "unwrap", "unwrap_err", "unwrap_or", "err"): return "i32"
            return "i32"

        if expr_class == "MatchExpr":
            for arm in expr.arms:
                if isinstance(arm.pattern, BindingPattern) and arm.pattern.name == "_":
                    continue
                scope = self._pattern_binding_types(arm.pattern)
                self.env.append(scope)
                t = self._infer_expr_type(arm.body)
                self.env.pop()
                if t not in ("any", "i32"):
                    return t
            # fallback: try with i32-default scope
            for arm in expr.arms:
                if isinstance(arm.pattern, BindingPattern) and arm.pattern.name == "_":
                    continue
                scope = self._pattern_binding_types(arm.pattern)
                self.env.append(scope)
                t = self._infer_expr_type(arm.body)
                self.env.pop()
                return t
            return "i32"

        # その他はデフォルトで i32
        return "i32"
    
    def _scan_generic_calls(self, block):
        """(Implementation detail)"""
        if not block or not hasattr(block, 'statements'):
            return
        
        for stmt in block.statements:
            self._scan_statement_for_generic_calls(stmt)
    
    def _scan_statement_for_generic_calls(self, stmt):
        """(Implementation detail)"""
        stmt_class = stmt.__class__.__name__
        
        if stmt_class == "ExprStmt":
            self._scan_expr_for_generic_calls(stmt.expr)
        elif stmt_class == "LetDecl":
            if stmt.init_expr:
                self._scan_expr_for_generic_calls(stmt.init_expr)
        elif stmt_class == "IfStmt":
            self._scan_expr_for_generic_calls(stmt.condition)
            self._scan_generic_calls(stmt.then_block)
            if stmt.else_block:
                self._scan_generic_calls(stmt.else_block)
        elif stmt_class == "WhileStmt":
            self._scan_expr_for_generic_calls(stmt.condition)
            self._scan_generic_calls(stmt.body)
        elif stmt_class == "ForStmt":
            self._scan_expr_for_generic_calls(stmt.iterable)
            if stmt.condition:
                self._scan_expr_for_generic_calls(stmt.condition)
            if stmt.update:
                self._scan_expr_for_generic_calls(stmt.update)
            self._scan_generic_calls(stmt.body)
        elif stmt_class == "ReturnStmt":
            if stmt.expr:
                self._scan_expr_for_generic_calls(stmt.expr)
        elif stmt_class == "Block":
            self._scan_generic_calls(stmt)
    
    def _scan_expr_for_generic_calls(self, expr):
        """(Implementation detail)"""
        if not expr:
            return
        
        expr_class = expr.__class__.__name__
        
        if expr_class == "FunctionCall":
            func = self.program_functions.get(expr.name)
            if func and func.type_params:
                # ジェネリック呼び出しを登録
                type_args = self._infer_generic_type_args(func, expr.args)
                self._register_generic_instantiation(expr.name, type_args)
            # 引数も再帰的にスキャン（ネストしたジェネリック呼び出しに対応）
            for arg in expr.args:
                self._scan_expr_for_generic_calls(arg)
        elif expr_class == "BinaryOp":
            self._scan_expr_for_generic_calls(expr.left)
            self._scan_expr_for_generic_calls(expr.right)
        elif expr_class == "UnaryOp":
            self._scan_expr_for_generic_calls(expr.operand)
        elif expr_class == "StructInit":
            if hasattr(expr, 'fields'):
                for _, value_expr in expr.fields:
                    self._scan_expr_for_generic_calls(value_expr)
        elif expr_class == "ArrayLiteral":
            if hasattr(expr, 'elements'):
                for elem in expr.elements:
                    self._scan_expr_for_generic_calls(elem)
        elif expr_class == "MethodCall":
            self._scan_expr_for_generic_calls(expr.obj)
            for arg in expr.args:
                self._scan_expr_for_generic_calls(arg)
        elif expr_class == "ArrayAccess":
            self._scan_expr_for_generic_calls(expr.array)
            self._scan_expr_for_generic_calls(expr.index)
