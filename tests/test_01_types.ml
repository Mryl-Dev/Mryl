// ============================================================
// Test 01: 基本型 / 変数宣言 / 型推論 / 型キャスト / 型昇格 / 文字列連結 / bool 分岐
//
// カバレッジ観点:
//   C0  : A〜F 全セクションの文を実行
//   C1  : F セクションで if の真ブランチ偽ブランチ両方を実行
//   MC/DC:
//     (p && q): {p=F,q=T}F, {p=T,q=F}F, {p=T,q=T}T
//       p が F のとき単独で結果を決定 / q が F のとき単独で結果を決定
//     (p || q): {p=T,q=F}T, {p=F,q=T}T, {p=F,q=F}F
//       p が T のとき単独で結果を決定 / q が T のとき単独で結果を決定
//     (!p)    : p=TF, p=FT
//   備考:
//     D(型昇格) は分岐なし  C0 相当のみ
//     E(文字列連結) は分岐なし  C0 相当のみ
// ============================================================
fn main() -> i32 {
    println("=== 01: Types ===");

    // ----------------------------------------------------------
    // A. 型付き局所変数宣言 (C0: 全宣言println が実行される)
    // ----------------------------------------------------------
    println("--- A: Typed ---");
    let a_i8  : i8  = 127(i8);
    let a_i16 : i16 = 32767(i16);
    let a_i32 : i32 = 2147483647;
    let a_i64 : i64 = 9999999999(i64);
    println("i8={}", a_i8);           // 127
    println("i16={}", a_i16);         // 32767
    println("i32={}", a_i32);         // 2147483647
    println("i64={}", a_i64);         // 9999999999

    let a_u8  : u8  = 255(u8);
    let a_u16 : u16 = 65535(u16);
    let a_u32 : u32 = 4000000000(u32);
    println("u8={}", a_u8);           // 255
    println("u16={}", a_u16);         // 65535
    println("u32={}", a_u32);         // 4000000000

    let a_f32 : f32 = 3.14(f32);
    let a_f64 : f64 = 2.718281828;
    println("f32={}", a_f32);         // 3.140000
    println("f64={}", a_f64);         // 2.718282

    let a_str : string = "mryl";
    let a_bool: bool   = true;
    println("string={}", a_str);      // mryl
    println("bool={}", a_bool);       // 1

    // ----------------------------------------------------------
    // B. 型推論 (C0: リテラルから正しい型が推論される)
    // ----------------------------------------------------------
    println("--- B: Inference ---");
    let b_i32  = 42;          // i32 と推論
    let b_f64  = 1.5;         // f64 と推論
    let b_str  = "world";     // string と推論
    let b_bool = false;       // bool と推論
    println("infer i32={}", b_i32);   // 42
    println("infer f64={}", b_f64);   // 1.500000
    println("infer str={}", b_str);   // world
    println("infer bool={}", b_bool); // 0

    // ----------------------------------------------------------
    // C. 型キャスト (サフィックス記法 / C0: 全キャストが実行される)
    // ----------------------------------------------------------
    println("--- C: Casting ---");
    let c_u8  = 200(u8);
    let c_i16 = 500(i16);
    let c_f32 = 3.14159(f32);
    let c_u32 = 1_000_000(u32);
    let c_i64 = 1_000_000_000(i64);
    println("u8={}", c_u8);           // 200
    println("i16={}", c_i16);         // 500
    println("f32={}", c_f32);         // 3.141590
    println("u32={}", c_u32);         // 1000000
    println("i64={}", c_i64);         // 1000000000

    // ----------------------------------------------------------
    // D. 型昇格 (C0: 各昇格パスが実行される / 分岐なしのため C1 以上は対象外)
    // ----------------------------------------------------------
    println("--- D: Promotion ---");
    let d_i8  : i8  = 10(i8);
    let d_i32 : i32 = 20;
    let d_ii  = d_i8 + d_i32;        // i8  i32 昇格 = 30
    println("i8+i32={}", d_ii);       // 30

    let d_i16 : i16 = 5(i16);
    let d_i64 : i64 = 100(i64);
    let d_il  = d_i16 + d_i64;       // i16  i64 昇格 = 105
    println("i16+i64={}", d_il);      // 105

    let d_f32 : f32 = 1.5(f32);
    let d_f64 : f64 = 2.5;
    let d_ff  = d_f32 + d_f64;       // f32  f64 昇格 = 4.0
    println("f32+f64={}", d_ff);      // 4.000000

    let d_i32b: i32 = 3;
    let d_f64b: f64 = 0.14;
    let d_if  = d_i32b + d_f64b;     // i32  f64 昇格 = 3.14
    println("i32+f64={}", d_if);      // 3.140000

    // ----------------------------------------------------------
    // E. 文字列連結 (C0: 各連結が実行される / 分岐なしのため C1 以上は対象外)
    // ----------------------------------------------------------
    println("--- E: String Concat ---");
    let e_s1 = "Hello";
    let e_s2 = ", ";
    let e_s3 = "World";
    let e_r1 = e_s1 + e_s2;
    let e_r2 = e_r1 + e_s3;
    println("{}", e_r2);              // Hello, World

    let e_num = to_string(100);
    let e_r3  = "answer=" + e_num;
    println("{}", e_r3);             // answer=100

    // ----------------------------------------------------------
    // F. bool 値の条件分岐 (C1 + MC/DC)
    // ----------------------------------------------------------
    println("--- F: Bool Conditions ---");

    // C1: 真ブランチ
    let ft = true;
    if (ft) { println("if-true"); } else { println("if-false"); }    // if-true

    // C1: 偽ブランチ
    let ff = false;
    if (ff) { println("if-true"); } else { println("if-false"); }    // if-false

    // MC/DC: &&  p=F が単独で結果を決める
    let p1 = false; let q1 = true;
    if (p1 && q1) { println("and=T"); } else { println("and=F"); }   // and=F

    // MC/DC: &&  q=F が単独で結果を決める
    let p2 = true;  let q2 = false;
    if (p2 && q2) { println("and=T"); } else { println("and=F"); }   // and=F

    // MC/DC: &&  両方 T で結果 T
    let p3 = true;  let q3 = true;
    if (p3 && q3) { println("and=T"); } else { println("and=F"); }   // and=T

    // MC/DC: ||  p=T が単独で結果を決める
    let p4 = true;  let q4 = false;
    if (p4 || q4) { println("or=T"); } else { println("or=F"); }     // or=T

    // MC/DC: ||  q=T が単独で結果を決める
    let p5 = false; let q5 = true;
    if (p5 || q5) { println("or=T"); } else { println("or=F"); }     // or=T

    // MC/DC: ||  両方 F で結果 F
    let p6 = false; let q6 = false;
    if (p6 || q6) { println("or=T"); } else { println("or=F"); }     // or=F

    // MC/DC: NOT  !true  0
    println("!true={}", !true);       // 0

    // MC/DC: NOT  !false  1
    println("!false={}", !false);     // 1

    println("=== OK ===");
    return 0;
}
