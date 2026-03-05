// ============================================================
// Test 06: enum / match
//   A. 基本 enum 定義バリアント比較
//   B. match 式 (C1: 全アーム網羅)
//   C. データ付き enum バリアント
//   D. デフォルトアーム (n =>) / ワイルドカード相当
//   E. enum フィールドを持つ struct
//
// カバレッジ観点:
//   C0  : 全 enum, 全関数, 全 match アームを少なくとも1回実行
//   C1  :
//     B: dir_to_int() の North/South/East/West の全4アームを実行
//     C: color_code() の Red/Green/Blue/Custom の全4アームを実行
//     D: grade() の 90/80/70/60/default の全5アームを実行
//   MC/DC:
//     is_moving() 内 (d == Direction::North || d == Direction::East)
//       {North=T, *}     true  (North が T で短絡=単独決定)
//       {South=F, E=T}   true  (East が T で単独決定)
//       {South=F, W=F}   false (両方 F で F に決定)
// ============================================================

// ----------------------------------------------------------
// A. 基本 enum (データなし)
// ----------------------------------------------------------
enum Direction {
    North,
    South,
    East,
    West,
}

// ----------------------------------------------------------
// B. match 式 / C1: 全アームを網羅
// ----------------------------------------------------------
fn dir_to_int(d: Direction) -> i32 {
    let v: i32 = match d {
        Direction::North => 0,
        Direction::South => 1,
        Direction::East  => 2,
        Direction::West  => 3,
    };
    return v;
}

// MC/DC: || 条件が独立して結果を決定するケースを網羅
fn is_moving(d: Direction) -> i32 {
    if (d == Direction::North || d == Direction::East) {
        return 1;
    }
    return 0;
}

// ----------------------------------------------------------
// C. データ付き enum バリアント
// ----------------------------------------------------------
enum Color {
    Red,
    Green,
    Blue,
    Custom(i32),
}

fn color_code(c: Color) -> i32 {
    let v: i32 = match c {
        Color::Red        => 1,
        Color::Green      => 2,
        Color::Blue       => 3,
        Color::Custom(n)  => n,
    };
    return v;
}

// ----------------------------------------------------------
// D. デフォルトアーム (n =>) / 数値リテラル match
// ----------------------------------------------------------
fn grade(score: i32) -> i32 {
    let g: i32 = match score {
        90 => 5,
        80 => 4,
        70 => 3,
        60 => 2,
        n  => 1,
    };
    return g;
}

// ----------------------------------------------------------
// E. enum フィールドを持つ struct
// ----------------------------------------------------------
struct Tile {
    x: i32;
    y: i32;
    dir: Direction;
}

// ----------------------------------------------------------
// main
// ----------------------------------------------------------
fn main() -> i32 {
    println("=== 06: enum / match ===");

    // ----------------------------------------------------------
    // A. 基本 enum (C0)
    // ----------------------------------------------------------
    println("--- A: Basic Enum ---");
    let n = Direction::North;
    let s = Direction::South;
    let e = Direction::East;
    let w = Direction::West;

    // enum == 比較
    if (n == Direction::North) {
        println("north ok");        // north ok
    }
    if (s == Direction::North) {
        println("south==north");    // 出力されない
    } else {
        println("south!=north");    // south!=north
    }

    // ----------------------------------------------------------
    // B. match 式 / C1: 全4アーム実行
    // ----------------------------------------------------------
    println("--- B: match C1 ---");
    println("North={}", dir_to_int(n));  // 0
    println("South={}", dir_to_int(s));  // 1
    println("East={}", dir_to_int(e));   // 2
    println("West={}", dir_to_int(w));   // 3

    // MC/DC: (d==North || d==East)
    println("--- B: MC/DC is_moving ---");
    // {North=T, *}  1 (North が T で短絡)
    println("North={}", is_moving(Direction::North));  // 1
    // {South=F, East=T}  1 (East が T で単独決定)
    println("East={}", is_moving(Direction::East));    // 1
    // {South=F, West=F}  0 (両方 F)
    println("South={}", is_moving(Direction::South));  // 0
    // {West=F, West=F}  0
    println("West={}", is_moving(Direction::West));    // 0

    // ----------------------------------------------------------
    // C. データ付き enum / C1: 全4アーム実行
    // ----------------------------------------------------------
    println("--- C: Data Enum ---");
    println("Red={}", color_code(Color::Red));         // 1
    println("Green={}", color_code(Color::Green));     // 2
    println("Blue={}", color_code(Color::Blue));       // 3
    println("Custom={}", color_code(Color::Custom(99)));  // 99

    // ----------------------------------------------------------
    // D. デフォルトアーム / C1: 全5アーム(90/80/70/60/default)実行
    // ----------------------------------------------------------
    println("--- D: Default Arm ---");
    println("90={}", grade(90));   // 5
    println("80={}", grade(80));   // 4
    println("70={}", grade(70));   // 3
    println("60={}", grade(60));   // 2
    println("50={}", grade(50));   // 1 (default arm)
    println("0={}", grade(0));     // 1 (default arm: 二度目)

    // ----------------------------------------------------------
    // E. enum フィールドを持つ struct (C0)
    // ----------------------------------------------------------
    println("--- E: Struct with Enum ---");
    let t = Tile { x: 3, y: 7, dir: Direction::North };
    println("x={}", t.x);                    // 3
    println("y={}", t.y);                    // 7
    println("dir={}", dir_to_int(t.dir));    // 0

    // フィールド更新後の確認
    t.dir = Direction::East;
    println("dir={}", dir_to_int(t.dir));    // 2

    println("=== OK ===");
    return 0;
}
