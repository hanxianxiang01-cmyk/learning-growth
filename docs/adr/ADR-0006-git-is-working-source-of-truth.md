# ADR-0006｜Git Is the Working Source of Truth

**Status:** Accepted

## Decision

```text
Git main = development source of truth
Tag = release identity
ZIP = release artifact
```

ZIP不再用于日常多人/多AI开发合并。

## Consequence
所有开发通过 branch + PR 合并。
