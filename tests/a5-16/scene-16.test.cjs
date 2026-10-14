'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');
const compiled=path.resolve(__dirname,'../../dist/isolated/apps/child-web/src/features/task-renderer/interaction/kernel');
const {buildA5Scene,a5IntentForDrop,a5ExplicitSelection}=require(path.join(compiled,'naturalScene.js'));
const {resolveNaturalIntent,A5_RENDERER_IDS}=require(path.join(compiled,'naturalIntent.js'));
const context={taskInstanceId:'a',activeTaskInstanceId:'a',uiRevision:4,activeUiRevision:4,disabled:false,modality:'pointer'};
const all=require('./fixtures.cjs').samples;
test('all sixteen exact-scene IDs, no A4 or protocol-only leakage',()=>{
 assert.deepEqual(all.map(x=>x[0].rendererId).sort(),[...A5_RENDERER_IDS].sort());
});
for(const [scene,source,target,action] of all){
 test(`${scene.rendererId}: DOM source/target resolves existing domain op`,()=>{
  const layout=buildA5Scene(scene);
  assert.equal(layout.rendererId,scene.rendererId);
  assert.ok(layout.title && layout.instructions);
  if(!source){assert.equal(layout.kind,'number-input');return;}
  assert.ok(layout.sources.some(s=>s.id===source),source);
  assert.ok(layout.targets.some(t=>t.id===target),target);
  const intent=a5IntentForDrop(scene,source,target,scene.rendererId==='estimation-canvas'?0.65:undefined);
  const result=resolveNaturalIntent(intent,context);
  assert.equal(result.status,'ready',JSON.stringify(result));
  assert.equal(result.command.operation,action);
  assert.equal(result.command.evidenceOwner,'existing-domain');
 });
}
for(const [scene,source,target] of all.filter(x=>x[1])){
 test(`${scene.rendererId}: forged DOM identity/outside drop blocked`,()=>{
  assert.equal(a5IntentForDrop(scene,`FORGED:${source}`,target),null);
  assert.equal(a5IntentForDrop(scene,source,'FORGED:target'),null);
  assert.equal(a5IntentForDrop(scene,source,null),null);
 });
}
test('explicit selections are actual, whitelist-bound domain actions',()=>{
 const expected={'formula-board':'applyActivate','place-value':'applyPick','sorting-board':'applySelectCard','shape-gallery':'applySelect'};
 for(const [scene] of all){
  const buttons=buildA5Scene(scene).explicitSelections;
  for(const btn of buttons){
   const cmd=a5ExplicitSelection(scene,btn.id);
   assert.equal(cmd.operation,expected[scene.rendererId]);
   assert.equal(cmd.evidenceOwner,'existing-domain');
  }
  assert.equal(a5ExplicitSelection(scene,'select:FORGED'),null);
 }
});
test('state mutation during gesture blocks stale selected item / illegal length',()=>{
 const [place]=all.find(x=>x[0].rendererId==='place-value');
 const changed={...place,pickedPoolIndex:null};
 assert.equal(resolveNaturalIntent(a5IntentForDrop(changed,'pool:0','slot:0'),context).status,'blocked');
 const [sort]=all.find(x=>x[0].rendererId==='sorting-board');
 assert.equal(resolveNaturalIntent(a5IntentForDrop({...sort,selectedCardId:null},'card:0','target:1'),context).status,'blocked');
 const [gallery]=all.find(x=>x[0].rendererId==='shape-gallery');
 assert.equal(resolveNaturalIntent(a5IntentForDrop({...gallery,selectedShapeId:null},'shape:0','home'),context).status,'blocked');
});
test('spatial constraints reject invalid geometry without hitting Judge',()=>{
 const [direction]=all.find(x=>x[0].rendererId==='direction-grid');
 assert.equal(resolveNaturalIntent(a5IntentForDrop(direction,'cursor','cell:2:2'),context).status,'cancelled');
 const [bar]=all.find(x=>x[0].rendererId==='bar-model');
 assert.equal(resolveNaturalIntent(a5IntentForDrop({...bar,blocks:[6]},'bar:0','bar:0:1'),context).status,'blocked');
 const [pattern]=all.find(x=>x[0].rendererId==='pattern-board');
 assert.equal(resolveNaturalIntent(a5IntentForDrop({...pattern,blanks:[{locked:true,label:'第一个空格'}]},'token:1','blank:0'),context).status,'cancelled');
 const [line]=all.find(x=>x[0].rendererId==='number-line');
 assert.equal(resolveNaturalIntent(a5IntentForDrop(line,'cursor','tick:4'),context).status,'cancelled');
});
test('layout does not render unbounded 2D scene nodes',()=>{
 assert.equal(buildA5Scene({rendererId:'direction-grid',rows:2000,cols:2000,current:{r:0,c:0}}).targets.length,0);
 assert.equal(buildA5Scene({rendererId:'shape-canvas',minX:0,maxX:1000,minY:0,maxY:1000}).targets.length,0);
 assert.equal(buildA5Scene({rendererId:'number-line',currentTick:0,minTick:0,maxTick:2000}).targets.length,0);
});
