#!/usr/bin/env bash
# CI 预提交校验：DDL + OpenAPI + Backlog Gate
# 任何一项失败即退出非零，阻断合并/发布。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$HOME/.workbuddy/binaries/python/envs/learning-engine/bin/python"

echo "===== [1/3] OpenAPI 契约校验 ====="
"$PY" "$ROOT/scripts/validate_openapi.py" "$ROOT/openapi.yaml"

echo ""
echo "===== [2/3] Backlog XLSX 缓存一致性 Gate ====="
BACKLOG="$ROOT/../../儿童学习成长系统_V2.0_冻结基线_V1.3.1同步包/05_Sprint_Backlog_v1.3.1.xlsx"
VALIDATOR="$ROOT/../../儿童学习成长系统_V2.0_冻结基线_V1.3.1同步包/06_validate_backlog_summary_cache.py"
"$PY" "$VALIDATOR" "$BACKLOG"

echo ""
echo "===== [3/3] DDL 可解析性校验（语法级） ====="
DDL="$ROOT/../../儿童学习成长系统_V2.0_冻结基线_V1.3.1同步包/01_schema_postgresql_v1.3.1.sql"
"$PY" "$ROOT/scripts/validate_ddl.py" "$DDL"

echo ""
echo "✅ CI Gate 全部通过"