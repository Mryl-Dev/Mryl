// ============================================================
// Test 08: Arrays
//   Fixed-length Arrays / Dynamic Arrays (T[])
// ============================================================

fn main() -> i32 {
    println("=== 08: Arrays ===");

    // ============================================================
    // Fixed-Length Arrays
    // ============================================================
    println("--- Fixed-Length Arrays ---");

    // no type annotation (inferred from literal)
    let arr = [1, 2, 3, 4, 5];
    println("arr[0]={}", arr[0]);   // 1
    println("arr[4]={}", arr[4]);   // 5

    // element assignment
    arr[2] = 99;
    println("arr[2] after={}", arr[2]);  // 99

    // iterate all elements with for-in
    for v in arr {
        println("{}", v);
    }
    // 1 2 99 4 5

    // float array
    let floats = [1.1, 2.2, 3.3];
    println("floats[1]={}", floats[1]);  // 2.2

    // string array
    let words = ["apple", "banana", "cherry"];
    for w in words {
        println("{}", w);
    }

    // ============================================================
    // Dynamic Arrays (T[])
    // ============================================================
    println("--- Dynamic Arrays ---");

    // declare empty, add with push
    let nums: i32[] = [];
    println("empty is_empty={}", nums.is_empty());  // true
    println("empty len={}", nums.len());            // 0

    nums.push(10);
    nums.push(20);
    nums.push(30);
    println("after 3 push, len={}", nums.len());    // 3
    println("is_empty={}", nums.is_empty());        // false

    // index access
    println("nums[0]={}", nums[0]);   // 10
    println("nums[2]={}", nums[2]);   // 30

    // index assignment
    nums[1] = 99;
    println("nums[1]={}", nums[1]);   // 99

    // pop
    let popped: i32 = nums.pop();
    println("popped={}", popped);       // 30
    println("len after pop={}", nums.len());  // 2

    // insert(index, value)
    nums.insert(0, 5);
    println("after insert(0,5): len={}", nums.len());  // 3
    println("nums[0]={}", nums[0]);    // 5
    println("nums[1]={}", nums[1]);    // 10

    // remove(index)
    let removed: i32 = nums.remove(1);
    println("removed={}", removed);             // 10
    println("len after remove={}", nums.len()); // 2

    // declare with initial values
    let xs: i32[] = [1, 2, 3, 4, 5];
    println("xs len={}", xs.len());    // 5
    println("xs[0]={}", xs[0]);        // 1
    println("xs[4]={}", xs[4]);        // 5

    // for-in (dynamic array)
    println("--- for-in Vec ---");
    for x in xs {
        println("{}", x);
    }
    // 1 2 3 4 5

    // pop all elements with while
    println("--- while pop ---");
    let stack: i32[] = [100, 200, 300];
    while (!stack.is_empty()) {
        let top: i32 = stack.pop();
        println("{}", top);
    }
    // 300 200 100

    // grow array by pushing inside loop
    println("--- grow in loop ---");
    let evens: i32[] = [];
    for n in 0..10 {
        if (n % 2 == 0) {
            evens.push(n);
        }
    }
    println("evens len={}", evens.len());  // 5
    for e in evens {
        println("{}", e);
    }
    // 0 2 4 6 8

    // dynamic string array
    println("--- string Vec ---");
    let tags: string[] = [];
    tags.push("rust");
    tags.push("Mryl");
    tags.push("c");
    println("tags len={}", tags.len());   // 3
    for t in tags {
        println("{}", t);
    }
    // rust Mryl c

    println("=== OK ===");
    return 0;
}
