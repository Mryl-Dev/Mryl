# 詳細設計書: Iter<T> 中間 MrylVec メモリリーク修正

**機能名**: iter_memleak_free
**バージョン**: v0.5.0
**対象 issue**: #62
**最終更新**: 2026年3月14日

---

## 1. 問題概要

`Iter<T>` のチェーン呼び出し（例: `arr.select(f).filter(g).count()`）において、
`select` / `filter` が生成する中間 `MrylVec` がヒープ確保されたまま解放されない。

### 再現パターン

```mryl
// 全ての中間 MrylVec がリークする
let cnt = arr.select(x => x * 2).filter(x => x > 3).count();
```

生成される C コード（修正前）:
```c
// select が malloc → 解放されない
(({ MrylVec_i32 __iter_0 = mryl_vec_i32_new();
    for (...) mryl_vec_i32_push(&__iter_0, lam(arr.data[i]));
    __iter_0; }))
```

---

## 2. 設計方針

### 2.1 ソース種別の判定

`_generate_iter_method` の呼び出し時に、レシーバの AST ノード種別を判定する。

| レシーバ種別 | `src_is_temp` | 説明 |
|-------------|:---:|------|
| `VarRef`（ユーザー変数） | `False` | ユーザーが所有 → free しない |
| `MethodCall`（中間 iter 結果） | `True` | 一時 MrylVec → 使用後 free する |

```python
src_is_temp = expr.obj.__class__.__name__ == 'MethodCall'
```

### 2.2 ソースキャプチャ

`src_is_temp=True` のとき、複数回評価を防ぐためソースを一度ローカル変数に代入する。

```c
MrylVec_T __src_N = (src_expr);   // ← 1回だけ評価
```

変数:
- `src_cap`  : `src_is_temp=True` のとき上記宣言文字列、`False` のとき空文字列
- `src_ref`  : `src_is_temp=True` のとき `__src_N`、`False` のとき `obj_c`
- `src_free` : `src_is_temp=True` のとき `free(__src_N.data);`、`False` のとき空文字列

### 2.3 各メソッドの対応

| メソッド | ソース消費 | src_free | 備考 |
|---------|:---------:|:--------:|------|
| `select`    | コピー（変換） | ✅ | 結果は新規確保 |
| `filter`    | コピー（フィルタ） | ✅ | 結果は新規確保 |
| `take`      | view（len のみ縮小） | ❌ | ポインタ共有 → 所有権を結果に移す |
| `skip`      | **src_is_temp=True: コピー** / False: view | ✅/❌ | ⚠️ オフセットポインタ問題のためコピーに変更 |
| `count`     | 終端（len を読む） | ✅ | statement expression に変更 |
| `any`       | 終端 | ✅ | |
| `all`       | 終端 | ✅ | |
| `for_each`  | 終端 | ✅ | |
| `aggregate` | 終端（2形式） | ✅ | |
| `first`     | 終端 | ✅ | |
| `to_array`  | 所有権移転 | ❌ | 呼び出し側が保有 |

### 2.4 `skip` 特例: オフセットポインタ問題

**問題**: `skip` の view 方式は `data + n` のオフセットポインタを返す。
これを `free()` に渡すと UB / クラッシュになる。

```c
// view 方式（src_is_temp=False のみ残す）
__iter.data = src.data + n;   // ← malloc 先頭ではない

// コピー方式（src_is_temp=True のとき）
MrylVec_T __iter = mryl_vec_T_new();
for (int i = n; i < src.len; i++) mryl_vec_T_push(&__iter, src.data[i]);
free(src.data);               // ← 安全に解放可能
```

**規則**:
- `src_is_temp=False`（ユーザー変数が対象）: 従来の view 方式を維持
- `src_is_temp=True`（中間 iter が対象）: コピー方式に変更

---

## 3. 実装箇所

### `core/CodeGenerator/_expr.py`

#### 変更点 1: `_generate_iter_method` シグネチャ

```python
def _generate_iter_method(
    self, expr, et: str, obj_c: str, src_is_temp: bool = False
) -> str:
```

#### 変更点 2: メソッド先頭に共通変数を追加

```python
src_var  = f"__src_{idx}"
src_cap  = f"MrylVec_{et} {src_var} = {obj_c}; " if src_is_temp else ""
src_ref  = src_var if src_is_temp else obj_c
src_free = f"free({src_var}.data); " if src_is_temp else ""
```

#### 変更点 3: 呼び出し元

```python
src_is_temp = expr.obj.__class__.__name__ == 'MethodCall'
return self._generate_iter_method(expr, et, obj_name, src_is_temp)
```

---

## 4. 生成 C コード例

### 修正後: `arr.select(f).filter(g).count()`

```c
({
    // count が filter 中間結果を受け取る
    MrylVec_i32 __src_2 = ({
        // filter が select 中間結果を受け取る
        MrylVec_i32 __src_1 = ({
            // select: src は VarRef → free しない
            MrylVec_i32 __iter_0 = mryl_vec_i32_new();
            for (int32_t __i_0 = 0; __i_0 < arr.len; __i_0++)
                mryl_vec_i32_push(&__iter_0, f(arr.data[__i_0]));
            __iter_0;
        });
        MrylVec_i32 __iter_1 = mryl_vec_i32_new();
        for (int32_t __i_1 = 0; __i_1 < __src_1.len; __i_1++)
            if (g(__src_1.data[__i_1]))
                mryl_vec_i32_push(&__iter_1, __src_1.data[__i_1]);
        free(__src_1.data);   // ← select 中間結果を解放
        __iter_1;
    });
    int32_t __cnt_2 = __src_2.len;
    free(__src_2.data);       // ← filter 中間結果を解放
    __cnt_2;
})
```

### 修正後: `arr.select(f).skip(2).count()`

```c
({
    MrylVec_i32 __src_2 = ({
        // skip: src_is_temp=True → コピー方式
        MrylVec_i32 __src_1 = (select_expr);
        int32_t __s_1 = (2 < __src_1.len ? 2 : __src_1.len);
        MrylVec_i32 __iter_1 = mryl_vec_i32_new();
        for (int32_t __i_1 = __s_1; __i_1 < __src_1.len; __i_1++)
            mryl_vec_i32_push(&__iter_1, __src_1.data[__i_1]);
        free(__src_1.data);   // ← select 中間結果を解放（オフセット問題なし）
        __iter_1;
    });
    int32_t __cnt_2 = __src_2.len;
    free(__src_2.data);
    __cnt_2;
})
```

---

## 5. 既知の制限（今回スコープ外）

| 制限 | 説明 |
|------|------|
| `to_array` 末端のリーク | チェーン末端が `to_array` の場合、ユーザーが保有するが Mryl に明示的 free 手段がない |
| string 要素の deep copy | `first` 等で string を返す場合、コピーは shallow のため解放後ダングリングの可能性あり |

---

## 6. テスト

既存 `tests/test_31_iter_linq.ml` 全 C1 ケースが引き続き通ること。

新規テストケース（`tests/test_32_iter_chain_free.ml`）:
- チェーン呼び出し（select → filter → count など）が正しい値を返すこと
- skip を含むチェーン（select → skip → count）が正しい値を返すこと
- 深いチェーン（select → filter → select → count）が正しい値を返すこと
