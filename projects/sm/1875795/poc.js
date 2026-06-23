b = function() {}
evaluate(`   
  oomTest(function() {
    var c = new b
    for (d in this) 
      c[d] = []
  });
`);