# V6 全量覆盖与设计落实

## 来源及边界

原始源码：`learning-growth-main (1).zip`，SHA-256 `b2a925b76358fdda4164da663599ffeeb4ddb44e3225b90b19fe5b7d12c7f401`。

视觉参考：`V14_Full_Illustrated_UI_v6.html`，SHA-256 `a346be99ffb364932bb71b94fee60395c734c529ccd5d8100d3a6ee3e8c6df66`。仅提取其中装饰性的背景/角色 SVG，正文、节点数据、工作区状态及提交逻辑仍由 React 与现有 API 驱动。没有把 HTML 的演示判题器、假学习记录或固定答案复制进运行逻辑。

本轮承接 M1/M2 已有公共框架与 Clock，再一次补齐生产19 Renderer和四类页面。所有原始文件均保留；有改动的文件会在补丁和 SOURCE_MANIFEST 中明确列出，不用另一套小型示例工程冒充全量仓库。

## 页面覆盖

| 页面 | 本轮实现 | 真实数据与约束 |
|---|---|---|
| 首页 | 场景背景、任务主卡、原有5类挑战、能力记录入口、加载/错误/重试 | 原profile/abilities/createSession；同步创建锁防重入；不伪造“今日3/5已完成” |
| 成长地图 | 七项能力的错落节点、真实连线路径、选择详情、手机内联详情 | 固定展示顺序不代表先修关系；只显示API level/count/trend，缺失显示待了解；没有锁关或本地掌握度公式 |
| 任务与反馈 | 原生题目、工作区、提交、错误/提示/重试/正确/结束与网络恢复 | 后端next_action和hint为准；合法错误答案可到达提交；待确认请求原样重发 |
| 学习小结 | 真实计数、行为记录、能力前后等级、后续入口、临时记录提示 | hint_usage是去重提示级别，不能当提示次数；临时记录不能伪装为正式能力评价 |

## Renderer 覆盖

| 生产ID | 对应组件（`src/components/renderers/`） | V6工作区内容 |
|---|---|---|
| `object-counter` | `ObjectCounterV2` | 分组计数、组合/拆分；保留真实计数与事件 |
| `bar-model` | `BarModelV2` | 线段块/已知与未知量，操作按钮保持可见 |
| `number-line` | `NumberLineV2` | 按真实刻度显示所有支持范围内刻度、跳跃弧线、窄屏原生滚动 |
| `number-input` | `NumberInputV2` | 原输入契约+数字键盘/退一位/清空，不以正确性限制提交 |
| `column-arithmetic` | `ColumnArithmetic` | 竖式位值、结果输入、进位；原列位置不变 |
| `place-value` | `PlaceValueV2` | 位值槽与数字卡片，不改变编码 |
| `ten-frame` | `TenFrameV2` | 十格、打包成十、拆分；不把目标答案当作当前操作结果 |
| `array-board` | `ArrayBoardV2` | 真实行列阵列与行列控制 |
| `grouping-board` | `GroupingBoardV2` | 分组、分配、真实余量 |
| `formula-board` | `FormulaBoardV2` | 数值槽与运算符两种金题模式 |
| `estimation-canvas` | `EstimationCanvasV2` | 真实数量参考物、估算滑条和理由选择 |
| `shape-gallery` | `ShapeGalleryV2` | 正确几何形状，任务语义颜色保持；明确放入操作 |
| `shape-canvas` | `ShapeCanvasV2` | 钉板、顶点、连线、键盘可访问点位 |
| `sorting-board` | `SortingBoardV2` | 交换卡片；保留题目原视觉干扰/数值关系 |
| `direction-grid` | `DirectionGridV2` | 真实格点/方向移动/当前坐标；窄屏不压缩几何 |
| `ruler` | `RulerV2` | 物体起止对准真实刻度，保留零点与非零起点测量 |
| `clock` | `ClockV2 + ClockV6` | 真实时针/分针、原parser/serializer，指针与键盘交互 |
| `money-board` | `MoneyBoardV2` | 真实面额与数量，不用皮肤色替换题目含义 |
| `pattern-board` | `PatternBoardV2` | 规律令牌、原语义颜色、标签和提交编码 |

## “全量”的具体口径

本次生产范围是冻结清单 `V2_RELEASE_RENDERER_IDS` 的19种，不把注册层23个协议枚举等同于23个生产实现。测试使用20个原仓库金题示例，覆盖19种；并不宣称已经遍历每个renderer的所有配置组合和所有数值边界。

历史V1数据继续走原兼容路径，不能为了视觉迁移强制改成V2数据、重写response或重灌题库。公共题干、页面、反馈与主题已统一接入；原V1交互协议和兼容控件仍保留，不在本次19个V2工作区的逐项浏览器检查口径内。开发画廊不混用V1演示题冒充V2生产覆盖。

## 关键设计约束

场景/角色是装饰层；能力等级、证据数、题干、选项及刻度为可编辑React层。手机端不把宽尺子/数轴压成不可用的细刻度，而在工作区内滚动；页面根节点不得横向溢出。屏幕较小时隐藏会抢占题干的装饰角色，不让插画覆盖文字。坐标/比例/刻度保留原数学含义，皮肤不重绘语义颜色。

成长地图API目前只提供聚合能力记录，没有逐条证据明细端点，因此详情只显示可证实的等级/记录数/趋势及能力说明，不编造最近三条学习事件。七个节点全可选择，缺失记录不是“未解锁”。未知trend按中性文案降级，不计算本地Mastery。

## 保持不变与必要共享修正

原后端、DB定义、原seed脚本、packages、OpenAPI、学习API协议/适配器/normalizer和数学纯模块保持原字节；最终哈希核对见 `evidence/frozen-files.json`。应用版本和package-lock保持原值；package.json仅增启动/检查命令。

共享层修正并非新数学规则：重试保留原作答；不确定网络错误使用相同submission_id及相同body重发；收到确认后计数一次；提示使用服务端attempt_id；浏览器缓存不可用时不能把已经成功的服务端提交变成失败；结果请求在旧会话失效后不覆盖新会话。V1/V2响应分流及后端判分逻辑没有替换。

## 交付状态

源码覆盖已完成；锁定工具链构建、真实Next浏览器、真实后端与L2/L3验收仍是交付后的必要验证项。不标Issue DONE，不创建或虚构PR合并，不宣称已经上线。`legacy`是显式回滚开关，不是遇到不支持题目时静默显示旧固定题。
