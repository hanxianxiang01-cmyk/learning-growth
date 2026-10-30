import { test, expect } from '@playwright/test';

// Requires a running Next dev server; no backend or test data writes.
// Explicit opt-in protects the existing broad e2e script from accidentally expanding scope.
test.skip(process.env.E2E_V6 !== '1', 'Set E2E_V6=1 and use playwright.v6.config.mjs.');

for (const width of [390, 820, 1440]) for (const skin of ['exploration-lab', 'healing']) {
  test(`V6 clock gallery ${width}px ${skin}: keyboard, wrong submission, undo, skin retention`, async ({ page }) => {
    const errors=[];page.on('pageerror', e=>errors.push(e.message));
    await page.setViewportSize({width,height:width===390?844:width===820?1180:1024});
    await page.goto('/dev/v6-clock');
    await page.getByTestId('v6-gallery-skin').selectOption(skin);
    const clock=page.getByTestId('clock-v2');
    await expect(clock).toBeVisible();
    await expect(page.getByTestId('ck-time')).toHaveText('3:00');
    await expect(page.getByTestId('ck-submit')).toBeDisabled();
    await expect(page.getByTestId('ck-undo')).toBeDisabled();

    const digit6=page.getByTestId('ck-hour-6');
    await digit6.focus();await page.keyboard.press('Enter');
    await expect(page.getByTestId('ck-time')).toHaveText('6:00');
    const minute=page.getByTestId('ck-minute-handle');
    await minute.focus();await page.keyboard.press('End');
    await expect(page.getByTestId('ck-time')).toHaveText('6:30');
    await expect(minute).toBeFocused();
    await expect(page.getByTestId('ck-submit')).toBeEnabled();
    // Local display must not give away correctness; dev submission is an envelope capture only.
    await expect(page.getByTestId('ck-evaluation')).not.toContainText(/PASS|FAIL|差 30|答对|看着.*长针/);
    await page.getByTestId('ck-submit').click();
    const captured=await page.getByTestId('v6-gallery-submission').textContent();
    expect(JSON.parse(captured).answer).toBe('390');
    await page.getByTestId('ck-undo').click();
    await expect(page.getByTestId('ck-time')).toHaveText('6:00');
    await page.getByTestId('v6-gallery-skin').selectOption(skin==='healing'?'exploration-lab':'healing');
    await expect(page.getByTestId('ck-time')).toHaveText('6:00');
    const cta=page.getByTestId('ck-submit');
    expect(await cta.evaluate(el=>getComputedStyle(el).backgroundColor)).toBe('rgb(10, 105, 114)');
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    await page.getByTestId('ck-reset').click();
    await expect(page.getByTestId('ck-time')).toHaveText('3:00');
    await expect(cta).toBeDisabled();
    expect(errors).toEqual([]);
  });
}

test('V6 clock: one drag is one undo; Escape cancels without response mutation',async({page})=>{
  await page.setViewportSize({width:820,height:1180});await page.goto('/dev/v6-clock');
  const hour=page.getByTestId('ck-hour-handle');
  const face=await page.getByTestId('ck-face').boundingBox();
  const start=await hour.boundingBox();
  const point=(x,y)=>({x:face.x+x/360*face.width,y:face.y+y/360*face.height});
  const six=point(180,234),nine=point(126,180);
  await page.mouse.move(start.x+start.width/2,start.y+start.height/2);await page.mouse.down();
  await page.mouse.move(six.x,six.y,{steps:8});await page.mouse.up();
  await expect(page.getByTestId('ck-time')).toHaveText('6:00');
  await page.getByTestId('ck-undo').click();await expect(page.getByTestId('ck-time')).toHaveText('3:00');
  await expect(page.getByTestId('ck-undo')).toBeDisabled();
  const s2=await hour.boundingBox();await page.mouse.move(s2.x+s2.width/2,s2.y+s2.height/2);await page.mouse.down();await page.mouse.move(nine.x,nine.y,{steps:8});await page.keyboard.press('Escape');await page.mouse.up();
  await expect(page.getByTestId('ck-time')).toHaveText('3:00');await expect(page.getByTestId('ck-undo')).toBeDisabled();
});
