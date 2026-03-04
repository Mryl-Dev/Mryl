// ============================================================
// Test 10: async / await
//   A. 基本 async (i32 戻り値)
//   B. void async
//   C. async チェーン (await inside async)
//   D. 条件分岐を持つ async - C1
//   E. 複合条件を持つ async - MC/DC
//   F. ネストループ内 await - C1, MC/DC
//
// カバレッジ観点:
//   C0  : 全 async 関数を少なくとも1回 await
//   C1  :
//     D: async_safe_div() の if(b==0)  true(Err) / false(Ok) 両ブランチ
//     F: 外ループ条件 T/F-branch, 内ループ条件 T/F-branch
//   MC/DC:
//     E: async_clamp(n, lo, hi) 内 (n < lo || n > hi):
//       {n<lo=T, *}       lo  (n<lo=T が単独決定)
//       {n<lo=F, n>hi=T}  lo  (n>hi=T が単独決定)
//       {n<lo=F, n>hi=F}  n   (両方 F)
//     F: 外ループ条件 (fi < 2) / 内ループ条件 (fj < 2):
//       {fi<2=T} fi=0       → ボディ実行     (T が単独決定)
//       {fi<2=F} limit_o=0  → 外即終了       (F が単独決定)
//       {fj<2=T} fj=0       → ボディ実行     (T が単独決定)
//       {fj<2=F} limit_i=0  → 内即終了       (F が単独決定)
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
// ----------------------------------------------------------
async fn safe_div(a: i32, b: i32) -> i32 {
    if (b == 0) { return -1; }
    return a / b;
}

// ----------------------------------------------------------
// E. 複合条件 async (MC/DC)
// ----------------------------------------------------------
async fn clamp(n: i32, lo: i32, hi: i32) -> i32 {
    if (n < lo || n > hi) { return lo; }
    return n;
}

// ----------------------------------------------------------
// F. ネストループ await (C1 / MC/DC)
// ----------------------------------------------------------
async fn nest_work(val: i32) -> i32 {
    return val;
}

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
    // D. 条件分岐 async / C1
    // ----------------------------------------------------------
    println("--- D: safe_div ---");
    let h8 = safe_div(10, 2); let r8: i32 = await h8;
    println("safe(10,2)={}", r8);  // 5
    let h9 = safe_div(10, 0); let r9: i32 = await h9;
    println("safe(10,0)={}", r9);  // -1

    // ----------------------------------------------------------
    // E. 複合条件 async / MC/DC
    // ----------------------------------------------------------
    println("--- E: clamp ---");
    let ha = clamp(-1, 0, 10);  let ra: i32 = await ha;
    println("clamp(-1,0,10)={}", ra);  // 0
    let hb = clamp(11, 0, 10);  let rb: i32 = await hb;
    println("clamp(11,0,10)={}", rb);  // 0
    let hc = clamp(5, 0, 10);   let rc: i32 = await hc;
    println("clamp(5,0,10)={}", rc);   // 5

    // ----------------------------------------------------------
    // F. ネストループ await / C1, MC/DC
    //
    // C0  : 外 i=0..1, 内 j=0..1 の全4組み合わせで await 実行
    // C1  :
    //   外ループ条件 (fi < limit_o)
    //     T-branch : limit_o=2, fi=0 → ボディ実行          [C0 で達成]
    //     F-branch : limit_o=0, fi<0 → ボディ未実行
    //   内ループ条件 (fj < limit_i)
    //     T-branch : limit_i=2, fj=0 → ボディ実行          [C0 で達成]
    //     F-branch : limit_i=0, fj<0 → ボディ未実行
    // MC/DC:
    //   外条件 (fi < 2): T=fi=0 継続, F=limit_o=0 で即終了
    //   内条件 (fj < 2): T=fj=0 継続, F=limit_i=0 で即終了
    // ----------------------------------------------------------
    println("--- F: nested-loop await ---");

    // [C0] 外2回 × 内2回 = 4回 await
    for (let fi = 0; fi < 2; fi++) {
        for (let fj = 0; fj < 2; fj++) {
            let fh = nest_work(fi * 10 + fj);
            let fr: i32 = await fh;
            println("nest({},{})={}", fi, fj, fr);  // 0,1,10,11
        }
    }

    // [C1/MC/DC 外 F-branch] limit_o=0: 外ループ条件が初回から偽 → ボディ未実行
    for (let fi2 = 0; fi2 < 0; fi2++) {
        let fh2 = nest_work(fi2);
        let fr2: i32 = await fh2;
        println("outer_body={}", fr2);  // 出力なし
    }
    println("outer_skip=ok");  // outer_skip=ok

    // [C1/MC/DC 内 F-branch] 外limit=1, 内limit=0: 内ループ条件が初回から偽 → 内ボディ未実行
    for (let fi3 = 0; fi3 < 1; fi3++) {
        for (let fj3 = 0; fj3 < 0; fj3++) {
            let fh3 = nest_work(fj3);
            let fr3: i32 = await fh3;
            println("inner_body={}", fr3);  // 出力なし
        }
        println("inner_skip({})=ok", fi3);  // inner_skip(0)=ok
    }

    println("=== OK ===");
    return 0;
}
