import type {
  AbilityChange,
  AbilityState,
  AttemptRequest,
  AttemptResult,
  HintResponse,
  LearnerProfile,
  LearningApi,
  LearningBehavior,
  LearningSession,
  NextRecommendation,
  SessionResult,
  TaskInstance
} from "./contracts";

type MockTask = TaskInstance & {
  __answer: string;
  __hints: string[];
};

type MockSessionStats = {
  childId: string;
  startedAt: number;
  completedAt?: number;
  taskCount: number;
  attemptCount: number;
  hintLevels: number[];
  retryAfterError: boolean;
  completed: boolean;
};

const abilities: AbilityState[] = [
  { ability_id: "MATH-LANG", name: "理解题意", level: 3, confidence: 0.78, evidence_count: 8, trend: "stable", fit_band: { min: 2, max: 3 } },
  { ability_id: "REL", name: "数量关系", level: 2, confidence: 0.72, evidence_count: 6, trend: "up", fit_band: { min: 2, max: 3 } },
  { ability_id: "CALC", name: "计算能力", level: 3, confidence: 0.84, evidence_count: 12, trend: "stable", fit_band: { min: 2, max: 4 } },
  { ability_id: "STRAT", name: "数学策略", level: 2, confidence: 0.64, evidence_count: 5, trend: "watch", fit_band: { min: 2, max: 3 } },
  { ability_id: "CHECK", name: "检查验证", level: 2, confidence: 0.61, evidence_count: 5, trend: "up", fit_band: { min: 2, max: 3 } },
  { ability_id: "TRANSFER", name: "迁移应用", level: 1, confidence: 0.42, evidence_count: 2, trend: "watch", fit_band: { min: 1, max: 2 } }
];

const taskBank: MockTask[] = [
  {
    task_instance_id: "mock-task-1",
    ability_id: "REL",
    difficulty: 2,
    goal: "理解“比……多/少”的数量关系",
    strategy_policy: { hint_max_level: 4 },
    ui_schema: {
      kind: "number",
      prompt: "小明有 8 个苹果，小红有 5 个苹果。小明比小红多几个苹果？",
      answer_placeholder: "输入数字",
      visual: {
        type: "objects",
        rows: [
          { label: "小明", count: 8, symbol: "🍎" },
          { label: "小红", count: 5, symbol: "🍎" }
        ]
      }
    },
    __answer: "3",
    __hints: [
      "先别急着算。题目是在问“合起来”，还是在“比较”？",
      "把小明和小红的苹果一一对齐，看看多出来几个。",
      "可以用减法表示“相差多少”：8 − 5。",
      "8 − 5 = 3，所以小明比小红多 3 个苹果。"
    ]
  },
  {
    task_instance_id: "mock-task-2",
    ability_id: "STRAT",
    difficulty: 2,
    goal: "用画图/摆一摆的方法理解关系",
    strategy_policy: { hint_max_level: 4 },
    ui_schema: {
      kind: "number",
      prompt: "书架上原来有 12 本书，借走 4 本。现在还有几本？",
      answer_placeholder: "输入数字",
      visual: {
        type: "bar-model",
        rows: [{ label: "原来", count: 12, symbol: "▮" }]
      }
    },
    __answer: "8",
    __hints: [
      "“借走”以后，数量是变多了还是变少了？",
      "可以把 12 个小格划掉 4 个。",
      "这可以写成 12 − 4。",
      "12 − 4 = 8。"
    ]
  },
  {
    task_instance_id: "mock-task-3",
    ability_id: "CHECK",
    difficulty: 2,
    goal: "完成后主动检查",
    strategy_policy: { hint_max_level: 4 },
    ui_schema: {
      kind: "number",
      prompt: "一盒彩笔有 6 支，两盒一共有多少支？",
      answer_placeholder: "输入数字",
      visual: {
        type: "objects",
        rows: [
          { label: "第1盒", count: 6, symbol: "✏️" },
          { label: "第2盒", count: 6, symbol: "✏️" }
        ]
      }
    },
    __answer: "12",
    __hints: [
      "这里是两个同样多的 6，要找“一共”。",
      "可以把两组 6 合起来数一数。",
      "可以写成 6 + 6。",
      "6 + 6 = 12。"
    ]
  }
];

const sessionIndex = new Map<string, number>();
const sessionStats = new Map<string, MockSessionStats>();
const taskInstanceMeta = new Map<
  string,
  { task: MockTask; sessionId: string }
>();
const attemptMeta = new Map<
  string,
  { task: MockTask; sessionId: string }
>();

function uuid() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `mock-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export class MockLearningApi implements LearningApi {
  async getProfile(childId: string): Promise<LearnerProfile> {
    await wait();
    return {
      child_id: childId,
      grade: "2",
      region_code: "CN-SH",
      active_abilities: abilities.filter(a => ["REL", "STRAT", "CHECK"].includes(a.ability_id)),
      strengths: ["CALC"],
      developing: ["REL", "STRAT", "CHECK"],
      observations: ["开始主动使用画图方法"]
    };
  }

  async getAbilities(): Promise<AbilityState[]> {
    await wait();
    return abilities;
  }

  async createSession(input: {
    child_id: string;
    subject: "math" | "english";
    requested_minutes?: number;
    plan_id?: string;
  }): Promise<LearningSession> {
    await wait();
    const session_id = uuid();
    sessionIndex.set(session_id, 0);
    sessionStats.set(session_id, {
      childId: input.child_id,
      startedAt: Date.now(),
      taskCount: 0,
      attemptCount: 0,
      hintLevels: [],
      retryAfterError: false,
      completed: false
    });

    return {
      session_id,
      status: "active",
      plan_id: input.plan_id ?? "00000000-0000-0000-0000-000000000101"
    };
  }

  async getNextTask(input: {
    child_id: string;
    session_id: string;
    subject: "math" | "english";
    requested_minutes?: number;
  }): Promise<TaskInstance> {
    await wait();
    const idx = sessionIndex.get(input.session_id) ?? 0;
    const task = taskBank[Math.min(idx, taskBank.length - 1)];
    const instanceId = `${task.task_instance_id}-${idx}`;

    sessionIndex.set(input.session_id, idx + 1);
    taskInstanceMeta.set(instanceId, {
      task,
      sessionId: input.session_id
    });

    const { __answer, __hints, ...publicTask } = task;
    return { ...publicTask, task_instance_id: instanceId };
  }

  async submitAttempt(input: AttemptRequest): Promise<AttemptResult> {
    await wait();

    const meta =
      taskInstanceMeta.get(input.task_instance_id) ??
      { task: taskBank[0], sessionId: "" };
    const task = meta.task;
    const stats = sessionStats.get(meta.sessionId);

    if (stats) {
      stats.attemptCount += 1;
      if (input.attempt_no > 1) stats.retryAfterError = true;
      sessionStats.set(meta.sessionId, stats);
    }

    const correct =
      String(input.response).trim().toLowerCase() ===
      task.__answer.trim().toLowerCase();

    const attempt_id = uuid();
    attemptMeta.set(attempt_id, meta);

    if (correct) {
      const isLast = task.task_instance_id === "mock-task-3";

      if (stats) {
        stats.taskCount += 1;
        if (isLast) {
          stats.completed = true;
          stats.completedAt = Date.now();
        }
        sessionStats.set(meta.sessionId, stats);
      }

      return {
        attempt_id,
        correct: true,
        diagnosis: null,
        next_action: { type: isLast ? "COMPLETE" : "NEXT_TASK" }
      };
    }

    return {
      attempt_id,
      correct: false,
      diagnosis: {
        code: input.attempt_no === 1 ? "E03" : "E05",
        label: input.attempt_no === 1 ? "关系识别偏差" : "策略使用不足",
        confidence: 0.78,
        evidence_scope: { task_instance_id: input.task_instance_id }
      },
      next_action: {
        type: "HINT",
        hint_level: Math.min(input.attempt_no, 4),
        policy_id: "mock-hint-policy-v1"
      }
    };
  }

  async requestHint(input: {
    attempt_id: string;
    requested_level?: number;
  }): Promise<HintResponse> {
    await wait();
    const meta =
      attemptMeta.get(input.attempt_id) ??
      { task: taskBank[0], sessionId: "" };

    const level = Math.max(1, Math.min(input.requested_level ?? 1, 4));
    const stats = sessionStats.get(meta.sessionId);
    if (stats) {
      stats.hintLevels = Array.from(new Set([...stats.hintLevels, level]));
      sessionStats.set(meta.sessionId, stats);
    }

    return {
      policy_id: "mock-hint-policy-v1",
      hint_level: level,
      action_type:
        level === 1 ? "QUESTION" :
        level === 2 ? "STRUCTURE_HINT" :
        level === 4 ? "TEACH" : "STEP_HINT",
      text: meta.task.__hints[level - 1],
      answer_revealed: level === 4
    };
  }

  async getSessionResult(sessionId: string): Promise<SessionResult> {
    await wait();
    const stats =
      sessionStats.get(sessionId) ??
      {
        childId: "00000000-0000-0000-0000-000000000001",
        startedAt: Date.now() - 6 * 60 * 1000,
        completedAt: Date.now(),
        taskCount: 3,
        attemptCount: 4,
        hintLevels: [1],
        retryAfterError: true,
        completed: true
      };

    const behaviors: LearningBehavior[] = [
      {
        code: "SESSION_COMPLETED",
        label: "完成了本次数学任务",
        achieved: stats.completed
      },
      {
        code: "RETRY_AFTER_ERROR",
        label: "遇到困难后继续尝试",
        achieved: stats.retryAfterError
      },
      {
        code: "HINT_USED_APPROPRIATELY",
        label: "合理使用提示",
        achieved: stats.hintLevels.length <= 2
      },
      {
        code: "ACTIVE_CHECK",
        label: "完成后主动检查",
        achieved: stats.completed
      }
    ];

    const abilityChanges: AbilityChange[] = [
      {
        ability_id: "REL",
        name: "数量关系",
        before_level: 2,
        after_level: 2,
        confidence: 0.77,
        trend: "up",
        evidence_delta: 2
      }
    ];

    const recommendation: NextRecommendation = {
      type: "CONTINUE_ABILITY",
      title: "继续练习数量关系",
      description: "下一轮继续在不同情境中练习“比较”和“相差多少”。",
      ability_id: "REL"
    };

    return {
      session_id: sessionId,
      child_id: stats.childId,
      status: stats.completed ? "completed" : "active",
      duration_ms: Math.max(
        0,
        (stats.completedAt ?? Date.now()) - stats.startedAt
      ),
      task_count: stats.taskCount,
      attempt_count: stats.attemptCount,
      hint_usage: stats.hintLevels,
      learning_behaviors: behaviors,
      ability_changes: abilityChanges,
      next_recommendation: recommendation,
      completed_at: stats.completedAt
        ? new Date(stats.completedAt).toISOString()
        : undefined
    };
  }
}

function wait(ms = 180) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
