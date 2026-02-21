// ============================================================
// Test 14: Branch Coverage Tests
//   Spec: doc/UNIT_TEST_SPEC.md §4.2
//   Focus : C0 instruction coverage / C1 branch coverage / MC/DC
//
// Target functions:
//   classify(n)   - if/else if/else full path coverage (C1)
//   logic_and(a,b)- && compound condition MC/DC
//   logic_or(a,b) - || compound condition MC/DC
//   cmp_ops(a,b)  - all comparison operators true/false path coverage (C1)
// ============================================================

// --- classify: n>0 -> 1, n<0 -> -1, n==0 -> 0 ---
fn classify(n: i32) -> i32 {
    if (n > 0) {
        return 1;
    } else if (n < 0) {
        return -1;
    } else {
        return 0;
    }
}

// --- logic_and: (a>0) && (b>0) ---
fn logic_and(a: i32, b: i32) -> i32 {
    if ((a > 0) && (b > 0)) {
        return 1;
    } else {
        return 0;
    }
}

// --- logic_or: (a>0) || (b>0) ---
fn logic_or(a: i32, b: i32) -> i32 {
    if ((a > 0) || (b > 0)) {
        return 1;
    } else {
        return 0;
    }
}

fn main() -> i32 {
    println("=== 14: Branch Coverage Tests ===");

    // ----------------------------------------------------------
    // classify function - C1 branch coverage
    // branch1 (n>0): T14-01: n= 1          -> 1 (positive)
    //                T14-02: n= 0          -> falls through to else
    // branch2 (n<0): T14-03: n=-1          -> -1 (negative)
    //                T14-04: n= 0          -> 0 (zero)
    // boundary ext:  T14-05: n= 2147483647 -> 1 (i32 max)
    //                T14-06: n=-2147483648 -> -1 (i32 min)
    // ----------------------------------------------------------
    println("--- classify (C1) ---");

    // T14-01: boundary+1 direction (positive minimum) -> true branch taken
    let c1: i32 = classify(1);
    println("classify(1)={}", c1);

    // T14-02 / T14-04: zero (boundary) -> branch1=false, branch2=false -> else
    let c2: i32 = classify(0);
    println("classify(0)={}", c2);

    // T14-03: boundary-1 direction (negative maximum) -> branch1=false, branch2=true
    let c3: i32 = classify(-1);
    println("classify(-1)={}", c3);

    // T14-05: i32 max value -> positive
    let c4: i32 = classify(2147483647);
    println("classify(i32_max)={}", c4);

    // T14-06: i32 min value -> negative
    let c5: i32 = classify(-2147483648);
    println("classify(i32_min)={}", c5);

    // ----------------------------------------------------------
    // logic_and - MC/DC
    // A=(a>0), B=(b>0), D= A&&B
    //
    // T14-07: a= 1, b= 1  -> A=T B=T D=1  baseline
    // T14-08: a= 1, b= 0  -> A=T B=F D=0  B independence check (D changes vs T14-07)
    // T14-09: a= 0, b= 1  -> A=F B=T D=0  A independence check (D changes vs T14-07)
    // T14-10: a= 0, b= 0  -> A=F B=F D=0  C1 complement
    // T14-11: a= 0, b=-1  -> A=F B=F D=0  negative input check (nominal)
    // MC/DC achieved: {T14-07,T14-08} for B / {T14-07,T14-09} for A
    // ----------------------------------------------------------
    println("--- logic_and (MC/DC) ---");

    // T14-07: TT -> 1
    let a1: i32 = logic_and(1, 1);
    println("and(1,1)={}", a1);

    // T14-08: TF -> 0  [B independence check]
    let a2: i32 = logic_and(1, 0);
    println("and(1,0)={}", a2);

    // T14-09: FT -> 0  [A independence check]
    let a3: i32 = logic_and(0, 1);
    println("and(0,1)={}", a3);

    // T14-10: FF -> 0  [C1 complement]
    let a4: i32 = logic_and(0, 0);
    println("and(0,0)={}", a4);

    // T14-11: negative input -> 0
    let a5: i32 = logic_and(0, -1);
    println("and(0,-1)={}", a5);

    // ----------------------------------------------------------
    // logic_or - MC/DC
    // A=(a>0), B=(b>0), D= A||B
    //
    // T14-12: a= 0, b= 0  -> A=F B=F D=0  baseline
    // T14-13: a= 1, b= 0  -> A=T B=F D=1  A independence check (D changes vs T14-12)
    // T14-14: a= 0, b= 1  -> A=F B=T D=1  B independence check (D changes vs T14-12)
    // T14-15: a= 1, b= 1  -> A=T B=T D=1  C1 complement
    // MC/DC achieved: {T14-12,T14-13} for A / {T14-12,T14-14} for B
    // ----------------------------------------------------------
    println("--- logic_or (MC/DC) ---");

    // T14-12: FF -> 0 baseline
    let o1: i32 = logic_or(0, 0);
    println("or(0,0)={}", o1);

    // T14-13: TF -> 1 [A independence check]
    let o2: i32 = logic_or(1, 0);
    println("or(1,0)={}", o2);

    // T14-14: FT -> 1 [B independence check]
    let o3: i32 = logic_or(0, 1);
    println("or(0,1)={}", o3);

    // T14-15: TT -> 1 [C1 complement]
    let o4: i32 = logic_or(1, 1);
    println("or(1,1)={}", o4);

    // ----------------------------------------------------------
    // Comparison operators C1 coverage
    // Execute both true and false paths for each operator
    // T14-16 to T14-27 (true/false once each per operator)
    // ----------------------------------------------------------
    println("--- Comparison Operators C1 ---");
    let va: i32 = 5;
    let vb: i32 = 5;
    let vc: i32 = 6;

    // == true path (T14-16) / false path (T14-17)
    if (va == vb) { println("eq_true"); }  else { println("eq_false"); }
    if (va == vc) { println("eq_true"); }  else { println("eq_false"); }

    // != true path (T14-18) / false path (T14-19)
    if (va != vc) { println("ne_true"); }  else { println("ne_false"); }
    if (va != vb) { println("ne_true"); }  else { println("ne_false"); }

    // < true path (T14-20) / false path (T14-21)
    if (va < vc) { println("lt_true"); }   else { println("lt_false"); }
    if (va < vb) { println("lt_true"); }   else { println("lt_false"); }

    // <= true path (T14-22) / false path (T14-23)
    if (va <= vb) { println("le_true"); }  else { println("le_false"); }
    if (vc <= va) { println("le_true"); }  else { println("le_false"); }

    // > true path (T14-24) / false path (T14-25)
    if (vc > va) { println("gt_true"); }   else { println("gt_false"); }
    if (va > vb) { println("gt_true"); }   else { println("gt_false"); }

    // >= true path (T14-26) / false path (T14-27)
    if (va >= vb) { println("ge_true"); }  else { println("ge_false"); }
    if (va >= vc) { println("ge_true"); }  else { println("ge_false"); }

    return 0;
}
