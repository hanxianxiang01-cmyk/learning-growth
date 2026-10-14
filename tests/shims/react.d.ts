/** Strict stand-in only for offline TS API compatibility. Not React types or runtime. */
declare module 'react' {
 export type Dispatch<T> = (next:T|((prev:T)=>T))=>void;
 export type SetStateAction<T> = T|((prev:T)=>T);
 export type ReactNode = any;
 export type MouseEvent<T=HTMLElement> = { detail:number; currentTarget:T; preventDefault():void;stopPropagation():void;target:EventTarget|null };
 export type ChangeEvent<T=HTMLElement> = {currentTarget:T};
 export type KeyboardEvent<T=HTMLElement> = {key:string;currentTarget:T;target:EventTarget|null;preventDefault():void;stopPropagation():void};
 export type PointerEvent<T=HTMLElement> = {pointerId:number;button:number;clientX:number;clientY:number;
   currentTarget:T; target:EventTarget|null;stopPropagation():void; preventDefault():void};
 export function useId():string;
 export function useCallback<T extends (...args:any[])=>any>(value:T,deps:readonly unknown[]):T;
 export function useEffect(fn:()=>void|(()=>void),deps?:readonly unknown[]):void;
 export function useMemo<T>(fn:()=>T,deps:readonly unknown[]):T;
 export function useRef<T>(value:T):{current:T};
 export function useState<T>(init:T|(()=>T)):[T,Dispatch<T>];
}
declare namespace JSX { interface IntrinsicElements { [key:string]: any; } }
declare module 'react/jsx-runtime' { export const Fragment:any; export function jsx(type:any,props:any,key?:string):any;export function jsxs(type:any,props:any,key?:string):any; }
