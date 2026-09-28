# 08｜项目接手指南

> 新开发人员建议先读本文，再读代码。

---

# 1. 先理解产品边界

这是：

> 小学二年级数学能力成长系统儿童端 Sprint 3 前端

不是普通题库。

核心方法：

```text
画图
尝试
分类
找规律
验证
```

Learning Engine 是教育决策中心。

前端：

> 不实现教育决策，只负责交互、呈现、状态和调用。

---

# 2. 开发前先看这些文件

```text
README.md
CHANGELOG.md

docs/
├── 01_COMPONENT_IMPLEMENTATION.md
├── 02_STATE_MACHINE.md
├── 03_API_MAPPING.md
├── 04_SPRINT3_ACCEPTANCE.md
├── 05_VALIDATION_REPORT.md
├── 06_FRONTEND_MODULE_MAP.md
├── 07_NEXT_DEVELOPMENT_ROADMAP.md
└── 08_HANDOVER_GUIDE.md
```

---

# 3. 代码阅读顺序

## Step 1｜Route

```text
app/child/math
```

先理解页面入口。

## Step 2｜Screens

```text
src/screens/
```

理解页面怎么组装。

## Step 3｜State Machine

```text
src/features/learning/
```

这是学习页核心。

## Step 4｜API

```text
src/lib/api/
```

理解 Mock / HTTP Adapter。

## Step 5｜Components

```text
src/components/
```

理解18个核心组件。

## Step 6｜Theme

```text
src/theme/
```

理解两套 Built-in Skin。

---

# 4. 本地启动

```bash
cp .env.example .env.local
npm install
npm run dev
```

默认 Mock：

```env
NEXT_PUBLIC_LEARNING_API_MODE=mock
```

访问：

```text
/child/math
```

---

# 5. 联调后端

改：

```env
NEXT_PUBLIC_LEARNING_API_MODE=http
NEXT_PUBLIC_LEARNING_API_BASE_URL=http://localhost:8000/api
```

然后验证：

```text
Profile
Abilities
Create Session
Next Task
Attempt
Hint
Complete
```

---

# 6. 绝对不要做的事情

不要：

- 在前端计算 Mastery
- 在前端重写 Diagnosis
- 在组件里硬编码 Learning Rule
- 把 E01~E07 当系统错误
- 第一次错误直接显示答案
- 让孩子在儿童端自由切换皮肤
- 直接从 Child UI 调用 LLM
- 把 Session Snapshot 当成最终数据源（V1.2已改为Session Result API）

---

# 7. 下一位开发最应该做什么

优先顺序：

```text
1 Task Renderer V1
2 Math Manipulative Engine V1
3 Ability Detail
4 Learning Plan
5 Skin Resolver
```

不要先做：
- 更多普通卡片
- 更多首页装饰
- Skin Engine
- Voice
- 家长端

除非产品排期明确调整。

---

# 8. 每次发版必须更新什么

每次提交正式版本：

1. 修改 `package.json` version
2. 更新 `CHANGELOG.md`
3. 更新相关 docs
4. 更新 `04_SPRINT3_ACCEPTANCE.md` / 后续对应验收表
5. 如果新增API：
   - 更新 `contracts.ts`
   - 更新 `docs/03_API_MAPPING.md`
6. 如果新增状态：
   - 更新 `machine.ts`
   - 更新 `docs/02_STATE_MACHINE.md`
7. 如果新增组件：
   - 更新 `/dev/ui-kit`
   - 更新组件清单

---

# 9. 状态标记约定

文档统一：

```text
✅ 已完成
🟡 部分完成 / 已留接口
❌ 未实现
⚠️ 存在风险 / 依赖外部
```

不要用“完成”描述只有占位UI的功能。
