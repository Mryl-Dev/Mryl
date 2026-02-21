from Ast import *
from MrylError import *

# 数値型のセット（型推論に使用）
INTEGER_TYPES = {"i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64"}
FLOAT_TYPES = {"f32", "f64"}
NUMERIC_TYPES = INTEGER_TYPES | FLOAT_TYPES

class TypeChecker:
    def __init__(self):
        self.structs = {}     # name -> StructDecl
        self.functions = {}   # name -> FunctionDecl
        self.enums = {}       # name -> EnumDecl
        self.env = []         # スコープのスタック（辞書のリスト）
        self.const_table = {} # Const values (name -> value)

        # ---- 組み込み関数 ----
        # print(x)
        self.functions["print"] = FunctionDecl(
            name="print",
            params=[Param("x", TypeNode("any"))],
            return_type=TypeNode("int"),
            body=None,
            type_params=[] # 念のためジェネリックパラメータを明示的クリア
        )

        # println(x)
        self.functions["println"] = FunctionDecl(
            name="println",
            params=[Param("x", TypeNode("any"))],
            return_type=TypeNode("int"),
            body=None,
            type_params=[] # 念のためジェネリックパラメータを明示的クリア
        )

        # to_string(x)
        self.functions["to_string"] = FunctionDecl(
            name="to_string",
            params=[Param("x", TypeNode("int"))],  # int → string
            return_type=TypeNode("string"),
            body=None,
            type_params=[] # 念のためジェネリックパラメータを明示的クリア
        )

    # ============================================
    # 型比較（ジェネリクス対応）
    # ============================================
    def types_equal(self, a: TypeNode, b: TypeNode) -> bool:
        # ★ デバッグ：TypeNode の中身を全部出す
        # if not isinstance(a.type_args, list) or not isinstance(b.type_args, list):
        #     print("DEBUG TYPE ERROR:")
        #     print("  A:", a, " array_size=", a.array_size, " type_args=", a.type_args)
        #     print("  B:", b, " array_size=", b.array_size, " type_args=", b.type_args)

        # any は何とでも一致する
        if a.name == "any" or b.name == "any":
            return True

        # Result 型: Ok/Err はパラメータなしの Result を返すため基底型名だけで一致
        if a.name == "Result" and b.name == "Result":
            return True

        # 配列型の比較
        if a.array_size is not None or b.array_size is not None:
            # 動的配列(array_size=-1)は同名の固定長配列リテラルとも一致する
            a_dyn = (a.array_size == -1)
            b_dyn = (b.array_size == -1)
            if a.name != b.name:
                return False
            if a_dyn or b_dyn:
                return True  # T[] matches T[N] for any N, and T[] matches T[]
            return a.array_size == b.array_size

        # 通常の型比較
        if a.name != b.name:
            return False
        if len(a.type_args) != len(b.type_args):
            return False
        for x, y in zip(a.type_args, b.type_args):
            if not self.types_equal(x, y):
                return False
        return True

    # ============================================
    # 型置換（T → int など）
    # ============================================
    def substitute_type(self, t: TypeNode, subst: dict):
        # T → int のような置換
        if t.name in subst:
            return subst[t.name]

        # 配列
        if t.array_size is not None:
            return TypeNode(t.name, array_size=t.array_size)

        # ジェネリクス
        if t.type_args:
            new_args = [self.substitute_type(a, subst) for a in t.type_args]
            return TypeNode(t.name, type_args=new_args)

        return TypeNode(t.name)

    # ============================================
    # 型昇格（数値型互換性）
    # ============================================
    def numeric_type_rank(self, type_name: str) -> int:
        """数値型のランクを返す。大きいほど「大きい型」。
        同じカテゴリ内でのみ昇格可能。"""
        # 符号あり整数
        if type_name == "i8":   return 1
        if type_name == "i16":  return 2
        if type_name == "i32":  return 3
        if type_name == "i64":  return 4
        # 符号なし整数
        if type_name == "u8":   return 5
        if type_name == "u16":  return 6
        if type_name == "u32":  return 7
        if type_name == "u64":  return 8
        # 浮動小数点
        if type_name == "f32":  return 9
        if type_name == "f64":  return 10
        return -1  # 数値型ではない

    def is_signed_int(self, type_name: str) -> bool:
        return type_name in ("i8", "i16", "i32", "i64")
    
    def is_unsigned_int(self, type_name: str) -> bool:
        return type_name in ("u8", "u16", "u32", "u64")

    def find_common_numeric_type(self, a: TypeNode, b: TypeNode) -> TypeNode:
        """2つの数値型の共通上位型を見つける。
        昇格ルール:
        - 符号あり整数 + 符号あり整数 = より大きい符号あり整数
        - 符号なし整数 + 符号なし整数 = より大きい符号なし整数
        - 浮動小数点 + 浮動小数点 = より大きい浮動小数点
        - 整数 + 浮動小数点 = 浮動小数点
        """
        a_name = a.name
        b_name = b.name

        # 同じ型ならそのまま
        if a_name == b_name:
            return a

        # どちらかが浮動小数点なら浮動小数点に統一
        if self.is_float_type(a_name) or self.is_float_type(b_name):
            # f32 + f64 = f64
            if self.is_float_type(a_name) and self.is_float_type(b_name):
                rank_a = self.numeric_type_rank(a_name)
                rank_b = self.numeric_type_rank(b_name)
                return a if rank_a >= rank_b else b
            # 整数 + 浮動小数点 = 浮動小数点（f64）
            return TypeNode("f64")

        # 両方とも整数型
        # 符号なし + 符号なし
        if self.is_unsigned_int(a_name) and self.is_unsigned_int(b_name):
            rank_a = self.numeric_type_rank(a_name)
            rank_b = self.numeric_type_rank(b_name)
            larger = a_name if rank_a >= rank_b else b_name
            return TypeNode(larger)

        # 符号あり + 符号あり
        if self.is_signed_int(a_name) and self.is_signed_int(b_name):
            rank_a = self.numeric_type_rank(a_name)
            rank_b = self.numeric_type_rank(b_name)
            larger = a_name if rank_a >= rank_b else b_name
            return TypeNode(larger)

        # 符号あり + 符号なし → 昇格不可（エラー）
        raise TypeError_(f"Cannot find common type for {a_name} and {b_name}")

    # ============================================
    # エントリポイント
    # ============================================
    def check_program(self, program: Program):
        # Process const declarations first
        for const_decl in program.consts:
            self.check_const_decl(const_decl)

        # 構造体と関数を登録
        for s in program.structs:
            self.structs[s.name] = s

        # enum を登録
        for e in program.enums:
            self.enums[e.name] = e

        for f in program.functions:
            self.functions[f.name] = f

        # main があるかチェック
        if "main" not in self.functions:
            raise TypeError_("main() function not found", program)

        # 各構造体のメソッドをチェック
        for s in program.structs:
            for method in s.methods:
                self.check_method(s, method)

        # 各関数をチェック
        for f in program.functions:
            self.check_function(f)

    # ============================================
    # メソッド
    # ============================================
    def check_method(self, struct: StructDecl, method: MethodDecl):
        self.env = [{}]

        # self パラメータをリソルブ（struct 型）
        method.params[0].type_node = TypeNode(struct.name)
        
        # パラメータを登録
        for p in method.params:
            self.env[-1][p.name] = p.type_node

        # メソッド本体をチェック
        self.check_block(method.body, method.return_type)

    # ============================================
    # 関数
    # ============================================
    def check_function(self, func: FunctionDecl):
        # ジェネリック関数の場合、本体チェックは呼び出し時（instantiation）に行うため、
        # ここではスキップして、呼び出し時の詳細なチェックに任せる
        if func.type_params:
            # ジェネリック関数はスキップ
            return
        
        self.env = [{}]

        # パラメータを登録
        for p in func.params:
            self.env[-1][p.name] = p.type_node

        # 関数本体をチェック
        self.check_block(func.body, func.return_type)

    # ============================================
    # ブロック
    # ============================================
    def check_block(self, block: Block, expected_return_type):
        self.env.append({})

        for stmt in block.statements:
            self.check_statement(stmt, expected_return_type)

        self.env.pop()

    # ============================================
    # 文
    # ============================================
    def check_statement(self, stmt, expected_return_type):
        if isinstance(stmt, LetDecl):
            self.check_let(stmt)

        elif isinstance(stmt, Assignment):
            self.check_assignment(stmt)

        elif isinstance(stmt, IfStmt):
            self.check_if(stmt, expected_return_type)

        elif isinstance(stmt, WhileStmt):
            self.check_while(stmt, expected_return_type)

        elif isinstance(stmt, ForStmt):
            self.check_for(stmt, expected_return_type)

        elif isinstance(stmt, ReturnStmt):
            self.check_return(stmt, expected_return_type)

        elif isinstance(stmt, BreakStmt):
            pass  # 型チェック不要

        elif isinstance(stmt, ContinueStmt):
            pass  # 型チェック不要

        elif isinstance(stmt, ExprStmt):
            self.check_expr(stmt.expr)
        
        elif isinstance(stmt, ConditionalBlock):
            self.check_conditional_block(stmt, expected_return_type)

        else:
            raise TypeError_(f"Unknown statement type: {stmt}", stmt)

    # ============================================
    # let
    # ============================================
    def check_let(self, stmt: LetDecl):
        if stmt.type_node is None:
            # 型推論
            if stmt.init_expr is None:
                raise TypeError_(f"Cannot infer type of '{stmt.name}' without initializer", stmt)
            inferred = self.check_expr(stmt.init_expr)
            stmt.type_node = inferred
        else:
            # 動的配列の空リテラル初期化: let arr: T[] = [] → 型チェックをスキップ
            if (stmt.type_node.array_size == -1 and
                    stmt.init_expr is not None and
                    stmt.init_expr.__class__.__name__ == "ArrayLiteral" and
                    len(stmt.init_expr.elements) == 0):
                self.env[-1][stmt.name] = stmt.type_node
                return
            expr_type = self.check_expr(stmt.init_expr)
            if not self.types_equal(expr_type, stmt.type_node):
                raise TypeError_(
                    f"Type mismatch in let {stmt.name}: expected {stmt.type_node}, got {expr_type}",
                    stmt.init_expr
                )

        # 変数をスコープに登録
        self.env[-1][stmt.name] = stmt.type_node

    # ============================================
    # const
    # ============================================
    def check_const_decl(self, stmt: ConstDecl):
        """Check const declaration and evaluate its value"""
        try:
            expr_type = self.check_expr(stmt.init_expr)
            # Store const value with its type
            self.const_table[stmt.name] = {
                'type': expr_type,
                'expr': stmt.init_expr
            }
        except Exception as e:
            raise TypeError_(f"Error in const declaration '{stmt.name}': {e}", stmt)

    # ============================================
    # conditional block
    # ============================================
    def check_conditional_block(self, stmt: ConditionalBlock, expected_return_type):
        """Check conditional compilation block"""
        # For conditional blocks, we check both branches
        # (The actual condition evaluation happens at runtime/code gen)
        self.check_block(stmt.then_block, expected_return_type)
        
        if stmt.else_block is not None:
            self.check_block(stmt.else_block, expected_return_type)

    # ============================================
    # 代入
    # ============================================
    def check_assignment(self, stmt: Assignment):
        target_type = self.check_expr(stmt.target)
        expr_type = self.check_expr(stmt.expr)

        if not self.types_equal(target_type, expr_type):
            raise TypeError_(
                f"Type mismatch in assignment: {target_type} = {expr_type}",
                stmt
            )

    # ============================================
    # if
    # ============================================
    def check_if(self, stmt: IfStmt, expected_return_type):
        cond_type = self.check_expr(stmt.condition)
        if cond_type.name != "bool":
            raise TypeError_("Condition of if must be bool", stmt.condition)

        # then は必ず Block
        self.check_block(stmt.then_block, expected_return_type)

        # else は Block または IfStmt
        if stmt.else_block:
            if isinstance(stmt.else_block, IfStmt):
                self.check_if(stmt.else_block, expected_return_type)
            else:
                self.check_block(stmt.else_block, expected_return_type)

    # ============================================
    # while
    # ============================================
    def check_while(self, stmt: WhileStmt, expected_return_type):
        cond_type = self.check_expr(stmt.condition)
        if cond_type.name != "bool":
            raise TypeError_("Condition of while must be bool", stmt.condition)

        self.check_block(stmt.body, expected_return_type)

    # ============================================
    # for loops
    # ============================================
    def check_for(self, stmt: ForStmt, expected_return_type):
        if stmt.is_c_style:
            # C-style: for (let i = 0; i < 10; i++)
            # Register loop variable
            init_type = self.check_expr(stmt.iterable)  # init_expr stored in iterable
            self.env[-1][stmt.variable] = init_type
            
            # Check condition is bool
            cond_type = self.check_expr(stmt.condition)
            if cond_type.name != "bool":
                raise TypeError_("Loop condition must be bool", stmt.condition)
            
            # Check update expression (could be assignment or ++/--)
            if isinstance(stmt.update, Assignment):
                self.check_assignment(stmt.update)
            else:
                self.check_expr(stmt.update)
        else:
            # Rust-style: for x in iterable
            iterable_type = self.check_expr(stmt.iterable)
            
            # Determine element type
            if isinstance(stmt.iterable, Range):
                # Range<start, end> yields integers
                element_type = TypeNode("i32")  # Default for ranges
            elif iterable_type.array_size is not None:
                # Array type [T; N]
                element_type = TypeNode(iterable_type.name, array_size=None, type_args=iterable_type.type_args)
            else:
                raise TypeError_(f"Cannot iterate over {iterable_type}", stmt.iterable)
            
            # Register loop variable with element type
            self.env[-1][stmt.variable] = element_type
        
        # Check loop body
        self.check_block(stmt.body, expected_return_type)
        
        # Remove loop variable from scope
        if stmt.variable in self.env[-1]:
            del self.env[-1][stmt.variable]

    # ============================================
    # return
    # ============================================
    def check_return(self, stmt: ReturnStmt, expected_return_type):
        expr_type = self.check_expr(stmt.expr)
        if expected_return_type is not None and not self.types_equal(expr_type, expected_return_type):
            raise TypeError_(
                f"Return type mismatch: expected {expected_return_type}, got {expr_type}",
                stmt.expr
            )

    # ============================================
    # 式
    # ============================================
    def check_expr(self, expr):
        if isinstance(expr, NumberLiteral):
            # 明示的な型があれば使用（i32, u8 など）
            if hasattr(expr, 'explicit_type') and expr.explicit_type:
                return TypeNode(expr.explicit_type)
            # デフォルトは i32
            return TypeNode("i32")

        if isinstance(expr, FloatLiteral):
            # 明示的な型があれば使用（f32, f64 など）
            if hasattr(expr, 'explicit_type') and expr.explicit_type:
                return TypeNode(expr.explicit_type)
            # デフォルトは f64
            return TypeNode("f64")

        if isinstance(expr, StringLiteral):
            return TypeNode("string")

        if isinstance(expr, BoolLiteral):
            return TypeNode("bool")

        if isinstance(expr, VarRef):
            return self.lookup_var(expr.name, expr)

        if isinstance(expr, BinaryOp):
            return self.check_binary(expr)

        if isinstance(expr, UnaryOp):
            return self.check_unary(expr)

        if isinstance(expr, ArrayAccess):
            return self.check_array_access(expr)

        if isinstance(expr, StructAccess):
            return self.check_struct_access(expr)

        if isinstance(expr, FunctionCall):
            return self.check_call(expr)

        if isinstance(expr, MethodCall):
            return self.check_method_call(expr)

        if isinstance(expr, StructInit):
            return self.check_struct_init(expr)

        if isinstance(expr, ArrayLiteral):
            return self.check_array_literal(expr)

        if isinstance(expr, Range):
            # Check that both start and end are numeric types
            start_type = self.check_expr(expr.start)
            end_type = self.check_expr(expr.end)
            
            if not self.is_numeric_type(start_type.name):
                raise TypeError_(f"Range start must be numeric, got {start_type}", expr.start)
            if not self.is_numeric_type(end_type.name):
                raise TypeError_(f"Range end must be numeric, got {end_type}", expr.end)
            
            # Both must be the same numeric type
            if not self.types_equal(start_type, end_type):
                raise TypeError_(f"Range bounds must be same type: {start_type} vs {end_type}", expr)
            
            # Return a Range type (represented as TypeNode with a special name)
            return TypeNode("Range", type_args=[start_type])
        if isinstance(expr, AwaitExpr):
            return self.check_await(expr)
        if isinstance(expr, Lambda):
            return self.check_lambda(expr)

        if isinstance(expr, AwaitExpr):
            return self.check_await(expr)

        if isinstance(expr, EnumVariantExpr):
            # Return the enum type; just trust the name for now
            return TypeNode(expr.enum_name)

        if isinstance(expr, MatchExpr):
            self.check_expr(expr.scrutinee)
            arm_types = []
            for arm in expr.arms:
                scope = self._pattern_bindings_scope(arm.pattern)
                self.env.append(scope)
                try:
                    t = self.check_expr(arm.body)
                except Exception:
                    t = TypeNode("any")
                self.env.pop()
                arm_types.append(t)
            return arm_types[0] if arm_types else TypeNode("void")

        if isinstance(expr, BlockExpr):
            # ブロック式: 各ステートメントを型チェック後、result_expr の型を返す
            self.env.append({})
            try:
                for stmt in expr.stmts:
                    self.check_statement(stmt, TypeNode("any"))
                ret = TypeNode("any")
                if expr.result_expr is not None:
                    ret = self.check_expr(expr.result_expr)
            finally:
                self.env.pop()
            return ret

        raise TypeError_(f"Unknown expression type: {expr}", expr)

    def _pattern_bindings_scope(self, pattern):
        """Return a scope dict with binding names introduced by the pattern."""
        if isinstance(pattern, BindingPattern):
            return {pattern.name: TypeNode("any")}
        if isinstance(pattern, EnumPattern):
            return {name: TypeNode("any") for name in pattern.bindings}
        if isinstance(pattern, StructPattern):
            return {f: TypeNode("any") for f in pattern.fields}
        return {}

    # ============================================
    # lookup_var
    # ============================================
    def lookup_var(self, name, expr):
        # Check local scopes first
        for scope in reversed(self.env):
            if name in scope:
                return scope[name]
        
        # Check const table
        if name in self.const_table:
            return self.const_table[name]['type']
        
        raise TypeError_(f"Undefined variable: {name}", expr)

    # ============================================
    # Lambda
    # ============================================
    def check_lambda(self, expr: Lambda):
        """Type-check a lambda expression, returning TypeNode("fn")."""
        # Push a new scope for the lambda's parameters
        self.env.append({})
        param_types = []
        for p in expr.params:
            # Default to "any" when no annotation is provided
            ptype = p.type_node if p.type_node is not None else TypeNode("any")
            self.env[-1][p.name] = ptype
            param_types.append(ptype)

        # Check body
        if isinstance(expr.body, Block):
            # For block body, check each statement; return type not enforced here
            for stmt in expr.body.statements:
                try:
                    self.check_statement(stmt, None)
                except Exception:
                    pass
            return_type = TypeNode("void")
        else:
            try:
                return_type = self.check_expr(expr.body)
            except Exception:
                return_type = TypeNode("any")

        self.env.pop()

        # Store inferred return type on the Lambda node for codegen
        expr.inferred_return_type = return_type
        # Return a function type: fn<(param_types) -> return_type>
        return TypeNode("fn", type_args=param_types + [return_type])

    # ============================================
    # AwaitExpr
    # ============================================
    def check_await(self, expr: AwaitExpr):
        """Type-check an await expression."""
        handle_type = self.check_expr(expr.expr)
        # handle_type should be Future<T>; unwrap T
        if handle_type.name == "Future" and handle_type.type_args:
            return handle_type.type_args[0]
        # For void async functions, return void
        return TypeNode("void")

    # ============================================
    # Helper: 型分類
    # ============================================
    def is_integer_type(self, type_name: str) -> bool:
        return type_name in INTEGER_TYPES or type_name == "int"
    
    def is_float_type(self, type_name: str) -> bool:
        return type_name in FLOAT_TYPES
    
    def is_numeric_type(self, type_name: str) -> bool:
        return self.is_integer_type(type_name) or self.is_float_type(type_name)

    # ============================================
    # Unary
    # ============================================
    def check_unary(self, expr: UnaryOp):
        operand = self.check_expr(expr.operand)

        if expr.op == "!":
            # Logical NOT - works on bool or numeric
            if not (operand.name == "bool" or self.is_numeric_type(operand.name)):
                raise TypeError_("Unary ! requires bool or numeric type", expr)
            return TypeNode("bool")

        if expr.op == "~":
            # Bitwise NOT - requires numeric type
            if not self.is_numeric_type(operand.name):
                raise TypeError_("Unary ~ requires numeric type", expr)
            return operand

        if expr.op == "-":
            # 数値型なら OK
            if not self.is_numeric_type(operand.name):
                raise TypeError_("Unary - requires numeric type", expr)
            return operand
        
        if expr.op == "+":
            # Unary plus - requires numeric type
            if not self.is_numeric_type(operand.name):
                raise TypeError_("Unary + requires numeric type", expr)
            return operand

        if expr.op in ("++", "--"):
            # Pre-increment/decrement: ++i, --i
            if not self.is_numeric_type(operand.name):
                raise TypeError_(f"Unary {expr.op} requires numeric type", expr)
            return operand

        if expr.op in ("post++", "post--"):
            # Post-increment/decrement: i++, i--
            if not self.is_numeric_type(operand.name):
                raise TypeError_(f"Postfix {expr.op} requires numeric type", expr)
            return operand

        return operand

    # ============================================
    # Binary
    # ============================================
    def check_binary(self, expr: BinaryOp):
        left = self.check_expr(expr.left)
        right = self.check_expr(expr.right)
        op = expr.op

        # 算術演算（+, -, *, /, %）
        if op in ("+", "-", "*", "/", "%"):
            # 両辺が同じ型ならOK
            if self.types_equal(left, right):
                # 数値型なら数値型を返す、文字列なら文字列を返す
                if self.is_numeric_type(left.name) or left.name == "string":
                    return left
                raise TypeError_(f"Invalid operands for {op}", expr)
            
            # 数値型の昇格を試みる
            if self.is_numeric_type(left.name) and self.is_numeric_type(right.name):
                common = self.find_common_numeric_type(left, right)
                if common:
                    return common
                else:
                    raise TypeError_(
                        f"Binary {op}: incompatible numeric types. got {left.name} and {right.name}",
                        expr
                    )
            
            # 数値型以外の異型混在はエラー
            if self.is_numeric_type(left.name) or self.is_numeric_type(right.name):
                raise TypeError_(
                    f"Binary {op}: operands must have compatible types. got {left.name} and {right.name}",
                    expr
                )
            
            raise TypeError_(f"Invalid operands for {op}", expr)

        # 比較演算（<, <=, >, >=）
        if op in ("<", "<=", ">", ">="):
            # 両辺が数値型で同じか昇格可能ならOK
            if self.is_numeric_type(left.name) and self.is_numeric_type(right.name):
                if self.types_equal(left, right):
                    return TypeNode("bool")
                common = self.find_common_numeric_type(left, right)
                if common:
                    return TypeNode("bool")
            raise TypeError_(f"Comparison {op}: operands must be same or compatible numeric types", expr)

        # 等価演算（==, !=）
        if op in ("==", "!="):
            # 両辺が同じ型か、数値型で昇格可能ならOK
            if self.types_equal(left, right):
                return TypeNode("bool")
            if self.is_numeric_type(left.name) and self.is_numeric_type(right.name):
                common = self.find_common_numeric_type(left, right)
                if common:
                    return TypeNode("bool")
            raise TypeError_(f"Equality {op}: operands must have compatible types", expr)

        # 論理演算（&&, ||）
        if op in ("&&", "||"):
            # 両辺がboolかint型（パイソン風に）ならOK
            if (self.is_numeric_type(left.name) or left.name == "bool") and \
               (self.is_numeric_type(right.name) or right.name == "bool"):
                return TypeNode("bool")
            raise TypeError_(f"Logical {op}: operands must be numeric or bool types", expr)

        # ビット演算（&, |, ^, <<, >>）
        if op in ("&", "|", "^", "<<", ">>"):
            # 両辺が整数型ならOK
            if self.is_numeric_type(left.name) and self.is_numeric_type(right.name):
                if self.types_equal(left, right):
                    return left
                common = self.find_common_numeric_type(left, right)
                if common:
                    return common
            raise TypeError_(f"Bitwise {op}: operands must be compatible numeric types", expr)

        raise TypeError_(f"Unknown operator {op}", expr)

    # ============================================
    # StructInit（ジェネリクス対応）
    # ============================================
    def check_struct_init(self, expr: StructInit):
        struct = self.structs.get(expr.struct_name)
        if not struct:
            raise TypeError_(f"Undefined struct: {expr.struct_name}", expr)

        # 型パラメータ数チェック
        if len(expr.type_args) != len(struct.type_params):
            raise TypeError_(
                f"Struct {expr.struct_name} expects {len(struct.type_params)} type args, got {len(expr.type_args)}",
                expr
            )

        # T → int のような置換マップ作成
        subst = {}
        for param, arg in zip(struct.type_params, expr.type_args):
            # arg が文字列の場合は TypeNode に変換
            arg_node = TypeNode(arg) if isinstance(arg, str) else arg
            subst[param] = arg_node

        # フィールドチェック
        for field in struct.fields:
            expected = self.substitute_type(field.type_node, subst)

            found = False
            for name, value_expr in expr.fields:
                if name == field.name:
                    found = True
                    value_type = self.check_expr(value_expr)
                    if not self.types_equal(value_type, expected):
                        raise TypeError_(
                            f"Field {expr.struct_name}.{name} type mismatch: expected {expected}, got {value_type}",
                            value_expr
                        )
            if not found:
                raise TypeError_(f"Missing field {field.name} in struct init", expr)

        return TypeNode(expr.struct_name, type_args=expr.type_args)

    # ============================================
    # StructAccess（ジェネリクス対応）
    # ============================================
    def check_struct_access(self, expr: StructAccess):
        obj_type = self.check_expr(expr.obj)
        struct = self.structs.get(obj_type.name)

        if not struct:
            raise TypeError_(f"{obj_type.name} is not a struct", expr.obj)

        # ジェネリクス置換マップ
        subst = {}
        for param, arg in zip(struct.type_params, obj_type.type_args):
            subst[param] = arg

        for field in struct.fields:
            if field.name == expr.field:
                return self.substitute_type(field.type_node, subst)

        raise TypeError_(f"Struct {obj_type.name} has no field {expr.field}", expr)

    # ============================================
    # MethodCall
    # ============================================
    def check_method_call(self, expr: MethodCall):
        # オブジェクトの型を取得
        obj_type = self.check_expr(expr.obj)

        # 動的配列(T[])のメソッド処理
        if obj_type.array_size == -1:
            elem_type = TypeNode(obj_type.name)
            if expr.method == 'push':
                return TypeNode('void')
            elif expr.method == 'pop':
                return elem_type
            elif expr.method == 'len':
                return TypeNode('i32')
            elif expr.method == 'is_empty':
                return TypeNode('bool')
            elif expr.method == 'remove':
                return elem_type
            elif expr.method == 'insert':
                return TypeNode('void')
            else:
                raise TypeError_(f"Dynamic array has no method '{expr.method}'", expr)

        # Result<T,E> のメソッド処理
        if obj_type.name == "Result":
            if expr.method in ("is_ok", "is_err"):
                return TypeNode("bool")
            if expr.method in ("try", "unwrap", "unwrap_err", "err"):
                return TypeNode("i32")  # 簡略: 詳細な型推論は TypeChecker 拡張で対応
            if expr.method == "unwrap_or":
                return TypeNode("i32")
            raise TypeError_(f"Result has no method '{expr.method}'", expr)

        # 型がストラクトであるかを確認
        struct = self.structs.get(obj_type.name)
        if not struct:
            raise TypeError_(f"{obj_type.name} is not a struct, cannot call method {expr.method}", expr.obj)
        
        # メソッドを検索
        method = None
        for m in struct.methods:
            if m.name == expr.method:
                method = m
                break
        
        if not method:
            raise TypeError_(f"Struct {obj_type.name} has no method {expr.method}", expr)
        
        # 引数の数をチェック（self を除外）
        expected_arg_count = len(method.params) - 1
        if len(expr.args) != expected_arg_count:
            raise TypeError_(
                f"Method {expr.method} expects {expected_arg_count} arguments, got {len(expr.args)}",
                expr
            )
        
        # 引数の型をチェック
        arg_types = [self.check_expr(arg) for arg in expr.args]
        
        # ジェネリクス置換マップ（構造体の型引数）
        subst = {}
        for param, arg in zip(struct.type_params, obj_type.type_args):
            subst[param] = arg
        
        # 各引数の型をメソッドのパラメータと照合（self を除外）
        for i, (arg_t, param) in enumerate(zip(arg_types, method.params[1:])):
            param_t = self.substitute_type(param.type_node, subst)
            if not self.types_equal(arg_t, param_t):
                raise TypeError_(
                    f"Argument {i} to {expr.method}: expected {param_t}, got {arg_t}",
                    expr.args[i]
                )
        
        # メソッドの戻り値の型を返す
        return self.substitute_type(method.return_type, subst)

    # ============================================
    # FunctionCall
    # ============================================
    def check_call(self, expr: FunctionCall):
        # Check if the name refers to a lambda variable in scope
        for scope in reversed(self.env):
            if expr.name in scope:
                var_type = scope[expr.name]
                if isinstance(var_type, TypeNode) and var_type.name == "fn":
                    # Lambda call: return type is the last type_arg
                    if var_type.type_args:
                        return var_type.type_args[-1]
                    return TypeNode("void")

        func = self.functions.get(expr.name)
        if not func:
            # Ok/Err はビルトイン関数として扱う
            if expr.name in ("Ok", "Err"):
                return TypeNode("Result")
            raise TypeError_(f"Undefined function: {expr.name}", expr)

        # ----------------------------------------
        # 1. 引数の数チェック（builtin 関数は除外）
        # ----------------------------------------
        # builtin 関数は body=None なので、引数の可変性を許容
        if func.body is not None and len(expr.args) != len(func.params):
            raise TypeError_("Argument count mismatch", expr)

        # ----------------------------------------
        # 2. ジェネリック関数か？
        # ----------------------------------------
        if not func.type_params:
            # 通常の関数
            return self.check_call_non_generic(expr, func)

        # ----------------------------------------
        # 3. ジェネリック関数
        # ----------------------------------------
        # 明示的な型引数がある場合
        if expr.type_args:
            if len(expr.type_args) != len(func.type_params):
                raise TypeError_(
                    f"Function {func.name} expects {len(func.type_params)} type args, got {len(expr.type_args)}",
                    expr
                )
            subst = dict(zip(func.type_params, expr.type_args))

        else:
            # ----------------------------------------
            # 4. 型推論（制約解決）
            # ----------------------------------------
            subst = {}
            for arg_expr, param in zip(expr.args, func.params):
                arg_type = self.check_expr(arg_expr)
                param_type = param.type_node

                # param_type が T の場合
                if param_type.name in func.type_params:
                    # T がまだ決まっていない
                    if param_type.name not in subst:
                        subst[param_type.name] = arg_type
                    else:
                        # すでに T が決まっている → 一致するか？
                        if not self.types_equal(subst[param_type.name], arg_type):
                            raise TypeError_(
                                f"Type inference failed for {func.name}: conflicting types for {param_type.name}",
                                arg_expr
                            )
                else:
                    # 通常の型チェック
                    if not self.types_equal(arg_type, param_type):
                        raise TypeError_(
                            f"Argument type mismatch in call to {func.name}",
                            arg_expr
                        )

            # すべての T が決まったか？
            for t in func.type_params:
                if t not in subst:
                    raise TypeError_(f"Cannot infer type parameter {t} in call to {func.name}", expr)

        # ----------------------------------------
        # 5. パラメータ型チェック（置換後）
        # ----------------------------------------
        for arg_expr, param in zip(expr.args, func.params):
            arg_type = self.check_expr(arg_expr)
            expected = self.substitute_type(param.type_node, subst)
            if not self.types_equal(arg_type, expected):
                raise TypeError_(
                    f"Argument type mismatch in call to {func.name}: expected {expected}, got {arg_type}",
                    arg_expr
                )

        # ----------------------------------------
        # 6. 戻り値型（置換後）を返す
        # ----------------------------------------
        ret_type = self.substitute_type(func.return_type, subst)
        # Async functions return Future<T>
        if getattr(func, 'is_async', False):
            return TypeNode("Future", type_args=[ret_type] if ret_type else [TypeNode("void")])
        return ret_type

    # ============================================
    # 非ジェネリック対応
    # ============================================    
    def check_call_non_generic(self, expr: FunctionCall, func: FunctionDecl):
        # builtin 関数（body=None）の場合は型チェックをスキップ
        # 実行時に型チェックが行われる
        if func.body is None:
            # builtin 関数: 引数の型はチェックせず、各引数の型を調べるだけ
            for arg in expr.args:
                self.check_expr(arg)
            return func.return_type

        # ユーザー定義関数: 型チェック
        # ここに来る時点で「引数の数」はすでにチェック済み
        # 引数の型を全部チェック
        arg_types = [self.check_expr(arg) for arg in expr.args]

        # パラメータ型と一致するか確認
        for arg_t, param in zip(arg_types, func.params):
            param_t = param.type_node
            if not self.types_equal(arg_t, param_t):
                raise TypeError_(
                    f"Argument type mismatch in call to {func.name}: " 
                    f"expected {param_t}, got {arg_t}",
                    expr
                )

        # 戻り値の型をそのまま返す（async 関数は Future<T> を返す）
        if getattr(func, 'is_async', False):
            rt = func.return_type if func.return_type is not None else TypeNode("void")
            return TypeNode("Future", type_args=[rt])
        return func.return_type

    # ============================================
    # ArrayAccess
    # ============================================
    def check_array_access(self, expr: ArrayAccess):
        array_type = self.check_expr(expr.array)
        index_type = self.check_expr(expr.index)

        if index_type.name not in {"int", "i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64"}:
            raise TypeError_("Array index must be an integer type", expr.index)

        if array_type.array_size is None:
            raise TypeError_("Not an array", expr.array)

        return TypeNode(array_type.name)

    # ============================================
    # ArrayLiteral
    # ============================================
    def check_array_literal(self, expr: ArrayLiteral):
        if not expr.elements:
            raise TypeError_("Empty array literal not supported yet", expr)

        first_type = self.check_expr(expr.elements[0])

        for e in expr.elements[1:]:
            t = self.check_expr(e)
            if not self.types_equal(t, first_type):
                raise TypeError_("All elements in array literal must have same type", e)

        return TypeNode(first_type.name, len(expr.elements))