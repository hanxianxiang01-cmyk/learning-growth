/**
 * M1/M2 executable unit checks. Reads the actual production TS modules.
 * No React / browser / API mocking, no network calls. NOT a Next build or E2E test.
 * Normal: node scripts/check-v6-migration.mjs (after npm ci)
 * Dependency-limited inspection: V6_TYPESCRIPT_PATH=/absolute/path/to/typescript
 * reports that compiler's actual version; this is not the lockfile toolchain check.
 */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
let ts;
try { ts = require(process.env.V6_TYPESCRIPT_PATH || 'typescript'); }
catch { console.error('BLOCKED: TypeScript dependency unavailable. Run npm ci.'); process.exit(2); }
const options = { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, esModuleInterop: true, jsx: ts.JsxEmit.ReactJSX };
const cache = new Map();
const context = vm.createContext({ console, structuredClone, crypto: webcrypto, Date, Math, JSON, Object, Number, String, Array, Set, Map, window: {}, sessionStorage: { setItem(){ throw new Error('storage blocked'); }, getItem(){ throw new Error('storage blocked'); } } });
function load(file) {
  if (!path.extname(file)) file += '.ts';
  if(cache.has(file))return cache.get(file).exports;
  const module={exports:{}};cache.set(file,module);
  const output=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:options,fileName:file});
  const resolve = spec => {
    const resolved = spec.startsWith('@/') ? path.join(root,spec.slice(2)) : spec.startsWith('.') ? path.resolve(path.dirname(file),spec) : null;
    if(!resolved)throw new Error('Unexpected external dependency: '+spec);
    return load(resolved);
  };
  new vm.Script(`(function(require,module,exports){${output.outputText}\n})`,{filename:file}).runInContext(context)(resolve,module,module.exports);
  return module.exports;
}
const mod = name => load(path.join(root,'src',name));
const plain = obj => JSON.parse(JSON.stringify(obj));
const results=[];
function test(name,fn){try{fn();results.push({name,status:'PASS'});}catch(e){results.push({name,status:'FAIL',detail:e.stack});}}
const clock=mod('features/task-renderer/clockV2'),ui=mod('features/ui-v6/clockInput'),runtime=mod('features/task-renderer/rendererRuntime'),machine=mod('features/learning/machine'),response=mod('features/task-renderer/taskResponse'),adapter=mod('lib/api/v2AttemptAdapter'),theme=mod('theme/uiVersion'),tokens=mod('theme/v6Tokens'),store=mod('lib/runtime/sessionStore');
const config=clock.parseClockConfig({start:[3,0],target:[6,0]});
const initial=clock.initialClockV2State(config);
const changed=(h,m)=>clock.applySetMinute(clock.applySetHour(initial,h).state,m).state;
const task={task_instance_id:'10000000-0000-0000-0000-000000000099',ability_id:'app_cond',difficulty:1,strategy_policy:{},ui_schema:{schema_version:'2.0',ui_revision:'clock-unit-1',prompt:{text:'拨到6点整'},workspaces:[{workspace_id:'clock_main',renderer:'clock',renderer_version:'2.0',mode:'time_setting',config:{start:[3,0],target:[6,0]},initial_state:{h:3,m:0,adjust_history:[]},capabilities:['set_time','answer_input','undo','reset']}],response_contract:{response_type:'clock',evidence_targets:['h','m','adjust_history','structure']}}};
const toResponse = state => ({schema_version:'1.0',answer:clock.clockAnswer(state)===null?'':String(clock.clockAnswer(state)),v2_workspaces:[{workspace_id:'clock_main',data:clock.serializeClockV2(state,config)}],v2_response_type:'clock',v2_ui_revision:'clock-unit-1',interaction_events:[]});
const wrong=toResponse(changed(6,30));

test('repository gold config accepted',()=>assert.deepEqual(plain(config),{start:{h:3,m:0},target:{h:6,m:0}}));
test('15 minute config rejected',()=>assert.equal(clock.parseClockConfig({start:[3,15],target:[6,0]}),null));
test('object-shaped time remains rejected',()=>assert.equal(clock.parseClockConfig({start:{h:3,m:0},target:{h:6,m:0}}),null));
test('swap self-loop still rejected',()=>assert.equal(clock.parseClockConfig({start:[3,0],target:[12,0]}),null));
test('initial board has no fabricated answer or history',()=>{assert.equal(clock.clockAnswer(initial),null);assert.equal(runtime.createRendererWorkspaceState(initial).history.length,0);});
test('wrong hour is legal and not blocked by readiness',()=>{const r=toResponse(changed(5,0));assert.equal(r.answer,'300');assert.equal(response.isTaskResponseReady(r,task),true);});
test('wrong minute is legal and remains submitted scalar 390',()=>{assert.equal(wrong.answer,'390');assert.equal(response.isTaskResponseReady(wrong,task),true);assert.equal(wrong.v2_workspaces[0].data.structure.error,'wrong_time');});
test('correct result is canonical scalar 360',()=>{const r=toResponse(changed(6,0));assert.equal(r.answer,'360');assert.equal(r.v2_workspaces[0].data.structure.status,'PASS');});
test('hand-swap diagnosis unchanged',()=>assert.equal(clock.serializeClockV2(changed(12,0),config).structure.error,'hand_swap'));
test('minute mutation rejects five-minute input',()=>assert.equal(clock.applySetMinute(initial,5).ok,false));
test('hour mutation rejects out-of-range values',()=>{assert.equal(clock.applySetHour(initial,0).ok,false);assert.equal(clock.applySetHour(initial,13).ok,false);});
test('same-value action adds no history',()=>assert.equal(clock.applySetHour(initial,3).unchanged,true));
test('pointer jitter below 7px stays a selection',()=>assert.equal(ui.clockDragStarted(1,1,5,5),false));
test('pointer drag starts at threshold',()=>assert.equal(ui.clockDragStarted(0,0,7,0),true));
test('center dead-zone produces no update',()=>assert.equal(ui.clockValueFromPoint('hour',180,180,0),null));
test('invalid pointer values cannot enter state',()=>assert.equal(ui.clockValueFromPoint('hour',NaN,0,0),null));
test('hour geometry accounts for half-hour offset',()=>{const a=195*Math.PI/180;assert.equal(ui.clockValueFromPoint('hour',180+54*Math.sin(a),180-54*Math.cos(a),30),6);});
test('minute geometry only emits 0 or 30 for 360 angles',()=>{for(let d=0;d<360;d++){const a=d*Math.PI/180;assert.ok([0,30].includes(ui.clockValueFromPoint('minute',180+86*Math.sin(a),180-86*Math.cos(a),0)));}});
test('keyboard bounds do not wrap through illegal times',()=>{assert.equal(ui.clockKeyValue('hour',1,'ArrowLeft'),1);assert.equal(ui.clockKeyValue('hour',12,'ArrowRight'),12);});
test('keyboard Home and End semantics',()=>{assert.equal(ui.clockKeyValue('hour',5,'Home'),1);assert.equal(ui.clockKeyValue('hour',5,'End'),12);assert.equal(ui.clockKeyValue('minute',30,'Home'),0);assert.equal(ui.clockKeyValue('minute',0,'End'),30);});
test('unhandled keys cannot change answer',()=>assert.equal(ui.clockKeyValue('hour',3,'Tab'),null));
test('undo reverses one commit rather than resets all',()=>{let r=runtime.createRendererWorkspaceState(initial);r=runtime.rendererWorkspaceReducer(r,{type:'SET_STATE',state:clock.applySetHour(r.present,5).state});r=runtime.rendererWorkspaceReducer(r,{type:'SET_STATE',state:clock.applySetMinute(r.present,30).state});r=runtime.rendererWorkspaceReducer(r,{type:'UNDO'});assert.equal(r.present.h,5);assert.equal(r.present.m,0);assert.equal(r.history.length,1);});
test('reset restores original state and clears history',()=>{let r=runtime.createRendererWorkspaceState(initial);r=runtime.rendererWorkspaceReducer(r,{type:'SET_STATE',state:changed(6,30)});r=runtime.rendererWorkspaceReducer(r,{type:'RESET'});assert.deepEqual(plain(r.present),plain(initial));assert.equal(r.history.length,0);});
test('empty V2 response not ready',()=>assert.equal(response.isTaskResponseReady(response.createEmptyTaskResponse(),task),false));
test('answer without V2 workspace not ready',()=>assert.equal(response.isTaskResponseReady({schema_version:'1.0',answer:'390'},task),false));
test('RETRY preserves answer workspace and events',()=>{const before={...machine.initialLearningState,task,response:wrong,status:'retry',attemptNo:2,error:'old'};const after=machine.learningReducer(before,{type:'RETRY'});assert.equal(after.status,'answering');assert.deepEqual(plain(after.response),plain(wrong));assert.equal(after.attemptNo,2);assert.equal(after.error,null);});
test('server wrong result increments attempt once and enables hints',()=>{const result={attempt_id:'attempt-1',correct:false,next_action:{type:'HINT',hint_level:1}};const after=machine.learningReducer({...machine.initialLearningState,task,response:wrong,status:'submitting'},{type:'ATTEMPT_RESULT',result});assert.equal(after.attemptNo,2);assert.equal(after.status,'hint_available');});
test('transport error does not consume next attempt number',()=>{const after=machine.learningReducer({...machine.initialLearningState,attemptNo:2},{type:'ERROR',message:'network'});assert.equal(after.attemptNo,2);});
test('hint uses server text and preserves response',()=>{const after=machine.learningReducer({...machine.initialLearningState,response:wrong},{type:'HINT_LOADED',hint:{hint_level:1,text:'server hint'}});assert.equal(after.hint.text,'server hint');assert.equal(after.response.answer,'390');});
test('new task clears prior attempt and hint state',()=>{const after=machine.learningReducer({...machine.initialLearningState,response:wrong,attemptNo:4},{type:'TASK_LOADED',task});assert.equal(after.response.answer,'');assert.equal(after.attemptNo,1);});
test('V2 payload uses original envelope and UUID',()=>{const p=adapter.buildAttemptPayload(task,{task_instance_id:task.task_instance_id,attempt_no:1,response:wrong});assert.equal(p.response.schema_version,'2.0');assert.equal(p.response.type,'clock');assert.equal(p.response.answer.value,390);assert.equal(p.response.workspaces[0].data.structure.error,'wrong_time');assert.match(p.submission_id,/^[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}$/);});
test('same submission derives same id; retry attempt gets a new id',()=>{const id1=adapter.stableSubmissionId(task.task_instance_id,1,'r');assert.equal(id1,adapter.stableSubmissionId(task.task_instance_id,1,'r'));assert.notEqual(id1,adapter.stableSubmissionId(task.task_instance_id,2,'r'));});
test('stable request retransmission keeps answer envelope unchanged',()=>{const req={task_instance_id:task.task_instance_id,attempt_no:1,response:wrong};assert.deepEqual(plain(adapter.buildAttemptPayload(task,req)),plain(adapter.buildAttemptPayload(task,structuredClone(req))));});
test('event vocabulary and workspace bindings preserved',()=>{const e=runtime.buildRendererEvent('CLOCK_MINUTE_SET',{task_instance_id:task.task_instance_id,workspace_id:'clock_main',renderer_id:'clock',capability_id:'set_time',payload:{from:0,to:30}});assert.equal(e.event_type,'CLOCK_MINUTE_SET');assert.equal(e.target_id,'clock_main');assert.equal(e.capability_id,'set_time');});
test('flag defaults to legacy and rejects unknown values',()=>{assert.equal(theme.resolveChildUiVersion(), 'legacy');assert.equal(theme.resolveChildUiVersion('latest'),'legacy');assert.equal(theme.resolveChildUiVersion('v6'),'v6');});
test('both repository skin IDs have V6 tokens; primary is shared',()=>{assert.ok(tokens.v6Tokens['exploration-lab']);assert.ok(tokens.v6Tokens.healing);assert.equal(tokens.v6Actions.primary,'#0a6972');});
test('blocked browser cache cannot turn acknowledged response into error',()=>{assert.doesNotThrow(()=>store.saveSessionSnapshot({sessionId:'cache-unit'}));assert.equal(store.loadSessionSnapshot('cache-unit'),null);});

// Independent TS semantic check on pure modules only. NOT React/Next app typecheck.
const roots=[...cache.keys()];
const program=ts.createProgram(roots,{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,moduleResolution:ts.ModuleResolutionKind.Bundler,strict:true,noEmit:true,skipLibCheck:true,types:[],lib:['lib.es2022.d.ts','lib.dom.d.ts'],baseUrl:root,paths:{'@/*':['./*']}});
const diagnostics=ts.getPreEmitDiagnostics(program);
test('pure-module TypeScript semantic check (explicit limited scope)',()=>assert.equal(diagnostics.length,0,ts.formatDiagnosticsWithColorAndContext(diagnostics,{getCanonicalFileName:f=>f,getCurrentDirectory:()=>root,getNewLine:()=> '\n'})));
const summary={scope:'pure module unit tests + pure TS semantic check; excludes React/hooks/browser/API/DB',compiler:ts.version,compiler_source:process.env.V6_TYPESCRIPT_PATH?'external inspection compiler':'installed dependency',at:new Date().toISOString(),pass:results.filter(x=>x.status==='PASS').length,fail:results.filter(x=>x.status==='FAIL').length,results};
console.log(JSON.stringify(summary,null,2));process.exitCode=summary.fail?1:0;
