// ============================================================
// Test 27: match 式 _ ワイルドカードパターン
//   A. i32 scrutinee - _ がキャッチオールとして機能する
//   B. string scrutinee - _ がキャッチオールとして機能する
//   C. _ のみのアーム（単一アーム match）
//   D. Result 型 match - _ で残りバリアントをまとめる
//   E. Option 型 match - None を _ でキャッチ
//
// カバレッジ観点:
//   C0  : _ アームが実際に実行されることを確認
//   C1  :
//     A: 具体アーム実行（_ 不実行）/ _ アーム実行 両ブランチ
//     D: Ok アーム実行 / _ アーム実行（Err を _ でキャッチ）
//     E: Some アーム実行 / _ アーム実行（None を _ でキャッチ）
// ============================================================

fn main() -> i32 {
    // ----------------------------------------------------------
    // A. i32 scrutinee - _ キャッチオール
    // ----------------------------------------------------------
    let a1: string = match 1 {
        1 => "one",
        _ => "other",
    };
    println("{}", a1);   // one  (具体アーム)

    let a2: string = match 99 {
        1 => "one",
        2 => "two",
        _ => "other",
    };
    println("{}", a2);   // other  (_ アーム)

    // ----------------------------------------------------------
    // B. string scrutinee - _ キャッチオール
    // ----------------------------------------------------------
    let word: string = "hello";
    let b1: string = match word {
        "hi"    => "greeting",
        "hello" => "formal",
        _       => "unknown",
    };
    println("{}", b1);   // formal

    let b2: string = match "xyz" {
        "hi"    => "greeting",
        "hello" => "formal",
        _       => "unknown",
    };
    println("{}", b2);   // unknown

    // ----------------------------------------------------------
    // C. _ のみの単一アーム match（常にマッチ）
    // ----------------------------------------------------------
    let c1: i32 = match 123 {
        _ => 999,
    };
    println("{}", c1);   // 999

    // ----------------------------------------------------------
    // D. Result 型 match - Err を _ でキャッチ
    // ----------------------------------------------------------
    let r1: Result<i32, string> = Ok(10);
    let d1: string = match r1 {
        Ok(v)  => "ok",
        _      => "catch",
    };
    println("{}", d1);   // ok

    let r2: Result<i32, string> = Err("fail");
    let d2: string = match r2 {
        Ok(v)  => "ok",
        _      => "catch",
    };
    println("{}", d2);   // catch

    // ----------------------------------------------------------
    // E. Option 型 match - None を _ でキャッチ
    // ----------------------------------------------------------
    let o1: Option<i32> = Some(5);
    let e1: string = match o1 {
        Some(v) => "some",
        _       => "none_or_other",
    };
    println("{}", e1);   // some

    let o2: Option<i32> = None;
    let e2: string = match o2 {
        Some(v) => "some",
        _       => "none_or_other",
    };
    println("{}", e2);   // none_or_other

    return 0;
}
