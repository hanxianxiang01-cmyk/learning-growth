'use strict';
/** Runs the COMPILED TSX handler closures using a transparent hook/JSX shim.
 * This is NOT React18 DOM mounting, Chromium touch, Next build or real reducer E2E.
 */
const test=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');
const Module=require('node:module');
const base=path.resolve(__dirname,'../../dist/isolated/apps/child-web/src/features/task-renderer/interaction/kernel');
const samples=require('./fixtures.cjs').samples;
const jsx={jsx:(type,props)=>({type,props:props||{}}),jsxs:(type,props)=>({type,props:props||{}}),Fragment:'Fragment'};
const react={
 useCallback:fn=>fn,useMemo:fn=>fn(),useId:()=>'-offline-test-',useRef:v=>({current:v}),
 useState:v=>[typeof v==='function'?v():v,()=>{}],useEffect:()=>{}
};
function pointerShim(onCommit){
 let active=null;let preview=null;
 return {
  get preview(){return preview;},
  beginPointer(id,value){if(active!==null)return false;active=id;preview=value;return true;},
  movePointer(id,value){if(id!==active)return false;preview=value;return true;},
  finishPointer(id,last,derive){if(id!==active)return false;active=null;preview=null;
    const action=derive(last);if(action!==null){onCommit(action);return true;}return false;},
  cancelPointer(id){if(id===undefined||active===id){active=null;preview=null;}}
 };
}
const original=Module._load;
Module._load=function(name,parent,main){
 if(name==='react')return react;
 if(name==='react/jsx-runtime')return jsx;
 if(name==='./useKernelPointerGesture')return {useKernelPointerGesture:pointerShim};
 return original.apply(this,arguments);
};
let components;
try { components=require(path.join(base,'A5NaturalControls.js')); }
finally{Module._load=original;}
const context={taskInstanceId:'task-1',activeTaskInstanceId:'task-1',uiRevision:17,
  activeUiRevision:17,disabled:false,modality:'pointer'};
function nodes(element,match,out=[]){
 if(!element||typeof element!=='object')return out;
 if(Array.isArray(element)){element.forEach(e=>nodes(e,match,out));return out;}
 if(element.type&&match(element))out.push(element);
 if(element.props)nodes(element.props.children,match,out);
 return out;
}
function byProp(root,key,val){return nodes(root,e=>e.props?.[key]===val)[0];}
function simulate(scene,source,target,options={}){
 const receives=[];const resolutions=[];
 const tree=components.A5NaturalControls({scene,context,canApply:()=>!options.reject,
    onDomainCommand:c=>receives.push(c),onResolution:r=>resolutions.push(r)});
 const sourceEl=byProp(tree,'data-a5-source',source);
 const targetEl=byProp(tree,'data-a5-drop',target);
 assert.ok(sourceEl,`${scene.rendererId} source ${source}`);
 assert.ok(targetEl,`${scene.rendererId} target ${target}`);
 const targetNode={dataset:{a5Drop:target},getBoundingClientRect:()=>({left:0,width:100})};
 targetNode.closest=()=>targetNode;
 tree.props.ref.current={contains:node=>!options.outside&&node===targetNode};
 const oldDocument=global.document;
 global.document={elementFromPoint:()=>options.outside?null:targetNode};
 let captured=null;
 const currentTarget={
   setPointerCapture:id=>{captured=id;},hasPointerCapture:id=>captured===id,
   releasePointerCapture:id=>{if(captured===id)captured=null;}
 };
 const ev=(id,x=65)=>({pointerId:id,button:0,clientX:x,clientY:30,currentTarget,
   stopPropagation(){},preventDefault(){}});
 try {
   sourceEl.props.onPointerDown(ev(13,1));
   sourceEl.props.onPointerDown(ev(14,1)); // Second finger cannot replace active.
   sourceEl.props.onPointerMove(ev(14,80));
   sourceEl.props.onPointerMove(ev(13,30));
   if(options.cancel)sourceEl.props.onPointerCancel(ev(13,30));
   sourceEl.props.onPointerUp(ev(13));
   sourceEl.props.onPointerUp(ev(13)); // duplicate pointer-up must not double-submit.
   sourceEl.props.onLostPointerCapture(ev(13));
 }finally{global.document=oldDocument;}
 return {receives,resolutions,tree};
}
test('all sixteen exported real React control entrypoints exist',()=>{
 const names=['A5NumberInputControls','A5FormulaBoardControls','A5TenFrameControls',
 'A5GroupingBoardControls','A5MoneyBoardControls','A5BarModelControls',
 'A5ArrayBoardControls','A5PlaceValueControls','A5SortingBoardControls',
 'A5NumberLineControls','A5RulerControls','A5DirectionGridControls',
 'A5ShapeCanvasControls','A5PatternBoardControls','A5ShapeGalleryControls',
 'A5EstimationCanvasControls'];
 assert.equal(names.length,16);
 for(const name of names)assert.equal(typeof components[name],'function',name);
});
for(const [scene,source,target,action] of samples.filter(x=>x[1])){
 test(`${scene.rendererId} pointer release calls existing-domain port EXACTLY ONCE`,()=>{
  const r=simulate(scene,source,target);
  assert.equal(r.receives.length,1,`${scene.rendererId}:${JSON.stringify(r.resolutions)}`);
  assert.equal(r.receives[0].operation,action);
  assert.equal(r.receives[0].evidenceOwner,'existing-domain');
 });
}
for(const [scene,source,target] of samples.filter(x=>x[1])){
 test(`${scene.rendererId} cancelled drop produces ZERO domain commits`,()=>{
  const a=simulate(scene,source,target,{cancel:true});assert.equal(a.receives.length,0);
  const b=simulate(scene,source,target,{outside:true});assert.equal(b.receives.length,0);
  const c=simulate(scene,source,target,{reject:true});assert.equal(c.receives.length,0);
 });
}
test('direct number typing calls existing-domain port, no fake math judging',()=>{
 const scene=samples[0][0];const got=[];
 const tree=components.A5NaturalControls({scene,context,canApply:()=>true,onDomainCommand:x=>got.push(x)});
 const input=nodes(tree,e=>e.type==='input')[0];
 input.props.onChange({currentTarget:{value:'74'}});
 assert.equal(got.length,1);assert.equal(got[0].operation,'text change');
 assert.equal(got[0].args.text,'74');
});
test('disabled task rejects actual renderer pointer handler',()=>{
 const [scene,source,target]=samples[2];
 const receives=[];
 const tree=components.A5NaturalControls({scene,context:{...context,disabled:true},canApply:()=>true,onDomainCommand:c=>receives.push(c)});
 const el=byProp(tree,'data-a5-source',source);
 let captured=false;
 el.props.onPointerDown({pointerId:5,button:0,clientX:0,clientY:0,currentTarget:{setPointerCapture:()=>{captured=true;}}});
 assert.equal(captured,false);assert.equal(receives.length,0);
});

/** Headless integration boundary runs handlers on the existing renderer's DOM annotations. */
let boundaryModule;
Module._load=function(name,parent,main){
 if(name==='react')return react;
 if(name==='react/jsx-runtime')return jsx;
 if(name==='./useKernelPointerGesture')return {useKernelPointerGesture:pointerShim};
 return original.apply(this,arguments);
};
try{boundaryModule=require(path.join(base,'A5NaturalRendererBoundary.js'));}
finally{Module._load=original;}
function headless(scene,source,target,{noMotion=false}={}){
 const receives=[];
 const tree=boundaryModule.A5NaturalRendererBoundary({scene,context,children:'existing original renderer content',
   canApply:()=>true,onDomainCommand:c=>receives.push(c)});
 tree.props.ref.current={contains:()=>true};
 const src={dataset:{a5Source:source},closest:selector=>selector==='[data-a5-source]'?src:null};
 const dst={dataset:{a5Drop:target},closest:selector=>selector==='[data-a5-drop]'?dst:null,
   getBoundingClientRect:()=>({left:0,width:100})};
 const prevDoc=global.document;global.document={elementFromPoint:()=>dst};
 let captured=null;const currentTarget={setPointerCapture:id=>{captured=id;},
   hasPointerCapture:id=>captured===id,releasePointerCapture:()=>{captured=null;}};
 let stops=0,prevents=0;
 const e=(x)=>({pointerId:9,button:0,clientX:x,clientY:20,currentTarget,target:src,
   stopPropagation:()=>{stops++;},preventDefault:()=>{prevents++;}});
 try{
   tree.props.onPointerDownCapture(e(1));
   tree.props.onPointerMoveCapture(e(noMotion?1:40));
   tree.props.onPointerUpCapture(e(noMotion?1:65));
   tree.props.onPointerUpCapture(e(65));
   const click={detail:1,target:src,stopPropagation:()=>{stops++;},preventDefault:()=>{prevents++;}};
   tree.props.onClickCapture(click);
 } finally {global.document=prevDoc;}
 return{receives,stops,prevents};
}
test('existing-renderer Boundary is a mountable React component',()=>{
 assert.equal(typeof boundaryModule.A5NaturalRendererBoundary,'function');
});
for(const [scene,source,target,operation] of samples.filter(x=>x[1])){
 test(`${scene.rendererId} ORIGINAL DOM annotation => one existing domain action`,()=>{
  const r=headless(scene,source,target);
  assert.equal(r.receives.length,1,scene.rendererId);
  assert.equal(r.receives[0].operation,operation);
  assert.ok(r.stops>0,'original pointer handler suppressed to prevent double commit');
 });
}
test('existing single click without movement retains legacy click fallback',()=>{
 const [scene,source,target]=samples[2];
 const r=headless(scene,source,target,{noMotion:true});
 assert.equal(r.receives.length,1,'a legitimate same-target release can be processed once');
 assert.equal(r.prevents,0,'legacy source click is not blanket-suppressed');
});
