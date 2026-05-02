// CVE-2024-3854: JIT Diamond Condition Folding OOB
// Bug 1884552 - Assertion failure: ins->isGoto(), at jit/IonAnalysis.cpp:715
// Run with: --fuzzing-safe
for (let i22 = 0, i23 = 10;
    (() => {
        for (let i26 = 0, i27 = 10;
            (() => {
                let v28 = i26 != i27;
                const v29 = v28 === i23;
                if (v29) {
                    v28 = v29;
                } else {
                    switch (this) {
                    }
                }
                return v28;
            })();
            ) {
        }
        return i22 < i23;
    })();
    ) {
}
