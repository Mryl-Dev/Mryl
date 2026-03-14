// ============================================================
// Test 33: select_many C コード生成 (#65)
//   A. ArrayLiteral 返却ラムダ（基本展開）
//   B. VarRef 返却ラムダ（既存配列 flatten）
//   C. select_many → to_array チェーン
//   D. select_many → count（終端操作チェーン）
//   E. select_many → filter（中間操作チェーン）
//   F. 空要素が混在する配列（MC/DC: inner.len == 0 分岐）
//   G. 単要素配列（C1: 要素数1）
//   H. select_many → select チェーン（変換と展開の組み合わせ）
//   I. src_is_temp=True（select → select_many チェーン）
//
// カバレッジ観点:
//   C0  : 各コードパスを最低1回実行
//   C1  : inner.len == 0 / inner.len > 0、src 空の境界値
//   MC/DC: inner_needs_free の分岐（ArrayLiteral vs VarRef）
// ============================================================

fn helper_range(n: i32) -> i32[] {
    let result: i32[] = [];
    let i: i32 = 0;
    while (i < n) {
        result.push(i + 1);
        i = i + 1;
    }
    return result;
}

fn main() -> i32 {

    // ----------------------------------------------------------
    // A. ArrayLiteral 返却ラムダ（基本展開）
    //    各 x に対して [x, x * 10] を生成・展開
    // ----------------------------------------------------------
    let nums: i32[] = [1, 2, 3];
    let flat_a: i32[] = nums.select_many((x: i32) => [x, x * 10]).to_array();
    println("A1: {}", flat_a.len());   // A1: 6
    println("A2: {}", flat_a[0]);      // A2: 1
    println("A3: {}", flat_a[1]);      // A3: 10
    println("A4: {}", flat_a[4]);      // A4: 3
    println("A5: {}", flat_a[5]);      // A5: 30

    // ----------------------------------------------------------
    // B. FunctionCall 返却ラムダ（ヘルパー関数経由の展開）
    //    helper_range(n) → [1..n] を flatten
    // ----------------------------------------------------------
    let sizes: i32[] = [3, 2, 1];
    let flat_b: i32[] = sizes.select_many((n: i32) => helper_range(n)).to_array();
    println("B1: {}", flat_b.len());   // B1: 6
    println("B2: {}", flat_b[0]);      // B2: 1
    println("B3: {}", flat_b[3]);      // B3: 1
    println("B4: {}", flat_b[5]);      // B4: 1

    // ----------------------------------------------------------
    // C. select_many → count チェーン（終端操作）
    // ----------------------------------------------------------
    let cnt: i32 = nums.select_many((x: i32) => [x, x * 10]).count();
    println("C1: {}", cnt);            // C1: 6

    // ----------------------------------------------------------
    // D. select_many → filter チェーン（中間操作）
    //    展開後に偶数だけ残す
    // ----------------------------------------------------------
    let evens: i32[] = nums
        .select_many((x: i32) => [x, x * 10])
        .filter((v: i32) => v % 2 == 0)
        .to_array();
    println("D1: {}", evens.len());    // D1: 4  (10, 2, 20, 30 が偶数)
    println("D2: {}", evens[0]);       // D2: 10
    println("D3: {}", evens[2]);       // D3: 20

    // ----------------------------------------------------------
    // E. 空 inner が混在する配列（C1: inner.len == 0 の分岐）
    //    x=2 のとき helper_range(0)=[] → inner.len==0 パスを通る
    // ----------------------------------------------------------
    let mixed: i32[] = [2, 3, 4];
    let flat_e: i32[] = mixed
        .select_many((x: i32) => helper_range(x - 2))
        .to_array();
    // x=2: helper_range(0)=[], x=3: helper_range(1)=[1], x=4: helper_range(2)=[1,2]
    println("E1: {}", flat_e.len());   // E1: 3
    println("E2: {}", flat_e[0]);      // E2: 1
    println("E3: {}", flat_e[2]);      // E3: 2

    // ----------------------------------------------------------
    // F. 単要素配列（C1: ソース len == 1）
    // ----------------------------------------------------------
    let one: i32[] = [5];
    let flat_f: i32[] = one.select_many((x: i32) => [x, x + 1]).to_array();
    println("F1: {}", flat_f.len());   // F1: 2
    println("F2: {}", flat_f[0]);      // F2: 5
    println("F3: {}", flat_f[1]);      // F3: 6

    // ----------------------------------------------------------
    // G. select → select_many チェーン（src_is_temp=True）
    //    select で i32 → i32 変換後に select_many で展開
    // ----------------------------------------------------------
    let base: i32[] = [1, 2];
    let flat_g: i32[] = base
        .select((x: i32) => x * 2)
        .select_many((x: i32) => [x, x + 1])
        .to_array();
    println("G1: {}", flat_g.len());   // G1: 4
    println("G2: {}", flat_g[0]);      // G2: 2
    println("G3: {}", flat_g[1]);      // G3: 3
    println("G4: {}", flat_g[2]);      // G4: 4
    println("G5: {}", flat_g[3]);      // G5: 5

    // ----------------------------------------------------------
    // H. select_many → select チェーン（展開後に変換）
    // ----------------------------------------------------------
    let flat_h: i32[] = nums
        .select_many((x: i32) => [x, x * 10])
        .select((v: i32) => v + 1)
        .to_array();
    println("H1: {}", flat_h.len());   // H1: 6
    println("H2: {}", flat_h[0]);      // H2: 2
    println("H3: {}", flat_h[1]);      // H3: 11

    return 0;
}
