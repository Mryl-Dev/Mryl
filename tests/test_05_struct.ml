// ============================================================
// Test 05: Structs / Methods / Generic Structs
// ============================================================

// --- Basic Struct ---
struct Point {
    x: i32;
    y: i32;
}

impl Point {
    fn display(self) -> void {
        println("Point({}, {})", self.x, self.y);
    }

    fn sum(self) -> i32 {
        return self.x + self.y;
    }

    fn move_by(self, dx: i32, dy: i32) -> void {
        self.x = self.x + dx;
        self.y = self.y + dy;
    }
}

// --- Struct with String Field ---
struct Person {
    name: string;
    age: i32;
}

impl Person {
    fn greet(self) -> void {
        println("I am {}, {} years old.", self.name, self.age);
    }

    fn birthday(self) -> void {
        self.age = self.age + 1;
    }
}

// --- Struct with Float Field ---
struct Circle {
    radius: f64;
}

impl Circle {
    fn area(self) -> f64 {
        return self.radius * self.radius * 3.14159;
    }

    fn perimeter(self) -> f64 {
        return 2.0 * 3.14159 * self.radius;
    }
}

// --- Generic Struct ---
struct Box<T> {
    value: T;
}

struct Pair<T, U> {
    first: T;
    second: U;
}

fn main() -> i32 {
    println("=== 05: Structs ===");

    // --- Basic Operations ---
    println("--- Point ---");
    let p = Point { x: 3, y: 4 };
    p.display();                          // Point(3, 4)
    println("sum={}", p.sum());           // 7

    // field assignment
    p.x = 10;
    p.y = 20;
    p.display();                          // Point(10, 20)

    // move via method
    p.move_by(5, -3);
    p.display();                          // Point(15, 17)

    // field access
    println("x={}", p.x);
    println("y={}", p.y);

    // --- String Field ---
    println("--- Person ---");
    let alice = Person { name: "Alice", age: 30 };
    alice.greet();                        // I am Alice, 30 years old.
    alice.birthday();
    alice.greet();                        // I am Alice, 31 years old.

    let bob = Person { name: "Bob", age: 25 };
    bob.greet();

    // --- Float Field ---
    println("--- Circle ---");
    let c = Circle { radius: 5.0 };
    println("area={}", c.area());             // 78.539...
    println("perimeter={}", c.perimeter());   // 31.415...

    let c2 = Circle { radius: 1.0 };
    println("unit area={}", c2.area());       // 3.14159

    // --- Generic Struct ---
    println("--- Generic ---");
    let bi = Box<i32> { value: 42 };
    println("Box<i32>={}", bi.value);    // 42

    let bs = Box<string> { value: "hello" };
    println("Box<string>={}", bs.value); // hello

    let bf = Box<f64> { value: 3.14 };
    println("Box<f64>={}", bf.value);    // 3.14

    let pair = Pair<i32, string> { first: 1, second: "one" };
    println("Pair.first={}", pair.first);   // 1
    println("Pair.second={}", pair.second); // one

    println("=== OK ===");
    return 0;
}
