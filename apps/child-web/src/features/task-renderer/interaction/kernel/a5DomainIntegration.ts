/**
 * MIK-A5 source-grounded bridge between the actual FE-1445 V6 domain modules
 * and the sixteen natural-scene controls. No alternate state, Judge or Evidence.
 * Read-only clones are used exclusively for legality preflight.
 */
import type { A5Scene } from './naturalScene';
import type { A5RendererId, DomainCommand } from './naturalIntent';
import { applyNumberKey, applyOperatorKey } from '../../formulaBoardV2';
import { applyCell } from '../../tenFrameV2';
import { applyAddItem, applyRemoveItem } from '../../groupingBoardV2';
import { applyAddCoin, applyRemoveCoin } from '../../moneyBoardV2';
import { applyBarDelta, type BarId } from '../../barModelV2';
import { applyRowDelta, applyColDelta } from '../../arrayBoardV2';
import { applyPick, applySlot } from '../../placeValueV2';
import { applySelectCard, applySwap } from '../../sortingBoardV2';
import { applyJump } from '../../numberLineV2';
import { applyPlaceMark } from '../../rulerV2';
import { applyMoveTo } from '../../directionGridV2';
import { applyAddPoint } from '../../shapeCanvasV2';
import { applyReplaceAt } from '../../patternBoardV2';
import { applySelect, applyPlaceHome, applyReturnHome } from '../../shapeGalleryV2';
import { applyEstimate } from '../../estimationCanvasV2';
import type { FormulaBoardV2Config, FormulaBoardV2State } from '../../formulaBoardV2';
import type { TenFrameV2Config, TenFrameV2State } from '../../tenFrameV2';
import type { GroupingBoardV2State } from '../../groupingBoardV2';
import type { MoneyV2Config, MoneyV2State } from '../../moneyBoardV2';
import type { BarModelV2Config, BarModelV2State } from '../../barModelV2';
import type { ArrayBoardV2Config, ArrayBoardV2State } from '../../arrayBoardV2';
import type { PlaceValueV2Config, PlaceValueV2State } from '../../placeValueV2';
import type { SortingBoardV2Config, SortingBoardV2State } from '../../sortingBoardV2';
import type { NumberLineV2Config, NumberLineV2State } from '../../numberLineV2';
import type { RulerV2Config, RulerV2State } from '../../rulerV2';
import type { DirectionGridV2Config, DirectionGridV2State } from '../../directionGridV2';
import type { ShapeCanvasV2Config, ShapeCanvasV2State } from '../../shapeCanvasV2';
import type { PatternV2Config, PatternV2State } from '../../patternBoardV2';
import type { ShapeGalleryV2Config, ShapeGalleryV2State } from '../../shapeGalleryV2';
import type { EstimationCanvasV2Config, EstimationCanvasV2State } from '../../estimationCanvasV2';

export type A5ActiveId = Exclude<A5RendererId, 'number-input'>;
const named=(v:unknown):v is string=>typeof v==='string'&&v.length>0;
const number=(v:unknown):number=>Number.isSafeInteger(v)?v as number:NaN;
const bars:readonly BarId[]=['a','b','c'];

/** Shape snapshots are made from the original reducer's present state. */
export function buildA5LiveScene(rendererId:A5ActiveId,rawState:unknown,rawConfig:unknown):A5Scene {
 switch(rendererId){
  case 'formula-board':{
   const s=rawState as FormulaBoardV2State,c=rawConfig as FormulaBoardV2Config;
   return {rendererId,slots:c.tokens.filter(x=>x.t==='slot').map(x=>({id:x.t==='slot'?x.id:'',label:x.t==='slot'?x.id:''})),
     activeSlotId:s.activeSlot,digits:[0,1,2,3,4,5,6,7,8,9],operators:['+','-']};}
  case 'ten-frame':{
   const s=rawState as TenFrameV2State;
   return {rendererId,frames:[Array.from({length:10},(_,i)=>({occupied:i<s.count}))]};}
  case 'grouping-board':{
   const s=rawState as GroupingBoardV2State;
   return {rendererId,groupCounts:s.groups,poolCount:s.pool};}
  case 'money-board':{
   const s=rawState as MoneyV2State,c=rawConfig as MoneyV2Config;
   return {rendererId,denominationsJiao:c.denominations,walletCounts:s.counts};}
  case 'bar-model':{
   const s=rawState as BarModelV2State,c=rawConfig as BarModelV2Config;
   return {rendererId,blocks:bars.map(x=>s.bars[x]),maxBlocks:bars.map(()=>c.maxBlocks)};}
  case 'array-board':{
   const s=rawState as ArrayBoardV2State,c=rawConfig as ArrayBoardV2Config;
   return {rendererId,rows:s.rows,cols:s.cols,maxRows:c.maxRows,maxCols:c.maxCols};}
  case 'place-value':{
   const s=rawState as PlaceValueV2State,c=rawConfig as PlaceValueV2Config;
   return {rendererId,pool:s.pool.map((v,i)=>({id:`${i}:${v}`,label:String(v)})),pickedPoolIndex:s.picked,
     slots:c.places.map((place,i)=>({id:String(i),label:`${place} ${s.slots[i]??'空'}`}))};}
  case 'sorting-board':{
   const s=rawState as SortingBoardV2State,c=rawConfig as SortingBoardV2Config;
   return {rendererId,cards:s.order.map(id=>({id,label:String(c.items.find(x=>x.id===id)?.value??'?')})),selectedCardId:s.selected};}
  case 'number-line':{
   const s=rawState as NumberLineV2State,c=rawConfig as NumberLineV2Config;
   return {rendererId,currentTick:s.current??c.min,minTick:c.min,maxTick:c.max,tickStep:c.tickStep};}
  case 'ruler':{
   const s=rawState as RulerV2State,c=rawConfig as RulerV2Config;
   return {rendererId,marks:[s.marks[0]??null,s.marks[1]??null],minTick:0,maxTick:c.max,step:1};}
  case 'direction-grid':{
   const s=rawState as DirectionGridV2State,c=rawConfig as DirectionGridV2Config;
   return {rendererId,rows:c.rows,cols:c.cols,current:s.steps[s.steps.length-1]??c.start};}
  case 'shape-canvas':{
   const c=rawConfig as ShapeCanvasV2Config;
   return {rendererId,minX:0,maxX:c.grid-1,minY:0,maxY:c.grid-1};}
  case 'pattern-board':{
   const s=rawState as PatternV2State,c=rawConfig as PatternV2Config;
   return {rendererId,palette:c.palette,blanks:s.beads.map((x,i)=>({locked:false,label:`第${i+1}格：${x??'空'}`}))};}
  case 'shape-gallery':{
   const s=rawState as ShapeGalleryV2State,c=rawConfig as ShapeGalleryV2Config;
   return {rendererId,shapes:c.shapes.map(x=>({id:x.id,label:x.name})),selectedShapeId:s.selected,homeIds:s.home};}
  case 'estimation-canvas':{
   const s=rawState as EstimationCanvasV2State,c=rawConfig as EstimationCanvasV2Config;
   return {rendererId,min:0,max:c.max,step:1,currentEstimate:s.estimate};}
 }
}

/** NO correctness/pass checks. Pure action preflight only. */
export function canApplyA5Domain(rendererId:A5ActiveId,rawState:unknown,rawConfig:unknown,cmd:DomainCommand):boolean {
 if(cmd.rendererId!==rendererId)return false;
 const a=cmd.args;
 const s=structuredClone(rawState);
 const c=rawConfig;
 switch(rendererId){
  case 'formula-board':{
   const state=s as FormulaBoardV2State,config=c as FormulaBoardV2Config;
   if(cmd.operation==='applyActivate')return named(a.slotId)&&config.tokens.some(x=>x.t==='slot'&&x.id===a.slotId);
   if(cmd.operation==='applyNumberKey')return applyNumberKey(state,config,number(a.digit)).ok;
   if(cmd.operation==='applyOperatorKey')return (a.symbol==='+'||a.symbol==='-')&&applyOperatorKey(state,config,a.symbol).ok;
   return false;}
  case 'ten-frame':return cmd.operation==='applyCell'&&number(a.frameIndex)===0 &&
    applyCell(s as TenFrameV2State,number(a.cellIndex),c as TenFrameV2Config).ok;
  case 'grouping-board':
   if(cmd.operation==='applyAddItem')return applyAddItem(s as GroupingBoardV2State,number(a.groupIndex)).ok;
   if(cmd.operation==='applyRemoveItem')return applyRemoveItem(s as GroupingBoardV2State,number(a.groupIndex)).ok;
   return false;
  case 'money-board':
   if(cmd.operation==='applyAddCoin')return applyAddCoin(s as MoneyV2State,c as MoneyV2Config,number(a.denominationJiao)).ok;
   if(cmd.operation==='applyRemoveCoin')return applyRemoveCoin(s as MoneyV2State,c as MoneyV2Config,number(a.denominationJiao)).ok;
   return false;
  case 'bar-model':{
   const bar=bars[number(a.barIndex)];return !!bar&&cmd.operation==='applyBarDelta'&&
    applyBarDelta(s as BarModelV2State,bar,number(a.delta),c as BarModelV2Config).ok;}
  case 'array-board':
   if(cmd.operation==='applyRowDelta')return applyRowDelta(s as ArrayBoardV2State,number(a.delta),c as ArrayBoardV2Config).ok;
   if(cmd.operation==='applyColDelta')return applyColDelta(s as ArrayBoardV2State,number(a.delta),c as ArrayBoardV2Config).ok;
   return false;
  case 'place-value':
   if(cmd.operation==='applyPick')return applyPick(s as PlaceValueV2State,number(a.poolIndex)).ok;
   if(cmd.operation==='applySlot')return applySlot(s as PlaceValueV2State,number(a.slotIndex)).ok;
   return false;
  case 'sorting-board':
   if(cmd.operation==='applySelectCard')return named(a.cardId)&&applySelectCard(s as SortingBoardV2State,c as SortingBoardV2Config,a.cardId).ok;
   if(cmd.operation==='applySwap')return named(a.targetCardId)&&applySwap(s as SortingBoardV2State,c as SortingBoardV2Config,a.targetCardId).ok;
   return false;
  case 'number-line':{
   const state=s as NumberLineV2State,config=c as NumberLineV2Config,tick=number(a.toTick);
   return cmd.operation==='applyJump'&&state.current!==null&&Number.isSafeInteger(tick)&&
     tick>=config.min&&tick<=config.max&&(tick-config.min)%config.tickStep===0&&
     applyJump(state,tick,()=> 'preflight').current!==state.current;}
  case 'ruler':{
   const state=s as RulerV2State,mark=number(a.markIndex);
   return cmd.operation==='applyPlaceMark'&&mark===(state.marks.length===1?1:0) &&
     applyPlaceMark(state,c as RulerV2Config,number(a.tick)).ok;}
  case 'direction-grid':return cmd.operation==='applyMoveTo'&&
     applyMoveTo(s as DirectionGridV2State,c as DirectionGridV2Config,{r:number(a.r),c:number(a.c)}).ok;
  case 'shape-canvas':return cmd.operation==='applyAddPoint'&&
     applyAddPoint(s as ShapeCanvasV2State,c as ShapeCanvasV2Config,number(a.x),number(a.y)).ok;
  case 'pattern-board':return cmd.operation==='applyReplaceAt'&&
     applyReplaceAt(s as PatternV2State,c as PatternV2Config,number(a.blankIndex),number(a.token)).ok;
  case 'shape-gallery':
    if(cmd.operation==='applySelect')return named(a.shapeId)&&applySelect(s as ShapeGalleryV2State,c as ShapeGalleryV2Config,a.shapeId).ok;
    if(cmd.operation==='applyPlaceHome')return named(a.shapeId)&&
      (s as ShapeGalleryV2State).selected===a.shapeId&&applyPlaceHome(s as ShapeGalleryV2State,c as ShapeGalleryV2Config).ok;
    if(cmd.operation==='applyReturnHome')return named(a.shapeId)&&
      applyReturnHome(s as ShapeGalleryV2State,a.shapeId).ok;
    return false;
  case 'estimation-canvas':{
   const state=s as EstimationCanvasV2State;
   const result=applyEstimate(state,c as EstimationCanvasV2Config,number(a.value));
   return cmd.operation==='applyEstimate'&&result.ok&&result.state!==state;}
 }
 return false;
}
