// ============================================================
// Test 04: Functions / Lambdas / Generics
// ============================================================

// --- Basic Functions ---
fn add(a: i32, b: i32) -> i32 {
    return a + b;
}

fn multiply(a: i32, b: i32) -> i32 {
    return a * b;
}

fn greet(name: string) -> void {
    println("Hello, {}!", name);
}

fn max(a: i32, b: i32) -> i32 {
    if (a > b) {
        return a;
    }
    return b;
}

// --- Recursive Functions ---
fn factorial(n: i32) -> i32 {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

fn fib(n: i32) -> i32 {
    if (n <= 1) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

// --- Generic Functions ---
fn identity<T>(value: T) -> T {
    return value;
}

fn generic_add<T>(a: T, b: T) -> T {
    return a + b;
}

fn main() -> i32 {
    println("=== 04: Functions ===");

    // --- Basic Function Calls ---
    println("--- Basic Functions ---");
    println("add(5,3)={}", add(5, 3));           // 8
    println("mul(4,7)={}", multiply(4, 7));       // 28
    println("max(10,20)={}", max(10, 20));        // 20
    println("max(30,15)={}", max(30, 15));        // 30
    greet("Mryl");                                // Hello, Mryl!

    // --- Recursion ---
    println("--- Recursion ---");
    println("0!={}", factorial(0));   // 1
    println("1!={}", factorial(1));   // 1
    println("5!={}", factorial(5));   // 120
    println("10!={}", factorial(10)); // 3628800

    println("fib(0)={}", fib(0));  // 0
    println("fib(1)={}", fib(1));  // 1
    println("fib(7)={}", fib(7));  // 13
    println("fib(10)={}", fib(10)); // 55

    // --- Lambdas ---
    println("--- Lambdas ---");
    let double = (x: i32) => x * 2;
    println("double(5)={}", double(5));    // 10
    println("double(0)={}", double(0));    // 0

    let add_lambda = (x: i32, y: i32) => x + y;
    println("add(3,7)={}", add_lambda(3, 7));   // 10

    let is_positive = (n: i32) => n > 0;
    println("is_positive(5)={}", is_positive(5));    // true
    println("is_positive(-3)={}", is_positive(-3));  // false

    let square = (x: i32) => x * x;
    let cube   = (x: i32) => x * x * x;
    println("square(4)={}", square(4));  // 16
    println("cube(3)={}", cube(3));      // 27

    // use lambda inside loop
    for i in 1..6 {
        println("{}^2={}", i, square(i));
    }
    // 1 4 9 16 25

    // --- Generics ---
    println("--- Generics ---");
    println("identity(42)={}", identity(42));           // 42
    println("identity(true)={}", identity(true));       // true

    println("generic_add(10,20)={}", generic_add(10, 20));      // 30
    println("generic_add(1.5,2.5)={}", generic_add(1.5, 2.5)); // 4.0

    println("=== OK ===");
    return 0;
}
