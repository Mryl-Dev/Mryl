// ============================================================
// Test 24: Zero Division Safety (issue #13)
//   A. 整数 / と % 演算子 - 非ゼロ除算            (C0: 正常経路確認)
//   B. checked_div(a, b) -> Result<i32, string>  (C1: Ok  経路)
//   C. checked_div(a, b) -> Result<i32, string>  (C1: Err 経路)
//
// カバレッジ観点:
//   C0  : / 演算子, % 演算子, checked_div を 1 回以上実行
//   C1  :
//     B: checked_div の if(b==0) false ブランチ → Ok
//     C: checked_div の if(b==0) true  ブランチ → Err
//   MC/DC:
//     checked_div 内 (b == 0) は単一条件のため C1 = MC/DC
//       T24-06: b= 3 → b==0=F → Ok  (false ブランチ; 単独決定)
//       T24-09: b= 0 → b==0=T → Err (true  ブランチ; 単独決定)
//     MC/DC achieved: {T24-06, T24-09} for (b == 0)
//
// 既知バグ:
//   Bug#7: Err(string) の中身を println で表示すると C native でゴミ値
//          Err アームでは文字列を print せずセンチネル値(-1)を返す
//
// Note:
//   / と % のゼロ除算経路 (mryl_safe_div/mryl_safe_mod の panic ブランチ) は
//   Mryl コード内から到達不可のため本テストの対象外とする
// ============================================================

fn main() -> i32 {
    println("=== 24: Zero Division Safety ===");

    // ----------------------------------------------------------
    // A. 整数 / と % - 非ゼロ除算 (C0)
    // T24-01: 10 / 3 = 3   (余り切り捨て: 代表値)
    // T24-02: 10 % 3 = 1   (剰余: 代表値)
    // T24-03: 20 / 4 = 5   (割り切れる値)
    // T24-04: 0  / 5 = 0   (被除数 = 0: 最小境界)
    // T24-05: 0  % 7 = 0   (被除数 = 0: 最小境界)
    // ----------------------------------------------------------
    println("--- A: integer div and mod ---");

    // T24-01
    let q1: i32 = 10 / 3;
    println("10/3={}", q1);          // 3

    // T24-02
    let r1: i32 = 10 % 3;
    println("10%3={}", r1);          // 1

    // T24-03
    let q2: i32 = 20 / 4;
    println("20/4={}", q2);          // 5

    // T24-04: 被除数 = 0
    let q3: i32 = 0 / 5;
    println("0/5={}", q3);           // 0

    // T24-05: 被除数 = 0
    let r2: i32 = 0 % 7;
    println("0%7={}", r2);           // 0

    // ----------------------------------------------------------
    // B. checked_div - C1: if(b==0) false ブランチ → Ok
    // T24-06: checked_div(10, 3) → Ok(3)  (余り切り捨て: 代表値)
    // T24-07: checked_div(20, 4) → Ok(5)  (割り切れる値)
    // T24-08: checked_div(0,  5) → Ok(0)  (被除数 = 0: 最小境界)
    // ----------------------------------------------------------
    println("--- B: checked_div Ok ---");

    // T24-06: 代表値  [MC/DC: b==0=F で単独決定]
    let cr1: Result<i32, string> = checked_div(10, 3);
    let cv1: i32 = match cr1 {
        Ok(v)  => v,
        Err(e) => -1,
    };
    println("checked_div(10,3)={}", cv1);    // 3

    // T24-07: 割り切れる値
    let cr2: Result<i32, string> = checked_div(20, 4);
    let cv2: i32 = match cr2 {
        Ok(v)  => v,
        Err(e) => -1,
    };
    println("checked_div(20,4)={}", cv2);    // 5

    // T24-08: 被除数 = 0
    let cr3: Result<i32, string> = checked_div(0, 5);
    let cv3: i32 = match cr3 {
        Ok(v)  => v,
        Err(e) => -1,
    };
    println("checked_div(0,5)={}", cv3);     // 0

    // ----------------------------------------------------------
    // C. checked_div - C1: if(b==0) true ブランチ → Err
    // T24-09: checked_div(7,  0) → Err → sentinel -1  [MC/DC: b==0=T で単独決定]
    // T24-10: checked_div(0,  0) → Err → sentinel -1  (被除数・除数ともに 0)
    // [Bug#7] Err 文字列を println に渡すと C native でゴミ値 → sentinel を返す
    // ----------------------------------------------------------
    println("--- C: checked_div Err ---");

    // T24-09: 除数 = 0  [MC/DC: b==0=T で単独決定]
    let cr4: Result<i32, string> = checked_div(7, 0);
    let cv4: i32 = match cr4 {
        Ok(v)  => v,
        Err(e) => -1,    // [Bug#7] e を print しない
    };
    println("checked_div(7,0)={}", cv4);     // -1

    // T24-10: 被除数・除数ともに 0
    let cr5: Result<i32, string> = checked_div(0, 0);
    let cv5: i32 = match cr5 {
        Ok(v)  => v,
        Err(e) => -1,    // [Bug#7]
    };
    println("checked_div(0,0)={}", cv5);     // -1

    println("=== OK ===");
    return 0;
}
