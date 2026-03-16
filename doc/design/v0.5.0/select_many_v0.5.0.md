# select_many C コード生成 詳細設計書

**バージョン**: v0.5.0
**関連 issue**: #65
**作成日**: 2026-03-15

---

## 1. 概要

`select_many` は C# LINQ の `SelectMany` に相当する操作（map + flatten）。
`fn(T) -> U[]` を受け取り、各要素に適用した結果をフラット化して `Iter<U>` を返す。

v0.4.0 では Python インタプリタのみ実装済み。v0.5.0 で C コード生成バックエンドを実装する。

---

## 2. 型規則

```
select_many: (Iter<T>, fn(T) -> U[]) -> Iter<U>
```

### 例
```mryl
let nums: i32[] = [1, 2, 3];
let flat: i32[] = nums.select_many((x: i32) => [x, x * 10]).to_array();
// → [1, 10, 2, 20, 3, 30]
```

---

## 3. 修正ファイル一覧

| ファイル | 内容 |
|---------|------|
| `core/CodeGenerator/_type.py` | `array_size == -1` → `MrylVec_{T}` 変換バグ修正 |
| `core/CodeGenerator/_lambda.py` | 式ラムダの ret_type + lambda params を env に追加 |
| `core/CodeGenerator/_expr.py` | `ArrayLiteral` 式生成 + `select_many` 本体実装 |
| `core/CodeGenerator/_generic.py` | `select_many` の型推論修正 |

---

## 4. 修正詳細

### 4.1 `_type.py` — `array_size=-1` 変換バグ修正

**問題**: `_type_to_c(TypeNode('i32', array_size=-1))` が `"int32_t[-1]"` を返す（無効な C 型）。
**修正**: `array_size == -1` のとき `MrylVec_{name}` を返すよう最初にチェック。

```python
if type_node.array_size == -1:
    return f"MrylVec_{type_name}"
```

### 4.2 `_lambda.py` — 式ラムダの戻り値型修正

**問題**: 式ラムダの `ret_type` が常に `"int32_t"` にハードコードされていた。
**修正 A**: ラムダパラメータを `self.env` に一時追加し、body 内の型推論を正確化。
**修正 B**: `ret_type` 決定ロジックを 3 段階で判定:

1. body が `ArrayLiteral` → `MrylVec_{elem_t}`（新規確保）
2. `inferred_return_type.array_size == -1` → `MrylVec_{inferred.name}`
3. それ以外 → `"int32_t"`（従来どおり）

### 4.3 `_expr.py` — `ArrayLiteral` を式として生成

**目的**: ラムダの return 式などで配列リテラルが使われた場合に対応。

```c
// [x, x * 10] → 新規 MrylVec を返す式
mryl_vec_i32_from((int32_t[]){x, x * 10}, 2)
```

`mryl_vec_from` は既存ヘッダーで定義済みの静的ヘルパー。

### 4.4 `_expr.py` — `select_many` C コード生成

```c
({
    MrylVec_i32 __result_0 = mryl_vec_i32_new();
    for (int32_t __i_0 = 0; __i_0 < src.len; __i_0++) {
        MrylVec_i32 __inner_0 = __lambda_0(src.data[__i_0]);
        for (int32_t __j_0 = 0; __j_0 < __inner_0.len; __j_0++) {
            mryl_vec_i32_push(&__result_0, __inner_0.data[__j_0]);
        }
        // inner_needs_free = true の場合のみ:
        free(__inner_0.data);
    }
    __result_0;
})
```

#### `inner_needs_free` ヒューリスティック

| lambda body の種類 | `free(__inner.data)` | 理由 |
|---|:---:|---|
| `VarRef` → 既存配列を参照 | ❌ | ポインタ共有、free すると UB |
| `ArrayLiteral` | ✅ | `mryl_vec_from` で新規確保 |
| `FunctionCall` / `MethodCall` | ✅ | 新規確保と見なす |
| 関数参照渡し / その他 | ❌ | 不明なため安全側 |

### 4.5 `_generic.py` — `select_many` 型推論修正

**問題**: `select_many` が `vec_{elem_c}` を返していた（フラット化前の型）。
**修正**: Lambda の `inferred_return_type.name` から正確な出力型 `vec_{U}` を返す。

---

## 5. 制限事項（v0.5.0）

| 制限 | 詳細 |
|------|------|
| VarRef ラムダ時のメモリ管理 | `(xs: i32[]) => xs` では `__inner.data` を free しない。元の配列が生存している間は安全だが、ラムダ返却配列の所有権は言語仕様外（将来の所有権機能で解決予定）。 |
| `FunctionCall` / `MethodCall` 返却時のリーク確認 | ヒューリスティックで free するが、関数が既存配列を返した場合は UB。呼び出し側関数が新規確保することが前提。 |
| ArrayLiteral 返却のタイプ不一致 | TypeChecker は `[x, x*10]` を `i32[2]`（固定サイズ）と推論するが、codegen では `mryl_vec_from` で動的配列として生成。型システムとの整合性は将来改善予定。 |

---

## 6. テスト

- `tests/test_33_select_many.ml`: 新規テスト（C0/C1/MC/DC）
- `tests/test_31_iter_linq.ml`: K. select_many ケース追加
