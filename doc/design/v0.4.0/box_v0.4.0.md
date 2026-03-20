# Mryl Box\<T\> 型 詳細設計書

**バージョン**: v0.4.0
**Issue**: #56
**日付**: 2026-03-14

---

## 1. 概要

ヒープ上に値を確保するポインタ型 `Box<T>` を導入する。
Rust の `Box<T>` / C++ の `std::unique_ptr<T>` に相当し、C バックエンドでは `T*` として扱う。
再帰的なデータ構造（連結リスト・AST ノード等）の実現に不可欠。

```mryl
let b: Box<i32> = Box::new(42);
let v: i32 = *b;          // * デリファレンス → 42
let v2: i32 = b.unbox();  // .unbox() でも同等

// 多重ポインタ
let bb: Box<Box<i32>> = Box::new(Box::new(99));
let inner: i32 = *(*bb);  // 99
```

---

## 2. API

| 構文 | 説明 |
|---|---|
| `Box::new(expr)` | `expr` をヒープに確保し `Box<T>` を返す |
| `*b` | `Box<T>` をデリファレンスし `T` を返す |
| `b.unbox()` | `*b` と等価のメソッド構文 |
| `Box<Box<T>>` | 多重ポインタ（任意の深さ対応） |

### 型シグネチャ

```
Box::new : fn(T) -> Box<T>
*b       : Box<T> -> T
b.unbox(): Box<T> -> T
```

---

## 3. 設計方針

### 3.1 AST

既存の StaticMethodCall / Deref / MethodCall ノードを活用する。

| 構文 | AST 表現 |
|---|---|
| `Box::new(v)` | `StaticMethodCall("Box", "new", [v])` |
| `*b` | `Deref(b)` |
| `b.unbox()` | `MethodCall(b, "unbox", [])` |
| `Box<T>` 型注釈 | `TypeNode("Box", type_args=[T])` |

### 3.2 Parser

**変更不要**。
- `Box::new(v)` は既存の `::` 静的メソッド呼び出し構文でパース可能
- `*b` は既存の単項 `*` 演算子 (Deref) でパース可能
- `b.unbox()` は既存のメソッド呼び出し構文でパース可能

### 3.3 Interpreter（`core/Interpreter.py`）

`Box<T>` の内部表現として専用クラスを定義する。

```python
class MrylBox:
    def __init__(self, value): self.value = value
```

| 操作 | Python 実装 |
|---|---|
| `Box::new(v)` | `MrylBox(v)` を生成 |
| `*b` (Deref) | `b.value` を返す |
| `b.unbox()` | `b.value` を返す |
| `Box<Box<T>>` | `MrylBox(MrylBox(v))` のネスト |

### 3.4 TypeChecker（`core/TypeChecker/_call.py`, `_expr.py`）

#### Box::new の型規則

```
Box::new(v: T) -> Box<T>
```

引数型を `T` とし `TypeNode("Box", type_args=[T])` を返す。

#### Deref (*b) の型規則

```
*(b: Box<T>) -> T
```

scrutinee の型が `TypeNode("Box", type_args=[T])` の場合、`T` を返す。
多重ポインタ `Box<Box<T>>` の場合は外側を 1 段剥がした `Box<T>` を返す。

#### unbox() の型規則

```
(b: Box<T>).unbox() -> T
```

`*b` と同一の型規則を適用する。

### 3.5 C コード生成（`core/CodeGenerator/_expr.py`, `_type.py`）

C バックエンドでは `Box<T>` を `T*` として扱う。

#### 型変換（`_type.py`）

```python
# Box<T> → T*
TypeNode("Box", type_args=[T]) → f"{c_type(T)}*"

# Box<Box<T>> → T**
TypeNode("Box", type_args=[Box<T>]) → f"{c_type(T)}**"
```

#### Box::new(v) の C コード生成

```c
// Box<i32> b = Box::new(42);
// → 生成コード
int32_t* __b = (int32_t*)malloc(sizeof(int32_t));
*__b = 42;
```

省略形（式として使う場合は statement expression）:

```c
({ int32_t* __p = (int32_t*)malloc(sizeof(int32_t)); *__p = (expr); __p; })
```

#### Deref (*b) の C コード生成

```c
(*b)
```

多重デリファレンス `*(*bb)` はそのまま C の `*(*bb)` として出力する。

#### unbox() の C コード生成

```c
(*b)   // *b と等価
```

---

## 4. 既知の制限（v0.4.0 スコープ外）

| 制限 | 詳細 |
|---|---|
| `free()` の自動挿入 | Box のライフタイムを追わず free しない（メモリリーク） |
| `Box<string>` | `MrylString` 構造体を包む場合の C 型生成は未検証 |
| 再帰的 struct での使用 | `struct Node { val: i32; next: Box<Node>; }` は v0.5.0 以降 |
| ミュータブル書き込み | `*b = new_val` の代入構文は未実装 |

---

## 5. テスト観点（C0 / C1 / MC/DC）

対応テストファイル: `tests/test_28_box.ml`

| # | ケース | 観点 | 内容 |
|---|---|---|---|
| T28-A1 | `Box::new(42)` → `*b` → 42 | C0 | 基本生成・deref |
| T28-A2 | `Box::new(-7)` → `*b` → -7 | C0 | 負数値 |
| T28-B1 | `Box::new(100)` → `.unbox()` → 100 | C1 | unbox パス |
| T28-B2 | `Box::new(0)` → `.unbox()` → 0 | C1 | ゼロ値 |
| T28-C1 | `Box<f64>` の `*` deref | C0 | f64 型 |
| T28-D1 | `Box<bool>` の `.unbox()` | C0 | bool 型 |
| T28-E1 | 関数引数・戻り値として `Box<T>` | C1 | 関数経由パス |
| T28-F1 | `Box<Box<i32>>` 2重ポインタ | MC/DC | 多重ネスト deref |
| T28-G1 | `Box<Box<Box<i32>>>` 3重 | MC/DC | 3重ネスト |
| T28-H1 | `Box<Box<Box<Box<i32>>>>` 4重 | MC/DC | 4重ネスト |

---

## 6. 関連

- Issue #56: https://github.com/Mryl-Dev/Mryl/issues/56
- `option_v0.4.0.md`（Option<T> との組み合わせで再帰構造の要素が Option になりうる）
