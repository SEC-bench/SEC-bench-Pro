let g = newGlobal({newCompartment: true});
g.eval(`var mem = new WebAssembly.Memory({initial: 1, maximum: 2, shared: true});`);
serialize(g.mem, undefined, {SharedArrayBuffer: "allow", scope: "SameProcess"});
