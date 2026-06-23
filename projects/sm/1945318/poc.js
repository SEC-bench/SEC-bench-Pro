function* a() {
     yield b = {}
     Error.captureStackTrace(b, Error)
 }
 async function c() {
     d = a();
     (await d.next())(d.next())
 }
 c()