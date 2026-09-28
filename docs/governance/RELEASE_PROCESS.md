# Release Process

正式Release步骤：

```text
Milestone scope locked
 ↓
All target Issues DONE
 ↓
All target PRs merged
 ↓
CI green on main
 ↓
CHANGELOG [Unreleased] → [X.Y.Z]
 ↓
VERSION / package versions / release manifests
 ↓
npm run governance:check
npm run release:check
npm run child:typecheck
npm run child:build
 ↓
git tag vX.Y.Z
 ↓
Release Artifact ZIP
```

ZIP只在这里生成。

日常协作禁止用ZIP覆盖别人工作。
