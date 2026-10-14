'use client';
/**
 * Headless natural-event boundary for the EXISTING 16 kernel React renderers.
 * Place inside a V1.4 renderer and annotate its real manipulatives with
 * data-a5-source / data-a5-drop IDs from buildA5Scene(scene).
 * This reuses the existing visual board rather than drawing another answer UI.
 *
 * The renderer MUST use the domain port for its approved SET_STATE + Event;
 * it MUST NOT keep its old click commit on an annotated drag surface.
 */
import { useCallback, useEffect, useRef, useState,
  type KeyboardEvent, type MouseEvent, type PointerEvent, type ReactNode } from 'react';
import { useA5NaturalDrop } from './useA5NaturalDrop';
import { a5IntentForDrop,buildA5Scene,type A5Scene } from './naturalScene';
import type { A5Context,A5Intent,A5Resolution,DomainCommand } from './naturalIntent';

type Props=Readonly<{
  scene:A5Scene;context:A5Context;children:ReactNode;
  canApply:(command:DomainCommand)=>boolean;
  onDomainCommand:(command:DomainCommand)=>void;
  onResolution?:(resolution:A5Resolution)=>void;
}>;

export function A5NaturalRendererBoundary({scene,context,children,canApply,onDomainCommand,onResolution}:Props){
  const rootRef=useRef<HTMLDivElement|null>(null);
  const sceneRef=useRef(scene);sceneRef.current=scene;
  const activeSource=useRef<string|null>(null);
  const dragStart=useRef<{x:number;y:number;moved:boolean}|null>(null);
  const suppressSourceClick=useRef<string|null>(null);
  const [keyboardSource,setKeyboardSource]=useState<string|null>(null);
  const snapshotKey=JSON.stringify(scene);
  const report=useCallback((r:A5Resolution)=>{onResolution?.(r);},[onResolution]);
  const hit=useCallback((source:string,point:{x:number;y:number}):A5Intent|null=>{
    if(typeof document==='undefined')return null;
    const at=document.elementFromPoint(point.x,point.y);
    if(!at || typeof (at as Element).closest!=='function')return null;
    const target=(at as Element).closest('[data-a5-drop]') as HTMLElement|null;
    if(!target || !rootRef.current?.contains(target))return null;
    let ratio:number|undefined;
    if(target.dataset.a5Drop==='range'){
      const r=target.getBoundingClientRect();
      if(r.width>0)ratio=Math.max(0,Math.min(1,(point.x-r.left)/r.width));
    }
    return a5IntentForDrop(sceneRef.current,source,target.dataset.a5Drop??null,ratio);
  },[]);
  const drop=useA5NaturalDrop<string>({context,toIntent:hit,canApply,onDomainCommand,onResolution:report});
  const cancelPointer=drop.cancelPointer;
  useEffect(()=>{
    cancelPointer();activeSource.current=null;setKeyboardSource(null);
  },[context.taskInstanceId,context.uiRevision,snapshotKey,context.disabled,cancelPointer]);
  const findData=(target:EventTarget|null,name:'data-a5-source'|'data-a5-drop')=>{
    if(!target || typeof (target as Element).closest!=='function')return null;
    const node=(target as Element).closest(`[${name}]`) as HTMLElement|null;
    return node && rootRef.current?.contains(node)?node:null;
  };
  const pointerDown=(e:PointerEvent<HTMLDivElement>)=>{
    if(context.disabled || e.button!==0 || activeSource.current)return;
    const element=findData(e.target,'data-a5-source');
    const key=element?.dataset.a5Source;
    if(!key || !buildA5Scene(sceneRef.current).sources.some(x=>x.id===key))return;
    activeSource.current=key;dragStart.current={x:e.clientX,y:e.clientY,moved:false};
    suppressSourceClick.current=null;
    drop.getPointerProps(key).onPointerDown(e);
    e.stopPropagation();
  };
  const pointerMove=(e:PointerEvent<HTMLDivElement>)=>{
    if(!activeSource.current)return;
    const start=dragStart.current;
    if(start && Math.hypot(e.clientX-start.x,e.clientY-start.y)>8)start.moved=true;
    drop.getPointerProps(activeSource.current).onPointerMove(e);
    e.stopPropagation();
  };
  const pointerUp=(e:PointerEvent<HTMLDivElement>)=>{
    const key=activeSource.current;if(!key)return;
    const start=dragStart.current;dragStart.current=null;
    activeSource.current=null;
    suppressSourceClick.current=start?.moved||!!(start&&Math.hypot(e.clientX-start.x,e.clientY-start.y)>8)?key:null;
    drop.getPointerProps(key).onPointerUp(e);
    e.stopPropagation();
  };
  const pointerCancel=(e:PointerEvent<HTMLDivElement>)=>{
    const key=activeSource.current;activeSource.current=null;dragStart.current=null;
    if(key){drop.getPointerProps(key).onPointerCancel(e);e.stopPropagation();}
  };
  const keyDown=(e:KeyboardEvent<HTMLDivElement>)=>{
    if(context.disabled || !['Enter',' '].includes(e.key))return;
    const source=findData(e.target,'data-a5-source')?.dataset.a5Source;
    const target=findData(e.target,'data-a5-drop')?.dataset.a5Drop;
    if(source && buildA5Scene(sceneRef.current).sources.some(x=>x.id===source)){
      setKeyboardSource(x=>x===source?null:source);e.preventDefault();e.stopPropagation();return;
    }
    if(target && keyboardSource){
      const intent=a5IntentForDrop(sceneRef.current,keyboardSource,target,
        sceneRef.current.rendererId==='estimation-canvas'?0.5:undefined);
      if(!intent)report({status:'cancelled',reason:'invalid-source-target'});
      else report(drop.commitAccessible(intent));
      setKeyboardSource(null);e.preventDefault();e.stopPropagation();
    }
  };
  const clickCapture=(e:MouseEvent<HTMLDivElement>)=>{
    // Pointer-up may generate a synthetic click. Do NOT also run the old onClick.
    const source=findData(e.target,'data-a5-source')?.dataset.a5Source;
    if(suppressSourceClick.current && source===suppressSourceClick.current && e.detail>0){
      suppressSourceClick.current=null;e.preventDefault();e.stopPropagation();
    }
  };
  return <div ref={rootRef} data-a5-existing-renderer={scene.rendererId} role="group"
    aria-label="操作题目中的物体；键盘可先选来源再选目标"
    onPointerDownCapture={pointerDown} onPointerMoveCapture={pointerMove}
    onPointerUpCapture={pointerUp} onPointerCancelCapture={pointerCancel}
    onLostPointerCapture={pointerCancel} onKeyDownCapture={keyDown}
    onClickCapture={clickCapture}>
    {children}
    {drop.preview && <output className="a5-preview" aria-hidden="true"
      style={{left:drop.preview.x,top:drop.preview.y}}>●</output>}
  </div>;
}
