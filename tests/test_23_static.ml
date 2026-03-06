// ============================================================
// Test 23: static fn (静的メソッド)
//   A. 基本 static fn 呼び出し: TypeName::method()        [C0]
//   B. static fn が struct を返す（コンストラクタ）        [C0]
//   C. static fn 内から同 struct の他 static fn を呼ぶ    [C0]
//   D. static fn を fn 型変数に代入して呼ぶ               [C0]
//   E. static fn をコールバック引数として渡す             [C0]
//   F. instance fn と static fn の併用                    [C1]
//
// カバレッジ観点:
//   C0: 全パスを少なくとも1回実行
//   C1: F の分岐（正値/負値）を両方実行
// ============================================================

// ----------------------------------------------------------
// A/B/C. 基本コンストラクタ系 struct
// ----------------------------------------------------------
struct Counter {
    value: i32;
}

impl Counter {
    static fn new() -> Counter {
        return Counter { value: 0 };
    }

    static fn with_value(v: i32) -> Counter {
        return Counter { value: v };
    }

    // C. 同 struct の他 static fn を呼ぶ
    static fn default_max() -> i32 {
        return 100;
    }

    static fn bounded() -> Counter {
        let max = Counter::default_max();
        return Counter { value: max };
    }

    fn increment(self) {
        self.value = self.value + 1;
    }

    fn get(self) -> i32 {
        return self.value;
    }
}

// ----------------------------------------------------------
// E. コールバック用
// ----------------------------------------------------------
struct Point {
    x: i32;
    y: i32;
}

impl Point {
    static fn origin() -> Point {
        return Point { x: 0, y: 0 };
    }

    static fn unit_x() -> Point {
        return Point { x: 1, y: 0 };
    }
}

fn make_point(factory: fn() -> Point) -> Point {
    return factory();
}

// ----------------------------------------------------------
// F. 引数によって static/instance を切り替え
// ----------------------------------------------------------
struct Signed {
    value: i32;
}

impl Signed {
    static fn positive() -> Signed {
        return Signed { value: 1 };
    }

    static fn negative() -> Signed {
        return Signed { value: -1 };
    }

    fn get(self) -> i32 {
        return self.value;
    }
}

fn get_signed(positive: bool) -> Signed {
    if (positive) {
        return Signed::positive();
    }
    return Signed::negative();
}

// ----------------------------------------------------------
// main
// ----------------------------------------------------------
fn main() -> i32 {
    println("=== 23: Static fn ===");

    // ----------------------------------------------------------
    // A. 基本的な static fn 呼び出し
    // ----------------------------------------------------------
    println("--- A: Basic static fn ---");
    let c = Counter::new();
    println("new().value={}", c.value);        // 0

    let c2 = Counter::with_value(42);
    println("with_value(42)={}", c2.value);    // 42

    // ----------------------------------------------------------
    // B. static fn が struct を返す（コンストラクタパターン）
    // ----------------------------------------------------------
    println("--- B: Constructor pattern ---");
    let b = Counter::with_value(10);
    b.increment();
    b.increment();
    println("after 2 increments={}", b.get()); // 12

    // ----------------------------------------------------------
    // C. 同 struct の他 static fn を呼ぶ
    // ----------------------------------------------------------
    println("--- C: static fn calls static fn ---");
    let max = Counter::default_max();
    println("default_max={}", max);            // 100

    let bd = Counter::bounded();
    println("bounded().value={}", bd.value);   // 100

    // ----------------------------------------------------------
    // D. static fn を fn 型変数に代入
    // ----------------------------------------------------------
    println("--- D: fn type variable ---");
    let f: fn() -> Counter = Counter::new;
    let d = f();
    println("f().value={}", d.value);          // 0

    let g: fn(i32) -> Counter = Counter::with_value;
    let d2 = g(99);
    println("g(99).value={}", d2.value);       // 99

    // ----------------------------------------------------------
    // E. static fn をコールバックとして渡す
    // ----------------------------------------------------------
    println("--- E: Callback ---");
    let p1 = make_point(Point::origin);
    println("origin.x={}", p1.x);              // 0
    println("origin.y={}", p1.y);              // 0

    let p2 = make_point(Point::unit_x);
    println("unit_x.x={}", p2.x);              // 1
    println("unit_x.y={}", p2.y);              // 0

    // ----------------------------------------------------------
    // F. 分岐で static fn を使い分け [C1]
    // ----------------------------------------------------------
    println("--- F: Branch C1 ---");
    let s1 = get_signed(true);
    println("positive={}", s1.get());          // 1

    let s2 = get_signed(false);
    println("negative={}", s2.get());          // -1

    return 0;
}
