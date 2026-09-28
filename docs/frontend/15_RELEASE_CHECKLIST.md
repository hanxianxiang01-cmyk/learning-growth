# 15｜Release Checklist

发布任何正式版本前逐项确认。

## Version
- [ ] `VERSION` 已更新
- [ ] `package.json.version` 一致
- [ ] `project_manifest.json.version` 一致
- [ ] `CHANGELOG.md` 有该版本
- [ ] `releases/{version}.json` 存在

## Automated Version Check
- [ ] `npm run release:check` 通过

## Code
- [ ] TypeScript语法检查
- [ ] Import检查
- [ ] Mock主流程可跑
- [ ] HTTP适配器Contract检查
- [ ] 新增状态有文档
- [ ] 新增API有Mapping

## Product
- [ ] 未完成能力没有标记成✅
- [ ] 孩子端无研发术语
- [ ] 教育判断没有移到前端
- [ ] 默认Skin没有被意外修改

## Docs
- [ ] README
- [ ] Module Map
- [ ] Project Status
- [ ] Roadmap
- [ ] Known Issues
- [ ] Migration Guide（如需要）

## Package
- [ ] ZIP名称与版本一致
- [ ] ZIP内根目录版本一致
