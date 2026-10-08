# R17 Clock Vertical Gate 验收底表（FE-1430）

状态：**CLOSED**（2026-10-08）｜ 模板：B5 五件套第十六实例 ｜ 上游：docs/frontend/31 Gap R17（Batch E 第二题）

## 1. Gap R17 条目对照

| Gap 条目 | 要求 | 落地 |
|---|---|---|
| Semantic P0 | hour / minute / time relation | 钟面时针(短)/分针(长)两针职责 + 整时/半点组合 |
| State P0 | hand movement / answer | (h,m) + adjust_history（每笔 [hand, from, to]） |
| Interaction P0 | hour/minute hand manipulation | **点数字拨短针**（1..12）+ **点整点/半点拨长针**（0/30）——SVG 点选替代拖拽（儿童可靠性口径） |
| Response P0 | expected time | data={h,m,time_text,adjust_history,answer,structure}；answer=总分钟 h*60+m（6:00→360） |
| Evaluator P0 | time evaluator | evaluateClock：EMPTY→PASS→hand_swap→wrong_time（分钟差原料） |
| Evidence P0 | 指针调整过程 | adjust_history=[["hour",3,6]]（E2E-04 断言） |
| Diagnosis P0 | **时针/分针关系错误** | hand_swap——把**长针指着的数字**当时针读（6:00 长针在 12 → 拨成 12:00，answer=720≠360）精确命中 |
| Acceptance P0 | E2E | 10 用例全过（见 §4） |

## 2. 分诊靶形式化（hand_swap）

二年级真实错法："6 点整时**长针指着 12**，那时针应该读 12"——即互换两针读数语义。
形式化：`swapOf(target) = { h: target.m===0 ? 12 : target.m/5, m: target.m }`
（长针所在钟面数字 m/5 被当成时针读数；分针档保持不变）。

parser 守卫（延续 R15"每个 FAIL 态必有可达且互斥靶"纪律）：
- swap 态必须是合法组合；
- swap 态 ≠ target（目标 12:00 的互换=自身→该题被拒，配置层消灭退化）；
- answer(swap)≠answer(target)（720≠360，后端必判错——判错+分诊形态）。

## 3. 与 Gap 原文差异（如实记录）

- 口径=**整时/半点**（二年级认识时间单元）：m∈{0,30}；Gap"expected time"落地为
  总分钟数标量（60 粒度，不动判分冻结链；文本 `H:MM` 形态在 time_text 原料里）。
- Gap Interaction="hand manipulation"（拖拽指针）：本 Gate=点数字/点档位（同 R07/R08/R12/R14/R16 儿童可靠性口径）。
- 分针只有两档按钮（整/半点）而时针 12 个数字位——不对称是刻意的：分针 30 分一格，12 个数字全点对低龄段噪音过大；差异如实记录。
- 原基座 Clock（`<input type="time">`）保留在 V2RendererLibrary 作参考；专件已替换路由分支。

## 4. E2E 用例（10 例，全绿）

| 用例 | 验证 | 结果 |
|---|---|---|
| E2E-01 (G1) | 钟面 12 数字、初始 3:00（3 与"整点"picked） | ✅（坑：picked class 在 SVG `<g>`（testid 层）与 `<circle>` 双层镜像——首跑只加 circle 导致 g 断言 30s 超时） |
| E2E-02 (G2) | 零拨针拦提交（EMPTY） | ✅ |
| E2E-03 | 拨针生效：点 6 → picked 迁移 + 时针 transform rotate(180 100 100) | ✅ |
| E2E-04 (G4/G6) | envelope：type=clock、answer={value:360}、time_text、adjust_history、CLOCK_HOUR_SET、无泄漏 | ✅ |
| E2E-05 | hand_swap 专项：点 12→false+HINT+文案"看着长针指的数字读钟" | ✅ |
| E2E-06 | 半点链：长针 30 + 6:30 合法组合 + 差 30 分钟提示 | ✅ |
| E2E-07 (G5/G7) | 修正路径：swap 判错→拨 6→NEXT_TASK attempt_no≥2 | ✅ |
| E2E-08 | UNDO 回末次拨针；RESET 回 3:00 + EMPTY 拦提交 | ✅ |
| E2E-09 | dblclick 防重入=1 attempt | ✅ |
| E2E-10 | healing 皮肤同链判对 | ✅ |

## 5. API 实证记录（pin=814b32f1-a3ac-4d7c-9ae2-6c39fbd6c84f）

① pin 下发 clock（start[3,0]/target[6,0]）；② hand_swap 720→false+HINT；
③a 重放同 attempt_id；③b 异内容 409；④ PASS 360→true+NEXT_TASK。

## 6. 词表进展

**time_schedule 族首题真实覆盖**（此前"启用但零覆盖"记录解除——context_family.py 注释与
CONTEXT_FAMILY_VOCABULARY.md 的"零覆盖"口径在下批题库文档统一更新）。

## 7. Batch E 进度

**2/4**：Ruler(R16) ✅ Clock(R17) ✅ → 余 MoneyBoard(R18)、PatternBoard(R19)。
Vertical Gate 总进度 **17/19**。
