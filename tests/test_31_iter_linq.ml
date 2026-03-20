// ============================================================
// Test 31: Iter<T> / LINQ スタイルコレクション操作 (fix #43)
//   A. filter 単体
//   B. select 単体
//   C. filter → select → to_array チェーン
//   D. take / skip
//   E. count
//   F. first（正常・空配列エラー）
//   G. any / all
//   H. aggregate 初期値なし（合計）
//   I. aggregate 初期値あり
//   J. for_each 副作用確認
//   K. select_many（#65 v0.5.0 実装）
//   L. filter: 全要素通過 / 全要素除外（C1 境界値）
//   M. take(0) / take(n>len) 境界値
//   N. aggregate 空配列 → Err
//   O. any MC/DC: 最初の要素で true / 全て false
//   P. all MC/DC: 最初の要素で false / 全て true
//
// カバレッジ観点:
//   C0  : 各メソッドを少なくとも 1 回実行
//   C1  : filter 全通過・全除外、take 境界値
//   MC/DC: any / all の分岐
// ============================================================

fn main() -> i32 {

    // ----------------------------------------------------------
    // A. filter 単体 (偶数だけ残す)
    // ----------------------------------------------------------
    let nums: i32[] = [1, 2, 3, 4, 5, 6];
    let evens: i32[] = nums.filter((x: i32) => x % 2 == 0).to_array();
    println("A1: {}", evens.len());    // A1: 3
    println("A2: {}", evens[0]);       // A2: 2
    println("A3: {}", evens[2]);       // A3: 6

    // ----------------------------------------------------------
    // B. select 単体 (×10 変換)
    // ----------------------------------------------------------
    let tens: i32[] = nums.select((x: i32) => x * 10).to_array();
    println("B1: {}", tens.len());     // B1: 6
    println("B2: {}", tens[0]);        // B2: 10
    println("B3: {}", tens[5]);        // B3: 60

    // ----------------------------------------------------------
    // C. filter → select → to_array チェーン
    // ----------------------------------------------------------
    let result: i32[] = nums
        .filter((x: i32) => x % 2 == 0)
        .select((x: i32) => x * 10)
        .to_array();
    println("C1: {}", result.len());   // C1: 3
    println("C2: {}", result[0]);      // C2: 20
    println("C3: {}", result[2]);      // C3: 60

    // ----------------------------------------------------------
    // D. take / skip
    // ----------------------------------------------------------
    let taken: i32[] = nums.take(3).to_array();
    println("D1: {}", taken.len());    // D1: 3
    println("D2: {}", taken[2]);       // D2: 3

    let skipped: i32[] = nums.skip(4).to_array();
    println("D3: {}", skipped.len());  // D3: 2
    println("D4: {}", skipped[0]);     // D4: 5

    // ----------------------------------------------------------
    // E. count
    // ----------------------------------------------------------
    let cnt: i32 = nums.filter((x: i32) => x > 3).count();
    println("E1: {}", cnt);            // E1: 3

    // ----------------------------------------------------------
    // F. first（正常・空配列）
    // ----------------------------------------------------------
    let f1 = nums.filter((x: i32) => x > 4).first();
    match f1 {
        Ok(v)  => println("F1: {}", v),   // F1: 5
        Err(e) => println("F1: err"),
    };

    let empty: i32[] = [];
    let f2 = empty.first();
    match f2 {
        Ok(v)  => println("F2: ok"),
        Err(e) => println("F2: err"),     // F2: err
    };

    // ----------------------------------------------------------
    // G. any / all
    // ----------------------------------------------------------
    let has_even: bool = nums.any((x: i32) => x % 2 == 0);
    println("G1: {}", has_even);       // G1: true

    let all_pos: bool = nums.all((x: i32) => x > 0);
    println("G2: {}", all_pos);        // G2: true

    let all_even: bool = nums.all((x: i32) => x % 2 == 0);
    println("G3: {}", all_even);       // G3: false

    // ----------------------------------------------------------
    // H. aggregate 初期値なし（合計）
    // ----------------------------------------------------------
    let small: i32[] = [1, 2, 3, 4, 5];
    let sum = small.aggregate((a: i32, b: i32) => a + b);
    match sum {
        Ok(v)  => println("H1: {}", v),   // H1: 15
        Err(e) => println("H1: err"),
    };

    // ----------------------------------------------------------
    // I. aggregate 初期値あり（0 から足す）
    // ----------------------------------------------------------
    let sum2: i32 = small.aggregate(0, (acc: i32, x: i32) => acc + x);
    println("I1: {}", sum2);           // I1: 15

    // ----------------------------------------------------------
    // J. for_each 副作用確認
    // ----------------------------------------------------------
    let fa: i32[] = [10, 20, 30];
    fa.for_each((x: i32) => println("J: {}", x));
    // J: 10
    // J: 20
    // J: 30

    // ----------------------------------------------------------
    // K. select_many（#65 v0.5.0 実装）
    // ----------------------------------------------------------
    let sm_src: i32[] = [1, 2, 3];
    let sm_flat: i32[] = sm_src.select_many((x: i32) => [x, x * 10]).to_array();
    println("K1: {}", sm_flat.len());  // K1: 6
    println("K2: {}", sm_flat[0]);     // K2: 1
    println("K3: {}", sm_flat[1]);     // K3: 10
    println("K4: {}", sm_flat[5]);     // K4: 30

    // ----------------------------------------------------------
    // L. C1: filter 全要素通過 / 全要素除外
    // ----------------------------------------------------------
    let all_pass: i32[] = nums.filter((x: i32) => x > 0).to_array();
    println("L1: {}", all_pass.len()); // L1: 6

    let none_pass: i32[] = nums.filter((x: i32) => x > 100).to_array();
    println("L2: {}", none_pass.len()); // L2: 0

    // ----------------------------------------------------------
    // M. take(0) / take(n>len) 境界値
    // ----------------------------------------------------------
    let t0: i32[] = nums.take(0).to_array();
    println("M1: {}", t0.len());       // M1: 0

    let t_over: i32[] = nums.take(100).to_array();
    println("M2: {}", t_over.len());   // M2: 6

    // ----------------------------------------------------------
    // N. aggregate 空配列 → Err
    // ----------------------------------------------------------
    let empty2: i32[] = [];
    let agg_empty = empty2.aggregate((a: i32, b: i32) => a + b);
    match agg_empty {
        Ok(v)  => println("N1: ok"),
        Err(e) => println("N1: err"),  // N1: err
    };

    // ----------------------------------------------------------
    // O. MC/DC any: 最初で true / 全て false
    // ----------------------------------------------------------
    let singles: i32[] = [99, 1, 2, 3];
    let any_big: bool = singles.any((x: i32) => x > 50);
    println("O1: {}", any_big);        // O1: true

    let any_neg: bool = nums.any((x: i32) => x < 0);
    println("O2: {}", any_neg);        // O2: false

    // ----------------------------------------------------------
    // P. MC/DC all: 最初で false / 全て true
    // ----------------------------------------------------------
    let all_small: bool = singles.all((x: i32) => x < 50);
    println("P1: {}", all_small);      // P1: false

    let all_pos2: bool = small.all((x: i32) => x > 0);
    println("P2: {}", all_pos2);       // P2: true

    println("=== OK ===");
    return 0;
}
