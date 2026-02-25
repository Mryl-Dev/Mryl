// ============================================================
// Test 19: ネスト struct / struct 配列 / 複合データ構造
//   A. Vec2 struct + Segment (フラットフィールドでネスト相当) / C0
//   B. struct の配列 (Array of struct) / C0
//   C. Rect メソッド / C0+C1
//   D. for ループで struct 配列走査 / C0
//   E. struct フィールド条件 MC/DC
//
// カバレッジ観点:
//   C0  : 全セクションの文が少なくとも1回実行される
//   C1  :
//     C: is_square() の true / false 両ブランチ
//   MC/DC (E):
//     is_in_box(px, py, bx, by) 内 (px >= bx && py >= by):
//       {px>=bx=F, *}         0
//       {px>=bx=T, py>=by=F}  0
//       {px>=bx=T, py>=by=T}  1
// ============================================================

// ----------------------------------------------------------
// A. Vec2 struct (基本的な 2D 座標)
// ----------------------------------------------------------
struct Vec2 {
    x: i32;
    y: i32;
}

impl Vec2 {
    fn sum(self) -> i32 {
        return self.x + self.y;
    }
}

// ----------------------------------------------------------
// A. Segment struct (開始終端を平坦フィールドで保持)
// ----------------------------------------------------------
struct Segment {
    sx: i32;
    sy: i32;
    ex: i32;
    ey: i32;
}

impl Segment {
    fn length_approx(self) -> i32 {
        let dx = self.ex - self.sx;
        let dy = self.ey - self.sy;
        if (dx < 0) { dx = 0 - dx; }
        if (dy < 0) { dy = 0 - dy; }
        return dx + dy;
    }
}

// ----------------------------------------------------------
// B. Score struct (struct 配列用)
// ----------------------------------------------------------
struct Score {
    value: i32;
    bonus: i32;
}

fn total_score(s: Score) -> i32 {
    return s.value + s.bonus;
}

// ----------------------------------------------------------
// C. Rect struct (C1 対象メソッド付き)
// ----------------------------------------------------------
struct Rect {
    ox: i32;
    oy: i32;
    width: i32;
    height: i32;
}

impl Rect {
    fn area(self) -> i32 {
        return self.width * self.height;
    }
    fn is_square(self) -> i32 {
        if (self.width == self.height) {
            return 1;
        }
        return 0;
    }
    fn perimeter(self) -> i32 {
        return 2 * (self.width + self.height);
    }
}

// ----------------------------------------------------------
// E. MC/DC ヘルパー
// ----------------------------------------------------------
fn is_in_box(px: i32, py: i32, bx: i32, by: i32) -> i32 {
    if (px >= bx && py >= by) {
        return 1;
    }
    return 0;
}

// ----------------------------------------------------------
// main
// ----------------------------------------------------------
fn main() -> i32 {
    println("=== 19: Nested Struct & Composite ===");

    // ----------------------------------------------------------
    // A. Vec2 + Segment / C0
    // ----------------------------------------------------------
    println("--- A: Vec2 + Segment ---");

    let v1 = Vec2 { x: 3, y: 4 };
    println("v1.x={}", v1.x);        // 3
    println("v1.y={}", v1.y);        // 4
    println("v1.sum={}", v1.sum());   // 7

    let v2 = Vec2 { x: 0, y: 0 };
    println("v2.sum={}", v2.sum());   // 0

    let seg = Segment { sx: 0, sy: 0, ex: 3, ey: 4 };
    println("seg.sx={}", seg.sx);                      // 0
    println("seg.ey={}", seg.ey);                      // 4
    println("seg.len={}", seg.length_approx());        // 7

    let seg2 = Segment { sx: 1, sy: 2, ex: 4, ey: 6 };
    println("seg2.len={}", seg2.length_approx());      // 7

    let seg3 = Segment { sx: 4, sy: 4, ex: 1, ey: 2 };
    println("seg3.len={}", seg3.length_approx());      // 5

    // ----------------------------------------------------------
    // B. Score 配列 / C0
    // ----------------------------------------------------------
    println("--- B: Struct array ---");

    let scores: Score[3] = [
        Score { value: 10, bonus: 5 },
        Score { value: 20, bonus: 0 },
        Score { value: 15, bonus: 3 }
    ];

    println("score[0].value={}", scores[0].value);          // 10
    println("score[0].bonus={}", scores[0].bonus);          // 5
    println("score[0].total={}", total_score(scores[0]));   // 15
    println("score[1].total={}", total_score(scores[1]));   // 20
    println("score[2].total={}", total_score(scores[2]));   // 18

    scores[0].value = 99;
    println("score[0].updated={}", scores[0].value);        // 99

    // ----------------------------------------------------------
    // C. Rect メソッド / C0 + C1
    // ----------------------------------------------------------
    println("--- C: Rect methods ---");

    let r1 = Rect { ox: 0, oy: 0, width: 4, height: 4 };
    println("r1.area={}", r1.area());             // 16
    println("r1.is_square={}", r1.is_square());   // 1  (C1: true)
    println("r1.perim={}", r1.perimeter());        // 16

    let r2 = Rect { ox: 1, oy: 2, width: 3, height: 5 };
    println("r2.area={}", r2.area());             // 15
    println("r2.is_square={}", r2.is_square());   // 0  (C1: false)
    println("r2.perim={}", r2.perimeter());        // 16

    let r3 = Rect { ox: 0, oy: 0, width: 1, height: 1 };
    println("r3.area={}", r3.area());             // 1
    println("r3.is_square={}", r3.is_square());   // 1

    // ----------------------------------------------------------
    // D. for-in で struct 配列走査 / C0
    // ----------------------------------------------------------
    println("--- D: for-in struct array ---");

    let totals = 0;
    for s in scores {
        totals = totals + total_score(s);
    }
    // scores更新後: [99+5=104, 20, 18]  total=142
    println("sum_totals={}", totals);    // 142

    // ----------------------------------------------------------
    // E. MC/DC: is_in_box(px, py, bx, by)
    //    (px >= bx && py >= by)
    // ----------------------------------------------------------
    println("--- E: MC/DC ---");

    // {px>=bx=F, *}  0
    println("inbox(0,5,1,1)={}", is_in_box(0, 5, 1, 1));  // 0

    // {px>=bx=T, py>=by=F}  0
    println("inbox(5,0,1,1)={}", is_in_box(5, 0, 1, 1));  // 0

    // {px>=bx=T, py>=by=T}  1
    println("inbox(5,5,1,1)={}", is_in_box(5, 5, 1, 1));  // 1

    // 境界値 (equal): both true
    println("inbox(1,1,1,1)={}", is_in_box(1, 1, 1, 1));  // 1

    // struct フィールドを引数として渡す
    let p = Vec2 { x: 3, y: 7 };
    let origin = Vec2 { x: 0, y: 5 };
    println("inbox(p,org)={}", is_in_box(p.x, p.y, origin.x, origin.y));   // 1

    let p2 = Vec2 { x: 3, y: 4 };
    println("inbox(p2,org)={}", is_in_box(p2.x, p2.y, origin.x, origin.y)); // 0  (4>=5 false)

    println("=== OK ===");
    return 0;
}

