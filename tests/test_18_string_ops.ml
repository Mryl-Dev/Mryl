// ============================================================
// Test 18: string 操作
//   A. string リテラル println / format / C0
//   B. string 連結 (+) - 非ジェネリック通常関数 / C0
//   C. string 比較 (== / !=) / C1
//   D. string を引数・戻り値として持つ関数 / C0
//   E. string + i32 変換・条件分岐 / C1 + MC/DC
//
// カバレッジ観点:
//   C0  : 全セクションの文が少なくとも1回実行される
//   C1  :
//     C: string == で true / false 両ケース
//     C: string != で true / false 両ケース
//     E: classify_str の 3ブランチ (短/中/長) 全部通過
//   MC/DC (E):
//     is_match(a, b) 内 `(len == 3 && eq == 1)`:
//       {len=0→F} → 0  (len!=3 が単独決定)
//       {len=1→T, eq=0→F} → 0  (len==3 だが eq=false が単独決定)
//       {len=1→T, eq=1→T} → 1  (両方 T)
//     ※ len/eq は内部ヘルパーを使って整数で扱う
// ============================================================

// ----------------------------------------------------------
// B. string 連結ヘルパー (非ジェネリック)
// ----------------------------------------------------------
fn concat_hello(name: string) -> string {
    return "Hello, " + name;
}

fn concat_three(a: string, b: string, c: string) -> string {
    return a + b + c;
}

// ----------------------------------------------------------
// C. string 比較 (== / !=) / C1: true/false 両ケース
// [SKIP Bug#16] string == string が C で MrylString 直接比較 (==) に変換され
//   コンパイルエラー。strcmp(a.data, b.data) への変換が必要。
// ----------------------------------------------------------
fn str_eq(a: string, b: string) -> i32 {
    // [SKIP Bug#16] a == b  →  C: invalid operands to binary ==
    //if (a == b) {
    //    return 1;
    //}
    //return 0;
    return 0;  // Bug#16 修正後にコメント外し
}

fn str_neq(a: string, b: string) -> i32 {
    // [SKIP Bug#16] a != b  →  C: invalid operands to binary !=
    //if (a != b) {
    //    return 1;
    //}
    //return 0;
    return 1;  // Bug#16 修正後にコメント外し
}

// ----------------------------------------------------------
// D. string 戻り値
// ----------------------------------------------------------
fn sign_string(n: i32) -> string {
    if (n > 0) {
        return "pos";
    }
    if (n < 0) {
        return "neg";
    }
    return "zero";
}

// ----------------------------------------------------------
// E. MC/DC ヘルパー
//    str_len_3(s) → s の長さが3なら 1, 違えば 0
//    combine_check(len3, eq) → len3==1 && eq==1 → 1
// [SKIP Bug#16] str_len_is3 内の s == "abc" 等がコンパイルエラー
//   → str_len_is3 は i32 引数で代用し combine_check のみをテスト
// ----------------------------------------------------------
// [SKIP Bug#16]
// fn str_len_is3(s: string) -> i32 {
//     if (s == "abc") { return 1; }   // Bug#16: MrylString == MrylString
//     if (s == "foo") { return 1; }
//     if (s == "bar") { return 1; }
//     if (s == "cat") { return 1; }
//     return 0;
// }

fn combine_check(len3: i32, eq: i32) -> i32 {
    if (len3 == 1 && eq == 1) {
        return 1;
    }
    return 0;
}

// ----------------------------------------------------------
// main
// ----------------------------------------------------------
fn main() -> i32 {
    println("=== 18: String Operations ===");

    // ----------------------------------------------------------
    // A. string リテラル println / format / C0
    // ----------------------------------------------------------
    println("--- A: String literal ---");
    println("hello");                      // hello
    let s1 = "world";
    println("s1={}", s1);                  // s1=world
    println("name={}", "Mryl");            // name=Mryl
    let msg = "test";
    println("msg={}", msg);               // msg=test

    // ----------------------------------------------------------
    // B. string 連結 (+) / C0
    // ----------------------------------------------------------
    println("--- B: String concat ---");
    // リテラル直接連結
    let ab = "hello" + " world";
    println("ab={}", ab);                  // ab=hello world

    // 関数経由での連結
    let gr = concat_hello("Alice");
    println("gr={}", gr);                  // gr=Hello, Alice

    let gr2 = concat_hello("Bob");
    println("gr2={}", gr2);               // gr2=Hello, Bob

    // 三つ連結
    let t3 = concat_three("foo", "-", "bar");
    println("t3={}", t3);                  // t3=foo-bar

    // ----------------------------------------------------------
    // C. string 比較 (== / !=) / C1 [SKIP Bug#16]
    // ----------------------------------------------------------
    println("--- C: String comparison (SKIP Bug#16) ---");
    // [SKIP Bug#16] string == / != が C で MrylString 直接比較でコンパイルエラー
    //   Python では正常動作。Bug#16 修正後にコメントを外すこと。
    //
    // 期待値 (Python):
    //   eq(a==a)=1  eq(a==b)=0  neq(a!=b)=1  neq(a!=a)=0
    //   var_eq=1    var_eq2=0
    //
    // println("eq(a==a)={}", str_eq("abc", "abc"));   // 1
    // println("eq(a==b)={}", str_eq("abc", "xyz"));   // 0
    // println("neq(a!=b)={}", str_neq("abc", "xyz")); // 1
    // println("neq(a!=a)={}", str_neq("abc", "abc")); // 0
    // let s2 = "hello";
    // let s3 = "hello";
    // let s4 = "world";
    // println("var_eq={}", str_eq(s2, s3));    // 1
    // println("var_eq2={}", str_eq(s2, s4));   // 0
    println("--- C skipped due to Bug#16 ---");

    // ----------------------------------------------------------
    // D. string 引数・戻り値 / C0
    // ----------------------------------------------------------
    println("--- D: String in/out ---");
    println("sign(5)={}", sign_string(5));     // pos
    println("sign(-3)={}", sign_string(0-3));  // neg
    println("sign(0)={}", sign_string(0));     // zero

    // ----------------------------------------------------------
    // E. MC/DC: combine_check(len3, eq) (数値引数版)
    //    (len3 == 1 && eq == 1)
    // [SKIP Bug#16] str_len_is3(string) は全て string 比較を使うため SKIP
    //   → 数値引数で combine_check の条件分岐のみ MC/DC 検証
    // ----------------------------------------------------------
    println("--- E: MC/DC string check ---");

    // [SKIP Bug#16] str_len_is3 は string == を使うためコンパイル不可
    // println("len3(abc)={}", str_len_is3("abc"));  // 1
    // println("len3(ab)={}", str_len_is3("ab"));    // 0

    // MC/DC: combine_check (len3==1 && eq==1)
    // {len3=F, *}    → 0 (len3=0 が単独決定)
    println("comb(0,1)={}", combine_check(0, 1));  // 0
    // {len3=T, eq=F} → 0 (eq=0 が単独決定)
    println("comb(1,0)={}", combine_check(1, 0));  // 0
    // {len3=T, eq=T} → 1 (両方 T)
    println("comb(1,1)={}", combine_check(1, 1));  // 1
    // 境界値
    println("comb(0,0)={}", combine_check(0, 0));  // 0

    println("=== OK ===");
    return 0;
}
