import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// pathname 会把非 ASCII 路径 URL 编码（中文目录），必须用 fileURLToPath 解码
const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");
const assert = (condition, message) => {
  if (!condition) throw new Error(`V1.4 contract check failed: ${message}`);
};

const contracts = read("src/lib/api/contracts.ts");
const registry = read("src/features/task-renderer/rendererRegistry.ts");
const workspace = read("src/features/math-workspace/WorkspaceProvider.tsx");
const renderer = read("src/features/task-renderer/TaskRenderer.tsx");
const http = read("src/lib/api/http.ts");

for (const id of ["number-input", "object-counter", "bar-model", "number-line", "unsupported"]) {
  assert(registry.includes(`"${id}"`), `missing renderer ${id}`);
}
assert(contracts.includes("interaction_events?: InteractionEvent[]"), "TaskResponse missing interaction_events");
assert(contracts.includes("renderer_id?: string"), "TaskUISchema missing renderer_id");
assert(contracts.includes("interaction_capabilities?: string[]"), "TaskUISchema missing interaction_capabilities");
assert(workspace.includes("capabilities") && workspace.includes("can("), "Workspace API capability gate missing");
assert(renderer.includes("resolveRendererId") && renderer.includes("getRendererDescriptor"), "TaskRenderer is not registry driven");
assert(http.includes("normalizeAttemptResult") && http.includes("normalizeHintResponse"), "HTTP adapter normalization missing");
assert(fs.existsSync(path.join(root, "app/dev/v1.4-qa/page.tsx")), "V1.4 QA page missing");

// Frontend boundary: no Mastery/Diagnosis calculation may be introduced in renderer/workspace code.
for (const [label, content] of [["renderer", renderer], ["workspace", workspace]]) {
  assert(!/mastery|curriculum_engine|evidence_role|candidate_upgrade|downgrad/i.test(content), `${label} contains forbidden local learning-decision keywords`);
}

console.log("V1.4 frontend contract check: PASS");
