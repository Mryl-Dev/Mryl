// ============================================================
// Test 20: fn 型パラメータ（コールバック）
//   A. 基本 sync コールバック: fn(i32)->i32 / fn(i32)->void   [C0]
//   B. 戻り値型バリエーション: f64 / string                   [C0]
//   C. 複数パラメータコールバック: fn(i32,i32)->i32            [C0]
//   D. string パラメータコールバック: fn(string)->i32          [C0]
//   E. コールバック分岐選択 (if/else)                         [C1]
//   F. 複合条件コールバック選択                                [MC/DC]
//   G. イレギュラーパターン                                    [C0]
//
// カバレッジ観点:
//   C0  : 全コールバック経路を最低 1 回実行
//   C1  :
//     E: dispatch(flag) の true/false 両ブランチ
//        → flag=1: double コールバック、flag=0: negate コールバック
//   MC/DC (F):
//     select(a, b, x) 内 (a == 1 && b == 1) で各条件が
//     独立して結果を決定することを確認
//       {a=T, b=F} → result=0 (b=F が単独決定)
//       {a=F, b=T} → result=0 (a=F が単独決定)
//       {a=T, b=T} → result=1 (両方 T で決定)
// ============================================================

// ----------------------------------------------------------
// A. fn(i32)->i32 の apply
// ----------------------------------------------------------
fn apply_i32(callback: fn(i32) -> i32, x: i32) -> i32 {
    return callback(x);
}

// fn(i32)->void の apply
fn apply_void(callback: fn(i32) -> void, x: i32) -> void {
    callback(x);
}

// ----------------------------------------------------------
// B. fn(i32)->f64 の apply
// ----------------------------------------------------------
fn apply_f64(callback: fn(i32) -> f64, x: i32) -> f64 {
    return callback(x);
}

// fn(i32)->string の apply
fn apply_str(callback: fn(i32) -> string, x: i32) -> string {
    return callback(x);
}

// ----------------------------------------------------------
// C. fn(i32, i32)->i32 の apply
// ----------------------------------------------------------
fn apply2(callback: fn(i32, i32) -> i32, a: i32, b: i32) -> i32 {
    return callback(a, b);
}

// ----------------------------------------------------------
// D. fn(string)->i32 の apply
// ----------------------------------------------------------
fn apply_slen(callback: fn(string) -> i32, s: string) -> i32 {
    return callback(s);
}

// ----------------------------------------------------------
// E. コールバック分岐選択 [C1]
//    flag=1 → f1, flag=0 → f2
// ----------------------------------------------------------
fn dispatch(f1: fn(i32) -> i32, f2: fn(i32) -> i32, flag: i32, x: i32) -> i32 {
    if (flag == 1) {
        return f1(x);
    } else {
        return f2(x);
    }
}

// ----------------------------------------------------------
// F. 複合条件 MC/DC [MC/DC]
//    (a == 1 && b == 1) → f1, else → f2
// ----------------------------------------------------------
fn my_select(f1: fn(i32) -> i32, f2: fn(i32) -> i32, a: i32, b: i32, x: i32) -> i32 {
    if (a == 1 && b == 1) {
        return f1(x);
    }
    return f2(x);
}

// ----------------------------------------------------------
// G. イレギュラー: 名前付き関数をそのまま渡す
// ----------------------------------------------------------
fn double_i32(n: i32) -> i32 {
    return n * 2;
}

fn negate(n: i32) -> i32 {
    return 0 - n;
}

fn identity(n: i32) -> i32 {
    return n;
}

fn constant42(n: i32) -> i32 {
    return 42;
}

// ----------------------------------------------------------
// main
// ----------------------------------------------------------
fn main() -> i32 {
    println("=== 20: Callbacks ===");

    // ----------------------------------------------------------
    // A. 基本 fn(i32)->i32 / fn(i32)->void [C0]
    // ----------------------------------------------------------
    println("--- A: Basic sync callback ---");

    let double = (x: i32) => { return x * 2; };
    let triple = (x: i32) => { return x * 3; };
    println("double(5)={}", apply_i32(double, 5));      // 10
    println("triple(4)={}", apply_i32(triple, 4));      // 12
    println("double(0)={}", apply_i32(double, 0));      // 0
    println("double(-3)={}", apply_i32(double, -3));    // -6

    let print_cb = (x: i32) => { println("cb={}", x); };
    apply_void(print_cb, 7);    // cb=7
    apply_void(print_cb, 0);    // cb=0

    // ----------------------------------------------------------
    // B. 戻り値型バリエーション: f64 / string [C0]
    // ----------------------------------------------------------
    println("--- B: Return type variants ---");

    let to_half = (x: i32) => { return x / 2.0; };
    println("half(10)={}", apply_f64(to_half, 10));     // 5
    println("half(3)={}", apply_f64(to_half, 3));       // 1.5

    let to_label = (x: i32) => {
        if (x > 0) { return "pos"; }
        return "non-pos";
    };
    println("label(1)={}", apply_str(to_label, 1));     // pos
    println("label(0)={}", apply_str(to_label, 0));     // non-pos
    println("label(-1)={}", apply_str(to_label, -1));   // non-pos

    // ----------------------------------------------------------
    // C. 複数パラメータ fn(i32,i32)->i32 [C0]
    // ----------------------------------------------------------
    println("--- C: Multi-param callback ---");

    let add = (a: i32, b: i32) => { return a + b; };
    let mul = (a: i32, b: i32) => { return a * b; };
    let max_of = (a: i32, b: i32) => {
        if (a > b) { return a; }
        return b;
    };

    println("add(3,4)={}", apply2(add, 3, 4));          // 7
    println("mul(3,4)={}", apply2(mul, 3, 4));          // 12
    println("max(3,4)={}", apply2(max_of, 3, 4));       // 4
    println("max(9,2)={}", apply2(max_of, 9, 2));       // 9
    println("add(0,0)={}", apply2(add, 0, 0));          // 0

    // ----------------------------------------------------------
    // D. string パラメータコールバック [C0]
    // ----------------------------------------------------------
    println("--- D: String param callback ---");

    // string パラメータは渡せることを確認する（文字列比較は別 issue のため固定値を返す）
    let str_len_cb = (s: string) => { return 7; };
    println("len(hi)={}", apply_slen(str_len_cb, "hi"));        // 7
    println("len(hello)={}", apply_slen(str_len_cb, "hello"));  // 7
    println("len(x)={}", apply_slen(str_len_cb, "x"));          // 7

    // ----------------------------------------------------------
    // E. コールバック分岐選択 [C1: flag=1/0 両ブランチ]
    // ----------------------------------------------------------
    println("--- E: Dispatch [C1] ---");

    let neg = (x: i32) => { return 0 - x; };
    // flag=1 → double (C1: true ブランチ)
    println("dispatch(1,5)={}", dispatch(double, neg, 1, 5));   // 10
    println("dispatch(1,3)={}", dispatch(double, neg, 1, 3));   // 6
    // flag=0 → negate (C1: false ブランチ)
    println("dispatch(0,5)={}", dispatch(double, neg, 0, 5));   // -5
    println("dispatch(0,3)={}", dispatch(double, neg, 0, 3));   // -3

    // ----------------------------------------------------------
    // F. select: MC/DC (a==1 && b==1)
    // ----------------------------------------------------------
    println("--- F: Select [MC/DC] ---");

    let sq = (x: i32) => { return x * x; };

    // {a=T, b=F}: b=F が単独決定 → f2(double)
    println("select(1,0,4)={}", my_select(sq, double, 1, 0, 4));   // 8   (double)
    // {a=F, b=T}: a=F が単独決定 → f2(double)
    println("select(0,1,4)={}", my_select(sq, double, 0, 1, 4));   // 8   (double)
    // {a=T, b=T}: 両方 T → f1(sq)
    println("select(1,1,4)={}", my_select(sq, double, 1, 1, 4));   // 16  (square)
    // {a=F, b=F}: → f2(double)
    println("select(0,0,4)={}", my_select(sq, double, 0, 0, 4));   // 8   (double)

    // ----------------------------------------------------------
    // G. イレギュラーパターン [C0]
    // ----------------------------------------------------------
    println("--- G: Irregular patterns ---");

    // 名前付き関数をコールバックとして渡す
    println("named/double(7)={}", apply_i32(double_i32, 7));    // 14
    println("named/negate(5)={}", apply_i32(negate, 5));        // -5
    println("named/identity(9)={}", apply_i32(identity, 9));    // 9
    // 引数を無視して定数を返すコールバック
    println("const42(0)={}", apply_i32(constant42, 0));         // 42
    println("const42(999)={}", apply_i32(constant42, 999));     // 42
    // コールバック結果をさらにコールバックへ
    let v1 = apply_i32(double, 3);   // 6
    println("chained={}", apply_i32(sq, v1));                   // 36
    // 負の入力
    println("double(-10)={}", apply_i32(double, -10));          // -20
    println("triple(-4)={}", apply_i32(triple, -4));            // -12
    // ゼロを返すコールバック
    let zero_cb = (x: i32) => { return 0; };
    println("zero(99)={}", apply_i32(zero_cb, 99));             // 0

    println("=== OK ===");
    return 0;
}
