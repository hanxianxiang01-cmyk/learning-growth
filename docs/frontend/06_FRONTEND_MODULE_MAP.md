# 06｜前端模块地图 V1.3

| 模块 | 功能 | 状态 |
|---|---|---|
| 数学首页 | Profile / Ability / Create Session | ✅ |
| 数学学习页 | TaskRenderer + Learning Flow | ✅ |
| Learning State | Attempt / Hint / Retry / Complete | ✅ |
| Workspace State | Representation / Undo / Reset / Hint Action | ✅ V1.3 |
| Task Renderer | Schema → Renderer路由 | ✅ V1.3 |
| Object Counter | Pointer拖动 / 一一对齐 | ✅ V1.3 |
| Bar Model | 线段长度 / 总量部分 / 比较 | ✅ V1.3 |
| Number Line | 起点 / 跳步 / 前后移动 | ✅ V1.3 |
| Structured Response | answer + representation | ✅ V1.3 |
| Workspace Hint | UI Action | ✅ V1.3 |
| 结果页 | Session Result API | ✅ V1.2保持 |
| 成长地图 | Ability Overview | ✅ |
| Built-in Skin | healing / math-lab | ✅ |
| Choice Renderer | — | ❌ 后续 |
| Formula Renderer | — | ❌ 后续 |
| Interaction Events | — | ❌ 后续 |
| Free Draw / Sorting / Matching | — | ❌ 后续 |

## 学习页V1.3结构

```text
MathLearningScreen
├── TaskRenderer
│   ├── NumberRenderer
│   └── ManipulativeRenderer
│       ├── WorkspaceProvider
│       ├── ObjectCounter
│       ├── BarModel
│       └── NumberLine
│
└── CoachPanel
    └── ui_action → Workspace State
```

## 数据边界

```text
Learning Engine = 教育判断
Child Web       = 交互呈现 + representation采集
```

前端不将 Workspace操作直接转换为 Mastery/Diagnosis。
