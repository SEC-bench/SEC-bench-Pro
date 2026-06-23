const length = 32767;
const pattern_body = "^" + "a".repeat(length);
const pattern = new RegExp("(?<=" + pattern_body + ")", "m");
pattern.exec("");
