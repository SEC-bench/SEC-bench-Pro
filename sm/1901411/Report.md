# Assertion failure: generator->isCompleted(), at /root/src/js/src/vm/AsyncIteration.cpp:605

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1901411
CVE: CVE-2024-7652
Component: JavaScript Engine
Bounty: (unknown)
Date: 2024-06-09T07:26:24Z
Keywords: regression, reporter-external, sec-high
See Also:
- https://github.com/tc39/ecma262/pull/2413
- https://github.com/tc39/ecma262/security/advisories/GHSA-g38c-wh3c-5h9r
- https://issues.chromium.org/issues/346692561
- https://bugs.webkit.org/show_bug.cgi?id=275407
- https://github.com/boa-dev/boa/pull/3879

Created attachment 9406244
bug.js

Steps to reproduce:

Checkout commit 15778b8c32f8535624fff2af36fc669e65a9af3 and invoke the js shell as follows:
```
/root/js-spidermonkey-shell  --fuzzing-safe  <testcase>
```


Actual results:

```
Assertion failure: generator->isCompleted(), at /root/src/js/src/vm/AsyncIteration.cpp:605
```

---

**Comment 1 — jdemooij@mozilla.com — 2024-06-10T11:04:26Z**

arai, needinfo'ing you because this looks like an issue with async functions and/or promises.

---

**Comment 2 — arai.unmht@gmail.com — 2024-06-10T15:47:20Z**

Good find!

Apparently this is a bug in the spec.

Here's reduced testcase:

```js
async function* f() {}
const g = f();
Object.defineProperty(Object.prototype, "then", {
  get: function() {
    g.return();
    return;
  },
});
g.return();
```

The first step is the top-level `g.return();` call.
At the point of the `%AsyncGeneratorPrototype%.return` step 8, The `generator.[[AsyncGeneratorState]]` internal slot is `suspended-start`,
and it sets the slot to `awaiting-return`, and the it performs `AsyncGeneratorAwaitReturn`.

https://tc39.es/ecma262/#sec-asyncgenerator-prototype-return
```
%AsyncGeneratorPrototype%.return ( value )

...
  8. If state is either suspended-start or completed, then
    a. Set generator.[[AsyncGeneratorState]] to awaiting-return.
    b. Perform ! AsyncGeneratorAwaitReturn(generator).
...
```

`AsyncGeneratorAwaitReturn` creates `fulfilledClosure` with the following, and it's called while draining job queue.


https://tc39.es/ecma262/#sec-asyncgeneratorawaitreturn
```
AsyncGeneratorAwaitReturn ( generator )
...
  7. Let fulfilledClosure be a new Abstract Closure with parameters
     (value) that captures generator and performs the following steps when
     called:
    a. Set generator.[[AsyncGeneratorState]] to completed.
    b. Let result be NormalCompletion(value).
    c. Perform AsyncGeneratorCompleteStep(generator, result, true).
    d. Perform AsyncGeneratorDrainQueue(generator).
...
```

At the `AsyncGeneratorAwaitReturn` step 7.a, it sets `generator.[[AsyncGeneratorState]]` internal slot to `completed`,
and the `AsyncGeneratorDrainQueue` step 1, performed from the `AsyncGeneratorAwaitReturn` step 7.d expects the `generator.[[AsyncGeneratorState]]` internal slot remains `completed`.

https://tc39.es/ecma262/#sec-asyncgeneratordrainqueue
```
AsyncGeneratorDrainQueue ( generator )
...
  1. Assert: generator.[[AsyncGeneratorState]] is completed.
...
```

Then, the problem is the `AsyncGeneratorCompleteStep` performed in between them, at the `AsyncGeneratorAwaitReturn` step 7.c.

https://tc39.es/ecma262/#sec-asyncgeneratorcompletestep
```
AsyncGeneratorCompleteStep ( generator, completion, done [ , realm ] )

...
  7. Else,
...
    d. Perform ! Call(promiseCapability.[[Resolve]], undefined, «
       iteratorResult »).
  8. Return unused.
```

At the `AsyncGeneratorCompleteStep` step 7.d, `promiseCapability.[[Resolve]]` is called, which is `Promise Resolve Functions` in this case, and it accesses `then` property of `iteratorResult`.  Given the `iteratorResult` is a plain object, it results in accessing `Object.prototype.then` property.
In the testcase, it reslts in calling the `then` getter function.

https://tc39.es/ecma262/#sec-promise-resolve-functions
```
Promise Resolve Functions
...
  9. Let then be Completion(Get(resolution, "then")).
...
```

In the getter function, it calls `g.return();` again, and it sets to `generator.[[AsyncGeneratorState]]` internal slot back to `awaiting-return`.

https://tc39.es/ecma262/#sec-asyncgenerator-prototype-return
```
%AsyncGeneratorPrototype%.return ( value )

...
  8. If state is either suspended-start or completed, then
    a. Set generator.[[AsyncGeneratorState]] to awaiting-return.
```

So, the assertion at the `AsyncGeneratorDrainQueue` step 1 fails, which is the exact assertion shown in the comment #0.

---

**Comment 3 — arai.unmht@gmail.com — 2024-06-10T15:55:59Z**

Possible fix is to replace the `AsyncGeneratorDrainQueue` step 1 with the following, or something along that line:

```
  1. If generator.[[AsyncGeneratorState]] is not completed:
     a. NOTE: AsyncGeneratorCompleteStep performed before AsyncGeneratorDrainQueue can call %AsyncGeneratorPrototype%.return.
     b. Assert: generator.[[AsyncGeneratorState]] is awaiting-return.
     c. Return unused.
```

other possibility is to perhaps somehow prevent the `then` property access while resolving the promise with `iteratorResult`, but this sounds error-prone.

---

**Comment 4 — arai.unmht@gmail.com — 2024-06-10T19:02:15Z**

In short, this can result in type confusion on non-debug build, due to dequeueing from empty list once or more, on certain situation.
I haven't yet figured out how much exploitable this is tho, it should be sec-high or higher maybe?

Here's the details:

In term of requests in the queue, the behavior is the following:

https://tc39.es/ecma262/#sec-asyncgenerator-prototype-return
```
%AsyncGeneratorPrototype%.return ( value )

  1. Let generator be the this value.
  2. Let promiseCapability be ! NewPromiseCapability(%Promise%).
...
  5. Let completion be Completion Record { [[Type]]: return, [[Value]]:
     value, [[Target]]: empty }.
  6. Perform AsyncGeneratorEnqueue(generator, completion, promiseCapability).
  7. Let state be generator.[[AsyncGeneratorState]].
  8. If state is either suspended-start or completed, then
    a. Set generator.[[AsyncGeneratorState]] to awaiting-return.
    b. Perform ! AsyncGeneratorAwaitReturn(generator).
...
  11. Return promiseCapability.[[Promise]].
```

The `%AsyncGeneratorPrototype%.return` step 6 performs `AsyncGeneratorEnqueue`, which enqueues one `AsyncGeneratorRequest`, let's call this `Request1`.

https://tc39.es/ecma262/#sec-asyncgeneratorenqueue
```
AsyncGeneratorEnqueue ( generator, completion, promiseCapability )

  1. Let request be AsyncGeneratorRequest { [[Completion]]: completion,
     [[Capability]]: promiseCapability }.
  2. Append request to generator.[[AsyncGeneratorQueue]].
  3. Return unused.
```

And `%AsyncGeneratorPrototype%.return` step 8.b performs `AsyncGeneratorAwaitReturn`.
At this point, there's `Request1` in the queue, and the assertion at step 2 passes.
The `completion` is the `Completion Record { [[Type]]: return, [[Value]]: value, [[Target]]: empty }`, created at the `%AsyncGeneratorPrototype%.return` step 5, where `[[Value]]` is the `return` method's parameter.
In the reduced testcase, it's undefined, but it can be arbitrary value, let's say `Value1`.

The step 6 resolves a newly created promise, let's call `Promise1` with `Value1`, and the step 11 performs `PerformPromiseThen` on `Promise1` with the `fulfilledClosure`, which results in creating and enqueueing a promise reaction job, let's call `ReactionJob1`, for `fulfilledClosure`.

https://tc39.es/ecma262/#sec-asyncgeneratorawaitreturn
```
AsyncGeneratorAwaitReturn ( generator )

  1. Let queue be generator.[[AsyncGeneratorQueue]].
  2. Assert: queue is not empty.
  3. Let next be the first element of queue.
  4. Let completion be Completion(next.[[Completion]]).
  5. Assert: completion is a return completion.
  6. Let promise be ? PromiseResolve(%Promise%, completion.[[Value]]).
  7. Let fulfilledClosure be a new Abstract Closure with parameters
     (value) that captures generator and performs the following steps when
     called:
...
  8. Let onFulfilled be CreateBuiltinFunction(fulfilledClosure, 1, "", «
     »).
...
  11. Perform PerformPromiseThen(promise, onFulfilled, onRejected).
  12. Return unused.
```

In `ReactionJob1`, the `fulfilledClosure` is called, and the step 7.c performs `AsyncGeneratorCompleteStep`

https://tc39.es/ecma262/#sec-asyncgeneratorawaitreturn
```
AsyncGeneratorAwaitReturn ( generator )

...
  7. Let fulfilledClosure be a new Abstract Closure with parameters
     (value) that captures generator and performs the following steps when
     called:
    a. Set generator.[[AsyncGeneratorState]] to completed.
    b. Let result be NormalCompletion(value).
    c. Perform AsyncGeneratorCompleteStep(generator, result, true).
    d. Perform AsyncGeneratorDrainQueue(generator).
    e. Return undefined.
```

At this point, `generator.[[AsyncGeneratorQueue]]` still contains only the `Request1`, and the assertion at the step 1 passes, and `next` becomes the `Request1`, and `Request1` is removed from the `generator.[[AsyncGeneratorQueue]]` at the step 3, which results in `generator.[[AsyncGeneratorQueue]]` being empty in the testcase (but it's not necessarily be empty in general).

Steps 5-7 resolve the `Reqeust1.[[Capability]]` with a newly created iterator result object.

https://tc39.es/ecma262/#sec-asyncgeneratorcompletestep
```
AsyncGeneratorCompleteStep ( generator, completion, done [ , realm ] )

  1. Assert: generator.[[AsyncGeneratorQueue]] is not empty.
  2. Let next be the first element of generator.[[AsyncGeneratorQueue]].
  3. Remove the first element from generator.[[AsyncGeneratorQueue]].
  4. Let promiseCapability be next.[[Capability]].
  5. Let value be completion.[[Value]].
...
  7. Else,
    a. Assert: completion is a normal completion.
    b. If realm is present, then
...
      iii. Let iteratorResult be CreateIterResultObject(value, done).
...
    c. Else,
      i. Let iteratorResult be CreateIterResultObject(value, done).
    d. Perform ! Call(promiseCapability.[[Resolve]], undefined, «
       iteratorResult »).
  8. Return unused.
```

Then, in the testcase, `%AsyncGeneratorPrototype%.return` is called at the step 7.d.
  * Let's call the `return` paramter `Value2`
  * It enqueues yet another `AsyncGeneratorRequest`, let's call this `Request2` at `%AsyncGeneratorPrototype%.return` step 6
  * It created and resolved promise `Promise2` with `Value2`
  * It performs `PerformPromiseThen` on `Promise2`, and enqueues yet another promise reaction job `ReactionJob2` at the `AsyncGeneratorAwaitReturn` step 11, performed at the `%AsyncGeneratorPrototype%.return` step 8.b

The `Request2` remains in the `generator.[[AsyncGeneratorQueue]]` at this point.

https://tc39.es/ecma262/#sec-asyncgenerator-prototype-return
```
%AsyncGeneratorPrototype%.return ( value )

...
  6. Perform AsyncGeneratorEnqueue(generator, completion, promiseCapability).
  7. Let state be generator.[[AsyncGeneratorState]].
  8. If state is either suspended-start or completed, then
    a. Set generator.[[AsyncGeneratorState]] to awaiting-return.
    b. Perform ! AsyncGeneratorAwaitReturn(generator).
...
```

After that, going back to `AsyncGeneratorAwaitReturn`, the step 7.d performs `AsyncGeneratorDrainQueue`.

At this point, `generator.[[AsyncGeneratorQueue]]` contains only `Request2`.
As mentioned above, there can be some more requests in general, and the step 3 `If queue is empty, return unused.` doesn't necessarily match.

At the step 5.a, `next` becomes the `Request2`, and its `[[Completion]]` is
`Completion Record { [[Type]]: return, [[Value]]: value, [[Target]]: empty }` created at the `%AsyncGeneratorPrototype%.return` step 5.

Given it's `return` completion, it matches the step 5.c, and performs `AsyncGeneratorAwaitReturn` at step 5.c.ii

https://tc39.es/ecma262/#sec-asyncgeneratordrainqueue
```
AsyncGeneratorDrainQueue ( generator )

  1. Assert: generator.[[AsyncGeneratorState]] is completed.
  2. Let queue be generator.[[AsyncGeneratorQueue]].
  3. If queue is empty, return unused.
  4. Let done be false.
  5. Repeat, while done is false,
    a. Let next be the first element of queue.
    b. Let completion be Completion(next.[[Completion]]).
    c. If completion is a return completion, then
      i. Set generator.[[AsyncGeneratorState]] to awaiting-return.
      ii. Perform ! AsyncGeneratorAwaitReturn(generator).
      iii. Set done to true.
...
  6. Return unused.
```

In `AsyncGeneratorAwaitReturn`, step 3 finds `Request2` again.
It resolves newly created promise `Promise3` with `Value2`, and performs `PerformPromiseThen` on `Promise3`, which results in enqueueing `ReactionJob3`.

https://tc39.es/ecma262/#sec-asyncgeneratorawaitreturn
```
AsyncGeneratorAwaitReturn ( generator )

  1. Let queue be generator.[[AsyncGeneratorQueue]].
  2. Assert: queue is not empty.
  3. Let next be the first element of queue.
  4. Let completion be Completion(next.[[Completion]]).
  5. Assert: completion is a return completion.
  6. Let promise be ? PromiseResolve(%Promise%, completion.[[Value]]).
  7. Let fulfilledClosure be a new Abstract Closure with parameters
     (value) that captures generator and performs the following steps when
     called:
...
  8. Let onFulfilled be CreateBuiltinFunction(fulfilledClosure, 1, "", «
     »).
...
  11. Perform PerformPromiseThen(promise, onFulfilled, onRejected).
  12. Return unused.
```

`Promise2` and `Promise3` are both resolved with `Value2`, and `ReactionJob2` and `ReactionJob3` will be called with the same value, comes from `Value2`.

If `Value2` is a promise from the same realm, or if it's not an object, those reaction jobs will receive `Value2` itself.

Otherwise, `Value2`'s `then` property is accessed at the `Promise Resolve Functions` step 9, and thenable job will call the `then` function.
These operations are duplicated because of the duplicate `AsyncGeneratorAwaitReturn` calls.

https://tc39.es/ecma262/#sec-promise-resolve-functions
```
Promise Resolve Functions

...
  8. If resolution is not an Object, then
    a. Perform FulfillPromise(promise, resolution).
    b. Return undefined.
  9. Let then be Completion(Get(resolution, "then")).
  10. If then is an abrupt completion, then
    a. Perform RejectPromise(promise, then.[[Value]]).
    b. Return undefined.
  11. Let thenAction be then.[[Value]].
  12. If IsCallable(thenAction) is false, then
    a. Perform FulfillPromise(promise, resolution).
    b. Return undefined.
  13. Let thenJobCallback be HostMakeJobCallback(thenAction).
  14. Let job be NewPromiseResolveThenableJob(promise, resolution,
      thenJobCallback).
  15. Perform HostEnqueuePromiseJob(job.[[Job]], job.[[Realm]]).
...
```

https://tc39.es/ecma262/#sec-promise-resolve
```
27.2.4.7.1 PromiseResolve ( C, x )

The abstract operation PromiseResolve takes arguments C (a constructor) and x
(an ECMAScript language value) and returns either a normal completion
containing an ECMAScript language value or a throw completion. It returns a
new promise resolved with x. It performs the following steps when called:

  1. If IsPromise(x) is true, then
    a. Let xConstructor be ? Get(x, "constructor").
    b. If SameValue(xConstructor, C) is true, return x.
  2. Let promiseCapability be ? NewPromiseCapability(C).
  3. Perform ? Call(promiseCapability.[[Resolve]], undefined, « x »).
  4. Return promiseCapability.[[Promise]].
```

https://tc39.es/ecma262/#sec-asyncgeneratorawaitreturn
```
AsyncGeneratorAwaitReturn ( generator )

...
  7. Let fulfilledClosure be a new Abstract Closure with parameters
     (value) that captures generator and performs the following steps when
     called:
    a. Set generator.[[AsyncGeneratorState]] to completed.
    b. Let result be NormalCompletion(value).
    c. Perform AsyncGeneratorCompleteStep(generator, result, true).
    d. Perform AsyncGeneratorDrainQueue(generator).
    e. Return undefined.
```

Then, with either the same `Value2`, or some value that `Value2.then(...)` produces, `ReactionJob2` and `ReactionJob3` are called, and `AsyncGeneratorCompleteStep` is called for each.

Then, if `ReactionJob2` is called first, it dequeues `Request2` from `generator.[[AsyncGeneratorQueue]]`, and resolves it with `Value2` or the value `Value2.then(...)` produces.

After that, `ReactionJob3` is called, and it tries to dequeue request, but the queue is already empty.  The assertion at step 1 fails, and the step 2 doesn't work.

https://tc39.es/ecma262/#sec-asyncgeneratorcompletestep
```
AsyncGeneratorCompleteStep ( generator, completion, done [ , realm ] )

  1. Assert: generator.[[AsyncGeneratorQueue]] is not empty.
  2. Let next be the first element of generator.[[AsyncGeneratorQueue]].
  3. Remove the first element from generator.[[AsyncGeneratorQueue]].
  4. Let promiseCapability be next.[[Capability]].
  5. Let value be completion.[[Value]].
...
  7. Else,
    a. Assert: completion is a normal completion.
    b. If realm is present, then
...
      iii. Let iteratorResult be CreateIterResultObject(value, done).
...
    c. Else,
      i. Let iteratorResult be CreateIterResultObject(value, done).
    d. Perform ! Call(promiseCapability.[[Resolve]], undefined, «
       iteratorResult »).
  8. Return unused.
```

In SpiderMonkey's case, the dequeue is performed by `AsyncGeneratorObject::dequeueRequest`.

https://searchfox.org/mozilla-central/rev/46d0387f0b582f00a5722c20d4e6b8693793631b/js/src/vm/AsyncIteration.cpp#444-457
```cpp
[[nodiscard]] static bool AsyncGeneratorCompleteStepNormal(
    JSContext* cx, Handle<AsyncGeneratorObject*> generator, HandleValue value,
    bool done) {
  // Step 1. Let queue be generator.[[AsyncGeneratorQueue]].
  // Step 2. Assert: queue is not empty.
  MOZ_ASSERT(!generator->isQueueEmpty());

  // Step 3. Let next be the first element of queue.
  // Step 4. Remove the first element from queue.
  AsyncGeneratorRequest* next =
      AsyncGeneratorObject::dequeueRequest(cx, generator);
  if (!next) {
    return false;
  }
```

If there was at most one request in the queue, it means the queue is now empty, and the `Slot_QueueOrRequest` value is `NullValue`, it matches `generator->isSingleQueue()` case, and it returns `generator->singleQueueRequest()`.

https://searchfox.org/mozilla-central/rev/46d0387f0b582f00a5722c20d4e6b8693793631b/js/src/vm/AsyncIteration.cpp#158-167
```cpp
AsyncGeneratorRequest* AsyncGeneratorObject::dequeueRequest(
    JSContext* cx, Handle<AsyncGeneratorObject*> generator) {
  if (generator->isSingleQueue()) {
    AsyncGeneratorRequest* request = generator->singleQueueRequest();
    generator->clearSingleQueueRequest();
    return request;
  }

  Rooted<ListObject*> queue(cx, generator->queue());
  return &queue->popFirstAs<AsyncGeneratorRequest>(cx);
```

Here, it tries to treat it as `AsyncGeneratorRequest`. This also hits assertion failure, but on non-debug build, it results in returning `nullptr` on 32-bit, and `0x0004000000000000` on 64-bit, which is object pointer extracted from `NullValue`.
This results in simple crash.

https://searchfox.org/mozilla-central/rev/46d0387f0b582f00a5722c20d4e6b8693793631b/js/src/vm/AsyncIteration.h#430-434
```cpp
AsyncGeneratorRequest* singleQueueRequest() const {
  return &getFixedSlot(Slot_QueueOrRequest)
              .toObject()
              .as<AsyncGeneratorRequest>();
}
```

On the other hand, if there were 2 or more requests, `Slot_QueueOrRequest` contains a ListObject, and `popFirstAs` is called, and it can read random value (for empty case, or -1 items case), and results in type confusion.

https://searchfox.org/mozilla-central/rev/46d0387f0b582f00a5722c20d4e6b8693793631b/js/src/vm/AsyncIteration.cpp#158-159,166-167
```cpp
AsyncGeneratorRequest* AsyncGeneratorObject::dequeueRequest(
    JSContext* cx, Handle<AsyncGeneratorObject*> generator) {
...
  Rooted<ListObject*> queue(cx, generator->queue());
  return &queue->popFirstAs<AsyncGeneratorRequest>(cx);
```

https://searchfox.org/mozilla-central/rev/46d0387f0b582f00a5722c20d4e6b8693793631b/js/src/vm/List-inl.h#86-89
```cpp
template <class T>
inline T& js::ListObject::popFirstAs(JSContext* cx) {
  return popFirst(cx).toObject().as<T>();
}
```

https://searchfox.org/mozilla-central/rev/46d0387f0b582f00a5722c20d4e6b8693793631b/js/src/vm/List-inl.h#57-70
```cpp
inline JS::Value js::ListObject::popFirst(JSContext* cx) {
  uint32_t len = length();
  MOZ_ASSERT(len > 0);

  JS::Value entry = get(0);
  if (!tryShiftDenseElements(1)) {
    moveDenseElements(0, 1, len - 1);
    setDenseInitializedLength(len - 1);
    shrinkElements(cx, len - 1);
  }

  MOZ_ASSERT(length() == len - 1);
  return entry;
}
```

Then, this is specific to ``%AsyncGeneratorPrototype%.return`, given `next` and `throw` doesn't change the `generator.[[AsyncGeneratorState]]` and doesn't enqueue, if it's completed.

https://tc39.es/ecma262/#sec-asyncgenerator-prototype-next
```
%AsyncGeneratorPrototype%.next ( value )

...
  5. Let state be generator.[[AsyncGeneratorState]].
  6. If state is completed, then
    a. Let iteratorResult be CreateIterResultObject(undefined, true).
    b. Perform ! Call(promiseCapability.[[Resolve]], undefined, «
       iteratorResult »).
    c. Return promiseCapability.[[Promise]].
...
```

https://tc39.es/ecma262/#sec-asyncgenerator-prototype-throw
```
%AsyncGeneratorPrototype%.throw ( exception )

...
  5. Let state be generator.[[AsyncGeneratorState]].
...
  7. If state is completed, then
    a. Perform ! Call(promiseCapability.[[Reject]], undefined, «
       exception »).
    b. Return promiseCapability.[[Promise]].
...
```

---

**Comment 5 — arai.unmht@gmail.com — 2024-06-10T19:03:12Z**

:jandem, can you help me figuring out the sec- rating?

---

**Comment 6 — arai.unmht@gmail.com — 2024-06-10T19:29:45Z**

Given this is a spec bug, this had been there from the version where it's implemented in bug 1331092, which was version 55.

---

**Comment 7 — arai.unmht@gmail.com — 2024-06-10T19:47:53Z**

At least the testcase doesn't crash JavaScriptCore and V8 shells.
maybe I'm misinterpreting the spec, or they have extra check?

---

**Comment 8 — arai.unmht@gmail.com — 2024-06-10T20:31:23Z**

engine262 hits the same assertion failure.
so at least this is a spec bug.

---

**Comment 9 — arai.unmht@gmail.com — 2024-06-10T22:40:14Z**

Actually, the assertion in the spec comes from https://github.com/tc39/ecma262/pull/2413
which is reflected to SpiderMonkey in bug 1724123, version 97.
I've confirmed the crash happens on 97, but not on 96.

Then, I don't see the corresponding update in v8 code nor JSC code (at least the building blocks I see in their code seems to be based on ECMAScript 2021's abstract operations' names which is before https://github.com/tc39/ecma262/pull/2413), so I assume the problematic change is not reflected there.

---

**Comment 10 — arai.unmht@gmail.com — 2024-06-11T00:54:38Z**

In engine262, when I change the `AsyncGeneratorDrainQueue` step 1 to return if `generator.[[AsyncGeneratorState]]` is not `completed`, then the other assertion in `AsyncGeneratorAwaitReturn` step 5 fails.

https://tc39.es/ecma262/#sec-asyncgeneratordrainqueue
```
AsyncGeneratorDrainQueue ( generator )

  1. Assert: generator.[[AsyncGeneratorState]] is completed.
```


https://tc39.es/ecma262/#sec-asyncgeneratorawaitreturn
```
AsyncGeneratorAwaitReturn ( generator )

  1. Let queue be generator.[[AsyncGeneratorQueue]].
  2. Assert: queue is not empty.
  3. Let next be the first element of queue.
  4. Let completion be Completion(next.[[Completion]]).
  5. Assert: completion is a return completion.
...
```

Given the https://github.com/tc39/ecma262/pull/2413 is a refactoring based on the idea of "state machine", I guess there are some states which are overlooked, and no longer represented/handled properly.

I'll look into bug 1724123 patch stack to see if I can locate the regressor, which may tell us what part of the spec change was wrong.

---

**Comment 11 — arai.unmht@gmail.com — 2024-06-11T04:50:59Z**

It looks like, the root cause is the mis-assumption about `PerformPromiseThen`.

To my understanding, the refactoring is based on the following assumption (which is I used while the refactoring on the SpiderMonkey's side, to get the steps which matches the spec):
  * `PerformPromiseThen` with `iteratorResult` object cannot change the generator's state and queue
  * the `generator.[[AsyncGeneratorState]]` value persists across `PerformPromiseThen`
  * the content of `generator.[[AsyncGeneratorQueue]]` persists across `PerformPromiseThen`

As mentioned above, this is wrong, because `PerformPromiseThen` accesses `then` property of `iteratorResult` object, which can be user-modified `Object.prototype.then` property, and the `then` getter can run arbitrary code, including calling the generator's methods.

Then, the refactoring uses the assumption to eliminate "dead" branches or skip operations.

For example `AsyncGeneratorResumeNext` is refactored into the 2 parts:
  * `AsyncGeneratorDrainQueue` for `completed` state
    * this is mostly a copy of `AsyncGeneratorResumeNext`, with branches for non-`completed` cases eliminated
  * code for other cases, inlined into the caller

There, some caller directly calls `AsyncGeneratorDrainQueue`, assuming the `completed` state set before `PerformPromiseThen` persists. This means, if the `then` getter modifies the generator's state into something else than `completed`, that's not handled properly.

Also, `AsyncGeneratorDrainQueue` itself is also inlined into some callers.
For example `AsyncGenerator.prototype.return`, where some more "dead" branches are eliminated, but they're not actually dead, which results in  the wrong assertion "Assert: completion is a return completion." at step 5 above.

Also, the inlining assumes the queue was empty at certain point, for example, `AsyncGenerator.prototype.next ` with `complete` case.
It skips enqueue+dequeue operation, but this is also wrong because the queue can contain extra values due to the side effect of `then`, which results in performing out-of-order operation.

So, possible options from here are the following:
  * (A) Revert all changes
     1. Revert bug 1724123 patch stack on m-c (+900 lines, -1305 lines)
     2. Uplift the stack to beta/esr
     3. Revisit the refactoring in the spec's side (either just revert or resurrect dead branches)
     4. Optionally apply the diff to m-c as followup
  * (B) Figure out the minimal fix
     1. Resurrect dead branches in the spec
     2. Apply the diff to m-c
     3. Uplift the change to beta/esr

I've tried reverting all changes, and it looks like most of them applies straight-forward, but given the amount of the change, I wonder if it fits uplift.

---

**Comment 12 — jdemooij@mozilla.com — 2024-06-11T08:12:49Z**

Great find and analysis.

(In reply to Tooru Fujisawa [:arai] from comment #5)
> :jandem, can you help me figuring out the sec- rating?

I'll mark this sec-high based on comment 4. Can you post a test case where we try to read from an empty `ListObject` in non-debug builds? Because that's the part that makes this exploitable.

How many "dead" branches are vulnerable? We should try to change those to match the behavior before bug 1724123 + add some strategic release assertions if needed. I think we should only back out bug 1724123 if we think there are more (spec) bugs hidden here because it will be a large patch to uplift.

Let's report this to tc39 as a security vulnerability and coordinate with them on when we make this public. We should have a patch ready in the meantime in case this gets out somehow.

---

**Comment 13 — arai.unmht@gmail.com — 2024-06-11T08:38:22Z**

(In reply to Jan de Mooij [:jandem] from comment #12)
> Can you post a test case where we try to read from an empty `ListObject` in non-debug builds? Because that's the part that makes this exploitable.

For example this, where I see the `queue->length()` being `0` and `-1` before `popFirstAs` call.

```js
async function* f() {}
const g = f();
let count = 0;
Object.defineProperty(Object.prototype, "then", {
  get: function() {
    if (count < 10) {
      count++;
      g.return();
      g.return();
    }
    return;
  },
});
g.return();
```

https://searchfox.org/mozilla-central/rev/aa9d148d5be3e7b606448f0b8da6e9f4fa43112f/js/src/vm/AsyncIteration.cpp#158-159,166-167
```cpp
AsyncGeneratorRequest* AsyncGeneratorObject::dequeueRequest(
    JSContext* cx, Handle<AsyncGeneratorObject*> generator) {
...
  Rooted<ListObject*> queue(cx, generator->queue());
  return &queue->popFirstAs<AsyncGeneratorRequest>(cx);
```

> How many "dead" branches are vulnerable? We should try to change those to match the behavior before bug 1724123 + add some strategic release assertions if needed. I think we should only back out bug 1724123 if we think there are more (spec) bugs hidden here because it will be a large patch to uplift.

5 or so, maybe?  The dead code elimination and inlining happens in multiple places.
there are 4 places where it peeks or dequeues.
I haven't checked how much critical the the out-of-order or duplicate request handling is.

At least we should revive `AsyncGeneratorResumeNext`, and rewrite the past consumers to use it, instead of `AsyncGeneratorDrainQueue` or more inlined ones.
And iirc, `AsyncGeneratorResumeNext` is the largest block that was touched by the patch stack. so if we revive it, the amount of code change would be similar to the whole revert, except for cosmetic changes such as comment or variable names.
anyway, I'll try enumerating all affected cases.
also I'll see if we can revert the patch stack while keeping the surrounding code unchanged as much as possible.

> Let's report this to tc39 as a security vulnerability and coordinate with them on when we make this public. We should have a patch ready in the meantime in case this gets out somehow.

Okay, I'll do that in parallel.

---

**Comment 14 — arai.unmht@gmail.com — 2024-06-12T01:02:47Z**

Created attachment 9406866
Bug 1901411 - Part 1: Partially revert AsyncGeneratorDrainQueue to AsyncGeneratorResumeNext. r?mgaudet!

---

**Comment 15 — arai.unmht@gmail.com — 2024-06-12T01:02:58Z**

Created attachment 9406867
Bug 1901411 - Part 2: Fix sanity check for debugger. r?mgaudet!

---

**Comment 16 — arai.unmht@gmail.com — 2024-06-12T01:03:14Z**

Created attachment 9406868
Bug 1901411 - Part 3: Revert inlining of AsyncGeneratorDrainQueue in AsyncGeneratorNext. r?mgaudet!

---

**Comment 17 — arai.unmht@gmail.com — 2024-06-12T01:03:25Z**

Created attachment 9406869
Bug 1901411 - Part 4: Revert inlining of AsyncGeneratorDrainQueue in AsyncGeneratorReturn. r?mgaudet!

---

**Comment 18 — arai.unmht@gmail.com — 2024-06-12T01:03:37Z**

Created attachment 9406870
Bug 1901411 - Part 5: Revert inlining of AsyncGeneratorDrainQueue in AsyncGeneratorThrow. r?mgaudet!

---

**Comment 19 — arai.unmht@gmail.com — 2024-06-12T01:03:48Z**

Created attachment 9406871
Bug 1901411 - Part 6: Revert inlining of AsyncGeneratorDrainQueue in AsyncGeneratorYield. r?mgaudet!

---

**Comment 20 — arai.unmht@gmail.com — 2024-06-12T01:06:19Z**

filed for TC39 https://github.com/tc39/ecma262/security/advisories/GHSA-g38c-wh3c-5h9r

---

**Comment 21 — arai.unmht@gmail.com — 2024-06-12T01:37:42Z**

> So, possible options from here are the following:

In order to make it easier/safer to uplift, and also avoid waiting on the spec's fix, I've taken yet another approach here:

  * (C) Revert minimally
      * Revert bug 1724123 patch stack, fold the stack, reorder and move code, re-apply some definitely-safe refactoring, in order to minimize the diff, and split the patch into each part (+66, -161 lines in total)
      * Uplift the stack to beta/esr
      * Revisit the refactoring in the spec's side (either just revert or resurrect dead branches)
      * Optionally apply the diff to m-c as followup

The patch stack applies cleanly for central = 129, beta = 128, and esr115 (just in case).

---

**Comment 22 — arai.unmht@gmail.com — 2024-06-12T01:40:05Z**

Testcases I've reported to TC39 (in addition to tests in above comments):

Assertion failure for the queue length:
```js
async function* f() {}
const g = f();
let first = true;
Object.defineProperty(Object.prototype, "then", {
  get: function() {
    if (first) {
      first = false;
      g.return();
    }
    return;
  },
});
g.return();
```

Assertion failure for the completion type:
```js
async function* f() {}
const g = f();
let count = 0;
Object.defineProperty(Object.prototype, "then", {
  get: function() {
    if (count < 2) {
      count++;
      g.return();
    }
    return;
  },
});
g.next();
g.next();
g.return();
```

---

**Comment 23 — mgaudet@mozilla.com — 2024-06-12T06:00:23Z**

I will try to get these patches reviewed in the next day or so, but this may slip till next week due to TC39 -- having said that I'm also going to see about what's going on with this from committee perspective.

---

**Comment 24 — mgaudet@mozilla.com — 2024-06-12T06:55:14Z**

Hey Dan, 

So given that this is a Spec bug (and it has been suggested to me that there's at least one other vulnerable implementation), and there may be a spec fix available for this... I'd like to ask if you could help us with coordination, as you're our TG3 member :) 

Until we have some confidence that the spec fix will be good and we can coordinate landing, I'll plan on reviewing the existing patches, but the mechanics of how we'll land this are currently beyond me.

---

**Comment 25 — dveditz@mozilla.com — 2024-06-12T18:16:23Z**

Looks like you got in touch with TC39 overnight. 

> Until we have some confidence that the spec fix will be good and we can coordinate landing, I'll plan on reviewing the existing patches, but the mechanics of how we'll land this are currently beyond me.

We do need to coordinate to make sure we're not exposing other implementations, but how long will it take to fix the spec, implement the new spec, and test the new implementation? Coordination aside, would it make sense to
1. revert to the earlier behavior as in this set of patches to fix the security bug in Firefox, land on main + ESR115
2. In a new bug, implement the new spec.

Could we skip landing changes for the spec update (step 2) on ESR? from comment 9 it sounds like it won't be a web compatibility issue to leave it out if we've reverted to a state that looks more like what V8 and JSC have implemented. That's strictly from a "more change is more risk" base assumption, but maybe the updated spec will result in only a minor change from what we have before the reversion patches in this bug.

---

**Comment 26 — arai.unmht@gmail.com — 2024-06-12T23:47:31Z**

I agree with those 2 steps.

Especially given the spec fix is going to change the observable behavior compared to the previous way, e.g. ES2021 (which V8 and JSC would follow right now, and what SpiderMonkey implemented before bug 1724123), it won't fit uplift.

We should revert the behavior back to ES2021 for all supported branches, and after that,
implement the new spec on central in separate bug, so that even if the new spec change caused yet another regression, it won't affect other branches.

---

**Comment 27 — dveditz@mozilla.com — 2024-06-13T00:25:56Z**

Adding chromium and webkit bug links where they have been asked to confirm that they are not affected by this.

---

**Comment 28 — mgaudet@mozilla.com — 2024-06-13T05:28:57Z**

So I've asked Jan to also review this stack -- the nature of the partial revert is such that having more eyes is better here. The patches do highlight the revert a bit, and I'm not sure we should; similarly I'm not sure if it should land here or under a cover bug-- this is the closest I've ever seen to something that might make sense to cover?

---

**Comment 29 — arai.unmht@gmail.com — 2024-06-13T15:12:47Z**

Comment on attachment 9406866
Bug 1901411 - Part 1: Partially revert AsyncGeneratorDrainQueue to AsyncGeneratorResumeNext. r?mgaudet!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Not easy, given this patch just reverts the behavior to older spec, and the exploitable part about the promise handling isn't directly mentioned.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: beta, release, esr115
* **If not all supported branches, which bug introduced the flaw?**: Bug 1724123
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: The same patch is applicable to beta, release, and esr115.
* **How likely is this patch to cause regressions; how much testing does it need?**: Less likely.
This is basically a backout of bug 1724123 and small no-op refactoring for the definition order, function name, type name, comment etc, to reduce the diff.

About "Is the patch ready to land after security approval is given?" below, while the patch itself is ready, I've chosen "No" because this is a spec bug and we need to coordinate with TC39/TG3 and other implementers (at least Boa JS is affected) about when to land.
* **Is the patch ready to land after security approval is given?**: No
* **Is Android affected?**: Yes

---

**Comment 30 — dveditz@mozilla.com — 2024-06-19T03:41:57Z**

Boa is apparently landing a patch this weekend. Since this doesn't affect any major engine other than us I think it should be fine to land this as a "back-out" without going into detail about the fact that it's fundamentally a spec issue.

---

**Comment 31 — dveditz@mozilla.com — 2024-06-19T03:46:56Z**

Comment on attachment 9406866
Bug 1901411 - Part 1: Partially revert AsyncGeneratorDrainQueue to AsyncGeneratorResumeNext. r?mgaudet!

sec-approval+ = dveditz.

We clearly want to uplift this to beta and ESR. Should we also try to get this into the planned 127 point release, scheduled for June 25? Maybe not... they hadn't planned to do an ESR release, and they might even have builds in testing already (and if not then soon). We might want more fuzz-testing time on nightly before we ship this.

---

**Comment 32 — arai.unmht@gmail.com — 2024-06-19T05:19:28Z**

just for record.  I've found the following PR for Boa, that looks like a fix for this spec bug.
it's already public. and the code comment there slightly explains the issue.

https://github.com/boa-dev/boa/pull/3879

---

**Comment 33 — pulsebot@bmo.tld — 2024-06-19T18:58:13Z**

Pushed by arai_a@mac.com:
https://hg.mozilla.org/integration/autoland/rev/176552175727
Part 1: Partially revert AsyncGeneratorDrainQueue to AsyncGeneratorResumeNext. r=mgaudet,jandem
https://hg.mozilla.org/integration/autoland/rev/ac0ac74137df
Part 2: Fix sanity check for debugger. r=mgaudet
https://hg.mozilla.org/integration/autoland/rev/0932b09b1061
Part 3: Revert inlining of AsyncGeneratorDrainQueue in AsyncGeneratorNext. r=mgaudet,jandem
https://hg.mozilla.org/integration/autoland/rev/2e5903c1cfe4
Part 4: Revert inlining of AsyncGeneratorDrainQueue in AsyncGeneratorReturn. r=mgaudet,jandem
https://hg.mozilla.org/integration/autoland/rev/9029618226ce
Part 5: Revert inlining of AsyncGeneratorDrainQueue in AsyncGeneratorThrow. r=mgaudet,jandem
https://hg.mozilla.org/integration/autoland/rev/5379da5208ac
Part 6: Revert inlining of AsyncGeneratorDrainQueue in AsyncGeneratorYield. r=mgaudet,jandem

---

**Comment 34 — arai.unmht@gmail.com — 2024-06-19T21:36:06Z**

Comment on attachment 9406866
Bug 1901411 - Part 1: Partially revert AsyncGeneratorDrainQueue to AsyncGeneratorResumeNext. r?mgaudet!

### Beta/Release Uplift Approval Request
* **User impact if declined**: (I'm not using Lando because it doesn't support uplift for 6 patches)

Possible random pointer dereference and type confusion, just by visiting a crafted website.

The code itself is covered by existing automated tests, but the specific scenario isn't covered.
Testcase should be landed once this fix reaches all supported branches and also once the spec advisory becomes available.
* **Is this code covered by automated tests?**: No
* **Has the fix been verified in Nightly?**: No
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: none
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: This is essentially a backout of bug 1724123 patch
* **String changes made/needed**: none
* **Is Android affected?**: Yes

### ESR Uplift Approval Request
* **If this is not a sec:{high,crit} bug, please state case for ESR consideration**: this is sec-high
* **User impact if declined**: Possible random pointer dereference and type confusion, just by visiting a crafted website.
* **Fix Landed on Version**: 129
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: This is essentially a backout of bug 1724123 patch

---

**Comment 35 — arai.unmht@gmail.com — 2024-06-19T23:18:45Z**

something went wrong, but `approval-mozilla-beta?` is supposed to be added also for Parts 2-6.

---

**Comment 36 — aryx.bugmail@gmx-topmail.de — 2024-06-20T07:52:54Z**

https://hg.mozilla.org/mozilla-central/rev/176552175727
https://hg.mozilla.org/mozilla-central/rev/ac0ac74137df
https://hg.mozilla.org/mozilla-central/rev/0932b09b1061
https://hg.mozilla.org/mozilla-central/rev/2e5903c1cfe4
https://hg.mozilla.org/mozilla-central/rev/9029618226ce
https://hg.mozilla.org/mozilla-central/rev/5379da5208ac

---

**Comment 37 — ryanvm@gmail.com — 2024-06-20T17:51:09Z**

Comment on attachment 9406866
Bug 1901411 - Part 1: Partially revert AsyncGeneratorDrainQueue to AsyncGeneratorResumeNext. r?mgaudet!

Approved for 128.0b6.

---

**Comment 38 — pulsebot@bmo.tld — 2024-06-20T17:53:29Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/d1e9f6e04f87
https://hg.mozilla.org/releases/mozilla-beta/rev/cb8e5841fcb6
https://hg.mozilla.org/releases/mozilla-beta/rev/b31e6031f7f1
https://hg.mozilla.org/releases/mozilla-beta/rev/de4bd2d21631
https://hg.mozilla.org/releases/mozilla-beta/rev/28765eb2017e
https://hg.mozilla.org/releases/mozilla-beta/rev/11bc3719c557

---

**Comment 39 — dmeehan@mozilla.com — 2024-06-27T14:03:29Z**

Comment on attachment 9406866
Bug 1901411 - Part 1: Partially revert AsyncGeneratorDrainQueue to AsyncGeneratorResumeNext. r?mgaudet!

Approved for 115.13esr.

---

**Comment 40 — dmeehan@mozilla.com — 2024-06-27T14:03:33Z**

Comment on attachment 9406867
Bug 1901411 - Part 2: Fix sanity check for debugger. r?mgaudet!

Approved for 115.13esr.

---

**Comment 41 — dmeehan@mozilla.com — 2024-06-27T14:03:39Z**

Comment on attachment 9406868
Bug 1901411 - Part 3: Revert inlining of AsyncGeneratorDrainQueue in AsyncGeneratorNext. r?mgaudet!

Approved for 115.13esr.

---

**Comment 42 — dmeehan@mozilla.com — 2024-06-27T14:03:43Z**

Comment on attachment 9406869
Bug 1901411 - Part 4: Revert inlining of AsyncGeneratorDrainQueue in AsyncGeneratorReturn. r?mgaudet!

Approved for 115.13esr.

---

**Comment 43 — dmeehan@mozilla.com — 2024-06-27T14:03:47Z**

Comment on attachment 9406870
Bug 1901411 - Part 5: Revert inlining of AsyncGeneratorDrainQueue in AsyncGeneratorThrow. r?mgaudet!

Approved for 115.13esr.

---

**Comment 44 — dmeehan@mozilla.com — 2024-06-27T14:03:54Z**

Comment on attachment 9406871
Bug 1901411 - Part 6: Revert inlining of AsyncGeneratorDrainQueue in AsyncGeneratorYield. r?mgaudet!

Approved for 115.13esr.

---

**Comment 45 — pulsebot@bmo.tld — 2024-06-27T14:05:16Z**

https://hg.mozilla.org/releases/mozilla-esr115/rev/d382a54cc7f5
https://hg.mozilla.org/releases/mozilla-esr115/rev/773331445d0a
https://hg.mozilla.org/releases/mozilla-esr115/rev/7284a79c57d1
https://hg.mozilla.org/releases/mozilla-esr115/rev/f3a0dc06d81b
https://hg.mozilla.org/releases/mozilla-esr115/rev/7a21c5ed21b6
https://hg.mozilla.org/releases/mozilla-esr115/rev/f2d6693842ac

---

**Comment 46 — dveditz@mozilla.com — 2024-08-09T17:58:20Z**

We've reserved CVE-2024-7652 for the Firefox instance of this flaw.

---

**Comment 47 — tom@mozilla.com — 2024-09-06T18:17:57Z**

This has now been published: https://github.com/mozilla/foundation-security-advisories/commit/91adafacf06d678ecf9370a5fafda042ab676b86
