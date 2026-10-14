'use client';
/**
 * 16 real React/DOM natural interaction surfaces, suitable for mounting INSIDE
 * the existing renderer. Domain state, approved event construction, reducer,
 * response serializer and Judge remain exclusively the calling renderer's job.
 *
 * No DOM.click(), no silent synthetic selection, no alternate answer state.
 */
import { useCallback, useEffect, useId, useMemo, useRef, useState,
  type ChangeEvent, type KeyboardEvent, type PointerEvent, type MouseEvent } from 'react';
import { useA5NaturalDrop } from './useA5NaturalDrop';
import { type A5Context, type A5Intent,
  type A5Resolution, type DomainCommand } from './naturalIntent';
import { a5ExplicitSelection, a5IntentForDrop, buildA5Scene, type A5Scene } from './naturalScene';

export type A5NaturalControlsProps = Readonly<{
  scene: A5Scene;
  context: A5Context;
  /** The existing domain function, on a CLONED state, must decide legal action. */
  canApply: (command: DomainCommand) => boolean;
  /** Call the existing approved domain action, then ONE reducer/event commit. */
  onDomainCommand: (command: DomainCommand) => void;
  onResolution?: (result: A5Resolution) => void;
  className?: string;
}>;

const block = (reason: string): A5Resolution => ({ status: 'blocked', reason });
function targetAt(root: HTMLElement | null, x: number, y: number): HTMLElement | null {
  if (!root || typeof document === 'undefined') return null;
  const at = document.elementFromPoint(x, y);
  if (!at || typeof (at as Element).closest !== 'function') return null;
  const target = (at as Element).closest('[data-a5-drop]') as HTMLElement | null;
  return target && root.contains(target) ? target : null;
}
function safeRange(scene: Extract<A5Scene, {rendererId:'estimation-canvas'}>, raw: number): number {
  if (!Number.isFinite(raw) || scene.step <= 0) return scene.min;
  const clipped = Math.max(scene.min,Math.min(scene.max,raw));
  return Math.max(scene.min,Math.min(scene.max,
    scene.min+Math.round((clipped-scene.min)/scene.step)*scene.step));
}

/** One mountable component; all sixteen scene variants run through the same pointer coordinator. */
export function A5NaturalControls({scene,context,canApply,onDomainCommand,onResolution,className}:A5NaturalControlsProps) {
  const rootRef=useRef<HTMLElement|null>(null);
  const contextRef=useRef(context);contextRef.current=context;
  const sceneRef=useRef(scene);sceneRef.current=scene;
  const [selected,setSelected]=useState<string|null>(null);
  const [message,setMessage]=useState('');
  const [draft,setDraft]=useState<number>(()=>scene.rendererId==='estimation-canvas'?scene.currentEstimate??scene.min:0);
  const uid=useId();
  const layout=useMemo(()=>buildA5Scene(scene),[scene]);
  const snapshotKey=JSON.stringify(scene);

  const notify=useCallback((resolution:A5Resolution)=>{
    onResolution?.(resolution);
    if (resolution.status==='blocked')setMessage('当前操作不符合题目要求，请换个位置试试。');
    else if (resolution.status==='cancelled')setMessage('已取消本次移动。');
    else setMessage('已放好。');
  },[onResolution]);

  const hitToIntent=useCallback((source:string,point:{x:number;y:number}):A5Intent|null=>{
    const node=targetAt(rootRef.current,point.x,point.y);
    const target=node?.dataset.a5Drop??null;
    let ratio: number|undefined;
    if (node && target==='range') {
      const rect=node.getBoundingClientRect();
      if (rect.width>0)ratio=Math.max(0,Math.min(1,(point.x-rect.left)/rect.width));
    }
    return a5IntentForDrop(sceneRef.current,source,target,ratio);
  },[]);

  const gesture=useA5NaturalDrop<string>({
    context,
    toIntent:hitToIntent,
    canApply,
    onDomainCommand,
    onResolution:notify
  });
  const cancelPointer=gesture.cancelPointer;
  useEffect(()=>{
    // React re-render from task/domain state changes invalidates a staged action.
    cancelPointer();setSelected(null);
    if (scene.rendererId==='estimation-canvas')setDraft(scene.currentEstimate??scene.min);
  },[context.taskInstanceId, context.uiRevision,snapshotKey,cancelPointer]);

  const commitExplicit=useCallback((key:string)=>{
    const cmd=a5ExplicitSelection(sceneRef.current,key);
    if (!cmd)return notify(block('not-a-domain-explicit-selection'));
    if (contextRef.current.disabled ||
        contextRef.current.taskInstanceId!==contextRef.current.activeTaskInstanceId ||
        contextRef.current.uiRevision!==contextRef.current.activeUiRevision) {
      notify({status:'cancelled',reason:'task-disabled-or-changed'});return;
    }
    if (!canApply(cmd))return notify(block('existing-domain-preflight-rejected'));
    onDomainCommand(cmd);notify({status:'ready',command:cmd});
  },[canApply,onDomainCommand,notify]);

  const keyboardCommit=useCallback((intent:A5Intent|null)=>{
    if (!intent)return notify({status:'cancelled',reason:'invalid-source-target-pair'});
    const result=gesture.commitAccessible(intent);
    notify(result);
    setSelected(null);
  },[gesture.commitAccessible,notify]);

  const submitKeyboard=(source:string,target:string)=>{
    keyboardCommit(a5IntentForDrop(sceneRef.current,source,target,
      sceneRef.current.rendererId==='estimation-canvas'?0.5:undefined));
  };

  if (scene.rendererId==='number-input'){
    return <section ref={rootRef} className={`a5-panel ${className??''}`.trim()}
      aria-label="自然数字输入" data-a5-renderer="number-input">
      <label htmlFor={`${uid}-number`} className="a5-title">写下你的答案</label>
      <input id={`${uid}-number`} value={scene.text} inputMode={scene.integerOnly?'numeric':'decimal'}
        aria-describedby={`${uid}-hint`} disabled={context.disabled} type="text" autoComplete="off"
        onChange={(event:ChangeEvent<HTMLInputElement>)=>keyboardCommit({
          rendererId:'number-input',text:event.currentTarget.value,integerOnly:scene.integerOnly,maxLength:scene.maxLength
        })}/>
      <p id={`${uid}-hint`}>可以先输入部分数字；是否完整由原题目判断。</p>
      <p role="status" aria-live="polite" className="a5-status">{message}</p>
    </section>;
  }

  const estimation=scene.rendererId==='estimation-canvas'?scene:null;
  const sourceEl=(s:{id:string;label:string;title?:string})=>{
    const g=gesture.getPointerProps(s.id);
    return <button key={s.id} type="button" disabled={context.disabled} className={`a5-source ${selected===s.id?'is-selected':''}`}
        title={s.title??'拖动到下方目标；键盘可先选此物体再选目标'}
        aria-pressed={selected===s.id} data-a5-source={s.id} style={{touchAction:'none'}}
        onPointerDown={g.onPointerDown} onPointerMove={g.onPointerMove} onPointerUp={g.onPointerUp}
        onPointerCancel={g.onPointerCancel} onLostPointerCapture={g.onLostPointerCapture}
        onClick={(e:MouseEvent<HTMLButtonElement>)=>{ // detail=0 means keyboard-invoked click; pointer release never replays an action.
          if(e.detail===0)setSelected(v=>v===s.id?null:s.id);
        }}>
        {s.label}
      </button>;
  };
  const targetEl=(t:{id:string;label:string;title?:string})=>
    <button key={t.id} type="button" data-a5-drop={t.id} className="a5-target" disabled={context.disabled}
      onClick={()=>{
        if(selected)submitKeyboard(selected,t.id);
        else setMessage('先在上方选择一个物体，再选择放置位置。');
      }} aria-label={t.label}>{t.label}</button>;

  const commitEstimate=(value:number)=>{
    if (!estimation)return;
    keyboardCommit({rendererId:'estimation-canvas',estimate:safeRange(estimation,value),
      min:estimation.min,max:estimation.max,step:estimation.step});
  };

  return <section ref={rootRef} className={`a5-panel ${className??''}`.trim()} data-a5-renderer={scene.rendererId}
    aria-label={layout.title} aria-describedby={`${uid}-hint`}>
    <div className="a5-head"><strong className="a5-title">{layout.title}</strong>
      <span className="a5-instructions" id={`${uid}-hint`}>{layout.instructions}</span></div>
    {layout.explicitSelections.length>0&&<div className="a5-selections" aria-label="明确选中操作">
      {layout.explicitSelections.map(s=><button type="button" key={s.id} disabled={context.disabled}
        className="a5-select" data-a5-explicit={s.id} onClick={()=>commitExplicit(s.id)}>{s.label}</button>)}
    </div>}
    <div className="a5-sources" role="group" aria-label="可以移动的物体">
      {layout.sources.map(sourceEl)}
    </div>
    <div className={`a5-targets a5-${scene.rendererId}`} role="group" aria-label="可以放置的位置">
      {layout.targets.map(targetEl)}
    </div>
    {estimation&&<div className="a5-range-standalone">
      <label htmlFor={`${uid}-slider`}>当前预览：{draft}</label>
      <input id={`${uid}-slider`} type="range" disabled={context.disabled}
        min={estimation.min} max={estimation.max} step={estimation.step}
        value={draft} onChange={(e:ChangeEvent<HTMLInputElement>)=>setDraft(Number(e.currentTarget.value))}
        onPointerUp={(e:PointerEvent<HTMLInputElement>)=>{e.stopPropagation();commitEstimate(Number(e.currentTarget.value));}}
        onKeyUp={(e:KeyboardEvent<HTMLInputElement>)=>{
          if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End','PageUp','PageDown'].includes(e.key))
            commitEstimate(Number(e.currentTarget.value));
        }} onPointerCancel={()=>setDraft(estimation.currentEstimate??estimation.min)}
        aria-label="拖动或方向键调整估计值；松手提交一次"/>
    </div>}
    {gesture.preview && <output aria-hidden="true" className="a5-preview"
      style={{left:gesture.preview.x,top:gesture.preview.y}}>●</output>}
    <p role="status" aria-live="polite" className="a5-status">{message}</p>
  </section>;
}

/** Sixteen individually importable React control surfaces, one delivery batch. */
type SceneFor<I extends A5Scene['rendererId']> = Extract<A5Scene,{rendererId:I}>;
type VariantProps<I extends A5Scene['rendererId']> = Omit<A5NaturalControlsProps,'scene'> & {scene:SceneFor<I>};
export const A5NumberInputControls=(p:VariantProps<'number-input'>)=><A5NaturalControls {...p}/>;
export const A5FormulaBoardControls=(p:VariantProps<'formula-board'>)=><A5NaturalControls {...p}/>;
export const A5TenFrameControls=(p:VariantProps<'ten-frame'>)=><A5NaturalControls {...p}/>;
export const A5GroupingBoardControls=(p:VariantProps<'grouping-board'>)=><A5NaturalControls {...p}/>;
export const A5MoneyBoardControls=(p:VariantProps<'money-board'>)=><A5NaturalControls {...p}/>;
export const A5BarModelControls=(p:VariantProps<'bar-model'>)=><A5NaturalControls {...p}/>;
export const A5ArrayBoardControls=(p:VariantProps<'array-board'>)=><A5NaturalControls {...p}/>;
export const A5PlaceValueControls=(p:VariantProps<'place-value'>)=><A5NaturalControls {...p}/>;
export const A5SortingBoardControls=(p:VariantProps<'sorting-board'>)=><A5NaturalControls {...p}/>;
export const A5NumberLineControls=(p:VariantProps<'number-line'>)=><A5NaturalControls {...p}/>;
export const A5RulerControls=(p:VariantProps<'ruler'>)=><A5NaturalControls {...p}/>;
export const A5DirectionGridControls=(p:VariantProps<'direction-grid'>)=><A5NaturalControls {...p}/>;
export const A5ShapeCanvasControls=(p:VariantProps<'shape-canvas'>)=><A5NaturalControls {...p}/>;
export const A5PatternBoardControls=(p:VariantProps<'pattern-board'>)=><A5NaturalControls {...p}/>;
export const A5ShapeGalleryControls=(p:VariantProps<'shape-gallery'>)=><A5NaturalControls {...p}/>;
export const A5EstimationCanvasControls=(p:VariantProps<'estimation-canvas'>)=><A5NaturalControls {...p}/>;
