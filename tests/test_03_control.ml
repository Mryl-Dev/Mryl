// ============================================================
// Test 03: 制御フロー
//   A. if/else if/else / B. while / C. for Rust / D. for C
//   E. ネスト制御 / F. return 早期脱出
//
// カバレッジ観点:
//   C0  : A〜F 全セクションの文を実行
//   C1  :
//     A: if/else if/else の全分岐を実行
//     B: while の「継続」「脱出」「0回」「break」「continue」経路
//     C: for range の境界(0..0 / 0..3) + 配列イテレーション
//     D: for C スタイルの「条件真」「条件偽」経路
//     E: ネスト内の内側条件の真偽両方を実行
//     F: 早期 return 経路と通常 return 経路の両方を実行
//   MC/DC:
//     A: 各条件が単独で分岐結果を決める
//       score>=90 だけで "A" に到達, score>=70 だけで "B" に到達 など
//     B: while 条件 i<N: i=0(T)〜i=N(F) で両辺値が独立して変化
//     E: ネスト if 条件 v>5 : v=3(F), v=7(T) で分岐結果が反転することを確認
//   備考:
//     D,C の for の MC/DC は条件が自明なため C1 と同等に扱う
// ============================================================

// F. 早期脱出テスト用ヘルパー関数
fn classify(v: i32) -> i32 {
    if (v < 0) {
        return -1;         // 早期 return (負数)
    }
    if (v == 0) {
        return 0;          // 早期 return (ゼロ)
    }
    return 1;              // 通常 return (正数)
}

fn main() -> i32 {
    println("=== 03: Control Flow ===");

    // ----------------------------------------------------------
    // A. if / else if / else チェーン (C1 + MC/DC)
    // ----------------------------------------------------------
    println("--- A: if/else if/else ---");

    // MC/DC: score>=90 が単独で "A" を決める
    let score = 95;
    if (score >= 90) {
        println("grade=A");           // grade=A
    } else if (score >= 70) {
        println("grade=B");
    } else if (score >= 50) {
        println("grade=C");
    } else {
        println("grade=F");
    }

    // MC/DC: score>=90 が F で score>=70 が T  "B"
    score = 75;
    if (score >= 90) {
        println("grade=A");
    } else if (score >= 70) {
        println("grade=B");           // grade=B
    } else if (score >= 50) {
        println("grade=C");
    } else {
        println("grade=F");
    }

    // MC/DC: score>=70 が F で score>=50 が T  "C"
    score = 55;
    if (score >= 90) {
        println("grade=A");
    } else if (score >= 70) {
        println("grade=B");
    } else if (score >= 50) {
        println("grade=C");           // grade=C
    } else {
        println("grade=F");
    }

    // MC/DC: 全条件が F  "F"
    score = 30;
    if (score >= 90) {
        println("grade=A");
    } else if (score >= 70) {
        println("grade=B");
    } else if (score >= 50) {
        println("grade=C");
    } else {
        println("grade=F");           // grade=F
    }

    // C1: else なし if の偽ブランチ (スキップ確認)
    let x = 0;
    if (x > 0) { println("positive"); }
    println("after-if={}", x);        // 0 (ブランチをスキップ)

    // ----------------------------------------------------------
    // B. while ループ (C1: 継続/脱出/0回/break/continue)
    // ----------------------------------------------------------
    println("--- B: while ---");

    // 通常実行 (04 の 5 回)
    let i = 0;
    while (i < 5) {
        println("{}", i);             // 0 1 2 3 4
        i++;
    }

    // 0回実行 (C1: 条件が最初から偽)
    let j = 10;
    while (j < 5) {
        println("never");
    }
    println("0-iter-done");           // 0-iter-done

    // break (C1: break 経路)
    let k = 0;
    while (k < 10) {
        if (k == 3) {
            break;
        }
        println("k={}", k);          // 0 1 2
        k++;
    }

    // continue (C1: continue 経路)
    let m = 0;
    while (m < 5) {
        m++;
        if (m == 3) {
            continue;
        }
        println("m={}", m);          // 1 2 4 5  (3はスキップ)
    }

    // ----------------------------------------------------------
    // C. for Rust スタイル (C1)
    // ----------------------------------------------------------
    println("--- C: for Rust ---");

    // 範囲 0..4 (C1: 条件 n<4 が真偽 の両経路)
    for n in 0..4 {
        println("r={}", n);          // 0 1 2 3
    }

    // 配列イテレーション
    let arr = [10, 20, 30];
    for v in arr {
        println("v={}", v);          // 10 20 30
    }

    // ----------------------------------------------------------
    // D. for C スタイル (C1)
    // ----------------------------------------------------------
    println("--- D: for C ---");

    // 増分 1
    for (let ci = 0; ci < 4; ci++) {
        println("c={}", ci);         // 0 1 2 3
    }

    // 増分 2
    for (let ci = 0; ci < 6; ci = ci + 2) {
        println("c2={}", ci);        // 0 2 4
    }

    // ----------------------------------------------------------
    // E. ネスト制御 (C1 + MC/DC: ネスト内 if 条件の真偽両方)
    // ----------------------------------------------------------
    println("--- E: Nested ---");

    // for 内 if  v>5 が F(3) と T(7) の両方を通る  MC/DC 達成
    let vals = [3, 7, 5];
    for v in vals {
        if (v > 5) {
            println("big={}", v);    // 7
        } else {
            println("small={}", v);  // 3, 5
        }
    }

    // while 内 while (ネスト2段)
    let oi = 0;
    while (oi < 3) {
        let ij = 0;
        while (ij < 2) {
            println("o={} i={}", oi, ij); // (0,0)(0,1)(1,0)(1,1)(2,0)(2,1)
            ij++;
        }
        oi++;
    }

    // ----------------------------------------------------------
    // F. return 早期脱出 (C1: 早期 return / 通常 return 両方)
    // ----------------------------------------------------------
    println("--- F: early return ---");
    println("classify(-5)={}", classify(0 - 5));  // -1 (早期 return)
    println("classify(0)={}", classify(0));        // 0  (早期 return)
    println("classify(3)={}", classify(3));        // 1  (通常 return)

    // ----------------------------------------------------------
    // G. 包含レンジ `to` (#10)
    // ----------------------------------------------------------
    println("--- G: inclusive range to ---");

    // T03-G1: 0 to 4 → 0,1,2,3,4 の合計 = 10
    let to_sum: i32 = 0;
    for i in 0 to 4 {
        to_sum = to_sum + i;
    }
    println("to_sum_0_4={}", to_sum);    // 10

    // T03-G2: 1 to 1 → 1回だけ (境界値: 等値)
    let to_one: i32 = 0;
    for i in 1 to 1 {
        to_one = to_one + i;
    }
    println("to_one={}", to_one);        // 1

    // T03-G3: 変数を上限に使用
    let lo: i32 = 3;
    let hi: i32 = 6;
    let to_var: i32 = 0;
    for i in lo to hi {
        to_var = to_var + i;
    }
    println("to_var_3_6={}", to_var);    // 18 (3+4+5+6)

    println("=== OK ===");
    return 0;
}
