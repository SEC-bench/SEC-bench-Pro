# Assertion failure: !masm.maybeRealm(), at /js/src/jit/BaselineCodeGen.h:153 with experimental.self_hosted_cache=true

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1985224
Component: JavaScript Engine
Bounty: (unknown)
Date: 2025-08-26T09:12:04Z
Keywords: assertion, csectype-uaf, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20250825-9426f4b06a46 (debug build, run with --fuzzing-safe --setpref=experimental.self_hosted_cache=true):

    Object.defineProperty(this, "x", {
      value: {
        c: function*() {}.constructor
      }
    })
    x.c()().next();
    setJitCompilerOption("offthread-compilation.enable", 1);
    while (true) {
      x.c()().next();
    }


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x0000555557b1c6e6 in js::jit::BaselineCodeGen<js::jit::BaselineCompilerHandler>::emit_Resume() ()
    #1  0x0000555557afcbcb in js::jit::BaselineCompiler::emitBody() ()
    #2  0x0000555557afae34 in js::jit::BaselineCompiler::compileImpl() ()
    #3  0x0000555557b38c77 in js::jit::OffThreadBaselineSnapshot::compileOffThread(js::jit::TempAllocator&, js::jit::CompileRealm*) ()
    #4  0x0000555557b389b0 in js::jit::BaselineCompileTask::runTask() ()
    #5  0x0000555557b388a6 in js::jit::BaselineCompileTask::runHelperThreadTask(js::AutoLockHelperThreadState&) ()
    #6  0x00005555571fc90f in js::GlobalHelperThreadState::runTaskLocked(JS::HelperThreadTask*, js::AutoLockHelperThreadState&) ()
    #7  0x00005555571fc7a4 in js::GlobalHelperThreadState::runOneTask(JS::HelperThreadTask*, js::AutoLockHelperThreadState&) ()
    #8  0x0000555557220cf1 in js::HelperThread::threadLoop(js::InternalThreadPool*) ()
    #9  0x0000555557220a7c in js::HelperThread::ThreadMain(js::InternalThreadPool*, js::HelperThread*) ()
    #10 0x0000555557233da8 in js::detail::ThreadTrampoline<void (&)(js::InternalThreadPool*, js::HelperThread*), js::InternalThreadPool*&, js::HelperThread*>::Start(void*) ()
    #11 0x0000555556f75b4d in set_alt_signal_stack_and_start(PthreadCreateParams*) ()
    #12 0x00007ffff769caa4 in ?? () from /lib/x86_64-linux-gnu/libc.so.6
    #13 0x00007ffff7729c3c in ?? () from /lib/x86_64-linux-gnu/libc.so.6
    rax	0x0	0
    rbx	0x0	0
    rcx	0x99	153
    rdx	0x7ffff7804563	140737345766755
    rsi	0x0	0
    rdi	0x7ffff7805700	140737345771264
    rbp	0x7ffff41fe9e0	140737289120224
    rsp	0x7ffff41fe950	140737289120080
    r8	0x0	0
    r9	0x3	3
    r10	0x0	0
    r11	0x293	659
    r12	0x7ffff3184b48	140737271843656
    r13	0x7ffff31851f0	140737271845360
    r14	0x7ffff41fe974	140737289120116
    r15	0x68f	1679
    rip	0x555557b1c6e6 <js::jit::BaselineCodeGen<js::jit::BaselineCompilerHandler>::emit_Resume()+3398>
    => 0x555557b1c6e6 <_ZN2js3jit15BaselineCodeGenINS0_23BaselineCompilerHandlerEE11emit_ResumeEv+3398>:	mov    %rcx,(%rax)
       0x555557b1c6e9 <_ZN2js3jit15BaselineCodeGenINS0_23BaselineCompilerHandlerEE11emit_ResumeEv+3401>:	call   0x555556f62880 <abort>

I'm not sure if this feature has been enabled meanwhile, please change to "disabled" if it is still off by default.

---

**Comment 1 — choller@mozilla.com — 2025-08-26T09:12:08Z**

Created attachment 9509477
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2025-08-26T09:12:09Z**

Created attachment 9509478
Testcase

---

**Comment 3 — bthrall@mozilla.com — 2025-08-26T15:46:31Z**

Off-thread compilation is not nulling out the realm ([see here](https://searchfox.org/firefox-main/rev/a5d7b5634b073a6b9e0d9f0f7df163d10cba478b/js/src/jit/BaselineJIT.cpp#333-335)) for self-hosted scripts when self_hosted_cache is enabled.

[This](https://searchfox.org/firefox-main/rev/a5d7b5634b073a6b9e0d9f0f7df163d10cba478b/js/src/jit/BaselineJIT.cpp#403-407) is how the Realm is nulled for on-thread compilation.

---

**Comment 4 — bugmon@mozilla.com — 2025-08-26T17:48:57Z**

Unable to reproduce bug 1985224 using build mozilla-central 20250825155516-9426f4b06a46.  Without a baseline, bugmon is unable to analyze this bug.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 5 — dveditz@mozilla.com — 2025-08-27T21:32:27Z**

What are the security consequences? If we don't null out the realm we might execute code in the wrong realm ( i.e. sec-high)?

---

**Comment 6 — bthrall@mozilla.com — 2025-08-27T21:49:29Z**

We can get UAF like in bug 1970438 and bug 1981780. It will not execute code in the wrong realm, but it checks the wrong realm to see if it needs a GC pre-barrier. If there is no pre-barrier when there should be, the GC can lose track of objects.

Note that the feature is disabled by default.

---

**Comment 7 — release-mgmt-account-bot@mozilla.tld — 2025-09-01T12:12:19Z**

The severity field for this bug is set to S3. However, the bug is flagged with the `sec-high` keyword.
:sdetar, could you consider increasing the severity of this security bug?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#severity_high_security.py).

---

**Comment 8 — continuation@gmail.com — 2025-09-02T12:30:39Z**

This is a disabled feature so there's no need for it to be S2.

---

**Comment 9 — sdetar@mozilla.com — 2025-09-02T16:28:36Z**

I think this bug is still a priority to fix, since it is a sec-high bug, so marking it a P1.

---

**Comment 10 — release-mgmt-account-bot@mozilla.tld — 2025-09-16T12:42:29Z**

Set release status flags based on info from the regressing bug 1970438

---

**Comment 11 — iireland@mozilla.com — 2025-10-01T23:01:08Z**

Created attachment 9517649
(secure)


The JSNullableAutoRealm mechanism that we use for on-thread compilation isn't available off-thread, since it works via the JSContext. It would be possible to manually null the realm pointer in a variety of places, but this seems cleanest and safest. A handful of main-thread compilations isn't a big deal; the whole point of the self-hosted cache is that we only compile each self-hosted function once per runtime.

---

**Comment 12 — pulsebot@bmo.tld — 2025-10-06T21:31:50Z**

Pushed by iireland@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/3905f930df89
https://hg.mozilla.org/integration/autoland/rev/a85f09fb6bd2
Don't compile realm-independent self-hosted baseline code off-thread r=bthrall

---

**Comment 13 — aryx.bugmail@gmx-topmail.de — 2025-10-07T10:14:22Z**

https://hg.mozilla.org/mozilla-central/rev/a85f09fb6bd2

---

**Comment 14 — afinder@mozilla.com — 2025-10-21T13:28:46Z**

(In reply to Pulsebot from comment #12)
> Pushed by iireland@mozilla.com:
> https://github.com/mozilla-firefox/firefox/commit/3905f930df89
> https://hg.mozilla.org/integration/autoland/rev/a85f09fb6bd2
> Don't compile realm-independent self-hosted baseline code off-thread
> r=bthrall

Hello!

Do you think it's possible the push mentioned in the referenced comment could have caused the improvement below ? 

We are unable to run backfills on the following [push range](https://treeherder.mozilla.org/jobs?repo=autoland&group_state=expanded&searchStr=Windows%2C11%2C24H2%2CShippable%2Copt%2CBrowsertime%2Cperformance%2Ctests%2Con%2CFirefox%2Ctest-windows11-64-24h2-shippable%2Fopt-browsertime-benchmark-firefox-speedometer%2Csp&tochange=e3f1fd706322ba441f886715b7d6dc5cf1e62c60&fromchange=3f5ca205df9eccca54c5a7fedab5bd33e02bf54a), and it's difficult to determine which of the patches in that push range caused the improvement.

Perfherder has detected a browsertime performance change from push [e3f1fd706322ba441f886715b7d6dc5cf1e62c60](https://hg.mozilla.org/integration/autoland/pushloghtml?changeset=e3f1fd706322ba441f886715b7d6dc5cf1e62c60).

If you have any questions, please reach out to a performance sheriff. Alternatively, you can find help on Slack by joining [#perf-help](https://mozilla.enterprise.slack.com/archives/C03U19JCSFQ), and on Matrix you can find help by joining [#perftest](https://matrix.to/#/#perftest:mozilla.org).

### Improvements:

| **Ratio** | **Test** | **Platform** | **Options** | **Absolute values (old vs new)** |  
|--|--|--|--|--| 
| [5%](https://treeherder.mozilla.org/perfherder/graphs?timerange=2592000&series=autoland,5256866,1,13)  | [speedometer](https://firefox-source-docs.mozilla.org/testing/perfdocs/raptor.html#speedometer-b) React-TodoMVC/DeletingAllItems | windows11-64-24h2-shippable | fission webrender | 11.45 -> 10.92 | 


Details of the alert can be found in the [alert summary](https://treeherder.mozilla.org/perfherder/alerts?id=47215), including links to graphs and comparisons for each of the affected tests.

If you need the profiling jobs [you can trigger them yourself from treeherder job view](https://firefox-source-docs.mozilla.org/testing/perfdocs/perftest-in-a-nutshell.html#using-the-firefox-profiler) or ask a performance sheriff to do that for you.

You can run all of these tests on try with `./mach try perf --alert 47215`

The following [documentation link](https://firefox-source-docs.mozilla.org/testing/perfdocs/mach-try-perf.html#running-alert-tests) provides more information about this command.

---

**Comment 15 — bthrall@mozilla.com — 2025-10-21T14:58:13Z**

No, that change shouldn't affect performance at all right now because it requires the self_hosted_cache pref to be enabled and it is disabled by default.
