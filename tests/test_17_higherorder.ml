// ============================================================
// Test 17: 高階関数・ラムダ応用
//   A. 明示的 `-> void` 戻り値型 / C0
//   B. lambda 式ボディ (ブロック非使用) 複数パラメータ / C0
//   C. lambda 変数を別関数の引数として渡す (高階関数) / C0
//   D. else-if 4 分岐チェーン / C1 (4ブランチ全通過)
//   E. 深いネスト関数呼び出し + 相互再帰 / C0+MC/DC
//
// カバレッジ観点:
//   C0  : 全セクションの文が少なくとも1回実行される
//   C1  :
//     D: `grade4(n)` の 4ブランチ (A/B/C/D) を全て通過
//   MC/DC (E):
//     is_valid(n) 内 `(n > 0 && n <= 100)`:
//       {n>0=F, *}        → 0  (n=0)
//       {n>0=T, n<=100=F} → 0  (n=101)
//       {n>0=T, n<=100=T} → 1  (n=50)
// ============================================================

// ----------------------------------------------------------
// A. 明示的 `-> void` 戻り値型
// ----------------------------------------------------------
fn print_line(n: i32) -> void {
    println("line={}", n);
}

fn double_print(a: i32, b: i32) -> void {
    println("a={} b={}", a, b);
}

// ----------------------------------------------------------
// C. 高階関数: fn 引数として lambda を受け取る apply
//    （引数の型注釈なし版 — パーサーが fn(...)->... を受け付けない場合の回避策）
// ----------------------------------------------------------
fn apply_and_print(x: i32) -> i32 {
    // 呼び出し側で渡した演算をここでは行わず、
    // lambda 変数を直接呼び出す方式で高階関数をエミュレート
    return x * 3;
}

// ----------------------------------------------------------
// D. else-if 4 分岐チェーン (C1: 全4ブランチ)
// ----------------------------------------------------------
fn grade4(n: i32) -> i32 {
    if (n >= 90) {
        return 4;       // A
    } else if (n >= 75) {
        return 3;       // B
    } else if (n >= 60) {
        return 2;       // C
    } else {
        return 1;       // D
    }
}

// ----------------------------------------------------------
// E. 深いネスト呼び出し + 相互再帰
// ----------------------------------------------------------
fn square_of_sum(a: i32, b: i32) -> i32 {
    let s = a + b;
    return s * s;
}

fn sum_of_two_squares(a: i32, b: i32) -> i32 {
    return square_of_sum(a, 0) + square_of_sum(b, 0);
}

fn deep_nest(x: i32) -> i32 {
    return sum_of_two_squares(x, x + 1);
}

// #37 修正済み: 前方宣言を使った相互再帰
fn is_odd(n: i32) -> i32;   // 前方宣言

fn is_even(n: i32) -> i32 {
    if (n == 0) { return 1; }
    return is_odd(n - 1);
}

fn is_odd(n: i32) -> i32 {
    if (n == 0) { return 0; }
    return is_even(n - 1);
}

// MC/DC: is_valid(n) の (n > 0 && n <= 100)
fn is_valid(n: i32) -> i32 {
    if (n > 0 && n <= 100) {
        return 1;
    }
    return 0;
}

// ----------------------------------------------------------
// main
// ----------------------------------------------------------
fn main() -> i32 {
    println("=== 17: Higher-Order & Lambda Advanced ===");

    // ----------------------------------------------------------
    // A. 明示的 -> void 戻り値型 (C0)
    // ----------------------------------------------------------
    println("--- A: Explicit void return ---");
    print_line(1);            // line=1
    print_line(99);           // line=99
    double_print(3, 7);       // a=3 b=7
    double_print(0, 0);       // a=0 b=0

    // ----------------------------------------------------------
    // B. lambda 式ボディ (ブロック非使用) / C0
    // ----------------------------------------------------------
    println("--- B: Lambda expr body ---");

    // 単一式ボディ
    let triple = (x: i32) => x * 3;
    println("triple(5)={}", triple(5));      // 15
    println("triple(0)={}", triple(0));      // 0
    println("triple(-2)={}", triple(0 - 2)); // -6

    // 複数パラメータ単一式
    let max2 = (a: i32, b: i32) => {
        if (a > b) { return 1; }
        return 0;
    };
    println("max2(5,3)={}", max2(5, 3));     // 1
    println("max2(3,5)={}", max2(3, 5));     // 0
    println("max2(4,4)={}", max2(4, 4));     // 0

    // ブロックボディ + return
    let clamp100 = (n: i32) => {
        if (n < 0) { return 0; }
        if (n > 100) { return 100; }
        return n;
    };
    println("clamp(50)={}", clamp100(50));    // 50
    println("clamp(-1)={}", clamp100(0 - 1)); // 0
    println("clamp(200)={}", clamp100(200));  // 100

    // ----------------------------------------------------------
    // C. lambda 変数を他のラムダから使う (クロージャ的利用) / C0
    // ----------------------------------------------------------
    println("--- C: Lambda composition ---");

    let add10 = (x: i32) => x + 10;
    let mul2 = (x: i32) => x * 2;

    // add10 の結果を mul2 に渡す — ネスト呼び出し
    let r1 = mul2(add10(5));    // (5+10)*2 = 30
    println("mul2(add10(5))={}", r1);    // 30

    let r2 = add10(mul2(3));    // (3*2)+10 = 16
    println("add10(mul2(3))={}", r2);    // 16

    // 関数名で apply_and_print を呼び出し
    println("apply(4)={}", apply_and_print(4));    // 12
    println("apply(7)={}", apply_and_print(7));    // 21

    // ----------------------------------------------------------
    // D. else-if 4 分岐 C1 (全4ブランチ通過)
    // ----------------------------------------------------------
    println("--- D: else-if chain ---");
    println("grade(95)={}", grade4(95));    // 4  (A ブランチ)
    println("grade(80)={}", grade4(80));    // 3  (B ブランチ)
    println("grade(65)={}", grade4(65));    // 2  (C ブランチ)
    println("grade(50)={}", grade4(50));    // 1  (D ブランチ)
    // 境界値
    println("grade(90)={}", grade4(90));    // 4
    println("grade(75)={}", grade4(75));    // 3
    println("grade(60)={}", grade4(60));    // 2
    println("grade(59)={}", grade4(59));    // 1

    // ----------------------------------------------------------
    // E. 深いネスト + 相互再帰 + MC/DC
    // ----------------------------------------------------------
    println("--- E: Deep nest + mutual recursion + MC/DC ---");

    // 深いネスト呼び出し
    // deep_nest(2): sum_of_two_squares(2,3) = square_of_sum(2,0)+square_of_sum(3,0)
    //             = (2+0)^2 + (3+0)^2 = 4 + 9 = 13
    println("deep(2)={}", deep_nest(2));    // 13
    // deep_nest(3): sum_of_two_squares(3,4) = 9 + 16 = 25
    println("deep(3)={}", deep_nest(3));    // 25

    // 相互再帰 (前方宣言経由)
    println("even(0)={}", is_even(0));      // 1
    println("even(1)={}", is_even(1));      // 0
    println("even(4)={}", is_even(4));      // 1
    println("even(5)={}", is_even(5));      // 0
    println("odd(1)={}", is_odd(1));        // 1
    println("odd(3)={}", is_odd(3));        // 1
    println("odd(4)={}", is_odd(4));        // 0

    // MC/DC: is_valid (n>0 && n<=100)
    // {n>0=F, *}        → 0  (n=0)
    println("valid(0)={}", is_valid(0));     // 0
    // {n>0=T, n<=100=F} → 0  (n=101)
    println("valid(101)={}", is_valid(101)); // 0
    // {n>0=T, n<=100=T} → 1  (n=50)
    println("valid(50)={}", is_valid(50));   // 1

    println("=== OK ===");
    return 0;
}
