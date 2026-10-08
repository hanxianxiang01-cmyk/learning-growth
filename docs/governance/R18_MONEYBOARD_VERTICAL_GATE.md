# R18 MoneyBoard Vertical Gate 验收底表（FE-1431）

状态：**CLOSED**（2026-10-08）｜ 模板：B5 五件套第十七实例 ｜ 上游：docs/frontend/31 Gap R18（Batch E 第三题）

## 1. Gap R18 条目对照

| Gap 条目 | 要求 | 落地 |
|---|---|---|
| Semantic P0 | money / amount / change | 人民币四档（1角/5角/1元/5元）凑付商品价；元角换算 |
| State P0 | select / compose / calculate | counts（面额→枚数）+ selection_history（每次 ±1） |
| Interaction P0 | money selection / exchange | 点档=拿一枚上台面，「取回」=放回去（12 枚上限防呆） |
| Response P0 | expected amount/change | data={counts,coins,total,total_text,selection_history,answer,price,structure}；answer=总角数（35） |
| Evaluator P0 | monetary evaluator | evaluatePayment：EMPTY→PASS(uses_extra)→denomination_confusion→underpaid/overpaid |
| Evidence P0 | 选择与换算过程 | selection_history=[[denom,±1]…] + counts 终态 + min_coins 对照（E2E-04 断言） |
| Diagnosis P0 | **面值/金额关系错误** | denomination_confusion——把「5角」当「5元」数（3枚1元+**5枚**5角=55角≠35）精确命中 |
| Acceptance P0 | E2E | 10 用例全过（见 §4） |

## 2. 解耦的第八次运用（R08/R15/R16 同形态：判对+留痕）

"付对钱"也有两层：**数值对**（总角数=价格）与**换算对**（用了最少币的最优组合）。
金题 3 元 5 角产生笨凑法靶 {10×2, 5×3}：total=35 恰等于 expected → 后端 correct=true，
但 `structure.uses_extra=true`（5 枚 > 贪心最少 4 枚）——钱凑没凑对=后端判、
换得笨不笨=结构层说（E2E-06 双断言实证）。教学含义：会用大币换小币（5角×2=1元）
是"策略选择"能力（本节点 app_strat）的过程性证据，答案对了不代表会换。

**判错侧（R14/R15/R17 同形态）**：denomination_confusion 把"5 角当 5 元"的惯性错法
从笼统 overpaid 里精确分出——同样是 correct=false，诊断链能区分"面值数错"与"多拿/少拿"。
parser 守卫双保险（延续 R15~R17"每个 FAIL 态必有可达互斥靶"纪律）：
1. 价格角位必须为 5 的非零倍数——整十价（如 30 角）混淆靶退化=正解本身，拒；
2. 钱包必须含 5 角与 1 元两档——混淆靶 {10×元位, 5×角位} 不可组时名存实亡，拒。

## 3. 与 Gap 原文差异（如实记录）

- Gap Response="expected amount/**change**"（找零）：本 Gate 口径=**正好凑付**（无找零链）——
  付多/付少直接给 overpaid/underpaid 差值原料；找零题（付 5 元买 3 元 5 角）留待题库包
  以多 workspace 或新 mode 扩展，不破坏本 Gate 契约。
- 答案单位=角（35）而非"3元5角"复合文本：保标量相等判分（冻结链）；`total_text` 原料供
  诊断/家长报告可读展示。
- 币数上限 12（OVER_LIMIT）：低龄防呆（超出后计数失控），拒绝事实不入 Evidence 链。
- 原基座 MoneyBoard（单档+1 累加滑显）保留在 V2RendererLibrary 作参考；专件已替换路由分支。

## 4. E2E 用例（10 例，首跑全绿）

| 用例 | 验证 | 结果 |
|---|---|---|
| E2E-01 (G1) | 四档钱包渲染、价格"3元5角" | ✅ |
| E2E-02 (G2) | 零币拦提交（EMPTY） | ✅ |
| E2E-03 | 拿币/取回生效 + underpaid 提示 | ✅ |
| E2E-04 (G4/G6) | envelope：type=money_board、answer={value:35}、counts={10:3,5:1}、total_text、uses_extra=false、MONEY_COIN_ADDED×4、无泄漏 | ✅ |
| E2E-05 | denomination_confusion 专项：{10×3,5×5}→55→false+HINT+文案"把 5角 当成 5元" | ✅ |
| E2E-06 | **解耦靶**：{10×2,5×3}=35→correct=true + structure.uses_extra=true 双断言 | ✅ |
| E2E-07 (G5/G7) | 修正路径：混淆→取回 4 枚 5 角→正好→NEXT_TASK attempt_no≥2 | ✅ |
| E2E-08 | 取回下限（该档为 0 禁用）+ 拿空回 EMPTY | ✅ |
| E2E-09 | dblclick 防重入=1 attempt | ✅ |
| E2E-10 | healing 皮肤同链判对 | ✅ |

## 5. API 实证记录（pin=b978d294-7ea5-4670-8538-3c04c2113536）

① pin 下发 money-board（price=35/四档）；② confusion 55→false+HINT；
③a 重放同 attempt_id；③b 异内容 409；④ PASS 35→true+NEXT_TASK。

## 6. Batch E 进度

**3/4**：Ruler(R16) ✅ Clock(R17) ✅ MoneyBoard(R18) ✅ → 余 PatternBoard(R19)。
Vertical Gate 总进度 **18/19**。
