# Mryl string.find() 詳細設計書

**バージョン**: v0.4.0
**Issue**: #54
**日付**: 2026-03-14

---

## 1. 概要

`string` 型に `find()` メソッドを追加し、部分文字列の最初の出現位置を `Option<i32>` で返す。
見つかった場合は `Some(位置)`, 見つからない場合は `None` を返す。
前提として `Option<T>` (#50) の実装が必要。

```mryl
let s: string = "hello world";

let r1 = s.find("world");
match r1 {
    Some(i) => println("found at {}", i),  // found at 6
    None    => println("not found"),
};

let r2 = "hello".find("xyz");
match r2 {
    Some(i) => println("{}", i),
    None    => println("not found"),       // not found
};
```

---

## 2. API

```
fn find(self: string, pattern: string) -> Option<i32>
```

| 引数 | 型 | 説明 |
|---|---|---|
| `self` | `string` | 検索対象文字列 |
| `pattern` | `string` | 検索するパターン |

### 動作仕様

| 入力 | 出力 | 説明 |
|---|---|---|
| `"hello world".find("world")` | `Some(6)` | 通常マッチ |
| `"hello world".find("ell")` | `Some(1)` | 先頭でないマッチ |
| `"hello world".find("xyz")` | `None` | 見つからない |
| `"hello".find("")` | `Some(0)` | 空文字列パターン → 先頭を返す |
| `"abcdef".find("abc")` | `Some(0)` | 先頭マッチ |
| `"abcdef".find("ef")` | `Some(4)` | 末尾近傍マッチ |
| `"aabaa".find("b")` | `Some(2)` | 複数出現 → 最初の位置 |

---

## 3. 設計方針

### 3.1 AST

**変更不要**。`s.find("pat")` は既存の `MethodCall(s, "find", ["pat"])` でパース可能。

### 3.2 Parser

**変更不要**。

### 3.3 Interpreter（`core/Interpreter.py`）

`_eval_string_method` に `find` を追加する。

```python
elif method == "find":
    pattern = args[0]
    idx = obj.find(pattern)   # Python の str.find() は -1 or 位置を返す
    if idx == -1:
        return MrylNone()
    return MrylSome(idx)
```

Python の `str.find()` を利用し、`-1` の場合は `MrylNone`、それ以外は `MrylSome(idx)` を返す。

### 3.4 TypeChecker（`core/TypeChecker/_call.py`）

string メソッドの型規則に `find` を追加する。

```python
elif method == "find":
    # 引数: string, 戻り値: Option<i32>
    return TypeNode("Option", type_args=[TypeNode("i32")])
```

### 3.5 C コード生成（`core/CodeGenerator/_expr.py`）

`mryl_str_find` ヘルパー関数を `_header.py` で生成し、C コード生成側から呼び出す。

#### ヘルパー関数定義（`_header.py` にて生成）

```c
static inline MrylOption_int32_t mryl_str_find(MrylString s, MrylString pat) {
    const char *p = strstr(s.data, pat.data);
    if (p == NULL) {
        return (MrylOption_int32_t){ .is_some = 0 };
    }
    return (MrylOption_int32_t){ .is_some = 1, .value = (int32_t)(p - s.data) };
}
```

空文字列パターン（`pat.length == 0`）の場合、`strstr` は先頭ポインタを返すため `Some(0)` となる（C 標準動作準拠）。

#### メソッド呼び出しの C コード生成

```c
// s.find("world")
mryl_str_find(s, mryl_str("world"))
```

---

## 4. 既知の制限（v0.4.0 スコープ外）

| 制限 | 詳細 |
|---|---|
| `find_all()` | 全出現位置を返すメソッドは未実装 |
| 後方検索 `rfind()` | 末尾から検索するメソッドは未実装 |
| 正規表現マッチ | v0.5.0 以降 |

---

## 5. テスト観点（C0 / C1 / MC/DC）

対応テストファイル: `tests/test_29_string_find.ml`

| # | ケース | 観点 | 内容 |
|---|---|---|---|
| T29-A1 | `"hello world".find("world")` → `Some(6)` | C0 | 基本マッチ |
| T29-A2 | `"hello world".find("ell")` → `Some(1)` | C0 | 先頭でないマッチ |
| T29-B1 | `s.find("xyz")` → `None` | C1 | 不一致パス |
| T29-C1 | `"hello".find("")` → `Some(0)` | C1 | 空文字列パターン |
| T29-D1 | `"abcdef".find("abc")` → `Some(0)` | C0 | 先頭マッチ |
| T29-E1 | `"abcdef".find("ef")` → `Some(4)` | C0 | 末尾マッチ |
| T29-F1 | `"aabaa".find("b")` → `Some(2)` | MC/DC | 複数出現・最初の位置 |
| T29-F2 | `"abcabc".find("bc")` → `Some(1)` | MC/DC | 複数出現・最初の位置 |
| T29-G1 | 関数戻り値として `Option<i32>` | MC/DC | 関数経由 Some パス |
| T29-G2 | 関数戻り値として `None` | MC/DC | 関数経由 None パス |
| T29-H1 | find 結果を match で分岐して計算 | MC/DC | `i + 1` 計算パス |

---

## 6. 関連

- Issue #54: https://github.com/Mryl-Dev/Mryl/issues/54
- `option_v0.4.0.md`（戻り値型 `Option<i32>` の前提）
- Issue #11: string 組み込みメソッド基盤
