// ============================================================
// Test 09: const / 条件コンパイル (#ifdef / #ifndef / #if / #else)
//   A. const 定義参照算術式
//   B. #ifdef (定義あり実行 / 定義なしスキップ) - C1
//   C. #ifndef (定義なし実行 / 定義ありスキップ) - C1
//   D. #if 値評価 (非零実行 / 零スキップ) - C1
//   E. #if 式評価 + #else + 複合条件 - C1 + MC/DC
//
// カバレッジ観点:
//   C0  : 全 const, 全ディレクティブを少なくとも1回評価
//   C1  :
//     B: #ifdef  taken / not-taken 両ケース
//     C: #ifndef  taken / not-taken 両ケース
//     D: #if 値  非零(実行) / 零(スキップ) 両ケース
//     E: #if 式  true / false 両ケース
//     E: #else  #ifdef taken 時と not-taken 時 両ケース
//   MC/DC:
//     E: #if (OPTIMIZATION_LEVEL > 1 && DEBUG):
//       {OPT>5=F, DEBUG=T}  skip (OPT>5=F が単独決定)
//       {OPT>1=T, MIN=F}    skip (MIN=F が単独決定)
//       {OPT>1=T, DEBUG=T}  taken (両方 T)
// ============================================================

const MAX_VALUE = 100;
const MIN_VALUE = 0;
const PI = 31415;
const DEBUG = 1;
const OPTIMIZATION_LEVEL = 2;
const VERSION = 3;

const DOUBLED_MAX = MAX_VALUE * 2;
const HALF_PI = PI / 2;

fn main() -> i32 {
    println("=== 09: const / Compile Conditions ===");

    // ----------------------------------------------------------
    // A. const 参照算術式 (C0)
    // ----------------------------------------------------------
    println("--- A: const ---");
    println("MAX={}", MAX_VALUE);       // 100
    println("MIN={}", MIN_VALUE);       // 0
    println("DEBUG={}", DEBUG);         // 1
    println("DOUBLED={}", DOUBLED_MAX); // 200
    println("HALF_PI={}", HALF_PI);     // 15707

    let x: i32 = MAX_VALUE + 50;
    println("MAX+50={}", x);            // 150
    let y: i32 = MAX_VALUE * VERSION;
    println("MAX*VER={}", y);           // 300

    // ----------------------------------------------------------
    // B. #ifdef  C1: taken / not-taken
    // ----------------------------------------------------------
    println("--- B: #ifdef ---");

    // C1: taken (DEBUG は定義済み)
    #ifdef DEBUG
    println("DEBUG defined");           // DEBUG defined
    #endif

    // C1: taken (OPTIMIZATION_LEVEL は定義済み)
    #ifdef OPTIMIZATION_LEVEL
    println("OPT defined");             // OPT defined
    #endif

    // C1: not-taken (PRODUCTION は未定義)
    #ifdef PRODUCTION
    println("PRODUCTION defined");      // スキップ
    #endif

    // C1: not-taken (RELEASE は未定義)
    #ifdef RELEASE
    println("RELEASE defined");         // スキップ
    #endif

    println("after ifdef");             // after ifdef

    // ----------------------------------------------------------
    // C. #ifndef  C1: taken / not-taken
    // ----------------------------------------------------------
    println("--- C: #ifndef ---");

    // C1: taken (PRODUCTION は未定義)
    #ifndef PRODUCTION
    println("PRODUCTION not def");      // PRODUCTION not def
    #endif

    // C1: taken (RELEASE は未定義)
    #ifndef RELEASE
    println("RELEASE not def");         // RELEASE not def
    #endif

    // C1: not-taken (DEBUG は定義済み)
    #ifndef DEBUG
    println("DEBUG not def");           // スキップ
    #endif

    println("after ifndef");            // after ifndef

    // ----------------------------------------------------------
    // D. #if 値評価  C1: 非零/零
    // ----------------------------------------------------------
    println("--- D: #if value ---");

    // C1: 非零実行 (DEBUG=1)
    #if DEBUG
    println("DEBUG truthy");            // DEBUG truthy
    #endif

    // C1: 非零実行 (OPTIMIZATION_LEVEL=2)
    #if OPTIMIZATION_LEVEL
    println("OPT truthy");              // OPT truthy
    #endif

    // C1: 零スキップ (MIN_VALUE=0)
    #if MIN_VALUE
    println("MIN truthy");              // スキップ
    #endif

    println("after if-value");          // after if-value

    // ----------------------------------------------------------
    // E. #if 式評価 / #else / MC/DC
    // ----------------------------------------------------------
    println("--- E: #if expr + #else ---");

    // C1: true (OPTIMIZATION_LEVEL=2 > 1)
    #if OPTIMIZATION_LEVEL > 1
    println("OPT>1 ok");                // OPT>1 ok
    #endif

    // C1: false (OPTIMIZATION_LEVEL=2 > 5)
    #if OPTIMIZATION_LEVEL > 5
    println("OPT>5 ok");                // スキップ
    #endif

    // C1: true (VERSION==3)
    #if VERSION == 3
    println("VER==3");                  // VER==3
    #endif

    // C1: true (MAX_VALUE==100)
    #if MAX_VALUE == 100
    println("MAX==100");                // MAX==100
    #endif

    // C1 #else: #ifdef taken  #else スキップ
    #ifdef DEBUG
    println("debug mode");              // debug mode
    #else
    println("release mode");            // スキップ
    #endif

    // C1 #else: #ifdef not-taken  #else 実行
    #ifdef PRODUCTION
    println("production build");        // スキップ
    #else
    println("dev build");               // dev build
    #endif

    // MC/DC: #if (OPTIMIZATION_LEVEL > 1 && DEBUG)
    // {OPT>5=F, DEBUG=T}  not-taken (OPT>5=F が単独決定)
    #if OPTIMIZATION_LEVEL > 5 && DEBUG
    println("opt>5 and debug");         // スキップ
    #endif

    // {OPT>1=T, MIN=F (0)}  not-taken (MIN=F が単独決定)
    #if OPTIMIZATION_LEVEL > 1 && MIN_VALUE
    println("opt>1 and min");           // スキップ
    #endif

    // {OPT>1=T, DEBUG=T}  taken (両方 T)
    #if OPTIMIZATION_LEVEL > 1 && DEBUG
    println("opt>1 and debug");         // opt>1 and debug
    #endif

    println("=== OK ===");
    return 0;
}
