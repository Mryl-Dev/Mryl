// Test: block body lambda with return value
fn main() -> void {
    let compute = (x: i32) => {
        let doubled = x * 2;
        let result = doubled + 10;
        return result;
    };

    let r1 = compute(3);   // 16
    let r2 = compute(5);   // 20
    println(r1);
    println(r2);
}
