# R15 DirectionGrid Vertical Gate 验收底表（FE-1427）

状态：**CLOSED**（2026-10-08）｜ 模板：B5 五件套第十四实例 ｜ 上游：docs/frontend/31 Gap R15（Batch D 收官题）

## 1. Gap R15 条目对照

| Gap 条目 | 要求 | 落地 |
|---|---|---|
| Semantic P0 | direction / position / route | 5×5 地图：起点/目标格位置关系 → 逐格移动成路线 |
| State P0 | current position / target | steps 序列（末位=脚下）+ config.start/target |
| Interaction P0 | move / route selection | **点相邻格挪一步**（上下左右）；对角/隔格/同格拒绝（NON_ADJACENT/SAME_CELL/NO_SUCH_CELL） |
| Response P0 | expected path / position | data={path,directions,move_count,turns,current,target,answer,structure}；answer=终点格编码 row*cols+col（=19） |
| Evaluator P0 | route evaluator | evaluateRoute：EMPTY→PASS(detour)→direction_reversed→wrong_position |
| Evidence P0 | movement sequence | path=["2,2","3,2",…] + directions=["down","right",…] + turns 转向数（E2E-04 断言全链） |
| Diagnosis P0 | **方向/位置关系错误** | direction_reversed——位移向量整体取反 (sr−dr, sc−dc) 恰为终点="完全往反方向走"精确命中；wrong_position 附曼哈顿距离 |
| Acceptance P0 | E2E | 10 用例全过（见 §4） |

## 2. 解耦的第六次运用（R08 同形态：判对+留痕）

金题 start=(2,2)、target=(3,4)（下1右2）。**绕路走到 ☆**（多走回头步，5 步>最短路 3 步）：
答案值=19 恰等于 expected → 后端 correct=true，但前端 `structure.detour=true` 原料走 Evidence——
到没走到=后端判、走得绕不绕=结构层说（E2E-07 双断言实证）。

**反走靶与 R14 同侧（判错也带分诊）**：上左左三步落在对称格 (1,0)，answer=5≠19 判错，
`structure.error=direction_reversed` 精确说清"错的方式是方向反了"（Diagnosis P0 落地）。
parser 守卫（行列位移非零 + 反走靶必须在盘内）保证该态**可达且与 PASS 互斥**——
每个 FAIL 态必须有可达靶，对齐 R14"三参考序互斥守卫"精神。

## 3. 与 Gap 原文差异（如实记录）

- Gap Response="expected path / position"：本 Gate 答案取**终点格编码**（标量，不动冻结判分链），
  完整路径走 Evidence `path/directions`——路径本身不判（多解路线判等需集合语义，超出标量判分链；
  绕路质量由 detour 原料承载）。
- 分诊粒度：单镜像方向错（如只上下反）终点仍可能是合法乱走位置，与 wrong_position 合一；
  direction_reversed 专抓**双镜像**（完全反走）——精确子集，其余位置错统一给距离原料。
- 原基座 DirectionGrid（单按钮选方向词）保留在 V2RendererLibrary 作参考；专件已替换路由分支。

## 4. E2E 用例（10 例，全绿）

| 用例 | 验证 | 结果 |
|---|---|---|
| E2E-01 (G1) | 25 格渲染不降级、起点/☆ 标注 | ✅ |
| E2E-02 (G2) | 未挪步拦提交（EMPTY） | ✅ |
| E2E-03 | 相邻约束：对角拒绝/相邻接受 + 脚下/起点 role | ✅（坑：cellRole start 优先于 walker——起点格离开后仍标 start，断言按角色常驻写） |
| E2E-04 (G4/G6) | envelope：type=direction_grid、answer={value:19}、path/directions/turns、PATH_EXTENDED×3、无 representation 泄漏 | ✅（坑：envelope 统一把数值答案封装成 `{value:N}`，断言先核 serialize 形态——r01/r10 同款） |
| E2E-05 | direction_reversed 专项：反走上左左→false+HINT | ✅ |
| E2E-06 (G5/G7) | 修正路径：reversed→重置→19→NEXT_TASK，attempt_no≥2 | ✅ |
| E2E-07 | detour 留痕：绕路到 ☆→correct=true + structure.detour=true + move_count=5 | ✅ |
| E2E-08 | 退一步：末步撤回、回起点按钮禁用、提交回 EMPTY | ✅ |
| E2E-09 | dblclick 防重入=1 attempt | ✅ |
| E2E-10 | healing 皮肤同链判对 | ✅ |

冷编译坑重现：E2E-06/09/10 首跑 3.7~7 分钟超时假失败，第二跑 19.8s 全绿——新组件收口前重跑一次再判定。

## 5. API 实证记录（pin=ee4d223b-…-1c26）

① pin 下发 direction-grid（config start(2,2)/target(3,4)）；② 反走 5→correct=false+HINT；
③a 同 submission 重放→200 同 attempt_id；③b 同 submission 异内容→409；
④ PASS 19（attempt_no=2）→correct=true+NEXT_TASK。

> 坑：submit 不带 attempt_no 默认 1，同 task 二次提交会撞兼容轨幂等（1.6 回放旧 attempt）——
> 重试必须显式递增 attempt_no（前端 session 页已如此，httpx 手测同样要带）。

## 6. Batch D 收官状态

**4/4**：ShapeGallery(R12) ✅ ShapeCanvas(R13) ✅ SortingBoard(R14) ✅ **DirectionGrid(R15) ✅**。
Vertical Gate 总进度 **15/19**；下一批 Batch E 生活数学 4 件：Ruler(R16)/Clock(R17)/MoneyBoard(R18)/PatternBoard(R19)。
