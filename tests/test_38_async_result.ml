// test_38_async_result.ml
// #51: async fn が Err を返した場合に await 側でエラーが伝播することを確認
//
// 注意: match arm 内で string バインディングを直接 println すると C native で
//       ゴミ値になる既知バグ(Bug#7)があるため、string Ok 値の確認は
//       match で変数を束縛せず固定文字列を出力することで回避する。

// ケース A: Result<string, string> を返す async fn
async fn fetch(url: string) -> Result<string, string> {
    if (url == "") {
        return Err("empty url");
    }
    return Ok("data received");
}

// ケース B: Result<i32, string> を返す async fn
async fn step1() -> Result<i32, string> {
    return Err("step1 failed");
}

async fn step2() -> Result<i32, string> {
    return Ok(42);
}

fn main() {
    // A-1: Err ケース — Err メッセージが伝播する (Bug#7 回避: Err(string)は直接表示可)
    let r1: Result<string, string> = await fetch("");
    match r1 {
        Ok(v)  => println("FAIL: should not be ok"),
        Err(e) => println("err: {}", e),
    };

    // A-2: Ok ケース — is_ok() で Ok 判定 (Bug#7 回避: string バインディングを print しない)
    let r2: Result<string, string> = await fetch("http://example.com");
    match r2 {
        Ok(v)  => println("ok: received"),
        Err(e) => println("FAIL: should not be err"),
    };

    // B-1: Result<i32, string> Err ケース — i32 バインディングは print 可能
    let r3: Result<i32, string> = await step1();
    match r3 {
        Ok(v)  => println("FAIL: should not be ok"),
        Err(e) => println("chain err: {}", e),
    };

    // B-2: Result<i32, string> Ok ケース — i32 バインディングは print 可能
    let r4: Result<i32, string> = await step2();
    match r4 {
        Ok(v)  => println("chain ok: {}", v),
        Err(e) => println("FAIL: should not be err"),
    };

    println("=== OK ===");
}
