from __future__ import annotations
from CodeGenerator._proto import _CodeGeneratorBase

# C言語予約語 (Mryl 変数名と衝突する可能性がある)
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


class CodeGeneratorUtilMixin(_CodeGeneratorBase):
    """副作用のない純粋ユーティリティ静的メソッド群 """

    @staticmethod
    def _c_escape(s: str) -> str:
        """Python 文字列を C 文字列リテラル用にエスケープする """
        return (
            s
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
            .replace("\r", "\\r")
        )

    @staticmethod
    def _strip_outer_parens(s: str) -> str:
        """冗長な外側の括弧を1層だけ除去する
        例: '(a < 10)' -> 'a < 10', '((a+b) > c)' -> '(a+b) > c'
        """
        s = s.strip()
        if len(s) < 2 or s[0] != '(' or s[-1] != ')':
            return s
        # GCC compound statement expression ({ ... }) — 外側の括弧を除去しない
        if s.startswith('({'):
            return s
        depth = 0
        for i, c in enumerate(s):
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            if depth == 0 and i < len(s) - 1:
                return s
        return s[1:-1]

    @staticmethod
    def _to_pascal(name: str) -> str:
        """snake_case を PascalCase に変換する """
        return ''.join(w.capitalize() for w in name.split('_'))
