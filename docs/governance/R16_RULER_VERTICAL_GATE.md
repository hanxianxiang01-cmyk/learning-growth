# R16 Ruler Vertical Gate 验收底表（FE-1429）

状态：**CLOSED**（2026-10-08）｜ 模板：B5 五件套第十五实例 ｜ 上游：docs/frontend/31 Gap R16（Batch E 起手题）

## 1. Gap R16 条目对照

| Gap 条目 | 要求 | 落地 |
|---|---|---|
| Semantic P0 | length / measure / compare | 尺面物体长度测量（铅笔跨 3..8）；compare=标记间隔 vs 物体两端 |
| State P0 | ruler interaction | marks（放置顺序，0/1/2 个）；第三点清空重放 |
| Interaction P0 | marker / endpoint movement | **点刻度放标记**（两步夹两端）；清标记/撤销/重置 |
| Response P0 | expected measurement | data={marks,span,reading,answer,object,structure}；answer=间隔（=5） |
| Evaluator P0 | tolerance evaluator | evaluateMeasurement：EMPTY→PASS(aligned)→from_zero_reading→wrong_span |
| Evidence P0 | **起止点、读数** | marks=[3,8] 起止 + reading 末读数 + span 差值（E2E-04 断言全链） |
| Diagnosis P0 | **刻度读取错误** | from_zero_reading——{0, right} 精确命中"对齐 0 才开量"惯性错误（answer=8≠5 判错+分诊） |
| Acceptance P0 | E2E | 10 用例全过（见 §4） |

## 2. 解耦的第七次运用（R08/R15 形态：判对+留痕）

量尺场景的"对"有两层：**数值对**（间隔=物体长）与**操作对**（标记恰好夹住物体两端）。
金题把被测物体故意放在 3..8（非零起点），产生平移段靶 {4,9}：
span=5 恰等于 expected → 后端 correct=true，但 `structure.aligned=false`——
"量对了=后端判、夹没夹住两头=结构层说"（E2E-06 双断言实证）。
教学含义：间隔碰巧相等不代表孩子真的理解"夹住物体"，Evidence 保住这层差异。

**判错侧（R14/R15 同形态）**：from_zero_reading 把"零起误读"从笼统 wrong_span 里精确分出来——
同样是 correct=false，诊断链能区分"对着 0 量到右端（惯性错误）"与"随便夹错一段"。
parser 守卫 `left≥1` 保证该靶 span=right≠length **必判错且与 PASS 互斥**（否则 left=0 时
{0,right} 就是正解本身，分诊名存实亡）——延续 R15"每个 FAIL 态必须有可达且互斥的靶"。

## 3. 与 Gap 原文差异（如实记录）

- Gap Evaluator="tolerance evaluator"（容差判分）：本 Gate 物体两端落**整数刻度**、答案=整数间隔，
  走标量相等判分（冻结链不动）；容差语义留待生活题库出现非整刻度物体时启用（前端结构层已能
  算 span/diff_to_length 原料，届时判分层加 tolerance 即可，不破坏本 Gate 契约）。
- Gap Interaction="marker / endpoint movement"（拖拽端点）：本 Gate 交互=**点刻度放标记**
  （儿童可靠性口径同 R07/R08/R12/R14：点选替代拖拽，轨迹一样可证）。
- 第三点行为=清空重放（非拒绝）——符合低龄"再点就是重来"心智；重放事实进 RULER_MARK_SET payload
  `restarting:true`，Evidence 不丢。原基座 Ruler（range 滑条读数）保留在 V2RendererLibrary 作参考。

## 4. E2E 用例（10 例，全绿）

| 用例 | 验证 | 结果 |
|---|---|---|
| E2E-01 (G1) | 渲染不降级：0/20 刻度可见、铅笔 data-left/right=3/8 | ✅ |
| E2E-02 (G2) | 标记<2 拦提交（EMPTY 两态提示文案分流） | ✅ |
| E2E-03 | 对准两端 {3,8}→marked 样式+PASS 提示+提交可用 | ✅ |
| E2E-04 (G4/G6) | envelope：type=ruler、answer={value:5}、marks=[3,8]、RULER_MARK_SET×2、无 representation 泄漏 | ✅ |
| E2E-05 | from_zero_reading 专项：{0,8}→false+HINT+文案"放在 0 上" | ✅ |
| E2E-06 | **解耦靶**：{4,9}→correct=true + structure.aligned=false 双断言 | ✅ |
| E2E-07 (G5/G7) | 修正路径：误读→清标记回 EMPTY→对准→NEXT_TASK attempt_no≥2 | ✅ |
| E2E-08 | 第三点重放语义 | ✅ |
| E2E-09 | dblclick 防重入=1 attempt | ✅ |
| E2E-10 | healing 皮肤同链判对 | ✅ |

## 5. API 实证记录（pin=1f23c045-615a-451a-9090-61c3d5d55013）

① pin 下发 ruler（config.object=[3,8]）；② 零起误读 8→correct=false+HINT；
③a 同 submission 重放→200 同 attempt_id；③b 同 submission 异内容→409；
④ PASS 5（attempt_no=2）→correct=true+NEXT_TASK。
（手测全程带递增 attempt_no——R15 坑口径已固化进流程。）

## 6. Batch E 进度

**1/4**：Ruler(R16) ✅ → 余 Clock(R17)、MoneyBoard(R18)、PatternBoard(R19)。
Vertical Gate 总进度 **16/19**。
