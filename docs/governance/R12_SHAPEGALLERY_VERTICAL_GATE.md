# R12 ShapeGallery Vertical Gate 验收底表（FE-1424）

状态：**CLOSED**（2026-10-07）｜ 模板：B5 五件套第十一实例 ｜ 上游：docs/frontend/31 Gap R12（Batch D 起手）

## 1. Gap R12 条目对照

| Gap 条目 | 要求 | 落地 |
|---|---|---|
| Semantic P0 | shape recognition / classification | 图形墙 6 形（3 正方形+2 长方形+1 圆形诱饵）→ 目标"正方形的家" |
| State P0 | selected / sorted / completed | selected（拿起/放下 toggle）→ home 序列（分类轨迹）→ 五态评估 |
| Interaction P0 | select / classify | 两步点选（点形=拿起、点家=放进）+ 退回（点家里成员）——select capability |
| Response P0 | expected shape/category | answer=家里图形个数（后端与 expected count 相等判分） |
| Evaluator P0 | classification evaluator | evaluateShapeGallery：attribute_confusion（混入异类，优先）→ missed（漏放）→ PASS |
| Evidence P0 | 选择与分类轨迹 | home 放入顺序 + home_kinds 每成员真实种类 + SHAPE_SELECTED/PLACED/RETURNED 事件链 |
| Diagnosis P0 | 属性识别错误 | attribute_confusion 原料入 structure.error（"把长方形当正方形"可分诊） |
| Acceptance P0 | E2E | 12 用例全过（见 §4） |

## 2. 解耦口径第三次运用（本 Gate 最锋利的一例）

`(r1长方形, s1, s2)` 家里 3 个——**数量=3 恰好等于答案 → 后端判对（correct=true / NEXT_TASK），
但 attribute_confusion 原料走 Evidence 入库**。诊断链由此能区分"会数但不会认属性"与
"真不会"。R08（transpose 判对留痕）、R11（近似数方向原料）之后，几何域同样成立——
**前端结构通道与后端判分通道独立不互污**已是跨域通用架构。

判定顺序=属性错优先于漏放（Diagnosis P0 权重）：家里只要有异类成员先报 attribute_confusion；
全对但缺员报 missed。config 守卫（与前端 parser 同式）：目标类必须有成员且墙上有诱饵，
否则分类不成立、答案退化为"全拿"。

## 3. 金题与数据

- **V2-R12-SHAPE-001 给正方形找一个家**（答案=3，school_objects 族）
- **app_cond 能力节点第二题**（第一题=竖式 B5）——条件识别域图形分类首链
- 已 seed 真实 RDS；pin 首抽即中（FE-1422a 机制第三次实战）

## 4. E2E 用例（12 例）

| 用例 | 验证 | 结果 |
|---|---|---|
| E2E-01 (G1) | 渲染不降级：墙 6 形+家可见 | ✅ |
| E2E-02 (G2) | 家空拦提交（EMPTY） | ✅ |
| E2E-03 | 拿起→放下 toggle 选择轨迹 | ✅ |
| E2E-04 (G3) | 空手放进家=NO_SELECTION 家数不变 | ✅ |
| E2E-05 (G4/G6) | envelope：type=shape_gallery、data 四字段、home=[s1,s2] 轨迹断言、无 representation 泄漏 | ✅ |
| E2E-06 | **解耦双断言**：混入长方形数对→correct=true + attribute_confusion 原料 | ✅ |
| E2E-07 | 退回修正路径：退长方形→补紫正方形→PASS NEXT_TASK | ✅ |
| E2E-08 | 已在家图形 disabled（IN_HOME 拒绝态） | ✅ |
| E2E-09 (G7) | 漏放 FAIL 可达后端 HINT→补放 attempt_no=2 判对 | ✅ |
| E2E-10 | 防重入 dblclick 只 1 POST | ✅ |
| E2E-11 | UNDO 单步（PLACE 一步撤销=1 个回家） | ✅ |
| E2E-12 | healing 双皮肤同链 | ✅ |

## 5. 回归与门禁

- node 语义矩阵：五态、toggle、IN_HOME/NOT_IN_HOME/NO_SELECTION 拒绝码、config 三守卫、serialize 轨迹序全过
- API 四连：解耦（true+原料）/ missed false HINT / PASS NEXT_TASK / 重放同 attempt_id
- 全量 E2E 零回归（十一套 Gate）；tsc 0 / 六 check PASS / 后端 96 passed（防漂移+1）

## 6. Batch D 状态

**1/4**：ShapeGallery(R12) ✅ → 余 ShapeCanvas(R13)、SortingBoard(R14)、DirectionGrid(R15)。

**Vertical Gate 总进度：12/19**。
