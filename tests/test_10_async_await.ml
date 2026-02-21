// ============================================================
// Test 10: async / await
// ============================================================

// --- Basic async functions (with return value) ---
async fn square(n: i32) -> i32 {
    return n * n;
}

async fn add_async(a: i32, b: i32) -> i32 {
    return a + b;
}

// --- async function with no return value (void) ---
async fn greet(name: string) -> void {
    println("Hello, {}!", name);
}

// --- async function with multiple awaits ---
async fn chain(x: i32) -> i32 {
    let a: i32 = await square(x);
    let b: i32 = await add_async(a, 1);
    return b;
}

fn main() -> i32 {
    println("=== 10: async/await ===");

    // --- simple await ---
    println("--- square ---");
    let h1 = square(7);
    let r1: i32 = await h1;
    println("square(7)={}", r1);        // 49

    let h2 = square(5);
    let r2: i32 = await h2;
    println("square(5)={}", r2);        // 25

    // --- void async ---
    println("--- void async ---");
    let h3 = greet("Mryl");
    await h3;
    // -> Hello, Mryl!

    // --- add_async ---
    println("--- add_async ---");
    let h4 = add_async(10, 20);
    let r4: i32 = await h4;
    println("add(10,20)={}", r4);       // 30

    let h5 = add_async(100, 200);
    let r5: i32 = await h5;
    println("add(100,200)={}", r5);     // 300

    // --- chain (await inside await) ---
    println("--- chain ---");
    let h6 = chain(3);
    let r6: i32 = await h6;
    println("chain(3)={}", r6);         // square(3)+1=10

    let h7 = chain(4);
    let r7: i32 = await h7;
    println("chain(4)={}", r7);         // square(4)+1=17

    println("=== OK ===");
    return 0;
}
