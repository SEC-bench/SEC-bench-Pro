x = [012345];
for (let i = 6; i < 260; ++i) {
  x.push(i % 10);
}
eval(`
(new Date().getTime(${x}))
`);