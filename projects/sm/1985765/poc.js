class b {
  #c;
  #$; 
  #n; 
  #m; 
  #e; 
  #f; 
  #g;
}
class h {
  #$;
  #n;
  #m;
  #e;
  #f;
  #g;
}
keyZone = newGlobal()
i = newGlobal()
keyZone.eval('var key = Symbol()')
i.eval('map = new WeakMap')
i.keyZone = keyZone
i.eval('map.set(keyZone.key, {})')
schedulezone(i)
schedulezone('atoms')
gc('zone')
