# R13 ShapeCanvas Vertical Gate 验收底表（FE-1425）

状态：**CLOSED**（2026-10-07）｜ 模板：B5 五件套第十二实例 ｜ 上游：docs/frontend/31 Gap R13（Batch D 第二题）

## 1. Gap R13 条目对照

| Gap 条目 | 要求 | 落地 |
|---|---|---|
| Semantic P0 | draw / compose / transform | draw=点钉加顶点、compose=自动闭合多边形、（transform 见 §3 差异） |
| State P0 | drawing lifecycle | EMPTY(<3)→vertex_count→not_right_angle→wrong_size→PASS 五态生命周期 |
| Interaction P0 | draw / move / rotate / delete | draw=点钉、delete=撤一个点/清空；**move/rotate 以"撤点重画"点序重建替代**（儿童可靠性口径不依赖拖拽，见 §3） |
| Response P0 | expected geometry constraints | data={vertices,vertex_count,area,right_angles,answer,structure}；constraints={vertex_count:4,right_angles:4,area:6} |
| Evaluator P0 | geometry evaluator | evaluateShapeCanvas：shoelace 面积（整数二倍面积免浮点误差）+ 点积直角判定（4/4 才过） |
| Evidence P0 | 绘制轨迹 | vertices 点击序（E2E-04 轨迹序断言）+ SHAPE_POINT_ADDED order 序号 + SHAPE_POINT_DELETED/REJECTED |
| Diagnosis P0 | 几何属性错误 | error 三分类原料入 structure；**解耦靶=平行四边形面积恰=6 → 后端判对 + not_right_angle 留痕**（第四次运用） |
| Acceptance P0 | E2E | 11 用例全过（见 §4） |

## 2. 几何评估器要点

- **shoelace 整数运算**：`doubledSignedArea` 二倍有向面积（叉积和），`polygonArea=abs/2`——纯整数免浮点误差，顺/逆时针同结果（E2E 顺时针长方形 PASS 实证）
- **直角判定**：四边形每个顶点相邻两边向量点积==0（整数）；直角个数随 Evidence 下发（`right_angles:0..4`）
- **判定顺序**：EMPTY(<3 点)→vertex_count(≠4)→not_right_angle(≠4 直角)→wrong_size(面积≠6)→PASS——**形状属性错优先于尺寸错**（Diagnosis P0 权重）
- config 守卫：grid 4~6、target_area 2~(grid-1)²、target_shape 暂只 rectangle（词表守卫）

## 3. 与 Gap 原文差异（如实记录）

Gap Interaction 列 move/rotate：本 Gate 交互模型是"点钉画多边形"，**没有对象级拖拽/旋转**——
以"撤点重画"（delete+re-draw）覆盖同等教学语义（改图形=改顶点）。原基座 ShapeCanvas
（resize/move 单个图形）保留在 V2RendererLibrary 作参考。若未来 release 需要真 rotate，
在顶点序上实现=坐标变换纯函数，不影响现有 Evidence 结构。

## 4. E2E 用例（11 例）

| 用例 | 验证 | 结果 |
|---|---|---|
| E2E-01 (G1) | 渲染不降级：5×5 点阵 25 peg | ✅ |
| E2E-02 (G2) | <3 点拦提交（EMPTY） | ✅ |
| E2E-03 | 三角形 FAIL 可达后端（vertex_count） | ✅ |
| E2E-04 (G4/G6) | envelope：type=shape_canvas、data 四字段、**vertices 点击序={x,y} 对象轨迹**、4×SHAPE_POINT_ADDED、无 representation 泄漏 | ✅（首跑断言形态笔误：数组对 vs 对象，修正后过） |
| E2E-05 | **解耦双断言**：平行四边形面积 6→correct=true + 歪斜提示 | ✅ |
| E2E-06 | wrong_size（2×2 面积 4）→false HINT | ✅ |
| E2E-07 (G7) | 修正路径：撤点重画 3×2→true NEXT_TASK、attempt_no 递增 | ✅ |
| E2E-08 | 重复点拒绝（taken peg 不增顶点） | ✅ |
| E2E-09 | dblclick 防重入只 1 POST | ✅ |
| E2E-10 | UNDO 单步 + 撤点回 EMPTY | ✅ |
| E2E-11 | healing 双皮肤同链 | ✅ |

## 5. 金题与回归

- **V2-R13-CANVAS-001 钉子板上画一个长方形**（答案=面积 6，school_objects，**app_model 第三题/第四能力节点链**）已 seed 真实 RDS；防漂移+1（后端 96→97）
- API 四连（pin 首抽即中）：解耦 true+原料 / wrong_size false / PASS NEXT_TASK / 重放同 attempt_id
- node 语义矩阵全过（含凹四边形/顺时针/config 三守卫/MAX_VERTICES）
- 全量 E2E **116/116 零回归**（十二套 Gate）；tsc 0 / 六 check PASS

## 6. Batch D 状态

**2/4**：ShapeGallery(R12) ✅ ShapeCanvas(R13) ✅ → 余 SortingBoard(R14)、DirectionGrid(R15)。

**Vertical Gate 总进度：13/19**。
