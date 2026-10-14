'use client';
/**
 * MIK-A5: a natural-control surface mounted inside each EXISTING V6 Renderer.
 * Each handler delegates to that renderers' existing domain action / native
 * reducer / original semantic event; this file never creates or scores answers.
 * Opt-in only via the task-pinned implementation Router.
 */
import { useMemo } from 'react';
import { A5NaturalControls } from './A5NaturalControls';
import { buildA5LiveScene, canApplyA5Domain, type A5ActiveId } from './a5DomainIntegration';
import type { DomainCommand, A5Context } from './naturalIntent';

export type A5HandlerArgs = DomainCommand['args'];
export type A5DomainHandlers = Readonly<Record<string,(args:A5HandlerArgs)=>void>>;
export function A5LivePanel({rendererId,state,config,handlers,taskInstanceId,uiRevision,disabled}:{
 rendererId:A5ActiveId;
 state:unknown;config:unknown;handlers:A5DomainHandlers;
 taskInstanceId:string;uiRevision:string|number;disabled?:boolean;
}){
 const scene=useMemo(()=>buildA5LiveScene(rendererId,state,config),[rendererId,state,config]);
 const context:A5Context={taskInstanceId,activeTaskInstanceId:taskInstanceId,
   uiRevision,activeUiRevision:uiRevision,disabled:!!disabled,modality:'pointer'};
 const canApply=(command:DomainCommand)=>
   !disabled && Object.prototype.hasOwnProperty.call(handlers,command.operation) &&
   canApplyA5Domain(rendererId,state,config,command);
 const onDomainCommand=(command:DomainCommand)=>{
   // Verify against LATEST state again before invoking an action. Unknown
   // operation cannot fall through to an implicit click/synthetic selection.
   if(!canApply(command))return;
   handlers[command.operation](command.args);
 };
 return <A5NaturalControls scene={scene} context={context} canApply={canApply}
   onDomainCommand={onDomainCommand}/>;
}
