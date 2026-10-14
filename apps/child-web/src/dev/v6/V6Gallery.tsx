"use client";

import { useState } from "react";
import { ChildSkinProvider } from "@/src/theme/ChildSkinProvider";
import type { ChildMathSkin } from "@/src/theme/skins";
import type { TaskInstance, TaskResponse } from "@/src/lib/api/contracts";
import { TaskRenderer, createEmptyTaskResponse } from "@/src/features/task-renderer/TaskRenderer";
import fixtureData from "./fixtures.json";

/** DEV ONLY. Twenty original examples cover nineteen renderers (formula has two modes).
 * No scoring, seed, database write, or simulated feedback belongs in this component. */
export const V6_FIXTURES = fixtureData as Array<{ id: string; renderer: string; title: string; expected: string; task: TaskInstance }>;

function Workspace({ task, locked }: { task: TaskInstance; locked: boolean }) {
  const [response, setResponse] = useState<TaskResponse>(() => createEmptyTaskResponse());
  const [submission, setSubmission] = useState<TaskResponse | null>(null);
  return <>
    <div className="v6-task-content"><TaskRenderer task={task} response={response} disabled={locked}
      onResponseChange={setResponse} onSubmit={() => setSubmission(structuredClone(response))} /></div>
    <details className="v6-dev-payload"><summary>开发者报文观察（不判分、不落库）</summary>
      <pre data-testid="v6-gallery-response">{JSON.stringify(response, null, 2)}</pre>
      <h3>最近捕获的提交</h3><pre data-testid="v6-gallery-submission">{JSON.stringify(submission, null, 2)}</pre>
    </details>
  </>;
}
export function V6Gallery() {
  const [skin, setSkin] = useState<ChildMathSkin>("exploration-lab");
  const [index, setIndex] = useState(0);
  const [locked, setLocked] = useState(false);
  const [epoch, setEpoch] = useState(0);
  const fixture = V6_FIXTURES[index];
  return <section className="v6-dev-gallery" data-testid="v6-gallery">
    <h1>V6 全量工作区 · DEV ONLY</h1><p className="v6-dev-note">19个 Renderer，20个原仓库示例。切换皮肤不重置操作；切换题目或重新开始会清空工作区。这里只捕获实际组件提交的报文，不代替后端判分或核验落库。</p>
    <div className="v6-dev-toolbar">
      <label>示例<select data-testid="v6-gallery-renderer" value={index} onChange={e => { setIndex(Number(e.target.value)); setLocked(false); }}>
        {V6_FIXTURES.map((item, i) => <option key={item.id} value={i}>{item.renderer} · {item.task.ui_schema.schema_version === "2.0" ? item.task.ui_schema.workspaces[0].mode : ""}</option>)}</select></label>
      <label>皮肤<select data-testid="v6-gallery-skin" value={skin} onChange={e => setSkin(e.target.value as ChildMathSkin)}><option value="exploration-lab">探索实验室</option><option value="healing">轻量治愈</option></select></label>
      <label><span>交互锁定</span><input type="checkbox" data-testid="v6-gallery-lock" checked={locked} onChange={e => setLocked(e.target.checked)} /></label>
      <button type="button" data-testid="v6-gallery-reset" onClick={() => { setEpoch(n => n + 1); setLocked(false); }}>重新开始示例</button>
    </div>
    <ChildSkinProvider skin={skin} uiVersion="v6"><Workspace key={`${index}-${epoch}`} task={fixture.task} locked={locked} /></ChildSkinProvider>
  </section>;
}
