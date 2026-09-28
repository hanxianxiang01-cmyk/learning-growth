# 12｜版本管理规范

## 目标

任何开发人员拿到项目后，都能回答：

1. 当前版本是什么？
2. 上一版是什么？
3. 本版新增了什么？
4. 本版修改了什么？
5. 有没有Breaking Change？
6. 已知问题是什么？
7. 下一版做什么？

---

# 一、版本号唯一规则

采用 Semantic Versioning：

```text
MAJOR.MINOR.PATCH
```

### MAJOR
架构边界或对外Contract出现重大不兼容。

例如：
- Learning API大规模Breaking Change
- Routing整体重构
- Task Schema 2.0不兼容1.x

### MINOR
增加完整可用能力且向后兼容。

例如：
- V1.2 Session Result闭环
- V1.3 Task Renderer
- 新增正式模块

### PATCH
修Bug、小型视觉调整、非Breaking兼容修正。

例如：
- 1.2.1 Result空状态修复
- 1.2.2 iPad布局修复

---

# 二、版本 Source of Truth

必须保持一致：

```text
VERSION
package.json
CHANGELOG.md
project_manifest.json
releases/{version}.json
```

如果不一致：

> `VERSION` + `package.json` 视为构建版本，必须在发布前修复其他文件。

---

# 三、每次版本发布必须更新

## 必改

```text
VERSION
package.json
CHANGELOG.md
project_manifest.json
releases/{version}.json
```

## 按需

```text
README.md
docs/模块地图
docs/项目状态
docs/API Mapping
docs/State Machine
Migration Guide
Known Issues
```

---

# 四、Changelog分类

统一使用：

```text
Added
Changed
Fixed
Deprecated
Removed
Compatibility
Known Issues / Known Constraint
```

不要只写“优化了一些内容”。

必须写清：
- 哪个模块
- 哪个文件/接口
- 变化前
- 变化后
- 是否影响旧代码

---

# 五、Release Manifest

每个Minor/Major版本新增：

```text
releases/X.Y.Z.json
```

机器可读记录：
- version
- release_date
- release_name
- previous_version
- added
- changed
- breaking_changes
- known_constraints
- source_of_truth

便于后续 AI 工程师读取。

---

# 六、迁移说明

Minor版本如果改变数据来源或集成方式，必须增加：

```text
docs/MIGRATION_旧版本_TO_新版本.md
```

即使没有Breaking Change，也要告诉接手者“该删什么旧逻辑”。

---

# 七、禁止

禁止：
- 只改zip文件名不改package版本
- 只改package.json不写CHANGELOG
- 修改API Contract不写迁移说明
- 把未完成占位功能写成“已完成”
- 删除旧版本历史


---

# 八、自动一致性检查

项目提供：

```bash
npm run release:check
```

脚本：

```text
scripts/check-release.mjs
```

会自动检查：

```text
VERSION
package.json
project_manifest.json
releases/index.json
releases/{version}.json
CHANGELOG.md
```

正式发版前必须通过。
