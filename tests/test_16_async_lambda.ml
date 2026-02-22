// ============================================================
// test_16_async_lambda.ml
// async ラムダ式の動作確認テスト
// 対象: async (params) => { block } の定義・呼び出し・await 待機
// ============================================================

async fn double_value(n: i32) -> i32 {
    return n * 2;
}

fn main() {
    // ---- T16-01: async ラムダ（ボディ内 await なし、void） ----
    let greet = async (x: i32) => {
        println(x);
    };
    await greet(42);

    // ---- T16-02: async ラムダ（ボディ内 await あり） ----
    let compute = async (x: i32) => {
        let result = await double_value(x);
        println(result);
    };
    await compute(5);

    // ---- T16-03: async ラムダ 複数回呼び出し ----
    await greet(100);
    await compute(10);
}
