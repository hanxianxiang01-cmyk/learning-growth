import type { SVGProps } from "react";

const paths = {
  plus: "M5 12h14M12 5v14",
  layers: "m3 8 9-5 9 5-9 5Zm0 5 9 5 9-5M3 18l9 4 9-4",
  grid: "M4 4h16v16H4ZM4 9h16M4 15h16M9 4v16M15 4v16",
  transfer: "M3 7h17m-5-4 5 4-5 4M21 17H4m5-4-5 4 5 4",
  eye: "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Zm10-3a3 3 0 1 0 0 6 3 3 0 0 0 0-6",
  book: "M3 4h6l3 2 3-2h6v15h-6l-3 2-3-2H3Zm9 2v15",
  compass: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm4 5-2 7-7 3 3-7Z",
  search: "M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14Zm5 12 6 6",
  flag: "M5 22V3h14l-3 5 3 5H5",
  clock: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 4v6l5 3",
  ruler: "M3 7h18v10H3Zm4 0v5m4-5v3m4-3v5m4-5v3",
  wallet: "M3 5h16v3H3Zm0 3h18v13H3Zm12 4h6v5h-6Z",
  shapes: "M3 11 7 3l4 8ZM16 3h6v7h-6ZM7 16a3 3 0 1 0 0 6 3 3 0 0 0 0-6ZM15 15h7v7h-7Z",
  document: "M5 2h10l4 4v16H5Zm9 0v5h5M8 11h8M8 15h8M8 19h5",
  spark: "m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z",
  check: "m5 12 4 4L19 6",
  warning: "M12 8v5m0 4h.01M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Z",
  edit: "m14 5 5 5M4 20l4-1L21 6l-3-3L5 16Z",
  arrow: "M4 12h16m-6-6 6 6-6 6",
  back: "M20 12H4m6-6-6 6 6 6",
  hint: "M9 18h6m-6 3h6M8 15a7 7 0 1 1 8 0v2H8Z",
  map: "m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2Zm6-2v16m6-14v16",
  undo: "M9 5 4 10l5 5M4 10h9a6 6 0 0 1 0 12",
  reset: "M20 7V2l-4 4a9 9 0 1 0 4 10M20 7h-5",
  close: "m6 6 12 12M6 18 18 6"
} as const;

export type ChildIconName = keyof typeof paths;
export function ChildIcon({ name, ...props }: SVGProps<SVGSVGElement> & { name: ChildIconName }) {
  return <svg viewBox="0 0 24 24" className="v6-icon" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" {...props}><path d={paths[name]} /></svg>;
}
