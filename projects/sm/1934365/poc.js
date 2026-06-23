evalInWorker(`
    function c() {
      d = new AsyncDisposableStack
      d.defer(() => e)
      d.defer(() => c())
      d.disposeAsync()
    } c();
`)
