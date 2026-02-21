// ============================================================
// Test 13: Numeric Type Boundary Tests
//   Spec: doc/UNIT_TEST_SPEC.md §4.1
//   Focus : C0 instruction coverage / boundary value analysis
//           min / min+1 / nominal(zero) / max-1 / max
// ============================================================

fn main() -> i32 {
    println("=== 13: Numeric Type Boundary Tests ===");

    // ----------------------------------------------------------
    // i8 type  range: -128 to 127
    // T13-01: min             -128
    // T13-02: min+1           -127
    // T13-03: nominal (zero)     0
    // T13-04: max-1            126
    // T13-05: max              127
    // T13-N1: min-1 (-129) -> N/A: out of i8 range, C UB (doc §6.1)
    // T13-N2: max+1 ( 128) -> N/A: out of i8 range, C UB (doc §6.1)
    // ----------------------------------------------------------
    println("--- i8 ---");
    let i8_min:  i8 = -128(i8);
    let i8_min1: i8 = -127(i8);
    let i8_zero: i8 =    0(i8);
    let i8_max1: i8 =  126(i8);
    let i8_max:  i8 =  127(i8);
    println("i8_min={}", i8_min);
    println("i8_min1={}", i8_min1);
    println("i8_zero={}", i8_zero);
    println("i8_max1={}", i8_max1);
    println("i8_max={}", i8_max);

    // ----------------------------------------------------------
    // u8 type  range: 0 to 255
    // T13-06: min             0
    // T13-07: min+1           1
    // T13-08: nominal (mid) 127
    // T13-09: max-1         254
    // T13-10: max           255
    // T13-N3: min-1 (-1)  -> N/A: out of u8 range (doc §6.1)
    // T13-N4: max+1 (256) -> N/A: out of u8 range (doc §6.1)
    // ----------------------------------------------------------
    println("--- u8 ---");
    let u8_min:  u8 =   0(u8);
    let u8_min1: u8 =   1(u8);
    let u8_mid:  u8 = 127(u8);
    let u8_max1: u8 = 254(u8);
    let u8_max:  u8 = 255(u8);
    println("u8_min={}", u8_min);
    println("u8_min1={}", u8_min1);
    println("u8_mid={}", u8_mid);
    println("u8_max1={}", u8_max1);
    println("u8_max={}", u8_max);

    // ----------------------------------------------------------
    // i16 type  range: -32768 to 32767
    // T13-11: min           -32768
    // T13-12: min+1         -32767
    // T13-13: nominal (zero)     0
    // T13-14: max-1          32766
    // T13-15: max            32767
    // ----------------------------------------------------------
    println("--- i16 ---");
    let i16_min:  i16 = -32768(i16);
    let i16_min1: i16 = -32767(i16);
    let i16_zero: i16 =      0(i16);
    let i16_max1: i16 =  32766(i16);
    let i16_max:  i16 =  32767(i16);
    println("i16_min={}", i16_min);
    println("i16_min1={}", i16_min1);
    println("i16_zero={}", i16_zero);
    println("i16_max1={}", i16_max1);
    println("i16_max={}", i16_max);

    // ----------------------------------------------------------
    // i32 type  range: -2147483648 to 2147483647
    // T13-16: min           -2147483648
    // T13-17: min+1         -2147483647
    // T13-18: nominal (zero)           0
    // T13-19: max-1          2147483646
    // T13-20: max            2147483647
    // ----------------------------------------------------------
    println("--- i32 ---");
    let i32_min:  i32 = -2147483648;
    let i32_min1: i32 = -2147483647;
    let i32_zero: i32 = 0;
    let i32_max1: i32 = 2147483646;
    let i32_max:  i32 = 2147483647;
    println("i32_min={}", i32_min);
    println("i32_min1={}", i32_min1);
    println("i32_zero={}", i32_zero);
    println("i32_max1={}", i32_max1);
    println("i32_max={}", i32_max);

    // ----------------------------------------------------------
    // i64 type
    // T13-N5: all boundary values -> C Native N/A
    //         Reason: CodeGenerator uses %d (32-bit) format for i64 output
    //                 Python Interpreter works correctly; verified there only
    // ----------------------------------------------------------
    println("--- i64 (Python only) ---");
    let i64_val: i64 = 9999999999(i64);
    println("i64_val={}", i64_val);
    // [!] C Native SKIP: %d 32-bit truncation yields 1410065407 (§6.2)

    // ----------------------------------------------------------
    // Arithmetic boundary values (i32)
    // T13-21: nominal  add  1 + 1          = 2
    // T13-22: boundary add  2147483646 + 1 = 2147483647
    // T13-23: nominal  sub  0 - 1          = -1
    // T13-24: boundary sub -2147483647 - 1 = -2147483648
    // T13-25: nominal  mul  100 * 100      = 10000
    // T13-26: nominal  div  10 / 3         = 3 (truncate)
    // T13-27: boundary div  1 / 1          = 1
    // T13-28: nominal  mod  10 % 3         = 1
    // T13-29: boundary mod  7 % 7          = 0
    // T13-N6: zero division -> N/A: UB/SIGFPE (doc §6.3)
    // T13-N7: MAX + 1       -> N/A: signed overflow UB (doc §6.4)
    // ----------------------------------------------------------
    println("--- Arithmetic ---");
    let add1:  i32 = 1 + 1;
    let add2:  i32 = 2147483646 + 1;
    let sub1:  i32 = 0 - 1;
    let sub2:  i32 = -2147483647 - 1;
    let mul1:  i32 = 100 * 100;
    let div1:  i32 = 10 / 3;
    let div2:  i32 = 1 / 1;
    let mod1:  i32 = 10 % 3;
    let mod2:  i32 = 7 % 7;
    println("add 1+1={}", add1);
    println("add MAX-1+1={}", add2);
    println("sub 0-1={}", sub1);
    println("sub MIN+1-1={}", sub2);
    println("mul 100*100={}", mul1);
    println("div 10/3={}", div1);
    println("div 1/1={}", div2);
    println("mod 10%3={}", mod1);
    println("mod 7%7={}", mod2);

    return 0;
}
