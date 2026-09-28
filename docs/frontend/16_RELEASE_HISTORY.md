# 16｜Release History

| Version | Release | 核心变化 |
|---|---|---|
| **1.2.0** | Learning Result Closure | Session Result API成为结果页正式数据源；behavior/change/recommendation服务端驱动 |
| **1.1.0** | Handover & Project Governance | 模块地图、路线图、接手指南、项目状态、Changelog |
| **1.0.0** | Runnable Learning Flow | 18组件、4核心页面、状态机、Mock/HTTP、双Built-in Skin |

机器可读历史：

```text
releases/index.json
releases/1.0.0.json
releases/1.1.0.json
releases/1.2.0.json
```

## 自动版本一致性检查

```bash
npm run release:check
```

检查：

```text
VERSION
package.json
project_manifest.json
releases/index.json
releases/{version}.json
CHANGELOG.md
```

任何一项版本不一致即失败。

## 后续发布示例

开发 V1.3：

```text
1. 在 CHANGELOG [Unreleased] 记录开发变化
2. 完成验收
3. VERSION → 1.3.0
4. package.json → 1.3.0
5. project_manifest → 1.3.0
6. 新建 releases/1.3.0.json
7. 更新 releases/index.json
8. 把 Unreleased 内容归档到 [1.3.0]
9. npm run release:check
10. npm run typecheck
11. npm run build
12. 打包 Math_Sprint3_Frontend_V1.3.zip
```
