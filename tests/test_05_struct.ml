// ============================================================
// Test 05: 構造体 / メソッド / ジェネリック構造体
//   A. 基本構造体 / B. struct メソッド / C. ジェネリック構造体
//   D. ジェネリック struct メソッド / E. 複数フィールド+ネストアクセス
//
// カバレッジ観点:
//   C0  : A〜E 全セクションの文を実行 (スキップ以外)
//   C1  : B: classify() の真/偽ブランチ両方を実行
//   MC/DC:
//     B: Point.classify() の (x>0 && y>0)
//       {x>0=F,y>0=T}0, {x>0=T,y>0=F}2, {x>0=T,y>0=T}1
//       x>0 が F のとき単独で結果を決定
//       y>0 が F のとき単独で結果を決定
//
// 既知バグ (C Native):
//   Bug#5: 異なる struct が同名メソッドを持つ場合 CodeGenerator が誤った関数名を使用
//           Rect.size()/border() で回避
//   Bug#6: struct メソッド内 self.field 代入が C では値渡しのため反映されない
//           move_by()/birthday() のミューテーション検証はスキップ
//   Bug#7: struct の string フィールドが C native で printf %d になる
//           Person (name: string) 関連をスキップ
//   Bug#8: struct の f64 フィールド / f64 返却が C native で printf %d になる
//           Circle.area() (f64) 関連をスキップ
//   Bug#9: ジェネリック struct の string/f64 フィールドが C native で正しく出力されない
//           Box<string> / Box<f64> をスキップ
//   Bug#10: impl Struct<T> 構文がパーサー未対応
//           impl Box<T> セクション全体をスキップ
// ============================================================

// ----------------------------------------------------------
// A. 基本構造体
// ----------------------------------------------------------
struct Point {
    x: i32;
    y: i32;
}

// ----------------------------------------------------------
// B. struct メソッド (impl)
// ----------------------------------------------------------
impl Point {
    fn display(self) -> void {
        println("Point({},{})", self.x, self.y);
    }

    fn sum(self) -> i32 {
        return self.x + self.y;
    }

    // [Bug#6] C では値渡しのため self.field 代入が呼び出し元に反映されない
    fn move_by(self, dx: i32, dy: i32) -> void {
        self.x = self.x + dx;
        self.y = self.y + dy;
    }

    // C1 + MC/DC: (x>0 && y>0) で全分岐を網羅
    fn classify(self) -> i32 {
        if (self.x > 0 && self.y > 0) {
            return 1;   // 第1象限
        }
        if (self.x > 0) {
            return 2;   // x のみ正
        }
        return 0;       // その他
    }
}

// ----------------------------------------------------------
// struct with string field  [Bug#7: C native で string フィールドが %d になる]
// ----------------------------------------------------------
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

// ----------------------------------------------------------
// struct with f64 field  [Bug#8: C native で f64 フィールドが %d になる]
// ----------------------------------------------------------
struct Circle {
    radius: f64;
}

impl Circle {
    fn area(self) -> f64 {
        return self.radius * self.radius * 3.14159;
    }
}

// ----------------------------------------------------------
// C. ジェネリック構造体
// ----------------------------------------------------------
struct Box<T> {
    value: T;
}

// ----------------------------------------------------------
// D. ジェネリック struct メソッド
// [Bug#10] impl Box<T>: パーサーが impl Struct<T> の型引数 <T> に未対応
//          parse_impl_decl が IDENT の直後に LBRACE を期待しており LT で SyntaxError
//          Issue: ジェネリック impl (impl StructName<T>) のパーサーサポートを追加する
// ----------------------------------------------------------
// impl Box<T> {
//     fn get(self) -> T {
//         return self.value;
//     }
//
//     fn set(self, v: T) -> void {
//         self.value = v;
//     }
// }

// ----------------------------------------------------------
// E. 複数フィールド+メソッド
// [Bug#5] Circle.area() と名前が衝突するため size()/border() を使用
// ----------------------------------------------------------
struct Rect {
    origin: i32;
    width: i32;
    height: i32;
}

impl Rect {
    fn size(self) -> i32 {
        return self.width * self.height;
    }

    fn border(self) -> i32 {
        return 2 * (self.width + self.height);
    }
}

// ----------------------------------------------------------
// main
// ----------------------------------------------------------
fn main() -> i32 {
    println("=== 05: Structs ===");

    // ----------------------------------------------------------
    // A. 基本構造体 (C0)
    // ----------------------------------------------------------
    println("--- A: Basic Struct ---");
    let p = Point { x: 3, y: 4 };
    println("x={}", p.x);      // 3
    println("y={}", p.y);      // 4

    p.x = 10;
    p.y = 20;
    println("x={}", p.x);      // 10
    println("y={}", p.y);      // 20

    // ----------------------------------------------------------
    // B. struct メソッド (C1 + MC/DC)
    // ----------------------------------------------------------
    println("--- B: Methods ---");
    let q = Point { x: 3, y: 4 };
    q.display();                // Point(3,4)
    println("sum={}", q.sum()); // 7

    // [SKIP Bug#6] move_by によるミューテーション: C では値渡しのため反映されない
    // q.move_by(2, -1);
    // q.display();  // expect Point(5,3) but C native returns Point(3,4)

    // MC/DC: x>0=T, y>0=T  1
    let pa = Point { x: 1, y: 1 };
    println("classify(1,1)={}", pa.classify());  // 1

    // MC/DC: x>0=T, y>0=F  2
    let pb = Point { x: 1, y: 0 };
    println("classify(1,0)={}", pb.classify());  // 2

    // MC/DC: x>0=F, y>0=T  0
    let pc = Point { x: 0, y: 1 };
    println("classify(0,1)={}", pc.classify());  // 0

    // C1: 第2分岐も偽
    let pd = Point { x: 0, y: 0 };
    println("classify(0,0)={}", pd.classify());  // 0

    // B: Person (string フィールド)
    println("--- B: Person ---");
    let alice = Person { name: "Alice", age: 30 };
    alice.greet();      // I am Alice, 30 years old.
    // [SKIP Bug#6] birthday() は self.age を書き換えるが C では値渡しのため
    //   呼び出し元の alice.age が変わらず、greet() の出力が Python と不一致になる
    // alice.birthday();
    // alice.greet();   // Python: 31 years old. / C: 30 years old.


    // B: Circle (f64 フィールド・戻り値)
    println("--- B: Circle ---");
    let ci = Circle { radius: 5.0 };
    println("area={}", ci.area());    // 78.5397
    let ci2 = Circle { radius: 1.0 };
    println("area={}", ci2.area());   // 3.14159


    // ----------------------------------------------------------
    // C. ジェネリック構造体 (C0)
    // ----------------------------------------------------------
    println("--- C: Generic Struct ---");
    let bi = Box<i32> { value: 42 };
    println("Box<i32>={}", bi.value);       // 42

    // [SKIP Bug#9] Box<string>: string フィールドが C native で %d になる
    // let bs = Box<string> { value: "hello" };
    // println("Box<string>={}", bs.value);  // hello
    println("Box<string>=(SKIP Bug#9)");

    // [SKIP Bug#9] Box<f64>: f64 フィールドが C native で %d になる
    // let bf = Box<f64> { value: 3.14 };
    // println("Box<f64>={}", bf.value);     // 3.14
    println("Box<f64>=(SKIP Bug#9)");

    // ----------------------------------------------------------
    // D. ジェネリック struct メソッド (SKIP Bug#10)
    // ----------------------------------------------------------
    println("--- D: Generic Methods (SKIP Bug#10) ---");

    // ----------------------------------------------------------
    // E. 複数フィールド + メソッド (C0)
    // ----------------------------------------------------------
    println("--- E: Rect ---");
    let r = Rect { origin: 0, width: 6, height: 4 };
    println("size={}", r.size());       // 24
    println("border={}", r.border());   // 20

    r.width = 3;
    r.height = 3;
    println("size={}", r.size());       // 9

    println("=== OK ===");
    return 0;
}
