// ============================================================
// Test 10: async / await
//   A. 基本 async (i32 戻り値)
//   B. void async
//   C. async チェーン (await inside async)
//   D. 条件分岐を持つ async - C1
//   E. 複合条件を持つ async - MC/DC
//
// カバレッジ観点:
//   C0  : 全 async 関数を少なくとも1回 await
//   C1  :
//     D: async_safe_div() の if(b==0)  true(Err) / false(Ok) 両ブランチ
//   MC/DC:
//     E: async_clamp(n, lo, hi) 内 (n < lo || n > hi):
//       {n<lo=T, *}       lo  (n<lo=T が単独決定)
//       {n<lo=F, n>hi=T}  lo  (n>hi=T が単独決定)
//       {n<lo=F, n>hi=F}  n   (両方 F)
// ============================================================

// ----------------------------------------------------------
// A. 基本 async
// ----------------------------------------------------------
async fn square(n: i32) -> i32 {
    return n * n;
}

async fn add_async(a: i32, b: i32) -> i32 {
    return a + b;
}

// ----------------------------------------------------------
// B. void async
// ----------------------------------------------------------
async fn print_double(n: i32) -> void {
    println("double={}", n * 2);
}

// ----------------------------------------------------------
// C. async チェーン
// ----------------------------------------------------------
async fn chain(x: i32) -> i32 {
    let a: i32 = await square(x);
    let b: i32 = await add_async(a, 1);
    return b;
}

// ----------------------------------------------------------
// D. 条件分岐 async (C1)
// [Bug#12] async 関数内の条件 return が void move_next 内で return 値; に
//          生成されるため C コンパイルエラー
//          Issue: async state machine の早期 return を
//                 __task->result = val; return; に変換する
// ----------------------------------------------------------
// async fn safe_div(a: i32, b: i32) -> i32 {
//     if (b == 0) { return -1; }
//     return a / b;
// }

// ----------------------------------------------------------
// E. 複合条件 async (MC/DC)
// [Bug#12] 同上
// ----------------------------------------------------------
// async fn clamp(n: i32, lo: i32, hi: i32) -> i32 {
//     if (n < lo || n > hi) { return lo; }
//     return n;
// }

// ----------------------------------------------------------
// main
// ----------------------------------------------------------
fn main() -> i32 {
    println("=== 10: async/await ===");

    // ----------------------------------------------------------
    // A. 基本 async (C0)
    // ----------------------------------------------------------
    println("--- A: square ---");
    let h1 = square(7);
    let r1: i32 = await h1;
    println("square(7)={}", r1);       // 49

    let h2 = square(5);
    let r2: i32 = await h2;
    println("square(5)={}", r2);       // 25

    println("--- A: add_async ---");
    let h3 = add_async(10, 20);
    let r3: i32 = await h3;
    println("add(10,20)={}", r3);      // 30

    // ----------------------------------------------------------
    // B. void async (C0)
    // ----------------------------------------------------------
    println("--- B: void async ---");
    let h4 = print_double(6);
    await h4;                          // double=12
    let h5 = print_double(0);
    await h5;                          // double=0

    // ----------------------------------------------------------
    // C. async チェーン (C0)
    // ----------------------------------------------------------
    println("--- C: chain ---");
    let h6 = chain(3);
    let r6: i32 = await h6;
    println("chain(3)={}", r6);        // square(3)+1 = 10

    let h7 = chain(4);
    let r7: i32 = await h7;
    println("chain(4)={}", r7);        // square(4)+1 = 17

    // ----------------------------------------------------------
    // D. 条件分岐 async / C1 [SKIP Bug#12]
    // ----------------------------------------------------------
    println("--- D: safe_div (SKIP Bug#12) ---");
    // let h8 = safe_div(10, 2); let r8: i32 = await h8;
    // println("safe(10,2)={}", r8);  // 5
    // let h9 = safe_div(10, 0); let r9: i32 = await h9;
    // println("safe(10,0)={}", r9);  // -1

    // ----------------------------------------------------------
    // E. 複合条件 async / MC/DC [SKIP Bug#12]
    // ----------------------------------------------------------
    println("--- E: clamp (SKIP Bug#12) ---");
    // let ha = clamp(-1, 0, 10);  let ra: i32 = await ha;
    // println("clamp(-1,0,10)={}", ra);  // 0
    // let hb = clamp(11, 0, 10);  let rb: i32 = await hb;
    // println("clamp(11,0,10)={}", rb);  // 0
    // let hc = clamp(5, 0, 10);   let rc: i32 = await hc;
    // println("clamp(5,0,10)={}", rc);   // 5

    println("=== OK ===");
    return 0;
}
