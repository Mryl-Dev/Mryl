// ============================================================
// Test 22: ユーザー入力 (read_line / parse_int / parse_f64)
//
//   A. read_line — 文字列の読み取り
//   B. parse_int — 文字列 → i32 変換
//   C. parse_f64 — 文字列 → f64 変換
//   D. 組み合わせ — read_line + parse_int / parse_f64
//   E. fix との連携 — read_line 結果を fix に代入
//
// テスト方法: 標準入力をリダイレクト
//   echo "hello\n42\n3.14\n100\n2.5\nworld" | Mryl test_22_input.ml
// ============================================================

fn main() -> i32 {
    println("=== 22: Input ===");

    // ----------------------------------------------------------
    // A. read_line — echo 入力からの読み取り
    // ----------------------------------------------------------
    println("--- A: read_line ---");
    let a_s: string = read_line();
    println("got={}", a_s);

    // ----------------------------------------------------------
    // B. parse_int
    // ----------------------------------------------------------
    println("--- B: parse_int ---");
    let b_s: string = read_line();
    let b_n: i32    = parse_int(b_s);
    println("int={}", b_n);
    println("int+1={}", b_n + 1);

    // ----------------------------------------------------------
    // C. parse_f64
    // ----------------------------------------------------------
    println("--- C: parse_f64 ---");
    let c_s: string = read_line();
    let c_f: f64    = parse_f64(c_s);
    println("f64={}", c_f);
    println("f64*2={}", c_f * 2.0);

    // ----------------------------------------------------------
    // D. 組み合わせ
    // ----------------------------------------------------------
    println("--- D: combined ---");
    let d_s1: string = read_line();
    let d_s2: string = read_line();
    let d_n: i32     = parse_int(d_s1);
    let d_f: f64     = parse_f64(d_s2);
    println("sum={}", d_n + 1);
    println("prod={}", d_f * 3.0);

    // ----------------------------------------------------------
    // E. fix との連携
    // ----------------------------------------------------------
    println("--- E: fix ---");
    let e_raw: string = read_line();
    fix e_s: string   = e_raw;
    println("fix_str={}", e_s);

    println("=== OK ===");
    return 0;
}
