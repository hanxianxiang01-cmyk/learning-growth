# R14 SortingBoard Vertical Gate 验收底表（FE-1426）

状态：**CLOSED**（2026-10-07）｜ 模板：B5 五件套第十三实例 ｜ 上游：docs/frontend/31 Gap R14（Batch D 第三题）

## 1. Gap R14 条目对照

| Gap 条目 | 要求 | 落地 |
|---|---|---|
| Semantic P0 | compare / classify / order | 数字卡按数值维度 compare→order；classify=三分类评估（正序/降序/视觉序） |
| State P0 | sorting process | EMPTY(零交换)→PASS→reversed→dimension_confusion→disordered（三 FAIL 态互斥） |
| Interaction P0 | drag/drop | **两步点选交换**（点第一张=拿起、点第二张=换位）替代拖拽（儿童可靠性口径，见 §3） |
| Response P0 | expected ordering | data={order,order_values,swaps,swap_count,answer,structure}；answer=数值升序拼接整数 |
| Evaluator P0 | order evaluator | evaluateSorting：与三参考序（target/reversed/visual）逐一比对，互斥分诊 |
| Evidence P0 | 排序过程 | swaps=[[from,to]…] 交换序列 + order/order_values 轨迹（E2E-05 断言 swaps=[[0,1],[1,3]]） |
| Diagnosis P0 | **比较维度错误** | dimension_confusion——**卡面字号（visual_rank）与数值故意错开**做干扰维度，按字号排精确命中此态 |
| Acceptance P0 | E2E | 11 用例全过（见 §4） |

## 2. 解耦的第五种形态（与前四次不同，如实记录）

前四次解耦（R08 transpose / R11 近似数方向 / R12 attribute_confusion / R13 not_right_angle）
的共性是**"判对 + 结构原料留痕"**——答案值恰等于 expected，后端 correct=true，但前端结构报非 PASS。

R14 是**另一种**：dimension_confusion（视觉序 1274）与 reversed（7421）的**答案值本身就 ≠ 正解 1247**，
所以后端判 correct=false。价值不在"判对留痕"，而在**"判错时能精确说出错的方式"**：
同样是 correct=false，`structure.error` 能区分"按字号排的（比较维度错）""方向反了""就是没排对"三种，
诊断链据此给不同 hint。这是解耦架构的对称补充——**判对能带原料，判错也能带分诊**。

parser 守卫保证三态互斥：visual 序既 ≠ 正序也 ≠ 降序（否则 dimension 与 reversed 重叠失效）。

## 3. 与 Gap 原文差异（如实记录）

Gap Interaction=drag/drop：本 Gate 交互是**两步点选交换**（点 A 再点 B=换位），不依赖 HTML5 拖拽——
儿童可靠性口径（drag 在触屏/低龄段失败率高），交换语义与拖拽等价且 swaps 轨迹一样可证。
原基座 SortingBoard（↑↓ 逐格移动）保留在 V2RendererLibrary 作参考。

## 4. E2E 用例（11 例）

| 用例 | 验证 | 结果 |
|---|---|---|
| E2E-01 (G1) | 渲染不降级：4 卡乱序 + **干扰字号显性化**（数字 1 卡字号 36px 最大、数字 4 卡 15px 最小）| ✅（首跑坑：`toHaveStyle` 是 Testing-Library API，Playwright 用 `toHaveCSS`） |
| E2E-02 (G2) | 零交换拦提交（EMPTY）；只拿起不算交换 | ✅ |
| E2E-03 | 两步点选交换生效（位置互换）| ✅ |
| E2E-04 | toggle 放下（再点同一张取消选中）| ✅ |
| E2E-05 (G4/G6) | envelope：type=sorting_board、data 五字段、**swaps=[[0,1],[1,3]] 交换轨迹**、无 representation 泄漏、SORT_CARD_* 事件 | ✅ |
| E2E-06 | **dimension_confusion 专项**：按字号排 1274→判错 + "字的大小"提示（Diagnosis P0 落地）| ✅ |
| E2E-07 | reversed 靶：7421 判错 + "方向反啦" | ✅ |
| E2E-08 (G5/G7) | 修正路径：disordered→再交换→PASS 1247 NEXT_TASK、attempt_no 递增 | ✅ |
| E2E-09 | 退回上次交换（applyUndoSwap 原子撤销末次）| ✅ |
| E2E-10 | dblclick 防重入只 1 POST | ✅ |
| E2E-11 | healing 双皮肤同链 | ✅ |

## 5. 金题与回归

- **V2-R14-SORT-001 把数字卡从小到大排好**（答案=1247，school_objects，**app_rd 第二题**——R06 位值后该节点再链）已 seed 真实 RDS；防漂移+1（后端 97→**98 passed**）
- API 四连（pin 首抽即中）：dimension 1274 false HINT / reversed 7421 false / PASS 1247 NEXT_TASK / 重放同 attempt_id
- node 语义矩阵全过（三 FAIL 态互斥、四拒绝码 NO_SELECTION/SAME_CARD/NO_SUCH_ITEM/NO_SWAP、config 六守卫：initial≠target/visual≠target&reversed/desc 拒/两位数拒/重复值拒/档位非排列拒）
- 全量 E2E **127/127 零回归**（十三套 Gate）；tsc 0 / 六 check PASS

## 6. Batch D 状态

**3/4**：ShapeGallery(R12) ✅ ShapeCanvas(R13) ✅ SortingBoard(R14) ✅ → 余 DirectionGrid(R15)。

**Vertical Gate 总进度：14/19**。
