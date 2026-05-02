const v3 = newGlobal();
v3.nukeAllCCWs();
const v13 = this.transplantableObject(v3);
const v27 = newGlobal({"newCompartment": true});

try {
    const t45 = v27.DataView;
    const v29 = new t45(v27);
} catch(e30) {
}

v27.firstGlobalInCompartment(v13.object);
v13.transplant(v3);
