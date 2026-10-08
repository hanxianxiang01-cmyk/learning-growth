# 消费索引：V1.4_P0_Trial_155（155 题试灌包审计轮，2026-10-08）

**判定：内容首次为真（真题文本+答案+词表合规），但与我方 Gate 实战契约存在系统性
语义错位——不作为可入库资产；产出《Renderer Config 契约对照表》（CONTRACT.md）
作为交付方扩产 3,108 前的对齐依据。**

## 三轮审计数据

| 轮 | 手段 | 结果 |
|---|---|---|
| ① 断言复核 | 7 条交付断言逐项实测 | prompt 真文本✅ / answer 全有✅ / 19 renderer 齐✅（上包缺的 ten-frame/estimation-canvas 已补）/ 7 app_* 全有题✅ / context_family **零越表**✅ / role 八类✅ / mapping 状态如实标 PENDING✅ ——**内容态度合格** |
| ② config×parser 硬审 | `audit-155-config.mjs`（我方 15 专件 parser 直接吃题包 config） | 专件 122 题：**PASS 8 / FAIL 114（93%）**；基座链 41 题宽松不硬拒 |
| ③ 垫片转换再审 | `convert_trial155.py`（字段名/答案提取归一）| 可转换 92 / **语义缺口拒转 22**（sorting 8+formula 6+gallery 8）；转换后 PASS 51 / FAIL 41——**字段错位占 1/3 可救，答案轴错位占 2/3 只能重导** |

## 关键发现

1. **答案语义轴冲突是主矛盾**（详见 CONTRACT.md §2）：direction-grid 答"步数"vs 我方"终点编码"、shape-canvas 答"形状名"vs 我方"面积数值"、sorting-board 是"分类"不是"排序"、pattern-board 是"等差数列"不是"ABAB 颜色周期"——这些**不可机器转换**，交互与评估器整体不同族。
2. **交付方数据内伤 18 题**（CONTRACT.md §3.5）：money-board change 题 paid−price=0 却答 64、direction-grid 坐标 1 起越界、clock 起点 2:15 超两档 UI、pattern 多位数答案——题包自带 schema 校验全查不出，**逐题一致性审计必须进交付流水线**。
3. **diagnosis 词表零重合**：题包 error tag（direction_or_position_error 等 20 种）与我方前端 structure.error（direction_reversed 等 19 Gate 定稿词）不对齐，诊断观察匹配永不命中。
4. 唯二亮点：context_family 全在受控词表内；ability_mapping_status 诚实标 PENDING 没装冻结。

## 处置

- **不 seed、不入库**（与 #68 口径一致）；临时转换器降级为审计分析工具，不作入库通道。
- **本目录 CONTRACT.md = 发给交付方的对齐依据**：7 类必改（~62 题）+ 格式统一 4 条 + 可直接沿用清单（~45 题 29%）+ 18 题数据内伤修正。
- `audit-155-config.mjs` 保留为**每批题入库前的验收门禁**（交付方重导后先跑②再审一次）。
- V1.4 收官链照旧不阻塞：FE-1433 qa_replay#7 → FE-1434 契约 FROZEN → FE-1435 立版。
