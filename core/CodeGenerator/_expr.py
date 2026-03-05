from __future__ import annotations
from Ast import BindingPattern, EnumPattern, StructPattern
from CodeGenerator._util import _safe_c_name
from CodeGenerator._proto import _CodeGeneratorBase

class CodeGeneratorExprMixin(_CodeGeneratorBase):
    """式(Expression)レベルの C コード生成を担当する Mixin
    _generate_expr / _generate_expr_with_temps /
    _generate_function_call / _generate_print_call /
    _generate_struct_init / _generate_match_expr /
    _infer_match_result_c_type / _pattern_binding_types /
    _match_pattern_to_c / _generate_method_call
    """

    def _generate_expr(self, expr) -> str:
        """式ノードを C 式文字列として返す (ディスパッチャ) """
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
            if expr.name in self.ident_renames:
                return self.ident_renames[expr.name]
            return _safe_c_name(expr.name)

        if expr_class == "BinaryOp":
            left       = self._generate_expr(expr.left)
            right      = self._generate_expr(expr.right)
            op         = expr.op
            left_type  = self._infer_expr_type(expr.left)
            right_type = self._infer_expr_type(expr.right)
            if left_type == "string" and right_type == "string":
                if op == "+":
                    return f"mryl_string_concat({left}, {right})"
                if op == "==":
                    return f"(strcmp(({left}).data, ({right}).data) == 0)"
                if op == "!=":
                    return f"(strcmp(({left}).data, ({right}).data) != 0)"
            # && / || を明示的にマップ(他は同一)
            c_op = {"&&": "&&", "||": "||"}.get(op, op)
            return f"({left} {c_op} {right})"

        if expr_class == "UnaryOp":
            operand = self._generate_expr(expr.operand)
            if expr.op == "post++":
                return f"({operand}++)"
            elif expr.op == "post--":
                return f"({operand}--)"
            elif expr.op == "!":
                return f"(!{operand})"
            elif expr.op == "~":
                return f"(~{operand})"
            else:
                return f"({expr.op}{operand})"

        if expr_class == "FunctionCall":
            return self._generate_function_call(expr)

        if expr_class == "StructAccess":
            obj = self._generate_expr(expr.obj)
            # self はポインタ渡しなので -> を使用 (Bug#28)
            op = "->" if (expr.obj.__class__.__name__ == "VarRef" and expr.obj.name == "self") else "."
            return f"{obj}{op}{expr.field}"

        if expr_class == "ArrayAccess":
            arr      = self._generate_expr(expr.array)
            idx      = self._generate_expr(expr.index)
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
            return "/* await - use let statement for typed await */"

        return "0"

    def _generate_expr_with_temps(self, expr, temp_string_mapping: dict) -> str:
        """一時文字列変数マッピングを考慮して式を生成する """
        if expr is None:
            return ""

        expr_class = expr.__class__.__name__

        if expr_class == "StringLiteral":
            if id(expr) in temp_string_mapping:
                return temp_string_mapping[id(expr)]
            return self._generate_expr(expr)

        if expr_class == "FunctionCall":
            for scope in reversed(self.env):
                if expr.name in scope and scope[expr.name] in ('fn', 'fn_closure'):
                    return self._generate_function_call(expr)
            args = [self._generate_expr_with_temps(arg, temp_string_mapping) for arg in expr.args]
            if expr.name in ["print", "println"]:
                return self._generate_print_call(expr)
            func = self.program_functions.get(expr.name)
            if func and func.type_params:
                type_args       = self._infer_generic_type_args(func, expr.args)
                type_args_tuple = tuple(str(t) for t in type_args)
                self._register_generic_instantiation(expr.name, type_args)
                instantiated_name = self._get_instantiated_func_name(expr.name, type_args_tuple)
                return f"{instantiated_name}({', '.join(args)})"
            # to_string(bool) → _mryl_to_string_bool を直接呼び出す
            if expr.name == "to_string" and len(expr.args) == 1:
                arg_type = self._infer_expr_type(expr.args[0])
                if arg_type == "bool":
                    return f"_mryl_to_string_bool({', '.join(args)})"
            return f"{expr.name}({', '.join(args)})"

        if expr_class == "BinaryOp":
            left       = self._generate_expr_with_temps(expr.left,  temp_string_mapping)
            right      = self._generate_expr_with_temps(expr.right, temp_string_mapping)
            left_type  = self._infer_expr_type(expr.left)
            right_type = self._infer_expr_type(expr.right)
            if left_type == "string" and right_type == "string":
                if expr.op == "+":
                    return f"mryl_string_concat({left}, {right})"
                if expr.op == "==":
                    return f"(strcmp(({left}).data, ({right}).data) == 0)"
                if expr.op == "!=":
                    return f"(strcmp(({left}).data, ({right}).data) != 0)"
            return f"({left} {expr.op} {right})"

        return self._generate_expr(expr)

    def _generate_function_call(self, expr) -> str:
        """FunctionCall を C 式文字列として返す """
        if expr.name in ["print", "println"]:
            return self._generate_print_call(expr)

        if expr.name in ("Ok", "Err"):
            val_code    = self._generate_expr(expr.args[0]) if expr.args else "0"
            struct_name = self.current_return_type or "MrylResult_i32_i32"
            if expr.name == "Ok":
                return f"({struct_name}){{1, {{.ok_val = {val_code}}}}}"
            else:
                return f"({struct_name}){{0, {{.err_val = {val_code}}}}}"

        for scope in reversed(self.env):
            if expr.name in scope and scope[expr.name] == "async_fn":
                factory = self.async_lambda_factories.get(expr.name, expr.name)
                args    = ", ".join(self._generate_expr(arg) for arg in expr.args)
                return f"{factory}({args})"
            if expr.name in scope and scope[expr.name] == "fn":
                c_name = self.ident_renames.get(expr.name, _safe_c_name(expr.name))
                args   = ", ".join(self._generate_expr(arg) for arg in expr.args)
                return f"{c_name}({args})"
            if expr.name in scope and scope[expr.name] == "fn_closure":
                c_name   = self.ident_renames.get(expr.name, _safe_c_name(expr.name))
                args     = ", ".join(self._generate_expr(arg) for arg in expr.args)
                all_args = f"{args}, &{c_name}.env" if args else f"&{c_name}.env"
                return f"{c_name}.fn({all_args})"

        func = self.program_functions.get(expr.name)
        if func and func.type_params:
            type_args         = self._infer_generic_type_args(func, expr.args)
            type_args_tuple   = tuple(str(t) for t in type_args)
            self._register_generic_instantiation(expr.name, type_args)
            instantiated_name = self._get_instantiated_func_name(expr.name, type_args_tuple)
            args              = ", ".join(self._generate_expr(arg) for arg in expr.args)
            return f"{instantiated_name}({args})"

        # to_string(bool) → _mryl_to_string_bool を直接呼び出す
        # (Mryl の bool は C の int にマップされるため _Generic の _Bool ブランチに
        #  マッチしない。引数の Mryl 型を見て直接ディスパッチする)
        if expr.name == "to_string" and len(expr.args) == 1:
            arg_type = self._infer_expr_type(expr.args[0])
            if arg_type == "bool":
                arg_code = self._generate_expr(expr.args[0])
                return f"_mryl_to_string_bool({arg_code})"

        args = ", ".join(self._generate_expr(arg) for arg in expr.args)
        return f"{expr.name}({args})"

    def _generate_print_call(self, expr) -> str:
        """print/println 呼び出しを C printf/printf+\n 呼び出しに変換する """
        if not expr.args:
            return f'{expr.name}("")'

        first_arg = expr.args[0]

        if first_arg.__class__.__name__ == "StringLiteral":
            if len(expr.args) > 1:
                fmt_str     = first_arg.value
                format_args = expr.args[1:]
                parts       = fmt_str.split("{}")
                if len(parts) != len(format_args) + 1:
                    # {} の数と引数が一致しない: 各 {} に対して型に応じた spec を使用
                    raw_parts = fmt_str.split("{}")
                    fmt_c = ""
                    for j, rp in enumerate(raw_parts[:-1]):
                        spec = self._type_to_fmt_spec(format_args[j]) if j < len(format_args) else "%d"
                        fmt_c += rp.replace("%", "%%") + spec
                    fmt_c += raw_parts[-1].replace("%", "%%")
                    fmt_c  = fmt_c.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
                    args  = [f'"{fmt_c}"']
                    for a in format_args:
                        arg_type = self._infer_expr_type(a)
                        arg_code = self._generate_expr(a)
                        if arg_type in ("string", "str"):
                            args.append(f"{arg_code}.data")
                        elif arg_type == "bool":
                            args.append(f"({arg_code} ? \"true\" : \"false\")")
                        else:
                            args.append(arg_code)
                    return f'{expr.name}({", ".join(args)})'
                fmt_c = ""
                for i, part in enumerate(parts[:-1]):
                    spec   = self._type_to_fmt_spec(format_args[i])
                    fmt_c += part.replace("%", "%%") + spec
                fmt_c += parts[-1].replace("%", "%%")
                fmt_c  = fmt_c.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
                c_args = [f'"{fmt_c}"']
                for a in format_args:
                    arg_type = self._infer_expr_type(a)
                    arg_code = self._generate_expr(a)
                    if arg_type in ("string", "str"):
                        c_args.append(f"{arg_code}.data")
                    elif arg_type == "bool":
                        c_args.append(f"({arg_code} ? \"true\" : \"false\")")
                    else:
                        c_args.append(arg_code)
                return f'{expr.name}({", ".join(c_args)})'
            else:
                escaped = self._c_escape(first_arg.value)
                return f'{expr.name}("{escaped}")'
        else:
            arg_type = self._infer_expr_type(first_arg)
            if arg_type in ("string", "str"):
                arg_code = self._generate_expr(first_arg)
                return f'{expr.name}("%s", {arg_code}.data)'
            elif arg_type in ("f32", "f64", "float"):
                arg_code = self._generate_expr(first_arg)
                return f'{expr.name}("%g", {arg_code})'
            elif arg_type == "bool":
                arg_code = self._generate_expr(first_arg)
                return f'{expr.name}("%s", ({arg_code} ? "true" : "false"))'
            else:
                arg_code = self._generate_expr(first_arg)
                return f'{expr.name}("%d", {arg_code})'

    def _generate_struct_init(self, expr) -> str:
        """StructInit を C99 Compound literal として返す """
        fields = ", ".join(
            f".{name} = {self._generate_expr(value)}"
            for name, value in expr.fields
        )
        # ジェネリック構造体の具体化名を使用 (例: Box<i32> → Box_i32)
        if getattr(expr, 'type_args', []):
            suffix = "_".join(t if isinstance(t, str) else t.name for t in expr.type_args)
            struct_c_name = f"{expr.struct_name}_{suffix}"
        else:
            struct_c_name = expr.struct_name
        return f"({struct_c_name}){{ {fields} }}"

    def _generate_match_expr(self, expr) -> str:
        """match 式を GCC compound statement 式として生成する """
        n  = self.lambda_counter
        self.lambda_counter += 1
        mv = f"__mv_{n}"
        mr = f"__mr_{n}"

        scrutinee_c         = self._generate_expr(expr.scrutinee)
        scrutinee_type      = self._infer_expr_type(expr.scrutinee)
        scrutinee_is_string = (scrutinee_type == "string")
        result_c_type       = self._infer_match_result_c_type(expr.arms)

        zero_val = (
            '""'               if result_c_type == "const char*" else
            'make_mryl_string("")' if result_c_type == "MrylString" else
            "0"
        )

        lines = [
            "({",
            f"    __auto_type {mv} = ({scrutinee_c});",
            f"    {result_c_type} {mr} = {zero_val};",
        ]

        has_catch_all = False
        first = True
        for arm in expr.arms:
            pattern = arm.pattern
            klass   = pattern.__class__.__name__

            if klass == "BindingPattern" and pattern.name == "_":
                has_catch_all = True
                kw = "else" if not first else ""
                lines.append(f"    {kw} {{" if kw else "    {")
                lines.append(
                    f'        mryl_panic("MatchError", "reached \'_\' error arm", '
                    f'__func__, __FILE__, __LINE__);'
                )
                lines.append("    }")
                first = False
                continue

            cond, bindings = self._match_pattern_to_c(mv, pattern, scrutinee_is_string)

            if isinstance(pattern, (BindingPattern, StructPattern)):
                has_catch_all = True

            if cond == "1":
                kw        = "else" if not first else ""
                cond_part = ""
            else:
                kw        = "else if" if not first else "if"
                cond_part = f" ({cond})"
            if kw:
                lines.append(f"    {kw}{cond_part} {{")
            else:
                lines.append("    {")
            for b in bindings:
                lines.append(f"        {b}")
            body_c = self._generate_expr(arm.body)
            lines.append(f"        {mr} = {body_c};")
            lines.append("    }")
            first = False

        if not has_catch_all:
            kw = "else" if len(expr.arms) > 0 else ""
            lines.append(f"    {kw} {{" if kw else "    {")
            lines.append(
                f'        mryl_panic("MatchError", "no arm matched", '
                f'__func__, __FILE__, __LINE__);'
            )
            lines.append("    }")

        lines.append(f"    {mr};")
        lines.append("})")
        return "\n".join(lines)

    def _infer_match_result_c_type(self, arms) -> str:
        """match 式のアーム群から結果の C 型を推論する """
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
        """パターンのバインディング変数とその型のマップを返す """
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
        """パターンを (条件式文字列, バインディング文字列リスト) に変換する """
        klass = pattern.__class__.__name__

        if klass == "LiteralPattern":
            val = pattern.value
            if isinstance(val, bool):
                cond = f"{mv} == {1 if val else 0}"
            elif isinstance(val, str):
                escaped = val.replace('"', '\\"')
                cond = (
                    f'strcmp({mv}.data, "{escaped}") == 0'
                    if scrutinee_is_string else
                    f'strcmp({mv}, "{escaped}") == 0'
                )
            elif isinstance(val, float):
                cond = f"{mv} == {val}"
            else:
                cond = f"{mv} == {val}"
            return cond, []

        if klass == "BindingPattern":
            return "1", [f"__auto_type {pattern.name} = {mv};"]

        if klass == "EnumPattern":
            enum_name    = pattern.enum_name
            variant_name = pattern.variant_name
            # Result<T,E> の Ok/Err パターン
            if enum_name in ("Ok", "Err"):
                is_ok    = (enum_name == "Ok")
                cond     = f"{mv}.is_ok" if is_ok else f"!{mv}.is_ok"
                field    = "ok_val" if is_ok else "err_val"
                bindings = [f"__auto_type {name} = {mv}.data.{field};" for name in pattern.bindings]
                return cond, bindings
            enum_decl    = self.enums.get(enum_name)
            has_data     = enum_decl and any(v.fields for v in enum_decl.variants)
            if has_data:
                cond     = f"{mv}.tag == {enum_name}_Tag_{variant_name}"
                bindings = [
                    f"__auto_type {name} = {mv}.data.{variant_name}._{i};"
                    for i, name in enumerate(pattern.bindings)
                ]
            else:
                cond     = f"{mv} == {enum_name}_{variant_name}"
                bindings = []
            return cond, bindings

        if klass == "StructPattern":
            bindings = [f"__auto_type {f} = {mv}.{f};" for f in pattern.fields]
            return "1", bindings

        if klass == "RegexPattern":
            pat_escaped = pattern.pattern_str.replace("\\", "\\\\").replace('"', '\\"')
            mv_data     = f"{mv}.data" if scrutinee_is_string else mv
            uid         = id(pattern) & 0xFFFF
            cond = (
                f"({{ regex_t __re_{uid}; "
                f"regcomp(&__re_{uid}, \"{pat_escaped}\", REG_EXTENDED | REG_NOSUB); "
                f"int __rc_{uid} = regexec(&__re_{uid}, {mv_data}, 0, NULL, 0); "
                f"regfree(&__re_{uid}); "
                f"__rc_{uid} == 0; }})"
            )
            return cond, []

        return "0", []

    def _generate_method_call(self, expr) -> str:
        """MethodCall を C 式文字列として返す (Vec/Result 特殊対応含む) """
        obj_type = self._infer_expr_type(expr.obj)

        # 動的配列 (MrylVec_<T>) のメソッド
        if obj_type.startswith("vec_"):
            et       = obj_type[4:]
            obj_name = (
                expr.obj.name if expr.obj.__class__.__name__ == 'VarRef'
                else self._generate_expr(expr.obj)
            )
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

        # Result<T,E> のメソッド
        obj_type = self._infer_expr_type(expr.obj)
        if obj_type == "Result" or obj_type.startswith("Result_"):
            obj_code = self._generate_expr(expr.obj)
            if expr.method == "is_ok":
                return f"({obj_code}.is_ok)"
            if expr.method == "is_err":
                return f"(!{obj_code}.is_ok)"
            if expr.method in ("try", "unwrap", "err"):
                return (
                    f"({{ __auto_type __uw = {obj_code}; "
                    f"if (!__uw.is_ok) {{ "
                    f'mryl_panic("Error", "try() called on Err value", __func__, __FILE__, __LINE__); }} '
                    f"__uw.data.ok_val; }})"
                )
            if expr.method == "unwrap_err":
                return (
                    f"({{ __auto_type __uw = {obj_code}; "
                    f"if (__uw.is_ok) {{ "
                    f'mryl_panic("UnwrapError", "unwrap_err() called on Ok value", '
                    f'__func__, __FILE__, __LINE__); }} '
                    f"__uw.data.err_val; }})"
                )
            if expr.method == "unwrap_or":
                default_code = self._generate_expr(expr.args[0]) if expr.args else "0"
                return f"({obj_code}.is_ok ? {obj_code}.data.ok_val : {default_code})"

        obj         = self._generate_expr(expr.obj)
        args_list   = [self._generate_expr(arg) for arg in expr.args]
        struct_name = obj_type   # Bug#27: obj の型から struct 名を解決
        all_args    = [f"&({obj})"] + args_list   # Bug#28: ポインタ渡し
        return f"{struct_name}_{expr.method}({', '.join(all_args)})"

