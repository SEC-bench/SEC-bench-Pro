const v = "123451234512345";
const createv = createExternalizableString(v);

externalizeString(createv);

const memoryView = new Sandbox.MemoryView(0, 4294967296);
const dataView = new DataView(memoryView);

const targetStringAddress = Sandbox.getAddressOf(v);

const twoByteMap = 381;
dataView.setUint32(targetStringAddress, twoByteMap, true);
console.log(v);
