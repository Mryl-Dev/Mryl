# Mryl Option\<T\> 型 詳細設計書

**バージョン**: v0.4.0
**Issue**: #50
**日付**: 2026-03-14

---

## 1. 概要

値の有無を型安全に表現する `Option<T>` 型を導入する。
`Some(value)` で値あり、`None` で値なしを表し、`match` 式でアンラップする。
Rust / Swift / Kotlin の Optional 型に相当する機能。

```mryl
fn safe_divide(a: i32, b: i32) -> Option<i32> {
    if (b == 0) { return None; }
    return Some(a / b);
}

let result = safe_divide(10, 2);
let v: i32 = match result {
    Some(n) => n,
    None    => -1,
};
println("{}", v);  // 5
```

---

## 2. API

| 構文 | 説明 |
|---|---|
| `Some(expr)` | 値 `expr` を包んだ Option を生成 |
| `None` | 値なしの Option を生成 |
| `match opt { Some(v) => ..., None => ... }` | パターンマッチでアンラップ |

### 型シグネチャ

```
Some : fn(T) -> Option<T>
None : Option<T>   （任意の T に対して多相）
```

---

## 3. 設計方針

### 3.1 AST

既存の `EnumVariant` / `MatchExpr` を流用する。新規 AST ノードは追加しない。

| 構文 | AST 表現 |
|---|---|
| `Some(v)` | `FunctionCall("Some", [v])` |
| `None` | `VarRef("None")` |
| `Option<T>` 型注釈 | `TypeNode("Option", type_args=[T])` |
| `Some(v) =>` パターン | `BindingPattern("Some", inner=BindingPattern("v"))` |
| `None =>` パターン | `LiteralPattern("None")` |

### 3.2 Parser

**変更不要**。`Some(...)` は既存の関数呼び出し構文でパース可能。
`None` は識別子として既存の VarRef でパース可能。

### 3.3 Interpreter（`core/Interpreter.py`）

`Option<T>` の内部表現として専用クラスを定義する。

```python
class MrylSome:
    def __init__(self, value): self.value = value

class MrylNone:
    pass
```

- `Some(v)` → `MrylSome(v)` を生成
- `None` → グローバル定数 `MRYL_NONE = MrylNone()` を返す
- `match` パターン:
  - `Some(bind)` アーム: `isinstance(val, MrylSome)` の場合マッチ、`bind` に `val.value` を束縛
  - `None` アーム: `isinstance(val, MrylNone)` の場合マッチ

### 3.4 TypeChecker（`core/TypeChecker/_call.py`, `_expr.py`）

#### Some の型規則

```
Some(v: T) -> Option<T>
```

- 引数型を `T` として取得し `TypeNode("Option", type_args=[T])` を返す

#### None の型規則

```
None -> Option<T>   （T は文脈から推論）
```

- 変数宣言 `let x: Option<i32> = None` では左辺の型注釈から `T = i32` を解決する
- 関数戻り値 `return None` では関数宣言の戻り値型から解決する

#### match パターン型規則

```
match (opt: Option<T>) {
    Some(v) => ...  // v: T として束縛
    None    => ...
}
```

- scrutinee が `Option<T>` の場合 `Some(v)` パターンで `v` を `T` 型として環境に追加する

### 3.5 C コード生成（`core/CodeGenerator/_header.py`, `_expr.py`）

#### 構造体定義（`_header.py` にて生成）

```c
// Option<T> 型ごとに生成
typedef struct {
    int is_some;
    int32_t value;
} MrylOption_int32_t;
```

型パラメータ `T` ごとに `MrylOption_<C型名>` を生成する。

#### Some(v) の C コード生成

```c
(MrylOption_int32_t){ .is_some = 1, .value = (expr) }
```

#### None の C コード生成

```c
(MrylOption_int32_t){ .is_some = 0 }
```

#### match パターンの C コード生成

```c
// match opt { Some(v) => body_some, None => body_none }
int32_t v;
if (opt.is_some) {
    v = opt.value;
    /* body_some */
} else {
    /* body_none */
}
```

---

## 4. 既知の制限（v0.4.0 スコープ外）

| 制限 | 詳細 |
|---|---|
| `Option<string>` の C 生成 | `MrylString` 構造体を含む Option の struct 生成は未検証 |
| `?` 演算子 | `Result<T,E>` 同様の early return 構文は v0.5.0 以降 |
| `Option<T>` へのメソッド（`map`, `unwrap_or`） | v0.5.0 以降 |

---

## 5. テスト観点（C0 / C1 / MC/DC）

対応テストファイル: `tests/test_26_option.ml`

| # | ケース | 観点 | 内容 |
|---|---|---|---|
| T26-A1 | `Some(10)` → match Some アーム実行 | C0 | Some 生成・match |
| T26-B1 | `None` → match None アーム実行 | C0 | None 生成・match |
| T26-C1 | 関数戻り値 `Some(42)` | C1 | 関数経由 Some パス |
| T26-D1 | 関数戻り値 `None` | C1 | 関数経由 None パス |
| T26-E1 | `safe_divide(10,2)` → `b==0=F` → Some | MC/DC | 条件 `b==0` が False |
| T26-E2 | `safe_divide(10,0)` → `b==0=T` → None | MC/DC | 条件 `b==0` が True |

---

## 6. 関連

- `iter_linq_v0.4.0.md`（`first()` など Iter<T> 終端操作が `Option<T>` を返す予定）
- `string_find_v0.4.0.md`（`string.find()` の戻り値が `Option<i32>`）
- Issue #50: https://github.com/Mryl-Dev/Mryl/issues/50
