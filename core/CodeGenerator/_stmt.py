from __future__ import annotations
from CodeGenerator._util import _safe_c_name
from CodeGenerator._proto import _CodeGeneratorBase

class CodeGeneratorStmtMixin(_CodeGeneratorBase):
    """文(Statement)レベルの C コード生成を担当する Mixin
    _generate_statement / _generate_conditional_block / _generate_let /
    _generate_return / _generate_if / _generate_if_inline /
    _generate_while / _generate_for / _generate_array_element
    """

    def _generate_statement(self, stmt):
        """文ノードを C コードとして出力する (ディスパッチャ) """
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
            target = self._generate_expr(stmt.target)
            value  = self._generate_expr(stmt.expr)
            self._emit(f"{target} = {value};")
        elif stmt_class == "ConditionalBlock":
            self._generate_conditional_block(stmt)
        else:
            self._emit(f"// Unknown statement: {stmt_class}")

    def _generate_conditional_block(self, stmt):
        """条件コンパイルブロック (#if 相当) を評価して出力する """
        condition_value = False

        if isinstance(stmt.condition_expr, str):
            if stmt.condition_expr in self.const_table:
                condition_value = bool(self.const_table[stmt.condition_expr])
        elif isinstance(stmt.condition_expr, tuple) and stmt.condition_expr[0] == 'not':
            const_name = stmt.condition_expr[1]
            condition_value = (const_name not in self.const_table) or \
                              not bool(self.const_table[const_name])
        else:
            try:
                result = self._eval_const_expr(stmt.condition_expr)
                condition_value = bool(result)
            except Exception:
                condition_value = False

        if condition_value:
            for s in stmt.then_block.statements:
                self._generate_statement(s)
        elif stmt.else_block:
            for s in stmt.else_block.statements:
                self._generate_statement(s)

    def _generate_let(self, stmt):
        """let 宣言を C 変数宣言として出力する """
        type_node       = stmt.type_node
        init_expr_class = stmt.init_expr.__class__.__name__ if stmt.init_expr else None

        var_type = self._type_to_c(type_node)

        # ラムダ式: 関数ポインタ変数として宣言
        if init_expr_class == "Lambda":
            lam_name, ret_type, params_str, captures = self._generate_lambda_inline(stmt.init_expr, stmt.name)
            c_var_name = _safe_c_name(stmt.name)
            if c_var_name != stmt.name:
                self.ident_renames[stmt.name] = c_var_name
            if captures:
                env_struct   = f"{lam_name}_env_t"
                closure_type = f"{lam_name}_closure_t"
                self._emit(f"{closure_type} {c_var_name};")
                self._emit(f"{c_var_name}.fn = {lam_name};")
                for cap_name in captures:
                    self._emit(f"{c_var_name}.env.{cap_name} = {cap_name};")
                self.env[-1][stmt.name] = "fn_closure"
                self.closure_env_types[stmt.name] = lam_name
            else:
                self._emit(f"{ret_type} (*{c_var_name})({params_str}) = {lam_name};")
                if ret_type == "MrylTask*":
                    self.env[-1][stmt.name] = "async_fn"
                    self.async_lambda_factories[stmt.name] = lam_name
                else:
                    self.env[-1][stmt.name] = "fn"
            return

        # FunctionCall 引数の StringLiteral を一時変数化
        temp_string_mapping = {}
        if init_expr_class == "FunctionCall":
            for i, arg in enumerate(stmt.init_expr.args):
                if arg.__class__.__name__ == "StringLiteral":
                    temp_var_name = f"__temp_str_{self.temp_string_counter}"
                    self.temp_string_counter += 1
                    escaped = self._c_escape(arg.value)
                    self._emit(f'MrylString {temp_var_name} = make_mryl_string("{escaped}");')
                    self.local_string_vars.append(temp_var_name)
                    temp_string_mapping[id(arg)] = temp_var_name

        init_expr = self._generate_expr_with_temps(stmt.init_expr, temp_string_mapping)

        # 動的配列 (array_size == -1): MrylVec_<T>
        if type_node and type_node.array_size == -1:
            et = type_node.name
            _c_map = {
                "i8": "int8_t", "i16": "int16_t", "i32": "int32_t", "i64": "int64_t",
                "u8": "uint8_t", "u16": "uint16_t", "u32": "uint32_t", "u64": "uint64_t",
                "f32": "float", "f64": "double", "bool": "int",
            }
            ct = _c_map.get(et, "int32_t")
            if init_expr_class == "ArrayLiteral" and stmt.init_expr.elements:
                elements  = [self._generate_expr(elem) for elem in stmt.init_expr.elements]
                elems_str = ", ".join(elements)
                n         = len(stmt.init_expr.elements)
                self._emit(f"MrylVec_{et} {stmt.name} = mryl_vec_{et}_from(({ct}[]){{{elems_str}}}, {n});")
            else:
                self._emit(f"MrylVec_{et} {stmt.name} = mryl_vec_{et}_new();")
            self.vec_var_types[stmt.name] = et
            self.env[-1][stmt.name] = f"vec_{et}"
            return

        # 固定長配列
        if type_node and type_node.array_size is not None and type_node.array_size > 0:
            base_type = self._type_to_c_base(type_node.name)
            if init_expr_class == "ArrayLiteral":
                elements    = [self._generate_expr(elem) for elem in stmt.init_expr.elements]
                init_values = "{" + ", ".join(elements) + "}"
                self._emit(f"{base_type} {stmt.name}[{type_node.array_size}] = {init_values};")
            else:
                self._emit(f"{base_type} {stmt.name}[{type_node.array_size}] = {{0}};")
            self.array_sizes[stmt.name] = type_node.array_size
            self.env[-1][stmt.name] = type_node.name
        elif init_expr_class == "ArrayLiteral":
            array_lit   = stmt.init_expr
            array_size  = len(array_lit.elements)
            elements    = [self._generate_expr(elem) for elem in array_lit.elements]
            init_values = "{" + ", ".join(elements) + "}"
            # 要素型を推論する (文字列配列は MrylString、数値配列は int32_t など)
            _c_elem_map = {
                "i8": "int8_t", "i16": "int16_t", "i32": "int32_t", "i64": "int64_t",
                "u8": "uint8_t", "u16": "uint16_t", "u32": "uint32_t", "u64": "uint64_t",
                "f32": "float", "f64": "double", "string": "MrylString", "bool": "int",
            }
            if array_lit.elements:
                elem_mryl = self._infer_expr_type(array_lit.elements[0])
            else:
                elem_mryl = "i32"
            elem_c = _c_elem_map.get(elem_mryl, "int32_t")
            self._emit(f"{elem_c} {stmt.name}[{array_size}] = {init_values};")
            self.array_sizes[stmt.name] = array_size
            self.env[-1][stmt.name] = elem_mryl
        else:
            # ジェネリック構造体の具体化 (例: Box<i32> → var_type = "Box_i32")
            if init_expr_class == "StructInit" and getattr(stmt.init_expr, 'type_args', []):
                suffix = "_".join(t if isinstance(t, str) else t.name for t in stmt.init_expr.type_args)
                var_type = f"{stmt.init_expr.struct_name}_{suffix}"
            elif var_type in ("any",) and stmt.init_expr is not None:
                inferred_mryl = self._infer_expr_type(stmt.init_expr)
                if inferred_mryl == "string":
                    var_type = "MrylString"
                else:
                    c = self._type_to_c_base(inferred_mryl)
                    var_type = c if c not in ("any", "") else "int32_t"
            self._emit(f"{var_type} {stmt.name} = {init_expr};")
            if type_node:
                self.env[-1][stmt.name] = type_node.name
                if type_node.name == "string":
                    self.local_string_vars.append(stmt.name)
            else:
                inferred_type = self._infer_expr_type(stmt.init_expr)
                self.env[-1][stmt.name] = inferred_type
                if inferred_type == "string":
                    self.local_string_vars.append(stmt.name)

    def _generate_return(self, stmt):
        """return 文を出力する。Ok/Err は Result compound literal に変換する """
        if stmt.expr:
            expr_class = stmt.expr.__class__.__name__
            if expr_class == "FunctionCall" and stmt.expr.name in ("Ok", "Err") \
                    and self.current_return_type:
                val_code    = self._generate_expr(stmt.expr.args[0]) if stmt.expr.args else "0"
                struct_name = self.current_return_type
                for (ok_c, err_c, sname) in self.result_type_registry:
                    if sname == struct_name:
                        if stmt.expr.name == "Ok":
                            self._emit(f"return ({struct_name}){{1, {{.ok_val = {val_code}}}}};")
                        else:
                            self._emit(f"return ({struct_name}){{0, {{.err_val = {val_code}}}}};")
                        return
                # fallback
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
        """if/else if/else 文を出力する """
        cond = self._generate_expr(stmt.condition)
        self._emit(f"if ({self._strip_outer_parens(cond)}) {{")
        self.indent_level += 1
        for s in stmt.then_block.statements:
            self._generate_statement(s)
        self.indent_level -= 1

        cur = stmt.else_block
        while cur is not None:
            if cur.__class__.__name__ == 'IfStmt':
                cur_cond = self._generate_expr(cur.condition)
                self._emit(f"}} else if ({self._strip_outer_parens(cur_cond)}) {{")
                self.indent_level += 1
                for s in cur.then_block.statements:
                    self._generate_statement(s)
                self.indent_level -= 1
                cur = cur.else_block
            else:
                self._emit("} else {")
                self.indent_level += 1
                for s in cur.statements:
                    self._generate_statement(s)
                self.indent_level -= 1
                cur = None

        self._emit("}")

    def _generate_if_inline(self, stmt):
        """インライン if 式 (内部利用; _generate_if に委譲) """
        self._generate_if(stmt)

    def _generate_while(self, stmt):
        """while ループを出力する。"""
        cond = self._generate_expr(stmt.condition)
        self._emit(f"while ({self._strip_outer_parens(cond)}) {{")
        self.indent_level += 1
        saved_str_vars = list(self.local_string_vars)
        for s in stmt.body.statements:
            self._generate_statement(s)
        for vn in self.local_string_vars:
            if vn not in saved_str_vars:
                self._emit(f"free_mryl_string({vn});")
        self.local_string_vars = saved_str_vars
        self.indent_level -= 1
        self._emit("}")

    def _generate_for(self, stmt):
        """for ループを出力する (C スタイル / Range / 配列 / Vec) """
        if stmt.is_c_style:
            var_name  = stmt.variable
            init_expr = self._generate_expr(stmt.iterable)
            init_code = f"int32_t {var_name} = {init_expr}"

            cond_code = self._generate_expr(stmt.condition) if stmt.condition else "1"
            if stmt.update:
                if stmt.update.__class__.__name__ == "Assignment":
                    target_c  = self._generate_expr(stmt.update.target)
                    value_c   = self._generate_expr(stmt.update.expr)
                    update_code = f"{target_c} = {value_c}"
                else:
                    update_code = self._generate_expr(stmt.update)
                update_code = self._strip_outer_parens(update_code)
            else:
                update_code = ""
            cond_code = self._strip_outer_parens(cond_code)
            self._emit(f"for ({init_code}; {cond_code}; {update_code}) {{")
        else:
            if stmt.iterable.__class__.__name__ == "Range":
                range_expr = stmt.iterable
                start  = self._generate_expr(range_expr.start)
                end    = self._generate_expr(range_expr.end)
                cmp_op = "<=" if range_expr.inclusive else "<"
                self._emit(
                    f"for (int {stmt.variable} = {start}; "
                    f"{stmt.variable} {cmp_op} {end}; {stmt.variable}++) {{"
                )
            elif stmt.iterable.__class__.__name__ == "ArrayLiteral":
                array_size    = len(stmt.iterable.elements)
                loop_var_name = f"__i{self.loop_counter}"
                self.loop_counter += 1
                self._emit(
                    f"for (int {loop_var_name} = 0; "
                    f"{loop_var_name} < {array_size}; {loop_var_name}++) {{"
                )
                self.indent_level += 1
                self._emit(
                    f"int32_t {stmt.variable} = "
                    f"({self._generate_array_element(stmt.iterable, loop_var_name)});"
                )
                for s in stmt.body.statements:
                    self._generate_statement(s)
                self.indent_level -= 1
                self._emit("}")
                return
            elif stmt.iterable.__class__.__name__ == "VarRef":
                var_name = stmt.iterable.name
                if var_name in self.vec_var_types:
                    et            = self.vec_var_types[var_name]
                    loop_var_name = f"__i{self.loop_counter}"
                    self.loop_counter += 1
                    self._emit(
                        f"for (int32_t {loop_var_name} = 0; "
                        f"{loop_var_name} < {var_name}.len; {loop_var_name}++) {{"
                    )
                    self.indent_level += 1
                    ct = {
                        "i8": "int8_t", "i16": "int16_t", "i32": "int32_t", "i64": "int64_t",
                        "u8": "uint8_t", "u16": "uint16_t", "u32": "uint32_t", "u64": "uint64_t",
                        "f32": "float",  "f64": "double",   "bool": "int",
                        "string": "MrylString",
                    }.get(et, "int32_t")
                    self._emit(f"{ct} {stmt.variable} = {var_name}.data[{loop_var_name}];")
                    self.env[-1][stmt.variable] = et
                    saved_str_vars = list(self.local_string_vars)
                    for s in stmt.body.statements:
                        self._generate_statement(s)
                    for vn in self.local_string_vars:
                        if vn not in saved_str_vars:
                            self._emit(f"free_mryl_string({vn});")
                    self.local_string_vars = saved_str_vars
                    self.indent_level -= 1
                    self._emit("}")
                    return
                elif var_name in self.array_sizes:
                    array_size    = self.array_sizes[var_name]
                    loop_var_name = f"__i{self.loop_counter}"
                    self.loop_counter += 1
                    self._emit(
                        f"for (int {loop_var_name} = 0; "
                        f"{loop_var_name} < {array_size}; {loop_var_name}++) {{"
                    )
                    self.indent_level += 1
                    _c_arr_map = {
                        "i8": "int8_t", "i16": "int16_t", "i32": "int32_t", "i64": "int64_t",
                        "u8": "uint8_t", "u16": "uint16_t", "u32": "uint32_t", "u64": "uint64_t",
                        "f32": "float", "f64": "double", "string": "MrylString", "bool": "int",
                    }
                    arr_elem_type = self.env[-1].get(var_name, 'i32')
                    arr_elem_c    = _c_arr_map.get(arr_elem_type, arr_elem_type)
                    self._emit(f"{arr_elem_c} {stmt.variable} = {var_name}[{loop_var_name}];")
                    self.env[-1][stmt.variable] = arr_elem_type
                    saved_str_vars = list(self.local_string_vars)
                    for s in stmt.body.statements:
                        self._generate_statement(s)
                    for vn in self.local_string_vars:
                        if vn not in saved_str_vars:
                            self._emit(f"free_mryl_string({vn});")
                    self.local_string_vars = saved_str_vars
                    self.indent_level -= 1
                    self._emit("}")
                    return
                else:
                    self._emit(f"// WARNING: Array size unknown for {var_name}, using fallback")
                    self._emit(
                        f"for (int {stmt.variable} = 0; "
                        f"{stmt.variable} < sizeof({var_name})/sizeof({var_name}[0]); "
                        f"{stmt.variable}++) {{"
                    )
            else:
                iterable = self._generate_expr(stmt.iterable)
                self._emit(f"// for ({stmt.variable} in {iterable})")
                self._emit(
                    f"for (int {stmt.variable} = 0; {stmt.variable} < 10; {stmt.variable}++) {{"
                )

        self.indent_level += 1
        saved_str_vars = list(self.local_string_vars)
        for s in stmt.body.statements:
            self._generate_statement(s)
        for vn in self.local_string_vars:
            if vn not in saved_str_vars:
                self._emit(f"free_mryl_string({vn});")
        self.local_string_vars = saved_str_vars
        self.indent_level -= 1
        self._emit("}")

    def _generate_array_element(self, array_expr, index) -> str:
        """配列式とインデックスから要素アクセス式を生成する """
        arr_code = self._generate_expr(array_expr)
        return f"{arr_code}[{index}]"
