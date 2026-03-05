// ============================================================
// Test 11: 組み込み関数 (print / println / to_string)
//   A. print (改行なし)
//   B. println (型ごと: i32 / f64 / string / bool)
//   C. println フォーマット文字列 (1引数 / 複数引数)
//   D. to_string (i32 / f64 / bool)
//   E. to_string 結果を使った条件分岐 - C1 + MC/DC
//
// カバレッジ観点:
//   C0  : print/println/to_string を全型全引数パターンで1回以上呼び出し
//   C1  :
//     B: println に i32/f64/string/bool を渡す全ケース
//     D: to_string に i32/f64/bool を渡す全ケース
//   MC/DC:
//     E: describe(n) 内 (n > 0 && n < 100):
//       {n>0=F, *}           "other" (n>0=F が単独決定: n=0)
//       {n>0=T, n<100=F}     "other" (n<100=F が単独決定: n=100)
//       {n>0=T, n<100=T}     "small" (両方 T: n=50)
// ============================================================

// E. MC/DC 用ヘルパー
fn describe(n: i32) -> void {
    if (n > 0 && n < 100) {
        println("small");
    } else {
        println("other");
    }
}

fn main() -> i32 {
    println("=== 11: Built-in Functions ===");

    // ----------------------------------------------------------
    // A. print (改行なし) / C0
    // ----------------------------------------------------------
    println("--- A: print ---");
    print("no");
    print("-");
    print("newline");
    print("\n");                         // no-newline

    // ----------------------------------------------------------
    // B. println 型ごと / C1
    // ----------------------------------------------------------
    println("--- B: println types ---");
    println("hello world");              // hello world
    println(42);                         // 42

    println(3.14);                        // 3.14

    println(true);                        // true
    println(false);                       // false

    // ----------------------------------------------------------
    // C. println フォーマット文字列 / C1: 引数数ごと
    // ----------------------------------------------------------
    println("--- C: println format ---");
    let i = 10;
    println("i={}", i);                  // i=10

    let f = 3.14;
    println("f={}", f);                   // f=3.14

    let s = "Mryl";
    println("lang={}", s);               // lang=Mryl

    let b = true;
    println("flag={}", b);               // flag=true

    // 複数引数
    let x = 5;
    let y = 20;
    println("x={}, y={}", x, y);         // x=5, y=20

    let name = "Mryl";
    let ver = 1;
    println("lang={}, ver={}", name, ver); // lang=Mryl, ver=1

    let aa = 1;
    let bb = 2;
    let cc = 3;
    println("{} {} {}", aa, bb, cc);     // 1 2 3

    // ----------------------------------------------------------
    // D. to_string / C1: 型ごと
    // ----------------------------------------------------------
    println("--- D: to_string ---");
    let n = 42;
    let sn = to_string(n);
    println("to_string(42)={}", sn);     // 42

    let neg = -7;
    let sneg = to_string(neg);
    println("to_string(-7)={}", sneg);   // -7

    // to_string(f64)
    let fv = 3.14;
    let sf = to_string(fv);
    println("to_string(3.14)={}", sf);   // 3.14

    let flag = true;
    let sb = to_string(flag);
    println("to_string(true)={}", sb);   // to_string(true)=true

    let val = 100;
    let msg = to_string(val);
    println("Value is {}", msg);         // Value is 100

    // ----------------------------------------------------------
    // E. to_string + 条件分岐 / C1 + MC/DC
    // MC/DC: describe(n) 内 (n > 0 && n < 100)
    // ----------------------------------------------------------
    println("--- E: MC/DC describe ---");

    // {n>0=F, *}  other (n=0: n>0=F が単独決定)
    describe(0);     // other

    // {n>0=T, n<100=F}  other (n=100: n<100=F が単独決定)
    describe(100);   // other

    // {n>0=T, n<100=T}  small (n=50: 両方 T)
    describe(50);    // small

    println("=== OK ===");
    return 0;
}
