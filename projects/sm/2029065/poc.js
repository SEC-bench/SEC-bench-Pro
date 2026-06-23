// Bug 2029065 — Follow-up to 2013543. OptimizeIteratorIndices queried
// dominates() on freshly-created MIR blocks whose dominator info was stale,
// producing garbage dominance results. Fix skips blocks with no dominator
// info via hasNoDominatorInfo.
//
// Fix: commit 5cfc09e7ce19a151df5651a24ebd250632aac10f

function f(obj1, obj2) {
    let keys1 = Object.keys(obj1);
    let r = 0;
    for (let i = 0; i < keys1.length; i++) {
        r += obj1[keys1[i]];
        let keys2 = Object.keys(obj2);
        r += obj2[keys1[i]];
        r += obj2[keys1[i]];
        r += keys2.length;
    }
    return r;
}

let o1 = {a: 1, b: 2, c: 3};
let o2 = {a: 10, b: 20, c: 30};

for (let i = 0; i < 1000; i++) {
    f(o1, o2);
}
