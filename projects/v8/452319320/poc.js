function makeJsonAndSetupMaps() {
    let o1 = { str: "A" };
    const length = 32;
    let o2 = { str: "B".repeat(length) };
    o2.f = {};
    let arr = [o1, o2];
    JSON.stringify(arr);
    return o1;
}

const feedback_obj = makeJsonAndSetupMaps();
const length = 32;
const long_str = "C".repeat(length);
const json_prefix = '[{"str":"A"}, {"str":"' + long_str + '", ';
// The syntax error: expected string (property key for the second property "f") but got ']'.
const json_suffix = ']]';
const json = json_prefix + json_suffix;

// We want GC to happen during ReportUnexpectedToken when the syntax error is encountered.
// The exact number might depend on the configuration and platform.
% SetAllocationTimeout(1, 18);

try {
    JSON.parse(json);
} catch (e) {
    print("Failed to trigger bug");
}
