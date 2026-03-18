// ============================================================
// Test 34: クロージャキャプチャ fat pointer 実装 (#44)
//   A. let lambda（単一変数キャプチャ）
//   B. make_adder（クロージャを返す関数）
//   C. filter 述語内でのキャプチャ変数参照
//   D. 複数変数キャプチャ
//   E. 関数パラメータのキャプチャ
//   F. fn 型パラメータとして渡すクロージャ
//
// カバレッジ観点:
//   C0  : 各コードパスを最低1回実行
//   C1  : キャプチャあり／なし、単一／複数変数
//   MC/DC: できる範囲で
// ============================================================

// --- 関数A: let lambda (単一キャプチャ) ---
fn test_single_capture() -> i32 {
    let base: i32 = 10;
    let add_base = (x: i32) => x + base;
    return add_base(5);  // 15
}

// --- 関数B: make_adder (クロージャを返す関数) ---
fn make_adder(n: i32) -> fn(i32) -> i32 {
    return (x: i32) => x + n;
}

fn test_make_adder() -> i32 {
    let add5 = make_adder(5);
    let a = add5(3);   // 8
    let b = add5(10);  // 15
    return a + b;      // 23
}

// --- 関数C: LINQ filter (キャプチャ変数を含む述語) ---
fn test_filter_capture() -> i32 {
    let threshold: i32 = 3;
    let nums: i32[] = [1, 2, 3, 4, 5];
    let result = nums
        .filter((x: i32) => x > threshold)
        .to_array();
    return result.len();  // 2
}

// --- 関数D: 複数変数キャプチャ ---
fn test_multi_capture() -> i32 {
    let a: i32 = 10;
    let b: i32 = 20;
    let f = (x: i32) => x + a + b;
    return f(5);  // 35
}

// --- 関数E: 関数パラメータをキャプチャ ---
fn apply_offset(offset: i32) -> i32 {
    let f = (x: i32) => x + offset;
    return f(100);  // offset + 100
}

fn test_param_capture() -> i32 {
    return apply_offset(10);  // 110
}

// --- 関数F: fn 型パラメータとして渡す ---
fn apply(f: fn(i32) -> i32, x: i32) -> i32 {
    return f(x);
}

fn test_fn_param() -> i32 {
    let multiplier: i32 = 3;
    let result = apply((x: i32) => x * multiplier, 5);
    return result;  // 15
}

fn main() -> i32 {
    let r1 = test_single_capture();
    let r2 = test_make_adder();
    let r3 = test_filter_capture();
    let r4 = test_multi_capture();
    let r5 = test_param_capture();
    let r6 = test_fn_param();

    println("{}", r1);  // 15
    println("{}", r2);  // 23
    println("{}", r3);  // 2
    println("{}", r4);  // 35
    println("{}", r5);  // 110
    println("{}", r6);  // 15

    println("=== OK ===");
    return 0;
}
