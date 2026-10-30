/** Full V6 migration inventory + executable presentation checks. Not an app typecheck. */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { parseOptions, launchPlan } from '../../../scripts/run-child-ui.mjs';
const app=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const root=path.resolve(app,'../..');
const require=createRequire(import.meta.url);
let ts;
try { ts=require(process.env.V6_TYPESCRIPT_PATH || 'typescript'); }
catch { console.error('BLOCKED: TypeScript unavailable. Run npm ci.'); process.exit(2); }
const cache=new Map();
const context=vm.createContext({console,process:{env:{}},Math,Date,JSON,Number,String,Object,Array,Map,Set});
function load(rel) {
  let file=path.resolve(app,rel); if (!path.extname(file)) file+='.ts';
  if(cache.has(file)) return cache.get(file).exports;
  const module={exports:{}};cache.set(file,module);
  const source=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS},fileName:file}).outputText;
  const req=spec=>load(spec.startsWith('@/')?spec.slice(2):path.resolve(path.dirname(file),spec));
  new vm.Script(`(function(require,module,exports){${source}\n})`,{filename:file}).runInContext(context)(req,module,module.exports);
  return module.exports;
}
const results=[];
function test(name,fn) { try { fn();results.push({name,status:'PASS'}); } catch(error) {results.push({name,status:'FAIL',detail:String(error.stack||error)});} }
const read=rel=>fs.readFileSync(path.join(app,rel),'utf8');
const fixtures=JSON.parse(read('src/dev/v6/fixtures.json'));
const registry=load('src/features/task-renderer/rendererRegistry');
const ability=load('src/features/ui-v6/abilityPresentation');
const config=load('src/config').config;
const names={ 'object-counter':'ObjectCounterV2','bar-model':'BarModelV2','number-line':'NumberLineV2','number-input':'NumberInputV2','column-arithmetic':'ColumnArithmetic','place-value':'PlaceValueV2','ten-frame':'TenFrameV2','array-board':'ArrayBoardV2','grouping-board':'GroupingBoardV2','formula-board':'FormulaBoardV2','estimation-canvas':'EstimationCanvasV2','shape-gallery':'ShapeGalleryV2','shape-canvas':'ShapeCanvasV2','sorting-board':'SortingBoardV2','direction-grid':'DirectionGridV2','ruler':'RulerV2','clock':'ClockV2','money-board':'MoneyBoardV2','pattern-board':'PatternBoardV2' };
test('twenty original examples cover all nineteen frozen release renderer IDs',()=>{
  assert.equal(fixtures.length,20); assert.equal(new Set(fixtures.map(f=>f.renderer)).size,19);
  assert.deepEqual([...new Set(fixtures.map(f=>f.renderer))].sort(),Array.from(registry.V2_RELEASE_RENDERER_IDS).sort());
});
for(const [id,filename] of Object.entries(names)) test(`${id}: explicit V6 branch and existing legacy branch remain`,()=>{
  const source=read(`src/components/renderers/${filename}.tsx`);
  assert.match(source,/uiVersion\s*===\s*"v6"/);
  assert.ok(source.includes(id) || source.includes('ClockV6'));
  assert.ok((source.match(/return\s*(?:\(|<)/g)||[]).length>=2);
});
test('fixture workspace IDs and response metadata exist without a live seed',()=>{
  for(const f of fixtures) {
    assert.equal(f.task.ui_schema.schema_version,'2.0');
    assert.equal(f.task.ui_schema.workspaces[0].workspace_id,'main');
    assert.equal(f.task.ui_schema.workspaces[0].renderer_version,'1.0');
    assert.equal(f.task.ui_schema.workspaces[0].renderer,f.renderer);
    assert.ok(typeof f.expected==='string');
  }
});
test('canonical seven-node order, no phantom forty-two live abilities',()=>assert.deepEqual(Array.from(ability.ABILITY_NODES,n=>n.id),['app_rel','app_check','app_rd','app_transfer','app_model','app_cond','app_strat']));
test('missing ability displays unknown rather than a fabricated zero level',()=>{const p=ability.presentAbility();assert.equal(p.level,'待了解');assert.equal(p.count,null);assert.equal(p.stable,false);});
test('zero evidence does not claim stable mastery even when API trend says stable',()=>{const p=ability.presentAbility({level:2,evidence_count:0,trend:'stable'});assert.equal(p.status,'暂无记录');assert.equal(p.stable,false);assert.equal(p.level,'L2');});
test('raw API level and evidence count are preserved',()=>{const p=ability.presentAbility({level:3,evidence_count:17,trend:'up'});assert.equal(p.level,'L3');assert.equal(p.count,17);});
test('unknown trend fails soft without throwing or computing mastery',()=>assert.doesNotThrow(()=>ability.presentAbility({level:1,evidence_count:2,trend:'unexpected'})));
test('canonical ID has priority over explicitly mapped legacy aliases',()=>{const legacy={ability_id:'REL',level:1},current={ability_id:'app_rel',level:3};assert.equal(ability.findAbility(ability.ABILITY_NODES[0],[legacy,current]),current);});
test('names do not borrow another ability record',()=>assert.equal(ability.findAbility(ability.ABILITY_NODES[0],[{ability_id:'other',name:'数量关系'}]),undefined));
test('application defaults to V6 and real repository skin ID',()=>{assert.equal(config.childUiVersion,'v6');assert.equal(config.childMathSkin,'exploration-lab');});
test('launch defaults explicitly select HTTP; preview requires explicit mock',()=>{assert.equal(parseOptions([]).api,'http');assert.equal(parseOptions(['--api','mock']).api,'mock');});
test('launcher keeps skins in separate Next build directories',()=>{assert.notEqual(launchPlan(parseOptions(['--skin','healing']),{}).env.NEXT_DIST_DIR,launchPlan(parseOptions([]),{}).env.NEXT_DIST_DIR);});
test('build/start flags use identical selected UI/skin build directory',()=>{assert.equal(launchPlan(parseOptions(['--build']),{}).env.NEXT_DIST_DIR,launchPlan(parseOptions(['--start']),{}).env.NEXT_DIST_DIR);});
test('legacy rollback is explicit, not a hidden fallback',()=>assert.equal(launchPlan(parseOptions(['--legacy']),{}).env.NEXT_PUBLIC_CHILD_UI_VERSION,'legacy'));
test('launcher rejects invalid options and credential URLs',()=>{for(const args of [['--skin','math-lab'],['--port','3;exit'],['--api','silent'],['--build','--start'],['--api-base','https://user:pw@example.invalid']])assert.throws(()=>parseOptions(args));});
test('all V6 gallery routes remain gated in production',()=>{for(const route of ['dev/v6','dev/ui-kit','dev/v6-clock']){const source=read(`app/${route}/page.tsx`);assert.ok(source.includes('production'));assert.ok(source.includes('notFound'));}});
test('home/growth/result have real screen-level V6 branches',()=>{for(const name of ['MathHomeScreen','MathGrowthScreen','MathResultScreen']) assert.match(read(`src/screens/${name}.tsx`),/uiVersion\s*===\s*"v6"/);});
test('hint_usage is rendered as unique levels, never labeled as request count in V6',()=>{const source=read('src/components/ui-v6/ResultView.tsx');assert.ok(source.includes('Array.from(new Set(result.hint_usage))'));assert.ok(source.includes('提示记录'));assert.ok(!source.includes('["提示使用", String(result.hint_usage.length), "次"]'));});
test('decorative assets exist for both skins; no prototype judge is imported',()=>{for(const skin of ['exploration-lab','healing'])for(const kind of ['scenery','hero'])assert.ok(fs.existsSync(path.join(app,`public/child-ui-v6/${kind}-${skin}.svg`)));assert.ok(!read('src/components/ui-v6/PageFrame.tsx').includes('.html'));});
const summary={scope:'Migration inventory and executable presentation/launcher assertions; NOT full TypeScript/Next/DB validation',compiler:ts.version,pass:results.filter(x=>x.status==='PASS').length,fail:results.filter(x=>x.status==='FAIL').length,results};
console.log(JSON.stringify(summary,null,2));process.exitCode=summary.fail?1:0;
