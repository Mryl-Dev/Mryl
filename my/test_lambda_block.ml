// Test: block body lambda
fn main() -> void {
    let l = (x: i32) => {
        let ll = x * 2;
        let result = ll * 2;
        println(result);
    };

    l(3);
    l(5);
}
