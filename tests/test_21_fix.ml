// ============================================================
// Test 21: fix キーワード (不変変数・不変引数)
//
//   A. fix 不変変数 — 全型 + 型推論
//   B. fix 変数を引数として渡す
//   C. fix パラメータ — 再代入は不可、値は正しく使える
//   D. fix + let 混在 — 可変/不変の共存
//   E. スコープ独立性 — 外側 fix と同名仮引数は別スコープ
//   F. ラムダ fix パラメータ
//   G. fix を使った定数ライクな計算
//
// カバレッジ観点:
//   C0 : A〜G 全セクションの文を実行
//   C1 :
//     C: fix パラメータへのアクセス (true) / 可変パラメータ書き換え (true)
//     D: fix との比較分岐 (true/false 両方)
//     E: 外側 fix を参照後に関数内同名変数を書き換え (スコープ分離)
//   MC/DC:
//     D: (g_mut > g_threshold) で true/false の独立決定
// ============================================================

// ----------------------------------------------------------
// C. fix パラメータ
// ----------------------------------------------------------
fn add_fix(fix a: i32, b: i32) -> i32 {
    b = b + 1;      // b は可変 OK
    return a + b;   // a は fix — 再代入なし
}

fn scale(fix factor: f64, v: f64) -> f64 {
    return factor * v;
}

fn prefix(fix tag: string, msg: string) -> string {
    return tag + msg;
}

// ----------------------------------------------------------
// D. fix + let の比較分岐
// ----------------------------------------------------------
fn clamp(fix lo: i32, fix hi: i32, v: i32) -> i32 {
    if (v < lo) { return lo; }
    if (v > hi) { return hi; }
    return v;
}

// ----------------------------------------------------------
// E. スコープ独立性 — 外側 fix x と同名の仮引数 x
// ----------------------------------------------------------
fn mut_inner(x: i32) -> i32 {
    x = x * 3;   // 仮引数 x (可変) への代入 — 外側 fix x とは無関係
    return x;
}

// ----------------------------------------------------------
// F. ラムダ fix パラメータ
// ----------------------------------------------------------
fn apply_fix(f: fn(i32) -> i32, v: i32) -> i32 {
    return f(v);
}

fn main() -> i32 {
    println("=== 21: Fix ===");

    // ----------------------------------------------------------
    // A. fix 不変変数 — 全型 + 型推論  [C0]
    // ----------------------------------------------------------
    println("--- A: Fix variables ---");
    fix a_i32 : i32    = 42;
    fix a_i64 : i64    = 9999999999(i64);
    fix a_f64 : f64    = 3.14159;
    fix a_str : string = "hello";
    fix a_bool: bool   = true;
    fix a_inf          = 100;     // 型推論: i32
    println("a_i32={}", a_i32);   // 42
    println("a_i64={}", a_i64);   // 9999999999
    println("a_f64={}", a_f64);   // 3.141590
    println("a_str={}", a_str);   // hello
    println("a_bool={}", a_bool); // true
    println("a_inf={}", a_inf);   // 100

    // ----------------------------------------------------------
    // B. fix 変数を引数として渡す  [C0]
    // ----------------------------------------------------------
    println("--- B: Pass fix to function ---");
    fix b_base: i32 = 10;
    let b_r1 = add_fix(b_base, 5);   // a=10(fix) b=5→6  result=16
    let b_r2 = add_fix(b_base, 20);  // a=10(fix) b=20→21 result=31
    println("add(10,5)={}", b_r1);   // 16
    println("add(10,20)={}", b_r2);  // 31
    // b_base は変わっていない
    println("b_base={}", b_base);    // 10

    fix b_rate: f64 = 2.5;
    let b_r3 = scale(b_rate, 4.0);
    println("scale(2.5,4)={}", b_r3); // 10.000000

    // ----------------------------------------------------------
    // C. fix パラメータ — 値は正しく使える  [C0/C1]
    // ----------------------------------------------------------
    println("--- C: Fix parameter ---");
    let c_r1 = add_fix(3, 4);     // a=3(fix) b=4→5  result=8
    let c_r2 = add_fix(0, 0);     // a=0(fix) b=0→1  result=1
    let c_r3 = add_fix(100, 99);  // a=100(fix) b=99→100 result=200
    println("add(3,4)={}", c_r1);    // 8
    println("add(0,0)={}", c_r2);    // 1
    println("add(100,99)={}", c_r3); // 200

    let c_r4 = prefix("mryl:", "lang");
    println("prefix={}", c_r4);      // mryl:lang

    // ----------------------------------------------------------
    // D. fix + let 混在、比較分岐  [C0/C1/MC/DC]
    // ----------------------------------------------------------
    println("--- D: Fix + let ---");
    fix d_lo: i32 = 0;
    fix d_hi: i32 = 100;
    let d_v1 = clamp(d_lo, d_hi, -5);   // 下限クランプ → 0
    let d_v2 = clamp(d_lo, d_hi, 200);  // 上限クランプ → 100
    let d_v3 = clamp(d_lo, d_hi, 50);   // 範囲内       → 50
    println("clamp(-5)={}", d_v1);   // 0
    println("clamp(200)={}", d_v2);  // 100
    println("clamp(50)={}", d_v3);   // 50

    // MC/DC: fix との比較で true/false が独立決定
    fix d_threshold: i32 = 10;
    let d_mut = 5;
    if (d_mut > d_threshold) { println("over=T"); } else { println("over=F"); }  // over=F
    d_mut = 15;
    if (d_mut > d_threshold) { println("over=T"); } else { println("over=F"); }  // over=T

    // ----------------------------------------------------------
    // E. スコープ独立性  [C0/C1]
    // ----------------------------------------------------------
    println("--- E: Scope isolation ---");
    fix e_x: i32 = 7;
    let e_r = mut_inner(e_x);    // 関数内で仮引数を書き換えても e_x は不変
    println("inner(7)={}", e_r); // 21  (7 * 3)
    println("e_x={}", e_x);      // 7  (変わっていない)

    // ----------------------------------------------------------
    // F. ラムダ fix パラメータ  [C0]
    // ----------------------------------------------------------
    println("--- F: Lambda fix param ---");
    let f_triple = (fix x: i32) => { return x * 3; };
    let f_r1 = f_triple(5);
    let f_r2 = apply_fix(f_triple, 8);
    println("triple(5)={}", f_r1);      // 15
    println("apply_fix(8)={}", f_r2);   // 24

    // ----------------------------------------------------------
    // G. fix を使った定数ライクな計算  [C0]
    // ----------------------------------------------------------
    println("--- G: Constant-like calc ---");
    fix g_pi  : f64 = 3.14159;
    fix g_r   : f64 = 5.0;
    let g_area = g_pi * g_r * g_r;
    println("area={}", g_area);   // 78.539750

    fix g_n: i32 = 10;
    let g_sum = 0;
    for (let i = 1; i <= g_n; i++) {
        g_sum = g_sum + i;
    }
    println("sum1to10={}", g_sum); // 55

    println("=== OK ===");
    return 0;
}
