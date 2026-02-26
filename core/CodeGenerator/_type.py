from __future__ import annotations
from CodeGenerator._proto import _CodeGeneratorBase


class CodeGeneratorTypeMixin(_CodeGeneratorBase):
    """型変換を担当する Mixin
    _type_to_c / _type_to_c_base / _type_to_fmt_spec / _emit_result_typedefs
    """

    def _type_to_c(self, type_node) -> str:
        """Mryl TypeNode を C 型文字列に変換する。
        副作用: Result<T,E> の初回変換時に self.result_type_registry へ登録する。
        """
        if not type_node:
            return "void"

        type_map = {
            "i8": "int8_t", "i16": "int16_t", "i32": "int32_t", "i64": "int64_t",
            "u8": "uint8_t", "u16": "uint16_t", "u32": "uint32_t", "u64": "uint64_t",
            "f32": "float", "f64": "double",
            "string": "MrylString", "bool": "int", "int": "int32_t", "void": "void",
        }

        type_name = type_node.name or ""
        base_type = type_map.get(type_name, type_name)

        if type_node.name == "Future":
            return "MrylTask*"

        if type_node.name == "Result":
            if type_node.type_args and len(type_node.type_args) == 2:
                ok_c  = self._type_to_c(type_node.type_args[0])
                err_c = self._type_to_c(type_node.type_args[1])
                struct_name = (
                    f"MrylResult_{ok_c}_{err_c}"
                    .replace("*", "Ptr")
                    .replace(" ", "_")
                )
                self.result_type_registry.add((ok_c, err_c, struct_name))
                return struct_name
            return "MrylResult_i32_i32"

        if type_node.name == "fn":
            return "void*"

        if type_node.array_size:
            return f"{base_type}[{type_node.array_size}]"

        return base_type

    def _type_to_c_base(self, type_name: str) -> str:
        """TypeNode なしで型名文字列を C 型文字列に変換する """
        type_map = {
            "i8": "int8_t", "i16": "int16_t", "i32": "int32_t", "i64": "int64_t",
            "u8": "uint8_t", "u16": "uint16_t", "u32": "uint32_t", "u64": "uint64_t",
            "f32": "float", "f64": "double",
            "string": "MrylString", "bool": "int", "int": "int32_t", "void": "void",
        }
        return type_map.get(type_name, type_name)

    def _type_to_fmt_spec(self, arg_expr) -> str:
        """printf 書式指定子を式の型から推定する。"""
        t = self._infer_expr_type(arg_expr)
        if t in ("string", "str"):
            return "%s"
        if t in ("f32", "f64", "float"):
            return "%g"
        if t in ("i64",):
            return "%lld"
        if t in ("u64",):
            return "%llu"
        if t in ("u32", "u16", "u8"):
            return "%u"
        if t in ("bool",):
            return "%s"
        return "%d"

    def _emit_result_typedefs(self):
        """result_type_registry に登録済みの Result<T,E> 型を typedef として出力する """
        if not self.result_type_registry:
            return
        self._emit("// ===== Result<T,E> type structs =====")
        for (ok_c, err_c, struct_name) in sorted(self.result_type_registry):
            self._emit(f"typedef struct {{")
            self._emit(f"    int is_ok;")
            self._emit(f"    union {{ {ok_c} ok_val; {err_c} err_val; }} data;")
            self._emit(f"}} {struct_name};")
        self._emit("")
