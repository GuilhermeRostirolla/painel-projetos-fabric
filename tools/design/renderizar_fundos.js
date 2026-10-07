// node tools/design/renderizar_fundos.js  (precisa do Playwright)
// gera tools/design/fundos/<página>.png a partir de docs/design/fundos.html, em 2x
const path = require('path');
const raiz = path.resolve(__dirname, '..', '..');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const p = await b.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.join(raiz, 'docs', 'design', 'fundos.html'));
  for (const q of await p.$$('.frame')) {
    const id = await q.getAttribute('id');
    await q.screenshot({ path: path.join(__dirname, 'fundos', id + '.png') });
  }
  await b.close();
})();
