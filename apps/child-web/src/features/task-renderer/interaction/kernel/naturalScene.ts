/**
 * MIK-A5 integrated sixteen-renderer scene specification.
 * The renderer supplies a read-only snapshot of its EXISTING domain state.
 * This file neither calculates answers nor creates Evidence.
 * Separate, explicit select/pick controls remain genuine domain actions.
 */
import {
  A5_DOMAIN_ACTIONS,
  type A5Intent,
  type A5RendererId,
  type DomainCommand
} from './naturalIntent';

type B = Readonly<{ id: string; label: string }>;
type Cell = Readonly<{ occupied: boolean }>;
export type A5Scene =
  | Readonly<{ rendererId: 'number-input'; text: string; integerOnly: boolean; maxLength: number }>
  | Readonly<{ rendererId: 'formula-board'; slots: readonly B[]; activeSlotId: string | null;
      digits: readonly number[]; operators: readonly string[] }>
  | Readonly<{ rendererId: 'ten-frame'; frames: readonly (readonly Cell[])[] }>
  | Readonly<{ rendererId: 'grouping-board'; groupCounts: readonly number[]; poolCount: number }>
  | Readonly<{ rendererId: 'money-board'; denominationsJiao: readonly number[];
      walletCounts: Readonly<Record<number, number>> }>
  | Readonly<{ rendererId: 'bar-model'; blocks: readonly number[]; maxBlocks: readonly number[] }>
  | Readonly<{ rendererId: 'array-board'; rows: number; cols: number; maxRows: number; maxCols: number }>
  | Readonly<{ rendererId: 'place-value'; pool: readonly B[]; pickedPoolIndex: number | null;
      slots: readonly B[] }>
  | Readonly<{ rendererId: 'sorting-board'; cards: readonly B[]; selectedCardId: string | null }>
  | Readonly<{ rendererId: 'number-line'; currentTick: number; minTick: number; maxTick: number; tickStep?: number }>
  | Readonly<{ rendererId: 'ruler'; marks: readonly [number | null, number | null];
      minTick: number; maxTick: number; step: number }>
  | Readonly<{ rendererId: 'direction-grid'; rows: number; cols: number;
      current: Readonly<{ r: number; c: number }> }>
  | Readonly<{ rendererId: 'shape-canvas'; minX: number; maxX: number; minY: number; maxY: number }>
  | Readonly<{ rendererId: 'pattern-board'; palette: readonly (string | number)[];
      blanks: readonly Readonly<{ locked: boolean; label: string }>[] }>
  | Readonly<{ rendererId: 'shape-gallery'; shapes: readonly B[];
      selectedShapeId: string | null; homeIds: readonly string[] }>
  | Readonly<{ rendererId: 'estimation-canvas'; min: number; max: number;
      step: number; currentEstimate: number | null }>;

export type A5Affordance = B & Readonly<{ title?: string }>;
export type A5SceneLayout = Readonly<{
  rendererId: A5RendererId;
  title: string;
  instructions: string;
  sources: readonly A5Affordance[];
  targets: readonly A5Affordance[];
  explicitSelections: readonly A5Affordance[];
  kind: 'drag-board' | 'number-input';
}>;

const maxItems = 180;
const make = (id: string, label: string, title?: string): A5Affordance => ({ id, label, title });
const finiteInt = (x: number): boolean => Number.isSafeInteger(x);
function ticks(min: number, max: number, step: number): number[] {
  if (!finiteInt(min) || !finiteInt(max) || !finiteInt(step) || step < 1 ||
      max < min || (max - min) / step > maxItems) return [];
  const a: number[] = [];
  for (let n = min; n <= max; n += step) a.push(n);
  return a;
}

/** No unchecked/out-of-bounds scene expansion, which could freeze a child device. */
export function buildA5Scene(scene: A5Scene): A5SceneLayout {
  const base = (title: string, instructions: string, sources: A5Affordance[],
    targets: A5Affordance[], explicitSelections: A5Affordance[] = [],
    kind: A5SceneLayout['kind'] = 'drag-board'): A5SceneLayout =>
    ({ rendererId: scene.rendererId, title, instructions, sources, targets, explicitSelections, kind });
  switch (scene.rendererId) {
    case 'number-input': return base('写下答案', '可以输入尚未完成的数字；按原有提交按钮检查。', [], [], [], 'number-input');
    case 'formula-board': return base('填算式', '先选择空格，再把数字或运算符拖进当前空格。',
      [...scene.digits.filter(x => finiteInt(x) && x >= 0 && x <= 9).map(x => make(`digit:${x}`, String(x))),
       ...scene.operators.map((x,i) => make(`op:${i}`, x))],
      scene.slots.filter(x=>x.id === scene.activeSlotId).map(x=>make(`slot:${x.id}`, x.label)),
      scene.slots.map(x=>make(`select:${x.id}`, `选 ${x.label}`)));
    case 'ten-frame': {
      const targets: A5Affordance[] = [];
      const sources: A5Affordance[] = [make('bank', '● 从篮子取1颗')];
      if (scene.frames.length > 8) return base('十格框', '格子数量超过交互显示上限。', [], []);
      scene.frames.forEach((frame,f) => frame.slice(0, 10).forEach((cell,c) => {
        if (cell.occupied) sources.push(make(`cell:${f}:${c}`, `第${f+1}框第${c+1}颗`));
        else targets.push(make(`cell:${f}:${c}`, `第${f+1}框第${c+1}格`));
      }));
      targets.push(make('return', '放回篮子'));
      return base('十格框', '每次拿放一颗；必须放到空格或归还篮子。', sources, targets);
    }
    case 'grouping-board': {
      const sources = scene.poolCount > 0 ? [make('pool', `待分配 ${scene.poolCount} 个`)] : [];
      scene.groupCounts.forEach((c, i) => { if (c > 0) sources.push(make(`group:${i}`, `从第${i+1}组取1个`)); });
      return base('分组', '每次拿一个，拖入已有分组或回到材料池。', sources,
        [...scene.groupCounts.map((c,i)=>make(`group:${i}`, `第${i+1}组（${c}个）`)), make('pool','归还材料池')]);
    }
    case 'money-board': {
      const ds = scene.denominationsJiao.filter(x=>finiteInt(x)&&x>0);
      const sources = ds.map(x=>make(`bank:${x}`, `取${x}角`));
      ds.forEach(x=>{ if ((scene.walletCounts[x] ?? 0) > 0) sources.push(make(`wallet:${x}`, `归还${x}角`)); });
      return base('付钱', '从钱币盒取一枚，放进钱包；也可放回零钱盒。', sources,
        [make('wallet','放进钱包'),make('return','零钱归还区')]);
    }
    case 'bar-model': return base('条形图', '按加一格、减一格控制条长；一次只变一格。',
      scene.blocks.map((n,i)=>make(`bar:${i}`, `第${i+1}条（${n}格）`)),
      scene.blocks.flatMap((_n,i)=>[make(`bar:${i}:1`,'加一格'),make(`bar:${i}:-1`,'减一格')]));
    case 'array-board': return base('行列阵列', '拖动行或列的控制柄，一次增减一整行或一整列。',
      [make('row','行控制柄'),make('col','列控制柄')],
      [make('row:1','加一行'),make('row:-1','减一行'),make('col:1','加一列'),make('col:-1','减一列')]);
    case 'place-value': return base('数位卡', '必须先明确选中一张数字卡，再拖进十位、个位等槽。',
      scene.pool.map((c,i)=>make(`pool:${i}`, `${c.label}（${c.id}）`)),
      scene.slots.map((c,i)=>make(`slot:${i}`,c.label)),
      scene.pool.map((c,i)=>make(`select:${i}`,`选 ${c.label}`)));
    case 'sorting-board': return base('排序', '先选中要交换的卡片，再拖到另一张卡片的位置。',
      scene.cards.map((c,i)=>make(`card:${i}`,c.label)),
      scene.cards.map((c,i)=>make(`target:${i}`,`与 ${c.label} 交换`)),
      scene.cards.map((c,i)=>make(`select:${i}`,`选 ${c.label}`)));
    case 'number-line': return base('数轴跳跃', '从当前位置拖到一个刻度，路径由原题目规则判断。',
      [make('cursor',`当前位置 ${scene.currentTick}`)],
      ticks(scene.minTick,scene.maxTick,scene.tickStep??1).map(n=>make(`tick:${n}`,String(n))));
    case 'ruler': return base('刻度尺', '移动第一或第二枚标记到刻度，不允许猜测零点。',
      [make('mark:0','第一枚标记'),make('mark:1','第二枚标记')],
      ticks(scene.minTick,scene.maxTick,scene.step).map(n=>make(`tick:${n}`,String(n))));
    case 'direction-grid': {
      const targets: A5Affordance[]=[];
      if (scene.rows > 0 && scene.cols > 0 && scene.rows*scene.cols<=maxItems)
        for(let r=0;r<scene.rows;r++) for(let c=0;c<scene.cols;c++)
          targets.push(make(`cell:${r}:${c}`, `${r+1}行${c+1}列`));
      return base('方向格', '只能走到上下左右的相邻格子。',
        [make('cursor','当前位置')], targets);
    }
    case 'shape-canvas': {
      const targets: A5Affordance[]=[];
      if (scene.maxX>=scene.minX && scene.maxY>=scene.minY &&
          (scene.maxX-scene.minX+1)*(scene.maxY-scene.minY+1)<=maxItems &&
          [scene.minX,scene.maxX,scene.minY,scene.maxY].every(finiteInt))
        for(let y=scene.minY;y<=scene.maxY;y++)for(let x=scene.minX;x<=scene.maxX;x++)
          targets.push(make(`point:${x}:${y}`,`(${x},${y})`));
      return base('几何画板', '每次落笔确定一个网格点；不自动补出任何线段。', [make('pen','画笔')],targets);
    }
    case 'pattern-board': return base('规律填空','把题目允许的颜色或数字放在可用空格。',
      scene.palette.map((x,i)=>make(`token:${i}`,String(x))),
      scene.blanks.map((x,i)=>make(`blank:${i}`,x.label)));
    case 'shape-gallery': return base('图形归类','先选中图形，再移入归类盒，或将已入盒的图形移回。',
      scene.shapes.map((c,i)=>make(`shape:${i}`,c.label)),
      [make('home','归类盒'),make('return','归还区')],
      scene.shapes.map((c,i)=>make(`select:${i}`,`选 ${c.label}`)));
    case 'estimation-canvas': return base('估一估','沿数值轨道滑动；松手后提交一次估算。',
      [make('estimate',`当前估计：${scene.currentEstimate ?? '未设置'}`)],
      [make('range','数值轨道')]);
  }
}

const idx = (part: string | undefined): number => part!==undefined && /^\d+$/.test(part)?Number(part):NaN;
const signed = (part: string | undefined): number => part!==undefined && /^-?\d+$/.test(part)?Number(part):NaN;
/** Convert a DOM drop to a typed intent; only scene-declared keys are accepted. */
export function a5IntentForDrop(scene: A5Scene, sourceKey: string, targetKey: string | null,
  normalizedPosition?: number): A5Intent | null {
  if (!targetKey) return null;
  const layout=buildA5Scene(scene);
  if (!layout.sources.some(s=>s.id===sourceKey) || !layout.targets.some(s=>s.id===targetKey)) return null;
  const s=sourceKey.split(':'),t=targetKey.split(':');
  switch(scene.rendererId){
    case 'number-input': return null;
    case 'formula-board': {
      const slotId=scene.activeSlotId;
      if (!slotId || targetKey!==`slot:${slotId}`) return null;
      if (s[0]==='digit') return {rendererId:'formula-board',slotId,activeSlotId:slotId,token:{kind:'number',digit:idx(s[1])}};
      if (s[0]==='op' && scene.operators[idx(s[1])]!==undefined)
        return {rendererId:'formula-board',slotId,activeSlotId:slotId,token:{kind:'operator',symbol:scene.operators[idx(s[1])]}};
      return null;
    }
    case 'ten-frame': {
      if(sourceKey==='bank' && t[0]==='cell') {
        const f=idx(t[1]),c=idx(t[2]);return {rendererId:'ten-frame',from:'bank',to:'cell',frameIndex:f,cellIndex:c,cellOccupied:!!scene.frames[f]?.[c]?.occupied};
      }
      if(s[0]==='cell'&&targetKey==='return'){
        const f=idx(s[1]),c=idx(s[2]);return {rendererId:'ten-frame',from:'cell',to:'return-tray',frameIndex:f,cellIndex:c,cellOccupied:!!scene.frames[f]?.[c]?.occupied};
      }
      return null;
    }
    case 'grouping-board': {
      if(sourceKey==='pool'&&t[0]==='group') return {rendererId:'grouping-board',from:'pool',to:'group',groupIndex:idx(t[1]),groupCount:scene.groupCounts.length,sourceHasItem:scene.poolCount>0};
      if(s[0]==='group'&&targetKey==='pool')return {rendererId:'grouping-board',from:'group',to:'pool',groupIndex:idx(s[1]),groupCount:scene.groupCounts.length,sourceHasItem:(scene.groupCounts[idx(s[1])]??0)>0};
      return null;
    }
    case 'money-board': {
      if(s[0]==='bank'&&targetKey==='wallet')return {rendererId:'money-board',from:'coin-bank',to:'wallet',denominationJiao:idx(s[1]),allowedDenominationsJiao:scene.denominationsJiao,walletCount:scene.walletCounts[idx(s[1])]??0};
      if(s[0]==='wallet'&&targetKey==='return')return {rendererId:'money-board',from:'wallet',to:'return-tray',denominationJiao:idx(s[1]),allowedDenominationsJiao:scene.denominationsJiao,walletCount:scene.walletCounts[idx(s[1])]??0};
      return null;
    }
    case 'bar-model': {
      if(s[0]==='bar'&&t[0]==='bar'&&s[1]===t[1]) {const i=idx(s[1]);return {rendererId:'bar-model',barIndex:i,delta:signed(t[2]),existingBlocks:scene.blocks[i]??NaN,maxBlocks:scene.maxBlocks[i]??NaN};}
      return null;
    }
    case 'array-board': {
      if((sourceKey==='row'||sourceKey==='col')&&t[0]===sourceKey)return {rendererId:'array-board',edge:sourceKey,delta:signed(t[1]),current:sourceKey==='row'?scene.rows:scene.cols,limit:sourceKey==='row'?scene.maxRows:scene.maxCols};
      return null;
    }
    case 'place-value': {
      if(s[0]!=='pool'||t[0]!=='slot')return null;
      return {rendererId:'place-value',sourcePoolIndex:idx(s[1]),pickedPoolIndex:scene.pickedPoolIndex,targetSlotIndex:idx(t[1]),slotCount:scene.slots.length};
    }
    case 'sorting-board': {
      if(s[0]!=='card'||t[0]!=='target')return null;
      const from=scene.cards[idx(s[1])],to=scene.cards[idx(t[1])];if(!from||!to)return null;
      return {rendererId:'sorting-board',sourceCardId:from.id,selectedCardId:scene.selectedCardId,targetCardId:to.id,cardIds:scene.cards.map(c=>c.id)};
    }
    case 'number-line': {
      if(sourceKey!=='cursor'||t[0]!=='tick')return null;
      return {rendererId:'number-line',currentTick:scene.currentTick,targetTick:signed(t[1]),minTick:scene.minTick,maxTick:scene.maxTick};
    }
    case 'ruler': {
      if(s[0]!=='mark'||t[0]!=='tick')return null;
      return {rendererId:'ruler',mark:idx(s[1])===0?0:1,targetTick:signed(t[1]),tickMin:scene.minTick,tickMax:scene.maxTick,allowedTickStep:scene.step};
    }
    case 'direction-grid': {
      if(sourceKey!=='cursor'||t[0]!=='cell')return null;
      return {rendererId:'direction-grid',current:scene.current,target:{r:idx(t[1]),c:idx(t[2])},rows:scene.rows,cols:scene.cols};
    }
    case 'shape-canvas': {
      if(sourceKey!=='pen'||t[0]!=='point')return null;
      return {rendererId:'shape-canvas',point:{x:signed(t[1]),y:signed(t[2])},gridMinX:scene.minX,gridMaxX:scene.maxX,gridMinY:scene.minY,gridMaxY:scene.maxY};
    }
    case 'pattern-board': {
      if(s[0]!=='token'||t[0]!=='blank')return null;
      const i=idx(s[1]),j=idx(t[1]);const token=scene.palette[i];if(token===undefined)return null;
      return {rendererId:'pattern-board',targetIndex:j,blankCount:scene.blanks.length,token,palette:scene.palette,locked:scene.blanks[j]?.locked??true};
    }
    case 'shape-gallery': {
      if(s[0]!=='shape'||(targetKey!=='home'&&targetKey!=='return'))return null;
      const shape=scene.shapes[idx(s[1])];if(!shape)return null;
      return {rendererId:'shape-gallery',sourceShapeId:shape.id,selectedShapeId:scene.selectedShapeId,target:targetKey==='home'?'home':'return-tray',currentlyAtHome:scene.homeIds.includes(shape.id)};
    }
    case 'estimation-canvas': {
      if(sourceKey!=='estimate'||targetKey!=='range'||normalizedPosition===undefined||
          !Number.isFinite(normalizedPosition)||!Number.isFinite(scene.min)||!Number.isFinite(scene.max)||
          scene.max<=scene.min||!Number.isFinite(scene.step)||scene.step<=0)return null;
      const v=scene.min+(scene.max-scene.min)*Math.max(0,Math.min(1,normalizedPosition));
      const snapped=scene.min+Math.round((v-scene.min)/scene.step)*scene.step;
      return {rendererId:'estimation-canvas',estimate:Math.max(scene.min,Math.min(scene.max,snapped)),min:scene.min,max:scene.max,step:scene.step};
    }
  }
}

/** An actual child selection click. Never invoke to simulate a hidden precursor step. */
export function a5ExplicitSelection(scene:A5Scene, selectionKey:string):DomainCommand|null {
  const layout=buildA5Scene(scene);
  if (!layout.explicitSelections.some(s=>s.id===selectionKey))return null;
  const parts=selectionKey.split(':');let operation:string|undefined;let args:Readonly<Record<string,string|number|boolean|null>>={};
  switch(scene.rendererId){
    case 'formula-board': operation='applyActivate'; args={slotId:selectionKey.slice(7)};break;
    case 'place-value':operation='applyPick';args={poolIndex:idx(parts[1])};break;
    case 'sorting-board':{const card=scene.cards[idx(parts[1])];if(!card)return null;operation='applySelectCard';args={cardId:card.id};break;}
    case 'shape-gallery':{const shape=scene.shapes[idx(parts[1])];if(!shape)return null;operation='applySelect';args={shapeId:shape.id};break;}
    default:return null;
  }
  if (!(A5_DOMAIN_ACTIONS[scene.rendererId] as readonly string[]).includes(operation))return null;
  return {rendererId:scene.rendererId,operation,args,evidenceOwner:'existing-domain'};
}
