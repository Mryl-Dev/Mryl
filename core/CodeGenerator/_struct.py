from __future__ import annotations
from CodeGenerator._proto import _CodeGeneratorBase

class CodeGeneratorStructMixin(_CodeGeneratorBase):
    """構造体・列挙型の C コード生成を担当する Mixin
    _generate_struct / _generate_enum /
    _generate_enum_variant_expr / _infer_struct_name
    """

    def _generate_struct(self, struct):
        """構造体宣言を typedef struct として出力する。"""
        if getattr(struct, 'type_params', None):
            return  # ジェネリック構造体は具体化時に _scan_generic_struct_uses で出力
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
        """EnumDecl を C コードとして出力する

        - フィールドなし: typedef enum { Name_A, Name_B } Name;
        - データあり: タグ付き共用体 + コンストラクタ関数
        """
        name     = enum_decl.name
        variants = enum_decl.variants
        has_data = any(v.fields for v in variants)

        self._emit(f"// Enum: {name}")

        if not has_data:
            constants = ", ".join(f"{name}_{v.name}" for v in variants)
            self._emit(f"typedef enum {{ {constants} }} {name};")
            self._emit("")
            return

        # タグ enum
        tag_entries = ", ".join(f"{name}_Tag_{v.name}" for v in variants)
        self._emit(f"typedef enum {{ {tag_entries} }} {name}_Tag;")

        # タグ + union の外側構造体
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

        # コンストラクタ関数 (static inline)
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

    def _generate_enum_variant_expr(self, expr) -> str:
        """EnumVariantExpr を C 式文字列として返す。
        TypeName::method(args)  → C 関数呼び出し (static fn)
        TypeName::method        → C 関数名 (fn 型変数への参照用)
        EnumName::Variant(args) → タグ付き共用体コンストラクタ
        """
        type_name    = expr.enum_name
        member_name  = expr.variant_name

        # struct の static fn かを判定
        struct_decl = None
        for s in self.structs:
            if s.name == type_name:
                struct_decl = s
                break

        if struct_decl is not None:
            method = next(
                (m for m in struct_decl.methods if m.name == member_name and getattr(m, 'is_static', False)),
                None
            )
            if method:
                c_func = f"{type_name}_{member_name}"
                if expr.has_parens:
                    arg_strs = [self._generate_expr(a) for a in expr.args]
                    return f"{c_func}({', '.join(arg_strs)})"
                else:
                    # 参照: C 関数名をそのまま返す（関数ポインタ代入用）
                    return c_func

        # enum variant (既存の処理)
        enum_decl    = self.enums.get(type_name)
        has_data     = enum_decl and any(v.fields for v in enum_decl.variants)

        if has_data:
            arg_strs = [self._generate_expr(a) for a in expr.args]
            return f"{type_name}_{member_name}({', '.join(arg_strs)})"
        return f"{type_name}_{member_name}"

    def _infer_struct_name(self, method_name) -> str:
        """メソッド名から所属する構造体名を推論する """
        for struct in self.structs:
            for method in struct.methods:
                if method.name == method_name:
                    return struct.name
        return "Object"
