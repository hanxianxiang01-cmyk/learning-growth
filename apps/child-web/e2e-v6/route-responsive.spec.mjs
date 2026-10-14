import fs from 'node:fs';
import { test, expect } from '@playwright/test';

/**
 * FE-1447 / MIK-A5 regression: the task-locked implementation Router is a
 * CSS Grid item even while LEGACY is selected. Its min-content width must not
 * leak a fixed-width math board into document-level horizontal overflow.
 *
 * Existing full-gallery.spec.mjs remains the 20-fixture wrong/correct, lock,
 * reset, 320/390/768 suite. This test isolates the six previously red cases,
 * checks BOTH child skins at TWO phone widths, and emits actionable offenders.
 */
const fixtures = JSON.parse(fs.readFileSync(new URL('../src/dev/v6/fixtures.json', import.meta.url), 'utf8'));
const vulnerable = new Set([
  'number-line', 'place-value', 'ten-frame', 'shape-canvas', 'direction-grid', 'ruler'
]);

const getOverflow = async (page) => page.evaluate(() => {
  const shell = document.querySelector('[data-testid="mik-route"]');
  const board = document.querySelector('[data-v6-renderer]');
  const delta = document.documentElement.scrollWidth - window.innerWidth;
  // Report visible offending elements, but exclude descendants confined within
  // a deliberate local horizontal scrollport (ruler/number-line/geometry).
  const offenders = [...document.querySelectorAll('body *')].filter(el => {
    const box = el.getBoundingClientRect();
    if (box.width <= 1 || box.right <= window.innerWidth + 1) return false;
    let ancestor = el.parentElement;
    while (ancestor && ancestor !== document.body) {
      const cs = getComputedStyle(ancestor);
      if (/^(auto|scroll|hidden|clip)$/.test(cs.overflowX) &&
          ancestor.getBoundingClientRect().right <= window.innerWidth + 1) return false;
      ancestor = ancestor.parentElement;
    }
    return true;
  }).slice(0, 8).map(el => {
    const rect = el.getBoundingClientRect();
    return { element: el.tagName.toLowerCase(), className: String(el.className?.baseVal ?? el.className).slice(0,100),
      right: Math.round(rect.right), width: Math.round(rect.width) };
  });
  return { delta, routeWidth: shell?.getBoundingClientRect().width,
    boardWidth: board?.getBoundingClientRect().width, offenders };
});

for (const [index, fixture] of fixtures.entries()) {
  if (!vulnerable.has(fixture.renderer)) continue;
  test(`MIK Router phone-width containment: ${fixture.renderer}`, async ({ page }) => {
    await page.goto('/dev/v6');
    await page.getByTestId('v6-gallery-renderer').selectOption(String(index));
    const router = page.getByTestId('mik-route');
    await expect(router).toHaveAttribute('data-mik-implementation', 'legacy');
    await expect(router).toHaveClass(/mik-implementation-route/);
    for (const skin of ['exploration-lab', 'healing']) {
      await page.getByTestId('v6-gallery-skin').selectOption(skin);
      for (const width of [320, 390]) {
        await page.setViewportSize({ width, height: 900 });
        const measured = await getOverflow(page);
        expect(measured.delta,
          `${fixture.renderer} ${skin} ${width}px, ${JSON.stringify(measured)}`
        ).toBeLessThanOrEqual(1);
        expect(measured.routeWidth).toBeLessThanOrEqual(width);
        expect(measured.boardWidth).toBeLessThanOrEqual(width);
      }
    }
  });
}
