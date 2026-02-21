// ============================================================
// Test 09: const Constants / Conditional Compilation
//   const / #ifdef / #ifndef / #if / #else
// ============================================================

const MAX_VALUE = 100;
const MIN_VALUE = 0;
const PI = 31415;
const DEBUG = 1;
const OPTIMIZATION_LEVEL = 2;
const VERSION = 3;

// derived constants using const
const DOUBLED_MAX = MAX_VALUE * 2;
const HALF_PI = PI / 2;

fn main() -> i32 {
    println("=== 09: const / Conditional Compilation ===");

    // --- const reference ---
    println("--- const ---");
    println("MAX_VALUE={}", MAX_VALUE);     // 100
    println("MIN_VALUE={}", MIN_VALUE);     // 0
    println("DEBUG={}", DEBUG);             // 1
    println("DOUBLED_MAX={}", DOUBLED_MAX); // 200
    println("HALF_PI={}", HALF_PI);         // 15707

    // use const in expressions
    let x: i32 = MAX_VALUE + 50;
    println("MAX+50={}", x);  // 150

    let y: i32 = MAX_VALUE * VERSION;
    println("MAX*VERSION={}", y);  // 300

    // --- #ifdef (defined -> executed) ---
    println("--- #ifdef ---");
    #ifdef DEBUG
    println("DEBUG is defined");   // <- printed
    #endif

    #ifdef OPTIMIZATION_LEVEL
    println("OPT is defined");     // <- printed
    #endif

    // --- #ifdef (not defined -> skipped) ---
    #ifdef PRODUCTION
    println("PRODUCTION defined"); // <- skipped
    #endif

    #ifdef RELEASE
    println("RELEASE defined");    // <- skipped
    #endif

    println("after ifdef");        // <- always printed

    // --- #ifndef (not defined -> executed) ---
    println("--- #ifndef ---");
    #ifndef PRODUCTION
    println("PRODUCTION not defined");  // <- printed
    #endif

    #ifndef RELEASE
    println("RELEASE not defined");     // <- printed
    #endif

    // #ifndef skipped when symbol is defined
    #ifndef DEBUG
    println("DEBUG not defined");   // <- skipped
    #endif

    println("after ifndef");        // <- always printed

    // --- #if (non-zero -> executed) ---
    println("--- #if ---");
    #if DEBUG
    println("DEBUG is truthy");     // <- printed
    #endif

    #if OPTIMIZATION_LEVEL
    println("OPT_LEVEL is truthy"); // <- printed
    #endif

    // #if skipped when value is zero
    #if MIN_VALUE
    println("MIN_VALUE is truthy"); // <- skipped (value is 0)
    #endif

    // --- #if expression evaluation ---
    println("--- #if expr ---");
    #if OPTIMIZATION_LEVEL > 1
    println("OPT_LEVEL > 1");    // <- printed
    #endif

    #if OPTIMIZATION_LEVEL > 5
    println("OPT_LEVEL > 5");    // <- skipped
    #endif

    #if VERSION == 3
    println("VERSION is 3");     // <- printed
    #endif

    #if MAX_VALUE == 100
    println("MAX is 100");       // <- printed
    #endif

    // --- #else ---
    println("--- #else ---");
    #ifdef DEBUG
    println("debug mode");       // <- printed
    #else
    println("release mode");
    #endif

    #ifdef PRODUCTION
    println("production build");
    #else
    println("dev build");        // <- printed
    #endif

    println("=== OK ===");
    return 0;
}
