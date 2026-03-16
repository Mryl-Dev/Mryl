# クロージャキャプチャ fat pointer 詳細設計書 (v0.5.0)

## 概要

issue #44 として実装したクロージャキャプチャ機能。`fn` 型変数を fat pointer struct として表現し、
キャプチャ変数を heap alloc した環境構造体経由でアクセスする方式を採用した。

---

## 設計方針

### Fat pointer 方式

`fn(T) -> U` 型を次の C struct として表現する。

```c
typedef struct {
    U (*fn)(T, void*);  // 関数ポインタ（最後の引数は常に void* __e）
    void* env;          // キャプチャ環境へのポインタ（キャプチャなし → NULL）
} MrylFn_T_ret_U;
```

### Uniform calling convention

すべてのラムダ関数に `void* __e` を最終引数として追加する。
関数本体内では `__env = (__lambda_N_env_t*)__e;` でキャストしてフィールドアクセスする。

### 命名規則

| 識別子 | 形式 | 例 |
|--------|------|-----|
| fat pointer typedef | `MrylFn_{arg_part}_ret_{ret_part}` | `MrylFn_int32_t_ret_int32_t` |
| 環境構造体 typedef | `__lambda_N_env_t` | `__lambda_0_env_t` |
| 環境ポインタ変数 | `__env___lambda_N` | `__env___lambda_0` |
| ラムダ関数名 | `__lambda_N` | `__lambda_0` |

---

## 実装コンポーネント

### 1. `_type.py` - fn 型 → C 型変換

`_type_to_c` が `fn` 型 TypeNode を受け取ると fat pointer struct 名を返す。
同時に `fn_type_registry` に `(arg_cs_tuple, ret_c, struct_name)` を登録する。

```python
if type_node.name == "fn":
    if getattr(type_node, 'type_args', None):
        # 最後の type_arg が戻り値型
        struct_name = f"MrylFn_{arg_part}_ret_{ret_part}"
        self.fn_type_registry.add((arg_cs, ret_c, struct_name))
        return struct_name
    return "void*"
```

### 2. `__init__.py` - プレースホルダー差し込み

コード生成終了後に `// __FN_TYPEDEFS_PLACEHOLDER__` の位置に fat pointer typedef を挿入する。

```c
// ===== fn type fat pointers =====
typedef struct { int32_t (*fn)(int32_t, void*); void* env; } MrylFn_int32_t_ret_int32_t;
```

### 3. `_lambda.py` - ラムダ生成

- `_collect_captures`: キャプチャ変数を収集。`fn`/`fn_closure` 型は `fn_var_c_types` から実際の MrylFn_* 型を取得。
- `_generate_lambda_inline`: `lambda_captures` に `{ret_c, arg_cs, captures}` を登録。
- `_generate_lambda`: 同様に登録。生成するラムダ関数は常に `void* __e` 付き。

### 4. `_stmt.py` - let 宣言

**Lambda 初期値の場合:**

```python
# キャプチャあり
__lambda_0_env_t* __env___lambda_0 = (__lambda_0_env_t*)malloc(sizeof(__lambda_0_env_t));
__env___lambda_0->base = base;
MrylFn_int32_t_ret_int32_t add_base = {__lambda_0, __env___lambda_0};
# local_closure_envs に追加 → 関数末尾で free

# キャプチャなし
MrylFn_int32_t_ret_int32_t f = {__lambda_0, NULL};
```

**FunctionCall が fn 型を返す場合（type_node is None）:**

`program_functions[func_name].return_type.name == "fn"` を確認し、
fat pointer struct 型で宣言して `env[-1][stmt.name] = "fn"` を登録する。

**TypeChecker が type_node を付与した場合（type_node.name == "fn"）:**

一般 else 分岐に `elif type_node.name == "fn":` を追加し、
`env[-1][stmt.name] = "fn"` および `fn_var_c_types[stmt.name] = var_type` を登録する。
（TypeChecker なしの場合は FunctionCall-returns-fn 分岐が担当）

### 5. `_expr.py` - 呼び出しサイト

**fn/fn_closure 変数の呼び出し:**

```python
for scope in reversed(self.env):
    if expr.name in scope and scope[expr.name] in ("fn", "fn_closure"):
        c_name = self.ident_renames.get(expr.name, _safe_c_name(expr.name))
        all_args = f"{args}, {c_name}.env" if args else f"{c_name}.env"
        return f"{c_name}.fn({all_args})"
```

**Lambda 引数の fat pointer 変換:**

関数呼び出しの引数に Lambda ノードが含まれる場合、env struct を `_emit` してアドレスを渡す。

**LINQ (_lam_full):**

`_lam_full(arg_idx)` は `(env_setup, fn_expr, env_arg)` タプルを返す。
- Lambda: キャプチャあり → env struct 初期化 + アドレス / なし → NULL
- fn/fn_closure 変数: `.fn` / `.env` を取得
- 通常関数参照: `__thunk_N` サンクを自動生成

---

## メモリ管理

| ケース | alloc | free |
|--------|-------|------|
| let lambda（キャプチャあり） | `_generate_let` で malloc | 関数末尾 (`local_closure_envs`) |
| return で lambda を返す | `_generate_return` で malloc | 呼び出し元の責任 |
| Lambda 引数（スタック alloc） | `_emit` でブロックスコープ変数 | スコープ終了時に自動 |
| FunctionCall が fn を返す | callee 内で alloc | callee または呼び出し元（未対応、将来課題） |

---

## 新規フィールド（`__init__.py` / `_proto.py`）

| フィールド | 型 | 用途 |
|-----------|-----|------|
| `fn_var_c_types` | `dict[str, str]` | var_name → MrylFn_* 型名（キャプチャ型解決用） |
| `fn_type_registry` | `set` | fat pointer typedef 登録済み型の集合 |
| `local_closure_envs` | `list[str]` | 関数末尾で free する env ポインタ名リスト |
| `closure_var_env_ptrs` | `dict[str, str]` | var_name → env_ptr（return 時 free スキップ用） |
| `lambda_captures` | `dict[str, dict]` | lam_name → {captures, ret_c, arg_cs} |

---

## テスト

`tests/test_34_closure_capture.ml`

| テストケース | 検証内容 | 期待値 |
|-------------|---------|--------|
| test_single_capture | 単一変数キャプチャ | 15 |
| test_make_adder | クロージャを返す関数 | 23 |
| test_filter_capture | LINQ filter + キャプチャ | 2 |
| test_multi_capture | 複数変数キャプチャ | 35 |
| test_param_capture | 関数パラメータキャプチャ | 110 |
| test_fn_param | fn 型パラメータ渡し | 15 |

---

## 既知の制限事項

- `FunctionCall` が返す fat pointer の env ライフタイム管理は callee 依存（解放責任が曖昧）
- `async lambda` は旧来の関数ポインタ構文を維持
- ネストしたクロージャ（クロージャがクロージャをキャプチャ）は未テスト
