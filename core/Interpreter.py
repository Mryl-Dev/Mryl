from Ast import *
import asyncio
try:
    import nest_asyncio
    nest_asyncio.apply()    # ネストした run_until_complete 許可
except ImportError:
    pass                    # nest_asyncio 未インストール時はフォールバック
import datetime
import os

# 数値型のセット（型推論に使用）
INTEGER_TYPES = {"i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64"}
FLOAT_TYPES = {"f32", "f64"}
NUMERIC_TYPES = INTEGER_TYPES | FLOAT_TYPES

class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value

class BreakSignal(Exception):
    pass

class ContinueSignal(Exception):
    pass

class CallFrame:
    """Represents a single stack frame in a Mryl runtime error trace."""
    def __init__(self, function: str, file: str = "<unknown>", line=None):
        self.function = function
        self.file = file
        self.line = line


class MrylRuntimeError(Exception):
    """Fatal Mryl runtime error with structured call stack info.

    Carries a snapshot of the call stack at the moment the error was raised,
    so it can be formatted even after the interpreter has unwound.
    """
    def __init__(self, message: str, error_type: str = "RuntimeError", call_stack=None):
        self.message = message
        self.error_type = error_type
        # Snapshot: copy so later stack changes don't affect this record
        self.stack: list = list(call_stack) if call_stack else []
        super().__init__(message)

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------
    def format_detail(self) -> str:
        """Return the full multi-line error report (write to log / stderr)."""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        top = self.stack[-1] if self.stack else None
        func  = top.function if top else "<unknown>"
        file_ = top.file    if top else "<unknown>"
        line  = top.line    if top else "?"
        module = os.path.splitext(os.path.basename(file_))[0] if file_ != "<unknown>" else "<unknown>"

        lines = [
            f"[{now}] ERROR {self.error_type}: {self.message}",
            f"  module: {module}",
            f"  function: {func}",
            f"  file: {file_}",
            f"  line: {line if line is not None else '?'}",
            "",
            "Stacktrace:",
        ]
        for frame in reversed(self.stack):
            lines.append(f"  {frame.function}({frame.file}:{frame.line if frame.line is not None else '?'})")
        return "\n".join(lines)

    def format_brief(self) -> str:
        """One-line summary for the console."""
        return f"{self.error_type}: {self.message}"


class MatchError(Exception):
    """Raised when no match arm matches the scrutinee."""
    pass

class Interpreter:
    """Mryl language interpreter: executes AST and manages runtime state.
    
    Responsible for:
    - Statement execution (let, if, while, for, return, assignment)
    - Expression evaluation (literals, operators, function calls, methods)
    - Variable and struct management via scope stack
    - Generic function instantiation and type inference
    - Built-in function support (print, println, to_string)
    
    Runtime representation:
    - Variables: stored in scope stack (list of dicts)
    - Structures: represented as dicts with __struct_name__ key
    - Ranges: represented as dicts with __range__ key
    
    Notes:
    - Exception-based control flow for returns (ReturnSignal)
    - Supports C-style and Rust-style for loops
    - Implements generic type inference for polymorphic functions
    """
    def __init__(self):
        """Initialize interpreter with built-in functions and empty state."""
        self.functions = {}   # name -> FunctionDecl or ("builtin", func)
        self.structs = {}     # name -> StructDecl
        self.enums = {}       # name -> EnumDecl
        self.env = []         # list of dict (scope stack)
        self.const_table = {} # name -> {type, value}
        self.call_stack: list = []          # list of CallFrame (runtime call trace)
        self.source_file: str = "<unknown>" # current source file name (set from runner)

        # Built-in function definitions
        self.builtins = {
            "print": self.builtin_print,
            "println": self.builtin_println,
            "to_string": self.builtin_to_string,
        }

        # Register built-in functions
        for name, func in self.builtins.items():
            self.functions[name] = ("builtin", func)

    # ============================================================
    # プログラム実行
    # ============================================================
    def run(self, program: Program):
        """Execute Mryl program: load all structs and functions, then call main().
        
        Args:
            program (Program): AST of complete Mryl program
        
        Returns:
            Any: Return value of main() function
        
        Raises:
            RuntimeError: If main() function is not found
        
        Notes:
            - Built-in function declarations (body=None) are skipped
            - All user-defined functions and structs are registered
            - Entry point is always main() with no arguments
        """
        # Process const declarations
        env = [{}]  # Temporary scope for const evaluation
        for const_decl in program.consts:
            const_value = self.eval_expr(const_decl.init_expr, env)
            self.const_table[const_decl.name] = const_value

        # Register all structures
        for s in program.structs:
            self.structs[s.name] = s

        # Register all enums
        for e in program.enums:
            self.enums[e.name] = e

        # Register all functions (skip built-in declarations)
        for f in program.functions:
            # Skip built-in function declarations (body=None)
            if f.name in self.builtins and f.body is None:
                continue

            self.functions[f.name] = f

        if "main" not in self.functions:
            raise RuntimeError("main() function not found")

        return self.call_function("main", [], subst=None)

    # ============================================================
    # 関数呼び出し
    # ============================================================
    def call_function(self, name, args, subst=None):
        """Call a function by name with evaluated arguments.
        
        Args:
            name (str): Function name to call
            args (list): Evaluated argument values
            subst (dict, optional): Type substitution map for generics
        
        Returns:
            Any: Return value from function or None if no return
        
        Raises:
            RuntimeError: If function not found or body is None
        
        Notes:
            - Built-in functions bypass scope creation
            - Parameter binding is positional via zip
            - Generic type parameters added to environment
        """
        if name not in self.functions:
            # Ok/Err は内蔵関数
            if name == "Ok":
                return {'__result_tag__': 'ok', 'value': args[0] if args else None}
            if name == "Err":
                return {'__result_tag__': 'err', 'value': args[0] if args else None}
            raise RuntimeError(f"Undefined function: {name}")

        entry = self.functions[name]

        # Handle built-in functions
        if isinstance(entry, tuple) and entry[0] == "builtin":
            builtin_func = entry[1]
            return builtin_func(args)

        # Handle user-defined functions
        func = entry
        if not isinstance(func, FunctionDecl):
            raise RuntimeError(f"Invalid function entry for {name}")

        if func.body is None:
            raise RuntimeError(f"Function {name} has no body (body=None)")

        # Create new scope for function
        new_env = {}

        # Bind parameters to arguments
        for param, arg_value in zip(func.params, args):
            new_env[param.name] = arg_value

        # Add generic type substitutions to environment
        if subst:
            for tname, ttype in subst.items():
                new_env[tname] = ttype

        # Async function: run as asyncio coroutine and return a Future
        if getattr(func, 'is_async', False):
            async def _run_async_coro(captured_env=new_env, captured_func=func):
                self.env.append(captured_env)
                try:
                    self.eval_block(captured_func.body)
                except ReturnSignal as rs:
                    return rs.value
                finally:
                    if captured_env in self.env:
                        self.env.remove(captured_env)
                return None

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            task = loop.create_task(_run_async_coro())
            return {'__future__': True, 'task': task, 'loop': loop}

        # Push call frame (snapshot source location from FunctionDecl)
        frame = CallFrame(
            function=name,
            file=self.source_file,
            line=getattr(func, 'line', None),
        )
        self.call_stack.append(frame)

        # Push new scope and execute
        self.env.append(new_env)

        try:
            _ = self.eval_block(func.body)
        except ReturnSignal as rs:
            return rs.value
        finally:
            # Always clean up scope and frame
            if self.env and self.env[-1] is new_env:
                self.env.pop()
            self.call_stack.pop()

        return None

    # ============================================================
    # Lambda 呼び出し
    # ============================================================
    def call_lambda(self, closure, args):
        """Call a lambda closure with evaluated arguments.

        Args:
            closure (dict): Lambda closure {'params', 'body', 'captured_env'}
            args (list): Evaluated argument values

        Returns:
            Any: Return value from lambda body
        """
        params = closure['params']
        body = closure['body']
        captured_env = [dict(scope) for scope in closure['captured_env']]
        is_async = closure.get('is_async', False)

        # Create a new scope for lambda params (on top of captured env)
        new_scope = {}
        for param, arg_value in zip(params, args):
            new_scope[param.name] = arg_value
        captured_env.append(new_scope)

        # Async lambda: run body as asyncio coroutine and return a Future
        if is_async:
            async def _run_async_lambda(env=captured_env, b=body):
                try:
                    self.exec_block(b, env)
                except ReturnSignal as rs:
                    return rs.value
                return None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            task = loop.create_task(_run_async_lambda())
            return {'__future__': True, 'task': task, 'loop': loop}

        if isinstance(body, Block):
            try:
                self.exec_block(body, captured_env)
            except ReturnSignal as rs:
                return rs.value
            return None
        else:
            return self.eval_expr(body, captured_env)

    # ============================================================
    # スコープ操作
    # ============================================================
    def push_scope(self, env):
        """Create and push new empty scope onto scope stack.
        
        Args:
            env (list): Scope stack to push onto
        """
        env.append({})

    def pop_scope(self, env):
        """Remove and discard the innermost scope.
        
        Args:
            env (list): Scope stack to pop from
        """
        env.pop()

    def set_var(self, env, name, value):
        """Create variable in innermost scope (always defines new).
        
        Args:
            env (list): Scope stack
            name (str): Variable name
            value (Any): Value to bind
        
        Notes:
            - Always creates in innermost scope, shadows outer scopes
            - Used for local variable declarations
        """
        env[-1][name] = value

    def assign_var(self, env, name, value):
        """Assign to existing variable in any visible scope.
        
        Args:
            env (list): Scope stack
            name (str): Variable name to assign
            value (Any): New value
        
        Raises:
            RuntimeError: If variable not found in any scope
        
        Notes:
            - Searches from innermost to outermost scope
            - Updates first matching variable (shadowing)
        """
        for scope in reversed(env):
            if name in scope:
                scope[name] = value
                return
        raise RuntimeError(f"Undefined variable: {name}")

    def get_var(self, env, name):
        """Retrieve variable value from any visible scope.
        
        Args:
            env (list): Scope stack
            name (str): Variable name
        
        Returns:
            Any: Variable value
        
        Raises:
            RuntimeError: If variable not found
        
        Notes:
            - Searches from innermost to outermost
            - Returns first match (shadowing)
        """
        # Check local scopes first
        for scope in reversed(env):
            if name in scope:
                return scope[name]
        
        # Check const table
        if name in self.const_table:
            return self.const_table[name]
        
        raise RuntimeError(f"Undefined variable: {name}")

    # ============================================================
    # 文の実行
    # ============================================================
    def exec_block(self, block: Block, env):
        """Execute block of statements with new scope.
        
        Args:
            block (Block): Block AST node containing statements
            env (list): Current scope stack
        
        Notes:
            - Creates new scope at entry, removes at exit (guaranteed)
            - Uses try/finally to ensure scope cleanup
        """
        self.push_scope(env)
        try:
            for stmt in block.statements:
                self.exec_stmt(stmt, env)
        finally:
            self.pop_scope(env)

    def exec_stmt(self, stmt, env):
        """Execute a single statement.
        
        Args:
            stmt: Statement AST node (any Statement subclass)
            env (list): Scope stack
        
        Raises:
            ReturnSignal: When return statement is encountered
            RuntimeError: For unhandled statement types
        
        Handles:
            - LetDecl: Variable declarations with optional initialization
            - Assignment: Variable/array/field updates
            - IfStmt: Conditional execution with else-if chaining
            - WhileStmt: Loop execution
            - ForStmt: Both C-style and Rust-style loops
            - ReturnStmt: Function returns via exception
            - ExprStmt: Expression statements
            - Block: Nested blocks
        """
        if isinstance(stmt, LetDecl):
            value = None
            if stmt.init_expr:
                value = self.eval_expr(stmt.init_expr, env)
            self.set_var(env, stmt.name, value)

        elif isinstance(stmt, Assignment):
            self.exec_assignment(stmt, env)

        elif isinstance(stmt, IfStmt):
            cond = self.eval_expr(stmt.condition, env)
            if cond:
                self.exec_block(stmt.then_block, env)
            else:
                if stmt.else_block:
                    if isinstance(stmt.else_block, IfStmt):
                        # else if の場合は再帰的に IfStmt を処理
                        self.exec_stmt(stmt.else_block, env)
                    else:
                        # else { ... } の場合は Block
                        self.exec_block(stmt.else_block, env)

        elif isinstance(stmt, WhileStmt):
            while self.eval_expr(stmt.condition, env):
                try:
                    self.exec_block(stmt.body, env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue

        elif isinstance(stmt, ForStmt):
            self.exec_for(stmt, env)

        elif isinstance(stmt, ReturnStmt):
            value = self.eval_expr(stmt.expr, env)
            raise ReturnSignal(value)

        elif isinstance(stmt, BreakStmt):
            raise BreakSignal()

        elif isinstance(stmt, ContinueStmt):
            raise ContinueSignal()

        elif isinstance(stmt, ExprStmt):
            self.eval_expr(stmt.expr, env)

        elif isinstance(stmt, Block):
            self.exec_block(stmt, env)
        
        elif isinstance(stmt, ConditionalBlock):
            self.exec_conditional_block(stmt, env)

        else:
            raise RuntimeError(f"Unknown statement: {stmt}")

    def exec_conditional_block(self, stmt: ConditionalBlock, env):
        """Execute conditional compilation block"""
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
            condition_value = bool(self.eval_expr(stmt.condition_expr, env))
        
        # Execute appropriate block
        if condition_value:
            self.exec_block(stmt.then_block, env)
        elif stmt.else_block:
            self.exec_block(stmt.else_block, env)

    def exec_for(self, stmt: ForStmt, env):
        """Execute for loop (both Rust-style and C-style).
        
        Args:
            stmt (ForStmt): For loop statement (is_c_style flag determines type)
            env (list): Scope stack
        
        Processing:
            C-style: for (let i = 0; i < 10; i++)
                1. Execute initialization in outer scope
                2. Create new scope with loop variable
                3. Evaluate condition, execute body, evaluate update
            
            Rust-style: for x in iterable
                1. Evaluate iterable expression
                2. Create new scope
                3. Iterate over range OR array elements
        
        Supported iterables:
            - Range (dict with __range__ key): exclusive or inclusive
            - List: element-by-element iteration
        
        Raises:
            RuntimeError: If iterable type not supported
        
        Notes:
            - Loop scope includes only the loop variable
            - Updates can be assignments or expressions (++/--)
        """
        if stmt.is_c_style:
            # C-style: for (let i = 0; i < 10; i++)
            # Create new scope for loop variable
            loop_env = env + [{}]
            
            # Execute init: let i = 0
            init_value = self.eval_expr(stmt.iterable, env)  # init_expr stored in iterable
            self.set_var(loop_env, stmt.variable, init_value)
            
            # Loop: condition -> body -> update
            while self.eval_expr(stmt.condition, loop_env):
                try:
                    self.exec_block(stmt.body, loop_env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    pass  # continue でも update は実行する
                # Handle update (could be assignment or ++/--)
                if isinstance(stmt.update, Assignment):
                    self.exec_assignment(stmt.update, loop_env)
                else:
                    self.eval_expr(stmt.update, loop_env)
        else:
            # Rust-style: for x in iterable
            iterable_val = self.eval_expr(stmt.iterable, env)
            
            # Create new scope for loop variable
            loop_env = env + [{}]
            
            # Determine what to iterate over
            if isinstance(iterable_val, dict) and iterable_val.get("__range__"):
                # Range type: iterate from start to end (exclusive or inclusive)
                start = iterable_val["start"]
                end = iterable_val["end"]
                if iterable_val.get("inclusive"):
                    for i in range(start, end + 1):
                        self.set_var(loop_env, stmt.variable, i)
                        try:
                            self.exec_block(stmt.body, loop_env)
                        except BreakSignal:
                            return
                        except ContinueSignal:
                            continue
                else:
                    # Exclusive upper bound (default)
                    for i in range(start, end):
                        self.set_var(loop_env, stmt.variable, i)
                        try:
                            self.exec_block(stmt.body, loop_env)
                        except BreakSignal:
                            return
                        except ContinueSignal:
                            continue
            elif isinstance(iterable_val, list):
                # Array: iterate over elements
                for element in iterable_val:
                    self.set_var(loop_env, stmt.variable, element)
                    try:
                        self.exec_block(stmt.body, loop_env)
                    except BreakSignal:
                        return
                    except ContinueSignal:
                        continue
            else:
                raise RuntimeError(f"Cannot iterate over {type(iterable_val)}")

    def exec_assignment(self, stmt: Assignment, env):
        """Execute assignment to variable, array element, or struct field.
        
        Args:
            stmt (Assignment): Assignment statement with target and value
            env (list): Scope stack
        
        Processing:
            Variable assignment: name = expr
                1. Evaluate right-hand side
                2. Assign value to variable in scope
            
            Array element assignment: name[index] = expr
                1. Evaluate index and value
                2. Set array element by index
            
            Struct field assignment: obj.field = expr
                1. Evaluate field value
                2. Set field in struct dict
        
        Returns:
            None
        
        Raises:
            NameError: If variable not found in scope
            TypeError: If assignment target type mismatch (if type checking enabled)
            IndexError: If array index out of bounds
        
        Notes:
            - Type checker is notified of assignments for type inference
            - Struct fields created dynamically if not present
        """
        target = stmt.target

        # x = expr
        if isinstance(target, VarRef):
            value = self.eval_expr(stmt.expr, env)
            self.assign_var(env, target.name, value)
            return

        # arr[i] = expr
        if isinstance(target, ArrayAccess):
            arr = self.eval_expr(target.array, env)
            index = self.eval_expr(target.index, env)
            value = self.eval_expr(stmt.expr, env)
            arr[index] = value
            return

        # obj.field = expr
        if isinstance(target, StructAccess):
            obj = self.eval_expr(target.obj, env)
            value = self.eval_expr(stmt.expr, env)
            obj[target.field] = value
            return

        raise RuntimeError(f"Invalid assignment target: {target}")

    # ============================================================
    # Expression Evaluation
    # ============================================================
    def eval_expr(self, expr, env):
        """Evaluate expression to its runtime value.
        
        Args:
            expr: Expression AST node (supports 13+ expression types)
            env (list): Scope stack for variable lookup
        
        Supported expression types:
            - NumberLiteral: Return numeric value
            - FloatLiteral: Return float value
            - StringLiteral: Return string value
            - BoolLiteral: Return boolean value
            - VarRef: Look up variable in scope stack
            - UnaryOp: ++/--/post++/post-- (pre/post increment/decrement)
            - BinaryOp: Arithmetic, comparison, logical operations
            - FunctionCall: Invoke function with arguments
            - ArrayLiteral: Create list from elements
            - ArrayAccess: Index into array
            - StructInit: Create struct instance with fields
            - StructAccess: Access struct field
            - ConditionalExpr: Ternary operator (condition ? true : false)
        
        Returns:
            Computed value of expression (any Python type)
        
        Raises:
            NameError: If variable not found in scope
            RuntimeError: If operation invalid for operand types
            TypeError: If operation type mismatch
        
        Notes:
            - Pre/post increment differ: ++x returns new value, x++ returns old value
            - Variable scope searched deepest-first via get_var()
            - Function calls delegate to call_function()
        """
        if isinstance(expr, NumberLiteral):
            return expr.value

        if isinstance(expr, FloatLiteral):
            return expr.value

        if isinstance(expr, StringLiteral):
            return expr.value

        if isinstance(expr, BoolLiteral):
            return expr.value

        if isinstance(expr, VarRef):
            return self.get_var(env, expr.name)

        if isinstance(expr, UnaryOp):
            if expr.op == "++":
                # Pre-increment: ++i
                if isinstance(expr.operand, VarRef):
                    var_name = expr.operand.name
                    current = self.get_var(env, var_name)
                    new_val = current + 1
                    self.assign_var(env, var_name, new_val)
                    return new_val
                else:
                    raise RuntimeError("++ can only be applied to variables")
            
            if expr.op == "--":
                # Pre-decrement: --i
                if isinstance(expr.operand, VarRef):
                    var_name = expr.operand.name
                    current = self.get_var(env, var_name)
                    new_val = current - 1
                    self.assign_var(env, var_name, new_val)
                    return new_val
                else:
                    raise RuntimeError("-- can only be applied to variables")
            
            if expr.op == "post++":
                # Post-increment: i++
                if isinstance(expr.operand, VarRef):
                    var_name = expr.operand.name
                    current = self.get_var(env, var_name)
                    self.assign_var(env, var_name, current + 1)
                    return current  # Return old value
                else:
                    raise RuntimeError("++ can only be applied to variables")
            
            if expr.op == "post--":
                # Post-decrement: i--
                if isinstance(expr.operand, VarRef):
                    var_name = expr.operand.name
                    current = self.get_var(env, var_name)
                    self.assign_var(env, var_name, current - 1)
                    return current  # Return old value
                else:
                    raise RuntimeError("-- can only be applied to variables")
            
            v = self.eval_expr(expr.operand, env)
            if expr.op == "+":
                return +v
            if expr.op == "-":
                return -v
            if expr.op == "!":
                # Logical NOT
                return not self.is_truthy(v)
            if expr.op == "~":
                # Bitwise NOT
                return ~int(v)
            raise RuntimeError(f"Unknown unary operator: {expr.op}")

        if isinstance(expr, BinaryOp):
            # Handle short-circuit evaluation for logical operators
            if expr.op == "&&":
                left = self.eval_expr(expr.left, env)
                if not self.is_truthy(left):
                    return False  # Short-circuit: right is not evaluated
                right = self.eval_expr(expr.right, env)
                return self.is_truthy(right)
            
            if expr.op == "||":
                left = self.eval_expr(expr.left, env)
                if self.is_truthy(left):
                    return True  # Short-circuit: right is not evaluated
                right = self.eval_expr(expr.right, env)
                return self.is_truthy(right)
            
            # For other operators, evaluate both sides
            left = self.eval_expr(expr.left, env)
            right = self.eval_expr(expr.right, env)
            return self.eval_binary(expr.op, left, right)

        if isinstance(expr, ArrayAccess):
            arr = self.eval_expr(expr.array, env)
            index = self.eval_expr(expr.index, env)
            return arr[index]

        if isinstance(expr, StructAccess):
            obj = self.eval_expr(expr.obj, env)
            return obj[expr.field]

        if isinstance(expr, FunctionCall):
            # Check if the name refers to a lambda variable in scope
            try:
                maybe_lambda = self.get_var(env, expr.name)
                if isinstance(maybe_lambda, dict) and maybe_lambda.get('__lambda__'):
                    args = [self.eval_expr(a, env) for a in expr.args]
                    return self.call_lambda(maybe_lambda, args)
            except RuntimeError:
                pass  # Not a variable, fall through to normal function call

            subst = self.infer_call_subst(expr, env)
            args = [self.eval_expr(a, env) for a in expr.args]
            return self.call_function(expr.name, args, subst)

        if isinstance(expr, StructInit):
            return self.eval_struct_init(expr, env)

        if isinstance(expr, ArrayLiteral):
            return [self.eval_expr(e, env) for e in expr.elements]

        if isinstance(expr, MethodCall):
            return self.eval_method_call(expr, env)

        if isinstance(expr, Range):
            start = self.eval_expr(expr.start, env)
            end = self.eval_expr(expr.end, env)
            # Return a Range object (dict) that can be iterated
            # Using a dict to represent Range at runtime
            return {"__range__": True, "start": start, "end": end, "inclusive": expr.inclusive}

        if isinstance(expr, Lambda):
            # Create a closure: capture current env snapshot
            captured_env = [dict(scope) for scope in env]
            return {
                '__lambda__': True,
                'params': expr.params,
                'body': expr.body,
                'is_async': getattr(expr, 'is_async', False),
                'captured_env': captured_env,
            }

        if isinstance(expr, AwaitExpr):
            future = self.eval_expr(expr.expr, env)
            if isinstance(future, dict) and future.get('__future__'):
                loop = future.get('loop')
                if loop is None:
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                return loop.run_until_complete(future['task'])
            raise RuntimeError("await: expression is not a Future")

        if isinstance(expr, EnumVariantExpr):
            # Create enum value: {__enum__: EnumName, __variant__: VariantName, __data__: [...]}
            data = [self.eval_expr(a, env) for a in expr.args]
            return {'__enum__': expr.enum_name, '__variant__': expr.variant_name, '__data__': data}

        if isinstance(expr, MatchExpr):
            val = self.eval_expr(expr.scrutinee, env)
            for arm in expr.arms:
                bound, matched = self._match_pattern(arm.pattern, val)
                if matched:
                    arm_env = env + [bound]
                    return self.eval_expr(arm.body, arm_env)
            raise MrylRuntimeError(
                f"no arm matched value: {val!r}",
                error_type="MatchError",
                call_stack=self.call_stack,
            )

        if isinstance(expr, BlockExpr):
            # ブロック式: ステートメントを順番に実行し、最後の result_expr を返す
            block_env = env + [{}]
            for stmt in expr.stmts:
                self.exec_stmt(stmt, block_env)
            if expr.result_expr is not None:
                return self.eval_expr(expr.result_expr, block_env)
            return None

        raise RuntimeError(f"Unknown expression: {expr}")

    def _match_pattern(self, pattern, val):
        """Try to match pattern against val. Returns (bindings_dict, matched_bool)."""
        import re
        if isinstance(pattern, LiteralPattern):
            return {}, (val == pattern.value)
        if isinstance(pattern, BindingPattern):
            if pattern.name == "_":
                raise MrylRuntimeError(
                    f"'_' error arm reached with value: {val!r}",
                    error_type="MatchError",
                    call_stack=self.call_stack,
                )
            return {pattern.name: val}, True
        if isinstance(pattern, EnumPattern):
            # Result型 Ok(v) / Err(e) パターン
            if pattern.enum_name in ('Ok', 'Err') and pattern.variant_name in ('Ok', 'Err'):
                tag = 'ok' if pattern.enum_name == 'Ok' else 'err'
                if not (isinstance(val, dict) and val.get('__result_tag__') == tag):
                    return {}, False
                bindings = {}
                if pattern.bindings:
                    bindings[pattern.bindings[0]] = val.get('value')
                return bindings, True
            # 通常の enum パターン
            if not (isinstance(val, dict)
                    and val.get('__enum__') == pattern.enum_name
                    and val.get('__variant__') == pattern.variant_name):
                return {}, False
            bindings = {}
            for i, name in enumerate(pattern.bindings):
                data = val.get('__data__', [])
                bindings[name] = data[i] if i < len(data) else None
            return bindings, True
        if isinstance(pattern, StructPattern):
            if not isinstance(val, dict):
                return {}, False
            bindings = {f: val[f] for f in pattern.fields if f in val}
            return bindings, len(bindings) == len(pattern.fields)
        if isinstance(pattern, RegexPattern):
            matched = bool(re.fullmatch(pattern.pattern_str, str(val)))
            return {}, matched
        return {}, False

    # ============================================================
    # Binary Operations
    # ============================================================
    def eval_binary(self, op, left, right):
        """Evaluate binary operation on two operands.
        
        Args:
            op (str): Operator symbol (+, -, *, /, %, ==, !=, <, <=, >, >=, &&, ||, &, |, ^, <<, >>)
            left: Left operand value
            right: Right operand value
        
        Supported operations:
            Arithmetic: +, -, *, /, %
            Comparison: ==, !=, <, <=, >, >=
            Logical: && (short-circuit), || (short-circuit)
            Bitwise: & (and), | (or), ^ (xor), << (left shift), >> (right shift)
        
        Returns:
            Result of operation (numeric, boolean, or string)
        
        Raises:
            RuntimeError: If operator unknown or type mismatch
            ZeroDivisionError: If division by zero
        
        Notes:
            - Division (/) is integer division (// in Python)
            - String concatenation via + operator supported
            - Type coercion follows Python semantics
            - Logical operators handled with short-circuit evaluation in eval_expr
            - Bitwise operators work on integer operands
        """
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left // right  # Integer division
        if op == "%":
            return left % right

        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        if op == ">=":
            return left >= right

        # Bitwise operators
        if op == "&":
            return int(left) & int(right)
        if op == "|":
            return int(left) | int(right)
        if op == "^":
            return int(left) ^ int(right)
        if op == "<<":
            return int(left) << int(right)
        if op == ">>":
            return int(left) >> int(right)

        raise RuntimeError(f"Unknown binary operator: {op}")

    def is_truthy(self, value):
        """Determine if value is truthy in conditional context.
        
        Args:
            value: Value to evaluate for truthiness
        
        Returns:
            bool: True if value is considered truthy, False otherwise
        
        Truthiness rules:
            - False, 0, empty string (""), None: falsy
            - True, non-zero numbers, non-empty strings: truthy
        """
        if value is False or value is None:
            return False
        if value == 0 or value == "":
            return False
        return True

    # ============================================================
    # Struct
    # ============================================================
    def eval_struct_init(self, expr: StructInit, env):
        """Initialize struct instance with field values.
        
        Args:
            expr (StructInit): Struct initialization expression with name and fields
            env (list): Scope stack for field expression evaluation
        
        Processing:
            1. Look up struct definition by name
            2. Create dict with __struct_name__ key
            3. Store type_args if generic struct
            4. Evaluate each provided field expression
            5. Fill missing fields with None (default value)
        
        Returns:
            dict: Struct instance with __struct_name__, optional __type_args__, and fields
        
        Raises:
            RuntimeError: If struct type not defined
        
        Notes:
            - Generic structs store type arguments in __type_args__ for runtime dispatch
            - Fields not provided in constructor initialized to None
            - Struct instance is mutable (fields can be reassigned)
        """
        struct = self.structs.get(expr.struct_name)
        if not struct:
            raise RuntimeError(f"Undefined struct: {expr.struct_name}")

        obj = {"__struct_name__": expr.struct_name}

        # Store type_args if generic struct
        if expr.type_args:
            obj["__type_args__"] = expr.type_args

        for name, value_expr in expr.fields:
            obj[name] = self.eval_expr(value_expr, env)

        # Fill missing fields with None
        for field in struct.fields:
            if field.name not in obj:
                obj[field.name] = None

        return obj

    # ============================================================
    # Method Call
    # ============================================================
    def eval_method_call(self, expr: MethodCall, env):
        """Invoke method on struct instance.
        
        Args:
            expr (MethodCall): Method call expression with object, method name, and arguments
            env (list): Scope stack for argument evaluation
        
        Processing:
            1. Evaluate object expression to get struct instance
            2. Verify object is struct with __struct_name__
            3. Look up struct definition and method by name
            4. Evaluate argument expressions
            5. Create new scope with self binding
            6. Execute method body with parameter bindings
        
        Returns:
            Return value from method, or None if no explicit return
        
        Raises:
            RuntimeError: If object not struct, struct not defined, method not found
            ReturnSignal (exception): Caught to extract return value
        
        Notes:
            - First parameter (self) auto-bound to object instance
            - Remaining parameters filled by position with evaluated arguments
            - Method scope is isolated from caller scope
        """
        # Evaluate object to get struct instance
        obj = self.eval_expr(expr.obj, env)

        # 動的配列(Python list)のメソッド処理
        if isinstance(obj, list):
            args_eval = [self.eval_expr(a, env) for a in expr.args]
            if expr.method == 'push':
                obj.append(args_eval[0])
                return None
            elif expr.method == 'pop':
                if not obj:
                    raise MrylRuntimeError("pop() called on empty array", "IndexError", self.call_stack)
                return obj.pop()
            elif expr.method == 'len':
                return len(obj)
            elif expr.method == 'is_empty':
                return len(obj) == 0
            elif expr.method == 'remove':
                idx = int(args_eval[0])
                if idx < 0 or idx >= len(obj):
                    raise MrylRuntimeError(f"remove() index {idx} out of bounds", "IndexError", self.call_stack)
                return obj.pop(idx)
            elif expr.method == 'insert':
                idx, val = int(args_eval[0]), args_eval[1]
                obj.insert(idx, val)
                return None
            raise RuntimeError(f"Unknown array method: {expr.method}")

        # Result 型のメソッド処理
        if isinstance(obj, dict) and '__result_tag__' in obj:
            args_eval = [self.eval_expr(a, env) for a in expr.args]
            if expr.method == 'is_ok':
                return obj['__result_tag__'] == 'ok'
            if expr.method == 'is_err':
                return obj['__result_tag__'] == 'err'
            if expr.method == 'try':
                # .try() : Ok値を取り出す。Err なら構造化エラーで終了
                if obj['__result_tag__'] == 'ok':
                    return obj['value']
                raise MrylRuntimeError(
                    f"Err({obj['value']!r})",
                    error_type="Error",
                    call_stack=self.call_stack,
                )
            if expr.method == 'unwrap':
                if obj['__result_tag__'] == 'ok':
                    return obj['value']
                raise MrylRuntimeError(
                    f"unwrap() called on Err value: {obj['value']!r}",
                    error_type="UnwrapError",
                    call_stack=self.call_stack,
                )
            if expr.method == 'err':
                if obj['__result_tag__'] == 'ok':
                    return obj['value']
                raise MrylRuntimeError(
                    f"Err({obj['value']!r})",
                    error_type="Error",
                    call_stack=self.call_stack,
                )
            if expr.method == 'unwrap_err':
                if obj['__result_tag__'] == 'err':
                    return obj['value']
                raise MrylRuntimeError(
                    f"unwrap_err() called on Ok value: {obj['value']!r}",
                    error_type="UnwrapError",
                    call_stack=self.call_stack,
                )
            if expr.method == 'unwrap_or':
                if obj['__result_tag__'] == 'ok':
                    return obj['value']
                return args_eval[0] if args_eval else None
            raise RuntimeError(f"Unknown Result method: {expr.method}")

        # Verify object is struct with __struct_name__
        if not isinstance(obj, dict) or "__struct_name__" not in obj:
            raise RuntimeError(f"Cannot call method on non-struct value")
        
        struct_name = obj["__struct_name__"]
        struct = self.structs.get(struct_name)
        
        if not struct:
            raise RuntimeError(f"Undefined struct: {struct_name}")
        
        # Search for method by name
        method = None
        for m in struct.methods:
            if m.name == expr.method:
                method = m
                break
        
        if not method:
            raise RuntimeError(f"Struct {struct_name} has no method {expr.method}")
        
        # Evaluate arguments
        args = [self.eval_expr(a, env) for a in expr.args]
        
        # Create new scope
        new_env = {}
        
        # Bind self to first parameter
        new_env[method.params[0].name] = obj
        
        # Bind remaining arguments
        for param, arg_value in zip(method.params[1:], args):
            new_env[param.name] = arg_value
        
        # Execute method body
        self.env.append(new_env)
        try:
            for stmt in method.body.statements:
                self.exec_stmt(stmt, self.env)
        except ReturnSignal as ret:
            return ret.value
        finally:
            self.env.pop()
        
        # Default return value (if no explicit return)
        return None

    # ============================================================
    # Function Block Evaluation (for call_function)
    # ============================================================
    def eval_block(self, block: Block):
        """Execute function/method body block with scope management.
        
        Args:
            block (Block): Block of statements to execute
        
        Processing:
            1. Push new scope (empty environment dict)
            2. Execute all statements in block
            3. Pop scope (cleanup on exception via finally)
        
        Returns:
            None (statement execution only, no return value)
        
        Notes:
            - Used by call_function to evaluate function bodies
            - Return values handled by ReturnSignal exception
            - New scope isolates local variables from caller
        """
        # Create new scope for function/method
        self.env.append({})
        try:
            for stmt in block.statements:
                # ステートメントの行番号でコールフレームを更新
                if self.call_stack and getattr(stmt, 'line', None) is not None:
                    self.call_stack[-1].line = stmt.line
                self.exec_stmt(stmt, self.env)
        finally:
            self.env.pop()

    # ============================================================
    # Built-in Functions
    # ============================================================
    def builtin_print(self, args):
        """Print formatted string without newline.
        
        Args:
            args (list): List of values to print
        
        Processing:
            1. Format arguments using format_string()
            2. Print result without trailing newline
        
        Returns:
            None
        
        Notes:
            - Output goes directly to stdout (unbuffered)
            - No trailing newline (unlike println)
        """
        result = self.format_string(args)
        print(result, end="")
        return None

    def builtin_println(self, args):
        """Print formatted string with newline.
        
        Args:
            args (list): List of values to print
        
        Processing:
            1. Format arguments using format_string()
            2. Print result with trailing newline
        
        Returns:
            None
        
        Notes:
            - Output goes directly to stdout
            - Automatically adds newline at end
        """
        result = self.format_string(args)
        print(result)
        return None

    def builtin_to_string(self, args):
        """Convert value to string representation.
        
        Args:
            args (list): Must have at least 1 element (value to convert)
        
        Processing:
            1. If first arg is format string (contains "{}"), apply format_string()
            2. Otherwise, simple Python str() conversion
        
        Returns:
            str: String representation of value
        
        Raises:
            RuntimeError: If args is empty
        
        Notes:
            - Supports format string syntax: "Value: {}" with multiple arguments
            - Falls back to standard Python str() for simple conversion
        """
        if len(args) < 1:
            raise RuntimeError("to_string expects at least 1 argument")
        
        # If first arg is format string with placeholders, apply formatting
        if isinstance(args[0], str) and "{}" in args[0]:
            return self.format_string(args)
        
        # Simple string conversion
        return str(args[0])

    def format_string(self, args):
        """Format string with placeholder substitution.
        
        Args:
            args (list): [format_str, arg1, arg2, ...] where format_str contains {}
        
        Processing:
            1. First arg is format string with {} placeholders
            2. Remaining args substitute into placeholders left-to-right
            3. Handle escape sequences: \\n, \\t, etc.
        
        Returns:
            str: Formatted string with placeholders replaced by values
        
        Raises:
            IndexError: If not enough arguments for placeholders
        
        Notes:
            - Each {} is replaced by next argument in order
            - All values converted to string via str()
            - Escape sequences processed in final string
        """
        if len(args) == 0:
            return ""
        
        if not isinstance(args[0], str):
            # If no format string, concatenate all arguments
            return "".join(str(a) for a in args)
        
        format_str = args[0]
        rest_args = args[1:]
        
        # Find and replace {} placeholders
        result = []
        i = 0
        arg_index = 0
        
        while i < len(format_str):
            if i < len(format_str) - 1 and format_str[i:i+2] == "{}":
                # Found {} placeholder
                if arg_index >= len(rest_args):
                    raise RuntimeError("Not enough arguments for format string")
                result.append(str(rest_args[arg_index]))
                arg_index += 1
                i += 2
            elif format_str[i] == '\\' and i < len(format_str) - 1:
                # Escape sequences
                if format_str[i+1] == 'n':
                    result.append('\n')
                    i += 2
                elif format_str[i+1] == 't':
                    result.append('\t')
                    i += 2
                elif format_str[i+1] == '\\':
                    result.append('\\')
                    i += 2
                else:
                    result.append(format_str[i])
                    i += 1
            else:
                result.append(format_str[i])
                i += 1
        
        return "".join(result)

    # ============================================================
    # Type Rank (Numeric Type Compatibility)
    # ============================================================
    def numeric_type_rank(self, type_name: str) -> int:
        """Get numeric type rank for implicit type coercion.
        
        Args:
            type_name (str): Type name (i8, i16, i32, i64, u8, u16, u32, u64, f32, f64)
        
        Returns:
            int: Rank where higher value = larger type capacity
        
        Notes:
            - Signed int: i8(1) < i16(2) < i32(3) < i64(4)
            - Unsigned int: u8(5) < u16(6) < u32(7) < u64(8)
            - Float: f32(9) < f64(10)
            - Used in find_common_numeric_type() for type promotion
        """
        if type_name == "i8":   return 1
        if type_name == "i16":  return 2
        if type_name == "i32":  return 3
        if type_name == "i64":  return 4
        if type_name == "u8":   return 5
        if type_name == "u16":  return 6
        if type_name == "u32":  return 7
        if type_name == "u64":  return 8
        if type_name == "f32":  return 9
        if type_name == "f64":  return 10
        return -1

    def is_signed_int(self, type_name: str) -> bool:
        """Check if type is signed integer (i8, i16, i32, i64).
        
        Args:
            type_name (str): Type name to check
        
        Returns:
            bool: True if signed integer type
        """
        return type_name in ("i8", "i16", "i32", "i64")
    
    def is_unsigned_int(self, type_name: str) -> bool:
        """Check if type is unsigned integer (u8, u16, u32, u64).
        
        Args:
            type_name (str): Type name to check
        
        Returns:
            bool: True if unsigned integer type
        """
        return type_name in ("u8", "u16", "u32", "u64")

    def find_common_numeric_type(self, a: TypeNode, b: TypeNode) -> TypeNode:
        """Find common supertype for implicit type coercion.
        
        Args:
            a (TypeNode): First type
            b (TypeNode): Second type
        
        Returns:
            TypeNode: Type with higher rank (broader type for coercion)
        
        Notes:
            - Same types return as-is
            - Float types take precedence over int types
            - Among same category, higher rank type is returned
            - Rank: i8 < i16 < i32 < i64 < u8 < u16 < u32 < u64 < f32 < f64
        """
        a_name = a.name
        b_name = b.name

        if a_name == b_name:
            return a

        if FLOAT_TYPES and (a_name in FLOAT_TYPES or b_name in FLOAT_TYPES):
            if a_name in FLOAT_TYPES and b_name in FLOAT_TYPES:
                rank_a = self.numeric_type_rank(a_name)
                rank_b = self.numeric_type_rank(b_name)
                return a if rank_a >= rank_b else b
            return TypeNode("f64")

        if self.is_unsigned_int(a_name) and self.is_unsigned_int(b_name):
            rank_a = self.numeric_type_rank(a_name)
            rank_b = self.numeric_type_rank(b_name)
            larger = a_name if rank_a >= rank_b else b_name
            return TypeNode(larger)

        if self.is_signed_int(a_name) and self.is_signed_int(b_name):
            rank_a = self.numeric_type_rank(a_name)
            rank_b = self.numeric_type_rank(b_name)
            larger = a_name if rank_a >= rank_b else b_name
            return TypeNode(larger)

        return None

    # ============================================================
    # ジェネリック関数の型推論（T の制約解決）
    # ============================================================
    def infer_call_subst(self, expr, env):
        """Infer generic type substitution from function call arguments.
        
        Args:
            expr: Function call expression with name and arguments
            env (list): Scope stack for expression evaluation
        
        Processing:
            1. Look up function entry by name
            2. Return None if builtin or non-generic function
            3. If explicit type args provided, return direct substitution
            4. Otherwise, evaluate each argument and infer types:
               - Extract runtime type via runtime_type_of()
               - Match against generic type parameters
               - Resolve to most specific common type
        
        Returns:
            dict: Substitution mapping (type_param_name -> TypeNode) or None
        
        Raises:
            RuntimeError: If argument types conflict and no common type
        
        Notes:
            - Explicit type args override inference
            - Builtin functions don't support generics
            - Numeric type promotion uses find_common_numeric_type()
        """
        if expr.name not in self.functions:
            return None  # Not a registered function (could be lambda or undefined)
        entry = self.functions[expr.name]

        # 組み込み関数はジェネリック推論しない
        if isinstance(entry, tuple) and entry[0] == "builtin":
            return None

        # ジェネリックでない関数
        func = entry
        if not func.type_params:
            return None

        subst = {}

        # 明示的な型引数
        if hasattr(expr, "type_args") and expr.type_args:
            return dict(zip(func.type_params, expr.type_args))

        # 型推論
        for arg_expr, param in zip(expr.args, func.params):
            arg_value = self.eval_expr(arg_expr, env)
            arg_type = self.runtime_type_of(arg_value)

            param_type = param.type_node

            if param_type.name in func.type_params:
                if param_type.name not in subst:
                    subst[param_type.name] = arg_type
                else:
                    # すでに推論済みの型と一致するか、昇格可能か確認
                    existing = subst[param_type.name]
                    if self.types_equal(existing, arg_type):
                        # OK: 同じ型
                        pass
                    elif self.numeric_type_rank(existing.name) >= 0 and self.numeric_type_rank(arg_type.name) >= 0:
                        # Both are numeric types: unify to higher rank
                        common = self.find_common_numeric_type(existing, arg_type)
                        if common:
                            subst[param_type.name] = common
                        else:
                            raise RuntimeError(
                                f"Type inference conflict for {param_type.name}: incompatible types {existing.name} and {arg_type.name}"
                            )
                    else:
                        raise RuntimeError(
                            f"Type inference conflict for {param_type.name}"
                        )

        return subst

    # ============================================================
    # Runtime Type Inference
    # ============================================================
    def runtime_type_of(self, value):
        """Infer runtime type of Python value from Mryl semantics.
        
        Args:
            value: Runtime value (any Python type)
        
        Returns:
            TypeNode: Detected type (name, optional type_args)
        
        Processing:
            Dict with __struct_name__: Struct type
            Dict with __range__: Range type
            List: Array type (element type inferred from first element)
            bool: Boolean type
            int: Numeric type (i32 default)
            float: Float type (f64 default)
            str: String type
        
        Notes:
            - Does not distinguish between i32/i64, all ints -> TypeNode("i32")
            - Array elements assumed homogeneous (array<T>)
            - Domain-specific dicts (__struct_name__, __range__) recognized
        """
        # Check bool first (bool is subclass of int in Python)
        if isinstance(value, bool):
            return TypeNode("bool")
        if isinstance(value, int):
            # Default to i32
            return TypeNode("i32")
        if isinstance(value, float):
            # Default to f64
            return TypeNode("f64")
        if isinstance(value, str):
            return TypeNode("string")
        if isinstance(value, dict):
            return TypeNode(value["__struct_name__"], type_args=value.get("__type_args__", []))
        raise RuntimeError(f"Unknown runtime type: {value}")

    # ============================================================
    # Type Comparison (Needed in Interpreter)
    # ============================================================
    def types_equal(self, a: TypeNode, b: TypeNode):
        """Check if two types are structurally equal.
        
        Args:
            a (TypeNode): First type
            b (TypeNode): Second type
        
        Returns:
            bool: True if types match in all aspects (name, array_size, type_args recursively)
        
        Processing:
            1. Compare base type names
            2. Compare array sizes
            3. Recursively compare all type arguments
        
        Notes:
            - For generic types: T<i32> != T<i64>
            - For arrays: [T; 10] != [T; 20]
            - For nested generics: fully recursive comparison
        """
        if a.name != b.name:
            return False
        if a.array_size != b.array_size:
            return False
        if len(a.type_args) != len(b.type_args):
            return False
        for x, y in zip(a.type_args, b.type_args):
            if not self.types_equal(x, y):
                return False
        return True