# 07｜后续开发路线图

> 本文回答：当前 Sprint 3 前端之后，还要继续开发什么。

---

# V1.2 已完成

```text
✅ Session Result 正式结果闭环
✅ learning_behaviors
✅ ability_changes
✅ next_recommendation
✅ server source of truth
```

---

# P0｜下一阶段必须做（V1.3）

## 1. Math Manipulative Engine

当前只有工具入口和基础展示。

需要继续实现：

### Draw
- 自由画线
- 橡皮擦
- 清空
- 撤销
- 触控笔支持

### Blocks
- 可拖拽数学积木
- 自动吸附
- 分组
- 一一对应
- 数量计数

### Number Line
- 数轴
- 点选
- 拖动
- 区间
- 跳步

### Bar Model
- 线段图
- 总量/部分
- 比较关系
- 未知量
- 拖动调整

### Sorting
- 分类板
- 拖拽分类
- 多组
- 检查规则

### Matching
- 连线
- 一一对应
- 关系匹配

目标：

> 让“画图 / 尝试 / 分类 / 找规律 / 验证”真正成为可操作能力，而不是按钮。

---

## 2. Task Renderer

应建立统一 Renderer：

```text
TaskRenderer
├── NumberInputRenderer
├── ChoiceRenderer
├── FormulaRenderer
├── DragRenderer
├── NumberLineRenderer
├── BarModelRenderer
├── SortingRenderer
└── CanvasRenderer
```

根据：

```text
task.ui_schema.kind
task.ui_schema.visual.type
```

动态渲染。

---


# P1｜能力成长闭环

## 4. Ability Detail

从当前成长地图继续向下：

```text
AbilityMap
 ↓
AbilityDetail
```

需要：

- 当前 Level
- Confidence
- Evidence Count
- Trend
- 最近任务
- 最近错误类型
- 迁移证据
- “为什么判断为这个等级”

---

## 5. Evidence View

家长端/教研端需要：

```text
能力判断
 ↓
对应证据
```

包括：

- Task
- Attempt
- Hint Usage
- Diagnosis
- Retry
- Completion
- Transfer Task

目标：

> 所有能力判断都可解释。

---

## 6. Learning Plan

目前 Session 只是按 Learning Engine 选任务。

后续需要完整：

```text
Learning Plan
├── Today
├── This Week
├── Ability Focus
├── Speed Training
└── Review
```

---

# P1｜皮肤产品化

## 7. Skin Resolver

当前：

```text
.env
 ↓
ChildSkinProvider
```

后续：

```text
child_id
 ↓
Skin Resolver
 ↓
Skin Config
 ↓
ChildSkinProvider
```

孩子端仍然只读。

---

## 8. Parent Skin Management

未来家长端：

- 查看系统内置皮肤
- 预览
- 给孩子设置皮肤
- 恢复默认
- 查看当前生效皮肤

---

## 9. Skin Engine

未来单独项目：

```text
Built-in
Official Template
AI Custom
 ↓
Skin Schema
 ↓
Validator
 ↓
Preview
 ↓
Publish
 ↓
Bind Child
 ↓
Runtime Resolver
```

不建议现在塞进 Sprint 3 儿童端。

---

# P2｜多模态和交互体验

## 10. Voice / TTS

后续可增加：

- 题目朗读
- Hint朗读
- 儿童语音回答
- 语音确认
- 低年级无障碍模式

---

## 11. Animation

只建议做学习辅助动画：

- 数轴跳步
- 数量合并
- 线段比较
- 图形拆分
- 能力成长

禁止过度手游化。

---

# P2｜家长端

## 12. Parent Dashboard

至少包含：

- 本周学习
- 正确率
- 独立完成率
- Hint依赖
- 稳定度
- 迁移度
- 六大能力
- 错因趋势
- 皮肤管理

---

# P2｜教研 / 管理端

## 13. Content Authoring

需要：

- Task模板
- Ability绑定
- Difficulty
- ui_schema
- strategy_policy
- Hint ladder
- Resource Version
- Review / Publish

---

# 推荐实施顺序

```text
Phase 1
Math Manipulative Engine
+
Task Renderer

Phase 2
Session Result API
+
Ability Detail
+
Evidence

Phase 3
Learning Plan

Phase 4
Parent Dashboard
+
Skin Resolver

Phase 5
Skin Engine
+
AI Custom Skin

Phase 6
Voice / TTS
+
Advanced Interaction
```

---

# 当前最重要判断

不要优先继续增加普通页面。

当前最值得投入的是：

> `MathWorkspace + TaskRenderer`

因为它决定系统最终是：

```text
普通题库 + AI提示
```

还是：

```text
真正的数学能力训练系统
```
