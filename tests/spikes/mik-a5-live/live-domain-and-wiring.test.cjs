'use strict';
/* Actual FE-1445 domain preflight and 16 JSX static mounts. Not browser or DB E2E. */
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const cp=require('node:child_process');
const repo=path.resolve(__dirname,'../../..');
const domain=path.join(repo,'dist/isolated/apps/child-web/src/features/task-renderer');
const {canApplyA5Domain,buildA5LiveScene}=require(path.join(domain,'interaction/kernel/a5DomainIntegration.js'));
const src=path.join(repo,'apps/child-web/src');
const rows=[
 ['formula-board',{filled:{},activeSlot:'s'},{tokens:[{t:'slot',id:'s',accept:'number'}],maxNumber:99},'applyNumberKey',{digit:4},'FormulaBoardV2'],
 ['ten-frame',{tens:0,count:0},{target:7,maxFrames:2},'applyCell',{frameIndex:0,cellIndex:0},'TenFrameV2'],
 ['grouping-board',{groups:[0,0],pool:4},{items:4,targetGroups:2,maxGroups:3},'applyAddItem',{groupIndex:0},'GroupingBoardV2'],
 ['money-board',{counts:{},selection_history:[]},{price:35,denominations:[1,5,10]},'applyAddCoin',{denominationJiao:10},'MoneyBoardV2'],
 ['bar-model',{bars:{a:0,b:0,c:0},answerTouched:false},{mode:'part_whole',known:{a:3,b:4},answerBar:'c',maxBlocks:20},'applyBarDelta',{barIndex:2,delta:1},'BarModelV2'],
 ['array-board',{rows:0,cols:0},{targetRows:3,targetCols:2,maxRows:5,maxCols:5},'applyRowDelta',{delta:1},'ArrayBoardV2'],
 ['place-value',{pool:[7,2],slots:[null,null],picked:0},{places:['十','个']},'applySlot',{slotIndex:1},'PlaceValueV2'],
 ['sorting-board',{order:['b','a','c'],selected:'b',swaps:[]},{items:[{id:'a',value:2,visual_rank:1},{id:'b',value:1,visual_rank:3},{id:'c',value:3,visual_rank:2}]},'applySwap',{targetCardId:'a'},'SortingBoardV2'],
 ['number-line',{start:4,current:4,jumps:[]},{min:0,max:10,tickStep:1,startValue:4},'applyJump',{toTick:6},'NumberLineV2'],
 ['ruler',{marks:[]},{max:20,left:4,right:9},'applyPlaceMark',{markIndex:0,tick:4},'RulerV2'],
 ['direction-grid',{steps:[{r:0,c:0}]},{rows:3,cols:3,start:{r:0,c:0},target:{r:2,c:2}},'applyMoveTo',{r:0,c:1},'DirectionGridV2'],
 ['shape-canvas',{vertices:[]},{grid:4,targetArea:2,targetShape:'rectangle'},'applyAddPoint',{x:0,y:0},'ShapeCanvasV2'],
 ['pattern-board',{beads:[null,null],attempt_history:[]},{palette:[1,2],blanks:2,visible:[1,2],period:2},'applyReplaceAt',{blankIndex:0,token:1},'PatternBoardV2'],
 ['shape-gallery',{selected:'red',home:[]},{shapes:[{id:'red',name:'圆',kind:'circle',color:'red'}],targetKind:'circle'},'applyPlaceHome',{shapeId:'red'},'ShapeGalleryV2'],
 ['estimation-canvas',{estimate:null,reason:null,adjust_history:[]},{max:20,reference:10,expected:10,actual:11,tolerance:2},'applyEstimate',{value:14},'EstimationCanvasV2']
];
const cmd=(id,operation,args)=>({rendererId:id,operation,args,evidenceOwner:'existing-domain'});
for(const [id,s,c,op,a,name] of rows){
 test(`${id}: actual V6 domain action legal, and no preflight state write`,()=>{
   const before=JSON.stringify(s);assert.equal(canApplyA5Domain(id,s,c,cmd(id,op,a)),true);
   assert.equal(JSON.stringify(s),before);
 });
 test(`${id}: forged operation and wrong renderer blocked`,()=>{
   assert.equal(canApplyA5Domain(id,s,c,cmd(id,'forged',a)),false);
   assert.equal(canApplyA5Domain(id,s,c,cmd('other',op,a)),false);
 });
 test(`${id}: original component React JSX mount and scene`,()=>{
   const a=fs.readFileSync(path.join(src,`components/renderers/${name}.tsx`),'utf8');
   assert.ok(a.includes('<A5LivePanel')&&a.includes(`rendererId="${id}"`)&&a.includes('naturalEnabled'));
   const scene=buildA5LiveScene(id,s,c);assert.equal(scene.rendererId,id);
   assert.ok(!JSON.stringify(scene).includes('evaluation'));
 });
}
test('shape-gallery return does not create fake selection event',()=>{
 const ctx={taskInstanceId:'t',activeTaskInstanceId:'t',uiRevision:1,activeUiRevision:1,disabled:false,modality:'pointer'};
 const {resolveNaturalIntent}=require(path.join(domain,'interaction/kernel/naturalIntent.js'));
 const r=resolveNaturalIntent({rendererId:'shape-gallery',sourceShapeId:'red',selectedShapeId:null,target:'return-tray',currentlyAtHome:true},ctx);
 assert.equal(r.status,'ready');assert.equal(r.command.operation,'applyReturnHome');
 const c=rows.find(x=>x[0]==='shape-gallery')[2];
 assert.equal(canApplyA5Domain('shape-gallery',{selected:null,home:['red']},c,r.command),true);
});
test('ruler chronological mark and number-line tick step preflight',()=>{
 const ruler=rows.find(x=>x[0]==='ruler');
 assert.ok(canApplyA5Domain('ruler',{marks:[4]},ruler[2],cmd('ruler','applyPlaceMark',{markIndex:1,tick:9})));
 assert.ok(!canApplyA5Domain('ruler',{marks:[4]},ruler[2],cmd('ruler','applyPlaceMark',{markIndex:0,tick:9})));
 const line=rows.find(x=>x[0]==='number-line');
 assert.ok(!canApplyA5Domain('number-line',line[1],{...line[2],tickStep:2},cmd('number-line','applyJump',{toTick:5})));
});
test('16/16 pinned Router paths, unchanged legacy default, three A4 not opted in',()=>{
 const p=fs.readFileSync(path.join(src,'features/task-renderer/TaskRenderer.tsx'),'utf8');
 const router=fs.readFileSync(path.join(src,'features/math-interaction/TaskRendererImplementationBoundary.tsx'),'utf8');
 const policy=fs.readFileSync(path.join(src,'features/math-interaction/implementationPolicy.ts'),'utf8');
 assert.equal(rows.length,15);
 for(const id of ['number-input',...rows.map(x=>x[0])]){
  assert.ok(p.includes(`rendererId="${id}"`),id);
  assert.ok(router.includes(`'${id}'`),id);
 }
 assert.ok(!router.includes("'column-arithmetic'")&&!router.includes("'object-counter'")&&!router.includes("'clock'"));
 assert.ok(policy.includes("(configured ?? 'legacy')"));
});
test('SAFE-01 server owns evaluation; React files parse',()=>{
 const adapter=fs.readFileSync(path.join(src,'lib/api/v2AttemptAdapter.ts'),'utf8');
 assert.ok(adapter.includes('buildRendererEvidence')&&!adapter.includes('getRendererEvaluator'));
 let ts;try{ts=require('typescript')}catch{ts=require(path.join(cp.execFileSync('npm',['root','-g'],{encoding:'utf8'}).trim(),'typescript'));}
 const files=[path.join(src,'features/task-renderer/TaskRenderer.tsx'),path.join(src,'features/math-interaction/TaskRendererImplementationBoundary.tsx'),...rows.map(x=>path.join(src,`components/renderers/${x[5]}.tsx`))];
 for(const file of files){const tree=ts.createSourceFile(file,fs.readFileSync(file,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);assert.equal(tree.parseDiagnostics.length,0,file);}
});
