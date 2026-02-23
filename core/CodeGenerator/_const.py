from __future__ import annotations
from Ast import NumberLiteral, StringLiteral, BoolLiteral, BinaryOp
from CodeGenerator._proto import _CodeGeneratorBase

class CodeGeneratorConstMixin(_CodeGeneratorBase):
    """定数宣言・定数式評価を担当する Mixin
    _generate_const / _eval_const_expr
    """

    def _generate_const(self, const_decl):
        """ConstDecl を #define ディレクティブとして出力する """
        try:
            value = self._eval_const_expr(const_decl.init_expr)
            self._emit(f"#define {const_decl.name} {value}")
            self.const_table[const_decl.name] = value
        except Exception as e:
            error_msg = str(e).replace('"', "'")
            self._emit(f"// #define {const_decl.name} (error: {error_msg})")

    def _eval_const_expr(self, expr):
        """コード生成時に定数式を評価する """
        if isinstance(expr, NumberLiteral):
            return expr.value
        elif isinstance(expr, StringLiteral):
            return f'"{expr.value}"'
        elif isinstance(expr, BoolLiteral):
            return "1" if expr.value else "0"
        elif hasattr(expr, '__class__') and expr.__class__.__name__ == 'VarRef':
            if hasattr(expr, 'name') and expr.name in self.const_table:
                return self.const_table[expr.name]
            raise ValueError(f"Undefined const: {expr.name if hasattr(expr, 'name') else expr}")
        elif hasattr(expr, '__class__') and expr.__class__.__name__ == 'Identifier':
            if hasattr(expr, 'name') and expr.name in self.const_table:
                return self.const_table[expr.name]
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
            left_val  = self._eval_const_expr(expr.left)
            right_val = self._eval_const_expr(expr.right)

            if isinstance(left_val, str) or isinstance(right_val, str):
                if expr.op == '+':
                    return f'({left_val} {right_val})'
                raise ValueError(f"Unsupported operator on strings: {expr.op}")

            if expr.op == '+':   return left_val + right_val
            elif expr.op == '-': return left_val - right_val
            elif expr.op == '*': return left_val * right_val
            elif expr.op == '/':
                if right_val == 0:
                    raise ValueError("Division by zero in const expression")
                return left_val // right_val if isinstance(left_val, int) else left_val / right_val
            elif expr.op == '%':  return left_val % right_val
            elif expr.op == '==': return 1 if left_val == right_val else 0
            elif expr.op == '!=': return 1 if left_val != right_val else 0
            elif expr.op == '<':  return 1 if left_val < right_val else 0
            elif expr.op == '>':  return 1 if left_val > right_val else 0
            elif expr.op == '<=': return 1 if left_val <= right_val else 0
            elif expr.op == '>=': return 1 if left_val >= right_val else 0
            elif expr.op == '&&': return 1 if left_val and right_val else 0
            elif expr.op == '||': return 1 if left_val or right_val else 0
            elif expr.op == '&':  return left_val & right_val
            elif expr.op == '|':  return left_val | right_val
            elif expr.op == '^':  return left_val ^ right_val
            elif expr.op == '<<': return left_val << right_val
            elif expr.op == '>>': return left_val >> right_val
            else:
                raise ValueError(f"Unsupported operator in const expression: {expr.op}")
        else:
            raise ValueError(f"Cannot evaluate expression type in const context: {type(expr)}")
