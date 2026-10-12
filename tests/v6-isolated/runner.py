import asyncio,json,base64,os,shutil
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(os.environ.get('V6_SOURCE_ROOT', str(Path(__file__).resolve().parents[2])))
BASE=Path(os.environ.get('V6_ARTIFACT_DIR', str(ROOT/'.cache/v6-isolated')))
APP=ROOT/'apps/child-web'
BROWSER=os.environ.get('V6_BROWSER_EXECUTABLE') or shutil.which('chromium') or shutil.which('google-chrome')
(BASE/'evidence').mkdir(parents=True,exist_ok=True)
async def mount(page,initial='/dev/v6'):
 await page.set_content('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="root"></div></body></html>')
 await page.add_style_tag(content=(APP/'app/globals.css').read_text()+'\n'+(APP/'app/ui-v6.css').read_text())
 await page.add_script_tag(type='module',content=(BASE/'harness/vendor-inline.js').read_text())
 await page.wait_for_function('!!window.__vendor')
 assets={'/child-ui-v6/'+p.name:'data:image/svg+xml;base64,'+base64.b64encode(p.read_bytes()).decode() for p in (APP/'public/child-ui-v6').glob('*.svg')}
 await page.evaluate('(p)=>{window.__modules=p.mods;window.__assets=p.assets;window.__initialPath=p.initial}',{'mods':json.loads((BASE/'harness/modules.json').read_text()),'assets':assets,'initial':initial})
 await page.add_script_tag(content=(Path(__file__).parent/'bootstrap.js').read_text())
 await page.wait_for_timeout(160)
async def main():
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=BROWSER,headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1280,'height':1000},reduced_motion='reduce')
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await mount(page)
  print('TEXT', (await page.locator('body').inner_text())[:1400]);print('ERRORS',errors)
  await page.screenshot(path=str(BASE/'evidence/initial-gallery.png'),full_page=True)
  if not errors:
   fixtures=json.loads((APP/'src/dev/v6/fixtures.json').read_text());rows=[]
   for i,f in enumerate(fixtures):
    await page.get_by_test_id('v6-gallery-renderer').select_option(str(i))
    await page.wait_for_timeout(80)
    board=page.locator('[data-v6-renderer]')
    rows.append({'fixture':f['id'],'v6':await board.count(),'controls':await board.locator('button,input').evaluate_all('(es)=>es.map(e=>({id:e.getAttribute("data-testid"),label:e.getAttribute("aria-label"),text:e.textContent,disabled:e.disabled,tag:e.tagName,class:e.className}))'),'errors':list(errors)})
   (BASE/'evidence/controls.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
   print([(r['fixture'],r['v6']) for r in rows])
  await browser.close()
if __name__=='__main__':asyncio.run(main())
