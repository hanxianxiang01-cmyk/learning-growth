import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");
const assert = (ok, msg) => { if (!ok) throw new Error(`V1.4 contract test failed: ${msg}`); };
const registry = read("src/features/task-renderer/rendererRegistry.ts");
const runtime = read("src/features/task-renderer/rendererContract.ts");
const evaluator = read("src/features/task-renderer/evaluatorRegistry.ts");
const taskRenderer = read("src/features/task-renderer/TaskRenderer.tsx");
const adapter = read("src/lib/api/v2AttemptAdapter.ts");
const contracts = read("src/lib/api/contracts.ts");
const release = [
  "object-counter","bar-model","number-line","number-input","column-arithmetic","place-value",
  "ten-frame","array-board","grouping-board","formula-board","estimation-canvas","shape-gallery",
  "shape-canvas","sorting-board","direction-grid","ruler","clock","money-board","pattern-board"
];
assert(runtime.includes("RENDERER_STATES") && runtime.includes("canTransition"), "state contract missing");
assert(runtime.includes("createSemanticEvent") && runtime.includes("buildRendererEvidence"), "semantic event/evidence contract missing");
assert(evaluator.includes("RENDERER_EVALUATORS"), "evaluator registry missing");
// SAFE-01 P2: V2 契约入口校验在 TaskRenderer；提交时刻仅注入 Evidence。
// 后端独占 Judge/正确性/分数与 Mastery；禁止随请求透传本地 evaluation。
assert(taskRenderer.includes("assertTaskUiSchemaV2"), "TaskUISchema gate missing in TaskRenderer");
assert(adapter.includes("buildRendererEvidence") && adapter.includes("runtime_status"), "SAFE-01 submit-time evidence missing");
assert(!adapter.includes("getRendererEvaluator") && !/\bevaluation\s*[:,=]\s*getRendererEvaluator/.test(adapter), "SAFE-01 local evaluation must not be submitted");
assert(adapter.includes("stableSubmissionId") && adapter.includes("request.submission_id ??"), "submission id is not stable/idempotent");
assert(adapter.includes("|${attemptNo}|"), "submission id must depend on attempt_no (no cross-retry collision)");
assert(contracts.includes("submission_id?: string"), "submission_id missing from AttemptRequest");
for (const id of release) assert(registry.includes(`"${id}"`), `release renderer missing: ${id}`);
console.log(`V1.4 contract tests: PASS (${release.length}/19 release renderers)`);
