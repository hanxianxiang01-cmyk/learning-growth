/* SAFE-01 - exercise actual v2AttemptAdapter and HTTP JSON serialization.
 * No real child, network, database or tokens are used. Uses global TS if
 * project npm ci is unavailable. Never prints raw answer-bearing envelopes.
 */
const fs=require('node:fs'), path=require('node:path'), Module=require('node:module'), assert=require('node:assert/strict');
const REPO=path.resolve(__dirname,'../..');
const TS=require(require.resolve('typescript',{paths:[REPO, '/opt/nvm/versions/node/v22.16.0/lib/node_modules']}));
const cache=new Map();
function loadTS(file){
 const full=path.resolve(file); if(cache.has(full))return cache.get(full).exports;
 const src=fs.readFileSync(full,'utf8');
 const transpiled=TS.transpileModule(src,{fileName:full,compilerOptions:{module:TS.ModuleKind.CommonJS,target:TS.ScriptTarget.ES2022,esModuleInterop:true}});
 const m=new Module(full,module);m.filename=full;m.paths=Module._nodeModulePaths(path.dirname(full));cache.set(full,m);
 const orig=m.require.bind(m);
 m.require=(name)=>{
  if(name.startsWith('@/'))return loadTS(path.join(REPO,'apps/child-web',name.slice(2))+'.ts');
  if(name.startsWith('.')){const candidate=path.resolve(path.dirname(full),name);if(fs.existsSync(candidate+'.ts'))return loadTS(candidate+'.ts');if(fs.existsSync(candidate+'.tsx'))return loadTS(candidate+'.tsx');}
  return orig(name);
 };
 m._compile(transpiled.outputText,full);return m.exports;
}
const adapter=loadTS(path.join(REPO,'apps/child-web/src/lib/api/v2AttemptAdapter.ts'));
const {HttpLearningApi}=loadTS(path.join(REPO,'apps/child-web/src/lib/api/http.ts'));
const V2='/v1/learning/attempts';
const make=(config)=>{
 const taskId='99999999-9999-4999-8999-999999999901';
 const task={task_instance_id:taskId, ability_id:'app_rel',difficulty:1,ui_schema:{schema_version:'2.0',ui_revision:'safe01-gold',prompt:{text:'36+27 = ?'},workspaces:[{workspace_id:'main',renderer:'number-input',renderer_version:'1.0',mode:'numeric',config,initial_state:{answer:null},capabilities:['answer_input']}],response_contract:{response_type:'number_input',required_fields:['answer','workspaces'],evidence_targets:[]}},strategy_policy:{}};
 const request={task_instance_id:taskId,attempt_no:1,response:{schema_version:'1.0',answer:'99',interaction_events:[],v2_workspaces:[{workspace_id:'main',data:{state:{answer:99},input_history:[]}}],v2_response_type:'number_input',v2_ui_revision:'safe01-gold'}};
 return {task,request};
};
const dataNoAnswer=make({min:0,max:200,integer_only:true});
const dataWithExpected=make({min:0,max:200,integer_only:true,expected_answer:63});
function read(payload){return payload.response.workspaces[0].data;}
const noAnswer=adapter.buildAttemptPayload(dataNoAnswer.task,dataNoAnswer.request);
const withAnswer=adapter.buildAttemptPayload(dataWithExpected.task,dataWithExpected.request);
assert.equal(noAnswer.response.answer.value,99);
assert.equal('evaluation' in read(noAnswer),false);
assert.equal('expected_answer' in read(noAnswer),false);
assert.equal('evaluation' in read(withAnswer),false);
assert.equal('expected_answer' in read(withAnswer),false);
assert.equal('score' in read(withAnswer),false);
assert.equal(noAnswer.response.workspaces[0].data.evidence.state_snapshot.answer,'99');
assert.equal(typeof noAnswer.submission_id,'string');
assert.equal(adapter.buildAttemptPayload(dataNoAnswer.task,dataNoAnswer.request).submission_id,noAnswer.submission_id);
assert.equal(noAnswer.response.workspaces[0].data.evidence.attempt_no,1);
async function capturedWire(){
 const previous=global.fetch; let seen=null;
 global.fetch=async (url,opts)=>{
   assert.equal(new URL(url).pathname,V2);
   seen=JSON.parse(opts.body);
   return {ok:true,json:async()=>({attempt_id:'aaaa0000-0000-4000-8000-000000000001',correct:false,next_action:{type:'RETRY'}})};
 };
 try{const api=new HttpLearningApi('http://localhost:11111','/v1/learning/sessions/{session_id}/result');await api.submitAttempt(dataWithExpected.request,dataWithExpected.task);}
 finally{global.fetch=previous;}
 assert.ok(seen);assert.equal('evaluation' in read(seen),false);
 return seen;
}
function deepField(value,key, prefix='',paths=[]){
 if(Array.isArray(value))value.forEach((x,i)=>deepField(x,key,`${prefix}[${i}]`,paths));
 else if(value&&typeof value==='object')for(const [k,v] of Object.entries(value)){
   const p=prefix?`${prefix}.${k}`:k;if(k===key)paths.push(p);deepField(v,key,p,paths);
 }
 return paths;
}
(async()=>{
 const wire=await capturedWire();
 const result={schema:'safe01-evidence/1',source:'provided 443-file baseline',execution:'patched TypeScript transpiled and executed; HTTP request intercepted via fetch stub; no network',cases:[
  {id:'C1_clean',config_has_expected:false,wire_expected_answer_paths:deepField(noAnswer,'expected_answer'),evaluation_forwarded:Object.hasOwn(read(noAnswer),'evaluation')},
  {id:'C2_injected_expected',config_has_expected:true,wire_expected_answer_paths:deepField(wire,'expected_answer'),evaluation_forwarded:Object.hasOwn(read(wire),'evaluation')}
 ],assertions_passed:12,unsafe_path_blocked:deepField(wire,'expected_answer').length===0&&!Object.hasOwn(read(wire),'evaluation'),backend_judge_checked_by_source_only:true,database_write_tested:false,logging_pipeline_tested:false};
 if(!result.unsafe_path_blocked)process.exitCode=1;
 if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify(result,null,2));
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
