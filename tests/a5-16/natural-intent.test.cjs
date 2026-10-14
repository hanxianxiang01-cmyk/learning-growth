'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const {
  A5_RENDERER_IDS, A5_DOMAIN_ACTIONS, resolveNaturalIntent
} = require('../../dist/isolated/apps/child-web/src/features/task-renderer/interaction/kernel/naturalIntent.js');

const base = Object.freeze({
  taskInstanceId: 'task-a', activeTaskInstanceId: 'task-a',
  uiRevision: 14, activeUiRevision: 14, disabled: false,
  modality: 'pointer'
});
const keyboard = {...base, modality: 'keyboard'};
const ready = (intent, ctx=base, operation) => {
  const r=resolveNaturalIntent(intent,ctx);
  assert.equal(r.status,'ready',`${intent.rendererId}: ${JSON.stringify(r)}`);
  assert.equal(r.command.rendererId,intent.rendererId);
  assert.equal(r.command.evidenceOwner,'existing-domain');
  assert.ok(A5_DOMAIN_ACTIONS[intent.rendererId].includes(r.command.operation));
  if (operation) assert.equal(r.command.operation,operation);
  return r.command;
};
const notReady = (intent, ctx=base, reason=null) => {
  const r=resolveNaturalIntent(intent,ctx);
  assert.notEqual(r.status,'ready',JSON.stringify(r));
  if(reason) assert.equal(r.reason,reason);
  return r;
};

const cases = [
  [{rendererId:'number-input',text:'74',integerOnly:true,maxLength:4},keyboard,'text change'],
  [{rendererId:'formula-board',slotId:'s',activeSlotId:'s',token:{kind:'number',digit:4}},keyboard,'applyNumberKey'],
  [{rendererId:'ten-frame',from:'bank',to:'cell',frameIndex:0,cellIndex:9,cellOccupied:false},base,'applyCell'],
  [{rendererId:'grouping-board',from:'pool',to:'group',groupIndex:1,groupCount:2,sourceHasItem:true},base,'applyAddItem'],
  [{rendererId:'money-board',from:'coin-bank',to:'wallet',denominationJiao:10,allowedDenominationsJiao:[1,5,10,50],walletCount:0},base,'applyAddCoin'],
  [{rendererId:'bar-model',barIndex:0,delta:1,existingBlocks:2,maxBlocks:6},base,'applyBarDelta'],
  [{rendererId:'array-board',edge:'row',delta:1,current:2,limit:4},base,'applyRowDelta'],
  [{rendererId:'place-value',sourcePoolIndex:1,pickedPoolIndex:1,targetSlotIndex:0,slotCount:2},base,'applySlot'],
  [{rendererId:'sorting-board',sourceCardId:'a',selectedCardId:'a',targetCardId:'b',cardIds:['a','b','c']},base,'applySwap'],
  [{rendererId:'number-line',currentTick:4,targetTick:8,minTick:0,maxTick:10},base,'applyJump'],
  [{rendererId:'ruler',mark:1,targetTick:8,tickMin:0,tickMax:20,allowedTickStep:1},base,'applyPlaceMark'],
  [{rendererId:'direction-grid',current:{r:1,c:1},target:{r:1,c:2},rows:3,cols:3},base,'applyMoveTo'],
  [{rendererId:'shape-canvas',point:{x:2,y:3},gridMinX:0,gridMaxX:6,gridMinY:0,gridMaxY:8},base,'applyAddPoint'],
  [{rendererId:'pattern-board',targetIndex:1,blankCount:2,token:2,palette:[1,2],locked:false},base,'applyReplaceAt'],
  [{rendererId:'shape-gallery',sourceShapeId:'circle-a',selectedShapeId:'circle-a',target:'home',currentlyAtHome:false},base,'applyPlaceHome'],
  [{rendererId:'estimation-canvas',estimate:13,min:0,max:20,step:1},base,'applyEstimate']
];

test('exactly sixteen A5-only renderers (not the three A4 pilots)',()=>{
  assert.equal(A5_RENDERER_IDS.length,16);
  assert.deepEqual(new Set(A5_RENDERER_IDS),new Set(Object.keys(A5_DOMAIN_ACTIONS)));
  for(const name of ['object-counter','clock','column-arithmetic'])assert.ok(!A5_RENDERER_IDS.includes(name));
});
for (const [intent,ctx,op] of cases) {
  test(`${intent.rendererId} => one catalogued domain command`, () => {
    const cmd=ready(intent,ctx,op);
    assert.equal(typeof cmd.args,'object');
    assert.equal(cmd.args === null,false);
  });
}

test('stale task/revision/disabled cannot generate an approved command',()=>{
  for (const [intent,ctx] of cases) {
    notReady(intent,{...ctx,disabled:true},'disabled');
    notReady(intent,{...ctx,activeTaskInstanceId:'other'},'task-instance-changed');
    notReady(intent,{...ctx,activeUiRevision:15},'ui-revision-changed');
    notReady(null,ctx,'outside-valid-target');
  }
});

test('number-input supports intermediate incomplete edits but not invalid letters or pointer drag',()=>{
  const template=cases[0][0];
  ready({...template,text:'-'},keyboard);
  ready({...template,text:''},keyboard);
  notReady({...template,text:'abc'},keyboard,'invalid-integer-text');
  notReady({...template,text:'12345'},keyboard,'invalid-length');
  notReady(template,base,'number-input-has-no-drag-semantic');
});

test('formula numeric/operator types and active slot; zero fake selection',()=>{
  const template=cases[1][0];
  ready({...template,token:{kind:'operator',symbol:'+'}},keyboard,'applyOperatorKey');
  notReady({...template,activeSlotId:null},keyboard,'slot-must-be-explicitly-active-no-synthetic-selection');
  notReady({...template,token:{kind:'number',digit:10}},keyboard,'invalid-digit');
});

test('ten-frame one counter (fill or remove), invalid release never commits',()=>{
  const x=cases[2][0];
  ready({...x,from:'cell',to:'return-tray',cellOccupied:true},base,'applyCell');
  notReady({...x,cellOccupied:true},base,'illegal-ten-frame-drop');
  notReady({...x,cellIndex:10},base,'invalid-frame-cell');
  notReady({...x,from:'cell',to:'cell'},base,'illegal-ten-frame-drop');
});

test('group pool conservation enforced by domain; source must exist to remove',()=>{
  const x=cases[3][0];
  ready({...x,from:'group',to:'pool'},base,'applyRemoveItem');
  notReady({...x,from:'group',to:'pool',sourceHasItem:false});
  notReady({...x,groupIndex:3},base,'unknown-group');
});

test('money denomination uses jiao; wallet cannot remove missing coin',()=>{
  const x=cases[4][0];
  ready({...x,from:'wallet',to:'return-tray',walletCount:1},base,'applyRemoveCoin');
  notReady({...x,from:'wallet',to:'return-tray',walletCount:0});
  notReady({...x,denominationJiao:2},base,'denomination-not-in-config');
});

test('bar model and array only support one domain delta per release',()=>{
  const b=cases[5][0],a=cases[6][0];
  notReady({...b,delta:2},base,'invalid-one-block-resize');
  notReady({...b,delta:-1,existingBlocks:0},base,'invalid-one-block-resize');
  notReady({...a,delta:3},base,'array-edge-only-one-row-or-column');
  notReady({...a,delta:-1,current:0},base,'array-edge-only-one-row-or-column');
  ready({...a,edge:'col',delta:-1},base,'applyColDelta');
});

test('selected pool/card state is required (no silent synthesized selection evidence)',()=>{
  const p=cases[7][0],s=cases[8][0];
  notReady({...p,pickedPoolIndex:null},base,'requires-existing-pick-domain-event');
  notReady({...s,selectedCardId:null},base,'requires-existing-selection-no-synthetic-event');
  notReady({...s,targetCardId:'x'},base,'unknown-card');
  notReady({...s,targetCardId:'a'},base,'drop-on-same-card');
});

test('number line signed jump remains positive/negative, bounded to actual ticks',()=>{
  const x=cases[9][0];
  assert.equal(ready(x,base).args.signedJump,4);
  assert.equal(ready({...x,currentTick:8,targetTick:4},base).args.signedJump,-4);
  notReady({...x,currentTick:2,targetTick:2},base,'zero-jump');
  notReady({...x,targetTick:11},base,'invalid-number-line-tick');
  notReady({...x,targetTick:2.5},base,'invalid-number-line-tick');
});

test('ruler respects non-zero origin and tick step',()=>{
  const x=cases[10][0];
  ready({...x,tickMin:1,targetTick:7,allowedTickStep:2},base,'applyPlaceMark');
  notReady({...x,tickMin:1,targetTick:8,allowedTickStep:2},base,'tick-must-be-a-legal-mark');
  notReady({...x,targetTick:21},base,'tick-must-be-a-legal-mark');
});

test('direction grid forbids diagonal, multi-hop and off-grid moves',()=>{
  const x=cases[11][0];
  ready({...x,target:{r:2,c:1}},base,'applyMoveTo');
  notReady({...x,target:{r:2,c:2}},base,'not-one-orthogonal-step');
  notReady({...x,target:{r:1,c:1}},base,'not-one-orthogonal-step');
  notReady({...x,target:{r:1,c:3}},base,'illegal-grid-cell');
});

test('shape canvas only commits a legal discretized point, never inferred stroke',()=>{
  const x=cases[12][0];
  notReady({...x,point:{x:3.2,y:3}},base,'outside-approved-canvas-grid');
  notReady({...x,point:{x:7,y:3}},base,'outside-approved-canvas-grid');
});

test('pattern palette and bounds, gallery selection and model rejection semantics',()=>{
  const p=cases[13][0],g=cases[14][0];
  notReady({...p,locked:true},base,'pattern-slot-not-available');
  notReady({...p,token:5},base,'token-not-in-config-palette');
  notReady({...p,targetIndex:2},base,'pattern-slot-not-available');
  notReady({...g,selectedShapeId:null},base,'requires-existing-shape-selection');
  ready({...g,target:'return-tray',currentlyAtHome:true},base,'applyReturnHome');
  notReady({...g,target:'return-tray',currentlyAtHome:false},base,'illegal-gallery-drop');
});

test('estimation preview must snap and commit once through approved domain action',()=>{
  const x=cases[15][0];
  ready({...x,estimate:20},base,'applyEstimate');
  notReady({...x,estimate:21},base,'unsnapped-or-out-of-range-estimate');
  notReady({...x,estimate:13.5},base,'unsnapped-or-out-of-range-estimate');
  notReady({...x,estimate:13,step:2},base,'unsnapped-or-out-of-range-estimate');
});
