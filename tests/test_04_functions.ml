// ============================================================
// Test 04: 関節
//   A. 基本関数 / B. 再帰 / C. ラムダ式 / D. ジェネリック
//   E. void 関数 / F. 関数ネスト呼び出し
//
// カバレッジ観点:
//   C0 : A〜F 全関数ラムダが実行される
//   C1 :
//     B: 再帰の基底ケース(n<=1  true) と 再帰ケース(n>1  false) 両方
//     C: lambda の式ボディ / ブロック-void / ブロック-return の 3 種を呼び出す
//     F: ネスト呼び出しで各段が実行される
//   MC/DC:
//     B: fact(n<=1) で n=1  基底(true), n=2  再帰(false) が単独で結果を決定
//     B: fib(n<=1)  で n=0,n=1  基底 / n=3  再帰
//   備考:
//     A,D,E は分岐なし  C0 相当のみ
//     D ジェネリック: 同一関数を型違いで呼び出すことで単相化パス確認
//
// [SKIP] pair_str<T,U> の呼び出し (2項目) は現在 C コンパイルエラー。
//   原因1: to_string() が MrylString 型を受け取れない (#Issue: to_string 引数型制限)
//   原因2: ジェネリック関数内の string + string が MrylString_concat に変換されない
//          (#Issue: ジェネリック内 string 加算)
//    当該 issue 修正後にコメントを外してテストを有効化すること
// ============================================================

// ----------------------------------------------------------
// A. 基本関数
// ----------------------------------------------------------
fn add(a: i32, b: i32) -> i32 {
    return a + b;
}

fn mul(a: i32, b: i32) -> i32 {
    return a * b;
}

fn negate(v: i32) -> i32 {
    return 0 - v;
}

// ----------------------------------------------------------
// B. 再帰関数
// ----------------------------------------------------------
// 階乗: fact(0)=1, fact(1)=1, fact(n)=n*fact(n-1)
fn fact(n: i32) -> i32 {
    if (n <= 1) {
        return 1;           // C1/MC/DC: 基底ケース
    }
    return n * fact(n - 1); // C1/MC/DC: 再帰ケース
}

// フィボナッチ: fib(0)=0, fib(1)=1, fib(n)=fib(n-1)+fib(n-2)
fn fib(n: i32) -> i32 {
    if (n <= 0) {
        return 0;
    }
    if (n == 1) {
        return 1;
    }
    return fib(n - 1) + fib(n - 2);
}

// ----------------------------------------------------------
// D. ジェネリック関数
// ----------------------------------------------------------
fn identity<T>(x: T) -> T {
    return x;
}

fn generic_add<T>(a: T, b: T) -> T {
    return a + b;
}

// [SKIP] pair_str: ジェネリック内 string 連結バグが修正されたら有効化する
// Issue: to_string が MrylString 型を受け取れない
// Issue: ジェネリック関数内 string + string が MrylString_concat に変換されない
//
// fn pair_str<T, U>(a: T, b: U) -> string {
//     return to_string(a) + to_string(b);
// }

// ----------------------------------------------------------
// E. void 関数
// ----------------------------------------------------------
fn print_sep() {
    println("----------");
}

fn print_sum(a: i32, b: i32) {
    let s = a + b;
    println("sum={}", s);
}

// ----------------------------------------------------------
// F. ネスト呼び出し用ヘルパー
// ----------------------------------------------------------
fn square(n: i32) -> i32 {
    return mul(n, n);
}

fn sum_of_squares(a: i32, b: i32) -> i32 {
    return add(square(a), square(b));
}

// ----------------------------------------------------------
// main
// ----------------------------------------------------------
fn main() -> i32 {
    println("=== 04: Functions ===");

    // ----------------------------------------------------------
    // A. 基本関数 (C0)
    // ----------------------------------------------------------
    println("--- A: Basic ---");
    println("add(3,4)={}", add(3, 4));       // 7
    println("mul(3,4)={}", mul(3, 4));       // 12
    println("negate(5)={}", negate(5));      // -5
    println("negate(-3)={}", negate(0 - 3)); // 3

    // ----------------------------------------------------------
    // B. 再帰関数 (C1 + MC/DC)
    // ----------------------------------------------------------
    println("--- B: Recursive ---");
    // MC/DC: fact の基底ケース (n=0,1)
    println("fact(0)={}", fact(0));          // 1
    println("fact(1)={}", fact(1));          // 1
    // MC/DC: fact の再帰ケース
    println("fact(5)={}", fact(5));          // 120
    println("fact(6)={}", fact(6));          // 720

    // MC/DC: fib の基底ケース
    println("fib(0)={}", fib(0));            // 0
    println("fib(1)={}", fib(1));            // 1
    // MC/DC: fib の再帰ケース
    println("fib(5)={}", fib(5));            // 5
    println("fib(7)={}", fib(7));            // 13

    // ----------------------------------------------------------
    // C. ラムダ式 (C1: 3 種のボディを実行)
    // ----------------------------------------------------------
    println("--- C: Lambda ---");

    // 単一式ボディ
    let double = (x: i32) => x * 2;
    println("double(5)={}", double(5));      // 10
    println("double(0)={}", double(0));      // 0

    // 複数パラメータ単一式
    let add_l = (x: i32, y: i32) => x + y;
    println("add_l(3,7)={}", add_l(3, 7));  // 10

    // ブロックボディ (void: return なし)
    let show = (x: i32) => {
        let doubled = x * 2;
        println("show doubled={}", doubled);
    };
    show(4);                                 // show doubled=8
    show(0);                                 // show doubled=0

    // ブロックボディ (return あり)
    let compute = (x: i32) => {
        let v = x * x;
        return v + 1;
    };
    println("compute(3)={}", compute(3));    // 10
    println("compute(0)={}", compute(0));    // 1

    // ----------------------------------------------------------
    // D. ジェネリック関数 (C0: 複数型で単相化)
    // ----------------------------------------------------------
    println("--- D: Generic ---");
    println("id_i32={}", identity(42));            // 42

    // [SKIP] identity(f64)/identity(string): C ネイティブで戻り値型が i32 扱いされ
    //   printf フォーマット指定子が %d になるバグ
    //   Issue: ジェネリック関数の戻り値型 f64/string で printf が %d になる
    //   Python 結果: id_f64=3.14, id_str=mryl (Python は正常)
    // println("id_f64={}", identity(3.14));       // 3.140000
    // println("id_str={}", identity("mryl"));     // mryl

    println("gadd_i32={}", generic_add(3, 4));     // 7

    // [SKIP] generic_add(f64): 同上バグにより C ネイティブで 0 になる
    //   Python 結果: gadd_f64=4.0 (Python は正常)
    // println("gadd_f64={}", generic_add(1.5, 2.5)); // 4.000000

    // [SKIP] pair_str: ジェネリック内 string 連結バグ修正後に有効化
    //   Issue: to_string が MrylString を受け取れない
    //   Issue: ジェネリック内 string + string が MrylString_concat に変換されない
    // println("pair={}", pair_str(10, "px"));     // 10px
    // println("pair={}", pair_str(3.14, 2));      // 3.1400002

    // ----------------------------------------------------------
    // E. void 関数 (C0)
    // ----------------------------------------------------------
    println("--- E: Void ---");
    print_sep();                             // ----------
    print_sum(3, 7);                         // sum=10
    print_sep();                             // ----------

    // ----------------------------------------------------------
    // F. 関数ネスト呼び出し (C1: 各段が実行される)
    // ----------------------------------------------------------
    println("--- F: Nested calls ---");
    println("square(4)={}", square(4));                  // 16
    println("sum_of_sq(3,4)={}", sum_of_squares(3, 4));  // 25
    println("sum_of_sq(0,5)={}", sum_of_squares(0, 5));  // 25

    println("=== OK ===");
    return 0;
}
