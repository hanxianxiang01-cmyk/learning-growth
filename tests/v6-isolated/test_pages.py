import asyncio,json,traceback
from pathlib import Path
from playwright.async_api import async_playwright
from runner import mount,APP,BASE,BROWSER
E=BASE/'evidence';FIX=json.loads((APP/'src/dev/v6/fixtures.json').read_text());CLOCK=next(f['task'] for f in FIX if f['renderer']=='clock')
CLOCK['task_instance_id']='20000000-0000-0000-0000-000000000016'
IDS=['app_rel','app_check','app_rd','app_transfer','app_model','app_cond','app_strat']
NAMES=['数量关系','检查验算','读题理解','迁移变式','建模表征','条件识别','策略选择']
ABILITIES=[dict(ability_id=id,name=name,level=[2,1,2,1,0,1,0][i],confidence=.5,evidence_count=[6,3,4,1,0,2,0][i],trend='stable' if i in [0,4] else 'watch') for i,(id,name) in enumerate(zip(IDS,NAMES))]
RESULT={'session_id':'30000000-0000-0000-0000-000000000001','child_id':'00000000-0000-0000-0000-000000000099','status':'completed','duration_ms':180000,'task_count':1,'completed_count':1,'attempt_count':2,'hint_usage':[1],'learning_behaviors':[{'code':'RETRY','label':'遇到困难后继续尝试','achieved':True},{'code':'CHECK','label':'主动检查自己的答案','achieved':False}],'ability_changes':[{'ability_id':'app_cond','name':'条件识别','before_level':1,'after_level':1,'evidence_delta':1,'trend':'watch'}],'next_recommendation':{'type':'NEXT','title':'继续一个小挑战','description':'用自己的节奏继续探索。'}}
JS=r'''data=>{
 window.__testData=data;window.__attemptIndex=0;window.__fail={};window.__delay=0;
 window.__apiHandler=async(call)=>{
  if(window.__delay)await new Promise(r=>setTimeout(r,window.__delay));
  const path=new URL(call.url).pathname;
  if(window.__fail[path]){const how=window.__fail[path];if(typeof how==='number')window.__fail[path]--;return {status:503,body:{message:'fixture service unavailable'}};}
  if(path.endsWith('/profile'))return {body:{child_id:data.result.child_id,grade:'2',active_abilities:data.abilities,strengths:['app_rel'],developing:['app_cond'],observations:['继续尝试用图和文字表达自己的想法。']}};
  if(path.endsWith('/abilities'))return {body:window.__testData.abilities};
  if(path==='/v1/learning/sessions')return {body:{session_id:data.result.session_id,child_id:data.result.child_id,subject:'math',status:'active'}};
  if(path.endsWith('/tasks/next'))return {body:data.clock};
  if(path.endsWith('/attempts')){const index=window.__attemptIndex++;return {body:index===0?{attempt_id:'40000000-0000-0000-0000-000000000001',correct:false,next_action:{type:'HINT',hint_level:1}}:{attempt_id:'40000000-0000-0000-0000-000000000002',correct:true,next_action:{type:'COMPLETE'}}};}
  if(path.endsWith('/hints'))return {body:{hint_level:1,policy_id:'fixture-hint-1',action_type:'QUESTION',text:'先找到6点的位置，再看看长针是否指向12。',answer_revealed:false}};
  if(path.endsWith('/result'))return {body:data.result};
  return {status:404,body:{message:'unhandled fixture '+path}};
 };
}'''
async def setup(page):
 await mount(page);await page.evaluate(JS,{'abilities':ABILITIES,'clock':CLOCK,'result':RESULT})
async def screen(p,name,skin,width):
 await p.evaluate('(v)=>window.__setSkin(v)',skin);await p.set_viewport_size({'width':width,'height':950});await p.wait_for_timeout(90)
 assert await p.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'),f'{name} overflow {width}'
 await p.screenshot(path=str(E/'screenshots'/f'page-{name}-{skin}-{width}.png'),full_page=True)
async def main():
 tests=[]
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=BROWSER,headless=True,args=['--no-sandbox']);p=await browser.new_page(viewport={'width':1280,'height':950},reduced_motion='reduce');p.set_default_timeout(4000)
  errors=[];p.on('pageerror',lambda e:errors.append(str(e)));await setup(p)
  async def run(name,fn):
   row={'name':name,'status':'FAIL'}
   try:await fn();row['status']='PASS'
   except Exception as err:row['detail']=str(err);row['trace']=traceback.format_exc();await p.screenshot(path=str(E/'screenshots'/('FAIL-page-'+str(len(tests))+'.png')),full_page=True)
   tests.append(row);print(name,row['status'],row.get('detail',''),flush=True)
  async def home():
   await p.evaluate("window.__navigate('/child/math')");await p.get_by_test_id('v6-home-start').wait_for()
   assert await p.locator('.v6-task-entry').count()==5
   assert await p.locator('.v6-record-count strong').inner_text()=='5'
   assert not await p.locator('select').count()
   for skin in ['exploration-lab','healing']:
    for width in [1280,390,320]:await screen(p,'home',skin,width)
  await run('home-api-bound-five-challenges-both-skins-1280-390-320',home)
  async def growth():
   await p.evaluate("window.__navigate('/child/math/growth')");await p.get_by_test_id('v6-node-app_rel').wait_for()
   assert await p.locator('[data-v6-node]').count()==7
   for skin in ['exploration-lab','healing']:
    for width in [1280,390,320]:await screen(p,'growth',skin,width)
   await p.get_by_test_id('v6-node-app_model').click()
   assert '暂无记录' in await p.get_by_test_id('v6-node-app_model').inner_text()
   assert '很稳定' not in await p.get_by_test_id('v6-node-app_model').inner_text()
   detail=p.locator('.v6-mobile-node-detail');assert await detail.is_visible()
   await detail.get_by_role('button',name='查看相关记录').click();assert '暂时还没有' in await detail.inner_text()
   await p.set_viewport_size({'width':1280,'height':950});assert await p.locator('.v6-map-detail-wide').is_visible()
   assert await p.get_by_test_id('v6-node-app_model').get_attribute('aria-pressed')=='true'
   assert '建模表征' in await p.locator('.v6-map-detail-wide').inner_text()
  await run('growth-seven-nodes-selection-responsive-detail-and-zero-records',growth)
  async def empty():
   await p.evaluate("window.__testData.abilities=[];window.__navigate('/child/math')");await p.get_by_test_id('v6-home-start').wait_for()
   await p.evaluate("window.__navigate('/child/math/growth')");await p.get_by_test_id('v6-node-app_rel').wait_for()
   assert await p.locator('[data-v6-node]:disabled').count()==0
   assert '成长从一次尝试开始' in await p.locator('body').inner_text()
   assert '待了解' in await p.get_by_test_id('v6-node-app_rel').inner_text()
   await screen(p,'growth-empty','healing',390)
   await p.evaluate('(v)=>window.__testData.abilities=v',ABILITIES)
  await run('empty-ability-data-not-fabricated-or-locked',empty)
  async def loading_error():
   await p.evaluate("window.__delay=350;window.__navigate('/child/math')")
   await p.get_by_role('heading',name='正在准备今天的学习').wait_for();await p.get_by_test_id('v6-home-start').wait_for()
   await p.evaluate("window.__delay=0;window.__fail['/v1/children/00000000-0000-0000-0000-000000000099/abilities']=1;window.__navigate('/child/math/growth')")
   await p.get_by_role('heading',name='成长记录暂时没加载成功').wait_for();assert not await p.locator('[data-v6-node]').count()
   await p.get_by_role('button',name='重新加载',exact=True).click();await p.get_by_test_id('v6-node-app_rel').wait_for()
  await run('loading-api-failure-and-retry',loading_error)
  async def flow():
   await p.evaluate("window.__navigate('/child/math');window.__attemptIndex=0;window.__apiCalls=[]")
   await p.get_by_test_id('v6-home-start').wait_for();await p.get_by_test_id('v6-home-start').click()
   await p.get_by_test_id('clock-v2').wait_for();assert not await p.get_by_test_id('v6-hint').count()
   await p.get_by_label('小时加一',exact=True).click();await p.get_by_label('小时加一',exact=True).click()
   # Repeated same-tick clicks must produce just one request through the real hook guard.
   await p.get_by_test_id('ck-submit').evaluate('(b)=>{b.click();b.click();}')
   await p.get_by_test_id('v6-retry').wait_for()
   assert await p.get_by_test_id('ck-time').inner_text()=='5:00'
   assert await p.get_by_test_id('ck-submit').is_disabled()
   assert await p.evaluate("window.__apiCalls.filter(x=>x.url.endsWith('/attempts')).length")==1
   await screen(p,'learning-incorrect','exploration-lab',1280)
   await p.get_by_test_id('v6-hint').click();await p.get_by_text('先找到6点的位置，再看看长针是否指向12。',exact=True).wait_for()
   hints=await p.evaluate("window.__apiCalls.filter(x=>x.url.endsWith('/hints'))")
   assert hints[0]['body']['attempt_id']=='40000000-0000-0000-0000-000000000001'
   await screen(p,'learning-hint','healing',390)
   await p.get_by_test_id('v6-retry').click();assert await p.get_by_test_id('ck-time').inner_text()=='5:00'
   await p.get_by_label('小时加一',exact=True).click();await p.get_by_test_id('ck-submit').click()
   await p.get_by_test_id('v6-result-screen').wait_for();await p.get_by_text('这次探索，告一段落',exact=True).wait_for()
   calls=await p.evaluate('window.__apiCalls');attempts=[x['body'] for x in calls if x['url'].endswith('/attempts')]
   assert len(attempts)==2
   assert [x['response']['answer']['value'] for x in attempts]==[300,360]
   assert [x['attempt_no'] for x in attempts]==[1,2]
   assert all(x['response']['schema_version']=='2.0' for x in attempts)
   assert attempts[0]['submission_id']!=attempts[1]['submission_id']
   assert 'used_hint_levels' not in attempts[1] # frozen V2 envelope; hint activity is a separate endpoint
   (E/'page-flow-api-calls.json').write_text(json.dumps(calls,ensure_ascii=False,indent=2))
   for skin in ['exploration-lab','healing']:
    for width in [1280,390,320]:await screen(p,'result',skin,width)
  await run('real-http-client-mocked-fetch-home-clock-wrong-hint-retry-correct-result',flow)
  async def transport_retry():
   await p.evaluate("window.__navigate('/child/math');window.__attemptIndex=0;window.__apiCalls=[];window.__fail['/v1/learning/attempts']=1")
   await p.get_by_test_id('v6-home-start').wait_for();await p.get_by_test_id('v6-home-start').click();await p.get_by_test_id('clock-v2').wait_for()
   await p.get_by_label('小时加一',exact=True).click();await p.get_by_test_id('ck-submit').click();await p.get_by_test_id('v6-recover').wait_for()
   assert await p.get_by_test_id('ck-submit').is_disabled();assert await p.get_by_label('小时加一',exact=True).is_disabled()
   await p.get_by_test_id('v6-recover').click();await p.get_by_test_id('v6-retry').wait_for()
   req=await p.evaluate("window.__apiCalls.filter(x=>x.url.endsWith('/attempts')).map(x=>x.body)")
   assert len(req)==2 and req[0]==req[1]
   (E/'transport-retry-identical-payload.json').write_text(json.dumps(req,ensure_ascii=False,indent=2))
  await run('uncertain-network-failure-locks-and-retransmits-identical-submission',transport_retry)
  async def result_unavailable():
   path=f'/v1/learning/sessions/{RESULT["session_id"]}/result'
   await p.evaluate('(path)=>{window.__fail[path]=1;window.__navigate("/child/math/result/'+RESULT['session_id']+'")}',path)
   await p.get_by_role('heading',name='暂时没有拿到学习小结').wait_for();await p.get_by_role('button',name='重新加载').click()
   await p.get_by_role('heading',name='这次探索，告一段落').wait_for()
  await run('result-unavailable-retry-without-fabricated-statistics',result_unavailable)
  if errors:tests.append({'name':'runtime-errors','status':'FAIL','detail':errors})
  else:tests.append({'name':'runtime-errors','status':'PASS'})
  (E/'page-browser.json').write_text(json.dumps({'harness':await p.evaluate('window.__harnessMeta'),'browser':browser.version,'tests':tests},ensure_ascii=False,indent=2));await browser.close()
 if any(t['status']!='PASS' for t in tests): raise SystemExit(1)
if __name__=='__main__':asyncio.run(main())
