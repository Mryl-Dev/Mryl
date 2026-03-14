# Mryl match _ ワイルドカードパターン 詳細設計書

**バージョン**: v0.4.0
**Issue**: #58（バグ修正）
**日付**: 2026-03-14

---

## 1. 概要

`match` 式の `_` パターンがキャッチオールワイルドカードとして正しく機能するよう修正する。
修正前は `_` アームに到達するとランタイムパニックになっていた。

```mryl
let x: i32 = 99;
let label: string = match x {
    1   => "one",
    2   => "two",
    _   => "other",   // 修正前: panic / 修正後: "other"
};
println("{}", label);  // other
```

---

## 2. 問題の詳細

### 2.1 症状

`_` パターンのアームが評価されるとランタイムエラーが発生。

```
MrylRuntimeError: '_' error arm reached with value: 42
```

### 2.2 根本原因

**Interpreter（`core/Interpreter.py`）:**

`_match_pattern()` が `BindingPattern("_")` の場合に `MrylRuntimeError` を raise していた。
本来は空バインディングとマッチ成功フラグ `({}, True)` を返すべきところ、パニック用のエラーアーム処理と混同していた。

**CodeGenerator（`core/CodeGenerator/_expr.py`）:**

`_generate_match_expr()` が `_` アームに対して通常の式コード生成を行わず、`mryl_panic()` 呼び出しを生成していた。
また、型推論時に `_` アームのボディ型が考慮されていなかったため、match 式の戻り値型が不正になる場合があった。

---

## 3. 修正方針

### 3.1 Interpreter（`core/Interpreter.py`）

`_match_pattern()` の `BindingPattern("_")` 分岐を修正する。

**修正前:**
```python
elif isinstance(pattern, BindingPattern) and pattern.name == "_":
    raise MrylRuntimeError("'_' error arm reached with value: ...")
```

**修正後:**
```python
elif isinstance(pattern, BindingPattern) and pattern.name == "_":
    return {}, True   # 空バインディング・マッチ成功
```

### 3.2 CodeGenerator（`core/CodeGenerator/_expr.py`）

`_generate_match_expr()` の `_` アームのコード生成を修正する。

**修正前:**
```c
// _ アームに対して mryl_panic() を生成していた
mryl_panic("unreachable");
```

**修正後:**
```c
// 他のアームと同様に通常の式コードを生成
// `_ => expr` → if (1) { result = expr; }
// （常に true 条件として最後のアームに配置）
```

`_` アームは常に最後に配置され、他のアームにマッチしなかった場合に実行される。
C コード生成では `else { ... }` ブランチとして出力する。

#### 型推論への `_` アームのボディ型の組み込み

match 式の戻り値型を決定する際、`_` アームのボディ型も型統合に含める。

```python
# 修正前: _ アームを無視して型推論
arm_types = [infer_type(arm.body) for arm in arms if arm.pattern != "_"]

# 修正後: _ アームも含める
arm_types = [infer_type(arm.body) for arm in arms]
```

---

## 4. 設計方針

### 4.1 AST

**変更不要**。`_` パターンは既存の `BindingPattern("_")` として表現される。

### 4.2 Parser

**変更不要**。`_` は識別子トークンとして既存のバインディングパターンでパース可能。

### 4.3 ワイルドカード使用上の制約

| 制約 | 内容 |
|---|---|
| 位置 | `_` アームは match の最後に置く必要がある（以降のアームは到達不能）|
| バインディング | `_` はバインディングを生成しない（値は捨てる）|
| 複数の `_` | 複数の `_` アームは TypeChecker で警告（v0.5.0 以降）|

### 4.4 C コード生成での `_` アームの出力

```c
// match x { 1 => "one", 2 => "two", _ => "other" }
MrylString __result;
if (x == 1) {
    __result = mryl_str("one");
} else if (x == 2) {
    __result = mryl_str("two");
} else {
    // _ アーム → else ブランチ
    __result = mryl_str("other");
}
```

Result / Option のバリアントに対する `_` アーム:

```c
// match opt { Some(v) => ..., _ => ... }
if (opt.is_some) {
    int32_t v = opt.value;
    /* body_some */
} else {
    /* body_wildcard */
}
```

---

## 5. テスト観点（C0 / C1 / MC/DC）

対応テストファイル: `tests/test_27_match_wildcard.ml`

| # | ケース | 観点 | 内容 |
|---|---|---|---|
| T27-A1 | `match 1 { 1 => ... _ => ... }` → 具体アーム実行 | C1 | _ が実行されないパス |
| T27-A2 | `match 99 { 1 => ... _ => ... }` → _ アーム実行 | C1 | _ が実行されるパス |
| T27-B1 | string scrutinee で具体アーム実行 | C1 | string match 具体パス |
| T27-B2 | string scrutinee で _ アーム実行 | C1 | string match _ パス |
| T27-C1 | `match 123 { _ => 999 }` 単一 _ アーム | C0 | _ のみのアーム |
| T27-D1 | `Result` match で `Ok` アーム実行 | C1 | Ok パス |
| T27-D2 | `Result` match で `_` が `Err` をキャッチ | C1 | _ が Err をキャッチ |
| T27-E1 | `Option` match で `Some` アーム実行 | C1 | Some パス |
| T27-E2 | `Option` match で `_` が `None` をキャッチ | C1 | _ が None をキャッチ |

---

## 6. 関連

- Issue #58: https://github.com/Mryl-Dev/Mryl/issues/58
- `option_v0.4.0.md`（Option の None を _ でキャッチするユースケース）
- ワークアラウンド: 修正前は名前付きバインディング（`n => ...` で値を無視）で代替可能だった
