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
  TaskInstance,
  TaskResponse,
  WorkspaceUiAction
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

// 与后端 ability_seed 一致的 7 能力（app_* 前缀），level 模拟一个正在成长中的孩子。
// 依赖链顺序：app_rd → app_cond → app_rel → app_model → app_strat → app_check → app_transfer
const abilities: AbilityState[] = [
  { ability_id: "app_rd", name: "读题理解", level: 3, confidence: 0.8, evidence_count: 10, trend: "stable", fit_band: { min: 2, max: 3 } },
  { ability_id: "app_cond", name: "条件识别", level: 3, confidence: 0.76, evidence_count: 8, trend: "stable", fit_band: { min: 2, max: 3 } },
  { ability_id: "app_rel", name: "数量关系", level: 2, confidence: 0.72, evidence_count: 6, trend: "up", fit_band: { min: 2, max: 3 } },
  { ability_id: "app_model", name: "建模表征", level: 1, confidence: 0.55, evidence_count: 3, trend: "up", fit_band: { min: 1, max: 2 } },
  { ability_id: "app_strat", name: "策略选择", level: 2, confidence: 0.64, evidence_count: 5, trend: "watch", fit_band: { min: 2, max: 3 } },
  { ability_id: "app_check", name: "检查验算", level: 2, confidence: 0.58, evidence_count: 5, trend: "down_review", fit_band: { min: 1, max: 2 } },
  { ability_id: "app_transfer", name: "迁移变式", level: 0, confidence: 0.4, evidence_count: 1, trend: "watch", fit_band: { min: 1, max: 1 } }
];

const structuredResponseSchema = {
  type: "structured" as const,
  answer_type: "number" as const,
  representation_required: true
};

const numberResponseSchema = {
  type: "structured" as const,
  answer_type: "number" as const,
  representation_required: false
};

// mock 题库：精选覆盖三种交互工作台（objects / bar-model / number-line）+ 关键能力，
// 与后端 50 题题库的题目同源（各取代表性变式），保证 mock 模式与 http 模式体验一致。
// 能力 ID 统一用 app_*，与 challengeMapping（按名称「数量关系」/「策略」匹配）联动。
const taskBank: MockTask[] = [
  // ---- app_rel（数量关系）—— 首页「数量关系挑战」入口 ----
  {
    task_instance_id: "mock-rel-objects-1",
    ability_id: "app_rel",
    difficulty: 1,
    goal: "理解两个部分合成一个整体的数量关系",
    strategy_policy: { hint_max_level: 4 },
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
      prompt: "小雨有4个红气球，又拿来了3个蓝气球。现在一共有多少个气球？",
      answer_placeholder: "输入数字",
      visual: {
        type: "objects",
        groups: [
          { id: "g1", label: "第1组", count: 4, symbol: "🎈" },
          { id: "g2", label: "第2组", count: 3, symbol: "🎈" }
        ]
      },
      tools: ["move", "align", "undo", "reset"],
      response_schema: structuredResponseSchema
    },
    __answer: "7",
    __hints: [
      "先看看，气球的数量是变多了还是变少了？",
      "把两组气球放到一起数一数。",
      "这是把4和3合在一起，可以用加法表示。",
      "4 + 3 等于几？"
    ]
  },
  {
    task_instance_id: "mock-rel-bar-1",
    ability_id: "app_rel",
    difficulty: 2,
    goal: "理解整体与部分之间的关系",
    strategy_policy: { hint_max_level: 4 },
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
      prompt: "盒子里一共有12张贴纸，其中5张是星星贴纸，其余都是圆形贴纸。圆形贴纸有多少张？",
      answer_placeholder: "输入数字",
      visual: {
        type: "bar-model",
        relationship: "part-whole",
        max_value: 14,
        bars: [
          { id: "total", label: "一共", value: 12, min: 0, max: 12 },
          { id: "known", label: "已知部分", value: 5, min: 0, max: 12 },
          { id: "unknown", label: "未知部分", min: 0, max: 12, unknown: true }
        ]
      },
      tools: ["resize", "undo", "reset"],
      response_schema: structuredResponseSchema
    },
    __answer: "7",
    __hints: [
      "12表示整体，5表示其中一部分。现在要找的是哪一部分？",
      "可以画一条表示12的长条，再标出其中5。",
      "已知整体和一部分，要找另一部分，可以用减法。",
      "12 - 5 等于几？"
    ]
  },
  {
    task_instance_id: "mock-rel-numberline-1",
    ability_id: "app_rel",
    difficulty: 1,
    goal: "理解数量增加后的结果关系",
    strategy_policy: { hint_max_level: 4 },
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
      prompt: "树上原来有6只小鸟，又飞来了2只。现在树上一共有多少只小鸟？",
      answer_placeholder: "输入数字",
      visual: {
        type: "number-line",
        min: 0,
        max: 10,
        step: 1,
        start: 6
      },
      tools: ["jump", "undo", "reset"],
      response_schema: structuredResponseSchema
    },
    __answer: "8",
    __hints: [
      "“又飞来了”以后，小鸟是变多了还是变少了？",
      "可以从6开始，再向更大的数走2步。",
      "数量变多，可以用加法表示。",
      "6 + 2 等于几？"
    ]
  },

  // ---- app_strat（策略选择）—— 首页「策略挑战」入口 ----
  {
    task_instance_id: "mock-strat-numberline-1",
    ability_id: "app_strat",
    difficulty: 1,
    goal: "理解数量增加后的结果关系",
    strategy_policy: { hint_max_level: 4 },
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
      prompt: "小明有5支铅笔，妈妈又给了他3支。现在小明有多少支铅笔？",
      answer_placeholder: "输入数字",
      visual: {
        type: "number-line",
        min: 0,
        max: 10,
        step: 1,
        start: 5
      },
      tools: ["jump", "undo", "reset"],
      response_schema: structuredResponseSchema
    },
    __answer: "8",
    __hints: [
      "“又给了”以后，铅笔是变多了还是变少了？",
      "可以从5开始，向更大的数走3步。",
      "增加的数量可以用加法算。",
      "5 + 3 等于几？"
    ]
  },
  {
    task_instance_id: "mock-strat-bar-1",
    ability_id: "app_strat",
    difficulty: 2,
    goal: "理解“比基准多多少”时较大数量的求法",
    strategy_policy: { hint_max_level: 4 },
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
      prompt: "小杰有7张卡片，小宁比小杰多4张。小宁有多少张卡片？",
      answer_placeholder: "输入数字",
      visual: {
        type: "bar-model",
        relationship: "compare",
        max_value: 13,
        bars: [
          { id: "base", label: "已知", value: 7, min: 0, max: 13 },
          { id: "unknown", label: "未知", min: 0, max: 13, unknown: true }
        ]
      },
      tools: ["resize", "undo", "reset"],
      response_schema: structuredResponseSchema
    },
    __answer: "11",
    __hints: [
      "小杰的7张是基准，小宁比这个基准多还是少？",
      "先画出表示7的线段，再在小宁这一条上多出4。",
      "求“比7多4”的数量，要把多出来的4加上去。",
      "7 + 4 等于几？"
    ]
  },
  {
    task_instance_id: "mock-strat-objects-1",
    ability_id: "app_strat",
    difficulty: 1,
    goal: "理解两个数量之间的差",
    strategy_policy: { hint_max_level: 4 },
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
      prompt: "小红有8朵花，小蓝有5朵花。小红比小蓝多几朵？",
      answer_placeholder: "输入数字",
      visual: {
        type: "objects",
        groups: [
          { id: "g1", label: "第1组", count: 8, symbol: "🌸" },
          { id: "g2", label: "第2组", count: 5, symbol: "🌸" }
        ]
      },
      tools: ["move", "align", "undo", "reset"],
      response_schema: structuredResponseSchema
    },
    __answer: "3",
    __hints: [
      "题目是在问一共，还是在问相差多少？",
      "把8朵和5朵一一对齐看看。",
      "求相差多少，可以用大的数减小的数。",
      "8 - 5 等于几？"
    ]
  },

  // ---- app_model（建模表征）—— 线段图 ----
  {
    task_instance_id: "mock-model-bar-1",
    ability_id: "app_model",
    difficulty: 2,
    goal: "用线段图表征整体与部分",
    strategy_policy: { hint_max_level: 4 },
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
      prompt: "一盒彩纸有13张，其中红色5张，其余是黄色。黄色彩纸有多少张？",
      answer_placeholder: "输入数字",
      visual: {
        type: "bar-model",
        relationship: "part-whole",
        max_value: 15,
        bars: [
          { id: "total", label: "一共", value: 13, min: 0, max: 13 },
          { id: "known", label: "已知部分", value: 5, min: 0, max: 13 },
          { id: "unknown", label: "未知部分", min: 0, max: 13, unknown: true }
        ]
      },
      tools: ["resize", "undo", "reset"],
      response_schema: structuredResponseSchema
    },
    __answer: "8",
    __hints: [
      "13是整体，5是其中一部分，要找另一部分。",
      "用一条线段表示13，标出已知的5。",
      "求另一部分，从整体去掉已知部分。",
      "13 - 5 等于几？"
    ]
  },

  // ---- app_check（检查验算）—— 数轴 ----
  {
    task_instance_id: "mock-check-numberline-1",
    ability_id: "app_check",
    difficulty: 2,
    goal: "能发现结果是否合理",
    strategy_policy: { hint_max_level: 4 },
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
      prompt: "小林有8个苹果，吃掉3个。小华算“8 - 3 = 6”。请检查：小华的答案正确填1，错误填0。",
      answer_placeholder: "输入1或0",
      visual: {
        type: "number-line",
        min: 0,
        max: 12,
        step: 1,
        start: 8
      },
      tools: ["jump", "undo", "reset"],
      response_schema: structuredResponseSchema
    },
    __answer: "0",
    __hints: [
      "先自己算一算：8减3等于几？",
      "在数轴上从8往左走3格，会到哪里？",
      "小华算的是6，和你算的结果一样吗？",
      "8 - 3 应该等于 5，所以小华错了吗？"
    ]
  },

  // ---- app_rd（读题理解）—— 纯 number ----
  {
    task_instance_id: "mock-rd-number-1",
    ability_id: "app_rd",
    difficulty: 1,
    goal: "能读清题目所问对象",
    strategy_policy: { hint_max_level: 4 },
    ui_schema: {
      schema_version: "1.0",
      kind: "number",
      prompt: "乐乐有5个橘子和2本书。题目问：乐乐有几本书？",
      answer_placeholder: "输入数字",
      response_schema: numberResponseSchema
    },
    __answer: "2",
    __hints: [
      "先圈出题目最后问的是什么。",
      "题目问的是“书”，不是“橘子”。",
      "找到和“书”放在一起的数字。",
      "“2本书”里的数字是多少？"
    ]
  },

  // ---- app_transfer（迁移变式）—— 数轴两步 ----
  {
    task_instance_id: "mock-transfer-numberline-1",
    ability_id: "app_transfer",
    difficulty: 5,
    goal: "把“先增加后减少”的两步策略迁移到新情境",
    strategy_policy: { hint_max_level: 4 },
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
      prompt: "书架上原来有8本新书，老师又放上5本，后来同学借走4本。现在书架上有多少本书？",
      answer_placeholder: "输入数字",
      visual: {
        type: "number-line",
        min: 0,
        max: 16,
        step: 1,
        start: 8
      },
      tools: ["jump", "undo", "reset"],
      response_schema: structuredResponseSchema
    },
    __answer: "9",
    __hints: [
      "先判断两次变化分别是增加还是减少。",
      "从8开始，先向前走5步，再向后走4步。",
      "第一步加5，第二步减4。",
      "先算8 + 5，再把结果减4。最后是多少？"
    ]
  }
];

const sessionIndex = new Map<string, number>();
const sessionStats = new Map<string, MockSessionStats>();
const taskInstanceMeta = new Map<string, { task: MockTask; sessionId: string }>();
const attemptMeta = new Map<string, { task: MockTask; sessionId: string }>();

// 一次 session 的目标任务数（与后端 SESSION_TASK_GOAL 对齐）
const SESSION_TASK_GOAL = 3;

function uuid() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `mock-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function extractAnswer(response: TaskResponse) {
  return String(response.answer ?? "").trim().toLowerCase();
}

function hintUiAction(task: MockTask, level: number): WorkspaceUiAction | null {
  if (
    level < 2 ||
    task.ui_schema.schema_version === "2.0" ||
    task.ui_schema.kind !== "manipulative"
  ) return null;
  const visual = task.ui_schema.visual;

  if (visual.type === "objects") {
    if (level === 2) return { type: "highlight", targets: visual.groups.map(group => group.id) };
    if (level === 3) return { type: "align_groups" };
  }

  if (visual.type === "bar-model") {
    return { type: "show_bar_relation", targets: visual.bars.map(bar => bar.id) };
  }

  if (visual.type === "number-line") {
    return { type: "show_number_line_start", value: visual.start };
  }

  return null;
}

export class MockLearningApi implements LearningApi {
  async getProfile(childId: string): Promise<LearnerProfile> {
    await wait();
    return {
      child_id: childId,
      grade: "2",
      region_code: "CN-SH",
      active_abilities: abilities,
      strengths: ["app_rd", "app_cond"],
      developing: ["app_rel", "app_model", "app_strat", "app_check", "app_transfer"],
      observations: ["开始主动使用图示方法"]
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
    ability_id?: string;
  }): Promise<TaskInstance> {
    await wait();
    const idx = sessionIndex.get(input.session_id) ?? 0;

    // 指定能力：优先取该能力的第一道题；否则按「已做过几题」轮换。
    let task: MockTask;
    if (input.ability_id) {
      const candidates = taskBank.filter(t => t.ability_id === input.ability_id);
      task = candidates.length
        ? candidates[Math.min(idx, candidates.length - 1)]
        : taskBank[Math.min(idx, taskBank.length - 1)];
    } else {
      task = taskBank[Math.min(idx, taskBank.length - 1)];
    }
    const instanceId = `${task.task_instance_id}-${idx}`;

    sessionIndex.set(input.session_id, idx + 1);
    taskInstanceMeta.set(instanceId, { task, sessionId: input.session_id });

    const { __answer, __hints, ...publicTask } = task;
    return { ...publicTask, task_instance_id: instanceId };
  }

  async submitAttempt(input: AttemptRequest): Promise<AttemptResult> {
    await wait();
    const meta = taskInstanceMeta.get(input.task_instance_id) ?? { task: taskBank[0], sessionId: "" };
    const stats = sessionStats.get(meta.sessionId);

    if (stats) {
      stats.attemptCount += 1;
      if (input.attempt_no > 1) stats.retryAfterError = true;
      sessionStats.set(meta.sessionId, stats);
    }

    const correct = extractAnswer(input.response) === meta.task.__answer.toLowerCase();
    const attempt_id = uuid();
    attemptMeta.set(attempt_id, meta);

    if (correct) {
      // 答对：taskCount+1，达到 SESSION_TASK_GOAL 时完成
      if (stats) {
        stats.taskCount += 1;
        if (stats.taskCount >= SESSION_TASK_GOAL) {
          stats.completed = true;
          stats.completedAt = Date.now();
        }
        sessionStats.set(meta.sessionId, stats);
      }
      const isComplete = stats ? stats.taskCount >= SESSION_TASK_GOAL : false;
      return {
        attempt_id,
        correct: true,
        diagnosis: null,
        next_action: { type: isComplete ? "COMPLETE" : "NEXT_TASK" }
      };
    }

    return {
      attempt_id,
      correct: false,
      diagnosis: {
        code: input.attempt_no === 1 ? "E03" : "E05",
        label: input.attempt_no === 1 ? "关系识别偏差" : "策略使用不足",
        confidence: 0.78,
        evidence_scope: {
          task_instance_id: input.task_instance_id,
          representation_type: input.response.representation?.type
        }
      },
      next_action: {
        type: "HINT",
        hint_level: Math.min(input.attempt_no, 4),
        policy_id: "mock-hint-policy-v13"
      }
    };
  }

  async requestHint(input: { attempt_id: string; requested_level?: number }): Promise<HintResponse> {
    await wait();
    const meta = attemptMeta.get(input.attempt_id) ?? { task: taskBank[0], sessionId: "" };
    const level = Math.max(1, Math.min(input.requested_level ?? 1, 4));
    const stats = sessionStats.get(meta.sessionId);
    if (stats) {
      stats.hintLevels = Array.from(new Set([...stats.hintLevels, level]));
      sessionStats.set(meta.sessionId, stats);
    }

    return {
      policy_id: "mock-hint-policy-v13",
      hint_level: level,
      action_type:
        level === 1 ? "QUESTION" :
        level === 2 ? "STRUCTURE_HINT" :
        level === 4 ? "TEACH" : "STEP_HINT",
      text: meta.task.__hints[level - 1],
      answer_revealed: level === 4,
      ui_action: hintUiAction(meta.task, level)
    };
  }

  async getSessionResult(sessionId: string): Promise<SessionResult> {
    await wait();
    const stats = sessionStats.get(sessionId) ?? {
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
      { code: "SESSION_COMPLETED", label: "完成了本次数学任务", achieved: stats.completed },
      { code: "RETRY_AFTER_ERROR", label: "遇到困难后继续尝试", achieved: stats.retryAfterError },
      { code: "HINT_USED_APPROPRIATELY", label: "合理使用提示", achieved: stats.hintLevels.length <= 2 },
      { code: "USED_REPRESENTATION", label: "尝试用数学图示表示关系", achieved: stats.taskCount > 0 }
    ];

    const abilityChanges: AbilityChange[] = [
      {
        ability_id: "app_rel",
        name: "数量关系",
        before_level: 1,
        after_level: 2,
        confidence: 0.79,
        trend: "up",
        evidence_delta: 3
      },
      {
        ability_id: "app_model",
        name: "建模表征",
        before_level: 1,
        after_level: 1,
        confidence: 0.63,
        trend: "stable",
        evidence_delta: 2
      },
      {
        ability_id: "app_check",
        name: "检查验算",
        before_level: 2,
        after_level: 2,
        confidence: 0.58,
        trend: "down_review",
        evidence_delta: 1
      }
    ];

    const recommendation: NextRecommendation = {
      type: "REVIEW_ABILITY",
      title: "再巩固一下检查验算",
      description: "系统会安排合适的练习，帮助这项能力变得更稳定。",
      ability_id: "app_check"
    };

    return {
      session_id: sessionId,
      child_id: stats.childId,
      status: stats.completed ? "completed" : "active",
      duration_ms: Math.max(0, (stats.completedAt ?? Date.now()) - stats.startedAt),
      task_count: stats.taskCount,
      completed_count: stats.completed ? stats.taskCount : 0,
      attempt_count: stats.attemptCount,
      hint_usage: stats.hintLevels,
      learning_behaviors: behaviors,
      ability_changes: abilityChanges,
      next_recommendation: recommendation,
      completed_at: stats.completedAt ? new Date(stats.completedAt).toISOString() : undefined
    };
  }
}

function wait(ms = 180) {
  return new Promise(resolve => setTimeout(resolve, ms));
}