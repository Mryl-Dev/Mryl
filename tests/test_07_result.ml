// ============================================================
// Test 07: Result<T,E> / Error Handling
// ============================================================

fn divide(a: i32, b: i32) -> Result<i32, string> {
    if (b == 0) {
        return Err("division by zero");
    }
    return Ok(a / b);
}

fn safe_sqrt(x: f64) -> Result<f64, string> {
    if (x < 0.0) {
        return Err("negative input");
    }
    // simple Newton's method (4 iterations)
    let g = x / 2.0;
    g = (g + x / g) / 2.0;
    g = (g + x / g) / 2.0;
    g = (g + x / g) / 2.0;
    g = (g + x / g) / 2.0;
    return Ok(g);
}

fn parse_positive(n: i32) -> Result<i32, string> {
    if (n <= 0) {
        return Err("not positive");
    }
    return Ok(n);
}

fn main() -> i32 {
    println("=== 07: Result Type ===");

    // --- Ok Path ---
    println("--- Ok ---");
    let r1 = divide(10, 2);
    let v1: i32 = match r1 {
        Ok(v)  => v,
        Err(e) => -999,
    };
    println("10/2={}", v1);     // 5

    let r2 = divide(7, 3);
    let v2: i32 = match r2 {
        Ok(v)  => v,
        Err(e) => -999,
    };
    println("7/3={}", v2);      // 2 (integer division)

    // --- Err Path ---
    println("--- Err ---");
    let r3 = divide(5, 0);
    let v3: i32 = match r3 {
        Ok(v)  => v,
        Err(e) => {
            println("error: {}", e);
            -1
        },
    };
    println("5/0 result={}", v3);   // error: division by zero  -1

    // --- f64 Result ---
    println("--- f64 Result ---");
    let sr1 = safe_sqrt(9.0);
    let sv1: f64 = match sr1 {
        Ok(v)  => v,
        Err(e) => -1.0,
    };
    println("sqrt(9)~={}", sv1);   // ~3.0

    let sr2 = safe_sqrt(-4.0);
    let sv2: f64 = match sr2 {
        Ok(v)  => v,
        Err(e) => {
            println("sqrt error: {}", e);
            0.0
        },
    };
    println("sqrt(-4) result={}", sv2);  // error: negative input  0.0

    // --- match Ok/Err check ---
    println("--- parse_positive ---");
    let values: i32[] = [5, -3, 0, 100];
    for val in values {
        let res = parse_positive(val);
        let out: i32 = match res {
            Ok(v)  => v,
            Err(e) => {
                println("{} is invalid: {}", val, e);
                0
            },
        };
        if (out > 0) {
            println("{} -> ok={}", val, out);
        }
    }
    // 5 -> ok=5
    // -3 is invalid: not positive
    // 0 is invalid: not positive
    // 100 -> ok=100

    // --- .try() success path ---
    println("--- .try() ok ---");
    let ok_val = divide(20, 4).try();
    println("try ok={}", ok_val);   // 5

    println("=== OK ===");
    return 0;
}
