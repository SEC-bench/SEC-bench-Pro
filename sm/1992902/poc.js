gczeal(2);
function test() {
  var subarray;
  for (var i = 0; i < 1000; i++) {
    var arr = new Int32Array(2);
    arr[0] = 1;
    subarray = arr.subarray(1);
    arr[1] = 1;
  }
  return subarray;
}
for (var j = 0; j < 50; j++) test();
