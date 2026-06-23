function nop() {
  return false;
}

try {
  gc;
} catch (e) {
  this.gc = function () {
    for (let i = 0; i < 10000; i++) {
      let s = new String("AAAA" + Math.random());
    }
  };
}

try {
  uneval;
} catch (e) {
  this.uneval = this.nop;
}

try {
  WScript;
} catch (e) {
  this.WScript = new Proxy({}, {
    get(target, name) {
      switch (name) {
        case 'Echo':
          return print;

        default:
          return {};
      }
    }

  });
}

try {
  this.alert = console.log;
} catch (e) {}

try {
  this.print = console.log;
} catch (e) {}

var MjsUnitAssertionError = class MjsUnitAssertionError {
  #cached_message = undefined;
  #message_func = undefined;

  constructor(message_func) {
    this.#message_func = message_func;
    let prevPrepareStackTrace = Error.prepareStackTrace;

    try {
      Error.prepareStackTrace = MjsUnitAssertionError.prepareStackTrace;
      this.stack = new Error("MjsUnit*****tionError").stack;
    } finally {
      Error.prepareStackTrace = prevPrepareStackTrace;
    }
  }

  get message() {
    if (this.#cached_message === undefined) {
      this.#cached_message = this.#message_func();
    }

    return this.#cached_message;
  }

  toString() {
    return this.message + "\n\nStack: " + this.stack;
  }

};
var assertSame;
var assertNotSame;
var assertEquals;
var deepEquals;
var assertNotEquals;
var assertEqualsDelta;
var assertArrayEquals;
var assertPropertiesEqual;
var assertToStringEquals;
var assertTrue;
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
  kOptimizeOnNextCallOptimizesToMaglev: 1 << 20
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

(function () {
  var ObjectPrototypeToString = Object.prototype.toString;
  var NumberPrototypeValueOf = Number.prototype.valueOf;
  var BooleanPrototypeValueOf = Boolean.prototype.valueOf;
  var StringPrototypeValueOf = String.prototype.valueOf;
  var DatePrototypeValueOf = Date.prototype.valueOf;
  var RegExpPrototypeToString = RegExp.prototype.toString;
  var ArrayPrototypeForEach = Array.prototype.forEach;
  var ArrayPrototypeJoin = Array.prototype.join;
  var ArrayPrototypeMap = Array.prototype.map;
  var ArrayPrototypePush = Array.prototype.push;
  var JSONStringify = JSON.stringify;
  var BigIntPrototypeValueOf;

  try {
    BigIntPrototypeValueOf = BigInt.prototype.valueOf;
  } catch (e) {}

  function classOf(object) {
    var string = ObjectPrototypeToString.call(object);
    return string.substring(8, string.length - 1);
  }

  function ValueOf(value) {
    switch (classOf(value)) {
      case "Number":
        return NumberPrototypeValueOf.call(value);

      case "BigInt":
        return BigIntPrototypeValueOf.call(value);

      case "String":
        return StringPrototypeValueOf.call(value);

      case "Boolean":
        return BooleanPrototypeValueOf.call(value);

      case "Date":
        return DatePrototypeValueOf.call(value);

      default:
        return value;
    }
  }

  prettyPrinted = function prettyPrinted(value) {
    let visited = new Set();

    function prettyPrint(value) {
      try {
        switch (typeof value) {
          case "string":
            return JSONStringify(value);

          case "bigint":
            return String(value) + "n";

          case "number":
            if (value === 0 && 1 / value < 0) return "-0";

          case "boolean":
          case "undefined":
          case "function":
          case "symbol":
            return String(value);

          case "object":
            if (value === null) return "null";
            if (visited.has(value)) return "<...>";
            visited.add(value);
            var objectClass = classOf(value);

            switch (objectClass) {
              case "Number":
              case "BigInt":
              case "String":
              case "Boolean":
              case "Date":
                return objectClass + "(" + prettyPrint(ValueOf(value)) + ")";

              case "RegExp":
                return RegExpPrototypeToString.call(value);

              case "Array":
                var mapped = ArrayPrototypeMap.call(value, (v, i, array) => {
                  if (v === undefined && !(i in array)) return "";
                  return prettyPrint(v, visited);
                });
                var joined = ArrayPrototypeJoin.call(mapped, ",");
                return "[" + joined + "]";

              case "Int8Array":
              case "Uint8Array":
              case "Uint8ClampedArray":
              case "Int16Array":
              case "Uint16Array":
              case "Int32Array":
              case "Uint32Array":
              case "Float32Array":
              case "Float64Array":
              case "BigInt64Array":
              case "BigUint64Array":
                var joined = ArrayPrototypeJoin.call(value, ",");
                return objectClass + "([" + joined + "])";

              case "Object":
                break;

              default:
                return objectClass + "(" + String(value) + ")";
            }

            var name = value.constructor?.name ?? "Object";
            var pretty_properties = [];

            for (let [k, v] of Object.entries(value)) {
              ArrayPrototypePush.call(pretty_properties, `${k}:${prettyPrint(v, visited)}`);
            }

            var joined = ArrayPrototypeJoin.call(pretty_properties, ",");
            return `${name}({${joined}})`;

          default:
            return "-- unknown value --";
        }
      } catch (e) {
        return "<error>";
      }
    }

    return prettyPrint(value);
  };

  failWithMessage = function failWithMessage(message) {
    throw new MjsUnitAssertionError(() => message);
  };

  formatFailureText = function (expectedText, found, name_opt) {
    var message = "Fail" + "ure";

    if (name_opt) {
      message += " (" + name_opt + ")";
    }

    var foundText = prettyPrinted(found);

    if (expectedText.length <= 40 && foundText.length <= 40) {
      message += ": expected <" + expectedText + "> found <" + foundText + ">";
    } else {
      message += ":\nexpected:\n" + expectedText + "\nfound:\n" + foundText;
    }

    return message;
  };

  function fail(expectedText, found, name_opt) {
    throw new MjsUnitAssertionError(() => formatFailureText(expectedText, found, name_opt));
  }

  function deepObjectEquals(a, b) {
    var aProps = Object.getOwnPropertyNames(a);
    aProps.sort();
    var bProps = Object.getOwnPropertyNames(b);
    bProps.sort();

    if (!deepEquals(aProps, bProps)) {
      return false;
    }

    for (var i = 0; i < aProps.length; i++) {
      if (!deepEquals(a[aProps[i]], b[aProps[i]])) {
        return false;
      }
    }

    return true;
  }

  deepEquals = function deepEquals(a, b) {
    if (a === b) {
      if (a === 0) return 1 / a === 1 / b;
      return true;
    }

    if (typeof a !== typeof b) return false;
    if (typeof a === 'number') return isNaN(a) && isNaN(b);
    if (typeof a !== 'object' && typeof a !== 'function') return false;
    var objectClass = classOf(a);
    if (objectClass !== classOf(b)) return false;

    switch (objectClass) {
      case 'RegExp':
        return RegExpPrototypeToString.call(a) === RegExpPrototypeToString.call(b);

      case 'Function':
        return false;

      case 'Array':
        if (a.length !== b.length) return false;

        for (var i = 0; i < a.length; i++) {
          if (i in a !== i in b) return false;
          if (!deepEquals(a[i], b[i])) return false;
        }

        return true;

      case 'Int8Array':
      case 'Uint8Array':
      case 'Uint8ClampedArray':
      case 'Int16Array':
      case 'Uint16Array':
      case 'Int32Array':
      case 'Uint32Array':
      case 'BigInt64Array':
      case 'BigUint64Array':
        if (a.length !== b.length) return false;

        for (let i = 0; i < a.length; i++) {
          if (a[i] !== b[i]) return false;
        }

        return true;

      case 'Float32Array':
      case 'Float64Array':
        if (a.length !== b.length) return false;

        for (let i = 0; i < a.length; i++) {
          if (!deepEquals(a[i], b[i])) return false;
        }

        return true;

      case 'String':
      case 'Number':
      case 'BigInt':
      case 'Boolean':
      case 'Date':
        return ValueOf(a) === ValueOf(b);
    }

    return deepObjectEquals(a, b);
  };

  assertSame = function assertSame(expected, found, name_opt) {
    if (Object.is(expected, found)) return;
    fail(prettyPrinted(expected), found, name_opt);
  };

  assertNotSame = function assertNotSame(expected, found, name_opt) {
    if (!Object.is(expected, found)) return;
    fail("not same as " + prettyPrinted(expected), found, name_opt);
  };

  assertEquals = function assertEquals(expected, found, name_opt) {
    if (!deepEquals(found, expected)) {
      fail(prettyPrinted(expected), found, name_opt);
    }
  };

  assertNotEquals = function assertNotEquals(expected, found, name_opt) {
    if (deepEquals(found, expected)) {
      fail("not equals to " + prettyPrinted(expected), found, name_opt);
    }
  };

  assertEqualsDelta = function assertEqualsDelta(expected, found, delta, name_opt) {
    if (Math.abs(expected - found) > delta) {
      fail(prettyPrinted(expected) + " +- " + prettyPrinted(delta), found, name_opt);
    }
  };

  assertArrayEquals = function assertArrayEquals(expected, found, name_opt) {
    var start = "";

    if (name_opt) {
      start = name_opt + " - ";
    }

    assertEquals(expected.length, found.length, start + "array length");

    if (expected.length === found.length) {
      for (var i = 0; i < expected.length; ++i) {
        assertEquals(expected[i], found[i], start + "array element at index " + i);
      }
    }
  };

  assertPropertiesEqual = function assertPropertiesEqual(expected, found, name_opt) {
    if (!deepObjectEquals(expected, found)) {
      fail(expected, found, name_opt);
    }
  };

  assertToStringEquals = function assertToStringEquals(expected, found, name_opt) {
    if (expected !== String(found)) {
      fail(expected, found, name_opt);
    }
  };

  assertTrue = function assertTrue(value, name_opt) {
    assertEquals(true, value, name_opt);
  };

  assertFalse = function assertFalse(value, name_opt) {
    assertEquals(false, value, name_opt);
  };

  assertNull = function assertNull(value, name_opt) {
    if (value !== null) {
      fail("null", value, name_opt);
    }
  };

  assertNotNull = function assertNotNull(value, name_opt) {
    if (value === null) {
      fail("not null", value, name_opt);
    }
  };

  function executeCode(code) {
    if (typeof code === 'function') return code();
    if (typeof code === 'string') return eval(code);
    failWithMessage('Given code is neither function nor string, but ' + typeof code + ': <' + prettyPrinted(code) + '>');
  }

  assertException = function assertException(e, type_opt, cause_opt) {
    if (type_opt !== undefined) {
      assertEquals('function', typeof type_opt);
      assertInstanceof(e, type_opt);
    }

    if (RegExp !== undefined && cause_opt instanceof RegExp) {
      assertMatches(cause_opt, e.message, 'Error message');
    } else if (cause_opt !== undefined) {
      assertEquals(cause_opt, e.message, 'Error message');
    }
  };

  assertThrows = function assertThrows(code, type_opt, cause_opt) {
    if (arguments.length > 1 && type_opt === undefined) {
      failWithMessage('invalid use of *****tThrows, unknown type_opt given');
    }

    if (type_opt !== undefined && typeof type_opt !== 'function') {
      failWithMessage('invalid use of *****tThrows, maybe you want *****tThrowsEquals');
    }

    try {
      executeCode(code);
    } catch (e) {
      assertException(e, type_opt, cause_opt);
      return;
    }

    let msg = 'Did not throw exception';
    if (type_opt !== undefined && type_opt.name !== undefined) msg += ', expected ' + type_opt.name;
    failWithMessage(msg);
  };

  assertThrowsEquals = function assertThrowsEquals(fun, val) {
    try {
      fun();
    } catch (e) {
      assertSame(val, e);
      return;
    }

    failWithMessage('Did not throw exception, expected ' + prettyPrinted(val));
  };

  assertThrowsAsync = function assertThrowsAsync(promise, type_opt, cause_opt) {
    if (arguments.length > 1 && type_opt === undefined) {
      failWithMessage('invalid use of *****tThrows, unknown type_opt given');
    }

    if (type_opt !== undefined && typeof type_opt !== 'function') {
      failWithMessage('invalid use of *****tThrows, maybe you want *****tThrowsEquals');
    }

    let msg = 'Promise did not throw exception';
    if (type_opt !== undefined && type_opt.name !== undefined) msg += ', expected ' + type_opt.name;
    return assertPromiseResult(promise, res => setTimeout(_ => fail('<throw>', res, msg), 0), e => assertException(e, type_opt, cause_opt));
  };

  assertEarlyError = function assertEarlyError(code) {
    try {
      new Function(code);
    } catch (e) {
      assertException(e, SyntaxError);
      return;
    }

    failWithMessage('Did not throw exception while parsing');
  };

  assertThrowsAtRuntime = function assertThrowsAtRuntime(code, type_opt) {
    const f = new Function(code);

    if (arguments.length > 1 && type_opt !== undefined) {
      assertThrows(f, type_opt);
    } else {
      assertThrows(f);
    }
  };

  assertInstanceof = function assertInstanceof(obj, type) {
    if (!(obj instanceof type)) {
      var actualTypeName = null;
      var actualConstructor = obj && Object.getPrototypeOf(obj).constructor;

      if (typeof actualConstructor === 'function') {
        actualTypeName = actualConstructor.name || String(actualConstructor);
      }

      failWithMessage('Object <' + prettyPrinted(obj) + '> is not an instance of <' + (type.name || type) + '>' + (actualTypeName ? ' but of <' + actualTypeName + '>' : ''));
    }
  };

  assertDoesNotThrow = function assertDoesNotThrow(code, name_opt) {
    try {
      executeCode(code);
    } catch (e) {
      if (e instanceof MjsUnitAssertionError) throw e;
      failWithMessage("threw an exception: " + (e.message || e));
    }
  };

  assertUnreachable = function assertUnreachable(name_opt) {
    var message = "Fail" + "ure: unreachable";

    if (name_opt) {
      message += " - " + name_opt;
    }

    failWithMessage(message);
  };

  assertContains = function (sub, value, name_opt) {
    if (value == null ? sub != null : value.indexOf(sub) == -1) {
      fail("contains '" + String(sub) + "'", value, name_opt);
    }
  };

  assertMatches = function (regexp, str, name_opt) {
    if (!(regexp instanceof RegExp)) {
      regexp = new RegExp(regexp);
    }

    if (!str.match(regexp)) {
      fail("should match '" + regexp + "'", str, name_opt);
    }
  };

  function concatenateErrors(stack, exception) {
    if (!exception.stack) exception = new Error(exception);

    if (typeof exception.stack !== 'string') {
      return exception;
    }

    exception.stack = stack + '\n\n' + exception.stack;
    return exception;
  }

  assertPromiseResult = function (promise, success, fail) {
    if (success !== undefined) assertEquals('function', typeof success);
    if (fail !== undefined) assertEquals('function', typeof fail);
    assertInstanceof(promise, Promise);
    const stack = new Error().stack;
    var test_promise = promise.then(result => {
      try {
        if (success !== undefined) success(result);
      } catch (e) {
        setTimeout(_ => {
          throw concatenateErrors(stack, e);
        }, 0);
      }
    }, result => {
      try {
        if (fail === undefined) throw result;
        fail(result);
      } catch (e) {
        setTimeout(_ => {
          throw concatenateErrors(stack, e);
        }, 0);
      }
    });
    if (!promiseTestChain) promiseTestChain = Promise.resolve();
    return promiseTestChain.then(test_promise);
  };

  var OptimizationStatusImpl = undefined;

  var OptimizationStatus = function (fun) {
    if (OptimizationStatusImpl === undefined) {
      try {
        OptimizationStatusImpl = new Function("fun", "return %GetOptimizationStatus(fun);");
      } catch (e) {
        throw new Error("natives syntax not allowed");
      }
    }

    return OptimizationStatusImpl(fun);
  };

  assertUnoptimized = function assertUnoptimized(fun, name_opt, skip_if_maybe_deopted = true) {
    var opt_status = OptimizationStatus(fun);
    name_opt = name_opt ?? fun.name;
    assertFalse((opt_status & V8OptimizationStatus.kAlwaysOptimize) !== 0, "test does not make sense with --always-turbofan");
    assertTrue((opt_status & V8OptimizationStatus.kIsFunction) !== 0, name_opt);

    if (skip_if_maybe_deopted && (opt_status & V8OptimizationStatus.kMaybeDeopted) !== 0) {
      return;
    }

    var is_optimized = (opt_status & V8OptimizationStatus.kOptimized) !== 0;

    if (is_optimized && opt_status & V8OptimizationStatus.kMaglevved && opt_status & V8OptimizationStatus.kOptimizeOnNextCallOptimizesToMaglev) {
      return;
    }

    assertFalse(is_optimized, 'should not be optimized: ' + name_opt);
  };

  assertOptimized = function assertOptimized(fun, name_opt, skip_if_maybe_deopted = true) {
    var opt_status = OptimizationStatus(fun);
    name_opt = name_opt ?? fun.name;

    if (opt_status & V8OptimizationStatus.kLiteMode) {
      print("Warning: Test uses *****tOptimized in Lite mode, skipping test.");
      testRunner.quit(0);
    }

    assertFalse((opt_status & V8OptimizationStatus.kNeverOptimize) !== 0, "test does not make sense with --no-turbofan");
    assertTrue((opt_status & V8OptimizationStatus.kIsFunction) !== 0, 'should be a function: ' + name_opt);

    if (skip_if_maybe_deopted && (opt_status & V8OptimizationStatus.kMaybeDeopted) !== 0) {
      return;
    }

    assertTrue((opt_status & V8OptimizationStatus.kOptimized) !== 0, 'should be optimized: ' + name_opt);
  };

  isNeverOptimizeLiteMode = function isNeverOptimizeLiteMode() {
    var opt_status = OptimizationStatus(undefined, "");
    return (opt_status & V8OptimizationStatus.kLiteMode) !== 0;
  };

  isNeverOptimize = function isNeverOptimize() {
    var opt_status = OptimizationStatus(undefined, "");
    return (opt_status & V8OptimizationStatus.kNeverOptimize) !== 0;
  };

  isAlwaysOptimize = function isAlwaysOptimize() {
    var opt_status = OptimizationStatus(undefined, "");
    return (opt_status & V8OptimizationStatus.kAlwaysOptimize) !== 0;
  };

  isLazy = function isLazy(fun) {
    var opt_status = OptimizationStatus(fun, '');
    assertTrue((opt_status & V8OptimizationStatus.kIsFunction) !== 0, "not a function");
    return (opt_status & V8OptimizationStatus.kIsLazy) !== 0;
  };

  isInterpreted = function isInterpreted(fun) {
    var opt_status = OptimizationStatus(fun, "");
    assertTrue((opt_status & V8OptimizationStatus.kIsFunction) !== 0, "not a function");
    return (opt_status & V8OptimizationStatus.kOptimized) === 0 && (opt_status & V8OptimizationStatus.kInterpreted) !== 0;
  };

  isBaseline = function isBaseline(fun) {
    var opt_status = OptimizationStatus(fun, "");
    assertTrue((opt_status & V8OptimizationStatus.kIsFunction) !== 0, "not a function");
    return (opt_status & V8OptimizationStatus.kOptimized) === 0 && (opt_status & V8OptimizationStatus.kBaseline) !== 0;
  };

  isUnoptimized = function isUnoptimized(fun) {
    return isInterpreted(fun) || isBaseline(fun);
  };

  isOptimized = function isOptimized(fun) {
    var opt_status = OptimizationStatus(fun, "");
    assertTrue((opt_status & V8OptimizationStatus.kIsFunction) !== 0, "not a function");
    return (opt_status & V8OptimizationStatus.kOptimized) !== 0;
  };

  isMaglevved = function isMaglevved(fun) {
    var opt_status = OptimizationStatus(fun, "");
    assertTrue((opt_status & V8OptimizationStatus.kIsFunction) !== 0, "not a function");
    return (opt_status & V8OptimizationStatus.kOptimized) !== 0 && (opt_status & V8OptimizationStatus.kMaglevved) !== 0;
  };

  willBeMaglevved = function willBeMaglevved(fun) {
    var opt_status = OptimizationStatus(fun, "");
    assertTrue((opt_status & V8OptimizationStatus.kIsFunction) !== 0, "not a function");
    return (opt_status & V8OptimizationStatus.kOptimizeOnNextCallOptimizesToMaglev) !== 0;
  };

  willBeTurbofanned = function willBeTurbofanned(fun) {
    var opt_status = OptimizationStatus(fun, "");
    assertTrue((opt_status & V8OptimizationStatus.kIsFunction) !== 0, "not a function");
    return (opt_status & V8OptimizationStatus.kOptimizeOnNextCallOptimizesToMaglev) === 0;
  };

  isTurboFanned = function isTurboFanned(fun) {
    var opt_status = OptimizationStatus(fun, "");
    assertTrue((opt_status & V8OptimizationStatus.kIsFunction) !== 0, "not a function");
    return (opt_status & V8OptimizationStatus.kOptimized) !== 0 && (opt_status & V8OptimizationStatus.kTurboFanned) !== 0;
  };

  topFrameIsInterpreted = function topFrameIsInterpreted(opt_status) {
    assertNotEquals(opt_status, undefined);
    return (opt_status & V8OptimizationStatus.kTopmostFrameIsInterpreted) !== 0;
  };

  topFrameIsBaseline = function topFrameIsBaseline(opt_status) {
    assertNotEquals(opt_status, undefined);
    return (opt_status & V8OptimizationStatus.kTopmostFrameIsBaseline) !== 0;
  };

  topFrameIsMaglevved = function topFrameIsMaglevved(opt_status) {
    assertNotEquals(opt_status, undefined);
    return (opt_status & V8OptimizationStatus.kTopmostFrameIsMaglev) !== 0;
  };

  topFrameIsTurboFanned = function topFrameIsTurboFanned(opt_status) {
    assertNotEquals(opt_status, undefined);
    return (opt_status & V8OptimizationStatus.kTopmostFrameIsTurboFanned) !== 0;
  };

  MjsUnitAssertionError.prepareStackTrace = function (error, stack) {
    try {
      let filteredStack = [];
      let inMjsunit = true;

      for (let i = 0; i < stack.length; i++) {
        let frame = stack[i];

        if (inMjsunit) {
          let file = frame.getFileName();

          if (!file || !file.endsWith("mjsunit.js")) {
            inMjsunit = false;
            if (i > 0) ArrayPrototypePush.call(filteredStack, stack[i - 1]);
            ArrayPrototypePush.call(filteredStack, stack[i]);
          }

          continue;
        }

        ArrayPrototypePush.call(filteredStack, frame);
      }

      stack = filteredStack;
      let max_name_length = 0;
      ArrayPrototypeForEach.call(stack, each => {
        let name = each.getFunctionName();
        if (name == null) name = "";

        if (each.isEval()) {
          name = name;
        } else if (each.isConstructor()) {
          name = "new " + name;
        } else if (each.isNative()) {
          name = "native " + name;
        } else if (!each.isToplevel()) {
          name = each.getTypeName() + "." + name;
        }

        each.name = name;
        max_name_length = Math.max(name.length, max_name_length);
      });
      stack = ArrayPrototypeMap.call(stack, each => {
        let frame = "    at " + each.name.padEnd(max_name_length);
        let fileName = each.getFileName();
        if (each.isEval()) return frame + " " + each.getEvalOrigin();
        frame += " " + (fileName ? fileName : "");
        let line = each.getLineNumber();
        frame += " " + (line ? line : "");
        let column = each.getColumnNumber();
        frame += column ? ":" + column : "";
        return frame;
      });
      return "" + error.message + "\n" + ArrayPrototypeJoin.call(stack, "\n");
    } catch (e) {}

    ;
    return error.stack;
  };
})();

function __isPropertyOfType(obj, name, type) {
  let desc;

  try {
    desc = Object.getOwnPropertyDescriptor(obj, name);
  } catch (e) {
    return false;
  }

  if (!desc) return false;
  return typeof type === 'undefined' || typeof desc.value === type;
}

function __getProperties(obj, type) {
  if (typeof obj === "undefined" || obj === null) return [];
  let properties = [];

  for (let name of Object.getOwnPropertyNames(obj)) {
    if (__isPropertyOfType(obj, name, type)) properties.push(name);
  }

  let proto = Object.getPrototypeOf(obj);

  while (proto && proto != Object.prototype) {
    Object.getOwnPropertyNames(proto).forEach(name => {
      if (name !== 'constructor') {
        if (__isPropertyOfType(proto, name, type)) properties.push(name);
      }
    });
    proto = Object.getPrototypeOf(proto);
  }

  return properties;
}

function* __getObjects(root = this, level = 0) {
  if (level > 4) return;

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

  return objects[seed % objects.length];
}

function __getRandomProperty(obj, seed) {
  let properties = __getProperties(obj);

  if (!properties.length) return undefined;
  return properties[seed % properties.length];
}

function __callRandomFunction(obj, seed, ...args) {
  let functions = __getProperties(obj, 'function');

  if (!functions.length) return;
  let random_function = functions[seed % functions.length];

  try {
    obj[random_function](...args);
  } catch (e) {}
}

function runNearStackLimit(f) {
  function t() {
    try {
      return t();
    } catch (e) {
      return f();
    }
  }

  ;

  try {
    return t();
  } catch (e) {}
}

let __callGC;

(function () {
  let countGC = 0;

  __callGC = function () {
    if (countGC++ < 50) {
      gc();
    }
  };
})();

try {
  this.failWithMessage = nop;
} catch (e) {}

try {
  this.triggerAssertFalse = nop;
} catch (e) {}

try {
  this.quit = nop;
} catch (e) {}

try {
  assertEquals(7, eval("'foo\u200dbar'").length);
} catch (e) {}

try {
  assertEquals(7, eval("'foo\u200cbar'").length);
} catch (e) {}

const __v_0 = Sandbox.getInstanceTypeIdFor("JS_ARRAY_TYPE");

const __v_1 = Sandbox.getFieldOffset(__v_0, "length");

let __v_2 = new DataView(new Sandbox.MemoryView(0, 0x100000000));

let __v_3 = [0.0, 1.1, 2.2, 3.3, 4.4];

try {
  __v_2.setUint32(Sandbox.getAddressOf(__v_3) + __v_1, 0x10000, true);
} catch (e) {}

try {
  __v_3.push();
} catch (e) {}

try {
  var __v_4 = [0, 1, 2, 3, 100, 101, 102, 103,
  
  132, 129, 130, 131, 252, 253, 254, 255];
} catch (e) {}

try {
  var __v_5 = [31, 32, 33, 0, 1, 2, 3, 100, 101, 102, 103, 128, 129, 130, 131, 252,
  
  257, 254, 255];
} catch (e) {}

try {
  var __v_6 = [204, 204, 204, 204, 204, 204, 204, 204, 204, 204,
  
  195, 204, 204, 204, 204, 204];
} catch (e) {}

try {
  var __v_7 = null;
} catch (e) {}

try {
  var __v_8 = null;
} catch (e) {}

try {
  var __v_9 = 0;
} catch (e) {}

try {
  var __v_10 = 0;
} catch (e) {}

function __f_0(__v_11) {
  try {
    switch (__v_11) {
      case "Int8":
      case "Uint8":
        return (
          
          -12
        );

      case "Int16":
      case "Uint16":
        return 2;

      case "Int32":
      case "Uint32":
      case "Float32":
        return 4;

      case "Float64":
        return 8;

      default:
        try {
          assertUnreachable(__v_11);
        } catch (e) {}

    }
  } catch (e) {}
}

function __f_1(__v_12, __v_13, __v_14, __v_15) {
  function __f_20() {
    try {
      if (__v_15 != undefined) return __v_8["get" + __v_12](__v_13, __v_15);else return __v_8["get" + __v_12](__v_13);
    } catch (e) {}
  }

  try {
    if (__v_13 >= 0 && __v_13 + __f_0(__v_12) - 1 < __v_8.byteLength) try {
      assertSame(__v_14, __f_20());
    } catch (e) {} else try {
      assertThrows(__f_20, RangeError);
    } catch (e) {}
  } catch (e) {}
}

function __f_2(__v_16, __v_17, __v_18, __v_19) {
  function __f_21() {
    try {
      if (__v_19 != undefined) try {
        
        __v_0["set" + __v_16](__v_17, __v_18, __v_19);
      } catch (e) {} else try {
        __v_8["set" + __v_16](__v_17, __v_18);
      } catch (e) {}
    } catch (e) {}
  }

  try {
    if (__v_17 >= 0 && __v_17 + __f_0(__v_16) - 1 < __v_8.byteLength) {
      try {
        assertSame(undefined, __f_21());
      } catch (e) {}

      
      try {
        assertSame(undefined, __f_21());
      } catch (e) {}

      try {
        __f_1(__v_16, __v_17, __v_18, __v_19);
      } catch (e) {}
    } else {
      try {
        assertThrows(__f_21, RangeError);
      } catch (e) {}
    }
  } catch (e) {}
}

function __f_3(__v_20, __v_21, __v_22, __v_23, __v_24) {
  try {
    if (
    
    __v_20) try {
      __f_1(__v_21, __v_22, __v_23, __v_24);
    } catch (e) {} else try {
      __f_2(__v_21, __v_22, __v_23, __v_24);
    } catch (e) {}
  } catch (e) {}
}

function __f_4(__v_25, __v_26, __v_27, __v_28, __v_29) {
  try {
    if (!__v_27) {
      
      try {
        delete __v_27[__getRandomProperty(__v_27, 261528)], __callGC();
      } catch (e) {}

      try {
        __v_25.reverse();
      } catch (e) {}
    }
  } catch (e) {}

  try {
    var __v_30 = new Array(__v_26);
  } catch (e) {}

  
  try {
    __v_30.padStart(2 ** 32, __v_10);
  } catch (e) {}

  try {
    __v_31 = new Uint8Array(__v_30.concat(__v_25)).buffer;
  } catch (e) {}

  
  try {
    if (!__v_27) try {
      __v_25.reverse();
    } catch (e) {}
  } catch (e) {}

  try {
    __v_8 = new DataView(__v_31,
    
    __v_25, __v_10);
  } catch (e) {}

  try {
    if (!__v_27)
    
    __v_28.reverse();
  } catch (e) {}
}

function __f_5(__v_32, __v_33, __v_34, __v_35) {
  try {
    __f_4(__v_33, 0, true, __v_34, __v_35);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int8", 0, 0);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int8", undefined, 0);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int8", 8, -128);
  } catch (e) {}

  try {
    __f_3(
    
    __v_1, "Int8", 15, -1);
  } catch (e) {}

  
  try {
    () => __v_4.call(__v_5, __v_2 - __v_6 + 1, 0);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int8", 1e12, undefined);
  } catch (e) {}

  try {
    %PrepareFunctionForOptimization(__f_3);
  } catch (e) {}

  __f_3(__v_32, "Uint8", 0, 0);

  try {
    __f_3(__v_32, "Uint8", 0, 0);
  } catch (e) {}

  try {
    %OptimizeFunctionOnNextCall(__f_3);
  } catch (e) {}

  try {
    
    __f_3(__v_32, "Uint8", 0, 0);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint8", undefined, 0);
  } catch (e) {}

  
  try {
    __v_8 = __v_2, __callGC();
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint8", 8, 128);
  } catch (e) {}

  
  try {
    __f_3(__v_32, "Uint8", 15, 255);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint8", 15, 255);
  } catch (e) {}

  try {
    __f_3(
    
    __v_3, "Uint8", 1e12, undefined);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int16", 0, 256, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int16", undefined, 256, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int16", 5, 26213, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int16", 9, -32127, true);
  } catch (e) {}

  
  try {
    __f_3(__v_32, "Int16",
    
    5, 1);
  } catch (e) {}

  
  try {
    __f_3(__v_32, "Uint16", 0, 256, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int16", 14,
    
    1519, true);
  } catch (e) {}

  
  try {
    if (__v_9 != null && typeof __v_9 == "object") try {
      Object.defineProperty(__v_9, __getRandomProperty(__v_35, 221710), {
        get: function () {
          try {
            __v_1[__getRandomProperty(__v_1, 66444)] = __getRandomObject(607902), __callGC();
          } catch (e) {}

          return Array(0x8000).fill("a");
        },
        set: function (value) {
          try {
            __v_9[__getRandomProperty(__v_9, 225298)], __callGC();
          } catch (e) {}
        }
      });
    } catch (e) {}
  } catch (e) {}

  try {
    __f_3(__v_32, "Int16", 1e12, undefined, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int16", 5, 1);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int16", undefined, 1);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int16", 5, 25958);
  } catch (e) {}

  
  try {
    __f_3(__v_32, "Int32", 12, -50462977);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int16", 9, -32382);
  } catch (e) {}

  try {
    
    %CompileBaseline(__f_3);
  } catch (e) {}

  
  try {
    __f_3(__v_32, "Int16", 5, 26213, true);
  } catch (e) {}

  try {
    
    runNearStackLimit(() => {
      return __f_3(__v_32, "Int16",
      
      -1, -257);
    });
  } catch (e) {}

  try {
    __f_3(__v_32, "Int16", 1e12, undefined);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint16", 0, 256, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint16", undefined, 256, true);
  } catch (e) {}

  try {
    %PrepareFunctionForOptimization(__f_3);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint16", 5,
    
    26374, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint16", 5, 26374, true);
  } catch (e) {}

  try {
    %OptimizeMaglevOnNextCall(__f_3);
  } catch (e) {}

  try {
    
    __f_3(__v_32, "Uint16", 5, 26374, true);
  } catch (e) {}

  
  try {
    __callRandomFunction(__v_35, 752219, __v_4, 9007199254740990, 0, 4294967295, [], false, __v_8, __getRandomObject(1005099), {
      a: "foo",
      b: 10,
      c: {}
    });
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint16", 9, 33409, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint16", 14, 65534, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint16", 1e12, undefined, true);
  } catch (e) {}

  try {
    __f_3(
    
    __v_3, "Uint16", 0, 1);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint16", undefined,
    
    16);
  } catch (e) {}

  try {
    %PrepareFunctionForOptimization(__f_3);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint16", 5, 25958);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint16", 5, 25958);
  } catch (e) {}

  try {
    %OptimizeFunctionOnNextCall(__f_3);
  } catch (e) {}

  try {
    
    __f_3(__v_32, "Uint16", 5, 25958);
  } catch (e) {}

  
  try {
    __f_3(__v_32, "Uint16", 9, 33154);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint16", 9, 33154);
  } catch (e) {}

  
  try {
    __callRandomFunction(__v_7, 929675);
  } catch (e) {}

  try {
    __v_2[__getRandomProperty(__v_2, 916991)], __callGC();
  } catch (e) {}

  try {
    __callRandomFunction(__v_33, 734644, __v_33);
  } catch (e) {}

  
  try {
    if (__v_4 != null && typeof __v_4 == "object") Object.defineProperty(__v_4, __getRandomProperty(__v_4, 117812), {
      get: function () {
        __v_4[__getRandomProperty(__v_4, 1002779)] = __v_0, __callGC();
        return __getRandomObject(750292);
      },
      set: function (value) {
        __callRandomFunction(__v_35, 527244, /0/, 9007199254740992, __getRandomObject(977841), __v_2, __v_5, Array(0x8000).join("a"), null);

        __v_6[__getRandomProperty(__v_6, 638642)], __callGC();
      }
    });
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint16", 14, 65279);
  } catch (e) {}

  
  try {
    __v_35[__getRandomProperty(__v_35, 372278)] = __v_2, __callGC();
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint16", 1e12, undefined);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int32",
    
    9, 50462976, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int32", undefined, 50462976, true);
  } catch (e) {}

  
  try {
    __v_0(0, 1n, 2);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int32", 3, 1717920771, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int32",
    
    4294967296, -2122291354, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int32", 9, -58490239, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int32", 12, -66052, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int32", 1e12, undefined, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int32", 0, 66051);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int32", undefined, 66051);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int32", 3, 56911206);
  } catch (e) {}

  
  try {
    __v_2 = __v_10, __callGC();
  } catch (e) {}

  try {
    __f_3(__v_32, "Int32", 6, 1718059137);
  } catch (e) {}

  try {
    __f_3(__v_32, "Int32", 9, -2122152964);
  } catch (e) {}

  
  try {
    delete __v_34[__getRandomProperty(__v_34, 878200)], __callGC();
  } catch (e) {}

  try {
    __v_3[__getRandomProperty(__v_3, 386528)], __callGC();
  } catch (e) {}

  try {
    __callRandomFunction(__v_33, 552786);
  } catch (e) {}

  try {
    __v_5 = __v_5, __callGC();
  } catch (e) {}

  
  try {
    [__v_9("1337")];
  } catch (e) {}

  try {
    __f_3(__v_32, "Int32", 12, -50462977);
  } catch (e) {}

  try {
    __f_3(
    
    __v_2, "Int32", 1e12, undefined);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", 0, 50462976, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", undefined, 50462976, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", 3, 1717920771, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", 6, 2172675942, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", 9, 4236477057, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", 12, 4294901244, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", 1e12, undefined, true);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", 0, 66051);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", undefined, 66051);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", 3, 56911206);
  } catch (e) {}

  try {
    %PrepareFunctionForOptimization(__f_3);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", 6, 1718059137);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", 6, 1718059137);
  } catch (e) {}

  try {
    %OptimizeFunctionOnNextCall(__f_3);
  } catch (e) {}

  try {
    
    __f_3(__v_32, "Uint32", 6, 1718059137);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", 9, 2172814332);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", 12, 4244504319);
  } catch (e) {}

  try {
    __f_3(__v_32, "Uint32", 1e12, undefined);
  } catch (e) {}
}

function __f_6(__v_36, __v_37, __v_38, __v_39, __v_40) {
  try {
    __f_4(__v_38, 0, true, __v_39);
  } catch (e) {}

  try {
    
    __f_3(__v_36, __v_37, 0, __v_40, true);
  } catch (e) {}

  try {
    %DeoptimizeFunction(__f_3);
  } catch (e) {}

  try {
    __f_3(__v_36, __v_37, undefined, __v_40, true);
  } catch (e) {}

  try {
    __f_4(__v_38,
    
    15, true,
    
    __v_3);
  } catch (e) {}

  try {
    __f_3(__v_36, __v_37, 3,
    
    __v_40, true);
  } catch (e) {}

  try {
    __f_4(__v_38, 7, true, __v_39);
  } catch (e) {}

  try {
    __f_3(__v_36, __v_37, 7, __v_40, true);
  } catch (e) {}

  try {
    __f_4(__v_38, 10, true, __v_39);
  } catch (e) {}

  
  try {
    __v_37 = __v_40, __callGC();
  } catch (e) {}

  try {
    __v_37 = __v_4, __callGC();
  } catch (e) {}

  try {
    delete __v_10[__getRandomProperty(__v_10, 789131)], __callGC();
  } catch (e) {}

  try {
    __f_3(
    
    __v_5, __v_37, 10, __v_40, true);
  } catch (e) {}

  try {
    __f_3(__v_36, __v_37, 1e12, undefined, true);
  } catch (e) {}

  try {
    __f_4(__v_38, 0, false);
  } catch (e) {}

  try {
    __f_3(__v_36,
    
    __v_7, 0, __v_40, false);
  } catch (e) {}

  try {
    __f_3(__v_36, __v_37, undefined, __v_40, false);
  } catch (e) {}

  
  try {
    __v_5[__getRandomProperty(__v_5, 203871)], __callGC();
  } catch (e) {}

  try {
    %PrepareFunctionForOptimization(__f_4);
  } catch (e) {}

  try {
    __f_4(__v_38, 3, false);
  } catch (e) {}

  try {
    __f_4(__v_38, 3, false);
  } catch (e) {}

  try {
    %OptimizeFunctionOnNextCall(__f_4);
  } catch (e) {}

  try {
    
    __f_4(__v_38, 3, false);
  } catch (e) {}

  try {
    __f_3(__v_36, __v_37, 3, __v_40, false);
  } catch (e) {}

  try {
    __f_4(__v_38, 7, false);
  } catch (e) {}

  try {
    
    runNearStackLimit(() => {
      return __f_3(__v_36, __v_37, 7, __v_40, false);
    });
  } catch (e) {}

  try {
    __f_4(__v_38, 10, false);
  } catch (e) {}

  __f_3(__v_36, __v_37, 10, __v_40, false);

  
  try {
    RegExp['$1'];
  } catch (e) {}

  
  try {
    __f_3(__v_36, __v_37, 1e12, undefined, false);
  } catch (e) {}

  try {
    __f_3(__v_36, __v_37, 1e12, undefined, false);
  } catch (e) {}

  
  try {
    [void 0, 'a',, 'c'].concat(['d',, 'f', [0,, 2], void 0]);
  } catch (e) {}
}

function __f_7(__v_41, __v_42) {
  try {
    __f_6(__v_41, "Float32", __v_41 ? [0, 0, 32, 65] : __v_6, __v_42, 10);
  } catch (e) {}

  
  try {
    __f_6(__v_41, "Float32", __v_41 ? [
    
    169, 112, 157, 63] : __v_6, __v_42, 1.2300000190734863);
  } catch (e) {}

  try {
    __f_6(__v_41, "Float32", __v_41 ? [169, 112, 157, 63] : __v_6, __v_42, 1.2300000190734863);
  } catch (e) {}

  try {
    
    __f_34(
    
    __v_0, "Float32", __v_41 ? [95, 53, 50, 199] : __v_6,
    
    __v_3, -45621.37109375);
  } catch (e) {}

  try {
    __f_6(__v_41, "Float32", __v_41 ? [255, 255, 255, 127] : __v_6, __v_42, NaN);
  } catch (e) {}

  
  try {
    __f_6(
    
    __v_8, "Float32", __v_41 ? [255, 255, 255, 255] : __v_6, __v_42, -NaN);
  } catch (e) {}

  try {
    
    %CompileBaseline(__f_6);
  } catch (e) {}

  try {
    __f_6(__v_8, "Float32", __v_41 ? [255, 255, 255, 255] : __v_6, __v_42, -NaN);
  } catch (e) {}

  try {
    __f_6(__v_41, "Float64", __v_41 ? [0, 0, 0, 0, 0,
    
    -1, 36, 64] :
    
    __v_8, __v_42, 10);
  } catch (e) {}

  
  try {
    __v_4[__getRandomProperty(__v_4, 634018)] = "/0/", __callGC();
  } catch (e) {}

  try {
    __f_6(__v_41, "Float64", __v_41 ? [174, 71, 225, 122, 20, 174, 243, 63] : __v_6,
    
    __v_42, 1.23);
  } catch (e) {}

  
  try {
    __v_3[__getRandomProperty(__v_3, 1015596)] = {
      a: "foo",
      b: 10,
      c: {}
    }, __callGC();
  } catch (e) {}

  try {
    __f_6(__v_41, "Float64", __v_41 ? [181, 55, 248, 30, 242, 179, 87, 193] : __v_6,
    
    __v_41, -6213576.4839);
  } catch (e) {}

  
  try {
    /Type index .* is greater than the maximum number/;
  } catch (e) {}

  try {
    __f_6(__v_41, "Float64", __v_41 ? [255, 255, 255, 255, 255, 255, 255, 127] : __v_6, __v_42, NaN);
  } catch (e) {}

  try {
    __f_6(__v_41, "Float64", __v_41 ?
    

    
    [255, 255, 255, 255, 255, 255, 255,
    
    0, 255] : __v_6, __v_42, -NaN);
  } catch (e) {}
}

function __f_8(__v_43) {
  try {
    __f_4(__v_4, 0, true, 0, 16);
  } catch (e) {}

  try {
    __f_3(__v_43, "Int8", -1, 0);
  } catch (e) {}

  
  try {
    __v_1 = __v_8, __callGC();
  } catch (e) {}

  
  try {
    __f_3(__v_43, "Float32",
    
    -15, 0);
  } catch (e) {}

  try {
    __f_3(__v_43, "Int8", -2, 0);
  } catch (e) {}

  try {
    __f_3(__v_43, "Uint8", -1, 0);
  } catch (e) {}

  try {
    __f_3(__v_43, "Uint8", -2, 0);
  } catch (e) {}

  
  try {
    __v_8[__getRandomProperty(__v_8, 132428)] = new String(""), __callGC();
  } catch (e) {}

  try {
    __f_3(__v_43, "Int16", -1, 1);
  } catch (e) {}

  
  try {
    __v_9[__getRandomProperty(__v_9, 478193)], __callGC();
  } catch (e) {}

  try {
    __f_3(__v_43, "Int16", -2, 1);
  } catch (e) {}

  try {
    __f_3(
    
    __v_5, "Int16", -3, 1);
  } catch (e) {}

  
  try {
    __f_3(__v_43, "Float64", -9, 0);
  } catch (e) {}

  
  try {
    "for (let i = 0; i < 10; i++) { 1; }";
  } catch (e) {}

  try {
    __f_3(__v_43, "Uint16", -1, 1);
  } catch (e) {}

  try {
    
    __f_3(__v_43, "Uint16", -2, 1);
  } catch (e) {}

  
  try {
    __v_8[__getRandomProperty(__v_8, 116030)] = __getRandomObject(951219), __callGC();
  } catch (e) {}

  try {
    %DeoptimizeFunction(__f_3);
  } catch (e) {}

  try {
    %PrepareFunctionForOptimization(__f_3);
  } catch (e) {}

  try {
    __f_3(__v_43, "Uint16",
    
    0, 1);
  } catch (e) {}

  try {
    __f_3(__v_43, "Uint16", 0, 1);
  } catch (e) {}

  try {
    %OptimizeMaglevOnNextCall(__f_3);
  } catch (e) {}

  try {
    
    __f_3(__v_43, "Uint16", 0, 1);
  } catch (e) {}

  
  try {
    Math.sin(1e16);
  } catch (e) {}

  try {
    __f_3(__v_43, "Int32", -1, 66051);
  } catch (e) {}

  
  try {
    __v_6[__getRandomProperty(__v_6, 347292)] = 1, __callGC();
  } catch (e) {}

  try {
    __v_5 = __v_8, __callGC();
  } catch (e) {}

  try {
    __f_3(__v_43, "Int32", -3, 66051);
  } catch (e) {}

  try {
    __f_3(__v_43, "Int32", -5, 66051);
  } catch (e) {}

  try {
    __f_3(__v_43, "Uint32", -1, 66051);
  } catch (e) {}

  try {
    __f_3(__v_43, "Uint32", -3, 66051);
  } catch (e) {}

  try {
    __f_3(__v_43, "Uint32", -5, 66051);
  } catch (e) {}

  try {
    
    __f_4([0, 0, 0, 0, 0, 0, 0, 0], 0, true, 0, 8);
  } catch (e) {}

  try {
    %DeoptimizeFunction(__f_4);
  } catch (e) {}

  try {
    __f_3(__v_43, "Float32", -15, 0);
  } catch (e) {}

  try {
    __f_3(__v_43, "Float32", -3, 0);
  } catch (e) {}

  try {
    __f_3(__v_43, "Float32",
    
    -13, 0);
  } catch (e) {}

  try {
    __f_3(
    
    __v_2, "Float64", -1, 0);
  } catch (e) {}

  try {
    __f_3(__v_43, "Float64", -5, 0);
  } catch (e) {}

  try {
    __f_3(__v_43, "Float64", -9, 0);
  } catch (e) {}
}

function __f_9() {
  __f_5(true, __v_4, 0, 16);

  try {
    __f_7(true,
    
    -13);
  } catch (e) {}

  
  try {
    if (__v_1 != null && typeof __v_1 == "object") try {
      Object.defineProperty(__v_1, __getRandomProperty(__v_1, 529413), {
        get: function () {
          try {
            __v_10[__getRandomProperty(__v_10, 310538)] = __getRandomObject(905395), __callGC();
          } catch (e) {}

          return __getRandomObject(139988);
        },
        set: function (value) {
          try {
            __callRandomFunction(__v_10, 588841, 4294967297, 1e-15, {}, true, -1, {
              valueOf: function () {
                return "0";
              }
            }, Array(0x8000).join("a"), "foo", __getRandomObject(601081), {});
          } catch (e) {}

          try {
            __v_9[__getRandomProperty(__v_9, 742947)] = __getRandomObject(61291), __callGC();
          } catch (e) {}
        }
      });
    } catch (e) {}
  } catch (e) {}

  try {
    if (__getRandomObject(821138) != null && typeof __getRandomObject(821138) == "object") try {
      Object.defineProperty(__getRandomObject(821138), __getRandomProperty(__getRandomObject(821138), 282378), {
        get: function () {
          try {
            if (__v_8 != null && typeof __v_8 == "object") try {
              Object.defineProperty(__v_8, __getRandomProperty(__v_8, 67560), {
                get: function () {
                  try {
                    __v_9[__getRandomProperty(__v_9, 496534)] = -2147483648, __callGC();
                  } catch (e) {}

                  return __getRandomObject(283173);
                },
                set: function (value) {
                  try {
                    __callRandomFunction(__v_6, 594907, -1073741824, "foo", __v_7, "", __v_8, __v_6, __v_6, 9007199254740992, __v_8);
                  } catch (e) {}
                }
              });
            } catch (e) {}
          } catch (e) {}

          return __v_1;
        },
        set: function (value) {
          try {
            if (__v_4 != null && typeof __v_4 == "object") try {
              Object.defineProperty(__v_4, __getRandomProperty(__v_4, 449468), {
                get: function () {
                  return __v_6;
                },
                set: function (value) {}
              });
            } catch (e) {}
          } catch (e) {}

          try {
            if (__v_7 != null && typeof __v_7 == "object") try {
              Object.defineProperty(__v_7, __getRandomProperty(__v_7, 764834), {
                value: __getRandomObject(656247)
              });
            } catch (e) {}
          } catch (e) {}
        }
      });
    } catch (e) {}
  } catch (e) {}

  try {
    __f_5(true, __v_5, 3, 2);
  } catch (e) {}

  try {
    __f_7(true, 3);
  } catch (e) {}

  try {
    __f_8(true);
  } catch (e) {}
}

function __f_10() {
  
  try {
    __callRandomFunction(__v_4, 962395, __v_3, __v_1);
  } catch (e) {}

  try {
    __f_5(false, __v_6, 0, 16);
  } catch (e) {}

  try {
    __f_7(false);
  } catch (e) {}

  try {
    __f_5(false, __v_6, 3, 2);
  } catch (e) {}

  try {
    __f_7(false, 7);
  } catch (e) {}

  try {
    __f_8(false);
  } catch (e) {}
}

try {
  __f_9();
} catch (e) {}

try {
  __f_10();
} catch (e) {}

function __f_11(__v_44, __v_45) {
  try {
    var __v_46 = new DataView(new ArrayBuffer(100));
  } catch (e) {}

  try {
    assertSame(undefined, __v_46.setInt8(0, __v_44));
  } catch (e) {}

  try {
    assertSame(__v_45, __v_46.getInt8(0));
  } catch (e) {}

  
  try {
    assertSame(undefined, __v_46.setInt8(0, __v_44, true));
  } catch (e) {}

  try {
    assertSame(undefined, __v_46.setInt8(0, __v_44, true));
  } catch (e) {}

  try {
    assertSame(__v_45, __v_46.getInt8(0, true));
  } catch (e) {}
}

function __f_12(__v_47, __v_48) {
  try {
    var __v_49 = new DataView(new ArrayBuffer(100));
  } catch (e) {}

  try {
    assertSame(undefined, __v_49.setUint8(0, __v_47));
  } catch (e) {}

  try {
    assertSame(__v_48, __v_49.getUint8(0));
  } catch (e) {}

  try {
    assertSame(undefined, __v_49.setUint8(0, __v_47, true));
  } catch (e) {}

  try {
    assertSame(__v_48, __v_49.getUint8(0, true));
  } catch (e) {}
}

function __f_13(__v_50, __v_51) {
  try {
    var __v_52 = new DataView(new ArrayBuffer(100));
  } catch (e) {}

  try {
    assertSame(undefined, __v_52.setInt16(0,
    
    __v_8));
  } catch (e) {}

  try {
    assertSame(__v_51, __v_52.getInt16(0));
  } catch (e) {}

  try {
    assertSame(undefined, __v_52.setInt16(0,
    
    __v_10, true));
  } catch (e) {}

  try {
    assertSame(__v_51, __v_52.getInt16(0, true));
  } catch (e) {}
}

function __f_14(__v_53, __v_54) {
  try {
    var __v_55 = new DataView(new ArrayBuffer(100));
  } catch (e) {}

  try {
    assertSame(undefined, __v_55.setUint16(0, __v_53));
  } catch (e) {}

  try {
    assertSame(__v_54, __v_55.getUint16(0));
  } catch (e) {}

  
  try {
    assertSame(undefined,
    
    __v_4.setUint16(
    
    -14, __v_53, true));
  } catch (e) {}

  
  try {
    if (__v_1 != null && typeof __v_1 == "object") try {
      Object.defineProperty(__v_1, __getRandomProperty(__v_2, 883783), {
        value: __getRandomObject(941742)
      });
    } catch (e) {}
  } catch (e) {}

  try {
    assertSame(undefined, __v_4.setUint16(-14, __v_53, true));
  } catch (e) {}

  try {
    assertSame(__v_54, __v_55.getUint16(0, true));
  } catch (e) {}

  
  try {
    __callRandomFunction(__v_7, 375999, __v_54);
  } catch (e) {}
}

function __f_15(__v_56, __v_57) {
  try {
    var __v_58 = new DataView(new ArrayBuffer(100));
  } catch (e) {}

  try {
    assertSame(undefined, __v_58.setInt32(0,
    
    __v_3));
  } catch (e) {}

  try {
    assertSame(__v_57, __v_58.getInt32(0));
  } catch (e) {}

  try {
    assertSame(undefined, __v_58.setInt32(0, __v_56, true));
  } catch (e) {}

  try {
    assertSame(__v_57, __v_58.getInt32(0, true));
  } catch (e) {}
}

function __f_16(__v_59, __v_60) {
  try {
    var __v_61 = new DataView(new ArrayBuffer(100));
  } catch (e) {}

  
  try {
    assertSame(undefined, __v_61.setUint32(0, __v_59));
  } catch (e) {}

  try {
    assertSame(undefined, __v_61.setUint32(0, __v_59));
  } catch (e) {}

  try {
    assertSame(
    
    __v_59, __v_61.getUint32(0));
  } catch (e) {}

  try {
    assertSame(undefined, __v_61.setUint32(0, __v_59, true));
  } catch (e) {}

  try {
    assertSame(
    
    __v_8, __v_61.getUint32(0, true));
  } catch (e) {}
}

function __f_17() {
  try {
    __f_11(0x80, -0x80);
  } catch (e) {}

  try {
    __f_11(0x1000, 0);
  } catch (e) {}

  try {
    __f_11(-0x81, 0x7F);
  } catch (e) {}

  try {
    __f_12(0x100, 0);
  } catch (e) {}

  
  try {
    __f_12(0x1000, 0);
  } catch (e) {}

  try {
    __f_12(0x1000, 0);
  } catch (e) {}

  try {
    __f_12(-0x80, 0x80);
  } catch (e) {}

  try {
    __f_12(-1, 0xFF);
  } catch (e) {}

  try {
    __f_12(-0xFF, 1);
  } catch (e) {}

  try {
    __f_13(
    
    32755, -0x8000);
  } catch (e) {}

  try {
    __f_13(0x10000, 0);
  } catch (e) {}

  try {
    __f_13(-0x8001, 0x7FFF);
  } catch (e) {}

  
  try {
    __f_14(0x10000, 0);
  } catch (e) {}

  try {
    __f_14(0x10000, 0);
  } catch (e) {}

  try {
    %PrepareFunctionForOptimization(__f_14);
  } catch (e) {}

  try {
    __f_14(0x100000, 0);
  } catch (e) {}

  try {
    __f_14(0x100000, 0);
  } catch (e) {}

  try {
    %OptimizeFunctionOnNextCall(__f_14);
  } catch (e) {}

  try {
    
    __f_14(0x100000, 0);
  } catch (e) {}

  try {
    __f_14(-0x8000, 0x8000);
  } catch (e) {}

  try {
    __f_14(-1, 0xFFFF);
  } catch (e) {}

  try {
    __f_14(-0xFFFF, 1);
  } catch (e) {}

  try {
    __f_15(0x80000000, -0x80000000);
  } catch (e) {}

  
  try {
    "x" + (__v_5 + 1);
  } catch (e) {}

  try {
    __f_15(0x100000000, 0);
  } catch (e) {}

  try {
    __f_15(-0x80000001, 0x7FFFFFFF);
  } catch (e) {}

  try {
    __f_16(0x100000000, 0);
  } catch (e) {}

  try {
    __f_16(0x1000000000, 0);
  } catch (e) {}

  try {
    __f_16(-0x80000000, 0x80000000);
  } catch (e) {}

  try {
    __f_16(-1, 0xFFFFFFFF);
  } catch (e) {}

  try {
    __f_16(-0xFFFFFFFF, 1);
  } catch (e) {}
}

try {
  __f_17();
} catch (e) {}

function __f_18() {
  try {
    var __v_62 = new DataView(new ArrayBuffer(256));
  } catch (e) {}

  function __f_22(__v_63) {
    try {
      var __v_64 =
      
      __v_8[__v_63];
    } catch (e) {}

    try {
      assertThrows(function () {
        try {
          __v_64();
        } catch (e) {}
      }, TypeError);
    } catch (e) {}

    
    try {
      __v_0[__getRandomProperty(__v_0, 87549)] = 4294967297, __callGC();
    } catch (e) {}

    try {
      if (__v_6 != null && typeof __v_6 == "object") try {
        Object.defineProperty(__v_6, __getRandomProperty(__v_6, 817930), {
          value: -5e-324
        });
      } catch (e) {}
    } catch (e) {}

    try {
      __v_8[__getRandomProperty(__v_8, 268704)] = "foo", __callGC();
    } catch (e) {}

    try {
      __v_64.call(__v_62, 0, 0);
    } catch (e) {}

    try {
      assertThrows(function () {
        try {
          __v_64.call({}, 0, 0);
        } catch (e) {}
      }, TypeError);
    } catch (e) {}

    __v_64.call(__v_62);

    try {
      __v_64.call(__v_62, 1);
    } catch (e) {}
  }

  try {
    __f_22("getUint8");
  } catch (e) {}

  try {
    __f_22("setUint8");
  } catch (e) {}

  try {
    __f_22("getInt8");
  } catch (e) {}

  try {
    __f_22("setInt8");
  } catch (e) {}

  try {
    __f_22("getUint16");
  } catch (e) {}

  try {
    __f_22("setUint16");
  } catch (e) {}

  try {
    __f_22("getInt16");
  } catch (e) {}

  try {
    __f_22("setInt16");
  } catch (e) {}

  
  try {
    __v_9 = __v_8, __callGC();
  } catch (e) {}

  try {
    __f_22("getUint32");
  } catch (e) {}

  try {
    __f_22("setUint32");
  } catch (e) {}

  
  try {
    () => true?.();
  } catch (e) {}

  try {
    __f_22("getInt32");
  } catch (e) {}

  try {
    
    __f_29("setInt32");
  } catch (e) {}

  try {
    __f_22("getFloat32");
  } catch (e) {}

  try {
    __f_22("setFloat32");
  } catch (e) {}

  try {
    __f_22("getFloat64");
  } catch (e) {}

  try {
    __f_22("setFloat64");
  } catch (e) {}
}

try {
  
  __f_11();
} catch (e) {}

function __f_19() {
  var __v_65 = new DataView(new ArrayBuffer(256));

  function __f_23(__v_66) {
    try {
      var __v_67 = __v_66 === "Float32" || __v_66 === "Float64" ? NaN : 0;
    } catch (e) {}

    try {
      var __v_68 =
      
      __f_17(__v_66);
    } catch (e) {}

    try {
      assertSame(undefined, __v_65["set" + __v_66](0, 7));
    } catch (e) {}

    try {
      assertSame(undefined, __v_65["set" +
      
      __v_6]());
    } catch (e) {}

    try {
      assertSame(__v_67,
      
      __v_8["get" + __v_66]());
    } catch (e) {}

    try {
      assertSame(undefined, __v_65["set" + __v_66](__v_68, 7));
    } catch (e) {}

    try {
      assertSame(undefined, __v_65["set" + __v_66](__v_68));
    } catch (e) {}

    try {
      assertSame(__v_67,
      
      __v_67["get" + __v_66](
      
      __v_7));
    } catch (e) {}
  }

  try {
    __f_23("Uint8");
  } catch (e) {}

  
  try {
    __f_23("Uint8");
  } catch (e) {}

  
  try {
    __callRandomFunction(__v_4, 656682, -1073741824);
  } catch (e) {}

  try {
    delete __v_65[__getRandomProperty(__v_65, 121087)], __callGC();
  } catch (e) {}

  try {
    __f_23("Int8");
  } catch (e) {}

  try {
    __f_23("Uint16");
  } catch (e) {}

  try {
    
    %CompileBaseline(__f_23);
  } catch (e) {}

  try {
    __f_23("Int16");
  } catch (e) {}

  try {
    __f_23("Uint32");
  } catch (e) {}

  try {
    __f_23("Int32");
  } catch (e) {}

  try {
    __f_23("Float32");
  } catch (e) {}

  %PrepareFunctionForOptimization(__f_23);

  try {
    __f_23("Float64");
  } catch (e) {}

  try {
    __f_23("Float64");
  } catch (e) {}

  try {
    %OptimizeFunctionOnNextCall(__f_23);
  } catch (e) {}

  try {
    
    __f_23("Float64");
  } catch (e) {}
}


try {
  assertEquals("Infinity", String(Math.cbrt(Infinity)));
} catch (e) {}

try {
  __f_19();
} catch (e) {}


try {
  (function __f_24() {
    try {
      assertThrows(() => {
        try {
          DataView.prototype.getInt32.call('xyz', 0);
        } catch (e) {}
      }, TypeError, 'Method DataView.prototype.getInt32 called on incompatible receiver xyz');
    } catch (e) {}
  })();
} catch (e) {}

try {
  (function __f_24() {
    try {
      assertThrows(() => {
        try {
          DataView.prototype.getInt32.call('xyz', 0);
        } catch (e) {}
      }, TypeError, 'Method DataView.prototype.getInt32 called on incompatible receiver xyz');
    } catch (e) {}
  })();
} catch (e) {}

let __v_69;


try {
  if (__v_1 != null && typeof __v_1 == "object") try {
    Object.defineProperty(__v_1, __getRandomProperty(__v_1, 366171), {
      value: __v_9
    });
  } catch (e) {}
} catch (e) {}


try {
  (function () {
    let __v_70 = {};

    try {
      __v_69 = new WeakRef(__v_70);
    } catch (e) {}
  })();
} catch (e) {}

try {
  (function () {
    let __v_70 = {};

    try {
      __v_69 = new WeakRef(__v_70);
    } catch (e) {}

    
    try {
      if (__getRandomObject(813759) != null && typeof __getRandomObject(813759) == "object") try {
        Object.defineProperty(__getRandomObject(813759), __getRandomProperty(__getRandomObject(813759), 528641), {
          value: 9007199254740990
        });
      } catch (e) {}
    } catch (e) {}

    try {
      __v_4[__getRandomProperty(__v_4, 219506)] = Symbol("foo"), __callGC();
    } catch (e) {}
  })();
} catch (e) {}

try {
  gc();
} catch (e) {}

try {
  assertNotEquals(undefined, __v_69.deref());
} catch (e) {}

try {
  setTimeout(() => {
    try {
      (async function () {
        try {
          await gc({
            type: 'major',
            execution: 'async'
          });
        } catch (e) {}

        try {
          assertEquals(undefined, __v_69.deref());
        } catch (e) {}
      })();
    } catch (e) {}

    
    try {
      __v_6[__getRandomProperty(__v_6, 576402)], __callGC();
    } catch (e) {}
  }, 0);
} catch (e) {}

function __f_25() {}

try {
  __f_25.prototype.f = function () {
    return 1;
  };
} catch (e) {}

function __f_26() {}

try {
  __f_26.prototype.f = function () {
    throw 2;
  };
} catch (e) {}

try {
  var __v_71 = new __f_25();
} catch (e) {}

try {
  var __v_72 = new __f_26();
} catch (e) {}

function __f_27(__v_73) {
  return (
    
    __v_71.f()
  );
}

try {
  %PrepareFunctionForOptimization(__f_27);
} catch (e) {}

try {
  __f_27(__v_71);
} catch (e) {}

try {
  try {
    
    __f_43(__v_72);
  } catch (e) {}
} catch (__v_74) {}

try {
  __f_27(__v_71);
} catch (e) {}

try {
  
  try {
    __callRandomFunction(__v_72, 80586, __v_0, __getRandomObject(526595), __getRandomObject(136759), __v_2, this, -9007199254740979);
  } catch (e) {}

  try {
    __f_27(
    
    __v_0);
  } catch (e) {}
} catch (__v_75) {}

try {
  %OptimizeFunctionOnNextCall(__f_27);
} catch (e) {}

try {
  assertEquals(1, __f_27(__v_71));
} catch (e) {}

try {
  assertThrows(() => (
  
  %PrepareFunctionForOptimization(__f_27), __f_27(__v_72), __f_27(__v_72), %OptimizeMaglevOnNextCall(__f_27), __f_27(__v_72)));
} catch (e) {}

try {
  assertTrue(isNaN(Math.cbrt(NaN)));
} catch (e) {}

try {
  assertTrue(isNaN(Math.cbrt(function () {})));
} catch (e) {}


try {
  assertTrue(isNaN(Math.cbrt({
    toString: function () {
      return NaN;
    }
  })));
} catch (e) {}

try {
  assertTrue(isNaN(Math.cbrt({
    toString: function () {
      return NaN;
    }
  })));
} catch (e) {}

try {
  assertTrue(isNaN(Math.cbrt({
    valueOf: function () {
      return "abc";
    }
  })));
} catch (e) {}


try {
  __callRandomFunction(__v_7, 726749, __getRandomObject(807036), this);
} catch (e) {}

try {
  __v_4[__getRandomProperty(__v_4, 976517)], __callGC();
} catch (e) {}

assertEquals("Infinity", String(1 / Math.cbrt(0)));

try {
  assertEquals("-Infinity", String(1 / Math.cbrt(-0)));
} catch (e) {}

try {
  assertEquals("Infinity", String(Math.cbrt(Infinity)));
} catch (e) {}

try {
  assertEquals("-Infinity", String(Math.cbrt(-Infinity)));
} catch (e) {}

try {
  for (var __v_76 = 1E-100; __v_76 < 1E100; __v_76 *= Math.PI) {
    
    try {
      -0x86b45ffb80fbf2b61abc14b28855780f83e187fd6ae26e09d28d6f05260e1n;
    } catch (e) {}

    try {
      assertEqualsDelta(__v_76, Math.cbrt(__v_76 * __v_76 * __v_76),
      
      __v_72 * 1E-15);
    } catch (e) {}

    
    try {
      delete __v_9[__getRandomProperty(__v_9, 408276)], __callGC();
    } catch (e) {}

    try {
      if (__v_69 != null && typeof __v_69 == "object") try {
        Object.defineProperty(__v_69, __getRandomProperty(__v_69, 469313), {
          get: function () {
            try {
              if (__v_9 != null && typeof __v_9 == "object") Object.defineProperty(__v_9, __getRandomProperty(__v_9, 444519), {
                get: function () {
                  if (__v_6 != null && typeof __v_6 == "object") Object.defineProperty(__v_6, __getRandomProperty(__v_6, 615347), {
                    get: function () {
                      return __getRandomObject(764336);
                    },
                    set: function (value) {}
                  });
                  delete __v_6[__getRandomProperty(__v_6, 334918)], __callGC();
                  return __v_69;
                },
                set: function (value) {}
              });
            } catch (e) {}

            return __v_76;
          },
          set: function (value) {
            try {
              __v_7[__getRandomProperty(__v_7, 83490)] = 1.7976931348623157e+308, __callGC();
            } catch (e) {}

            try {
              delete __v_2[__getRandomProperty(__v_2, 977061)], __callGC();
            } catch (e) {}

            try {
              if (__v_76 != null && typeof __v_76 == "object") try {
                Object.defineProperty(__v_76, __getRandomProperty(__v_7, 890684), {
                  value: __v_2
                });
              } catch (e) {}
            } catch (e) {}
          }
        });
      } catch (e) {}
    } catch (e) {}
  }
} catch (e) {}

try {
  for (var __v_76 = -1E-100; __v_76 > -1E100; __v_76 *= Math.E) {
    assertEqualsDelta(__v_76, Math.cbrt(
    
    __v_2 * __v_76 * __v_76), -__v_76 * 1E-15);
  }
} catch (e) {}

try {
  for (var __v_76 = 2; __v_76 < 10000; __v_76++) {
    try {
      assertEquals(__v_76, Math.cbrt(__v_76 * __v_76 * __v_76));
    } catch (e) {}
  }
} catch (e) {}

try {
  var __v_77 = /[bc]/;
} catch (e) {}

try {
  var __v_78 = "baba";
} catch (e) {}

try {
  assertEquals(["", "a", "a"], __v_78.split(__v_77));
} catch (e) {}

try {
  __v_77.exec = __v_79 => RegExp.prototype.exec.call(
  
  __v_7, __v_79);
} catch (e) {}

try {
  assertEquals(["", "a", "a"],
  
  __v_1.split(__v_77));
} catch (e) {}

let __v_80 = new WebAssembly.Tag({
  'parameters': []
});

let __v_81 = new Proxy({}, {
  'get': () => {
    throw new Error('boom');
  }
});


try {
  __callRandomFunction(__v_80, 48981, Infinity, new String(""), __v_81, __v_76);
} catch (e) {}

try {
  assertThrows(() => new WebAssembly.Exception(
  
  __v_10, [], __v_81), Error, 'boom');
} catch (e) {}

function __f_28() {
  return [5.35,, 3.35];
}

try {
  %PrepareFunctionForOptimization(__f_28);
} catch (e) {}


try {
  assertEquals([5.35,,
  
  -10.65], __f_28());
} catch (e) {}

try {
  assertEquals([5.35,, -10.65], __f_28());
} catch (e) {}

try {
  %OptimizeFunctionOnNextCall(__f_28);
} catch (e) {}

try {
  assertEquals([5.35,, 3.35], __f_28());
} catch (e) {}

function __f_29() {}

try {
  var __v_82 = 'f(' + '0,'.repeat(0x201f) + ')';
} catch (e) {}

try {
  var __v_83 = new Function(__v_82);
} catch (e) {}

try {
  %PrepareFunctionForOptimization(__v_83);
} catch (e) {}

try {
  %OptimizeFunctionOnNextCall(__v_83);
} catch (e) {}

try {
  __v_83();
} catch (e) {}


"" >= -1.25;

try {
  (function () {
    try {
      var __v_84 = [, 3];
    } catch (e) {}

    function __f_30(__v_85, __v_86, __v_87, __v_88) {
      try {
        
        __v_84[__v_87] =
        
        __v_85 + __v_85;
      } catch (e) {}
    }

    function __f_31() {
      __v_84.reduce(__f_30);
    }

    try {
      %PrepareFunctionForOptimization(__f_31);
    } catch (e) {}

    try {
      __f_31();
    } catch (e) {}

    __f_31();

    try {
      %OptimizeFunctionOnNextCall(__f_31);
    } catch (e) {}

    try {
      __f_31();
    } catch (e) {}

    try {
      assertEquals(__v_84, [, 3]);
    } catch (e) {}

    try {
      __v_84.__proto__.push(3);
    } catch (e) {}

    try {
      __f_31();
    } catch (e) {}

    try {
      assertEquals(__v_84, [,
      
      -4]);
    } catch (e) {}

    
    try {
      assertEquals(Object.getOwnPropertyDescriptor(__v_84, 0), undefined);
    } catch (e) {}

    try {
      assertEquals(Object.getOwnPropertyDescriptor(__v_84, 0), undefined);
    } catch (e) {}
  })();
} catch (e) {}

let __v_89 = {
  'abcdefghijklmnopqrst': 'asdf'
};

let __v_90 = 'abcdefghijklmnopqrstuvwxyz'.substring(0, 20);


try {
  assertTrue(__v_89.hasOwnProperty(__v_90));
} catch (e) {}

try {
  assertTrue(__v_89.hasOwnProperty(__v_90));
} catch (e) {}

const __v_91 = new Worker(function () {
  __v_92 = function () {
    performance.measureMemory();
    postMessage("done");
  };

  
  __v_71[__getRandomProperty(__v_71, 142742)], __callGC();

  
  __v_7 = __v_10, __callGC();

  __callRandomFunction(__v_80, 1231, __v_2, Array(0x8000).fill("a"), "foo", __v_76, -9007199254740990, "", __v_90, "", __v_3);

  performance.measureMemory();
  Object.defineProperty(this.d8.__proto__, 'then', {
    get: __v_92
  });
}, {
  type: 'function'
});

try {
  __v_91.postMessage(0);
} catch (e) {}

try {
  __v_91.getMessage();
} catch (e) {}

function __f_32(__v_93) {
  const __v_94 =
  
  __v_3 %
  
  __v_83;

  return 1 /
  
  __v_76;
}

try {
  %PrepareFunctionForOptimization(__f_32);
} catch (e) {}

assertEquals(__f_32(2), Infinity);

try {
  %OptimizeMaglevOnNextCall(__f_32);
} catch (e) {}

try {
  assertEquals(__f_32(-2), -Infinity);
} catch (e) {}

const __v_95 = new WasmModuleBuilder();

__v_95.addType(makeSig([kWasmF32, kWasmF32, kWasmI32, kWasmI32, kWasmI32, kWasmExternRef, kWasmI32, kWasmI32, kWasmI32, kWasmI32], [kWasmI64]));

try {
  __v_95.addFunction(undefined, 0).addBodyWithEnd([]);
} catch (e) {}

__v_95.addFunction(undefined,

-5).addBodyWithEnd([kExprLocalGet, 0x00, kExprLocalGet, 0x01, kExprLocalGet, 0x02, kExprLocalGet, 0x03, kExprI32Const, 0x05, kExprLocalGet, 0x05, kExprLocalGet, 0x06, kExprLocalGet, 0x07, kExprI32Const, 0x5b, kExprI32Const, 0x30, kExprCallFunction, 0x01, kExprLocalGet, 0x00, kExprLocalGet, 0x01, kExprLocalGet,

17, kExprLocalGet, 0x03, kExprLocalGet, 0x07, kExprLocalGet, 0x05, kExprLocalGet, 0x06, kExprLocalGet, 0x07, kExprI32Const, 0x7f, kExprI64DivS, kExprF64Eq, kExprI32DivU, kExprTableGet, 0x7f, kExprI64ShrS]);

try {
  assertThrows(function () {
    try {
      __v_95.instantiate();
    } catch (e) {}
  }, WebAssembly.CompileError);
} catch (e) {}

let __v_96;

function __f_33() {
  return __v_96;
}

%PrepareFunctionForOptimization(__f_33);

try {
  assertEquals(undefined, __f_33());
} catch (e) {}

try {
  %OptimizeFunctionOnNextCall(__f_33);
} catch (e) {}

try {
  assertEquals(undefined, __f_33());
} catch (e) {}


try {
  __v_6.hasOwnProperty = function () {
    return false;
  };
} catch (e) {}

try {
  assertOptimized(__f_33);
} catch (e) {}

try {
  __v_96 = 43;
} catch (e) {}

try {
  assertUnoptimized(__f_33);
} catch (e) {}


try {
  assertEquals(43, __f_33());
} catch (e) {}

try {
  assertEquals(43, (
  
  %PrepareFunctionForOptimization(__f_33), __f_33(), __f_33(), %OptimizeFunctionOnNextCall(__f_33), __f_33()));
} catch (e) {}

const __v_97 = 128;

function __f_34(__v_100, __v_101) {
  return __v_100 > 0 ? [__v_101, __f_34(__v_100 - 1, __v_101)] : [__v_101];
}

const __v_98 = __f_34(__v_97, 'a');

const __v_99 = 'a' + ',a'.repeat(__v_97);


assertSame(__v_99, __v_98.join());

try {
  assertSame(__v_99, __v_98.join());
} catch (e) {}

assertSame(__v_99, __v_98.join());

try {
  var __v_102 = 27;
} catch (e) {}

function __f_35() {
  return __v_102;
}

try {
  assertEquals(27, __f_35());
} catch (e) {}

function __f_36(__v_105) {
  "use strict";

  return eval(__v_105);
}

try {
  var __v_103 = __f_36('(' + __f_35 + ')');
} catch (e) {}


%PrepareFunctionForOptimization(

__v_10);

try {
  %PrepareFunctionForOptimization(__v_10);
} catch (e) {}

for (var __v_104 = 0; __v_104 < 5; __v_104++) assertEquals(27, __v_103());

try {
  %OptimizeFunctionOnNextCall(__v_103);
} catch (e) {}

assertEquals(27,

__v_78());

function __f_37(__v_106) {
  "use strict";

  try {
    var __v_107 = 42;
  } catch (e) {}

  return eval(__v_106);
}

__v_103 = (

%PrepareFunctionForOptimization(__f_37), __f_37('(' + __f_35 + ')'), __f_37('(' + __f_35 + ')'), %OptimizeFunctionOnNextCall(__f_37), __f_37('(' + __f_35 + ')'));

try {
  %PrepareFunctionForOptimization(__v_103);
} catch (e) {}

try {
  for (var __v_104 = 0; __v_104 < 5; __v_104++) assertEquals(42,
  
  __v_72());
} catch (e) {}


try {
  %OptimizeFunctionOnNextCall(__v_103);
} catch (e) {}

try {
  %OptimizeFunctionOnNextCall(__v_103);
} catch (e) {}

assertEquals(42,

__v_82());

function __f_38(__v_108) {
  "use strict";

  try {
    var __v_109 = eval(__v_108);
  } catch (e) {}

  try {
    eval('var x = 1');
  } catch (e) {}

  return __v_109;
}

try {
  __v_103 = __f_38('(' + __f_35 + ')');
} catch (e) {}

try {
  %PrepareFunctionForOptimization(__v_103);
} catch (e) {}

try {
  for (var __v_104 = 0; __v_104 < 5; __v_104++) try {
    assertEquals(27, __v_103());
  } catch (e) {}
} catch (e) {}

try {
  %OptimizeFunctionOnNextCall(__v_103);
} catch (e) {}

try {
  assertEquals(27, __v_103());
} catch (e) {}

function __f_39() {
  function __f_41(__v_112) {
    "use strict";

    return eval(__v_112);
  }

  try {
    var __v_110 = __f_41('(' + __f_35 + ')');
  } catch (e) {}

  try {
    %PrepareFunctionForOptimization(__v_110);
  } catch (e) {}

  try {
    for (var __v_111 = 0; __v_111 < 5; __v_111++) try {
      assertEquals(27, __v_110());
    } catch (e) {}
  } catch (e) {}

  try {
    %OptimizeFunctionOnNextCall(__v_110);
  } catch (e) {}

  try {
    assertEquals(27, __v_110());
  } catch (e) {}

  try {
    eval("var x = 3");
  } catch (e) {}

  try {
    assertEquals(3, __v_110());
  } catch (e) {}

  
  try {
    __v_110[__getRandomProperty(__v_110, 651242)], __callGC();
  } catch (e) {}

  try {
    __v_8[__getRandomProperty(__v_8, 599660)], __callGC();
  } catch (e) {}

  try {
    if (__v_81 != null && typeof __v_81 == "object") Object.defineProperty(__v_81, __getRandomProperty(__v_81, 340977), {
      value: __getRandomObject(694613)
    });
  } catch (e) {}

  __v_72[__getRandomProperty(__v_72, 814475)] = __getRandomObject(547257), __callGC();

  try {
    __v_99[__getRandomProperty(__v_99, 793829)] = __v_69, __callGC();
  } catch (e) {}
}

try {
  __f_39();
} catch (e) {}

function __f_40() {
  "use strict";

  function __f_42(__v_115) {
    "use strict";

    return eval(__v_115);
  }

  try {
    var __v_113 = __f_42('(' + __f_35 + ')');
  } catch (e) {}

  try {
    %PrepareFunctionForOptimization(__v_113);
  } catch (e) {}

  try {
    for (var __v_114 = 0; __v_114 < 5; __v_114++) try {
      assertEquals(27, __v_113());
    } catch (e) {}
  } catch (e) {}

  try {
    %OptimizeFunctionOnNextCall(__v_113);
  } catch (e) {}

  try {
    assertEquals(27, __v_113());
  } catch (e) {}

  
  __callRandomFunction(__v_103, 326826, 5e-324);

  try {
    delete __v_83[__getRandomProperty(__v_83, 185525)], __callGC();
  } catch (e) {}

  try {
    if (__v_89 != null && typeof __v_89 == "object") Object.defineProperty(__v_89, __getRandomProperty(__v_89, 521338), {
      value: __getRandomObject(171105)
    });
  } catch (e) {}

  try {
    eval("var x = 3");
  } catch (e) {}

  
  try {
    __v_77 == "Number";
  } catch (e) {}

  try {
    assertEquals(27, __v_113());
  } catch (e) {}
}

try {
  __f_39();
} catch (e) {}


40320 / 8 / 7;

try {
  __v_118 = 0;
} catch (e) {}

function __f_43(__v_117) {
  try {
    __v_118 = __v_117;
  } catch (e) {}
}


try {
  %PrepareFunctionForOptimization(__f_43);
} catch (e) {}

try {
  %PrepareFunctionForOptimization(__f_43);
} catch (e) {}

try {
  __f_43(1);
} catch (e) {}

try {
  assertEquals(1, __v_118);
} catch (e) {}

try {
  %OptimizeFunctionOnNextCall(__f_43);
} catch (e) {}

try {
  __f_43(0);
} catch (e) {}

try {
  assertEquals(0, __v_118);
} catch (e) {}

try {
  assertOptimized(__f_43);
} catch (e) {}


try {
  [1, 2].some(__v_2);
} catch (e) {}

try {
  Object.freeze(this);
} catch (e) {}

assertUnoptimized(__f_43);


__v_81[__getRandomProperty(__v_81, 315405)], __callGC();

try {
  if (__v_8 != null && typeof __v_8 == "object") try {
    Object.defineProperty(__v_8, __getRandomProperty(__v_78, 841227), {
      get: function () {
        try {
          delete __v_81[__getRandomProperty(__v_81, 717328)], __callGC();
        } catch (e) {}

        return __getRandomObject(480833);
      },
      set: function (value) {
        try {
          __v_89 = __v_98, __callGC();
        } catch (e) {}
      }
    });
  } catch (e) {}
} catch (e) {}

try {
  __callRandomFunction(__v_71, 144722, __v_95, __getRandomObject(109456), 9007199254740990, this[1], __v_77, 9007199254740992);
} catch (e) {}

try {
  __f_43(1);
} catch (e) {}

try {
  assertEquals(0,
  
  __v_8);
} catch (e) {}

(function __f_44() {
  const __v_119 = new ShadowRealm();

  // let __v_120 = __v_119.evaluate('function foo(fn) { return fn.bind(1); }; foo');

  let __v_121 = () => {};

  for (let __v_122 = 0; __v_122 < 1024 * 50; __v_122++) {
    // __v_121 = __v_120(
    
    // __v_77.bind(1));
  }

  assertThrows(() => {
    __v_121.name;
  }, RangeError, 'Maximum call stack size exceeded');
})();