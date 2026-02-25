// ============================================================
// Test 07: Result<T,E> / Ok / Err / .try()
//   A. 基本 Result (Ok/Err return + match)
//   B. C1: Ok アーム / Err アーム両方を実行
//   C. f64 Result  [Bug#8: C native で f64 が %d  SKIP]
//   D. .try() 成功パス
//   E. Result を使った処理チェーン
//
// カバレッジ観点:
//   C0  : 全関数, Ok/Err 両アーム, .try() を少なくとも1回実行
//   C1  :
//     A/B: divide() の if(b==0)  true(Err)/false(Ok) 両ブランチを実行
//     E: chain_divide() 内の中間 Ok/Err 両ケースを実行
//   MC/DC:
//     safe_divide() 内 (a < 0 || b == 0):
//       {a<0=T, *}           Err  (a<0 が T で短絡=単独決定)
//       {a<0=F, b==0=T}      Err  (b==0 が T で単独決定)
//       {a<0=F, b==0=F}      Ok   (両方 F で Ok に決定)
//
// 既知バグ:
//   Bug#7: Err(string) の中身を println で表示すると C native でゴミ値
//           Err アームでは文字列を print せずセンチネル値(-1)を返す
//   Bug#8: f64 が C native で %d 扱い  safe_sqrt セクションをスキップ
// ============================================================

// ----------------------------------------------------------
// A/B. 基本 Result / C1: Ok + Err 両ブランチ
// ----------------------------------------------------------
fn divide(a: i32, b: i32) -> Result<i32, string> {
    if (b == 0) {
        return Err("div by zero");
    }
    return Ok(a / b);
}

// ----------------------------------------------------------
// MC/DC: (a < 0 || b == 0)
// ----------------------------------------------------------
fn safe_divide(a: i32, b: i32) -> Result<i32, string> {
    if (a < 0 || b == 0) {
        return Err("invalid");
    }
    return Ok(a / b);
}

// ----------------------------------------------------------
// C. f64 Result [Bug#8 SKIP]
// ----------------------------------------------------------
// fn safe_sqrt(x: f64) -> Result<f64, string> {
//     if (x < 0.0) {
//         return Err("negative input");
//     }
//     let g = x / 2.0;
//     g = (g + x / g) / 2.0;
//     g = (g + x / g) / 2.0;
//     return Ok(g);
// }

fn parse_positive(n: i32) -> Result<i32, string> {
    if (n <= 0) {
        return Err("not positive");
    }
    return Ok(n);
}

// ----------------------------------------------------------
// E. Result チェーン: divide の結果を続けて divide
// ----------------------------------------------------------
fn chain_divide(a: i32, b: i32, c: i32) -> i32 {
    let r1 = divide(a, b);
    let v1: i32 = match r1 {
        Ok(v)  => v,
        Err(e) => -1,
    };
    if (v1 < 0) {
        return -1;
    }
    let r2 = divide(v1, c);
    let v2: i32 = match r2 {
        Ok(v)  => v,
        Err(e) => -1,
    };
    return v2;
}

// ----------------------------------------------------------
// main
// ----------------------------------------------------------
fn main() -> i32 {
    println("=== 07: Result ===");

    // ----------------------------------------------------------
    // A. 基本 Result + B. C1: Ok アーム
    // ----------------------------------------------------------
    println("--- A/B: Ok path ---");
    let r1 = divide(10, 2);
    let v1: i32 = match r1 {
        Ok(v)  => v,
        Err(e) => -1,
    };
    println("10/2={}", v1);   // 5

    let r2 = divide(7, 3);
    let v2: i32 = match r2 {
        Ok(v)  => v,
        Err(e) => -1,
    };
    println("7/3={}", v2);    // 2  (integer division)

    // B. C1: Err アーム
    println("--- B: Err path ---");
    let r3 = divide(5, 0);
    let v3: i32 = match r3 {
        Ok(v)  => v,
        Err(e) => -1,      // [Bug#7] e を println しない
    };
    println("5/0={}", v3);    // -1

    // parse_positive C1
    let rp1 = parse_positive(10);
    let vp1: i32 = match rp1 {
        Ok(v)  => v,
        Err(e) => -1,
    };
    println("pp(10)={}", vp1);   // 10

    let rp2 = parse_positive(-5);
    let vp2: i32 = match rp2 {
        Ok(v)  => v,
        Err(e) => -1,
    };
    println("pp(-5)={}", vp2);   // -1

    let rp3 = parse_positive(0);
    let vp3: i32 = match rp3 {
        Ok(v)  => v,
        Err(e) => -1,
    };
    println("pp(0)={}", vp3);    // -1

    // ----------------------------------------------------------
    // C. f64 Result [SKIP Bug#8]
    // ----------------------------------------------------------
    println("--- C: f64 Result (SKIP Bug#8) ---");
    // let sr1 = safe_sqrt(9.0);
    // let sv1: f64 = match sr1 { Ok(v) => v, Err(e) => -1.0 };
    // println("sqrt(9)={}", sv1);     // ~3.0
    //
    // let sr2 = safe_sqrt(-4.0);
    // let sv2: f64 = match sr2 { Ok(v) => v, Err(e) => -1.0 };
    // println("sqrt(-4)={}", sv2);    // -1.0

    // ----------------------------------------------------------
    // MC/DC: safe_divide (a < 0 || b == 0)
    // ----------------------------------------------------------
    println("--- MC/DC: safe_divide ---");

    // {a<0=T, *}  Err (-1): a<0 が T で短絡=単独決定
    let rs1 = safe_divide(-1, 5);
    let vs1: i32 = match rs1 { Ok(v) => v, Err(e) => -1 };
    println("safe(-1,5)={}", vs1);   // -1

    // {a<0=F, b==0=T}  Err (-1): b==0 が T で単独決定
    let rs2 = safe_divide(5, 0);
    let vs2: i32 = match rs2 { Ok(v) => v, Err(e) => -1 };
    println("safe(5,0)={}", vs2);    // -1

    // {a<0=F, b==0=F}  Ok: 両方 F で Ok に決定
    let rs3 = safe_divide(10, 2);
    let vs3: i32 = match rs3 { Ok(v) => v, Err(e) => -1 };
    println("safe(10,2)={}", vs3);   // 5

    // ----------------------------------------------------------
    // D. .try() 成功パス
    // ----------------------------------------------------------
    println("--- D: .try() ---");
    let tv = divide(20, 4).try();
    println("try(20,4)={}", tv);    // 5

    // ----------------------------------------------------------
    // E. Result チェーン (C0)
    // ----------------------------------------------------------
    println("--- E: Chain ---");
    // chain: (12/3)/2 = 2
    println("chain(12,3,2)={}", chain_divide(12, 3, 2));   // 2
    // chain: 最初の divide が Err (b=0)  -1
    println("chain(12,0,2)={}", chain_divide(12, 0, 2));   // -1
    // chain: 二番目の divide が Err (c=0)  -1
    println("chain(12,3,0)={}", chain_divide(12, 3, 0));   // -1

    println("=== OK ===");
    return 0;
}
