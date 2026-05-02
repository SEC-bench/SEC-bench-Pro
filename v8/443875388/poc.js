let kNumYields = 500000;

let body = `
  if ("foo" === "bar") {
    ${"yield* 42;".repeat(kNumYields)}
  }
  try {
    throw 42;
  } catch (e) {
     // Will never get here
  }
`;

const AsyncGeneratorFunction = Object.getPrototypeOf(async function* () { }).constructor;
let bug = new AsyncGeneratorFunction(body);

let r = bug();
r.next();
