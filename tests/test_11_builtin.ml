// ============================================================
// Test 11: Built-in Functions (print / println / to_string)
// ============================================================

fn main() -> i32 {
    println("=== 11: Built-in Functions ===");

    // --- print (no newline) ---
    println("--- print ---");
    print("no");
    print("-");
    print("newline");
    print("\n");                    // -> no-newline

    // --- println basic ---
    println("--- println basic ---");
    println("hello world");
    println(42);
    println(3.14);
    println(true);
    println(false);

    // --- println format string (1 variable) ---
    println("--- println format 1 ---");
    let i = 10;
    println("i={}", i);             // i=10

    let f = 3.14;
    println("f={}", f);             // f=3.14

    let s = "Mryl";
    println("lang={}", s);          // lang=Mryl

    let b = true;
    println("flag={}", b);          // flag=True

    // --- println format string (multiple variables) ---
    println("--- println format multi ---");
    let x = 5;
    let y = 20;
    println("x={}, y={}", x, y);   // x=5, y=20

    let name = "Mryl";
    let ver = 1;
    println("lang={}, ver={}", name, ver);  // lang=Mryl, ver=1

    let a = 1;
    let bv = 2;
    let c = 3;
    println("{} {} {}", a, bv, c);  // 1 2 3

    // --- to_string ---
    println("--- to_string ---");
    let n = 42;
    let sn = to_string(n);
    println("to_string(42)={}", sn);        // 42

    let fv = 3.14;
    let sf = to_string(fv);
    println("to_string(3.14)={}", sf);      // 3.14

    let flag = true;
    let sb = to_string(flag);
    println("to_string(true)={}", sb);      // True

    // --- to_string with format ---
    println("--- to_string format ---");
    let val = 100;
    let msg = to_string(val);
    println("Value is {}", msg);                // Value is 100

    let neg = -7;
    let smsg = to_string(neg);
    println("neg={}", smsg);                    // neg=-7

    println("=== OK ===");
    return 0;
}
