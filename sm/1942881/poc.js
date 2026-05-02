// CVE-2025-1934: RegExp Bailout Recovery GC Corruption
// Bug 1942881 - RRegExpMatcher recover calls RegExpMatcherRaw which triggers GC
// Run with: --fuzzing-safe --fast-warmup
//
// The RegExpMatcher MIR op was marked can_recover:true, so during JIT bailout
// the recovery code calls RegExpMatcherRaw. This can trigger GC while GC is
// suppressed during recovery, violating the !cx->suppressGC invariant.

for (a = 0; ; a++) {
    for (b = true; b; b = !inIon())
        c = 0
    function d() {
        if (c++ < 10)
            interruptIf(true)
        return true
    }
    setInterruptCallback(d)
    d()
    const e = "".substring().match("0*[]")
    if (a >= 50)
        e.f
}
