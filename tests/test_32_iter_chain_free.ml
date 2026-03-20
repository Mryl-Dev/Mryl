// ============================================================
// Test 32: Iter<T> チェーン呼び出しの中間 MrylVec 解放 (fix #62)
//
//   A. select → count  （中間 1 段）
//   B. filter → count  （中間 1 段）
//   C. select → filter → count  （中間 2 段）
//   D. filter → select → count  （中間 2 段）
//   E. select → filter → select → count  （中間 3 段）
//   F. select → skip → count  （skip: src_is_temp=True → コピー方式）
//   G. select → take → count  （take: 所有権移転）
//   H. select → skip → take → count  （複合チェーン）
//   I. select → any  （終端 any）
//   J. filter → all  （終端 all）
//   K. filter → first  （終端 first）
//   L. select → aggregate 初期値あり  （終端 aggregate）
//   M. filter → aggregate 初期値なし  （終端 aggregate）
//   N. filter → for_each  （終端 for_each）
//   O. select → filter → to_array  （to_array で所有権移転）
//   P. skip: ユーザー変数 → view 方式（従来動作維持）
//
// カバレッジ観点:
//   C0  : 各メソッドのチェーン経路を少なくとも 1 回
//   C1  : 深さ 1 / 2 / 3 のチェーン
//   MC/DC: skip の src_is_temp=True/False 両分岐
// ============================================================

fn main() -> i32 {
    let nums: i32[] = [1, 2, 3, 4, 5, 6];

    // ----------------------------------------------------------
    // A. select → count
    // ----------------------------------------------------------
    let ca: i32 = nums.select((x: i32) => x * 2).count();
    println("A1: {}", ca);   // A1: 6

    // ----------------------------------------------------------
    // B. filter → count
    // ----------------------------------------------------------
    let cb: i32 = nums.filter((x: i32) => x > 3).count();
    println("B1: {}", cb);   // B1: 3

    // ----------------------------------------------------------
    // C. select → filter → count  （中間 2 段）
    // ----------------------------------------------------------
    let cc: i32 = nums.select((x: i32) => x * 2).filter((x: i32) => x > 6).count();
    println("C1: {}", cc);   // C1: 3

    // ----------------------------------------------------------
    // D. filter → select → count  （中間 2 段）
    // ----------------------------------------------------------
    let cd: i32 = nums.filter((x: i32) => x % 2 == 0).select((x: i32) => x * 10).count();
    println("D1: {}", cd);   // D1: 3

    // ----------------------------------------------------------
    // E. select → filter → select → count  （中間 3 段）
    // ----------------------------------------------------------
    let ce: i32 = nums
        .select((x: i32) => x * 3)
        .filter((x: i32) => x > 6)
        .select((x: i32) => x + 1)
        .count();
    println("E1: {}", ce);   // E1: 4

    // ----------------------------------------------------------
    // F. select → skip → count  （skip: src_is_temp=True → コピー方式）
    // ----------------------------------------------------------
    let cf: i32 = nums.select((x: i32) => x * 2).skip(3).count();
    println("F1: {}", cf);   // F1: 3

    // ----------------------------------------------------------
    // G. select → take → count  （take: 所有権移転）
    // ----------------------------------------------------------
    let cg: i32 = nums.select((x: i32) => x + 100).take(4).count();
    println("G1: {}", cg);   // G1: 4

    // ----------------------------------------------------------
    // H. select → skip → take → count  （複合チェーン）
    // ----------------------------------------------------------
    let ch: i32 = nums.select((x: i32) => x * 2).skip(2).take(3).count();
    println("H1: {}", ch);   // H1: 3

    // ----------------------------------------------------------
    // I. select → any  （終端 any）
    // ----------------------------------------------------------
    let ci: bool = nums.select((x: i32) => x * 2).any((x: i32) => x > 10);
    println("I1: {}", ci);   // I1: true

    // ----------------------------------------------------------
    // J. filter → all  （終端 all）
    // ----------------------------------------------------------
    let cj: bool = nums.filter((x: i32) => x > 2).all((x: i32) => x > 0);
    println("J1: {}", cj);   // J1: true

    // ----------------------------------------------------------
    // K. filter → first  （終端 first）
    // ----------------------------------------------------------
    let ck = nums.filter((x: i32) => x > 4).first();
    match ck {
        Ok(v)  => println("K1: {}", v),   // K1: 5
        Err(e) => println("K1: err"),
    };

    // ----------------------------------------------------------
    // L. select → aggregate 初期値あり  （終端 aggregate）
    // ----------------------------------------------------------
    let cl: i32 = nums.select((x: i32) => x * 2).aggregate(0, (acc: i32, x: i32) => acc + x);
    println("L1: {}", cl);   // L1: 42

    // ----------------------------------------------------------
    // M. filter → aggregate 初期値なし  （終端 aggregate）
    // ----------------------------------------------------------
    let cm = nums.filter((x: i32) => x % 2 == 0).aggregate((a: i32, b: i32) => a + b);
    match cm {
        Ok(v)  => println("M1: {}", v),   // M1: 12
        Err(e) => println("M1: err"),
    };

    // ----------------------------------------------------------
    // N. filter → for_each  （終端 for_each）
    // ----------------------------------------------------------
    nums.filter((x: i32) => x > 4).for_each((x: i32) => println("N: {}", x));
    // N: 5
    // N: 6

    // ----------------------------------------------------------
    // O. select → filter → to_array  （to_array で所有権移転）
    // ----------------------------------------------------------
    let co: i32[] = nums.select((x: i32) => x * 10).filter((x: i32) => x > 30).to_array();
    println("O1: {}", co.len());   // O1: 3
    println("O2: {}", co[0]);      // O2: 40

    // ----------------------------------------------------------
    // P. skip: ユーザー変数 → view 方式（従来動作維持）
    // ----------------------------------------------------------
    let skipped: i32[] = nums.skip(4).to_array();
    println("P1: {}", skipped.len());   // P1: 2
    println("P2: {}", skipped[0]);      // P2: 5

    println("=== OK ===");
    return 0;
}
