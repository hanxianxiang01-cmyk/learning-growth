"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { InteractionEvent, TaskResponse, V2RendererWorkspace, V2TaskUiSchema } from "@/src/lib/api/contracts";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  workspace: V2RendererWorkspace;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

type EventName = string;
type State = Record<string, unknown>;

const asNumber = (value: unknown, fallback: number) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};
const asString = (value: unknown, fallback = "") => typeof value === "string" ? value : fallback;
const asArray = <T,>(value: unknown, fallback: T[] = []) => Array.isArray(value) ? value as T[] : fallback;
const labels = (config: State, key: string, fallback: string[]) => asArray<string>(config[key], fallback);

function makeEvent(taskInstanceId: string, renderer: string, event_type: EventName, payload: Record<string, unknown> = {}) {
  return {
    event_id: `${renderer}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    event_type,
    occurred_at: new Date().toISOString(),
    task_instance_id: taskInstanceId,
    renderer_id: renderer,
    capability_id: event_type.toLowerCase(),
    payload: Object.fromEntries(Object.entries(payload).map(([k, v]) => [k, typeof v === "number" || typeof v === "boolean" || typeof v === "string" ? v : JSON.stringify(v)])),
  } as InteractionEvent;
}

function useRendererState(props: Props, initial: State) {
  const { taskInstanceId, workspace, response, onResponseChange } = props;
  const renderer = workspace.renderer;
  const revision = props.schema.ui_revision;
  const stored = response.v2_workspaces?.find(w => w.workspace_id === workspace.workspace_id)?.data;
  const initialState = (stored?.state as State | undefined) ?? (workspace.initial_state as State) ?? initial;
  const [state, setState] = useState<State>(initialState);
  const lastRevision = useRef(revision);
  const lastWorkspace = useRef(workspace.workspace_id);

  useEffect(() => {
    if (lastRevision.current !== revision || lastWorkspace.current !== workspace.workspace_id) {
      setState(((workspace.initial_state as State) ?? initial));
      lastRevision.current = revision;
      lastWorkspace.current = workspace.workspace_id;
    }
  }, [revision, workspace.workspace_id, workspace.initial_state, initial]);

  const commit = (next: State, eventType: string, payload: Record<string, unknown> = {}) => {
    setState(next);
    const data = { state: next, present: next };
    const workspaces = [...(response.v2_workspaces ?? []).filter(w => w.workspace_id !== workspace.workspace_id), { workspace_id: workspace.workspace_id, data }];
    const events = [...(response.interaction_events ?? []), makeEvent(taskInstanceId, renderer, eventType, payload)].slice(-100);
    const answer = answerFromState(renderer, next);
    onResponseChange({
      ...response,
      answer,
      interaction_events: events,
      v2_workspaces: workspaces,
      v2_response_type: props.schema.response_contract.response_type,
      v2_ui_revision: revision,
    });
  };

  const reset = () => commit(((workspace.initial_state as State) ?? initial), "RESET");
  const update = (patch: State, eventType: string, payload?: Record<string, unknown>) => commit({ ...state, ...patch }, eventType, payload);
  return { state, update, reset };
}

function answerFromState(renderer: string, state: State): string {
  if (typeof state.answer === "string") return state.answer;
  if (state.answer !== undefined && state.answer !== null) return String(state.answer);
  if (renderer === "choice-grid") return asArray<string>(state.selected, []).join(",");
  if (renderer === "place-value") return String(state.digits ?? "");
  if (renderer === "ten-frame") return String(state.count ?? "");
  if (renderer === "array-board") return `${state.rows ?? ""}×${state.columns ?? ""}`;
  if (renderer === "grouping-board") return String(state.groups ?? "");
  if (renderer === "formula-board") return asString(state.formula);
  if (renderer === "estimation-canvas") return String(state.estimate ?? "");
  if (renderer === "shape-gallery") return asString(state.selectedShape);
  if (renderer === "shape-canvas") return asString(state.shape);
  if (renderer === "sorting-board") return asArray<string>(state.order, []).join(",");
  if (renderer === "direction-grid") return asString(state.direction);
  if (renderer === "ruler") return String(state.value ?? "");
  if (renderer === "clock") return asString(state.time);
  if (renderer === "timeline") return asArray<string>(state.order, []).join(",");
  if (renderer === "money-board") return String(state.amount ?? "");
  if (renderer === "data-table") return JSON.stringify(state.cells ?? {});
  if (renderer === "pictograph") return asString(state.answer);
  if (renderer === "pattern-board") return asArray<string | number>(state.values, []).join(",");
  return "";
}

function Shell({ props, children, title, onReset }: { props: Props; children?: ReactNode; title: string; onReset: () => void }) {
  const answer = props.response.answer?.trim();
  return <section className="renderer-v2-shell" data-renderer={props.workspace.renderer} data-testid={`renderer-${props.workspace.renderer}`}>
    <div className="renderer-v2-prompt">{props.schema.prompt.text}</div>
    <div className="renderer-v2-head"><strong>{title}</strong><span className="renderer-v2-version">V2 · {props.workspace.workspace_id}</span></div>
    <div className="renderer-v2-body">{children}</div>
    <div className="renderer-v2-actions">
      <button type="button" className="secondary-button" disabled={props.disabled} onClick={onReset}>重置</button>
      <span className="renderer-v2-answer">答案：{answer || "待填写"}</span>
      <button type="button" className="primary-button" disabled={props.disabled || !answer} onClick={props.onSubmit}>提交</button>
    </div>
  </section>;
}

export function ChoiceGrid(props: Props) {
  const config = props.workspace.config; const multi = Boolean(config.multi_select); const options = labels(config, "options", ["A", "B", "C"]);
  const { state, update, reset } = useRendererState(props, { selected: [] }); const selected = asArray<string>(state.selected, []);
  const toggle = (option: string) => { const next = multi ? (selected.includes(option) ? selected.filter(x => x !== option) : [...selected, option]) : [option]; update({ selected: next }, selected.includes(option) ? "OPTION_DESELECTED" : "OPTION_SELECTED", { option }); };
  return <Shell props={props} title="选择网格" onReset={reset}><div className="renderer-choice-grid">{options.map(o => <button key={o} type="button" className={selected.includes(o) ? "choice selected" : "choice"} disabled={props.disabled} onClick={() => toggle(o)}>{o}</button>)}</div><small>{multi ? "可多选" : "请选择一个答案"}</small></Shell>;
}

export function PlaceValue(props: Props) {
  const config = props.workspace.config; const places = labels(config, "places", ["千", "百", "十", "个"]); const target = asString(config.target, "2305");
  const { state, update, reset } = useRendererState(props, { digits: target }); const digits = asString(state.digits, target).padStart(places.length, "0").slice(-places.length);
  return <Shell props={props} title="位值板" onReset={reset}><div className="renderer-place-value">{places.map((p, i) => <label key={p}><span>{p}</span><input inputMode="numeric" value={digits[i] ?? ""} disabled={props.disabled} onChange={e => { const v = e.target.value.replace(/\D/g, "").slice(-1); const next = digits.split(""); next[i] = v; update({ digits: next.join("") }, "VALUE_CHANGED", { place: p, value: v }); }} /></label>)}</div><div className="renderer-place-number">{digits}</div></Shell>;
}

export function TenFrame(props: Props) {
  const config = props.workspace.config; const target = asNumber(config.target_count ?? config.target, 10); const { state, update, reset } = useRendererState(props, { count: asNumber(config.initial_count, 0) }); const count = asNumber(state.count, 0);
  return <Shell props={props} title="十格框" onReset={reset}><div className="renderer-ten-frame">{Array.from({ length: 10 }, (_, i) => <button key={i} type="button" className={i < count ? "cell filled" : "cell"} disabled={props.disabled} onClick={() => update({ count: i < count ? i : i + 1 }, i < count ? "COUNTER_REMOVED" : "COUNTER_ADDED", { index: i })}>{i < count ? "●" : "○"}</button>)}</div><small>目标：{target}　当前：{count}</small></Shell>;
}

export function ArrayBoard(props: Props) {
  const config = props.workspace.config; const { state, update, reset } = useRendererState(props, { rows: asNumber(config.rows, 3), columns: asNumber(config.columns, 4) }); const rows = Math.max(1, asNumber(state.rows, 1)); const columns = Math.max(1, asNumber(state.columns, 1));
  return <Shell props={props} title="阵列板" onReset={reset}><div className="renderer-array-controls"><label>行 <input type="number" min="1" max="10" value={rows} disabled={props.disabled} onChange={e => update({ rows: Number(e.target.value) }, "ROW_CHANGED")} /></label><label>列 <input type="number" min="1" max="10" value={columns} disabled={props.disabled} onChange={e => update({ columns: Number(e.target.value) }, "COLUMN_CHANGED")} /></label></div><div className="renderer-array-board" style={{ gridTemplateColumns: `repeat(${columns}, 28px)` }}>{Array.from({ length: rows * columns }, (_, i) => <span key={i}>●</span>)}</div><small>{rows} × {columns} = {rows * columns}</small></Shell>;
}

export function GroupingBoard(props: Props) {
  const config = props.workspace.config; const items = asNumber(config.items, 12); const { state, update, reset } = useRendererState(props, { groups: asNumber(config.groups, 3) }); const groups = Math.max(1, Math.min(items, asNumber(state.groups, 1))); const per = Math.floor(items / groups); const remainder = items % groups;
  return <Shell props={props} title="分组板" onReset={reset}><div className="renderer-group-controls"><button type="button" disabled={props.disabled || groups <= 1} onClick={() => update({ groups: groups - 1 }, "GROUP_REMOVED")}>−</button><strong>{groups} 组</strong><button type="button" disabled={props.disabled || groups >= items} onClick={() => update({ groups: groups + 1 }, "GROUP_CREATED")}>＋</button></div><div className="renderer-groups">{Array.from({ length: groups }, (_, i) => <div key={i}>{Array.from({ length: per + (i < remainder ? 1 : 0) }, (_, j) => <span key={j}>●</span>)}</div>)}</div><small>{items} 个对象 · 每组约 {per} · 余 {remainder}</small></Shell>;
}

export function FormulaBoard(props: Props) {
  const config = props.workspace.config; const initial = asString(config.formula, "3 + 4 = 7"); const { state, update, reset } = useRendererState(props, { formula: initial });
  return <Shell props={props} title="公式板" onReset={reset}><input className="renderer-formula-input" value={asString(state.formula, initial)} disabled={props.disabled} onChange={e => update({ formula: e.target.value }, "VALUE_CHANGED")} placeholder="输入算式" /><small>用算式表达数量关系。</small></Shell>;
}

export function EstimationCanvas(props: Props) {
  const config = props.workspace.config; const target = asNumber(config.target, 100); const { state, update, reset } = useRendererState(props, { estimate: asNumber(config.initial_estimate, 0) });
  return <Shell props={props} title="估算画布" onReset={reset}><input type="range" min={0} max={Math.max(target * 2, 10)} value={asNumber(state.estimate, 0)} disabled={props.disabled} onChange={e => update({ estimate: Number(e.target.value) }, "VALUE_CHANGED")} /><div className="renderer-estimate-value">{asNumber(state.estimate, 0)}</div><small>参考量：{target}</small></Shell>;
}

export function ShapeGallery(props: Props) {
  const shapes = labels(props.workspace.config, "shapes", ["圆形", "三角形", "正方形", "长方形"]); const { state, update, reset } = useRendererState(props, { selectedShape: "" });
  return <Shell props={props} title="图形画廊" onReset={reset}><div className="renderer-shape-grid">{shapes.map(shape => <button key={shape} type="button" className={state.selectedShape === shape ? "shape selected" : "shape"} disabled={props.disabled} onClick={() => update({ selectedShape: shape }, "SHAPE_SELECTED", { shape })}>{shape}</button>)}</div></Shell>;
}

export function ShapeCanvas(props: Props) {
  const { state, update, reset } = useRendererState(props, { shape: asString(props.workspace.config.initial_shape, "正方形"), size: asNumber(props.workspace.config.initial_size, 80), x: 50, y: 50 });
  const size = Math.max(30, Math.min(180, asNumber(state.size, 80)));
  return <Shell props={props} title="图形画布" onReset={reset}><div className="renderer-shape-canvas"><div className="shape-canvas-object" style={{ width: size, height: size, borderRadius: state.shape === "圆形" ? "50%" : 8 }} onClick={() => update({ size: size >= 180 ? 40 : size + 20 }, "RESIZED")}>{asString(state.shape, "正方形")}</div></div><div className="renderer-canvas-tools"><button type="button" disabled={props.disabled} onClick={() => update({ x: asNumber(state.x, 50) - 10 }, "MOVED")}>←</button><button type="button" disabled={props.disabled} onClick={() => update({ x: asNumber(state.x, 50) + 10 }, "MOVED")}>→</button><span>尺寸 {size}</span></div></Shell>;
}

export function SortingBoard(props: Props) {
  const items = labels(props.workspace.config, "items", ["2", "4", "1", "3"]); const { state, update, reset } = useRendererState(props, { order: items }); const order = asArray<string>(state.order, items);
  const move = (i: number, d: number) => { const j = i + d; if (j < 0 || j >= order.length) return; const next = [...order]; [next[i], next[j]] = [next[j], next[i]]; update({ order: next }, "ORDER_CHANGED", { from: i, to: j }); };
  return <Shell props={props} title="排序板" onReset={reset}><div className="renderer-sort-list">{order.map((x, i) => <div key={`${x}-${i}`}><span>{x}</span><button type="button" disabled={props.disabled || i === 0} onClick={() => move(i, -1)}>↑</button><button type="button" disabled={props.disabled || i === order.length - 1} onClick={() => move(i, 1)}>↓</button></div>)}</div></Shell>;
}

export function DirectionGrid(props: Props) {
  const { state, update, reset } = useRendererState(props, { direction: "" }); const dirs = ["上", "下", "左", "右"];
  return <Shell props={props} title="方向网格" onReset={reset}><div className="renderer-direction-grid">{dirs.map(d => <button key={d} type="button" className={state.direction === d ? "selected" : ""} disabled={props.disabled} onClick={() => update({ direction: d }, "DIRECTION_SELECTED", { direction: d })}>{d}</button>)}</div></Shell>;
}

export function Ruler(props: Props) {
  const max = asNumber(props.workspace.config.max, 20); const step = asNumber(props.workspace.config.step, 1); const { state, update, reset } = useRendererState(props, { value: 0 });
  return <Shell props={props} title="尺子" onReset={reset}><div className="renderer-ruler"><div className="ruler-line">{Array.from({ length: Math.floor(max / step) + 1 }, (_, i) => <span key={i}>{i * step}</span>)}</div><input type="range" min="0" max={max} step={step} value={asNumber(state.value, 0)} disabled={props.disabled} onChange={e => update({ value: Number(e.target.value) }, "MEASURE_CHANGED")} /></div><strong>读数：{asNumber(state.value, 0)}</strong></Shell>;
}

export function Clock(props: Props) {
  const { state, update, reset } = useRendererState(props, { time: asString(props.workspace.config.initial_time, "03:00") });
  return <Shell props={props} title="时钟" onReset={reset}><input type="time" value={asString(state.time, "03:00")} disabled={props.disabled} onChange={e => update({ time: e.target.value }, "TIME_CHANGED")} /><div className="renderer-clock-face">{asString(state.time, "03:00")}</div></Shell>;
}

export function Timeline(props: Props) {
  const events = labels(props.workspace.config, "events", ["起点", "事件 A", "事件 B", "终点"]); const { state, update, reset } = useRendererState(props, { order: events }); const order = asArray<string>(state.order, events);
  return <Shell props={props} title="时间线" onReset={reset}><div className="renderer-timeline">{order.map((e, i) => <div key={`${e}-${i}`}><span>{i + 1}</span><strong>{e}</strong></div>)}</div><button type="button" className="secondary-button" disabled={props.disabled || order.length < 2} onClick={() => update({ order: [...order].reverse() }, "ORDER_CHANGED")}>前后调整</button></Shell>;
}

export function MoneyBoard(props: Props) {
  const denominations = asArray<number>(props.workspace.config.denominations, [1, 5, 10]); const { state, update, reset } = useRendererState(props, { amount: 0, counts: {} }); const counts = (state.counts ?? {}) as Record<string, number>;
  const amount = denominations.reduce((sum, d) => sum + d * asNumber(counts[String(d)], 0), 0);
  return <Shell props={props} title="货币板" onReset={reset}><div className="renderer-money-grid">{denominations.map(d => <button key={d} type="button" disabled={props.disabled} onClick={() => { const next: Record<string, number> = { ...counts, [d]: asNumber(counts[String(d)], 0) + 1 }; const nextAmount = denominations.reduce((sum, value) => sum + value * asNumber(next[String(value)], 0), 0); update({ counts: next, amount: nextAmount }, "MONEY_ADDED", { denomination: d }); }}>¥{d}<small> × {counts[String(d)] ?? 0}</small></button>)}</div><strong>金额：¥{amount}</strong></Shell>;
}

export function DataTable(props: Props) {
  const rows = asArray<string>(props.workspace.config.rows, ["A", "B", "C", "D"]); const cols = asArray<string>(props.workspace.config.columns, ["数量"]); const { state, update, reset } = useRendererState(props, { cells: {} }); const cells = (state.cells ?? {}) as Record<string, string>;
  return <Shell props={props} title="数据表" onReset={reset}><table className="renderer-data-table"><thead><tr><th>项目</th>{cols.map(c => <th key={c}>{c}</th>)}</tr></thead><tbody>{rows.map(r => <tr key={r}><th>{r}</th>{cols.map(c => { const key = `${r}:${c}`; return <td key={key}><input value={cells[key] ?? ""} disabled={props.disabled} inputMode="numeric" onChange={e => update({ cells: { ...cells, [key]: e.target.value } }, "CELL_EDITED", { key })} /></td>; })}</tr>)}</tbody></table></Shell>;
}

export function Pictograph(props: Props) {
  const items = asArray<{ label: string; value: number }>(props.workspace.config.items, [{ label: "苹果", value: 4 }, { label: "香蕉", value: 6 }, { label: "橙子", value: 2 }]); const scale = asNumber(props.workspace.config.scale, 2); const { state, update, reset } = useRendererState(props, { selected: "" });
  return <Shell props={props} title="象形统计图" onReset={reset}><small>图例：● = {scale}</small><div className="renderer-pictograph">{items.map(item => <button key={item.label} type="button" className={state.selected === item.label ? "selected" : ""} disabled={props.disabled} onClick={() => update({ selected: item.label, answer: String(item.value) }, "DATA_POINT_SELECTED", { label: item.label, value: item.value })}><span>{item.label}</span><span>{"●".repeat(Math.ceil(item.value / scale))}</span></button>)}</div></Shell>;
}

export function PatternBoard(props: Props) {
  const initial = asArray<string | number>(props.workspace.config.values, [2, 4, 6, 8, "", ""]); const { state, update, reset } = useRendererState(props, { values: initial }); const values = asArray<string | number>(state.values, initial);
  return <Shell props={props} title="规律板" onReset={reset}><div className="renderer-pattern">{values.map((v, i) => <input key={i} value={String(v)} disabled={props.disabled} onChange={e => { const next = [...values]; next[i] = e.target.value; update({ values: next }, "BLANK_FILLED", { index: i }); }} />)}</div><small>观察相邻项，补全规律并验证。</small></Shell>;
}

export const V2_RENDERER_COMPONENTS = {
  "choice-grid": ChoiceGrid,
  "place-value": PlaceValue,
  "ten-frame": TenFrame,
  "array-board": ArrayBoard,
  "grouping-board": GroupingBoard,
  "formula-board": FormulaBoard,
  "estimation-canvas": EstimationCanvas,
  "shape-gallery": ShapeGallery,
  "shape-canvas": ShapeCanvas,
  "sorting-board": SortingBoard,
  "direction-grid": DirectionGrid,
  "ruler": Ruler,
  "clock": Clock,
  "timeline": Timeline,
  "money-board": MoneyBoard,
  "data-table": DataTable,
  "pictograph": Pictograph,
  "pattern-board": PatternBoard,
} as const;
