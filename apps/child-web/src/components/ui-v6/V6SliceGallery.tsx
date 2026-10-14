"use client";

import { useState } from "react";
import { ChildSkinProvider } from "@/src/theme/ChildSkinProvider";
import type { ChildMathSkin } from "@/src/theme/skins";
import type { ChildUiVersion } from "@/src/theme/uiVersion";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import { ClockV2 } from "@/src/components/renderers/ClockV2";
import { MathQuestionCard } from "@/src/components/learning/MathQuestionCard";

/** DEV ONLY: mirrors the repository's V2-R17-CLOCK-001 config, not a new production seed. */
const schema: V2TaskUiSchema = {
  schema_version: "2.0", ui_revision: "v6-gallery-clock-1",
  prompt: { text: "钟面现在是3点整，请把时针和分针拨到6点整。" },
  workspaces: [{
    workspace_id: "clock_main", renderer: "clock", renderer_version: "2.0",
    mode: "time_setting", config: { start: [3, 0], target: [6, 0] },
    initial_state: { h: 3, m: 0, adjust_history: [] },
    capabilities: ["set_time", "answer_input", "undo", "reset"]
  }],
  response_contract: { response_type: "clock", required_fields: ["h", "m", "adjust_history"], evidence_targets: ["h", "m", "adjust_history", "structure"] }
};

export function V6SliceGallery() {
  const [skin, setSkin] = useState<ChildMathSkin>("exploration-lab");
  const [version, setVersion] = useState<ChildUiVersion>("v6");
  const [response, setResponse] = useState<TaskResponse>({ schema_version: "1.0", answer: "", interaction_events: [] });
  const [submission, setSubmission] = useState<TaskResponse | null>(null);
  const [locked, setLocked] = useState(false);

  return <section className="ui-kit-preview" data-testid="v6-gallery">
    <header className="ui-kit-label"><h2>V6 Clock 迁移检查区 · DEV ONLY</h2>
      <p>以下切换器仅用于开发评审，不进入儿童正式页。提交仅捕获报文，不模拟正确／错误，也不写入学习记录。皮肤切换应保留操作，UI版本切换会重置组件。</p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
        <label>皮肤 <select value={skin} onChange={e => setSkin(e.target.value as ChildMathSkin)} data-testid="v6-gallery-skin"><option value="exploration-lab">探索实验室</option><option value="healing">轻量治愈</option></select></label>
        <label>界面 <select value={version} onChange={e => setVersion(e.target.value as ChildUiVersion)} data-testid="v6-gallery-version"><option value="v6">V6</option><option value="legacy">Legacy</option></select></label>
        <label><input type="checkbox" checked={locked} onChange={e => setLocked(e.target.checked)} data-testid="v6-gallery-lock" />外部禁用</label>
      </div>
    </header>
    <ChildSkinProvider skin={skin} uiVersion={version}>
      <div className="v6-task-content">
        <MathQuestionCard prompt={schema.prompt.text} />
        <ClockV2 taskInstanceId="v6-dev-gallery-clock" schema={schema} response={response} disabled={locked} onResponseChange={setResponse} onSubmit={() => setSubmission(structuredClone(response))} />
      </div>
    </ChildSkinProvider>
    <details><summary>开发者报文观察（非儿童UI）</summary><pre data-testid="v6-gallery-response" style={{ overflow: "auto", maxHeight: 300 }}>{JSON.stringify(response, null, 2)}</pre><h3>最近捕获的提交</h3><pre data-testid="v6-gallery-submission" style={{ overflow: "auto", maxHeight: 300 }}>{JSON.stringify(submission, null, 2)}</pre></details>
  </section>;
}
