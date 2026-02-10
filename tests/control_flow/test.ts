// control_flow_test.ts
function testControlFlow() {
    for (let i = 0; i < 10; i++) {
        // Yield statement
        function* testYield() {
            yield 1;
            yield 2;
            yield 3;
        }

        // Continue statement
        if (i % 2 === 0) {
            continue;
        }

        // Try-catch-finally statement
        try {
            let x = 10;
            let y = x / 2;
        } catch (e) {
            console.log(e);
        } finally {
            console.log("Finally block executed");
        }

        // Break statement
        if (i === 7) {
            break;
        }

        console.log(i);
    }
}
