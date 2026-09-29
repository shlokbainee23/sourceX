// Run with PLAYWRIGHT_MODULE and PLAYWRIGHT_BROWSERS_PATH pointing to local tools.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ reducedMotion: 'reduce' });
    const url = process.env.HOVER_TEST_URL || 'http://127.0.0.1:8000/workstation/';
    let checked = 0;
    for (const route of ['', '#/login']) {
      await page.goto('about:blank');
      await page.goto(url + route);
      await page.locator(route ? '#station-passphrase' : 'button').first().waitFor({ state: 'attached' });
      // Clone actual rendered controls into an unobstructed fixture: hovering
      // never activates a real workflow or needs operational credentials.
      const count = await page.evaluate(() => {
        const buttons = [...document.querySelectorAll('#root button')];
        const fixture = document.createElement('div');
        fixture.id = 'hover-fixture';
        fixture.style.cssText = 'position:fixed;inset:0;z-index:2147483647;background:white;overflow:auto;padding:20px';
        for (const button of buttons) fixture.append(button.cloneNode(true));
        for (const variant of ['primary', 'secondary', 'danger', 'warning', 'ghost', 'outline']) {
          const button = document.createElement('button');
          button.dataset.variant = variant;
          button.textContent = variant;
          fixture.append(button);
        }
        document.querySelector('#root').append(fixture);
        return fixture.children.length;
      });
      for (let i = 0; i < count; i++) {
        const button = page.locator('#hover-fixture > button').nth(i);
        await page.locator('#hover-fixture > button').evaluateAll(elements => elements.forEach(el => { el.style.display = 'none'; }));
        await button.evaluate(el => {
          Object.assign(el.style, { display: 'block', position: 'static', transform: 'none',
            opacity: '1', visibility: 'visible', margin: '12px', pointerEvents: 'auto' });
        });
        await page.mouse.move(0, 0);
        const before = await button.evaluate(el => getComputedStyle(el).backgroundColor);
        await button.hover({ force: true });
        await page.waitForTimeout(250);
        const after = await button.evaluate(el => getComputedStyle(el).backgroundColor);
        if (await button.isDisabled()) assert.equal(after, before, 'disabled colour stays unchanged');
        else {
          assert.notEqual(after, before, `hover changes colour: ${await button.innerText()}`);
          assert.equal(await button.evaluate(el => getComputedStyle(el).color), 'rgb(255, 255, 255)');
          checked++;
        }
      }
    }
    console.log(`PASS: ${checked} enabled button hover colours; disabled buttons unchanged.`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
