// ============================================================
// Test 12: 型宣言 / 型推論 / 型チェック / 型昇格
//   A. 型付き宣言 (i8〜i64, f32/f64, string, bool)
//   B. 型推論 (let 推論)
//   C. 関数戻り値型 (i32/string/bool) - C1
//   D. ジェネリック型推論 [Bug#4/11 で一部 SKIP]
//   E. 型昇格 (i8+i32, f32+f64, i16+i64) + MC/DC
//
// カバレッジ観点:
//   C0  : 全型宣言全型推論全型昇格ケースを1回以上実行
//   C1  :
//     C: typed_flag() の return x>0  true(x=5) / false(x=-1) 両ブランチ
//   MC/DC:
//     E: in_range(x, lo, hi) 内 (x >= lo && x <= hi):
//       {x>=lo=F, *}         false (x<lo: x=-1, lo=0: x>=lo=F 単独決定)
//       {x>=lo=T, x<=hi=F}   false (x=11, hi=10: x<=hi=F 単独決定)
//       {x>=lo=T, x<=hi=T}   true  (x=5: 両方 T)
//
// 既知バグ:
//   Bug#4:  ジェネリック戻り値 f64/string で printf が %d になる
//   Bug#7:  struct の string フィールドが C で %d になる
//   Bug#8:  struct の f64 フィールドが C で %d になる
//   Bug#11: bool 出力が Python=True/False, C=1/0 で不一致
//   Bug#13: f64 format 出力が Python=3.14 / C=3.140000 で不一致
// ============================================================

fn typed_add(a: i32, b: i32) -> i32 {
    return a + b;
}

fn typed_flag(x: i32) -> i32 {
    if (x > 0) {
        return 1;
    }
    return 0;
}

fn identity<T>(value: T) -> T {
    return value;
}

fn add_generic<T>(a: T, b: T) -> T {
    return a + b;
}

// MC/DC 用: (x >= lo && x <= hi)
fn in_range(x: i32, lo: i32, hi: i32) -> i32 {
    if (x >= lo && x <= hi) {
        return 1;
    }
    return 0;
}

fn main() -> i32 {
    println("=== 12: Type Check ===");

    // ----------------------------------------------------------
    // A. 型付き宣言 / C0
    // ----------------------------------------------------------
    println("--- A: Typed declaration ---");
    let a: i32 = 42;
    let b: i8  = 127(i8);
    let c: u8  = 255(u8);
    let d: i16 = 32767(i16);
    let e: i64 = 9999999999(i64);
    println("i32={}", a);    // 42
    println("i8={}", b);     // 127
    println("u8={}", c);     // 255
    println("i16={}", d);    // 32767
    println("i64={}", e);    // 9999999999

    // bool 宣言
    let bv: bool = true;
    println("bool={}", bv);   // true

    // f64 宣言
    let fv: f64 = 3.14;
    println("f64={}", fv);    // 3.14

    println("--- A: bool/f64 decl ---");

    // ----------------------------------------------------------
    // B. 型推論 / C0
    // ----------------------------------------------------------
    println("--- B: Type inference ---");
    let xi = 100;
    let xs = "world";
    let xa = [1, 2, 3];
    println("i32={}", xi);       // 100
    println("str={}", xs);       // world
    println("arr[1]={}", xa[1]); // 2

    // bool 型推論
    let xb = false;
    println("bool={}", xb);   // false

    // f64 型推論
    let xf = 2.718;
    println("f64={}", xf);    // 2.718

    // ----------------------------------------------------------
    // C. 関数戻り値型 / C1: typed_flag の true/false
    // ----------------------------------------------------------
    println("--- C: Return type C1 ---");
    let r1: i32 = typed_add(10, 20);
    println("add={}", r1);        // 30

    // C1: x>0=true
    let r3: i32 = typed_flag(5);
    println("flag(5)={}", r3);    // 1

    // C1: x>0=false
    let r4: i32 = typed_flag(-1);
    println("flag(-1)={}", r4);   // 0

    // C1: x=0 (境界: x>0=false)
    let r5: i32 = typed_flag(0);
    println("flag(0)={}", r5);    // 0

    // ----------------------------------------------------------
    // D. ジェネリック型推論 / C0
    // ----------------------------------------------------------
    println("--- D: Generic type ---");

    // i32 は安全
    let gi: i32 = identity(999);
    println("id<i32>={}", gi);    // 999

    let ga: i32 = add_generic(3, 4);
    println("add<i32>={}", ga);   // 7

    // [Bug#4 SKIP] identity(f64)/identity(string): printf が %d になる
    // let gf: f64 = identity(1.5);
    // println("id<f64>={}", gf);
    // let gs: string = identity("type");
    // println("id<string>={}", gs);
    println("id<f64/string>: (SKIP Bug#4)");

    // [Bug#4 SKIP] add_generic(f64)
    // let gaf: f64 = add_generic(1.5, 2.5);
    // println("add<f64>={}", gaf);
    println("add<f64>: (SKIP Bug#4)");

    // [Bug#11 SKIP] identity(bool)
    // let gb: bool = identity(true);
    // println("id<bool>={}", gb);
    println("id<bool>: (SKIP Bug#11)");

    // ----------------------------------------------------------
    // E. 型昇格 / C0 + MC/DC
    // ----------------------------------------------------------
    println("--- E: Type promotion ---");

    let i8v: i8  = 10(i8);
    let i32v: i32 = 100;
    let p1 = i8v + i32v;
    println("i8+i32={}", p1);    // 110

    let i16v: i16 = 50(i16);
    let i64v: i64 = 1000(i64);
    let p3 = i16v + i64v;
    println("i16+i64={}", p3);   // 1050

    // f32+f64 型昇格
    let f32v: f32 = 1.5(f32);
    let f64v: f64 = 2.5;
    let p2 = f32v + f64v;
    println("f32+f64={}", p2);   // 4

    // MC/DC: in_range(x, 0, 10) 内 (x >= 0 && x <= 10)
    println("--- E: MC/DC in_range ---");

    // {x>=lo=F, *}  0 (x=-1 < lo=0: x>=lo=F 単独決定)
    println("in_range(-1,0,10)={}", in_range(-1, 0, 10));  // 0

    // {x>=lo=T, x<=hi=F}  0 (x=11 > hi=10: x<=hi=F 単独決定)
    println("in_range(11,0,10)={}", in_range(11, 0, 10));  // 0

    // {x>=lo=T, x<=hi=T}  1 (x=5: 両方 T)
    println("in_range(5,0,10)={}", in_range(5, 0, 10));    // 1

    // 境界値確認
    println("in_range(0,0,10)={}", in_range(0, 0, 10));    // 1
    println("in_range(10,0,10)={}", in_range(10, 0, 10));  // 1

    println("=== OK ===");
    return 0;
}
