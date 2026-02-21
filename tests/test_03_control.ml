// ============================================================
// Test 03: Control Flow
//   if/else / while / for Rust-style / for C-style / break / continue
// ============================================================

fn main() -> i32 {
    println("=== 03: Control Flow ===");

    // --- if / else if / else ---
    println("--- if/else ---");
    let score = 75;
    if (score >= 90) {
        println("A");
    } else if (score >= 70) {
        println("B");   // <- here
    } else if (score >= 50) {
        println("C");
    } else {
        println("F");
    }

    // simple if
    let x = 10;
    if (x > 0) { println("positive"); }

    // false branch
    if (x < 0) {
        println("negative");
    } else {
        println("non-negative");  // <- here
    }

    // --- while ---
    println("--- while ---");
    let i = 0;
    while (i < 5) {
        println("{}", i);
        i++;
    }
    // 0 1 2 3 4

    // --- for Rust-style (range) ---
    println("--- for range ---");
    for n in 0..5 {
        println("{}", n);
    }
    // 0 1 2 3 4

    // --- for Rust-style (array) ---
    println("--- for array ---");
    let arr = [10, 20, 30];
    for v in arr {
        println("{}", v);
    }
    // 10 20 30

    // --- for C-style ---
    println("--- for C-style ---");
    for (let j = 0; j < 5; j++) {
        println("{}", j);
    }
    // 0 1 2 3 4

    // increment by 2
    for (let k = 0; k <= 8; k = k + 2) {
        println("{}", k);
    }
    // 0 2 4 6 8

    // --- break ---
    println("--- break ---");
    let cnt = 0;
    while (cnt < 10) {
        if (cnt == 4) { break; }
        println("{}", cnt);
        cnt++;
    }
    // 0 1 2 3

    // break in for-range
    for m in 0..10 {
        if (m == 3) { break; }
        println("{}", m);
    }
    // 0 1 2

    // --- continue ---
    println("--- continue ---");
    for p in 0..7 {
        if (p % 2 == 0) { continue; }
        println("{}", p);
    }
    // 1 3 5

    // C-style for continue (increment still executes)
    for (let q = 0; q < 8; q++) {
        if (q == 3) { continue; }
        if (q == 6) { break; }
        println("{}", q);
    }
    // 0 1 2 4 5

    // --- nested loop + break/continue ---
    println("--- nested loop ---");
    for outer in 0..3 {
        for inner in 0..3 {
            if (inner == 1) { continue; }
            println("{}-{}", outer, inner);
        }
    }
    // 0-0 0-2  1-0 1-2  2-0 2-2

    // break outer loop
    let found = 0;
    let row = 0;
    while (row < 5) {
        let col = 0;
        while (col < 5) {
            if (row * 5 + col == 7) {
                found = row * 5 + col;
                break;
            }
            col++;
        }
        if (found != 0) { break; }
        row++;
    }
    println("found={}", found);   // 7

    println("=== OK ===");
    return 0;
}
