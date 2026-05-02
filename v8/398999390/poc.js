const internalizedString = "aaaaaaaaaaaaaaaaaaaaaaaaaaabbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

const str = createExtenalTwoByteString(internalizedString);  // Simulate the behavior of blink
// s1 is not a thin string
// s1 is a two-byte string
// s1 is not internalized

const [sub_str] = /b+/.exec(str);
// sub_str is a two-byte string
// sub_str is a sliced string

console.log('expect: ', JSON.stringify(sub_str));

%InternalizeString(str); // Equivalent to: const map = {}; map[str];
// str is not a thin string
// str is a one-byte string
// sub_str is a two-byte string. Oops !!!!!!!!

console.log('found: ', JSON.stringify(sub_str));
