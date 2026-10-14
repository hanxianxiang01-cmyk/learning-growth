'use client';

/** Genuine alternate view/interaction for R04, not another scorer.
 * Reuses frozen R04 config parsing, answer serializer and event format.
 * No attempt to migrate the other 18 Renderers in this technical spike.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import type { TaskResponse, V2TaskUiSchema, InteractionEvent } from '@/src/lib/api/contracts';
import { buildRendererEvent } from '@/src/features/task-renderer/rendererRuntime';
import { parseAnswer, parseNumberInputConfig, serializeNumberInputV2 } from '@/src/components/renderers/NumberInputV2';

type Props={
 taskInstanceId:string;schema:V2TaskUiSchema;response:TaskResponse;disabled?:boolean;
 onResponseChange:(response:TaskResponse)=>void;onSubmit:()=>void;
};

export function NumberInputKernelPilot({taskInstanceId,schema,response,disabled,onResponseChange,onSubmit}:Props){
 const workspace=schema.workspaces[0];
 const config=useMemo(()=>parseNumberInputConfig((workspace?.config??{}) as Record<string,unknown>),[workspace]);
 const [text,setText]=useState('');
 const [events,setEvents]=useState<InteractionEvent[]>([]);
 const history=useRef<Array<{text:string;at:string}>>([]);
 const responseRef=useRef(response); responseRef.current=response;
 const revision=useRef(schema.ui_revision);
 useEffect(()=>{
  if(revision.current===schema.ui_revision)return;
  revision.current=schema.ui_revision;setText('');setEvents([]);history.current=[];
 },[schema.ui_revision]);
 const answer=parseAnswer(text,config);
 useEffect(()=>{
  if(!workspace)return;
  onResponseChange({...responseRef.current,answer:answer===null?'':String(answer),
   interaction_events:events,
   v2_workspaces:[{workspace_id:workspace.workspace_id,data:serializeNumberInputV2(answer,history.current)}],
   v2_response_type:schema.response_contract.response_type,v2_ui_revision:schema.ui_revision});
 },[answer,events,workspace,schema.response_contract.response_type,schema.ui_revision]);
 if(!workspace || workspace.renderer!=='number-input')return <div className="surface-card unsupported-task">数字题配置尚未准备好。</div>;
 function enter(next:string){
  if(disabled)return;
  const cleaned=config.integerOnly?next.replace(/[^\d-]/g,''):next.replace(/[^\d.\-]/g,'');
  setText(cleaned);history.current=[...history.current,{text:cleaned,at:new Date().toISOString()}].slice(-20);
  setEvents(previous=>[...previous,buildRendererEvent('NUMBER_INPUT_CHANGED',{
    task_instance_id:taskInstanceId,workspace_id:workspace.workspace_id,renderer_id:'number-input',
    capability_id:'answer_input',payload:{text:cleaned}})].slice(-100));
 }
 return <section className="manipulative-card" data-testid="number-input-kernel-pilot">
  <div className="manipulative-heading"><strong>写出答案</strong><span>在这里写下你算出的数。</span></div>
  <div className="ni-field" style={{maxWidth:360,margin:'20px auto',display:'grid',gap:12}}>
   <label htmlFor="mik-number-answer">我的答案</label>
   <input id="mik-number-answer" data-testid="mik-number-answer" type="text" inputMode={config.integerOnly?'numeric':'decimal'} autoComplete="off"
    value={text} onChange={e=>enter(e.target.value)} disabled={disabled} aria-describedby="mik-number-help" />
   <div id="mik-number-help" aria-live="polite">{text.trim()===''?'先写下一个数字':answer===null?'再检查一下数字格式':'可以修改，也可以提交'}</div>
   <button type="button" onClick={()=>enter('')} disabled={disabled||text===''}>清除</button>
   <button type="button" data-testid="mik-number-submit" onClick={onSubmit} disabled={disabled||answer===null}>提交我的答案</button>
  </div>
 </section>;
}
