// ============================================================
// Test 16: async ラムダ式
//   A. void async lambda (await なし)
//   B. 戻り値 async lambda (await あり)
//   C. async lambda 複数回呼び出し - C1
//   D. async lambda 内条件分岐 - C1 [Bug#12 確認]
//   E. ヘルパー関数経由 MC/DC
//
// カバレッジ観点:
//   C0  : 全 async lambda を少なくとも1回 await
//   C1  :
//     C: 同じ async lambda を複数の入力で呼び出す
//     D: async lambda 内 if 分岐の true/false 両ブランチ実行
//        [Bug#12: 条件 return が void move_next 内で Cerr になる場合は SKIP]
//   MC/DC:
//     E: helper(n) 内 (n > 0 && n < 100):
//       {n>0=F, *}         0 (n=0: n>0=F 単独決定)
//       {n>0=T, n<100=F}   0 (n=100: n<100=F 単独決定)
//       {n>0=T, n<100=T}   1 (n=50: 両方 T)
// ============================================================

// ----------------------------------------------------------
// A. 基本 async 関数 (lambda から await する)
// ----------------------------------------------------------
async fn double_value(n: i32) -> i32 {
    return n * 2;
}

// MC/DC ヘルパー (普通の関数: Bug#12 の影響なし)
fn in_small_range(n: i32) -> i32 {
    if (n > 0 && n < 100) {
        return 1;
    }
    return 0;
}

// ----------------------------------------------------------
// main
// ----------------------------------------------------------
fn main() -> i32 {
    println("=== 16: async lambda ===");

    // ----------------------------------------------------------
    // A. void async lambda / C0
    // ----------------------------------------------------------
    println("--- A: void async lambda ---");
    let greet = async (x: i32) => {
        println("greet={}", x);
    };
    await greet(42);     // greet=42
    await greet(0);      // greet=0

    // ----------------------------------------------------------
    // B. 戻り値 async lambda (await 内 await) / C0
    // ----------------------------------------------------------
    println("--- B: lambda with await ---");
    let compute = async (x: i32) => {
        let result: i32 = await double_value(x);
        println("double={}", result);
    };
    await compute(5);    // double=10
    await compute(3);    // double=6

    // ----------------------------------------------------------
    // C. 複数回呼び出し / C1: 異なる入力で複数回実行
    // ----------------------------------------------------------
    println("--- C: multiple calls ---");
    await greet(100);    // greet=100
    await greet(-1);     // greet=-1
    await compute(0);    // double=0
    await compute(10);   // double=20

    // ----------------------------------------------------------
    // D. async lambda 内条件分岐 / C1 [Bug#12 確認]
    // ----------------------------------------------------------
    println("--- D: lambda branch ---");
    let print_if_pos = async (n: i32) => {
        if (n > 0) {
            println("pos={}", n);
        }
    };
    // C1: n>0=true
    await print_if_pos(5);    // pos=5
    // C1: n>0=false (何も出力されない)
    await print_if_pos(-1);
    await print_if_pos(0);
    println("after branch lambda");    // after branch lambda

    // ----------------------------------------------------------
    // E. ヘルパー関数経由 MC/DC
    // (async lambda から普通の関数を呼び出して結果を出力)
    // ----------------------------------------------------------
    println("--- E: MC/DC via helper ---");
    let check = async (n: i32) => {
        println("check({})={}", n, in_small_range(n));
    };

    // {n>0=F, *}  0 (n=0)
    await check(0);    // check(0)=0

    // {n>0=T, n<100=F}  0 (n=100)
    await check(100);  // check(100)=0

    // {n>0=T, n<100=T}  1 (n=50)
    await check(50);   // check(50)=1

    println("=== OK ===");
    return 0;
}
