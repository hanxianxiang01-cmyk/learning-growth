import fs from "node:fs";

const required = [
  "src/features/task-renderer/TaskRenderer.tsx",
  "src/features/math-workspace/WorkspaceProvider.tsx",
  "src/features/math-workspace/workspaceReducer.ts",
  "src/components/manipulatives/ObjectCounter.tsx",
  "src/components/manipulatives/BarModel.tsx",
  "src/components/manipulatives/NumberLine.tsx",
  "src/lib/api/taskUiSchemaNormalizer.ts",
  "app/dev/v1.3-qa/page.tsx"
];

const fail = message => { console.error(`V1.3 QA failed: ${message}`); process.exit(1); };
const missing = required.filter(file => !fs.existsSync(file));
if (missing.length) fail(`missing ${missing.join(", ")}`);

const contracts = fs.readFileSync("src/lib/api/contracts.ts", "utf8");
for (const marker of [
  "TaskResponse",
  "WorkspaceUiAction",
  "ObjectCounterRepresentation",
  "BarModelRepresentation",
  "NumberLineRepresentation",
  "ManipulativeTaskUiSchema"
]) {
  if (!contracts.includes(marker)) fail(`contracts missing ${marker}`);
}

const learning = fs.readFileSync("src/screens/MathLearningScreen.tsx", "utf8");
if (!learning.includes("<TaskRenderer")) fail("MathLearningScreen is not using TaskRenderer");

const hook = fs.readFileSync("src/features/learning/useLearningSession.ts", "utf8");
if (!hook.includes("response: state.response")) fail("Attempt does not submit Structured Response");
if (hook.includes("response: state.answer")) fail("legacy primitive answer submit remains");

const mock = fs.readFileSync("src/lib/api/mock.ts", "utf8");
if (!mock.includes("ui_action: hintUiAction")) fail("Mock Hint is not workspace-aware");

const config = fs.readFileSync("src/config.ts", "utf8");
if (config.includes("localhost:8000/api")) fail("API base URL violates onboarding rule");

console.log("V1.3 static QA OK");
[
  "FE-1301 Task Renderer",
  "FE-1302 Workspace State",
  "FE-1303 Object Counter",
  "FE-1304 Bar Model",
  "FE-1305 Number Line",
  "API-1306 TaskUISchema V1",
  "API-1307 Structured Response",
  "API-1308 Workspace-aware Hint",
  "QA-1312 QA route"
].forEach(item => console.log(`- ${item}`));
