import { test, expect, request as newRequest } from '@playwright/test';
import { normalizeSessionResult } from '../src/lib/api/sessionResultNormalizer.ts';

/**
 * Real HTTP integration gate. No route.fulfill: only add the existing QA-only pin
 * parameter to the request sent to the real server. Judge and persistence are real.
 * This suite writes ONLY to the repository's QA child, never the real child.
 */
const API=process.env.E2E_API_BASE ?? 'http://127.0.0.1:8000';
const QA_CHILD='00000000-0000-0000-0000-000000000099';
test.skip(process.env.E2E_V6!=='1'||process.env.E2E_V6_LIVE!=='1', 'Opt in with E2E_V6=1 E2E_V6_LIVE=1. Requires HTTP mode and QA-only database.');

async function pinNext(page,request){
  if(process.env.E2E_CHILD_ID && process.env.E2E_CHILD_ID!==QA_CHILD)throw new Error('Refusing any non-QA child.');
  const c=await request.get(`${API}/v1/content/v2-catalog`);expect(c.ok()).toBe(true);
  const items=(await c.json()).items ?? [];
  // Catalog intentionally exposes title, not seed code; assert exact config after pin.
  const gold=items.find(it=>it.renderer==='clock'&&it.mode==='time_setting'&&it.title==='把钟拨到 6 点');
  if(!gold)throw new Error('Seeded V2-R17-CLOCK-001 missing from catalog; do not silently pick an unrelated clock.');
  const session=await request.post(`${API}/v1/learning/sessions`,{data:{child_id:QA_CHILD,subject:'math',requested_minutes:15}});expect(session.ok()).toBe(true);
  const sid=(await session.json()).session_id;expect(sid).toMatch(/^[0-9a-f-]{36}$/i);
  await page.route('**/v1/learning/tasks/next',async route=>{
    const original=route.request().postDataJSON();
    expect(original.child_id).toBe(QA_CHILD);expect(original.session_id).toBe(sid);
    await route.continue({postData:JSON.stringify({...original,pin_resource_version_id:gold.resource_version_id})});
  });
  const arrived=page.waitForResponse(r=>r.url().endsWith('/v1/learning/tasks/next')&&r.request().method()==='POST');
  await page.goto(`/child/math/session/${sid}?child_id=${QA_CHILD}`);
  const task=await (await arrived).json();
  expect(task.ui_schema.workspaces[0].config).toMatchObject({start:[3,0],target:[6,0]});
  await expect(page.getByTestId('v6-learning-screen')).toBeVisible();
  await expect(page.getByTestId('ck-time')).toHaveText('3:00');
  return {sid,task};
}
async function submit(page){
  const req=page.waitForRequest(r=>r.url().endsWith('/v1/learning/attempts')&&r.method()==='POST');
  const res=page.waitForResponse(r=>r.url().endsWith('/v1/learning/attempts')&&r.request().method()==='POST');
  await page.getByTestId('ck-submit').click();
  const result=await res;expect(result.ok()).toBe(true);return {body:(await req).postDataJSON(),result:await result.json()};
}

test('LIVE V6 clock: wrong minute → server feedback/hint → retry → correct → saved session result',async({page,request})=>{
  const {sid,task}=await pinNext(page,request);
  await page.getByTestId('ck-hour-6').focus();await page.keyboard.press('Enter');
  await page.getByTestId('ck-minute-handle').focus();await page.keyboard.press('End');
  await expect(page.getByTestId('ck-time')).toHaveText('6:30');
  await expect(page.getByTestId('ck-submit')).toBeEnabled();
  const wrong=await submit(page);
  expect(wrong.body.task_instance_id).toBe(task.task_instance_id);
  expect(wrong.body.response.answer.value).toBe(390);expect(wrong.body.attempt_no).toBe(1);
  expect(wrong.body.response.type).toBe('clock');expect(wrong.result.correct).toBe(false);
  expect(wrong.body.response.workspaces[0].data.adjust_history).toEqual([['hour',3,6],['minute',0,30]]);
  expect(wrong.body.response.workspaces[0].data.evidence).toBeTruthy();
  await expect(page.getByTestId('v6-learning-feedback')).toHaveAttribute('data-feedback-state','incorrect');
  if(['HINT','TEACH'].includes(wrong.result.next_action?.type)){
    const response=page.waitForResponse(r=>r.url().endsWith('/v1/learning/hints')&&r.request().method()==='POST');
    await page.getByTestId('v6-hint').click();const r=await response;expect(r.ok()).toBe(true);
    expect(r.request().postDataJSON().attempt_id).toBe(wrong.result.attempt_id);
  }
  await page.getByTestId('v6-retry').click();
  await expect(page.getByTestId('ck-time')).toHaveText('6:30');
  await expect(page.getByTestId('ck-submit')).toBeEnabled();
  await page.getByTestId('ck-minute-handle').focus();await page.keyboard.press('Home');
  await expect(page.getByTestId('ck-time')).toHaveText('6:00');
  const correct=await submit(page);
  expect(correct.result.correct).toBe(true);expect(correct.body.attempt_no).toBe(2);
  expect(correct.body.submission_id).not.toBe(wrong.body.submission_id);expect(correct.body.response.answer.value).toBe(360);
  const saved=await request.get(`${API}/v1/learning/sessions/${sid}/result`);expect(saved.ok()).toBe(true);
  const normalized=normalizeSessionResult(await saved.json(),sid);expect(normalized.attempt_count).toBe(2);
  // Independent request context: result must exist without the screen's local sessionStorage.
  const independent=await newRequest.newContext();
  try {
    const remote=await independent.get(`${API}/v1/learning/sessions/${sid}/result`,{headers:{'Cache-Control':'no-cache'}});expect(remote.ok()).toBe(true);
    expect(normalizeSessionResult(await remote.json(),sid).attempt_count).toBe(2);
  } finally { await independent.dispose(); }
});

test('LIVE V6 clock: lost acknowledged response retransmits identical submission without double record',async({page,request})=>{
  const {sid}=await pinNext(page,request);await page.getByTestId('ck-hour-6').click();
  const posts=[];let drop=true;
  await page.route('**/v1/learning/attempts',async route=>{
    posts.push(route.request().postDataJSON());
    if(drop){drop=false;const persisted=await route.fetch();expect(persisted.ok()).toBe(true);await route.abort('failed');}
    else await route.continue();
  });
  await page.getByTestId('ck-submit').click();await expect(page.getByTestId('v6-recover')).toBeVisible();
  await expect(page.getByTestId('ck-submit')).toBeDisabled();
  const ack=page.waitForResponse(r=>r.url().endsWith('/v1/learning/attempts')&&r.status()===200);
  await page.getByTestId('v6-recover').click();await ack;
  expect(posts.length).toBe(2);expect(posts[1]).toEqual(posts[0]);
  const saved=await request.get(`${API}/v1/learning/sessions/${sid}/result`);expect(saved.ok()).toBe(true);
  expect(normalizeSessionResult(await saved.json(),sid).attempt_count).toBe(1);
});
