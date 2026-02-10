// try.ts
function testTry() {
    try {
        let x = 10;
        let y = x / 2;
    } catch (e) {
        console.log(e);
    } finally {
        console.log("Finally block executed");
    }
}
