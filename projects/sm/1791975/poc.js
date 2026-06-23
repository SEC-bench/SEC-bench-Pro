// CVE-2022-45406 / Bugzilla 1791975 — GC sweep of a realm that was
// allocated during the SAME incremental GC pass leaves a poisoned realm
// reachable to the next sweep iteration.
// Fix: 4cd3dc8813f171cb6a8cb41088fd97eaa5909249 (Jon Coppeard).
function main() {
  let v2 = 0;
  do {
    const v5 = this.gczeal(10, v2);
    const v6 = v2++;
  } while (v2 < 10);
  for (let [v7] of "iV43r24wsw") {
    const v8 = v7 | 0;
    for (const v10 in "T4PnjCgpU2") {
      for (let v14 = 0; v14 < 10; v14++) {
        try {
          const v16 = this.oomAtAllocation(v14);
          const v18 = Float64Array();
        } catch(v19) {
          const v20 = v7 in v19;
          for (let v23 = 1; v23 < 64; v23++) {
            const v25 = this.oomAtAllocation(v23);
            try {
              function v26(v27, v28) {}
              const v31 = this.newGlobal();
              const v32 = Reflect.parse();
              function v33(v34, v35) {}
            } catch(v36) {}
          }
        }
      }
    }
    const v38 = v8 >> 25;
    const v39 = Math;
  }
  gc();
}
main();
