// ============================================================
// Test 08: 配列 (固定長 / 動的配列)
//   A. 固定長配列 (定義アクセス代入) i32 / f64 / string
//   B. 動的配列 (push / pop / len / is_empty)
//   C. 動的配列 insert / remove
//   D. for-in ループ (配列 + 範囲)
//   E. 配列 + 条件分岐 / 動的 string[] (C1 + MC/DC)
//
// カバレッジ観点:
//   C0  : 全メソッド (push/pop/insert/remove/len/is_empty) を1回以上実行
//   C1  :
//     B: is_empty()  true(空) / false(非空) 両ブランチ
//     B: while(!is_empty())  1回以上実行 / 0回実行(空配列) 両ケース
//   MC/DC:
//     E: ループ内 (n > 0 && n % 2 == 0):
//       {n>0=F, *}           skip (n=0: n>0=F が単独決定)
//       {n>0=T, n%2==0=F}    skip (n=1: n%2==0=F が単独決定)
//       {n>0=T, n%2==0=T}    push (n=2: 両方 T で push)
// ============================================================

fn main() -> i32 {
    println("=== 08: Arrays ===");

    // ----------------------------------------------------------
    // A. 固定長配列 (i32) / C0
    // ----------------------------------------------------------
    println("--- A: Fixed Array ---");
    let arr = [1, 2, 3, 4, 5];
    println("arr[0]={}", arr[0]);    // 1
    println("arr[4]={}", arr[4]);    // 5

    // 要素代入
    arr[2] = 99;
    println("arr[2]={}", arr[2]);    // 99

    // for-in 全要素走査 (C0)
    for v in arr {
        println("{}", v);
    }
    // 1 2 99 4 5

    // f64 固定長配列
    let floats = [1.1, 2.2, 3.3];
    println("f[1]={}", floats[1]);     // 2.2

    // string 固定長配列
    let words = ["apple", "banana", "cherry"];
    println("w[0]={}", words[0]);      // apple
    for w in words { println("{}", w); }
    // apple banana cherry
    println("--- A: f64/string Array ---");

    // ----------------------------------------------------------
    // B. 動的配列 / C1: is_empty + while ループ
    // ----------------------------------------------------------
    println("--- B: Dynamic Array ---");
    let nums: i32[] = [];

    // C1: is_empty() = true (空)
    // [Bug#11] is_empty() を直接 println すると Python=True/C=1 で表示差異
    // → if で 0/1 を出力して一致させる
    if (nums.is_empty()) { println("empty=1"); } else { println("empty=0"); }  // 1
    println("len={}",   nums.len());        // 0

    nums.push(10);
    nums.push(20);
    nums.push(30);

    // C1: is_empty() = false (非空)
    if (nums.is_empty()) { println("nonempty=1"); } else { println("nonempty=0"); }  // 0
    println("len={}", nums.len());             // 3

    println("nums[0]={}", nums[0]);   // 10
    println("nums[2]={}", nums[2]);   // 30

    // 要素代入
    nums[1] = 99;
    println("nums[1]={}", nums[1]);   // 99

    // pop
    let popped: i32 = nums.pop();
    println("popped={}", popped);              // 30
    println("len after pop={}", nums.len());   // 2

    // C1: while(!is_empty())  実行あり
    println("--- B: while pop (with data) ---");
    let stack: i32[] = [100, 200, 300];
    while (!stack.is_empty()) {
        let top: i32 = stack.pop();
        println("{}", top);
    }
    // 300 200 100

    // C1: while(!is_empty())  0回実行(空配列)
    println("--- B: while pop (empty) ---");
    let empty_stack: i32[] = [];
    while (!empty_stack.is_empty()) {
        let top2: i32 = empty_stack.pop();
        println("{}", top2);
    }
    println("done");   // done (ループ0回後に到達)

    // ----------------------------------------------------------
    // C. insert / remove / C0
    // ----------------------------------------------------------
    println("--- C: insert/remove ---");
    let xs: i32[] = [1, 2, 3, 4, 5];
    println("len={}", xs.len());    // 5

    // insert(idx, val)
    xs.insert(0, 0);
    println("after insert(0,0): len={}", xs.len());  // 6
    println("xs[0]={}", xs[0]);   // 0
    println("xs[1]={}", xs[1]);   // 1

    // remove(idx)
    let removed: i32 = xs.remove(1);
    println("removed={}", removed);              // 1
    println("len after remove={}", xs.len());    // 5
    println("xs[1]={}", xs[1]);                  // 2

    // ----------------------------------------------------------
    // D. for-in (動的配列 + 範囲) / C0
    // ----------------------------------------------------------
    println("--- D: for-in ---");
    let ys: i32[] = [10, 20, 30];
    for y in ys {
        println("{}", y);
    }
    // 10 20 30

    // 範囲 for-in
    for i in 0..3 {
        println("i={}", i);
    }
    // 0 1 2

    // ----------------------------------------------------------
    // E. 条件付き push / C1 + MC/DC
    // MC/DC: (n > 0 && n % 2 == 0)
    // n=0: n>0=F  skip (n>0=F が単独決定)
    // n=1: n>0=T, n%2==0=F  skip (n%2==0=F が単独決定)
    // n=2: n>0=T, n%2==0=T  push (両方 T)
    // ----------------------------------------------------------
    println("--- E: Conditional push MC/DC ---");
    let evens: i32[] = [];
    for n in 0..6 {
        if (n > 0 && n % 2 == 0) {
            evens.push(n);
        }
    }
    println("evens.len={}", evens.len());  // 2  (2,4)
    for e in evens {
        println("{}", e);
    }
    // 2 4

    // string 動的配列
    let tags: string[] = [];
    tags.push("rust");
    tags.push("Mryl");
    println("tags.len={}", tags.len());  // 2
    for t in tags { println("{}", t); }
    // rust Mryl
    println("--- E: string[] ---");

    println("=== OK ===");
    return 0;
}
