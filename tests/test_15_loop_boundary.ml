// ============================================================
// Test 15: Loop Boundary Tests
//   Spec: doc/UNIT_TEST_SPEC.md §4.3
//   Focus : C0 instruction coverage / C1 branch coverage / boundary value analysis
//
// Loop types: while / for range / for C-style
// Boundaries: 0 iterations (min) / 1 iteration (min+1) / N iterations (nominal) / 10 (representative max)
//
// Note: inclusive range (0..=N) is not supported (Parser only supports DOTDOT).
//       Use 0..(N+1) instead to verify 0/1/N iteration equivalents.
// ============================================================

fn main() -> i32 {
    println("=== 15: Loop Boundary Tests ===");

    // ----------------------------------------------------------
    // while loop
    // T15-01: 0 iters (min)     - condition false on entry -> body not executed
    // T15-02: 1 iter  (min+1)   - condition true once -> false after 1 execution
    // T15-03: 5 iters (nominal) - 0+1+2+3+4 = 10
    // T15-04: 10 iters (rep max) - 0+...+9 = 45
    // ----------------------------------------------------------
    println("--- while ---");

    // T15-01: 0 iterations (i<0 false on first check -> body skipped)
    let w0: i32 = 0;
    let wi0: i32 = 0;
    while (wi0 < 0) {
        w0 = w0 + wi0;
        wi0++;
    }
    println("while_0iter_sum={}", w0);

    // T15-02: 1 iteration (i<1 -> only 0 executed)
    let w1: i32 = 0;
    let wi1: i32 = 0;
    while (wi1 < 1) {
        w1 = w1 + wi1;
        wi1++;
    }
    println("while_1iter_sum={}", w1);

    // T15-03: 5 iterations (0+1+2+3+4 = 10)
    let w5: i32 = 0;
    let wi5: i32 = 0;
    while (wi5 < 5) {
        w5 = w5 + wi5;
        wi5++;
    }
    println("while_5iter_sum={}", w5);

    // T15-04: 10 iterations (0+...+9 = 45)
    let w10: i32 = 0;
    let wi10: i32 = 0;
    while (wi10 < 10) {
        w10 = w10 + wi10;
        wi10++;
    }
    println("while_10iter_sum={}", w10);

    // ----------------------------------------------------------
    // for range loop (0..N half-open interval)
    // T15-05: 0 iters (0..0 -> body not executed)
    // T15-06: 1 iter  (0..1 -> only 0 executed)
    // T15-07: 5 iters (0..5 -> count=5)
    // ----------------------------------------------------------
    println("--- for range ---");

    // T15-05: 0 iterations
    let fr0: i32 = 0;
    for _n0 in 0..0 {
        fr0 = fr0 + 1;
    }
    println("range_0iter_count={}", fr0);

    // T15-06: 1 iteration
    let fr1: i32 = 0;
    for _n1 in 0..1 {
        fr1 = fr1 + 1;
    }
    println("range_1iter_count={}", fr1);

    // T15-07: 5 iterations
    let fr5: i32 = 0;
    for _n5 in 0..5 {
        fr5 = fr5 + 1;
    }
    println("range_5iter_count={}", fr5);

    // verify sum (0+1+2+3+4 = 10)
    let fr5s: i32 = 0;
    for ns in 0..5 {
        fr5s = fr5s + ns;
    }
    println("range_5iter_sum={}", fr5s);

    // ----------------------------------------------------------
    // for C-style loop
    // T15-09: 0 iters (j<0  -> body not executed)
    // T15-10: 1 iter  (j<1  -> only 0 executed)
    // T15-11: custom step (j+=2, j<=8 -> 0,2,4,6,8 -> 5 steps)
    // ----------------------------------------------------------
    println("--- for C-style ---");

    // T15-09: 0 iterations
    let fc0: i32 = 0;
    for (let j0 = 0; j0 < 0; j0++) {
        fc0 = fc0 + 1;
    }
    println("cfor_0iter_count={}", fc0);

    // T15-10: 1 iteration
    let fc1: i32 = 0;
    for (let j1 = 0; j1 < 1; j1++) {
        fc1 = fc1 + 1;
    }
    println("cfor_1iter_count={}", fc1);

    // T15-11: j=0 to 8 in steps of 2 (0,2,4,6,8) -> 5 iters, last=8
    let fc_last: i32 = -1;
    for (let j2 = 0; j2 <= 8; j2 = j2 + 2) {
        fc_last = j2;
    }
    println("cfor_step2_last={}", fc_last);

    // ----------------------------------------------------------
    // break boundary
    // T15-12: break at n==3 -> last=2 (3 never reached)
    // T15-13: immediate break at n==0 -> count=0 (0 iterations executed)
    // ----------------------------------------------------------
    println("--- break ---");

    // T15-12: verify value just before break
    let br_last: i32 = -1;
    for nb in 0..10 {
        if (nb == 3) { break; }
        br_last = nb;
    }
    println("break_last={}", br_last);

    // T15-13: immediate break (0 iterations executed)
    let br0: i32 = 0;
    for nb0 in 0..10 {
        if (nb0 == 0) { break; }
        br0 = br0 + 1;
    }
    println("break_0iter_count={}", br0);

    // ----------------------------------------------------------
    // continue boundary
    // T15-14: skip even numbers -> count only odd 1,3
    //         (for 0..5 -> odds: 1,3 -> count=2)
    // C1: continue condition true (even) and false (odd) both paths executed
    // ----------------------------------------------------------
    println("--- continue ---");

    let cont: i32 = 0;
    let cont_last: i32 = -1;
    for nc in 0..5 {
        if (nc % 2 == 0) { continue; }
        cont = cont + 1;
        cont_last = nc;
    }
    println("continue_odd_count={}", cont);
    println("continue_last={}", cont_last);

    println("=== OK ===");
    return 0;
}
