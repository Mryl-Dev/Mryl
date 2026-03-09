const TASK_LIMIT = 256;

async fn compute(n: i32) -> i32 {
    return n * 1;
}

async fn task_async(id: i32, val: i32) {
    println("task {} start", id);
    let result = await compute(val);
    println("task {} end  -> {}", id, result);
}

fn main() {
    // Schedule a large number of tasks to test the scheduler's capacity
    for (let i = 0; i < TASK_LIMIT; i++) {
        let t = task_async(i, i * 10);
        await t;
    }
    
    // Alternatively, we can use a while loop to schedule tasks
    let j = 0;
    while (j < TASK_LIMIT) {
        let t = task_async(j, j * 10);
        await t;
        j++;
    }
}