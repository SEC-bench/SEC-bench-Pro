function main() {
    // Large sizes to increase memcpy time and OOB impact.
    const initialSize = 512 * 1024;
    const maxSize = 2 * initialSize;
    const newSize = maxSize;
    const syncSAB = new SharedArrayBuffer(4);
    const sync = new Int32Array(syncSAB);
    // States: 0=init, 1=worker ready, 2=main ready (grow now)
    const workerScript = `
        onmessage = function(e) {
            const gsab = e.data.gsab;
            const newSize = e.data.newSize;
            const sync = new Int32Array(e.data.sync);
            Atomics.store(sync, 0, 1);
            Atomics.notify(sync, 0);
            Atomics.wait(sync, 0, 1);
            gsab.grow(newSize);
            postMessage("done");
        };
    `;
    for (let i = 0; i < 100; i++) {
        // Reset synchronization state.
        Atomics.store(sync, 0, 0);
        let gsab_i = new SharedArrayBuffer(initialSize, { maxByteLength: maxSize });
        const ta_i = new Int8Array(gsab_i);
        const worker = new Worker(workerScript, { type: 'string' });
        worker.postMessage({ gsab: gsab_i, newSize: newSize, sync: syncSAB });
        // Wait for worker to become ready.
        while (Atomics.load(sync, 0) !== 1) { }
        // Signal worker to resize buffer.
        Atomics.store(sync, 0, 2);
        Atomics.notify(sync, 0);
        ta_i.sort();
        worker.getMessage();
        worker.terminate();
    }
}
main();
