# 01｜组件实现清单

## V1.0~V1.2 Core Components（18）

### UI
1. PrimaryButton
2. SurfaceCard
3. ProgressDots
4. AbilityBadge

### 首页
5. TodayGoalCard
6. MathTaskCard
7. GrowthEntryCard

### 学习
8. MathQuestionCard
9. MathWorkspace（legacy/basic visual）
10. ManipulativeToolbar（legacy/basic tools）
11. AnswerComposer
12. CoachPanel

### 结果
13. CompletionHero
14. LearningBehaviorChecklist
15. AbilityGrowthCard
16. SessionStats
17. NextTaskCard

### 成长
18. AbilityMap

---

## V1.3 Math Interaction Components（新增3）

```text
ObjectCounter
BarModel
NumberLine
```

它们不是复制Core Component，而是由：

```text
TaskRenderer
+
WorkspaceProvider / WorkspaceState
```

统一驱动。

## Dev验收

Core双皮肤：

```text
/dev/ui-kit
```

V1.3数学交互双皮肤：

```text
/dev/v1.3-qa
```
