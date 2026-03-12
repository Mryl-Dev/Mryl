// test_29_string_find.ml
// string.find() -> Option<i32> のテスト (fix #54)
//
// カバレッジ:
//   A. 基本検索（見つかる）
//   B. 見つからない場合 -> None
//   C. 空文字列パターン -> Some(0)
//   D. 先頭マッチ
//   E. 末尾近傍マッチ
//   F. 複数出現（最初の位置を返す）
//   G. 関数戻り値として Option<i32>
//   H. find() 結果を match で分岐

fn find_sub(s: string, pattern: string) -> Option<i32> {
    return s.find(pattern);
}

// ===== A. 基本検索（見つかる） =====
fn main() -> i32 {
    let s1: string = "hello world";

    let r1 = s1.find("world");
    match r1 {
        Some(i) => println("A1: {}", i),   // A1: 6
        None    => println("A1: none"),
    };

    let r2 = s1.find("ell");
    match r2 {
        Some(i) => println("A2: {}", i),   // A2: 1
        None    => println("A2: none"),
    };

    // ===== B. 見つからない =====
    let r3 = s1.find("xyz");
    match r3 {
        Some(i) => println("B1: {}", i),
        None    => println("B1: none"),     // B1: none
    };

    // ===== C. 空文字列パターン -> Some(0) =====
    let r4 = "hello".find("");
    match r4 {
        Some(i) => println("C1: {}", i),   // C1: 0
        None    => println("C1: none"),
    };

    // ===== D. 先頭マッチ =====
    let r5 = "abcdef".find("abc");
    match r5 {
        Some(i) => println("D1: {}", i),   // D1: 0
        None    => println("D1: none"),
    };

    // ===== E. 末尾近傍マッチ =====
    let r6 = "abcdef".find("ef");
    match r6 {
        Some(i) => println("E1: {}", i),   // E1: 4
        None    => println("E1: none"),
    };

    // ===== F. 複数出現 -> 最初の位置 =====
    let r7 = "aabaa".find("b");
    match r7 {
        Some(i) => println("F1: {}", i),   // F1: 2
        None    => println("F1: none"),
    };

    let r8 = "abcabc".find("bc");
    match r8 {
        Some(i) => println("F2: {}", i),   // F2: 1
        None    => println("F2: none"),
    };

    // ===== G. 関数戻り値 =====
    let idx1 = find_sub("hello world", "world");
    match idx1 {
        Some(i) => println("G1: {}", i),   // G1: 6
        None    => println("G1: none"),
    };

    let idx2 = find_sub("hello world", "zzz");
    match idx2 {
        Some(i) => println("G2: {}", i),
        None    => println("G2: none"),     // G2: none
    };

    // ===== H. match で分岐して計算 =====
    let base: string = "prefix_value";
    let pos = base.find("_");
    let offset: i32 = match pos {
        Some(i) => i + 1,
        None    => 0,
    };
    println("H1: {}", offset);             // H1: 7

    return 0;
}
