// Optional browser check (Playwright is NOT a project dependency): drives dashboard/evaluation/index.html through its interactive states and dumps what is DISPLAYED.
// Usage: NODE_PATH=<dir with playwright> node dump_display.js file:///.../dashboard/evaluation/index.html out.json   then   python compare_display.py out.json
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [, , url, outFile] = process.argv;
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
  const errs = []; p.on('pageerror', e => errs.push('pageerror: ' + e.message)); p.on('console', m => { if (['error', 'warning'].includes(m.type())) errs.push(m.text()); });
  await p.goto(url); await p.waitForTimeout(400);
  const rows = sel => p.$$eval(sel + ' tr', trs => trs.map(tr => [...tr.cells].map(c => c.textContent.trim())));
  const out = { errors: errs, stats: [], models: [], findings: [], nav: [], hrefs: [], title: await p.title() };
  out.stats = await p.$$eval('#glance .stat', els => els.map(e => ({ n: e.querySelector('.n').textContent, l: e.querySelector('.l').textContent })));
  for (const ev of ['cv', 'single']) for (const h of ['15m', '30m', '1h', '3h']) for (const m of ['rmse', 'skill']) for (const s of ['event_windows_stage10ft', 'event_windows_rise4ft3h']) {
    await p.click(`#segEv label:has(input[value="${ev}"])`); await p.click(`#segH label:has(input[value="${h}"])`); await p.click(`#segM label:has(input[value="${m}"])`); await p.click(`#segS label:has(input[value="${s}"])`);
    out.models.push({ ev, h, m, s, left: await rows('#tL'), right: await rows('#tR'), readout: await p.$eval('#readout', e => e.textContent), note: await p.$eval('#evNote', e => e.textContent), titleR: await p.$eval('#pR', e => e.textContent) });
  }
  await p.click('#segEv label:has(input[value="cv"])'); await p.click('#segM label:has(input[value="rmse"])');
  for (const h of ['15m', '30m', '1h', '3h']) {
    await p.click(`#segH label:has(input[value="${h}"])`);
    out.findings.push({ h, f1: await p.$$eval('#f1c text', ts => ts.map(t => t.textContent)), f1t: await rows('#f1t'), f2t: await rows('#f2t'), f3t: await rows('#f3t'), f4t: await rows('#f4t'), f5t: await rows('#f5t'),
      f2a: await p.$eval('#f2a', e => e.textContent), f3a: await p.$eval('#f3a', e => e.textContent), f3e: await p.$eval('#f3e', e => e.textContent), f4a: await p.$eval('#f4a', e => e.textContent), f5a: await p.$eval('#f5a', e => e.textContent), f3c: await p.$$eval('#f3c text', ts => ts.map(t => t.textContent)) });
  }
  out.strip = await rows('#stripT');
  out.milestones = await p.$$eval('#milestones .card', els => els.map(e => ({ title: e.querySelector('h3').textContent, text: e.querySelector('p').textContent, chips: [...e.querySelectorAll('.chip')].map(c => c.textContent) })));
  out.timeline = await p.$$eval('#timeline .phase', els => els.map(e => ({ name: e.querySelector('h3').textContent, chip: e.querySelector('.chip').textContent, note: e.querySelector('.progress-note').textContent, done: e.querySelectorAll('li.done').length, todo: e.querySelectorAll('li.todo').length })));
  out.limits = await p.$$eval('#limCards .card', els => els.map(e => ({ title: e.querySelector('h3').textContent, text: e.querySelector('p').textContent })));
  // navigation: every top-nav link must scroll its section into view and become active
  for (const href of await p.$$eval('#nav a', as => as.map(a => a.getAttribute('href')))) {
    await p.click(`#nav a[href="${href}"]`); await p.waitForTimeout(700);
    const top = await p.$eval(href, e => Math.round(e.getBoundingClientRect().top)); const active = await p.$eval(`#nav a[href="${href}"]`, a => a.classList.contains('active'));
    out.nav.push({ href, top, active });
  }
  out.hrefs = await p.$$eval('a[href]', as => as.map(a => a.getAttribute('href')));
  // chrome: projector mode and theme toggles must not break rendering
  await p.click('#projBtn'); await p.waitForTimeout(300); out.projector = await p.evaluate(() => document.documentElement.classList.contains('proj') && document.querySelectorAll('svg.chart').length > 5);
  await p.click('#projBtn'); await p.click('#themeBtn'); await p.waitForTimeout(300); out.theme = await p.evaluate(() => document.documentElement.getAttribute('data-theme')); await p.click('#themeBtn');
  out.errors = errs;
  fs.writeFileSync(outFile, JSON.stringify(out)); await b.close(); console.log('dumped', outFile, 'errors:', JSON.stringify(errs));
})();
