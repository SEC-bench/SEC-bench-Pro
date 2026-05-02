var my_simple_var_0;
var my_simple_var_1;
var my_simple_var_2;
var my_simple_var_3;
var my_simple_var_4;
var my_simple_var_5;
var my_simple_var_6;
var my_simple_var_7;
var my_simple_var_8;
var my_simple_var_9;
var my_simple_var_10;
var my_simple_var_11;
var my_simple_var_12;
var my_simple_var_13;
var my_simple_var_14;
var my_simple_var_15;
var my_simple_var_16;
var my_simple_var_17;
var my_simple_var_18;
var my_simple_var_19;
var my_simple_var_20;
var my_simple_var_21;
var my_simple_var_22;
var my_simple_var_23;
var my_simple_var_24;
var my_simple_var_25;
var my_simple_var_26;
var my_simple_var_27;
var my_simple_var_28;
var my_simple_var_29;
var my_simple_var_30;
var my_simple_var_31;
var my_simple_var_32;
var my_simple_var_33;
var my_simple_var_34;
var my_simple_var_35;
var my_simple_var_36;
var my_simple_var_37;
var my_simple_var_38;
var my_simple_var_39;
var my_simple_var_40;
var my_simple_var_41;
var my_simple_var_42;
var my_simple_var_43;
var my_simple_var_44;
var my_simple_var_45;
var my_simple_var_46;
var my_simple_var_47;
var my_simple_var_48;
var my_proxy_var_0 = new Proxy({}, {});
var assertFalse;
var assertNull;
var assertNotNull;
var assertThrows;
var assertException;
var assertThrowsEquals;
var assertThrowsAsync;
var assertDoesNotThrow;
var assertEarlyError;
var assertThrowsAtRuntime;
var assertInstanceof;
var assertUnreachable;
var assertOptimized;
var assertUnoptimized;
var assertContains;
var assertMatches;
var assertPromiseResult;
var promiseTestChain;

var V8OptimizationStatus = {
  kIsFunction: 1 << 0,
  kNeverOptimize: 1 << 1,
  kAlwaysOptimize: 1 << 2,
  kMaybeDeopted: 1 << 3,
  kOptimized: 1 << 4,
  kMaglevved: 1 << 5,
  kTurboFanned: 1 << 6,
  kInterpreted: 1 << 7,
  kMarkedForOptimization: 1 << 8,
  kMarkedForConcurrentOptimization: 1 << 9,
  kOptimizingConcurrently: 1 << 10,
  kIsExecuting: 1 << 11,
  kTopmostFrameIsTurboFanned: 1 << 12,
  kLiteMode: 1 << 13,
  kMarkedForDeoptimization: 1 << 14,
  kBaseline: 1 << 15,
  kTopmostFrameIsInterpreted: 1 << 16,
  kTopmostFrameIsBaseline: 1 << 17,
  kIsLazy: 1 << 18,
  kTopmostFrameIsMaglev: 1 << 19,
  kOptimizeOnNextCallOptimizesToMaglev: 1 << 20,
};

var isNeverOptimizeLiteMode;
var isNeverOptimize;
var isAlwaysOptimize;
var isLazy;
var isInterpreted;
var isBaseline;
var isUnoptimized;
var isOptimized;
var willBeMaglevved;
var willBeTurbofanned;
var isMaglevved;
var isTurboFanned;
var topFrameIsInterpreted;
var topFrameIsBaseline;
var topFrameIsMaglevved;
var topFrameIsTurboFanned;
var failWithMessage;
var formatFailureText;
var prettyPrinted;

function __isPropertyOfType(obj, name, type) {
  let desc;
  try {
    desc = Object.getOwnPropertyDescriptor(obj, name);
  } catch (e) {
  }
  return typeof type === 'undefined' || typeof desc.value === type;
}
function __getProperties(obj, type) {
  let properties = [];
  for (let name of Object.getOwnPropertyNames(obj)) {
    if (__isPropertyOfType(obj, name, type)) properties.push(name);
  }
  let proto = Object.getPrototypeOf(obj);
  while (proto && proto != Object.prototype) {
    Object.getOwnPropertyNames(proto).forEach(name => {
      if (name !== 'constructor') {
        if (__isPropertyOfType(proto, name, type)) {
          properties.push(name);
        }
      }
    });
    proto = Object.getPrototypeOf(proto);
  }
  return properties;
}

function* __getObjects(root = this, level = 0) {
  let obj_names = __getProperties(root, 'object');
  for (let obj_name of obj_names) {
    let obj = root[obj_name];
    if (obj === root) continue;
    yield obj;
    yield* __getObjects(obj, level + 1);
  }
}

function __getRandomObject(seed) {
  let objects = [];
  for (let obj of __getObjects()) {
    objects.push(obj);
  }
}

function __getRandomProperty(obj, seed) {
  let properties = __getProperties(obj);
}

function triggerFunction(obj, seed, ...args) {
  let functions = __getProperties(obj, 'function');
  try {
   obj.toString(...args);
  } catch (e) {}
}

let __v_1;
function __f_0() {
  let __v_2 = __v_1;

  for (var i = 0; i < 100; i++) { 
    --__v_1;
    __v_2 += __v_1;
    console.log(i);
    console.log(__v_1);
    triggerFunction(10000000, 456109613, __v_1,   Math.PI, __getRandomObject(5161),__v_2, __getRandomObject(639756),new Number(), undefined,undefined, undefined, undefined);
    let pr =  __getRandomProperty(__v_1, 958816);
    let pr2 = __getRandomProperty(__v_2, 0);
    delete __v_2[pr2];
  }
}

function __f_1() {
  %PrepareFunctionForOptimization(__f_0);  
  __f_0();
  %OptimizeMaglevOnNextCall(__f_0);
  __v_1 = 1073751824;
  __f_0();
}

__f_1();
