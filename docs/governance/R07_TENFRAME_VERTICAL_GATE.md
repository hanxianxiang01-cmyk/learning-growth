# R07 TenFrame Vertical Gate（FE-1416）

状态：**CLOSED**（2026-10-04）｜ 模板：B5 五件套第四实例 ｜ 上游：docs/frontend/31 SEM-1416 / Gap R07

## 1. 组件语义

ten-frame（V2 mode `quantity_structure`）：20 以内数量的"十与一"结构。
- **连续填充**（教学纪律）：点第 i 格=填到 i+1 或收缩到 i，不允许跳格留洞；
- **补十打包**（本 Gate 独有语义）：满 10 → `MAKE_TEN_COMPLETED` 事件 → 冻结为"一袋十"（tens+1），计数转第二框；`TEN_BROKEN` 反向拆开（拆十回退教学动作）；
- 答案 = tens×10 + count；quantity evaluator 对 target：EMPTY 拦提交，PASS∪FAIL 可达后端（P0-01 口径）。

## 2. 五件套对照

| 件 | 实现 | 证据 |
|---|---|---|
| mode Schema | `parseTenFrameConfig`（target 1~20 整数守卫、max_frames 默认 2） | tsc 0 |
| 链题 | R07 金题（app_rel d2 糖果装袋 13=1袋+3散，**sharing 族首题**，ten_frame）seed RDS | API 钉题命中 |
| Evaluator | `evaluateQuantity` 三态（对 target）；连续填充/越界在纯函数层拒绝 | R07-G2 |
| Evidence | data={tens, current_frame_count, total}——**十与一分解本身即结构证据**；事件 COUNTER_ADDED/REMOVED、MAKE_TEN_COMPLETED、TEN_BROKEN、UNDO、RESET | R07-E2E-01 断言链 |
| 浏览器 E2E | `e2e/r07-ten-frame.spec.mjs` 8 用例 | **8/8 passed**（含 healing） |

## 3. G1~G9 对照

G1 渲染不降级 ✅；G2 连续填充语义（点第5格=填5个非留洞；再点第2格=收缩到2）✅——**模板首次覆盖"拒绝式交互"负例**；G3 EMPTY 拦提交 ✅；G4 envelope 合同（type=ten_frame、tens=1、count=3、total=13）✅；G5 make-ten 全链（摆满→打包→续摆→判对→NEXT_TASK）✅；G6 错位 12 可提交→HINT ✅；G7 重试 attempt_no=2、补 1 格改对 ✅；G8 UNDO 回退打包态验证（12 撤销链）✅；G9 回归 ✅——**全量套件 35 passed**（B5 9 + R01 11 + R04 7 + R07 8 零回归）。双皮肤 healing ✅。

## 4. 模板增量

1. **新能力词 `fill`/`grouping`** 进 InteractionCapability + KNOWN_CAPABILITY_IDS 名单（名单机制第二次拦住漂移——ten-frame descriptor 与金题 capabilities 全对齐）；
2. **专件替换基座**：TaskRenderer 从 V2RendererLibrary 基座 TenFrame 切换到独立 TenFrameV2（基座组件保留作未来组件模板参考，路由优先专件——check-v14-renderers 断言兼容）；
3. **sharing 族第一题**：context_family 词表 6/7 族开始有真实覆盖（time_schedule 后第二个新族落题）。

## 5. 遗留

- 20 以上（3 框）不支持：max_frames 可扩展但 UI 未做多袋陈列优化——V1.4 范围外；
- R07 金题暂 1 道；retention/transfer 变式属内容线。

## 6. Batch A 状态

**Batch A 4/4 完成**：NumberLine（A5，FE-1405/1408 已闭）+ ObjectCounter（R01）+ NumberInput（R04）+ TenFrame（R07）。
**Vertical Gate 总进度：5/19**（A5/B5/R01/R04/R07，均按 docs/frontend/31 Release Scope 计数）。Batch B 起：BarModel(R02) / PlaceValue(R06) / ColumnArithmetic(B5 已闭)。
