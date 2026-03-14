# Mryl string.split() 詳細設計書

**バージョン**: v0.4.0
**Issue**: #55
**日付**: 2026-03-14

---

## 1. 概要

`string` 型に `split()` メソッドを追加し、区切り文字列で分割した `string[]` を返す。
主な用途は CSV パースや単語分割など。`Iter<T>` (#43) との連携（`.split(...).filter(...)`）も想定している。

```mryl
let parts: string[] = "apple,banana,cherry".split(",");
println("{}", parts.len());   // 3
println("{}", parts[0]);      // apple
println("{}", parts[1]);      // banana
```

---

## 2. API

```
fn split(self: string, delim: string) -> string[]
```

| 引数 | 型 | 説明 |
|---|---|---|
| `self` | `string` | 分割対象文字列 |
| `delim` | `string` | 区切り文字列 |

### 動作仕様

| 入力 | 出力 | 説明 |
|---|---|---|
| `"a,b,c".split(",")` | `["a","b","c"]` | 通常の分割 |
| `"abc".split("x")` | `["abc"]` | 区切りなし → 1 要素 |
| `"hello".split("")` | `["h","e","l","l","o"]` | 空文字列区切り → 1 文字ずつ |
| `"abcXYZdef".split("XYZ")` | `["abc","def"]` | 複数文字区切り |
| `",a,".split(",")` | `["","a",""]` | 先頭・末尾の区切りで空要素が生まれる |
| `"a b c".split(" ")` | `["a","b","c"]` | スペース区切り |

---

## 3. 設計方針

### 3.1 AST

**変更不要**。`s.split(",")` は既存の `MethodCall(s, "split", [","])` でパース可能。

### 3.2 Parser

**変更不要**。

### 3.3 Interpreter（`core/Interpreter.py`）

`_eval_string_method` に `split` を追加する。

```python
elif method == "split":
    delim = args[0]
    if delim == "":
        # 空文字列区切り → 1文字ずつ
        result = list(obj)
    else:
        result = obj.split(delim)
    # MrylVec として返す（動的配列）
    return result   # Python list → Interpreter 内部では list のまま扱う
```

Python の `str.split()` を利用する。ただし Python の `str.split("")` は `ValueError` になるため、空文字列の場合は `list(obj)` で 1 文字ずつ分割する。

### 3.4 TypeChecker（`core/TypeChecker/_call.py`）

string メソッドの型規則に `split` を追加する。

```python
elif method == "split":
    # 引数: string, 戻り値: string[]（動的配列）
    return TypeNode("string", array_size=-1)
```

### 3.5 C コード生成（`core/CodeGenerator/_header.py`, `_expr.py`）

`mryl_str_split` ヘルパー関数を `_header.py` で生成し、C コード生成側から呼び出す。

#### ヘルパー関数定義（`_header.py` にて生成）

```c
static inline MrylVec_MrylString mryl_str_split(MrylString s, MrylString delim) {
    MrylVec_MrylString result;
    result.data = (MrylString*)malloc(sizeof(MrylString) * (s.length + 1));
    result.len = 0;
    result.cap = s.length + 1;

    if (delim.length == 0) {
        // 空文字列区切り → 1文字ずつ
        for (int i = 0; i < s.length; i++) {
            char *buf = (char*)malloc(2);
            buf[0] = s.data[i];
            buf[1] = '\0';
            result.data[result.len++] = (MrylString){ .data = buf, .length = 1 };
        }
        return result;
    }

    const char *p = s.data;
    const char *found;
    while ((found = strstr(p, delim.data)) != NULL) {
        size_t seg = found - p;
        char *buf = (char*)malloc(seg + 1);
        memcpy(buf, p, seg);
        buf[seg] = '\0';
        result.data[result.len++] = (MrylString){ .data = buf, .length = (int)seg };
        p = found + delim.length;
    }
    // 残り部分
    size_t rest = strlen(p);
    char *buf = (char*)malloc(rest + 1);
    strcpy(buf, p);
    result.data[result.len++] = (MrylString){ .data = buf, .length = (int)rest };
    return result;
}
```

#### メソッド呼び出しの C コード生成

```c
// s.split(",")
mryl_str_split(s, mryl_str(","))
```

---

## 4. 既知の制限（v0.4.0 スコープ外）

| 制限 | 詳細 |
|---|---|
| split 結果の free | 各要素の `buf` は free されない（メモリリーク） |
| 最大分割数指定 | 第 2 引数で上限を指定する構文は未実装 |
| `splitn()` | n 個に制限して分割するメソッドは未実装 |

---

## 5. テスト観点（C0 / C1 / MC/DC）

対応テストファイル: `tests/test_30_string_split.ml`

| # | ケース | 観点 | 内容 |
|---|---|---|---|
| T30-A1 | `"apple,banana,cherry".split(",")` → 3要素 | C0 | 通常分割・len 確認 |
| T30-A2〜A4 | 各要素 `parts[0..2]` のインデックスアクセス | C0 | 要素値確認 |
| T30-B1 | `"abc".split("x")` → 1要素 | C1 | 区切りなしパス |
| T30-C1 | `"hello".split("")` → 5要素 | C1 | 空文字列区切りパス |
| T30-D1 | `"abcXYZdef".split("XYZ")` → 2要素 | MC/DC | 複数文字区切り |
| T30-E1 | `",a,".split(",")` → 3要素（先頭末尾空） | C1 | 空要素生成パス |
| T30-F1〜F4 | `"a b c".split(" ")` → 各要素確認 | C0 | スペース区切り |
| T30-G1 | 関数戻り値として `string[]` | MC/DC | 関数経由パス |

---

## 6. 関連

- Issue #55: https://github.com/Mryl-Dev/Mryl/issues/55
- `iter_linq_v0.4.0.md`（split 後に `Iter<T>` チェーンで filter 等を適用できる）
- Issue #43: Iter<T> / LINQ
- Issue #11: string 組み込みメソッド基盤
