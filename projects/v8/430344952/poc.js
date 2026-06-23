// Tests complex parameter expressions and multiple scopes

function outer(a = (function(){ return 1; })(), b = 2) {
  let obj = {x: 1, y: 2};
  {
    ev\u0061l('var z = 3;');
    function inner() {
      return obj;  // Should be confused
    }
    return inner;
  }
}

let fn = outer();
fn();
fn();