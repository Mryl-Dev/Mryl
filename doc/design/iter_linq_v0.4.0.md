# Mryl Iter<T> / LINQ スタイルコレクション操作 詳細設計書

**バージョン**: v0.4.0
**Issue**: #43
**日付**: 2026-03-14

---

## 1. 概要

配列（`T[]`）に直接メソッドチェーンで LINQ スタイルのコレクション操作を記述できるようにする。
C# LINQ をベースに命名し、`.iter()` 不要で配列から直接チェーンを開始できる。

```mryl
let nums: i32[] = [1, 2, 3, 4, 5];

let result = nums
    .filter((x: i32) => x % 2 == 0)
    .select((x: i32) => x * 10)
    .to_array();   // [20, 40]

println("{}", result.len());  // 2
```

---

## 2. API 一覧

### 中間操作（チェーン可能・Iter<T> を返す）

| メソッド | シグネチャ | C# 対応 | 説明 |
|---|---|---|---|
| `select` | `fn(fn(T) -> U) -> Iter<U>` | `Select` | 各要素を変換 |
| `filter` | `fn(fn(T) -> bool) -> Iter<T>` | `Where` | 条件を満たす要素だけ残す |
| `take` | `fn(i32) -> Iter<T>` | `Take` | 先頭 n 件 |
| `skip` | `fn(i32) -> Iter<T>` | `Skip` | 先頭 n 件をスキップ |
| `select_many` | `fn(fn(T) -> U[]) -> Iter<U>` | `SelectMany` | map + flatten（C コード生成は v0.5.0 defer） |

### 終端操作（評価・消費）

| メソッド | シグネチャ | C# 対応 | 説明 |
|---|---|---|---|
| `to_array` | `fn() -> T[]` | `ToArray` | `T[]` に変換 |
| `aggregate` | `fn(fn(T, T) -> T) -> Result<T, string>` | `Aggregate` | 初期値なし畳み込み |
| `aggregate` | `fn(U, fn(U, T) -> U) -> U` | `Aggregate` | 初期値あり畳み込み |
| `for_each` | `fn(fn(T) -> void) -> void` | `ForEach` | 副作用のみ（void・let 代入不可） |
| `count` | `fn() -> i32` | `Count` | 要素数 |
| `first` | `fn() -> Result<T, string>` | `First` | 先頭要素 |
| `any` | `fn(fn(T) -> bool) -> bool` | `Any` | 条件を満たす要素が存在するか |
| `all` | `fn(fn(T) -> bool) -> bool` | `All` | 全要素が条件を満たすか |

---

## 3. 設計方針

### 3.1 AST

**新規ノード不要**。既存の `MethodCall` ノードのネストでチェーンを表現する。
`Iter<T>` 型は既存の `TypeNode("Iter", type_args=[T])` で表現する。

### 3.2 Parser

**変更不要**。メソッドチェーン・ラムダ引数（`FAT_ARROW =>`）は既存実装で対応済み。

### 3.3 Interpreter

`Interpreter.py` の `_eval_array_method` に iter メソッドを追加する。
`Iter<T>` の中間値は Python `list` で表現し、チェーン操作は list comprehension / スライスで実装する。

| メソッド | Python 実装 |
|---|---|
| `select` | `[fn(x) for x in arr]` |
| `filter` | `[x for x in arr if fn(x)]` |
| `take` | `arr[:n]` |
| `skip` | `arr[n:]` |
| `select_many` | `[y for x in arr for y in fn(x)]` |
| `to_array` | `list(arr)` |
| `aggregate`（初期値なし） | `functools.reduce(fn, arr)` → `Ok(result)` / 空なら `Err(...)` |
| `aggregate`（初期値あり） | `functools.reduce(fn, arr, init)` |
| `for_each` | `for x in arr: fn(x)` |
| `count` | `len(arr)` |
| `first` | `Ok(arr[0])` / 空なら `Err(...)` |
| `any` | `any(fn(x) for x in arr)` |
| `all` | `all(fn(x) for x in arr)` |

#### aggregate のオーバーロード判別

引数が 1 つ → 初期値なし（`fn(T,T)->T`）
引数が 2 つ → 初期値あり（最初の引数が初期値 `U`、2番目が `fn(U,T)->U`）

### 3.4 TypeChecker（`core/TypeChecker/_call.py`）

`check_method_call` の動的配列ブランチ（`array_size == -1`）に以下の型規則を追加する。

```
select(fn: fn(T)->U)     -> TypeNode("Iter", type_args=[U])
filter(fn: fn(T)->bool)  -> TypeNode("Iter", type_args=[T])
take(n: i32)             -> TypeNode("Iter", type_args=[T])
skip(n: i32)             -> TypeNode("Iter", type_args=[T])
select_many(fn: fn(T)->U[]) -> TypeNode("Iter", type_args=[U])
to_array()               -> TypeNode(T.name, array_size=-1)
aggregate(fn)            -> TypeNode("Result", type_args=[T, TypeNode("string")])
aggregate(init, fn)      -> 初期値の型 U
for_each(fn)             -> TypeNode("void")
count()                  -> TypeNode("i32")
first()                  -> TypeNode("Result", type_args=[T, TypeNode("string")])
any(fn)                  -> TypeNode("bool")
all(fn)                  -> TypeNode("bool")
```

#### ラムダ引数の型推論（VarRef 対応）

引数が `Lambda` ノードの場合：`inferred_return_type` から戻り値型を取得する。
引数が `VarRef`（変数参照）の場合：環境から `fn` 型を取得し `type_args[-1]` を戻り値型とする。
引数が特定できない場合：レシーバ要素型 `T` で同一型フォールバックする。

#### Iter<T> チェーンの型伝播

`Iter<T>` 型を受け取った後続のメソッドも同様に処理する。
`TypeNode("Iter", type_args=[T])` の `array_size` は `-1` とし、既存の動的配列と同一ブランチで処理する。

### 3.5 C コード生成（`core/CodeGenerator/`）

#### `_expr.py`

`Iter<T>` の各メソッドを GCC statement expression `({ ... })` でインライン生成する。
中間値として既存の `MrylVec_T` 構造体を流用する。

##### select の C コード生成例

```c
({
    MrylVec_int32_t __iter_0 = { malloc(sizeof(int32_t) * src.len), src.len, src.len };
    for (int32_t __i = 0; __i < src.len; __i++) {
        __iter_0.data[__i] = __lambda_0(src.data[__i]);
    }
    __iter_0;
})
```

##### filter の C コード生成例

```c
({
    MrylVec_int32_t __iter_0 = { malloc(sizeof(int32_t) * src.len), 0, src.len };
    for (int32_t __i = 0; __i < src.len; __i++) {
        if (__lambda_0(src.data[__i])) {
            __iter_0.data[__iter_0.len++] = src.data[__i];
        }
    }
    __iter_0;
})
```

##### take / skip

```c
// take(n)
({ MrylVec_int32_t __r = src; __r.len = (n < src.len ? n : src.len); __r; })

// skip(n)
({ int32_t __s = (n < src.len ? n : src.len);
   MrylVec_int32_t __r = { src.data + __s, src.len - __s, src.len - __s }; __r; })
```

##### to_array

`Iter<T>` は内部的に `MrylVec_T` なのでそのまま値を渡す（変換コードなし）。

##### aggregate（初期値なし）

```c
({
    MrylResult_int32_t_MrylString __agg;
    if (src.len == 0) {
        __agg = (MrylResult_int32_t_MrylString){ .is_ok=0, .err=mryl_str("empty sequence") };
    } else {
        int32_t __acc = src.data[0];
        for (int32_t __i = 1; __i < src.len; __i++) {
            __acc = __lambda_0(__acc, src.data[__i]);
        }
        __agg = (MrylResult_int32_t_MrylString){ .is_ok=1, .ok=__acc };
    }
    __agg;
})
```

##### aggregate（初期値あり）

```c
({
    int32_t __acc = init;
    for (int32_t __i = 0; __i < src.len; __i++) {
        __acc = __lambda_0(__acc, src.data[__i]);
    }
    __acc;
})
```

##### for_each

`for_each` は void のため、statement expression を使わず `for` 文として直接出力する。
`let` 宣言の右辺では使用不可（TypeChecker で void 型代入をエラーにする）。

```c
for (int32_t __i = 0; __i < src.len; __i++) {
    __lambda_0(src.data[__i]);
}
```

##### count

```c
src.len
```

##### first

```c
({
    MrylResult_int32_t_MrylString __first;
    if (src.len == 0) {
        __first = (MrylResult_int32_t_MrylString){ .is_ok=0, .err=mryl_str("empty sequence") };
    } else {
        __first = (MrylResult_int32_t_MrylString){ .is_ok=1, .ok=src.data[0] };
    }
    __first;
})
```

##### any / all

```c
// any
({
    int8_t __found = 0;
    for (int32_t __i = 0; __i < src.len; __i++) {
        if (__lambda_0(src.data[__i])) { __found = 1; break; }
    }
    __found;
})

// all
({
    int8_t __ok = 1;
    for (int32_t __i = 0; __i < src.len; __i++) {
        if (!__lambda_0(src.data[__i])) { __ok = 0; break; }
    }
    __ok;
})
```

#### `_generic.py`

`vec_` prefix での iter メソッド戻り値型推論を追加する。

```python
elif method in ('select', 'filter', 'take', 'skip'):
    return f"MrylVec_{elem_c}"   # Iter<T> = MrylVec_T
elif method in ('count',):
    return "int32_t"
elif method in ('any', 'all'):
    return "int8_t"
elif method in ('first', 'aggregate'):
    return f"MrylResult_{elem_c}_{err_c}"
elif method == 'to_array':
    return f"MrylVec_{elem_c}"
```

#### select_many の C 生成（v0.5.0 defer）

v0.4.0 では `select_many` が C バックエンドで使われた場合、`NotImplementedError` を送出して明示的にエラーにする。
詳細は `issue_iter_select_many_codegen.md` を参照。

---

## 4. ループカウンタ・変数名の衝突防止

中間変数名は `CodeGenerator` の `loop_counter` を使ってユニーク化する。

```python
idx = self.loop_counter
self.loop_counter += 1
iter_var = f"__iter_{idx}"
i_var    = f"__i_{idx}"
```

---

## 5. 既知の制限（v0.4.0 スコープ外）

| 制限 | 詳細 | issue |
|---|---|---|
| 中間 MrylVec のメモリリーク | チェーン中間値が free されない | `issue_iter_intermediate_memleak.md` |
| ラムダ引数型検査が浅い | TypeChecker が引数型・戻り値型を完全検査しない | `issue_iter_lambda_typecheck_shallow.md` |
| for_each の void statement expression | void を返す statement expression は GCC 拡張制約に注意 | `issue_iter_for_each_void_stmtexpr.md` |
| select_many C 生成未実装 | Interpreter のみ対応 | `issue_iter_select_many_codegen.md` |

---

## 6. タスク一覧

- [ ] `Interpreter.py` の `_eval_array_method` に iter メソッド追加（select / filter / take / skip / select_many / to_array / aggregate / for_each / count / first / any / all）
- [ ] `TypeChecker/_call.py` に Iter<T> メソッドの型規則追加（VarRef type inference 含む）
- [ ] `CodeGenerator/_generic.py` に iter メソッド戻り値型推論追加
- [ ] `CodeGenerator/_expr.py` に iter メソッドの C コード生成追加
- [ ] `tests/test_31_iter_linq.ml` 作成・全テスト実行

---

## 7. テスト観点（C0 / C1 / MC/DC）

| # | 観点 | 内容 |
|---|---|---|
| 1 | C0 | `filter` 単体（偶数フィルタ） |
| 2 | C0 | `select` 単体（×10変換） |
| 3 | C0 | `filter` → `select` → `to_array` チェーン |
| 4 | C0 | `aggregate` 初期値なし（合計） |
| 5 | C0 | `aggregate` 初期値あり（文字列結合等） |
| 6 | C0 | `first` 正常・空配列エラー |
| 7 | C0 | `count` |
| 8 | C0 | `any` / `all` |
| 9 | C0 | `take` / `skip` |
| 10 | C0 | `for_each` 副作用確認 |
| 11 | C0 | `select_many` Interpreter 動作確認 |
| 12 | C1 | `filter` で全要素通過・全要素除外 |
| 13 | C1 | `take(0)` / `take(n>len)` 境界値 |
| 14 | C1 | `aggregate` 空配列 → `Err` |
| 15 | MC/DC | `any`: 最初の要素で true / 全て false |
| 16 | MC/DC | `all`: 最初の要素で false / 全て true |
*buf = (char*)malloc(new_len + 1); char *dst = buf; p = s.data;
    const char *found;
    while ((found = strstr(p, from.data)) != NULL) {
        size_t seg = found - p; memcpy(dst, p, seg); dst += seg;
        memcpy(dst, to_s.data, to_s.length); dst += to_s.length; p = found + from.length;
    }
    strcpy(dst, p); MrylString r; r.data = buf; r.length = new_len; return r;
---

## 8. 関連

- `issue_iter_linq.md`（要件定義）
- `issue_closure_capture.md`（キャプチャ変数との組み合わせ、将来対応）
- `issue_observable_rx.md`（Rx の基盤として Iter<T> が必要）
