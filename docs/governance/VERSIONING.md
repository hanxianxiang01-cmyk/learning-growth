# Versioning

## Product Version

当前：

```text
1.2.0
```

采用 SemVer：

```text
MAJOR.MINOR.PATCH
```

- MAJOR：不兼容架构/API改变
- MINOR：新增完整向后兼容能力
- PATCH：修复与小兼容改动

## Governance Version

仓库治理单独版本：

```text
GOVERNANCE_VERSION = 1.0.0
```

避免把“仓库治理升级”误当成产品功能版本。

## Release Source of Truth

必须一致：

```text
VERSION
package.json
apps/child-web/package.json
CHANGELOG.md
project_manifest.json
releases/index.json
releases/{version}.json
git tag v{version}
```

## Development

开发中的变化只写：

```text
CHANGELOG.md → [Unreleased]
```

不要每个PR都升版本。

## Release

Milestone全部完成后：

1. Freeze scope
2. CI green
3. CHANGELOG归档
4. VERSION bump
5. manifests更新
6. `npm run release:check`
7. tag `vX.Y.Z`
8. 生成ZIP/Release Artifact
