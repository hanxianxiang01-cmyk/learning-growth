# Freeze Baseline V1.3.1 — Change Summary

Date: 2026-09-28

## New control
### GATE-XLSX-CACHE — formula cache integrity
V1.3 made Summary A:F formula-driven, but XLSX formula cells also carry cached `<x:v>` results. Python consumers that do not recalculate formulas may read stale cache values after Backlog detail is modified.

V1.3.1 freezes the following delivery rule:
- any Backlog-detail edit MUST be followed by workbook recalculation using a calculation-capable engine;
- formula caches MUST be refreshed before commit/release;
- CI/Pre-commit MUST independently recompute Epic totals from Backlog detail and compare them with Summary cached values;
- missing/stale cache fails the Gate;
- a Python library that only writes formulas without calculating them cannot be the final publishing step.

## Backlog change
- Added `E0-08 XLSX公式缓存重算与Summary一致性Gate` (P0, 2 SP).
- E0 Foundation total is now: **9 Stories / 28 SP / P0=7 / P1=2**.
- Summary Gate block adds `GATE-XLSX-CACHE = HARD / PRE-COMMIT`.

## Validation asset
Added:
- `06_validate_backlog_summary_cache.py`

Validation command:
```bash
python 06_validate_backlog_summary_cache.py 05_Sprint_Backlog_v1.3.1.xlsx
```

## Unchanged semantics
- PostgreSQL schema semantics are unchanged from V1.3.
- OpenAPI contract semantics are unchanged from V1.3.
- DeepTutor SPI Gate remains RED/HARD/PENDING.
- Mastery and error-code freezes remain unchanged.

## Supersedes
Freeze V1.3 and all earlier freeze packages.
