// ============================================================
// Test 02: Operators
//   Arithmetic / Comparison / Logical / Bitwise / Compound Assignment / Increment
// ============================================================

fn main() -> i32 {
    println("=== 02: Operators ===");

    // --- Arithmetic ---
    println("--- Arithmetic ---");
    let a = 10;
    let b = 3;
    println("10+3={}", a + b);    // 13
    println("10-3={}", a - b);    // 7
    println("10*3={}", a * b);    // 30
    println("10/3={}", a / b);    // 3 (integer division)
    println("10%3={}", a % b);    // 1

    let fa = 10.0;
    let fb = 3.0;
    println("10.0/3.0={}", fa / fb);  // 3.333...

    // --- Comparison ---
    println("--- Comparison ---");
    println("5<10={}", 5 < 10);      // true
    println("5<=5={}", 5 <= 5);      // true
    println("10>5={}", 10 > 5);      // true
    println("10>=10={}", 10 >= 10);  // true
    println("5==5={}", 5 == 5);      // true
    println("5!=10={}", 5 != 10);    // true
    println("3>5={}", 3 > 5);        // false

    // --- Logical ---
    println("--- Logical ---");
    println("true||false={}", true || false);   // true
    println("true&&true={}", true && true);     // true
    println("true&&false={}", true && false);   // false
    println("!true={}", !true);                 // false
    println("!false={}", !false);               // true

    // short-circuit evaluation
    let x = 5;
    println("x>0&&x<10={}", x > 0 && x < 10);  // true
    println("x<0||x>3={}", x < 0 || x > 3);    // true

    // --- Bitwise ---
    println("--- Bitwise ---");
    let bx = 5;  // 0101
    let by = 3;  // 0011
    println("5&3={}", bx & by);    // 1 (0001)
    println("5|3={}", bx | by);    // 7 (0111)
    println("5^3={}", bx ^ by);    // 6 (0110)
    println("5<<1={}", bx << 1);   // 10
    println("5>>1={}", bx >> 1);   // 2

    // --- Compound Assignment ---
    println("--- Compound Assignment ---");
    let n = 10;
    n += 5;    println("+=: {}", n);   // 15
    n -= 3;    println("-=: {}", n);   // 12
    n *= 2;    println("*=: {}", n);   // 24
    n /= 3;    println("/=: {}", n);   // 8
    n %= 5;    println("%%=: {}", n);  // 3

    let m = 8;
    m <<= 1;   println("<<=: {}", m);  // 16
    m >>= 2;   println(">>=: {}", m);  // 4

    let k = 12;
    k ^= 5;   println("^=: {}", k);   // 9

    // --- Increment/Decrement ---
    println("--- Increment/Decrement ---");
    let i = 5;
    i++;
    println("i++ -> {}", i);       // 6
    ++i;
    println("++i -> {}", i);       // 7
    i--;
    println("i-- -> {}", i);       // 6
    --i;
    println("--i -> {}", i);       // 5

    // post-increment: use current value then increment
    let j = 0;
    let r1 = j++;
    println("j++ returns {} (j={})", r1, j);   // 0, 1

    // pre-increment: increment then use new value
    let r2 = ++j;
    println("++j returns {} (j={})", r2, j);   // 2, 2

    // --- Operator Precedence ---
    println("--- Precedence ---");
    println("2+3*4={}", 2 + 3 * 4);          // 14
    println("(2+3)*4={}", (2 + 3) * 4);      // 20
    println("10-2*3={}", 10 - 2 * 3);        // 4
    println("1+2==3={}", 1 + 2 == 3);        // true
    println("!false&&true={}", !false && true); // true

    println("=== OK ===");
    return 0;
}
