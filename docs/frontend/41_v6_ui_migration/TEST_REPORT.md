> **历史 M1/M2 记录。当前全量范围与测试状态见 `../42_v6_full_migration/`。此处旧默认开关、覆盖范围与待办不代表当前交付状态。**

# M1/M2 验证记录 · 2026-10-11

**结论：有限范围的纯函数与静态检查通过；完整应用 Typecheck/Build 阻断，React浏览器和真实HTTP/DB用例未执行。不能将此报告当成发布验收。**

## 一、执行环境

- Node 22.16.0；npm 10.9.2；外部全局TypeScript 5.8.3。
- 输入锁文件为React18.3.1 / Next14.2.35 / TypeScript5.9.3；无成功安装的React/Next依赖。
- `npm ci` 尝试约120秒后因依赖下载无法继续而中止；registry DNS不可达。未替换镜像、升级依赖或手写React类型来冒充通过。
- 当前Python3.13.5，不满足项目Python3.12范围；没有可运行的项目DB、后端服务。未访问用户生产数据库。

## 二、已实际执行

| 项目 | 结果 | 限定范围／证据 |
|---|---|---|
| 输入与冻结文件校验 | 13/13一致 | `evidence/frozen-files-check.json`，后端/合同/序列化/registry/版本/锁文件等 |
| 纯函数与纯TS模块检查 | 38/38 PASS | `evidence/pure-checks.json`，实际生产TS函数；无React/网络模拟判分 |
| 修改TS/TSX语法转译 | 23/23 PASS | `evidence/syntax-check.json`；**不是**React组件全量类型检查 |
| Node新测试脚本语法 | PASS | `node --check` 新增Playwright用例/配置及纯函数脚本 |
| branch:check | PASS | 本地工作分支 `feat/FE-1443-v6-clock-migration` |
| governance / data hygiene | PASS | 测试只配置QA child、没有新增凭据 |
| release:check | PASS | 仍为1.4.0，不等于发布 |
| child:v14:check | PASS | 仓库既有源码静态检查 |
| renderer / contracts / frontend release脚本 | PASS | 原脚本为静态合同断言；其“Release QA PASS”输出不代表浏览器或上线验收 |
| git diff --check | PASS | 无空白／补丁格式错误 |

纯函数测试覆盖：真实clock config解析、合法错误时间、0/30分钟边界、小时范围、指针几何／拖动阈值、键盘调整值、逐步撤销、重置、RETRY保留响应、attempt_no在确认结果后递增、hint正文来源、原V2 envelope／submission_id、相同请求重发、统一主操作色、缓存异常安全。

纯模块TypeScript语义检查使用真实全局5.8.3，不使用虚构类型；它不含React/Next组件或hooks，也不替代锁定5.9.3工具链的完整检查。

## 三、阻断／未执行

| 项目 | 状态 | 实际情况 |
|---|---|---|
| 原包baseline app typecheck | BLOCKED | 修改前即缺少node/react/react-dom/prop-types类型；日志`baseline-typecheck.log` |
| 本次app typecheck | BLOCKED，exit 2 | 同类依赖缺失；`app-typecheck.log`；不能据此断言新代码没有类型错误 |
| 本次Next build | BLOCKED，exit 127 | `next: not found`，见`app-build.log` |
| React组件浏览器用例（7） | NOT_RUN | 已写`v6-clock-gallery.spec.mjs`，需要Next实际运行 |
| 真实HTTP用例（2） | NOT_RUN | 已写`v6-clock-live.spec.mjs`，需要QA后端与已批准金题 |
| 原19 Renderer E2E回归 | NOT_RUN | 未宣称旧门禁全过；legacy分支须用原测试回归 |
| 真机/辅助技术/L2/L3 | NOT_RUN | 无人工签署，不编造儿童试用或读屏结论 |
| QA Replay / 入库 / 生产持久化 | NOT_RUN | 没有执行远程写入，只有源码中的待执行测试 |
| PR / merge | NOT_RUN | ZIP来源本地工作区，没有上游仓库权限或PR对象 |

## 四、接收方复跑要求

1. 应用补丁后用锁定依赖运行完整Typecheck/Build；错误须先修，不把缺依赖日志当代码通过。
2. 运行开发组件测试，两皮肤×三视口；检查键盘行为、拖动取消、焦点、命中范围、撤销、主题切换和真实CSS布局。
3. 运行真实HTTP用例；QA child …0099，固定金题3:00→6:00。验证6:30错误可提交→提示→重试保留→6:00正确，后端记录可读。
4. 模拟服务端已保存但响应丢失；原请求重复发送只对应一个attempt，不能重复累计。
5. 开关关闭跑旧renderer测试；开启跑新切片测试。未迁移18个Renderer仍需评估共享题卡/样式对它们的影响。
6. 签署L2；开展L3。全部完成再更新PROJECT_STATUS，不因有源码交付就标DONE。

## 五、补丁应用验证

交付时对原ZIP重新解压并执行`git apply --check`、实际应用、逐文件哈希比对。相关结果另见根交付说明及`evidence/patch-replay.json`（不改变测试范围）。
