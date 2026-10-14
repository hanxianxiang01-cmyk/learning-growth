/* Optional before/after comparison: BASELINE_REPO must point at the received,
 * unmodified repository. No HTTP or database required.
 */
const fs=require('fs'),path=require('path'),Module=require('module'),assert=require('assert/strict'),crypto=require('crypto');
const here=path.resolve(__dirname,'../..');const baseline=path.resolve(process.env.BASELINE_REPO||path.join(here,'..','baseline-repo'));
if(!fs.existsSync(path.join(baseline,'apps/child-web/src/lib/api/v2AttemptAdapter.ts')))throw Error('BASELINE_REPO missing unmodified source');
const ts=require(require.resolve('typescript',{paths:[here,'/opt/nvm/versions/node/v22.16.0/lib/node_modules']}));
function load(root){const cache=new Map();function run(filename){const full=path.resolve(filename);if(cache.has(full))return cache.get(full).exports;const source=fs.readFileSync(full,'utf8'),js=ts.transpileModule(source,{fileName:full,compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const m=new Module(full,module);m.filename=full;m.paths=Module._nodeModulePaths(path.dirname(full));cache.set(full,m);const original=m.require.bind(m);m.require=name=>name.startsWith('@/')?run(path.join(root,'apps/child-web',name.slice(2))+'.ts'):name.startsWith('.')&&fs.existsSync(path.resolve(path.dirname(full),name)+'.ts')?run(path.resolve(path.dirname(full),name)+'.ts'):original(name);m._compile(js,full);return m.exports;}
 return run(path.join(root,'apps/child-web/src/lib/api/v2AttemptAdapter.ts'));
}
function sample(){const tid='99999999-9999-4999-8999-999999999901';const ui_revision='cross-version-test';return {task:{task_instance_id:tid,ui_schema:{schema_version:'2.0',ui_revision,workspaces:[{workspace_id:'main',renderer:'number-input',renderer_version:'1.0',config:{expected_answer:63},initial_state:{},capabilities:['answer_input']}],response_contract:{response_type:'number_input'}}},request:{task_instance_id:tid,attempt_no:1,response:{schema_version:'1.0',answer:'99',v2_workspaces:[{workspace_id:'main',data:{state:{answer:99}}}],interaction_events:[]}}};}
const x=sample(),before=load(baseline).buildAttemptPayload(x.task,x.request),after=load(here).buildAttemptPayload(x.task,x.request);
assert.equal(before.submission_id,after.submission_id);assert.notDeepEqual(before.response,after.response);
const sum=v=>crypto.createHash('sha256').update(JSON.stringify(v)).digest('hex');
const result={same_submission_id:true,payload_identical:false,old_envelope_sha256:sum(before),new_envelope_sha256:sum(after),same_id_different_payload_yields_conflict_409_under_record_attempt:true,impact:'In-flight legacy retry may conflict after deploying SAFE-01 sanitizer; coordinate rollout/drain or immutable submit snapshot',real_db_tested:false};
if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
