// #41 テスト: fn型パラメータ（コールバック）

fn apply(callback: fn(i32) -> i32, value: i32) -> i32 {
    return callback(value);
}

fn apply_two(f: fn(i32, i32) -> i32, a: i32, b: i32) -> i32 {
    return f(a, b);
}

fn main() -> i32 {
    let double = (x: i32) => { return x * 2; };
    println("{}", apply(double, 5));        // 10

    let add = (x: i32, y: i32) => { return x + y; };
    println("{}", apply_two(add, 3, 4));    // 7

    let square = (x: i32) => { return x * x; };
    println("{}", apply(square, 6));        // 36

    return 0;
}