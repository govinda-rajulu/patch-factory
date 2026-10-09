const { chromium } = require('/opt/sd-artifact/node_modules/playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage(); const errs = [];
  p.on('pageerror', e => errs.push(String(e))); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto('file://' + process.argv[2] + '/docs/index.html'); await p.waitForTimeout(1500);
  const t = await p.title(); const n = (await p.content()).length;
  console.log('title=' + t + ' bytes=' + n + ' jserrors=' + errs.filter(e => !/net::|Failed to fetch|ERR_/.test(e)).length);
  errs.slice(0, 5).forEach(e => console.log('  ' + e.slice(0, 160))); await b.close();
})().catch(e => { console.log('RENDER_FAIL ' + e); process.exit(1); });
