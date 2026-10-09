# FE-1432g：155_question_bank_delivery_v2 权威验收审查（Gate 1~3）

- 审查对象：`/Users/hanxianxiang/Downloads/学习/儿童学习成长系统/155_question_bank_delivery_v2`（交付方 A/B/C 三路径整改批，2026-10-09 19:00 上传）
- 审查工具：我方权威 Gate 2 `consistency_audit.py` v2 + Gate 3 `audit-155-config.mjs`（仓库 main 版复跑）
- 结论：**Gate 1/2 全过；Gate 3 PASS 85 / FAIL 37（B 26 + C 11）。FAIL 根因＝§7 执行指令未成文全部 parser 守卫/形态（部分在 §2 金样例有展示但未要求逐字核对；另有 2 处我方笔误/诱导直接致错）——本 PR 已全部补进 CONTRACT §7；交付方按 §3 修复清单重交 37 题增量包。Gate 4~8 待修复版再审。**

## 1. 包完整性核验（全部通过）

| 项 | 结果 |
|---|---|
| A/B/C 题数 42+86+27=155，无重复、无交叉、与原 trial155 ID 集合一致（0 新增 0 丢失） | ✅ |
| DELIVERY_MANIFEST 155 行、分类与实际文件归属 0 不符 | ✅ |
| C 类按"B∩C 归 C"扩容 18→27（新发现 9 题内伤），未强行凑参考数 | ✅ 处置正确 |
| 我方 Gate 2 v2 复跑：A 0 / B 0 / C 0 违规 | ✅ 与自报一致 |
| 验收纪律：明示 Gate 3~8 未跑、80 题诊断词待核、映射 PENDING——无虚报 PASS | ✅ |

## 2. Gate 3 权威复跑：PASS 85 / FAIL 37 / 基座链无 parser 33

FAIL 分布：direction-grid 8、clock 8、formula-board 8、money-board 7、shape-canvas 4、grouping-board 2。

**责任切分（诚实口径）**：37 题**全部可追至我方契约文档债**——§7 指令写于 FE-1432b 时代（当时 Batch E 的 R15~R18 尚未打 Gate，守卫值域/形态只散在各 R 底表与 parser 源码，从未汇总成验收条款）。细分：
- **我方笔误直接致错**：shape-canvas 4 题（§7 写 rectangle/triangle，parser 只收 rectangle——交付方照做被拒）
- **我方诱导措辞致错**：money 找零 4 题（§7"change 题自查 paid−price=answer"暗示找零玩法存在，实际 R18 只有凑付）
- **我方守卫/形态未成文**：grouping 2、formula 8、direction 8、clock 8、money price 值域 3 题（§2 金样例部分有暗示但 §7 执行指令未点名，交付方无从查 parser 源码）

不存在"交付方看得到条款却故意违反"的实锤——本轮整改态度与产出质量均良好（Gate 2 从 216→0、ID/分类/MANIFEST 零缺陷）。**本次已把全部守卫补进 §7 成文**，同时立规矩：FE-1434 契约 FROZEN 时必须吸收"parser 守卫全集"进正文（散在底表=没有契约）。

## 3. 逐类修复清单（交付方执行）+ 契约勘误（我方执行，随本 PR）

### ① grouping-board（071/072）· 我方漏条 + 交付方改数据
`items=21/24` 超 parser 值域 `[2,20]`（§2 表当时只点名"items 非整除"、未写值域）。
→ **契约已补** items∈[2,20]；交付方改 items≤20 并保 total/group_size 自洽。

### ② formula-board（073~080，8 题）· 我方漏条（§2 金样例展示过 `{t,v}` 但 §7 未要求逐字核对）
tokens 用 `{type,value}`——我方 parser schema 是 **`{t,v}`**（t∈num|op|eq|slot），且 slot 需 `accept:"number"|"operator"`、id 全题唯一。数值语义全对，纯字段改名。
→ **契约已补** tokens 形态成文；交付方逐 token 改 `type→t, value→v`，slot 加 accept。

### ③ shape-canvas（098/100/102/104，4 题）· **我方笔误**
§7 原文"target 限定 rectangle/**triangle**"——**triangle 是我方笔误**（与 §2 表/§2 金样例/R13 parser 三处矛盾：parser 仅接受 `target_shape:"rectangle"`，三角形评估不在 R13 范围）。交付方照 §7 做了 4 道三角形题，被 parser 拒。
→ **契约已勘误** §7 = rectangle only；交付方 4 题改矩形可分解尺寸（base×height=area 均在点阵内），或删题另补。

### ④ direction-grid（113~120，8 题）· **我方漏条**
坐标已全部改 0 起、去纯直线（原 6 题内伤修复 ✓），但 8 题反走终点 `(2·sr−tr, 2·sc−tc)` 落盘外——**R15"反走靶必须可达"守卫从未成文**（只在 R15 底表），且 4×4 小盘放不下合规反走靶。
→ **契约已补**守卫公式 + 建议 5×5 盘与金样例（start(2,2)→target(3,4)，反走靶 (1,0) 盘内，answer=19）；交付方按公式换坐标重出 8 题。

### ⑤ clock（129~136，8 题）· **我方漏条**
R17 parser `readTime` **仅接受数组** `start:[h,m]`、`target:[h,m]`——§2 金样例写了数组，§7 指令未点形态，交付方写了 `{hour,minute}` 对象＋`*_pair` 双写保险，全被拒。8 题数值语义（含 210=3:30 半点链）全部合规，纯格式转换。
→ **契约已补**形态成文；交付方 8 题改数组、删冗余 pair 字段。

### ⑥ money-board（137/139/140 + 141~144，7 题）· 我方诱导 + 漏条
- **137/139/140**（凑付类）：price=8/28/68 非 5 倍数——R18 双守卫 `price%5==0 && price%10!=0`（角位非零 5 倍数，保混淆靶与 PASS 互斥）未成文。改 price（15/25/65 类）并保持金额自洽。
- **141~144**（找零类 paid/price）：Gate 2 一致性已修自洽 ✓，但 **R18 实现只有"凑付"交互，无"付钱找零"**——§7 原文"change 题自查 paid−price=answer"是**我方诱导措辞**（当时意在修数据内伤，未声明玩法边界）。
→ **契约已补** price 值域守卫成文 + 明示"R18 无找零玩法：找零题必须改造成凑付题（price=目标金额）或换挂 number-input"；交付方 4 题改造。

## 4. 先行放行评估

Gate 3 已过 85 题 + 基座链 33 题（宽松 config、无硬拒）= **118 题具备进 Gate 4~7 条件**。建议按任务单流程：37 题修复增量包到齐后整批一次进 Gate 4~7（抽 5%≥8 题 pin 实灌，覆盖全部出现 renderer）→ Judge/Evidence/Diagnosis → Gate 8 qa_replay。如需提速，可先行对 118 题抽样 E2E——但 seed 入库仍以整批 8-Gate 全过为门槛。

## 5. 随勘误发交付方两件套

1. **勘误后 CONTRACT.md**（§7/§8 补 9 条守卫/形态成文，责任标注清晰）
2. **ERROR_VOCAB.md**：19 Gate `structure.error` 权威词表全量（交付方 80 题诊断词待核项的对照底稿）——从各 V2 parser 源码提取，见本目录。

**诊断词预扫结果（代交付方完成其声明的待核项）**：155/155 题带 error_models，对照 ERROR_VOCAB 越表实例 65 处、**但只有 2 种词**——`strategy`×57、`calc`×8（均为借用其他渲染器行的合法词、跨行误用，非新造词）。修复规则简单：按题的 renderer 从 ERROR_VOCAB 对应行改选（如 bar-model 的 strategy→modeling/relation/calc 之一）；随 37 题修复增量一并改即可，不单退。

## 6. 本轮正面记录

- 交付方整改质量显著提升：Gate 2 从 216 条→0 条；ID/分类/MANIFEST 零缺陷；C 优先原则运用正确；待决项全部如实声明（未收到 fixtures 就不声称复跑）。
- 37 题 FAIL 暴露的根因**主要在我方契约文档**而非交付方糊弄——这恰好证明 8-Gate 链"机器门逐题过、文档逐条修"的价值：契约从"答案轴级"补全到"守卫级"。
