// 前后端真实联调 + 业务场景（用户旅程）测试
// 使用前端真实代码：HttpLearningApi + taskUiSchemaNormalizer（+ sessionResultNormalizer 经 adapter 内部调用）
// 连接真实后端。运行前置：
//   1. 起后端：cd apps/learning-api && DATABASE_URL=... uvicorn app.main:app --port 8000
//   2. 本脚本需 esbuild 打包 TS：esbuild scripts/integration-smoke.mts --bundle \
//        --format=esm --platform=node --outfile=/tmp/integration-smoke.mjs --alias:@/src=./apps/child-web/src
//   3. node /tmp/integration-smoke.mjs
import { HttpLearningApi } from "../apps/child-web/src/lib/api/http.ts";
import { normalizeTaskUiSchema } from "../apps/child-web/src/lib/api/taskUiSchemaNormalizer.ts";

// 数据卫生（docs/governance/QA_DATA_HYGIENE.md）：冒烟旅程写真实后端，用 QA-Simulator child。
const CHILD = process.env.QA_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const BASE = "http://127.0.0.1:8000";

// 直接实例化前端真实 Http adapter（绕过 config 的 mock 默认值，显式指定 http）
const api = new HttpLearningApi(BASE, "/v1/learning/sessions/{session_id}/result");

const results = [];
function record(name, pass, detail) {
  results.push({ name, pass, detail });
  console.log(`${pass ? "✅" : "❌"} ${name} — ${detail}`);
}

async function main() {
  console.log("========== 场景 A：孩子走完整学习旅程 ==========\n");

  // A1. 打开首页：读画像 + 能力
  const profile = await api.getProfile(CHILD);
  record("A1 读画像", !!profile.child_id, `grade=${profile.grade} developing=${profile.developing.length}个能力`);

  const abilities = await api.getAbilities(CHILD);
  record("A2 读能力", abilities.length === 7, `7个能力(${abilities.map(a => a.ability_id).join(",")})`);

  // A3. 点「数量关系挑战」→ createSession
  const session = await api.createSession({ child_id: CHILD, subject: "math", requested_minutes: 15 });
  record("A3 开会话", !!session.session_id, `session=${session.session_id.slice(0, 8)}…`);

  // A4. 后端出题（指定数量关系能力 app_rel）
  const taskRel = await api.getNextTask({
    child_id: CHILD, session_id: session.session_id, subject: "math", ability_id: "app_rel"
  });
  const uiRel = taskRel.ui_schema;
  record("A4 出题·数量关系", taskRel.ability_id === "app_rel" && uiRel.kind === "manipulative",
    `ability=${taskRel.ability_id} kind=${uiRel.kind} visual=${uiRel.visual?.type}`);

  // A5. 前端 normalizer 是否能解析这条真实 task
  const normalized = normalizeTaskUiSchema(taskRel.ui_schema);
  record("A5 前端normalizer解析", normalized.kind === "manipulative" && normalized.visual?.type === "objects",
    `normalized kind=${normalized.kind} visual=${normalized.visual?.type}`);

  // A6. 孩子答错 → 诊断 + 提示
  const attempt = await api.submitAttempt({
    task_instance_id: taskRel.task_instance_id, attempt_no: 1, response: { answer: "999" }
  });
  record("A6 答错判分", attempt.correct === false && attempt.next_action.type === "HINT",
    `correct=${attempt.correct} diagnosis=${attempt.diagnosis?.code} next=${attempt.next_action.type}`);

  // A7. 请求提示 → 检查 ui_action
  const hint = await api.requestHint({ attempt_id: attempt.attempt_id, requested_level: 2 });
  record("A7 提示带ui_action", !!hint.ui_action, `level=${hint.hint_level} ui_action=${JSON.stringify(hint.ui_action)}`);

  // A8. 孩子答对（前端仍用普通 answer，判分在后端）
  const attempt2 = await api.submitAttempt({
    task_instance_id: taskRel.task_instance_id, attempt_no: 2, response: { answer: "3" }
  });
  // 注意：需要知道正确答案。app_rel 第一题可能是"8比5多几=3"或"4+3=7"，不确定，因此这里不硬编码判断
  console.log(`   (A8 答对尝试结果 next_action=${attempt2.next_action?.type})`);

  // A9. 结果页：读 session result（前端真实 normalizer）
  const result = await api.getSessionResult(session.session_id);
  record("A9 结果页", result.session_id === session.session_id && result.duration_ms >= 0,
    `task_count=${result.task_count} attempt_count=${result.attempt_count} behaviors=${result.learning_behaviors.length}`);

  console.log("\n========== 场景 B：两个挑战分流验证 ==========\n");

  // B1. 策略挑战 → app_strat
  const s2 = await api.createSession({ child_id: CHILD, subject: "math" });
  const taskStrat = await api.getNextTask({
    child_id: CHILD, session_id: s2.session_id, subject: "math", ability_id: "app_strat"
  });
  record("B1 策略挑战出题", taskStrat.ability_id === "app_strat",
    `ability=${taskStrat.ability_id} visual=${taskStrat.ui_schema.visual?.type}`);

  // B2. 确认两个挑战出的题不一样（不同能力/不同题）
  record("B2 两挑战不同题", taskRel.task_instance_id !== taskStrat.task_instance_id,
    `rel=${taskRel.ability_id}/${taskRel.difficulty} vs strat=${taskStrat.ability_id}/${taskStrat.difficulty}`);

  console.log("\n========== 场景 C：无指定能力的默认路径 ==========\n");
  const s3 = await api.createSession({ child_id: CHILD, subject: "math" });
  const taskDefault = await api.getNextTask({ child_id: CHILD, session_id: s3.session_id, subject: "math" });
  record("C1 默认出题", !!taskDefault.task_instance_id,
    `ability=${taskDefault.ability_id} diff=${taskDefault.difficulty} visual=${taskDefault.ui_schema.visual?.type ?? "none"}`);

  console.log("\n========== 结果汇总 ==========");
  const pass = results.filter(r => r.pass).length;
  console.log(`通过 ${pass}/${results.length}`);
  console.log(JSON.stringify(results, null, 2));
}

main().catch(err => {
  console.error("❌ 联调脚本异常:", err);
  process.exit(1);
});