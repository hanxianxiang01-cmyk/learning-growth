"use client";
/**
 * Isolated A5 pointer coordinator. The supplied SAFE-01 SPIKE archive does NOT
 * include MIK-A0/A4's interactionKernel implementation; this self-contained
 * hook therefore provides only the pointer preview/commit protocol required
 * by A5. It is not the historic A4 implementation or its verification.
 *
 * All domain/evidence writes happen ONLY via onCommit after a legal PointerUp.
 */
import { useCallback, useEffect, useRef, useState } from "react";
export function useKernelPointerGesture<TPreview, TAction>(onCommit: (action: TAction) => void) {
  const active=useRef<{pointerId:number; preview:TPreview} | null>(null);
  const commitRef=useRef(onCommit);commitRef.current=onCommit;
  const [preview,setPreview]=useState<TPreview|null>(null);
  const beginPointer=useCallback((pointerId:number,initial:TPreview):boolean=>{
    if(active.current || !Number.isSafeInteger(pointerId))return false;
    active.current={pointerId,preview:initial};setPreview(initial);return true;
  },[]);
  const movePointer=useCallback((pointerId:number,next:TPreview):boolean=>{
    if(active.current?.pointerId!==pointerId)return false;
    active.current.preview=next;setPreview(next);return true;
  },[]);
  const cancelPointer=useCallback((pointerId?:number)=>{
    if(pointerId!==undefined && active.current?.pointerId!==pointerId)return;
    active.current=null;setPreview(null);
  },[]);
  const finishPointer=useCallback((pointerId:number,last:TPreview,
    derive:(preview:TPreview)=>TAction|null):boolean=>{
    if(active.current?.pointerId!==pointerId)return false;
    active.current.preview=last;
    // Clear the transaction before invoking external user code. A duplicate
    // PointerUp cannot submit the same operation twice, including on throws.
    active.current=null;setPreview(null);
    const action=derive(last);
    if(action===null)return false;
    commitRef.current(action);return true;
  },[]);
  useEffect(()=>()=>{active.current=null;},[]);
  return {preview,beginPointer,movePointer,finishPointer,cancelPointer};
}
