// ============================================================
// Test 12: Type Inference / Type Checking (happy path)
// ============================================================

// --- Typed Functions (return type check) ---
fn typed_add(a: i32, b: i32) -> i32 {
    return a + b;
}

fn typed_greet(name: string) -> string {
    return name;
}

fn typed_flag(x: i32) -> bool {
    return x > 0;
}

// --- Generic Type Inference ---
fn identity<T>(value: T) -> T {
    return value;
}

fn add_generic<T>(a: T, b: T) -> T {
    return a + b;
}

// --- Struct Field Type Check ---
struct Typed {
    n: i32;
    s: string;
    b: bool;
    f: f64;
}

fn main() -> i32 {
    println("=== 12: Type Inference / Type Check ===");

    // --- Typed Declarations ---
    println("--- typed declaration ---");
    let a: i32 = 42;
    let b: f64 = 3.14;
    let c: string = "hello";
    let d: bool = true;
    let e: i8 = 127(i8);
    let f: u8 = 255(u8);
    let g: i64 = 9999999999(i64);
    println("i32={}", a);
    println("f64={}", b);
    println("string={}", c);
    println("bool={}", d);
    println("i8={}", e);
    println("u8={}", f);
    println("i64={}", g);

    // --- Type Inference ---
    println("--- type inference ---");
    let xi = 100;               // i32
    let xf = 2.718;             // f64
    let xs = "world";           // string
    let xb = false;             // bool
    let xa = [1, 2, 3];         // i32[3]
    println("i32={}", xi);
    println("f64={}", xf);
    println("string={}", xs);
    println("bool={}", xb);
    println("arr[0]={}", xa[0]);

    // --- Function Return Type ---
    println("--- return type ---");
    let r1: i32 = typed_add(10, 20);
    println("add={}", r1);              // 30

    let r2: string = typed_greet("Mryl");
    println("greet={}", r2);            // Mryl

    let r3: bool = typed_flag(5);
    println("flag(5)={}", r3);          // True

    let r4: bool = typed_flag(-1);
    println("flag(-1)={}", r4);         // False

    // --- Generic Type Inference ---
    println("--- generic inference ---");
    let gi: i32 = identity(999);
    let gs: string = identity("type");
    let gf: f64 = identity(1.5);
    let gb: bool = identity(true);
    println("id<i32>={}", gi);
    println("id<string>={}", gs);
    println("id<f64>={}", gf);
    println("id<bool>={}", gb);

    let ga: i32 = add_generic(3, 4);
    let gaf: f64 = add_generic(1.5, 2.5);
    println("add<i32>={}", ga);         // 7
    println("add<f64>={}", gaf);        // 4.0

    // --- Struct Field Types ---
    println("--- struct field type ---");
    let t = Typed { n: 99, s: "ok", b: true, f: 2.71 };
    let tn: i32 = t.n;
    let ts: string = t.s;
    let tb: bool = t.b;
    let tf: f64 = t.f;
    println("n={}", tn);
    println("s={}", ts);
    println("b={}", tb);
    println("f={}", tf);

    // --- Type Promotion ---
    println("--- type promotion ---");
    let i8v: i8 = 10(i8);
    let i32v: i32 = 100;
    let p1 = i8v + i32v;        // promoted to i32
    println("i8+i32={}", p1);   // 110

    let f32v: f32 = 1.5(f32);
    let f64v: f64 = 2.5;
    let p2 = f32v + f64v;       // promoted to f64
    println("f32+f64={}", p2);  // 4.0

    let i16v: i16 = 50(i16);
    let i64v: i64 = 1000(i64);
    let p3 = i16v + i64v;       // promoted to i64
    println("i16+i64={}", p3);  // 1050

    println("=== OK ===");
    return 0;
}
