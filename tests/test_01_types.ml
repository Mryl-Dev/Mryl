// ============================================================
// Test 01: Basic Types / Variable Declarations / Type Inference / Type Casting / Type Promotion
// ============================================================

fn main() -> i32 {
    println("=== 01: Basic Types & Variable Declarations ===");

    // --- Typed Declarations ---
    let a: i8  = 127(i8);
    let b: i16 = 1000(i16);
    let c: i32 = 100000;
    let d: i64 = 9999999999(i64);
    println("i8={}", a);
    println("i16={}", b);
    println("i32={}", c);
    println("i64={}", d);

    let ua: u8  = 255(u8);
    let ub: u16 = 65535(u16);
    let uc: u32 = 4000000000(u32);
    println("u8={}", ua);
    println("u16={}", ub);
    println("u32={}", uc);

    let fa: f32 = 3.14(f32);
    let fb: f64 = 2.718281828;
    println("f32={}", fa);
    println("f64={}", fb);

    let s: string = "hello";
    let flag: bool = true;
    println("string={}", s);
    println("bool={}", flag);

    // --- Type Inference ---
    println("=== Type Inference ===");
    let xi = 42;         // inferred as i32
    let xf = 1.5;        // inferred as f64
    let xs = "world";    // inferred as string
    let xb = false;      // inferred as bool
    println("infer i32={}", xi);
    println("infer f64={}", xf);
    println("infer string={}", xs);
    println("infer bool={}", xb);

    // --- Type Casting (suffix notation) ---
    println("=== Type Casting ===");
    let c1 = 5(u8);
    let c2 = 100(i16);
    let c3 = 3.14159(f32);
    let c4 = 1_000_000(u32);
    println("u8={}", c1);
    println("i16={}", c2);
    println("f32={}", c3);
    println("u32={}", c4);

    // underscore separator
    let big = 1_000_000_000(i64);
    println("1_000_000_000={}", big);

    // --- Type Promotion ---
    println("=== Type Promotion ===");
    let p8: i8  = 10(i8);
    let p32: i32 = 20;
    let padd = p8 + p32;    // promoted to i32
    println("i8+i32={}", padd);

    let q16: i16 = 5(i16);
    let q64: i64 = 100(i64);
    let qadd = q16 + q64;   // promoted to i64
    println("i16+i64={}", qadd);

    let rf32: f32 = 1.5(f32);
    let rf64: f64 = 2.5;
    let radd = rf32 + rf64;  // promoted to f64
    println("f32+f64={}", radd);

    println("=== OK ===");
    return 0;
}
