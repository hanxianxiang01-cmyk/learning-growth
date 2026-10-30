import asyncio,json,sys,traceback
from pathlib import Path
from playwright.async_api import async_playwright
from runner import BASE,APP,mount,BROWSER
FIX=json.loads((APP/'src/dev/v6/fixtures.json').read_text())
EVID=BASE/'evidence'; (EVID/'screenshots').mkdir(exist_ok=True)
async def click(page,id,n=1):
 for _ in range(n):await page.get_by_test_id(id).click()
async def answer(page):return json.loads(await page.get_by_test_id('v6-gallery-response').text_content())
async def solve(p,renderer,correct=False,mode=''):
 if renderer=='number-line':
  for n in ([25,30,35] if correct else [25,30]):await click(p,f'v6-line-tick-{n}')
 elif renderer=='column-arithmetic':
  for label,val in [('百位结果','0'),('十位结果','7'),('个位结果','5' if correct else '4')]:await p.get_by_label(label,exact=True).fill(val)
  if correct:await p.get_by_label('个位进位到十位',exact=True).click()
 elif renderer=='object-counter':
  await click(p,'oc-add-g1',4);await click(p,'oc-add-g2',3 if correct else 2)
 elif renderer=='number-input':await p.get_by_test_id('ni-input').fill('5' if correct else '4')
 elif renderer=='ten-frame':
  for n in range(10 if correct else 9):await click(p,f'tf-cell-{n}')
  if correct:
   await click(p,'tf-make-ten')
   for n in range(3):await click(p,f'tf-cell-{n}')
 elif renderer=='bar-model':
  for bar,n in [('a',5),('b',3),('c',8 if correct else 7)]:await click(p,f'bm-plus-{bar}',n)
 elif renderer=='place-value':
  for i,n in enumerate([3,5,2] if correct else [2,5,3]):await click(p,f'pv-tile-{n}');await click(p,f'pv-slot-{i}')
 elif renderer=='formula-board':
  if mode=='unknown_number':await click(p,'fb-slot-box');await click(p,'fb-key-5' if correct else 'fb-key-4')
  else:await click(p,'fb-slot-op0');await click(p,'fb-op-minus' if correct else 'fb-op-plus')
 elif renderer=='array-board':await click(p,'ab-row-plus',3 if correct else 2);await click(p,'ab-col-plus',4)
 elif renderer=='grouping-board':
  n=3 if correct else 2;await click(p,'gb-add-group',n)
  for i in range(n):await click(p,f'gb-give-{i}',4 if correct else 6)
 elif renderer=='estimation-canvas':
  await p.get_by_test_id('ec-slider').evaluate('''(e,v)=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,String(v));e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));}''',40 if correct else 30)
  await click(p,'ec-reason-use_reference')
 elif renderer=='shape-gallery':
  for n in (['s1','s2','s3'] if correct else ['r1']):await click(p,f'sg-shape-{n}');await click(p,'v6-sg-place-home')
 elif renderer=='shape-canvas':
  for x,y in ([(0,0),(3,0),(3,2),(0,2)] if correct else [(0,0),(1,0),(1,1),(0,1)]):await click(p,f'sc-peg-{x}-{y}')
 elif renderer=='sorting-board':
  await click(p,'sb-card-0');await click(p,'sb-card-1')
  if correct:await click(p,'sb-card-1');await click(p,'sb-card-3')
 elif renderer=='direction-grid':
  await click(p,'dg-cell-2-3')
  if correct:await click(p,'dg-cell-2-4');await click(p,'dg-cell-3-4')
 elif renderer=='clock':await p.get_by_label('小时加一',exact=True).click();await p.get_by_label('小时加一',exact=True).click();
 elif renderer=='money-board':
  await click(p,'mb-add-10',3)
  if correct:await click(p,'mb-add-5')
 elif renderer=='pattern-board':await click(p,'pb-token-1' if correct else 'pb-token-2');await click(p,'pb-token-2')
 elif renderer=='ruler':await click(p,'rl-tick-3' if correct else 'rl-tick-0');await click(p,'rl-tick-8')
 if renderer=='clock' and correct:await p.get_by_label('小时加一',exact=True).click()
async def native_reset(page,renderer):
 board=page.locator('[data-v6-renderer]')
 if renderer=='number-input':await click(page,'v6-key-clear')
 else:await board.get_by_role('button',name='清空' if renderer=='shape-canvas' else '重置',exact=True).click()
async def main(start=0,stop=20):
 results=[]
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=BROWSER,headless=True,args=['--no-sandbox'])
  p=await browser.new_page(viewport={'width':1280,'height':1000},reduced_motion='reduce');p.set_default_timeout(3000)
  errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  await mount(p)
  for index in range(start,stop):
   f=FIX[index];row={'fixture':f['id'],'renderer':f['renderer'],'status':'FAIL','checks':[]}
   try:
    await p.set_viewport_size({'width':1280,'height':1000})
    await p.get_by_test_id('v6-gallery-renderer').select_option(str(index));await p.get_by_test_id('v6-gallery-reset').click()
    await p.get_by_test_id('v6-gallery-skin').select_option('exploration-lab')
    await p.wait_for_timeout(65)
    board=p.locator('[data-v6-renderer]');submit=board.locator('button.primary-button').last
    assert await board.count()==1
    assert await submit.is_disabled(), 'empty submit should be disabled';row['checks'].append('empty-submit-blocked')
    await solve(p,f['renderer'],False,f['task']['ui_schema']['workspaces'][0]['mode'])
    await p.wait_for_timeout(40)
    assert await submit.is_enabled(),'valid wrong answer blocked'
    wrong=await answer(p);assert str(wrong['answer'])!=f['expected']
    await submit.click();captured=json.loads(await p.get_by_test_id('v6-gallery-submission').text_content());assert captured==wrong
    assert wrong.get('v2_workspaces') and wrong.get('interaction_events')
    row['wrong']=wrong;row['checks'].append('valid-wrong-submits-original-payload')
    await p.get_by_test_id('v6-gallery-skin').select_option('healing');await p.wait_for_timeout(40)
    assert await answer(p)==wrong;row['checks'].append('skin-change-preserves-state-events')
    for width in [768,390,320]:
     await p.set_viewport_size({'width':width,'height':900});await p.wait_for_timeout(35)
     assert await answer(p)==wrong
     overflow=await p.evaluate('document.documentElement.scrollWidth-window.innerWidth')
     assert overflow<=1,f'viewport {width} overflow={overflow}'
    row['checks'].append('768-390-320-width-state-and-overflow')
    await p.get_by_test_id('v6-gallery-lock').check();assert await submit.is_disabled()
    active=await board.locator('button:enabled,input:enabled').count()
    assert active==0,f'{active} controls not locked'
    await p.get_by_test_id('v6-gallery-lock').uncheck();assert await answer(p)==wrong
    row['checks'].append('external-disable-preserves-and-locks')
    await native_reset(p,f['renderer']);await p.wait_for_timeout(40)
    assert await submit.is_disabled(),'reset should restore not-ready'
    row['checks'].append('native-reset-restores-initial-readiness')
    await solve(p,f['renderer'],True,f['task']['ui_schema']['workspaces'][0]['mode']);await p.wait_for_timeout(40)
    correct=await answer(p);assert str(correct['answer'])==f['expected'],f"expected {f['expected']} received {correct['answer']}"
    assert await submit.is_enabled()
    await submit.click();assert json.loads(await p.get_by_test_id('v6-gallery-submission').text_content())==correct
    row['correct']=correct;row['checks'].append('correct-answer-and-payload')
    await p.set_viewport_size({'width':390,'height':900})
    await p.locator('.v6-task-content').screenshot(path=str(EVID/'screenshots'/f'{index:02d}-{f["renderer"]}-healing-390.png'))
    await p.set_viewport_size({'width':1280,'height':1000});await p.get_by_test_id('v6-gallery-skin').select_option('exploration-lab')
    await p.locator('.v6-task-content').screenshot(path=str(EVID/'screenshots'/f'{index:02d}-{f["renderer"]}-lab-1280.png'))
    assert not errors,errors
    row['status']='PASS'
   except Exception as e:
    row['failure']=str(e);row['trace']=traceback.format_exc();row['runtime_errors']=list(errors)
    await p.screenshot(path=str(EVID/'screenshots'/f'FAIL-{index:02d}.png'),full_page=True)
   print(index,f['renderer'],row['status'],row.get('failure',''),flush=True);results.append(row)
   (EVID/f'renderer-browser-{start}-{stop}.json').write_text(json.dumps({'harness':await p.evaluate('window.__harnessMeta'),'browser':browser.version,'results':results},ensure_ascii=False,indent=2))
  await browser.close()
 if any(r['status']!='PASS' for r in results): raise SystemExit(1)
if __name__=='__main__':asyncio.run(main(*(map(int,sys.argv[1:]) if len(sys.argv)>1 else [0,20])))
