from __future__ import annotations

from Ast import TypeNode
from MrylError import TypeError_

# ============================================
# 型分類定数（全 Mixin の共通参照元）
# ============================================
INTEGER_TYPES: frozenset[str] = frozenset({
    "i8", "i16", "i32", "i64",
    "u8", "u16", "u32", "u64",
})
FLOAT_TYPES:   frozenset[str] = frozenset({"f32", "f64"})
NUMERIC_TYPES: frozenset[str] = INTEGER_TYPES | FLOAT_TYPES

# ============================================
# 型分類純粋関数
# ============================================

def is_integer_type(type_name: str) -> bool:
    """整数型（符号あり・符号なし・旧 int）かどうか。"""
    return type_name in INTEGER_TYPES or type_name == "int"


def is_float_type(type_name: str) -> bool:
    """浮動小数点型かどうか。"""
    return type_name in FLOAT_TYPES


def is_numeric_type(type_name: str) -> bool:
    """数値型（整数 or 浮動小数点）かどうか。"""
    return is_integer_type(type_name) or is_float_type(type_name)


def is_signed_int(type_name: str) -> bool:
    """符号あり整数型かどうか。"""
    return type_name in ("i8", "i16", "i32", "i64")


def is_unsigned_int(type_name: str) -> bool:
    """符号なし整数型かどうか。"""
    return type_name in ("u8", "u16", "u32", "u64")


def numeric_type_rank(type_name: str) -> int:
    """数値型のランクを返す。大きいほど「大きい型」。"""
    ranks = {
        "i8": 1, "i16": 2, "i32": 3, "i64": 4,
        "u8": 5, "u16": 6, "u32": 7, "u64": 8,
        "f32": 9, "f64": 10,
    }
    return ranks.get(type_name, -1)


def find_common_numeric_type(a: TypeNode, b: TypeNode) -> TypeNode:
    """2 つの数値型の共通上位型を返す。

    昇格ルール:
        符号あり同士 / 符号なし同士 → より大きい型
        整数 + 浮動小数点             → f64
        符号あり + 符号なし           → TypeError_
    """
    a_name, b_name = a.name, b.name

    if a_name == b_name:
        return a

    # どちらかが浮動小数点
    if is_float_type(a_name) or is_float_type(b_name):
        if is_float_type(a_name) and is_float_type(b_name):
            return a if numeric_type_rank(a_name) >= numeric_type_rank(b_name) else b
        return TypeNode("f64")

    # 符号なし + 符号なし
    if is_unsigned_int(a_name) and is_unsigned_int(b_name):
        return a if numeric_type_rank(a_name) >= numeric_type_rank(b_name) else b

    # 符号あり + 符号あり
    if is_signed_int(a_name) and is_signed_int(b_name):
        return a if numeric_type_rank(a_name) >= numeric_type_rank(b_name) else b

    # 符号あり + 符号なし → 昇格不可
    raise TypeError_(f"Cannot find common type for {a_name} and {b_name}")
