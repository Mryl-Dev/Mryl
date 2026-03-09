async fn compute() -> i32 {
    let result: i32 = 0; // ダミーの計算結果
    result++;
    return result;
}

async fn nested_await() -> void {
    for (let i = 0; i < 10; i++) {
        let r: i32 = await compute();
        println("Iteration {}: result = {}", i, r);
        for (let j = 0; j < 5; j++) {
            let nested_r: i32 = await compute();
            println("  Nested Iteration {}: nested result = {}", j, nested_r);
            for (let k = 0; k < 3; k++) {
                let nested_r2: i32 = await compute();
                println("    Nested Level 2 Iteration {}: nested result = {}", k, nested_r2);
                for (let l = 0; l < 2; l++) {
                    let nested_r3: i32 = await compute();
                    println("      Nested Level 3 Iteration {}: nested result = {}", l, nested_r3);
                }
            }
        }
    }
}

fn main() -> void {
    await nested_await();
}