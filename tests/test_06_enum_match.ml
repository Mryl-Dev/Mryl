// ============================================================
// Test 06: enum (Enumeration) / match expression
// ============================================================

// --- Simple enum (no data) ---
enum Direction {
    North,
    South,
    East,
    West,
}

// --- enum with data ---
enum Shape {
    Circle(f64),
    Rect(f64, f64),
    Triangle(f64, f64, f64),
    Point,
}

// --- nested enum ---
enum Status {
    Active,
    Inactive,
    Pending,
}

fn direction_name(d: Direction) -> string {
    let name: string = match d {
        Direction::North => "North",
        Direction::South => "South",
        Direction::East  => "East",
        Direction::West  => "West",
    };
    return name;
}

fn area(s: Shape) -> f64 {
    let a: f64 = match s {
        Shape::Circle(r)         => r * r * 3.14159,
        Shape::Rect(w, h)        => w * h,
        Shape::Triangle(a, b, c) => (a + b + c) / 2.0,
        Shape::Point             => 0.0,
    };
    return a;
}

fn main() -> i32 {
    println("=== 06: enum / match ===");

    // --- Simple enum ---
    println("--- Simple enum ---");
    let d1 = Direction::North;
    let d2 = Direction::East;
    let d3 = Direction::South;
    let d4 = Direction::West;

    println("{}", direction_name(d1));  // North
    println("{}", direction_name(d2));  // East
    println("{}", direction_name(d3));  // South
    println("{}", direction_name(d4));  // West

    // enum equality comparison
    if (d1 == Direction::North) {
        println("d1 is North");    // <- printed
    }
    if (d1 == Direction::South) {
        println("d1 is South");
    } else {
        println("d1 is not South");  // <- printed
    }

    // --- enum with data ---
    println("--- Data enum ---");
    let s1 = Shape::Circle(3.0);
    let s2 = Shape::Rect(4.0, 5.0);
    let s3 = Shape::Triangle(3.0, 4.0, 5.0);
    let s4 = Shape::Point;

    println("Circle area={}", area(s1));     // 28.274...
    println("Rect area={}", area(s2));       // 20.0
    println("Triangle semi={}", area(s3));   // 6.0
    println("Point area={}", area(s4));      // 0.0

    // --- match as expression assignment ---
    println("--- match as expr ---");
    let st = Status::Active;
    let label: string = match st {
        Status::Active   => "active",
        Status::Inactive => "inactive",
        Status::Pending  => "pending",
    };
    println("status={}", label);   // active

    let st2 = Status::Pending;
    let label2: string = match st2 {
        Status::Active   => "active",
        Status::Inactive => "inactive",
        Status::Pending  => "pending",
    };
    println("status2={}", label2);  // pending

    // --- match on numeric literal ---
    println("--- literal match ---");
    let score = 85;
    let grade: string = match score {
        100 => "perfect",
        90  => "excellent",
        85  => "very good",
        70  => "good",
        n   => "needs work",
    };
    println("grade={}", grade);   // very good

    let code = 0;
    let msg: string = match code {
        0   => "OK",
        404 => "Not Found",
        500 => "Server Error",
        n   => "Unknown",
    };
    println("code 0 -> {}", msg);   // OK

    let code2 = 999;
    let msg2: string = match code2 {
        0   => "OK",
        404 => "Not Found",
        500 => "Server Error",
        n   => "Unknown",
    };
    println("code 999 -> {}", msg2);   // Unknown

    // --- match in loop ---
    println("--- match in loop ---");
    let shapes: i32[] = [0, 1, 2];
    for idx in shapes {
        let name2: string = match idx {
            0 => "circle",
            1 => "rect",
            2 => "triangle",
            n => "other",
        };
        println("{}", name2);
    }
    // circle rect triangle

    println("=== OK ===");
    return 0;
}
